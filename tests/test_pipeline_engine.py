import pytest

from indestructibleautoops.engine import ExecutionContext, PipelineEngine
from indestructibleautoops.security import SecurityScanner


@pytest.fixture
def pipeline():
    engine = PipelineEngine()

    @engine.register_step(step_id="load_data")
    def load_data(ctx: ExecutionContext):
        ctx.set("dataset", [1, 2, 3, 4])
        return "Data loaded"

    @engine.register_step(step_id="analyze", depends_on="load_data")
    def analyze_data(ctx: ExecutionContext):
        data = ctx.get("dataset", [])
        return f"Analyzed {len(data)} records"

    @engine.register_step(step_id="secure_export", depends_on=["load_data", "analyze"])
    def export_data(ctx: ExecutionContext):
        scanner = SecurityScanner()
        return scanner.scan_file("export.json", '{"key": "value"}')

    return engine


def test_topological_sorting(pipeline):
    plan = pipeline.build_execution_plan()
    assert plan == ["load_data", "analyze", "secure_export"]


def test_full_execution(pipeline):
    report = pipeline.run_pipeline()
    assert report["load_data"]["status"] == "success"
    assert report["secure_export"]["status"] == "success"
    assert "is_safe" in report["secure_export"]["output"]
