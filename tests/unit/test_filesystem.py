import json
import os
import socket
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
