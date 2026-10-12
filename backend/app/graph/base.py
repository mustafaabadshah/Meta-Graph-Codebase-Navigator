from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.parser.models import RepositoryGraph

class BaseGraphStore(ABC):
    """
    Abstract Graph Storage Interface.
    Decouples graph retrieval logic and UI from specific database engines (Neo4j, NetworkX, etc.).
    """

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Returns connection health and backend details."""
        pass

    @abstractmethod
    def register_repository(self, graph: RepositoryGraph) -> None:
        """Registers a repository root node and metadata."""
        pass

    @abstractmethod
    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves registered repository metadata."""
        pass

    @abstractmethod
    def list_repositories(self) -> List[Dict[str, Any]]:
        """Lists all registered repositories."""
        pass

    @abstractmethod
    def create_or_update_index(self, graph: RepositoryGraph) -> None:
        """Ingests all files, symbols, and relationships into the graph."""
        pass

    @abstractmethod
    def get_graph_statistics(self, repo_id: str) -> Dict[str, Any]:
        """Returns node counts, edge counts, and schema breakdown for a repository."""
        pass

    @abstractmethod
    def get_symbol(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves exact symbol node details."""
        pass

    @abstractmethod
    def search_symbols(self, repo_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Searches symbols by name or qualified name."""
        pass

    @abstractmethod
    def get_file_symbols(self, repo_id: str, rel_path: str) -> Dict[str, Any]:
        """Returns all classes and functions defined inside a given file."""
        pass

    @abstractmethod
    def get_incoming_relationships(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves incoming edges to a symbol."""
        pass

    @abstractmethod
    def get_outgoing_relationships(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves outgoing edges from a symbol."""
        pass

    @abstractmethod
    def get_callers(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns functions that call this symbol."""
        pass

    @abstractmethod
    def get_callees(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns functions called by this symbol."""
        pass

    @abstractmethod
    def get_import_chain(self, repo_id: str, file_or_module: str, max_depth: int = 3) -> Dict[str, Any]:
        """Retrieves the tree of imported modules."""
        pass

    @abstractmethod
    def get_inheritance_tree(self, repo_id: str, class_name_or_id: str) -> Dict[str, Any]:
        """Retrieves ancestor and descendant inheritance chains."""
        pass

    @abstractmethod
    def trace_call_path(self, source_id: str, target_id: str, max_depth: int = 4) -> List[Dict[str, Any]]:
        """Finds directed execution call paths connecting source symbol to target symbol."""
        pass

    @abstractmethod
    def get_related_symbols(self, symbol_id: str, max_hops: int = 2, limit: int = 50) -> Dict[str, Any]:
        """Retrieves immediate neighborhood subgraph."""
        pass

    @abstractmethod
    def retrieve_multi_hop_context(
        self,
        repo_id: str,
        seed_symbol_ids: List[str],
        max_hops: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """Traverses bounded multi-hop subgraph around seed symbols."""
        pass

    @abstractmethod
    def get_subgraph(
        self,
        repo_id: str,
        view_mode: str = "architecture",
        focus_symbol_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 80
    ) -> Dict[str, Any]:
        """Retrieves a curated subgraph for visualization (architecture, modules, hierarchy, all)."""
        pass

    @abstractmethod
    def delete_repository_index(self, repo_id: str) -> None:
        """Deletes all graph nodes and edges belonging strictly to repo_id."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes any active database connections or drivers."""
        pass
