import errno
import fcntl
import json
import os
import re
import secrets
import socket
from collections.abc import Iterator
from contextlib import AbstractContextManager as ContextManager
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ybs_cli.errors import YbsError

_TASK_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,63}$")
_DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


def resolve_inside(root: Path, candidate: str | Path) -> Path:
    """Resolve a candidate path and prove that it remains below root."""
    try:
        resolved_root = root.resolve()
        candidate_path = Path(candidate)
        resolved_candidate = (
            candidate_path.resolve()
            if candidate_path.is_absolute()
            else (resolved_root / candidate_path).resolve()
        )
    except (OSError, RuntimeError) as exc:
        raise YbsError(f"cannot resolve workspace path: {candidate}: {exc}", 5) from exc
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise YbsError(f"path is outside workspace: {candidate}", 5) from exc
    return resolved_candidate


def atomic_write(path: Path, content: bytes) -> None:
    """Replace a file through one opened, symlink-free parent directory."""
    parent_descriptor = -1
    temporary_descriptor = -1
    temporary_name: str | None = None
    temporary_identity: tuple[int, int] | None = None
    try:
        target_name = _path_name(path)
        parent_descriptor = _open_directory(path.parent)
        temporary_name, temporary_descriptor = _create_temporary_file(
            parent_descriptor, target_name
        )
        temporary_stat = os.fstat(temporary_descriptor)
        temporary_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
        temporary_file = os.fdopen(temporary_descriptor, "wb")
        temporary_descriptor = -1
        with temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(
            temporary_name,
            target_name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
    except OSError as exc:
        _close_quietly(temporary_descriptor)
        if temporary_name is not None and temporary_identity is not None and parent_descriptor >= 0:
            with suppress(OSError):
                _unlink_if_same_file_at(parent_descriptor, temporary_name, temporary_identity)
        raise YbsError(f"atomic write failed for {path}: {exc}", 5) from exc
    finally:
        _close_quietly(parent_descriptor)


def task_lock(root: Path, task_id: str) -> ContextManager[None]:
    """Return a conservative process lock for one validated task ID."""
    if _TASK_ID_PATTERN.fullmatch(task_id) is None:
        raise YbsError(f"invalid task id: {task_id}", 2)
    try:
        resolved_root = root.resolve()
        root_stat = resolved_root.stat()
    except (OSError, RuntimeError) as exc:
        raise YbsError(f"task lock unavailable: {task_id}: {exc}", 5) from exc
    root_identity = (root_stat.st_dev, root_stat.st_ino)
    return _held_task_lock(resolved_root, root_identity, task_id)


@contextmanager
def _held_task_lock(root: Path, root_identity: tuple[int, int], task_id: str) -> Iterator[None]:
    root_descriptor = -1
    ybs_descriptor = -1
    locks_descriptor = -1
    lock_name = f"{task_id}.lock"
    try:
        root_descriptor = _open_directory(root)
        opened_root_stat = os.fstat(root_descriptor)
        if (opened_root_stat.st_dev, opened_root_stat.st_ino) != root_identity:
            raise OSError(errno.ESTALE, "workspace root changed before lock acquisition")
        ybs_descriptor = _open_or_create_directory(root_descriptor, ".ybs")
        locks_descriptor = _open_or_create_directory(ybs_descriptor, "locks")
        owner_bytes = _owner_record()
        if not _create_lock(
            locks_descriptor, lock_name, owner_bytes
        ) and not _recover_and_create_lock(locks_descriptor, lock_name, owner_bytes):
            raise YbsError(f"task lock unavailable: {task_id}", 5)
    except YbsError:
        _close_directories(locks_descriptor, ybs_descriptor, root_descriptor)
        raise
    except OSError as exc:
        _close_directories(locks_descriptor, ybs_descriptor, root_descriptor)
        raise YbsError(f"task lock unavailable: {task_id}: {exc}", 5) from exc

    try:
        yield
    finally:
        try:
            _release_if_owned(locks_descriptor, lock_name, owner_bytes)
        finally:
            _close_directories(locks_descriptor, ybs_descriptor, root_descriptor)


def _path_name(path: Path) -> str:
    name = path.name
    if name in {"", ".", ".."}:
        raise OSError(errno.EINVAL, f"invalid file name: {path}")
    return name


def _open_directory(path: Path) -> int:
    start = path.anchor if path.is_absolute() else "."
    descriptor = os.open(start, _DIRECTORY_OPEN_FLAGS)
    try:
        for component in path.parts:
            if component in {path.anchor, "", "."}:
                continue
            if component == "..":
                raise OSError(errno.EINVAL, f"parent traversal is not allowed: {path}")
            child_descriptor = os.open(
                component,
                _DIRECTORY_OPEN_FLAGS,
                dir_fd=descriptor,
            )
            try:
                os.close(descriptor)
            except OSError:
                _close_quietly(child_descriptor)
                raise
            descriptor = child_descriptor
    except BaseException:
        _close_quietly(descriptor)
        raise
    return descriptor


def _open_or_create_directory(parent_descriptor: int, name: str) -> int:
    with suppress(FileExistsError):
        os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
    return os.open(name, _DIRECTORY_OPEN_FLAGS, dir_fd=parent_descriptor)


def _create_temporary_file(parent_descriptor: int, target_name: str) -> tuple[str, int]:
    for _ in range(100):
        name = f".{target_name}.{secrets.token_hex(8)}.tmp"
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent_descriptor,
            )
        except FileExistsError:
            continue
        return name, descriptor
    raise OSError(errno.EEXIST, "could not allocate a unique temporary file")


