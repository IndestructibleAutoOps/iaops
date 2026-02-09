from indestructibleautoops.engine import OrchestrationEngine
from indestructibleautoops.security import SecurityScanner


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
    content = "API_KEY='SECRET-123'; SELECT * FROM users;"

    report = scanner.inspect("config.env", content)

    assert report["blocked_by_name"] is True
    assert report["sensitive_found"] is True
    assert "union\\s+select" in report["risks"][0]
    assert report["is_secure"] is False
