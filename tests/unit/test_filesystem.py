import errno
import json
import os
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from ybs_cli.errors import YbsError
from ybs_cli.filesystem import atomic_write, resolve_inside, task_lock


def test_resolve_inside_accepts_relative_and_absolute_paths_inside_root(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "status.yaml"

    assert resolve_inside(tmp_path, "nested/status.yaml") == nested
    assert resolve_inside(tmp_path, nested) == nested


def test_resolve_inside_rejects_parent_escape(tmp_path: Path) -> None:
    with pytest.raises(YbsError, match="outside workspace") as exc_info:
        resolve_inside(tmp_path, "../secret.txt")

    assert exc_info.value.code == 5


def test_resolve_inside_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(YbsError, match="outside workspace") as exc_info:
        resolve_inside(tmp_path, "link/secret.txt")

    assert exc_info.value.code == 5


def test_resolve_inside_maps_symlink_loop_to_operational_error(tmp_path: Path) -> None:
    (tmp_path / "loop").symlink_to("loop")

    with pytest.raises(YbsError, match="cannot resolve workspace path") as exc_info:
        resolve_inside(tmp_path, "loop/status.yaml")

    assert exc_info.value.code == 5


def test_atomic_write_replaces_file_without_leaving_temporary_files(tmp_path: Path) -> None:
    target = tmp_path / "status.yaml"
    target.write_bytes(b"stage: intake\n")

    atomic_write(target, b"stage: clarify\n")

    assert target.read_bytes() == b"stage: clarify\n"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_preserves_old_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "status.yaml"
    unrelated = tmp_path / ".keep.tmp"
    target.write_bytes(b"stage: intake\n")
    unrelated.write_bytes(b"keep")
    monkeypatch.setattr("ybs_cli.filesystem.os.replace", Mock(side_effect=OSError("boom")))

    with pytest.raises(YbsError, match="atomic write failed") as exc_info:
        atomic_write(target, b"stage: clarify\n")

    assert exc_info.value.code == 5
    assert target.read_bytes() == b"stage: intake\n"
    assert unrelated.read_bytes() == b"keep"
    assert sorted(path.name for path in tmp_path.iterdir()) == [".keep.tmp", "status.yaml"]


def test_atomic_write_requires_existing_parent_directory(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "status.yaml"

    with pytest.raises(YbsError, match="atomic write failed") as exc_info:
        atomic_write(target, b"stage: intake\n")

    assert exc_info.value.code == 5
    assert not target.parent.exists()


def test_atomic_write_rejects_symlink_target_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(YbsError, match="atomic write failed") as exc_info:
        atomic_write(linked_parent / "status.yaml", b"stage: intake\n")

    assert exc_info.value.code == 5
    assert not (outside / "status.yaml").exists()


def test_atomic_write_stays_bound_to_open_parent_when_path_is_swapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "state"
    parent.mkdir()
    moved_parent = tmp_path / "state-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = parent / "status.yaml"
    target.write_bytes(b"stage: intake\n")
    (outside / "status.yaml").write_bytes(b"outside\n")
    real_replace = os.replace

    def swap_parent_then_replace(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        parent.rename(moved_parent)
        parent.symlink_to(outside, target_is_directory=True)
        real_replace(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(os, "replace", swap_parent_then_replace)

    atomic_write(target, b"stage: clarify\n")

    assert (moved_parent / "status.yaml").read_bytes() == b"stage: clarify\n"
    assert (outside / "status.yaml").read_bytes() == b"outside\n"


def test_task_lock_rejects_invalid_task_id_before_creating_lock_directory(
    tmp_path: Path,
) -> None:
    with (
        pytest.raises(YbsError, match="invalid task id") as exc_info,
        task_lock(tmp_path, "../../escape"),
    ):
        pass

    assert exc_info.value.code == 2
    assert not (tmp_path / ".ybs").exists()


def test_task_lock_rejects_ybs_directory_swapped_to_symlink_before_entry(
    tmp_path: Path,
) -> None:
    ybs_directory = tmp_path / ".ybs"
    (ybs_directory / "locks").mkdir(parents=True)
    held_directory = tmp_path / ".ybs-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    pending_lock = task_lock(tmp_path, "DEMO-101")
    ybs_directory.rename(held_directory)
    ybs_directory.symlink_to(outside, target_is_directory=True)

    with pytest.raises(YbsError, match="task lock unavailable") as exc_info, pending_lock:
        pass

    assert exc_info.value.code == 5
    assert not (outside / "locks").exists()


def test_task_lock_maps_hostname_failure_to_operational_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_hostname_lookup() -> str:
        raise OSError("hostname unavailable")

    monkeypatch.setattr(socket, "gethostname", fail_hostname_lookup)

    with (
        pytest.raises(YbsError, match="task lock unavailable") as exc_info,
        task_lock(tmp_path, "DEMO-101"),
    ):
        pass

    assert exc_info.value.code == 5
    assert not (tmp_path / ".ybs" / "locks" / "DEMO-101.lock").exists()


def test_task_lock_closes_descriptor_and_keeps_lock_when_fstat_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    real_open = os.open
    real_fstat = os.fstat
    created_lock_descriptor = -1

    def record_lock_descriptor(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal created_lock_descriptor
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if os.fspath(path) == "DEMO-101.lock" and flags & os.O_EXCL:
            created_lock_descriptor = descriptor
        return descriptor

    def fail_for_created_lock(descriptor: int) -> os.stat_result:
        if descriptor == created_lock_descriptor:
            raise OSError("fstat unavailable")
        return real_fstat(descriptor)

    with monkeypatch.context() as context:
        context.setattr(os, "open", record_lock_descriptor)
        context.setattr(os, "fstat", fail_for_created_lock)
        with (
            pytest.raises(YbsError, match="task lock unavailable") as exc_info,
            task_lock(tmp_path, "DEMO-101"),
        ):
            pass

    assert exc_info.value.code == 5
    assert created_lock_descriptor >= 0
    with pytest.raises(OSError) as closed_error:
        real_fstat(created_lock_descriptor)
    assert closed_error.value.errno == errno.EBADF
    assert lock_path.exists()


def test_task_lock_active_same_host_pid_cannot_be_stolen(tmp_path: Path) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"

    with task_lock(tmp_path, "DEMO-101"):
        owner = json.loads(lock_path.read_text())
        assert set(owner) == {"pid", "host", "created_at"}
        assert owner["pid"] == os.getpid()
        assert owner["host"] == socket.gethostname()
        assert datetime.fromisoformat(owner["created_at"]).utcoffset() == timedelta(0)

        with (
            pytest.raises(YbsError, match="task lock unavailable") as exc_info,
            task_lock(tmp_path, "DEMO-101"),
        ):
            pass

        assert exc_info.value.code == 5
        assert json.loads(lock_path.read_text()) == owner

    assert not lock_path.exists()


def test_task_lock_recovers_confirmed_dead_same_host_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    lock_path.parent.mkdir(parents=True)
    stale_owner = {
        "pid": 12345,
        "host": socket.gethostname(),
        "created_at": "2026-09-13T00:00:00+00:00",
    }
    lock_path.write_text(json.dumps(stale_owner))

    def report_dead_process(pid: int, signal: int) -> None:
        assert (pid, signal) == (12345, 0)
        raise ProcessLookupError

    monkeypatch.setattr(os, "kill", report_dead_process)

    with task_lock(tmp_path, "DEMO-101"):
        recovered_owner = json.loads(lock_path.read_text())
        assert recovered_owner["pid"] == os.getpid()
        assert recovered_owner["host"] == socket.gethostname()
        assert recovered_owner != stale_owner

    assert not lock_path.exists()


def test_task_lock_serializes_two_contenders_recovering_same_stale_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    lock_path.parent.mkdir(parents=True)
    stale_pid = 12345
    stale_owner = {
        "pid": stale_pid,
        "host": socket.gethostname(),
        "created_at": "2026-09-13T00:00:00+00:00",
    }
    lock_path.write_text(json.dumps(stale_owner))

    real_kill = os.kill

    def report_only_stale_process_dead(pid: int, signal: int) -> None:
        if pid == stale_pid:
            raise ProcessLookupError
        real_kill(pid, signal)

    monkeypatch.setattr(os, "kill", report_only_stale_process_dead)

    real_read_bytes = Path.read_bytes
    read_condition = threading.Condition()
    reads_by_thread: dict[int, int] = {}
    second_read_count = 0
    contender_outcome = threading.Event()

    def synchronize_stale_comparison(path: Path) -> bytes:
        nonlocal second_read_count
        contents = real_read_bytes(path)
        if path == lock_path:
            thread_id = threading.get_ident()
            with read_condition:
                reads_by_thread[thread_id] = reads_by_thread.get(thread_id, 0) + 1
                if reads_by_thread[thread_id] == 2:
                    second_read_count += 1
                    read_condition.notify_all()
                    assert read_condition.wait_for(
                        lambda: second_read_count == 2 or contender_outcome.is_set(), timeout=2
                    )
        return contents

    monkeypatch.setattr(Path, "read_bytes", synchronize_stale_comparison)

    real_unlink = Path.unlink
    unlink_mutex = threading.Lock()
    recovery_unlink_count = 0
    first_owner_entered = threading.Event()

    def delay_second_recovery_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal recovery_unlink_count
        if path == lock_path:
            with unlink_mutex:
                recovery_unlink_count += 1
                unlink_number = recovery_unlink_count
            if unlink_number == 2:
                assert first_owner_entered.wait(timeout=2)
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", delay_second_recovery_unlink)

    result_mutex = threading.Lock()
    entered: list[str] = []
    errors: list[BaseException] = []
    overlap = threading.Event()

    def contend(name: str) -> None:
        try:
            with task_lock(tmp_path, "DEMO-101"):
                with result_mutex:
                    entered.append(name)
                    first = len(entered) == 1
                    if not first:
                        overlap.set()
                        contender_outcome.set()
                first_owner_entered.set()
                if first:
                    assert contender_outcome.wait(timeout=2)
        except BaseException as exc:
            with result_mutex:
                errors.append(exc)
            contender_outcome.set()
            with read_condition:
                read_condition.notify_all()

    contenders = [threading.Thread(target=contend, args=(name,)) for name in ("A", "B")]
    for contender in contenders:
        contender.start()
    for contender in contenders:
        contender.join(timeout=3)

    assert all(not contender.is_alive() for contender in contenders)
    assert not overlap.is_set()
    assert len(entered) == 1, errors
    assert len(errors) == 1
    assert isinstance(errors[0], YbsError)
    assert errors[0].code == 5


def test_task_lock_never_recovers_remote_host_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    lock_path.parent.mkdir(parents=True)
    remote_owner = {
        "pid": 12345,
        "host": "remote.example",
        "created_at": "2026-09-13T00:00:00+00:00",
    }
    original_bytes = json.dumps(remote_owner).encode()
    lock_path.write_bytes(original_bytes)

    def fail_if_checked(pid: int, signal: int) -> None:
        raise AssertionError(f"remote process must not be checked: {pid=}, {signal=}")

    monkeypatch.setattr(os, "kill", fail_if_checked)

    with (
        pytest.raises(YbsError, match="task lock unavailable") as exc_info,
        task_lock(tmp_path, "DEMO-101"),
    ):
        pass

    assert exc_info.value.code == 5
    assert lock_path.read_bytes() == original_bytes


def test_task_lock_never_recovers_malformed_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_bytes(b"not-json")

    with (
        pytest.raises(YbsError, match="task lock unavailable") as exc_info,
        task_lock(tmp_path, "DEMO-101"),
    ):
        pass

    assert exc_info.value.code == 5
    assert lock_path.read_bytes() == b"not-json"


def test_task_lock_never_recovers_invalid_timestamp_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    lock_path.parent.mkdir(parents=True)
    malformed_owner = {"pid": 12345, "host": socket.gethostname(), "created_at": "old"}
    original_bytes = json.dumps(malformed_owner).encode()
    lock_path.write_bytes(original_bytes)

    def report_dead_process(pid: int, signal: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(os, "kill", report_dead_process)

    with (
        pytest.raises(YbsError, match="task lock unavailable") as exc_info,
        task_lock(tmp_path, "DEMO-101"),
    ):
        pass

    assert exc_info.value.code == 5
    assert lock_path.read_bytes() == original_bytes


def test_task_lock_release_preserves_replaced_owner_record(tmp_path: Path) -> None:
    lock_path = tmp_path / ".ybs" / "locks" / "DEMO-101.lock"
    replacement = b'{"pid":999,"host":"replacement","created_at":"later"}'

    with task_lock(tmp_path, "DEMO-101"):
        lock_path.write_bytes(replacement)

    assert lock_path.read_bytes() == replacement
