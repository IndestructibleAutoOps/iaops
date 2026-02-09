from pathlib import Path

from indestructibleautoops.orchestration import (
    AgentOrchestrator,
    CIManager,
    FileSecurityScanner,
    GovernanceSystem,
    PipelineDAG,
    SecurityScanner,
)


def test_pipeline_dag_execution_order():
    dag = PipelineDAG(nodes=["a", "b", "c"], edges=[("a", "b"), ("b", "c")])
    assert dag.has_cycle() is False
    assert dag.topological_order() == ["a", "b", "c"]
    out = dag.execute(
        {"a": lambda _: "A", "b": lambda ctx: ctx["a"] + "B", "c": lambda ctx: ctx["b"] + "C"}
    )
    assert out["c"] == "ABC"


def test_pipeline_dag_detects_cycle():
    dag = PipelineDAG(nodes=["a", "b"], edges=[("a", "b"), ("b", "a")])
    assert dag.has_cycle() is True
    assert dag.topological_order() is None


def test_file_security_scanner_blocks_sensitive(tmp_path: Path):
    p = tmp_path / "creds.txt"
    p.write_text("aws_secret_access_key=abc", encoding="utf-8")
    scanner = FileSecurityScanner([])
    assert scanner.scan_file(p) is False

    ok_file = tmp_path / "ok.txt"
    ok_file.write_text("hello", encoding="utf-8")
    assert scanner.scan_file(ok_file) is True


def test_file_security_scanner_password_pattern(tmp_path: Path):
    """Verify the password regex matches 'password = ...' (whitespace, not literal backslash-s)."""
    p = tmp_path / "config.txt"
    p.write_text("password = hunter2", encoding="utf-8")
    scanner = FileSecurityScanner([])
    assert scanner.scan_file(p) is False


def test_file_security_scanner_structured_report(tmp_path: Path):
    p = tmp_path / "bad.txt"
    p.write_text("aws_access_key_id=AKIA...", encoding="utf-8")
    scanner = FileSecurityScanner([])
    report = scanner.scan(p)
    assert report["ok"] is False
    assert any("aws_access_key_id" in issue for issue in report["issues"])


def test_file_security_scanner_blocks_env_extension(tmp_path: Path):
    p = tmp_path / "secrets.env"
    p.write_text("clean content", encoding="utf-8")
    scanner = FileSecurityScanner([])
    report = scanner.scan(p)
    assert report["ok"] is False
    assert "skipped_disallowed_extension" in report["issues"]


def test_security_scanner_alias():
    """SecurityScanner is a backward-compatible alias for FileSecurityScanner."""
    assert SecurityScanner is FileSecurityScanner


def test_ci_manager_templates_and_updates(tmp_path: Path, monkeypatch):
    ci = CIManager(tmp_path)
    tpl = ci.apply_template("ci")
    assert tpl.exists()

    monkeypatch.setenv("ALLOW_UPDATES", "true")
    upd = ci.update_dependencies()
    assert upd is not None and upd.exists()


def test_agent_orchestrator_runs_dag(tmp_path: Path):
    dag = PipelineDAG(
        nodes=["pre_process", "process", "post_process"],
        edges=[("pre_process", "process"), ("process", "post_process")],
    )
    scanner = FileSecurityScanner([])
    governance = GovernanceSystem()
    orchestrator = AgentOrchestrator(dag, scanner, governance)

    calls: list[str] = []

    def pre(ctx):
        calls.append("pre")
        return "p"

    def proc(ctx):
        calls.append("process")
        return ctx["pre_process"] + "r"

    def post(ctx):
        calls.append("post")
        return ctx["process"] + "s"

    result = orchestrator.execute(
        agents={"pre_process": pre, "process": proc, "post_process": post},
        strategy="valid-strategy",
    )
    assert result["ok"] is True
    assert calls == ["pre", "process", "post"]
    assert result["results"]["post_process"] == "prs"


def test_agent_orchestrator_rejects_invalid_strategy(tmp_path: Path):
    dag = PipelineDAG(nodes=["a"], edges=[])
    scanner = FileSecurityScanner([])
    governance = GovernanceSystem()
    orchestrator = AgentOrchestrator(dag, scanner, governance)

    result = orchestrator.execute(agents={"a": lambda _: "ok"}, strategy="")
    assert result["ok"] is False
    assert result["error"] == "invalid_strategy"
