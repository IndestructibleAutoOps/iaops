from pathlib import Path

from indestructibleautoops.orchestration import (
    AgentOrchestrator,
    CIManager,
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


def test_security_scanner_blocks_sensitive(tmp_path: Path):
    p = tmp_path / "creds.txt"
    p.write_text("aws_secret_access_key=abc", encoding="utf-8")
    scanner = SecurityScanner([])
    assert scanner.scan_file(p) is False

    ok_file = tmp_path / "ok.txt"
    ok_file.write_text("hello", encoding="utf-8")
    assert scanner.scan_file(ok_file) is True


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
    scanner = SecurityScanner([])
    governance = GovernanceSystem()
    ci_manager = CIManager(tmp_path)
    orchestrator = AgentOrchestrator(dag, scanner, governance, ci_manager)

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
