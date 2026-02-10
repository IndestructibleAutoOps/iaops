from indestructibleautoops.engine import OrchestrationEngine
from indestructibleautoops.orchestration import FileSecurityScanner as SecurityScanner


def test_dag_linear_flow():
    engine = OrchestrationEngine()

    @engine.register_step("init")
    def init(ctx):
        ctx.set("data", "payload")
        return "Initialized"

    @engine.register_step("process", depends_on="init")
    def process(ctx):
        return f"Processed {ctx.get('data', '')}"

    @engine.register_step("finalize", depends_on="process")
    def finalize(ctx):
        return "Completed"

    results = engine.execute()

    assert results["init"].status == "success"
    assert "Processed payload" in results["process"].output
    assert results["finalize"].output == "Completed"


def test_security_scanner_detection():
    scanner = SecurityScanner()
    from pathlib import Path

    content = "API_KEY='SECRET-123'; SELECT * FROM users;"

    report = scanner.scan(Path("config.env"), content)

    assert report["ok"] is False
    assert len(report["issues"]) > 0