def _owner_record() -> bytes:
    metadata = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    return json.dumps(metadata, separators=(",", ":")).encode()


def _create_lock(
    directory_descriptor: int,
    lock_name: str,
    owner_bytes: bytes,
    *,
    recovery_guard_held: bool = False,
) -> bool:
    try:
        file_descriptor = os.open(
            lock_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_descriptor,
        )
    except FileExistsError:
        return False
    except OSError as exc:
        raise YbsError(f"task lock unavailable: {lock_name}: {exc}", 5) from exc

    identity: tuple[int, int] | None = None
    try:
        file_stat = os.fstat(file_descriptor)
        identity = (file_stat.st_dev, file_stat.st_ino)
        _write_all(file_descriptor, owner_bytes)
        os.fsync(file_descriptor)
        os.close(file_descriptor)
    except OSError as exc:
        _close_quietly(file_descriptor)
        if identity is not None:
            with suppress(OSError):
                if recovery_guard_held:
                    _unlink_if_same_file_at(directory_descriptor, lock_name, identity)
                else:
                    with _recovery_guard(directory_descriptor, lock_name):
                        _unlink_if_same_file_at(directory_descriptor, lock_name, identity)
        raise YbsError(f"task lock unavailable: {lock_name}: {exc}", 5) from exc
    return True


def _write_all(file_descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = os.write(file_descriptor, remaining)
        if written == 0:
            raise OSError("write made no progress")
        remaining = remaining[written:]


def _recover_and_create_lock(directory_descriptor: int, lock_name: str, owner_bytes: bytes) -> bool:
    try:
        with _recovery_guard(directory_descriptor, lock_name):
            if _create_lock(
                directory_descriptor,
                lock_name,
                owner_bytes,
                recovery_guard_held=True,
            ):
                return True
            if not _recover_dead_local_owner(directory_descriptor, lock_name):
                return False
            return _create_lock(
                directory_descriptor,
                lock_name,
                owner_bytes,
                recovery_guard_held=True,
            )
    except OSError as exc:
        raise YbsError(f"task lock unavailable: {lock_name}: {exc}", 5) from exc


@contextmanager
def _recovery_guard(directory_descriptor: int, lock_name: str) -> Iterator[None]:
    guard_name = f".{lock_name}.recovery"
    guard_descriptor = os.open(
        guard_name,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory_descriptor,
    )
    try:
        fcntl.flock(guard_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        _close_quietly(guard_descriptor)


def _recover_dead_local_owner(directory_descriptor: int, lock_name: str) -> bool:
    try:
        observed_bytes, observed_identity = _read_file_at(directory_descriptor, lock_name)
        metadata = json.loads(observed_bytes)
    except (OSError, RecursionError, UnicodeDecodeError, ValueError):
        return False

    if not _valid_lock_metadata(metadata) or metadata["host"] != socket.gethostname():
        return False

    try:
        os.kill(metadata["pid"], 0)
    except ProcessLookupError:
        pass
    except (PermissionError, OSError, OverflowError):
        return False
    else:
        return False

    try:
        current_bytes, current_identity = _read_file_at(directory_descriptor, lock_name)
    except OSError:
        return False
    if current_bytes != observed_bytes or current_identity != observed_identity:
        return False
    try:
        return _unlink_if_same_file_at(directory_descriptor, lock_name, observed_identity)
    except OSError:
        return False


def _read_file_at(directory_descriptor: int, name: str) -> tuple[bytes, tuple[int, int]]:
    file_descriptor = os.open(name, _FILE_OPEN_FLAGS, dir_fd=directory_descriptor)
    try:
        file_stat = os.fstat(file_descriptor)
        chunks = []
        while chunk := os.read(file_descriptor, 64 * 1024):
            chunks.append(chunk)
    finally:
        _close_quietly(file_descriptor)
    return b"".join(chunks), (file_stat.st_dev, file_stat.st_ino)


def _unlink_if_same_file_at(
    directory_descriptor: int, name: str, identity: tuple[int, int]
) -> bool:
    current = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    if (current.st_dev, current.st_ino) != identity:
        return False
    os.unlink(name, dir_fd=directory_descriptor)
    return True


def _release_if_owned(directory_descriptor: int, lock_name: str, owner_bytes: bytes) -> None:
    try:
        with _recovery_guard(directory_descriptor, lock_name):
            current_bytes, current_identity = _read_file_at(directory_descriptor, lock_name)
            if current_bytes == owner_bytes:
                _unlink_if_same_file_at(directory_descriptor, lock_name, current_identity)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise YbsError(f"task lock release failed: {lock_name}: {exc}", 5) from exc


def _valid_lock_metadata(metadata: object) -> bool:
    return (
        isinstance(metadata, dict)
        and set(metadata) == {"pid", "host", "created_at"}
        and type(metadata["pid"]) is int
        and metadata["pid"] > 0
        and isinstance(metadata["host"], str)
        and bool(metadata["host"])
        and isinstance(metadata["created_at"], str)
        and _is_aware_utc_timestamp(metadata["created_at"])
    )


def _is_aware_utc_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def _close_directories(*descriptors: int) -> None:
    for descriptor in descriptors:
        _close_quietly(descriptor)


def _close_quietly(file_descriptor: int) -> None:
    if file_descriptor < 0:
        return
    with suppress(OSError):
        os.close(file_descriptor)
