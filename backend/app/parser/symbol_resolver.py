from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

from app.parser.models import (
    ParsedFile, RepositoryGraph, Edge, ExternalSymbolNode,
    ClassNode, FunctionNode, FileNode, ModuleNode, ImportRecord, RawCallRecord
)
from app.utils.identifiers import (
    make_external_symbol_id, make_class_id, make_function_id
)
from app.core.logging import logger

class SymbolResolver:
    """
    Second-stage static analysis engine:
    Resolves cross-file imports, class inheritance hierarchies,
    and function/method call targets into verified graph edges.
    """
    def __init__(self, repo_id: str, repo_name: str, repo_path: str, parsed_files: List[ParsedFile]):
        self.repo_id = repo_id
        self.repo_name = repo_name
        self.repo_path = repo_path
        self.parsed_files = parsed_files

        # Global lookup indexes
        self.files_by_rel_path: Dict[str, FileNode] = {}
        self.modules_by_name: Dict[str, ModuleNode] = {}
        self.classes_by_id: Dict[str, ClassNode] = {}
        self.functions_by_id: Dict[str, FunctionNode] = {}
        self.external_symbols: Dict[str, ExternalSymbolNode] = {}

        # Name -> Node lists for resolution
        self.classes_by_simple_name: Dict[str, List[ClassNode]] = {}
        self.classes_by_qname: Dict[str, List[ClassNode]] = {}
        self.functions_by_simple_name: Dict[str, List[FunctionNode]] = {}
        self.functions_by_qname: Dict[str, List[FunctionNode]] = {}

        # Per-file symbol table: rel_path -> imported name -> target object/qname
        self.file_import_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

        self._build_indexes()

    def _build_indexes(self):
        for pf in self.parsed_files:
            self.files_by_rel_path[pf.file_node.rel_path] = pf.file_node
            if pf.module_node:
                self.modules_by_name[pf.module_node.name] = pf.module_node

            for ext in pf.external_symbols:
                self.external_symbols[ext.id] = ext

            for cls_node in pf.classes:
                self.classes_by_id[cls_node.id] = cls_node
                self.classes_by_simple_name.setdefault(cls_node.name, []).append(cls_node)
                self.classes_by_qname.setdefault(cls_node.qualified_name, []).append(cls_node)

            for fn_node in pf.functions:
                self.functions_by_id[fn_node.id] = fn_node
                self.functions_by_simple_name.setdefault(fn_node.name, []).append(fn_node)
                self.functions_by_qname.setdefault(fn_node.qualified_name, []).append(fn_node)

        # Build import maps for each file
        for pf in self.parsed_files:
            rel = pf.file_node.rel_path
            self.file_import_map[rel] = {}

            for imp in pf.imports:
                # E.g. from app.chess.validator import validate_move
                if imp.imported_name:
                    local_key = imp.alias or imp.imported_name
                    self.file_import_map[rel][local_key] = {
                        "module": imp.module,
                        "imported_name": imp.imported_name,
                        "is_relative": imp.is_relative,
                        "level": imp.level
                    }
                else:
                    # E.g. import chess
                    local_key = imp.alias or imp.module.split(".")[-1]
                    self.file_import_map[rel][local_key] = {
                        "module": imp.module,
                        "imported_name": None,
                        "is_relative": imp.is_relative,
                        "level": imp.level
                    }

    def _get_or_create_external(self, name: str, category: str = "library") -> ExternalSymbolNode:
        clean = name.strip()
        eid = make_external_symbol_id(clean)
        if eid not in self.external_symbols:
            self.external_symbols[eid] = ExternalSymbolNode(id=eid, name=clean, category=category, repo_id=self.repo_id)
        return self.external_symbols[eid]

    def resolve_inheritance(self) -> List[Edge]:
        """Resolves base class names to target ClassNodes or ExternalSymbols."""
        edges: List[Edge] = []
        for cls_node in self.classes_by_id.values():
            for base in cls_node.bases:
                base_simple = base.split(".")[-1]
                target_cls: Optional[ClassNode] = None

                # 1. Check in same file
                for c in self.classes_by_simple_name.get(base_simple, []):
                    if c.rel_path == cls_node.rel_path:
                        target_cls = c
                        break

                # 2. Check if imported in this file
                if not target_cls:
                    imp_info = self.file_import_map.get(cls_node.rel_path, {}).get(base_simple)
                    if imp_info:
                        imported_name = imp_info.get("imported_name") or base_simple
                        candidates = self.classes_by_simple_name.get(imported_name, [])
                        if candidates:
                            target_cls = candidates[0]

                # 3. Global match if unambiguous
                if not target_cls and base_simple in self.classes_by_simple_name:
                    candidates = self.classes_by_simple_name[base_simple]
                    if len(candidates) == 1:
                        target_cls = candidates[0]

                if target_cls:
                    edges.append(Edge(
                        source_id=cls_node.id,
                        target_id=target_cls.id,
                        type="INHERITS",
                        properties={"base_name": base, "is_resolved": True}
                    ))
                else:
                    ext_node = self._get_or_create_external(base, category="class")
                    edges.append(Edge(
                        source_id=cls_node.id,
                        target_id=ext_node.id,
                        type="INHERITS",
                        properties={"base_name": base, "is_resolved": False}
                    ))
        return edges

    def resolve_imports(self) -> List[Edge]:
        """Creates IMPORTS edges between File/Module and target modules or symbols."""
        edges: List[Edge] = []
        for pf in self.parsed_files:
            file_id = pf.file_node.id
            for imp in pf.imports:
                mod_name = imp.module
                # Check if matches an internal module
                matched_mod = None
                for m_name, m_node in self.modules_by_name.items():
                    if m_name == mod_name or m_name.endswith(f".{mod_name}"):
                        matched_mod = m_node
                        break

                if matched_mod:
                    edges.append(Edge(
                        source_id=file_id,
                        target_id=matched_mod.id,
                        type="IMPORTS",
                        properties={"line": imp.line, "imported_name": imp.imported_name, "alias": imp.alias}
                    ))
                else:
                    ext_name = f"{mod_name}.{imp.imported_name}" if imp.imported_name else mod_name
                    ext_node = self._get_or_create_external(ext_name, category="library")
                    edges.append(Edge(
                        source_id=file_id,
                        target_id=ext_node.id,
                        type="IMPORTS",
                        properties={"line": imp.line, "alias": imp.alias}
                    ))
        return edges

    def resolve_calls(self) -> List[Edge]:
        """Resolves RawCallRecords to target FunctionNodes or ExternalSymbols."""
        edges: List[Edge] = []

        for pf in self.parsed_files:
            rel_path = pf.file_node.rel_path
            imports = self.file_import_map.get(rel_path, {})

            for call in pf.raw_calls:
                caller = self.functions_by_id.get(call.caller_id)
                if not caller:
                    continue

                target_func: Optional[FunctionNode] = None
                method_name = call.method_or_func

                # Case A: Instance call on self (e.g. self._select_emergency_move)
                if call.receiver in ("self", "cls") and caller.parent_class:
                    target_qname = f"{caller.parent_class}.{method_name}"
                    candidates = self.functions_by_qname.get(target_qname, [])
                    for c in candidates:
                        if c.rel_path == rel_path:
                            target_func = c
                            break

                # Case B: Local function in same file
                if not target_func and not call.receiver:
                    for f in self.functions_by_simple_name.get(method_name, []):
                        if f.rel_path == rel_path and not f.is_method:
                            target_func = f
                            break

                # Case C: Imported function or class method
                if not target_func:
                    lookup_name = call.receiver or method_name
                    imp_entry = imports.get(lookup_name)
                    if imp_entry:
                        imp_target = imp_entry.get("imported_name") or lookup_name
                        # If receiver was imported, e.g. game_service.start_game
                        if call.receiver:
                            # Search for method in functions
                            candidates = self.functions_by_simple_name.get(method_name, [])
                            if candidates:
                                target_func = candidates[0]
                        else:
                            # Direct function imported, e.g. validate_move
                            candidates = self.functions_by_simple_name.get(imp_target, [])
                            if candidates:
                                target_func = candidates[0]

                # Case D: Unambiguous global match by simple name
                if not target_func and not call.receiver:
                    candidates = self.functions_by_simple_name.get(method_name, [])
                    if len(candidates) == 1:
                        target_func = candidates[0]

                # Case E: Domain receiver match (e.g. agent.select_move -> GroqChessAgent.select_move)
                if not target_func and call.receiver:
                    candidates = self.functions_by_simple_name.get(method_name, [])
                    if candidates:
                        rec_lower = call.receiver.lower()
                        matched = None
                        for cand in candidates:
                            parent_lower = (cand.parent_class or "").lower()
                            if rec_lower in parent_lower or (rec_lower == "agent" and "chessagent" in parent_lower):
                                matched = cand
                                break
                        target_func = matched or candidates[0]

                if target_func:
                    edges.append(Edge(
                        source_id=caller.id,
                        target_id=target_func.id,
                        type="CALLS",
                        properties={
                            "line": call.line,
                            "call_expr": call.call_expr,
                            "is_in_try": call.is_in_try_block,
                            "is_in_except": call.is_in_except_block,
                            "is_resolved": True,
                            "confidence": 1.0
                        }
                    ))
                else:
                    # External API or library call (e.g. client.chat.completions.create, asyncio.sleep)
                    target_name = f"{call.receiver}.{method_name}" if call.receiver else method_name
                    ext_node = self._get_or_create_external(target_name, category="call")
                    edges.append(Edge(
                        source_id=caller.id,
                        target_id=ext_node.id,
                        type="CALLS",
                        properties={
                            "line": call.line,
                            "call_expr": call.call_expr,
                            "is_in_try": call.is_in_try_block,
                            "is_in_except": call.is_in_except_block,
                            "is_resolved": False,
                            "confidence": 0.7
                        }
                    ))

        return edges

    def resolve_all(self, commit_hash: Optional[str] = None, warnings: Optional[List[str]] = None) -> RepositoryGraph:
        """Runs full multi-stage symbol resolution and compiles the complete RepositoryGraph."""
        all_files: List[FileNode] = []
        all_modules: List[ModuleNode] = []
        all_classes: List[ClassNode] = []
        all_functions: List[FunctionNode] = []
        all_edges: List[Edge] = []

        for pf in self.parsed_files:
            all_files.append(pf.file_node)
            if pf.module_node:
                all_modules.append(pf.module_node)
            all_classes.extend(pf.classes)
            all_functions.extend(pf.functions)
            all_edges.extend(pf.edges)

        # Cross-file resolution edges
        inheritance_edges = self.resolve_inheritance()
        import_edges = self.resolve_imports()
        call_edges = self.resolve_calls()

        all_edges.extend(inheritance_edges)
        all_edges.extend(import_edges)
        all_edges.extend(call_edges)

        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()

        return RepositoryGraph(
            repo_id=self.repo_id,
            repo_name=self.repo_name,
            repo_path=str(self.repo_path),
            commit_hash=commit_hash,
            indexed_at=now_iso,
            parser_version="1.0.0",
            files=all_files,
            modules=all_modules,
            classes=all_classes,
            functions=all_functions,
            external_symbols=list(self.external_symbols.values()),
            edges=all_edges,
            warnings=warnings or []
        )
