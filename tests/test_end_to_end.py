from pathlib import Path

from indestructibleautoops.engine import Engine


def test_end_to_end_plan(tmp_path: Path):
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    cfg = Path("configs/indestructibleautoops.pipeline.yaml").resolve()
    engine = Engine.from_config(cfg, tmp_path, mode="plan")
    out = engine.run()
    assert out["ok"] is True
