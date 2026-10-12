from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

class NavigatorState(TypedDict, total=False):
    question: str
    repository_id: str
    repo_path: str
    detail_level: str
    retrieval_depth: int
    
    # Analysis & Planning
    is_valid_question: bool
    plan: Dict[str, Any]
    
    # Graph Retrieval
    seed_symbol_ids: List[str]
    graph_context: Dict[str, Any]
    
    # Source Evidence
    source_evidence: List[Dict[str, Any]]
    
    # Generation & Validation
    raw_answer: str
    answer: str
    execution_flow: List[str]
    citations: List[Dict[str, Any]]
    warnings: List[str]
    model_metadata: Dict[str, Any]
    
    # Control Flow
    iteration: int
    is_complete: bool
