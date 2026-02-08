from indestructibleautoops.graph import DAG, dag_is_acyclic


def test_dag_acyclic_ok():
    dag = DAG.from_nodes(
        [
            {"id": "a", "kind": "step", "run": "x", "deps": []},
            {"id": "b", "kind": "step", "run": "x", "deps": ["a"]},
        ]
    )
    assert dag_is_acyclic(dag) is True


def test_dag_cycle_fail():
    dag = DAG.from_nodes(
        [
            {"id": "a", "kind": "step", "run": "x", "deps": ["b"]},
            {"id": "b", "kind": "step", "run": "x", "deps": ["a"]},
        ]
    )
    assert dag_is_acyclic(dag) is False


def test_dag_topological_sort():
    dag = DAG.from_nodes(
        [
            {"id": "a", "kind": "step", "run": "x", "deps": ["b"]},
            {"id": "b", "kind": "step", "run": "y", "deps": ["c"]},
            {"id": "c", "kind": "step", "run": "z", "deps": []},
        ]
    )
    assert dag.topological_sort() == ["c", "b", "a"]

    dag = DAG.from_nodes(
        [
            {"id": "a", "deps": ["c"]},
            {"id": "b", "deps": ["c"]},
            {"id": "c", "deps": []},
        ]
    )
    assert set(dag.topological_sort()) == {"c", "a", "b"}

    dag = DAG.from_nodes(
        [
            {"id": "a", "deps": ["b", "c"]},
            {"id": "b", "deps": ["d"]},
            {"id": "c", "deps": ["d", "e"]},
            {"id": "d", "deps": []},
            {"id": "e", "deps": []},
        ]
    )
    order = dag.topological_sort()
    assert order is not None
    pos = {node: order.index(node) for node in order}
    assert pos["d"] < pos["b"] < pos["a"]
    assert pos["d"] < pos["c"] < pos["a"]
    assert pos["e"] < pos["c"]
