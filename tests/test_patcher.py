from indestructibleautoops.patcher import Patcher


def test_patcher_mkdir_creates_directory(tmp_path):
    plan = {"actions": [{"id": "add_src_dir", "kind": "mkdir", "path": "src"}]}
    patcher = Patcher(tmp_path, allow_writes=True)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert (tmp_path / "src").is_dir()
    assert any(a["action"]["id"] == "add_src_dir" for a in result["applied"])


def test_patcher_mkdir_skips_when_writes_disabled(tmp_path):
    plan = {"actions": [{"id": "add_src_dir", "kind": "mkdir", "path": "src"}]}
    patcher = Patcher(tmp_path, allow_writes=False)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert not (tmp_path / "src").exists()
    assert len(result["applied"]) == 0
    assert any(s["reason"] == "writes_disabled" for s in result["skipped"])


def test_patcher_mkdir_skips_when_exists(tmp_path):
    (tmp_path / "src").mkdir()
    plan = {"actions": [{"id": "add_src_dir", "kind": "mkdir", "path": "src"}]}
    patcher = Patcher(tmp_path, allow_writes=True)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert len(result["applied"]) == 0
    assert any(s["reason"] == "exists" for s in result["skipped"])


def test_patcher_blocks_path_traversal(tmp_path):
    plan = {"actions": [{"id": "escape", "kind": "mkdir", "path": "../../etc/evil"}]}
    patcher = Patcher(tmp_path, allow_writes=True)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert len(result["applied"]) == 0
    assert any(s["reason"] == "path_traversal_blocked" for s in result["skipped"])


def test_patcher_blocks_absolute_path(tmp_path):
    plan = {"actions": [{"id": "abs", "kind": "write_file_if_missing", "path": "/tmp/evil.txt"}]}
    patcher = Patcher(tmp_path, allow_writes=True)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert len(result["applied"]) == 0
    assert any(s["reason"] == "path_traversal_blocked" for s in result["skipped"])


def test_patcher_write_file_skips_when_writes_disabled(tmp_path):
    plan = {"actions": [{"id": "f", "kind": "write_file_if_missing", "path": "foo.py"}]}
    patcher = Patcher(tmp_path, allow_writes=False)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert not (tmp_path / "foo.py").exists()
    assert any(s["reason"] == "writes_disabled" for s in result["skipped"])


def test_patcher_write_file_skips_when_exists(tmp_path):
    (tmp_path / "foo.py").write_text("existing", encoding="utf-8")
    plan = {"actions": [{"id": "f", "kind": "write_file_if_missing", "path": "foo.py"}]}
    patcher = Patcher(tmp_path, allow_writes=True)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert len(result["applied"]) == 0
    assert any(s["reason"] == "exists" for s in result["skipped"])
    # Content should not be overwritten
    assert (tmp_path / "foo.py").read_text() == "existing"
