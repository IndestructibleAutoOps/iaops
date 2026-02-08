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
