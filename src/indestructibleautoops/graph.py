from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


class GraphError(Exception):
    """Raised when the DAG contains a cyclic dependency."""


def topological_sort(nodes: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """Return a topological ordering of the DAG or raise GraphError on cycles."""
    graph: dict[str, list[str]] = {node: [] for node in nodes}
    in_degree: dict[str, int] = {node: 0 for node in nodes}

    for parent, child in edges:
        graph[parent].append(child)
        in_degree[child] = in_degree.get(child, 0) + 1

    queue: deque[str] = deque([node for node in nodes if in_degree[node] == 0])
    sorted_nodes: list[str] = []

    while queue:
        node = queue.popleft()
        sorted_nodes.append(node)

        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_nodes) != len(nodes):
        raise GraphError("Cyclic dependency detected in DAG")

    return sorted_nodes


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

    def topological_sort(self) -> list[str] | None:
        ids = set(self.ids())
        graph: dict[str, list[str]] = {i: [] for i in ids}
        indeg: dict[str, int] = {i: 0 for i in ids}
        for i in ids:
            deps = [d for d in self.deps(i) if d in ids]
            for d in deps:
                graph[d].append(i)
                indeg[i] += 1
        q: list[str] = [i for i in ids if indeg[i] == 0]
        order: list[str] = []
        while q:
            cur = q.pop(0)
            order.append(cur)
            for nxt in graph[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        if len(order) != len(ids):
            return None
        return order


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
