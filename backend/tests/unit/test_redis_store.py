import pytest
from app.graph.redis_store import RedisGraphCache, RedisNetworkXStore, redis_cache
from app.graph import set_active_backend, get_backend_status, get_graph_store
from app.parser.models import (
    RepositoryGraph, FileNode, ModuleNode, ClassNode,
    FunctionNode, ExternalSymbolNode, Edge
)

def make_sample_graph(repo_id: str = "redis_test_repo") -> RepositoryGraph:
    f1 = FileNode(
        id=f"{repo_id}:file:core/engine.py",
        repo_id=repo_id,
        rel_path="core/engine.py",
        module_name="core.engine",
        line_count=60,
        file_hash="hash_engine_123"
    )
    m1 = ModuleNode(
        id=f"{repo_id}:module:core.engine",
        repo_id=repo_id,
        name="core.engine",
        rel_path="core/engine.py"
    )
    c1 = ClassNode(
        id=f"{repo_id}:class:core/engine.py:ChessEngine",
        repo_id=repo_id,
        name="ChessEngine",
        qualified_name="ChessEngine",
        rel_path="core/engine.py",
        start_line=5,
        end_line=45
    )
    fn1 = FunctionNode(
        id=f"{repo_id}:func:core/engine.py:ChessEngine.calculate_best_move",
        repo_id=repo_id,
        name="calculate_best_move",
        qualified_name="ChessEngine.calculate_best_move",
        rel_path="core/engine.py",
        start_line=10,
        end_line=25,
        is_method=True,
        parent_class="ChessEngine"
    )
    fn2 = FunctionNode(
        id=f"{repo_id}:func:core/engine.py:ChessEngine.evaluate_board",
        repo_id=repo_id,
        name="evaluate_board",
        qualified_name="ChessEngine.evaluate_board",
        rel_path="core/engine.py",
        start_line=26,
        end_line=40,
        is_method=True,
        parent_class="ChessEngine"
    )
    ext1 = ExternalSymbolNode(
        id="ext:redis.Redis",
        name="redis.Redis",
        category="library"
    )

    edges = [
        Edge(source_id=f1.id, target_id=m1.id, type="CONTAINS"),
        Edge(source_id=m1.id, target_id=c1.id, type="DEFINES"),
        Edge(source_id=c1.id, target_id=fn1.id, type="DEFINES"),
        Edge(source_id=c1.id, target_id=fn2.id, type="DEFINES"),
        Edge(source_id=fn1.id, target_id=fn2.id, type="CALLS", properties={"line": 20}),
        Edge(source_id=fn1.id, target_id=ext1.id, type="REFERENCES", properties={"line": 15})
    ]

    return RepositoryGraph(
        repo_id=repo_id,
        repo_name="Redis Test Repo",
        repo_path="E:/test/redis_repo",
        indexed_at="2026-10-12T12:00:00Z",
        files=[f1],
        modules=[m1],
        classes=[c1],
        functions=[fn1, fn2],
        external_symbols=[ext1],
        edges=edges
    )

def test_redis_cache_operations():
    cache = RedisGraphCache()
    if not cache.is_connected():
        pytest.skip("Redis service not available for cache test")

    test_key = "subgraph:test_unit_key"
    test_data = {"nodes": [{"id": "n1"}], "edges": [{"source": "n1", "target": "n2"}]}

    cache.set(test_key, test_data, ttl_seconds=60)
    cached = cache.get(test_key)
    assert cached == test_data

    stats = cache.get_stats()
    assert stats["connected"] is True
    assert stats["backend"] == "redis"

    cache.clear_pattern("mg:cache:subgraph:test_unit_*")
    assert cache.get(test_key) is None

def test_redis_networkx_store_ingestion_and_traversal():
    store = RedisNetworkXStore()
    if not store.is_connected():
        pytest.skip("Redis service not available for RedisNetworkXStore test")

    sample_graph = make_sample_graph("redis_test_repo")
    store.create_or_update_index(sample_graph)

    stats = store.get_graph_statistics("redis_test_repo")
    assert stats["total_nodes"] >= 5
    assert stats["total_edges"] >= 5

    # Test Symbol Search
    results = store.search_symbols("redis_test_repo", "calculate_best_move")
    assert len(results) >= 1
    assert results[0]["name"] == "calculate_best_move"

    # Test Callers & Callees
    callees = store.get_callees(f"redis_test_repo:func:core/engine.py:ChessEngine.calculate_best_move")
    assert len(callees) >= 1
    assert any(c["id"] == "redis_test_repo:func:core/engine.py:ChessEngine.evaluate_board" for c in callees)

    callers = store.get_callers(f"redis_test_repo:func:core/engine.py:ChessEngine.evaluate_board")
    assert len(callers) >= 1
    assert any(c["id"] == "redis_test_repo:func:core/engine.py:ChessEngine.calculate_best_move" for c in callers)

    # Test Multi-hop Context
    context = store.retrieve_multi_hop_context(
        "redis_test_repo",
        [f"redis_test_repo:func:core/engine.py:ChessEngine.calculate_best_move"],
        max_hops=2
    )
    assert len(context["nodes"]) >= 2
    assert len(context["edges"]) >= 1

def test_multi_backend_runtime_switching():
    # Test switching to redis
    status_redis = set_active_backend("redis")
    assert status_redis["selection_mode"] == "redis"
    store_redis = get_graph_store()
    assert store_redis is not None

    # Test switching to networkx
    status_nx = set_active_backend("networkx")
    assert status_nx["selection_mode"] == "networkx"
    assert status_nx["active_engine"] == "NetworkXStore"

    # Test switching to auto
    status_auto = set_active_backend("auto")
    assert status_auto["selection_mode"] == "auto"

    # Verify invalid mode raises error
    with pytest.raises(ValueError):
        set_active_backend("invalid_mode_xyz")
