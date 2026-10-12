import pytest
import tempfile
from pathlib import Path

from app.graph.networkx_store import NetworkXStore
from app.parser.models import (
    RepositoryGraph, FileNode, ModuleNode, ClassNode,
    FunctionNode, ExternalSymbolNode, Edge
)

def make_sample_graph(repo_id: str = "test_repo") -> RepositoryGraph:
    f1 = FileNode(
        id=f"{repo_id}:file:app/main.py",
        repo_id=repo_id,
        rel_path="app/main.py",
        module_name="app.main",
        line_count=50,
        file_hash="hash1"
    )
    m1 = ModuleNode(
        id=f"{repo_id}:module:app.main",
        repo_id=repo_id,
        name="app.main",
        rel_path="app/main.py"
    )
    c1 = ClassNode(
        id=f"{repo_id}:class:app/main.py:TournamentRunner",
        repo_id=repo_id,
        name="TournamentRunner",
        qualified_name="TournamentRunner",
        rel_path="app/main.py",
        start_line=10,
        end_line=40
    )
    fn1 = FunctionNode(
        id=f"{repo_id}:func:app/main.py:TournamentRunner.run_match",
        repo_id=repo_id,
        name="run_match",
        qualified_name="TournamentRunner.run_match",
        rel_path="app/main.py",
        start_line=15,
        end_line=25,
        is_method=True,
        parent_class="TournamentRunner"
    )
    fn2 = FunctionNode(
        id=f"{repo_id}:func:app/main.py:TournamentRunner.play_move",
        repo_id=repo_id,
        name="play_move",
        qualified_name="TournamentRunner.play_move",
        rel_path="app/main.py",
        start_line=26,
        end_line=35,
        is_method=True,
        parent_class="TournamentRunner"
    )
    ext1 = ExternalSymbolNode(
        id="ext:groq.APIError",
        name="groq.APIError",
        category="exception"
    )

    edges = [
        Edge(source_id=f1.id, target_id=m1.id, type="CONTAINS"),
        Edge(source_id=f1.id, target_id=c1.id, type="DEFINES"),
        Edge(source_id=c1.id, target_id=fn1.id, type="CONTAINS"),
        Edge(source_id=c1.id, target_id=fn2.id, type="CONTAINS"),
        Edge(
            source_id=fn1.id,
            target_id=fn2.id,
            type="CALLS",
            properties={"line": 20, "call_expr": "self.play_move()"}
        ),
        Edge(
            source_id=fn2.id,
            target_id=ext1.id,
            type="HANDLES",
            properties={"line": 30, "exception": "APIError"}
        )
    ]

    return RepositoryGraph(
        repo_id=repo_id,
        repo_name="Test Repo",
        repo_path="/test/repo",
        indexed_at="2026-10-09T00:00:00Z",
        files=[f1],
        modules=[m1],
        classes=[c1],
        functions=[fn1, fn2],
        external_symbols=[ext1],
        edges=edges
    )

def test_networkx_store_ingestion_and_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = NetworkXStore(storage_dir=Path(tmpdir))
        sample_g = make_sample_graph("repo_alpha")
        store.create_or_update_index(sample_g)

        stats = store.get_graph_statistics("repo_alpha")
        assert stats["total_nodes"] >= 5
        assert stats["total_edges"] >= 6
        assert stats["nodes_by_type"].get("Function") == 2
        assert stats["edges_by_type"].get("CALLS") == 1

def test_call_path_tracing():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = NetworkXStore(storage_dir=Path(tmpdir))
        sample_g = make_sample_graph("repo_alpha")
        store.create_or_update_index(sample_g)

        src = "repo_alpha:func:app/main.py:TournamentRunner.run_match"
        dst = "repo_alpha:func:app/main.py:TournamentRunner.play_move"
        paths = store.trace_call_path(src, dst)

        assert len(paths) == 1
        assert paths[0]["nodes"] == [src, dst]
        assert paths[0]["steps"][0]["call_expr"] == "self.play_move()"

def test_multi_hop_neighborhood():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = NetworkXStore(storage_dir=Path(tmpdir))
        sample_g = make_sample_graph("repo_alpha")
        store.create_or_update_index(sample_g)

        seed = "repo_alpha:func:app/main.py:TournamentRunner.run_match"
        neighborhood = store.retrieve_multi_hop_context(
            repo_id="repo_alpha",
            seed_symbol_ids=[seed],
            max_hops=2,
            max_nodes=20
        )
        node_ids = [n["id"] for n in neighborhood["nodes"]]
        assert seed in node_ids
        assert "repo_alpha:func:app/main.py:TournamentRunner.play_move" in node_ids
        assert "ext:groq.APIError" in node_ids

def test_symbol_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = NetworkXStore(storage_dir=Path(tmpdir))
        sample_g = make_sample_graph("repo_alpha")
        store.create_or_update_index(sample_g)

        results = store.search_symbols("repo_alpha", "TournamentRunner")
        assert len(results) >= 1
        assert any(r["name"] == "TournamentRunner" for r in results)
