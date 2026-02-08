from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DAG:
    nodes: list[dict[str, Any]]

    @staticmethod
    def from_nodes(nodes: list[dict[str, Any]]) -> DAG:
        return DAG(nodes=nodes)

    def ids(self) -> list[str]:
        return [n["id"] for n in self.nodes]

    def deps(self, node_id: str) -> list[str]:
        for n in self.nodes:
            if n["id"] == node_id:
                return list(n.get("deps", []))
        return []


def dag_is_acyclic(dag: DAG) -> bool:
    ids = set(dag.ids())
    graph: dict[str, list[str]] = {i: [] for i in ids}
    indeg: dict[str, int] = {i: 0 for i in ids}
    for i in ids:
        deps = [d for d in dag.deps(i) if d in ids]
        for d in deps:
            graph[d].append(i)
            indeg[i] += 1
    q = [i for i in ids if indeg[i] == 0]
    seen = 0
    while q:
        cur = q.pop()
        seen += 1
        for nxt in graph[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)
    return seen == len(ids)
