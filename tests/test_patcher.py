from indestructibleautoops.patcher import Patcher


def test_patcher_mkdir_creates_directory(tmp_path):
    plan = {"actions": [{"id": "add_src_dir", "kind": "mkdir", "path": "src"}]}
    patcher = Patcher(tmp_path, allow_writes=True)

    result = patcher.apply(plan)

    assert result["ok"] is True
    assert (tmp_path / "src").is_dir()
    assert any(a["action"]["id"] == "add_src_dir" for a in result["applied"])
