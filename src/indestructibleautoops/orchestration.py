from __future__ import annotations

import os
import re
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class PipelineDAG:
    def __init__(self, nodes: list[str], edges: list[tuple[str, str]]):
        self.nodes = nodes
        self.edges = edges
        self._graph = self._build_graph()

    def _build_graph(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {n: [] for n in self.nodes}
        for src, dst in self.edges:
            if src not in graph:
                graph[src] = []
            if dst not in graph:
                graph[dst] = []
            graph[src].append(dst)
        return graph

    def has_cycle(self) -> bool:
        indeg: dict[str, int] = {n: 0 for n in self._graph}
        for src in self._graph:
            for dst in self._graph[src]:
                indeg[dst] = indeg.get(dst, 0) + 1
        q = deque([n for n, deg in indeg.items() if deg == 0])
        seen = 0
        while q:
            cur = q.popleft()
            seen += 1
            for nxt in self._graph.get(cur, []):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        return seen != len(indeg)

    def topological_order(self) -> list[str] | None:
        indeg: dict[str, int] = {n: 0 for n in self._graph}
        for _src, dsts in self._graph.items():
            for dst in dsts:
                indeg[dst] = indeg.get(dst, 0) + 1
        q = deque([n for n, deg in indeg.items() if deg == 0])
        order: list[str] = []
        while q:
            cur = q.popleft()
            order.append(cur)
            for nxt in self._graph.get(cur, []):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        if len(order) != len(indeg):
            return None
        return order

    def execute(self, steps: dict[str, Callable[[dict[str, Any]], Any]]) -> dict[str, Any]:
        order = self.topological_order()
        if order is None:
            raise ValueError("dag_cycle")
        ctx: dict[str, Any] = {}
        for step in order:
            if step not in steps:
                raise KeyError(f"missing step: {step}")
            ctx[step] = steps[step](ctx)
        return ctx


class SecurityScanner:
    def __init__(self, forbidden_patterns: Iterable[str] | None = None):
        pats = list(forbidden_patterns or [])
        pats.extend(
            [
                r"(?i)aws_access_key_id",
                r"(?i)aws_secret_access_key",
                r"(?i)-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----",
                r"(?i)password\\s*=",
            ]
        )
        self.patterns = [re.compile(p) for p in pats]

    def scan_file(self, path: Path) -> bool:
        if re.search(r"\.(env|secret)$", path.name):
            return False
        try:
            data = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False
        for pat in self.patterns:
            if pat.search(data):
                return False
        return True


class CIManager:
    def __init__(self, root: Path):
        self.root = root

    def apply_template(self, template_name: str) -> Path:
        ci_dir = self.root / ".indestructibleautoops" / "ci"
        ci_dir.mkdir(parents=True, exist_ok=True)
        p = ci_dir / f"{template_name}.yaml"
        contents = (
            "# Generated minimal CI template\n"
            "name: generated\n"
            "on: [push]\n"
            "jobs:\n"
            "  noop:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - run: echo 'noop'\n"
        )
        p.write_text(contents, encoding="utf-8")
        return p

    def update_dependencies(self) -> Path | None:
        if os.getenv("ALLOW_UPDATES") != "true":
            return None
        deps_dir = self.root / ".indestructibleautoops" / "deps"
        deps_dir.mkdir(parents=True, exist_ok=True)
        p = deps_dir / "updated.log"
        p.write_text(f"Dependencies updated at {datetime.now().isoformat()}\n", encoding="utf-8")
        return p


@dataclass
class GovernanceSystem:
    require_strategy: bool = True

    def request_approval(self, strategy: str) -> dict[str, Any]:
        approved = bool(strategy or not self.require_strategy)
        return {
            "status": "approved" if approved else "rejected",
            "strategy": strategy,
            "ts": datetime.now().isoformat(),
        }

    def continuous_monitoring(self) -> dict[str, Any]:
        return {"status": "ok", "ts": datetime.now().isoformat()}


class AgentOrchestrator:
    def __init__(
        self,
        dag: PipelineDAG,
        scanner: SecurityScanner,
        governance: GovernanceSystem,
        ci_manager: CIManager,
    ):
        self.dag = dag
        self.scanner = scanner
        self.governance = governance
        self.ci_manager = ci_manager

    def validate_strategy(self, strategy: str) -> bool:
        if not strategy:
            return False
        return re.match(r"^[a-zA-Z0-9 _-]+$", strategy) is not None

    def execute(
        self,
        agents: dict[str, Callable[[dict[str, Any]], Any]],
        files_to_scan: Iterable[Path] | None = None,
        strategy: str = "",
    ) -> dict[str, Any]:
        if not self.validate_strategy(strategy):
            return {"ok": False, "error": "invalid_strategy"}
        approval = self.governance.request_approval(strategy)
        if approval["status"] != "approved":
            return {"ok": False, "error": "approval_denied", "approval": approval}

        for f in files_to_scan or []:
            if not self.scanner.scan_file(f):
                return {"ok": False, "error": "security_blocked", "file": str(f)}

        order = self.dag.topological_order()
        if order is None:
            return {"ok": False, "error": "dag_cycle"}

        ctx: dict[str, Any] = {}
        for step in order:
            fn = agents.get(step)
            if not fn:
                return {"ok": False, "error": f"missing_agent:{step}"}
            ctx[step] = fn(ctx)

        monitoring = self.governance.continuous_monitoring()
        return {
            "ok": True,
            "order": order,
            "results": ctx,
            "approval": approval,
            "monitor": monitoring,
        }
