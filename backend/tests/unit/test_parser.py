import pytest
import tempfile
from pathlib import Path

from app.parser.scanner import RepositoryScanner
from app.parser.ast_parser import AstParser
from app.parser.symbol_resolver import SymbolResolver
from app.utils.identifiers import make_file_id, make_class_id, make_function_id
from app.utils.paths import resolve_safe_subpath, PathTraversalError

SAMPLE_CODE = """
import os
from math import sqrt as root
from typing import Optional

class BaseWorker:
    def __init__(self, name: str):
        self.name = name

class CalculationWorker(BaseWorker):
    def __init__(self, name: str, threshold: float = 10.0):
        super().__init__(name)
        self.threshold = threshold

    async def compute(self, val: float) -> Optional[float]:
        try:
            if val < 0:
                raise ValueError("Negative value not allowed")
            res = root(val)
            return self.process_result(res)
        except ValueError as err:
            self.handle_error(err)
            return None

    def process_result(self, val: float) -> float:
        return val * 2.0

    def handle_error(self, err: Exception):
        pass
"""

def test_ast_parser_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)
        test_file = root_path / "worker.py"
        test_file.write_text(SAMPLE_CODE, encoding="utf-8")

        parsed = AstParser.parse_file("test_repo", root_path, test_file)

        assert parsed.file_node.parse_status == "ok"
        assert parsed.file_node.line_count > 20
        assert len(parsed.classes) == 2
        
        class_names = [c.name for c in parsed.classes]
        assert "BaseWorker" in class_names
        assert "CalculationWorker" in class_names

        func_names = [f.name for f in parsed.functions]
        assert "compute" in func_names
        assert "process_result" in func_names
        assert "handle_error" in func_names

        compute_func = next(f for f in parsed.functions if f.name == "compute")
        assert compute_func.is_async is True
        assert compute_func.is_method is True
        assert compute_func.parent_class == "CalculationWorker"
        assert "ValueError" in compute_func.raises
        assert "ValueError" in compute_func.handles

def test_symbol_resolver():
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)
        test_file = root_path / "worker.py"
        test_file.write_text(SAMPLE_CODE, encoding="utf-8")

        parsed = AstParser.parse_file("test_repo", root_path, test_file)
        resolver = SymbolResolver("test_repo", "Test Repo", str(root_path), [parsed])
        graph = resolver.resolve_all()

        assert len(graph.files) == 1
        assert len(graph.classes) == 2
        
        # Check INHERITS edge
        inherits_edges = [e for e in graph.edges if e.type == "INHERITS"]
        assert len(inherits_edges) >= 1
        calc_class_id = make_class_id("test_repo", "worker.py", "CalculationWorker")
        base_class_id = make_class_id("test_repo", "worker.py", "BaseWorker")
        assert any(e.source_id == calc_class_id and e.target_id == base_class_id for e in inherits_edges)

        # Check CALLS edge (compute calls process_result and handle_error)
        call_edges = [e for e in graph.edges if e.type == "CALLS"]
        compute_func_id = make_function_id("test_repo", "worker.py", "CalculationWorker.compute")
        process_func_id = make_function_id("test_repo", "worker.py", "CalculationWorker.process_result")
        assert any(e.source_id == compute_func_id and e.target_id == process_func_id for e in call_edges)

def test_syntax_error_resilience():
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)
        bad_file = root_path / "broken.py"
        bad_file.write_text("def broken_syntax(:\n    pass", encoding="utf-8")

        parsed = AstParser.parse_file("test_repo", root_path, bad_file)
        assert parsed.file_node.parse_status == "syntax_error"
        assert "SyntaxError" in (parsed.file_node.parse_error or "")

def test_path_traversal_prevention():
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)
        with pytest.raises(PathTraversalError):
            resolve_safe_subpath(root_path, "../../etc/passwd")
        with pytest.raises(PathTraversalError):
            resolve_safe_subpath(root_path, "C:\\Windows\\System32\\cmd.exe")
