import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.parser.incremental import GraphDiffEngine, GraphDiffResult
from app.parser.ast_parser import AstParser
from app.graph.networkx_store import NetworkXStore
from app.parser.models import (
    RepositoryGraph, FileNode, ModuleNode, ClassNode,
    FunctionNode, ExternalSymbolNode, Edge
)

def test_graph_diff_detection_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_root, tempfile.TemporaryDirectory() as tmp_cache:
        root_path = Path(tmp_root)
        cache_path = Path(tmp_cache)

        engine = GraphDiffEngine(repo_id="test_diff_repo", repo_root=root_path, cache_dir=cache_path)

        # 1. Create two initial Python files
        file_a = root_path / "module_a.py"
        file_a.write_text("def func_a():\n    return 1\n", encoding="utf-8")

        file_b = root_path / "module_b.py"
        file_b.write_text("class ClassB:\n    pass\n", encoding="utf-8")

        current_files = [file_a, file_b]

        # Initial diff should detect all files as added
        diff, hashes, _ = engine.compute_diff(current_files, force_full=True)
        assert len(diff.added_files) == 2
        assert len(diff.modified_files) == 0
        assert len(diff.deleted_files) == 0
        assert len(diff.unchanged_files) == 0
        assert diff.has_changes is True

        # Parse and save state
        parsed_a = AstParser.parse_file("test_diff_repo", root_path, file_a)
        parsed_b = AstParser.parse_file("test_diff_repo", root_path, file_b)
        engine.save_state([parsed_a, parsed_b], hashes)

        # 2. Second run without file changes -> All files should be detected as unchanged!
        engine_2 = GraphDiffEngine(repo_id="test_diff_repo", repo_root=root_path, cache_dir=cache_path)
        diff_2, hashes_2, _ = engine_2.compute_diff(current_files, force_full=False)

        assert diff_2.is_incremental is True
        assert diff_2.has_changes is False
        assert len(diff_2.added_files) == 0
        assert len(diff_2.modified_files) == 0
        assert len(diff_2.deleted_files) == 0
        assert len(diff_2.unchanged_files) == 2
        assert "module_a.py" in diff_2.unchanged_files
        assert "module_b.py" in diff_2.unchanged_files

        # Test cached AST retrieval without parsing
        cached_a = engine_2.load_cached_parsed_file("module_a.py")
        assert cached_a is not None
        assert cached_a.file_node.rel_path == "module_a.py"
        assert len(cached_a.functions) == 1
        assert cached_a.functions[0].name == "func_a"

        # 3. Modify module_a.py, Add module_c.py, Delete module_b.py
        file_a.write_text("def func_a_v2():\n    return 2\n", encoding="utf-8")
        file_b.unlink()
        file_c = root_path / "module_c.py"
        file_c.write_text("def func_c():\n    return 3\n", encoding="utf-8")

        current_files_3 = [file_a, file_c]
        diff_3, hashes_3, _ = engine_2.compute_diff(current_files_3, force_full=False)

        assert diff_3.is_incremental is True
        assert diff_3.has_changes is True
        assert diff_3.added_files == ["module_c.py"]
        assert diff_3.modified_files == ["module_a.py"]
        assert diff_3.deleted_files == ["module_b.py"]
        assert len(diff_3.unchanged_files) == 0

def test_networkx_apply_graph_diff():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = NetworkXStore(storage_dir=Path(tmp_dir))
        repo_id = "diff_nx_repo"

        # Initial graph with 2 files
        f1 = FileNode(id=f"{repo_id}:file:f1.py", repo_id=repo_id, rel_path="f1.py", module_name="f1", line_count=20, file_hash="h1")
        f2 = FileNode(id=f"{repo_id}:file:f2.py", repo_id=repo_id, rel_path="f2.py", module_name="f2", line_count=30, file_hash="h2")
        fn1 = FunctionNode(id=f"{repo_id}:func:f1.py:f1_func", repo_id=repo_id, name="f1_func", qualified_name="f1_func", rel_path="f1.py", start_line=1, end_line=10)
        fn2 = FunctionNode(id=f"{repo_id}:func:f2.py:f2_func", repo_id=repo_id, name="f2_func", qualified_name="f2_func", rel_path="f2.py", start_line=1, end_line=15)
        e1 = Edge(source_id=fn1.id, target_id=fn2.id, type="CALLS")

        initial_graph = RepositoryGraph(
            repo_id=repo_id,
            repo_name="Diff NX Repo",
            repo_path="/test",
            indexed_at="2026-10-12T00:00:00Z",
            files=[f1, f2],
            functions=[fn1, fn2],
            edges=[e1]
        )
        store.create_or_update_index(initial_graph)

        stats_before = store.get_graph_statistics(repo_id)
        assert stats_before["total_nodes"] >= 4 # repo, 2 files, 2 funcs

        # Apply Graph Diff:
        # f1.py was modified (new function f1_func_modified)
        # f2.py was unchanged
        # f3.py was added
        f1_mod = FileNode(id=f"{repo_id}:file:f1.py", repo_id=repo_id, rel_path="f1.py", module_name="f1", line_count=25, file_hash="h1_mod")
        f3 = FileNode(id=f"{repo_id}:file:f3.py", repo_id=repo_id, rel_path="f3.py", module_name="f3", line_count=15, file_hash="h3")
        fn1_mod = FunctionNode(id=f"{repo_id}:func:f1.py:f1_func_modified", repo_id=repo_id, name="f1_func_modified", qualified_name="f1_func_modified", rel_path="f1.py", start_line=1, end_line=12)
        fn3 = FunctionNode(id=f"{repo_id}:func:f3.py:f3_func", repo_id=repo_id, name="f3_func", qualified_name="f3_func", rel_path="f3.py", start_line=1, end_line=8)
        e2 = Edge(source_id=fn1_mod.id, target_id=fn2.id, type="CALLS")

        updated_graph = RepositoryGraph(
            repo_id=repo_id,
            repo_name="Diff NX Repo",
            repo_path="/test",
            indexed_at="2026-10-12T01:00:00Z",
            files=[f1_mod, f2, f3],
            functions=[fn1_mod, fn2, fn3],
            edges=[e2]
        )

        res = store.apply_graph_diff(
            repo_id=repo_id,
            graph=updated_graph,
            added_files=["f3.py"],
            modified_files=["f1.py"],
            deleted_files=[]
        )

        assert res["status"] == "incremental_applied"
        assert res["nodes_pruned"] >= 2 # old f1.py file node and old f1_func node
        assert not store.graph.has_node(fn1.id) # old fn1 removed
        assert store.graph.has_node(fn1_mod.id) # new fn1_mod added
        assert store.graph.has_node(fn2.id)     # unchanged fn2 preserved
        assert store.graph.has_node(fn3.id)     # new fn3 added
