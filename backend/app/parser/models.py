from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

EdgeType = Literal[
    "HAS_FILE",
    "CONTAINS",
    "DEFINES",
    "IMPORTS",
    "CALLS",
    "INHERITS",
    "DECORATED_BY",
    "RAISES",
    "HANDLES",
    "REFERENCES",
    "TESTS"
]

class FileNode(BaseModel):
    id: str
    repo_id: str
    rel_path: str
    module_name: str
    line_count: int
    file_hash: str
    docstring: Optional[str] = None
    parse_status: str = "ok" # "ok", "syntax_error", "unsupported"
    parse_error: Optional[str] = None

class ModuleNode(BaseModel):
    id: str
    repo_id: str
    name: str
    rel_path: str

class ClassNode(BaseModel):
    id: str
    repo_id: str
    name: str
    qualified_name: str
    rel_path: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    bases: List[str] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)
    is_abstract: bool = False

class FunctionNode(BaseModel):
    id: str
    repo_id: str
    name: str
    qualified_name: str
    rel_path: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    parent_class: Optional[str] = None
    parameters: List[str] = Field(default_factory=list)
    return_annotation: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    raises: List[str] = Field(default_factory=list)
    handles: List[str] = Field(default_factory=list)

class ExternalSymbolNode(BaseModel):
    id: str
    name: str
    category: str = "library" # "exception", "library", "builtin", "call"
    repo_id: Optional[str] = None

class Edge(BaseModel):
    source_id: str
    target_id: str
    type: EdgeType
    properties: Dict[str, Any] = Field(default_factory=dict)

class ImportRecord(BaseModel):
    rel_path: str
    line: int
    module: str
    imported_name: Optional[str] = None
    alias: Optional[str] = None
    is_relative: bool = False
    level: int = 0

class RawCallRecord(BaseModel):
    caller_id: str
    caller_qualified_name: str
    rel_path: str
    line: int
    call_expr: str
    receiver: Optional[str] = None
    method_or_func: str
    is_in_try_block: bool = False
    is_in_except_block: bool = False

class ParsedFile(BaseModel):
    file_node: FileNode
    module_node: Optional[ModuleNode] = None
    classes: List[ClassNode] = Field(default_factory=list)
    functions: List[FunctionNode] = Field(default_factory=list)
    external_symbols: List[ExternalSymbolNode] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    imports: List[ImportRecord] = Field(default_factory=list)
    raw_calls: List[RawCallRecord] = Field(default_factory=list)

class RepositoryGraph(BaseModel):
    repo_id: str
    repo_name: str
    repo_path: str
    commit_hash: Optional[str] = None
    indexed_at: str
    parser_version: str = "1.0.0"
    files: List[FileNode] = Field(default_factory=list)
    modules: List[ModuleNode] = Field(default_factory=list)
    classes: List[ClassNode] = Field(default_factory=list)
    functions: List[FunctionNode] = Field(default_factory=list)
    external_symbols: List[ExternalSymbolNode] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
