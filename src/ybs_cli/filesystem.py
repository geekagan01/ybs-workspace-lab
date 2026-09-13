import json
import os
import re
import socket
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager as ContextManager
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ybs_cli.errors import YbsError

_TASK_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,63}$")


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
    """Replace a file only after its new contents are durable."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
        raise YbsError(f"atomic write failed for {path}: {exc}", 5) from exc


def task_lock(root: Path, task_id: str) -> ContextManager[None]:
    """Return a conservative process lock for one validated task ID."""
    if _TASK_ID_PATTERN.fullmatch(task_id) is None:
        raise YbsError(f"invalid task id: {task_id}", 2)
    lock_path = resolve_inside(root, Path(".ybs") / "locks" / f"{task_id}.lock")
    return _held_task_lock(lock_path)


@contextmanager
def _held_task_lock(lock_path: Path) -> Iterator[None]:
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise YbsError(f"task lock unavailable: {lock_path}: {exc}", 5) from exc

    owner_bytes = _owner_record()
    while not _create_lock(lock_path, owner_bytes):
        if not _recover_dead_local_owner(lock_path):
            raise YbsError(f"task lock unavailable: {lock_path}", 5)

    try:
        yield
    finally:
        _release_if_owned(lock_path, owner_bytes)


def _owner_record() -> bytes:
    metadata = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    return json.dumps(metadata, separators=(",", ":")).encode()


def _create_lock(lock_path: Path, owner_bytes: bytes) -> bool:
    try:
        file_descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    except OSError as exc:
        raise YbsError(f"task lock unavailable: {lock_path}: {exc}", 5) from exc

    identity = os.fstat(file_descriptor)
    try:
        remaining = memoryview(owner_bytes)
        while remaining:
            written = os.write(file_descriptor, remaining)
            if written == 0:
                raise OSError("lock metadata write made no progress")
            remaining = remaining[written:]
        os.fsync(file_descriptor)
    except OSError as exc:
        _close_quietly(file_descriptor)
        _unlink_if_same_file(lock_path, identity.st_dev, identity.st_ino)
        raise YbsError(f"task lock unavailable: {lock_path}: {exc}", 5) from exc
    try:
        os.close(file_descriptor)
    except OSError as exc:
        _unlink_if_same_file(lock_path, identity.st_dev, identity.st_ino)
        raise YbsError(f"task lock unavailable: {lock_path}: {exc}", 5) from exc
    return True


def _close_quietly(file_descriptor: int) -> None:
    with suppress(OSError):
        os.close(file_descriptor)


def _unlink_if_same_file(path: Path, device: int, inode: int) -> None:
    try:
        current = path.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) == (device, inode):
            path.unlink()
    except OSError:
        pass


def _recover_dead_local_owner(lock_path: Path) -> bool:
    try:
        observed_bytes = lock_path.read_bytes()
        metadata = json.loads(observed_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False

    if not _valid_lock_metadata(metadata) or metadata["host"] != socket.gethostname():
        return False

    try:
        os.kill(metadata["pid"], 0)
    except ProcessLookupError:
        pass
    except (PermissionError, OSError):
        return False
    else:
        return False

    try:
        if lock_path.read_bytes() != observed_bytes:
            return False
        lock_path.unlink()
    except OSError:
        return False
    return True


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


def _release_if_owned(lock_path: Path, owner_bytes: bytes) -> None:
    try:
        if lock_path.read_bytes() == owner_bytes:
            lock_path.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise YbsError(f"task lock release failed: {lock_path}: {exc}", 5) from exc
