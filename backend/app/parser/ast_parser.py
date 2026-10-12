import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

from app.parser.models import (
    FileNode, ModuleNode, ClassNode, FunctionNode,
    ExternalSymbolNode, Edge, ImportRecord, RawCallRecord, ParsedFile
)
from app.utils.identifiers import (
    make_file_id, make_module_id, make_class_id, make_function_id,
    make_external_symbol_id, compute_file_hash
)
from app.utils.paths import normalize_posix_relpath
from app.core.logging import logger

def _get_name_from_node(node: ast.AST) -> str:
    """Extracts identifier name string from various AST node types."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        parent = _get_name_from_node(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    elif isinstance(node, ast.Constant):
        return str(node.value)
    elif isinstance(node, ast.Call):
        return _get_name_from_node(node.func)
    return ""

def _infer_module_name(rel_path: str) -> str:
    """Infers module dot-path from a relative file path (e.g. backend/app/main.py -> backend.app.main)."""
    p = Path(rel_path)
    parts = list(p.parts)
    if not parts:
        return ""
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)

class AstFileVisitor(ast.NodeVisitor):
    def __init__(self, repo_id: str, rel_path: str, source_text: str):
        self.repo_id = repo_id
        self.rel_path = rel_path
        self.source_text = source_text
        self.lines = source_text.splitlines()
        
        self.classes: List[ClassNode] = []
        self.functions: List[FunctionNode] = []
        self.external_symbols: Dict[str, ExternalSymbolNode] = {}
        self.edges: List[Edge] = []
        self.imports: List[ImportRecord] = []
        self.raw_calls: List[RawCallRecord] = []
        
        # Scoping state
        self.scope_stack: List[str] = [] # e.g. ["GroqChessAgent"]
        self.current_class: Optional[str] = None
        self.current_func_node: Optional[FunctionNode] = None
        self.try_depth: int = 0
        self.except_depth: int = 0

    def _current_qualified_name(self, name: str) -> str:
        if self.scope_stack:
            return ".".join(self.scope_stack) + f".{name}"
        return name

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportRecord(
                rel_path=self.rel_path,
                line=node.lineno,
                module=alias.name,
                imported_name=None,
                alias=alias.asname,
                is_relative=False,
                level=0
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod_name = node.module or ""
        level = node.level
        for alias in node.names:
            self.imports.append(ImportRecord(
                rel_path=self.rel_path,
                line=node.lineno,
                module=mod_name,
                imported_name=alias.name,
                alias=alias.asname,
                is_relative=(level > 0),
                level=level
            ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        qname = self._current_qualified_name(node.name)
        cid = make_class_id(self.repo_id, self.rel_path, qname)

        bases: List[str] = []
        for b in node.bases:
            bname = _get_name_from_node(b)
            if bname:
                bases.append(bname)

        decorators: List[str] = []
        for d in node.decorator_list:
            dname = _get_name_from_node(d)
            if dname:
                decorators.append(dname)

        docstring = ast.get_docstring(node)
        is_abstract = any("ABC" in b or "abstract" in b.lower() for b in bases)

        cls_obj = ClassNode(
            id=cid,
            repo_id=self.repo_id,
            name=node.name,
            qualified_name=qname,
            rel_path=self.rel_path,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            docstring=docstring,
            bases=bases,
            decorators=decorators,
            is_abstract=is_abstract
        )
        self.classes.append(cls_obj)

        # File DEFINES Class edge
        file_id = make_file_id(self.repo_id, self.rel_path)
        self.edges.append(Edge(
            source_id=file_id,
            target_id=cid,
            type="DEFINES",
            properties={"line": node.lineno}
        ))

        # Enter class scope
        prev_class = self.current_class
        self.current_class = qname
        self.scope_stack.append(node.name)

        self.generic_visit(node)

        self.scope_stack.pop()
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool):
        qname = self._current_qualified_name(node.name)
        fid = make_function_id(self.repo_id, self.rel_path, qname, node.lineno)

        params: List[str] = []
        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            params.append(arg.arg)
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        decorators: List[str] = []
        for d in node.decorator_list:
            dname = _get_name_from_node(d)
            if dname:
                decorators.append(dname)

        ret_annotation: Optional[str] = None
        if node.returns:
            ret_annotation = _get_name_from_node(node.returns) or None

        docstring = ast.get_docstring(node)
        is_method = self.current_class is not None

        func_obj = FunctionNode(
            id=fid,
            repo_id=self.repo_id,
            name=node.name,
            qualified_name=qname,
            rel_path=self.rel_path,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            docstring=docstring,
            is_async=is_async,
            is_method=is_method,
            parent_class=self.current_class,
            parameters=params,
            return_annotation=ret_annotation,
            decorators=decorators,
            raises=[],
            handles=[]
        )
        self.functions.append(func_obj)

        file_id = make_file_id(self.repo_id, self.rel_path)
        if is_method and self.current_class:
            class_id = make_class_id(self.repo_id, self.rel_path, self.current_class)
            self.edges.append(Edge(
                source_id=class_id,
                target_id=fid,
                type="CONTAINS",
                properties={"line": node.lineno}
            ))
        else:
            self.edges.append(Edge(
                source_id=file_id,
                target_id=fid,
                type="DEFINES",
                properties={"line": node.lineno}
            ))

        # Enter function scope
        prev_func = self.current_func_node
        self.current_func_node = func_obj
        self.scope_stack.append(node.name)

        self.generic_visit(node)

        self.scope_stack.pop()
        self.current_func_node = prev_func

    def visit_Call(self, node: ast.Call):
        if self.current_func_node:
            func_name = _get_name_from_node(node.func)
            receiver: Optional[str] = None
            method_or_func = func_name

            if isinstance(node.func, ast.Attribute):
                receiver = _get_name_from_node(node.func.value)
                method_or_func = node.func.attr
            elif "." in func_name:
                parts = func_name.rsplit(".", 1)
                receiver = parts[0]
                method_or_func = parts[1]

            call_rec = RawCallRecord(
                caller_id=self.current_func_node.id,
                caller_qualified_name=self.current_func_node.qualified_name,
                rel_path=self.rel_path,
                line=node.lineno,
                call_expr=func_name or "<call>",
                receiver=receiver,
                method_or_func=method_or_func,
                is_in_try_block=(self.try_depth > 0),
                is_in_except_block=(self.except_depth > 0)
            )
            self.raw_calls.append(call_rec)

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        self.try_depth += 1
        for stmt in node.body:
            self.visit(stmt)
        self.try_depth -= 1

        self.except_depth += 1
        for handler in node.handlers:
            exc_name = _get_name_from_node(handler.type) if handler.type else "Exception"
            if self.current_func_node:
                self.current_func_node.handles.append(exc_name)
                ext_id = make_external_symbol_id(exc_name)
                if ext_id not in self.external_symbols:
                    self.external_symbols[ext_id] = ExternalSymbolNode(
                        id=ext_id,
                        name=exc_name,
                        category="exception",
                        repo_id=self.repo_id
                    )
                # HANDLES edge
                self.edges.append(Edge(
                    source_id=self.current_func_node.id,
                    target_id=ext_id,
                    type="HANDLES",
                    properties={"line": handler.lineno, "exception": exc_name}
                ))

            for stmt in handler.body:
                self.visit(stmt)
        self.except_depth -= 1

        for stmt in node.orelse:
            self.visit(stmt)
        for stmt in node.finalbody:
            self.visit(stmt)

    def visit_Raise(self, node: ast.Raise):
        if node.exc:
            exc_name = _get_name_from_node(node.exc)
            if self.current_func_node and exc_name:
                self.current_func_node.raises.append(exc_name)
                ext_id = make_external_symbol_id(exc_name)
                if ext_id not in self.external_symbols:
                    self.external_symbols[ext_id] = ExternalSymbolNode(
                        id=ext_id,
                        name=exc_name,
                        category="exception",
                        repo_id=self.repo_id
                    )
                # RAISES edge
                self.edges.append(Edge(
                    source_id=self.current_func_node.id,
                    target_id=ext_id,
                    type="RAISES",
                    properties={"line": node.lineno, "exception": exc_name}
                ))
        self.generic_visit(node)


class AstParser:
    @staticmethod
    def parse_file(repo_id: str, repo_root: Path, file_path: Path) -> ParsedFile:
        """
        Parses a single Python file using AST and returns rich structure with nodes and edges.
        """
        rel_posix = normalize_posix_relpath(repo_root, file_path)
        file_id = make_file_id(repo_id, rel_posix)
        module_name = _infer_module_name(rel_posix)
        module_id = make_module_id(repo_id, module_name)

        try:
            content_bytes = file_path.read_bytes()
            source_text = content_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to read file {rel_posix}: {e}")
            fn = FileNode(
                id=file_id,
                repo_id=repo_id,
                rel_path=rel_posix,
                module_name=module_name,
                line_count=0,
                file_hash="",
                parse_status="unsupported",
                parse_error=str(e)
            )
            return ParsedFile(file_node=fn)

        line_count = len(source_text.splitlines())
        fhash = compute_file_hash(content_bytes)

        try:
            tree = ast.parse(source_text, filename=rel_posix)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {rel_posix} (line {e.lineno}): {e.msg}")
            fn = FileNode(
                id=file_id,
                repo_id=repo_id,
                rel_path=rel_posix,
                module_name=module_name,
                line_count=line_count,
                file_hash=fhash,
                parse_status="syntax_error",
                parse_error=f"SyntaxError at line {e.lineno}: {e.msg}"
            )
            return ParsedFile(file_node=fn)

        file_docstring = ast.get_docstring(tree)
        file_node = FileNode(
            id=file_id,
            repo_id=repo_id,
            rel_path=rel_posix,
            module_name=module_name,
            line_count=line_count,
            file_hash=fhash,
            docstring=file_docstring,
            parse_status="ok"
        )

        module_node = ModuleNode(
            id=module_id,
            repo_id=repo_id,
            name=module_name,
            rel_path=rel_posix
        )

        visitor = AstFileVisitor(repo_id, rel_posix, source_text)
        visitor.visit(tree)

        # File CONTAINS Module edge
        visitor.edges.append(Edge(
            source_id=file_id,
            target_id=module_id,
            type="CONTAINS",
            properties={"module": module_name}
        ))

        return ParsedFile(
            file_node=file_node,
            module_node=module_node,
            classes=visitor.classes,
            functions=visitor.functions,
            external_symbols=list(visitor.external_symbols.values()),
            edges=visitor.edges,
            imports=visitor.imports,
            raw_calls=visitor.raw_calls
        )
