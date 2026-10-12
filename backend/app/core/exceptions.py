class NavigatorException(Exception):
    """Base exception for all Meta-Graph Navigator errors."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class RepositoryNotFoundError(NavigatorException):
    """Raised when a requested repository cannot be found."""
    pass

class RepositoryPathInvalidError(NavigatorException):
    """Raised when a target directory does not exist or is invalid."""
    pass

class PathTraversalError(NavigatorException):
    """Raised when a requested path attempts to escape the repository root."""
    pass

class IndexingError(NavigatorException):
    """Raised when an indexing or parsing operation fails."""
    pass

class GraphDatabaseError(NavigatorException):
    """Raised when an error occurs interacting with Neo4j or NetworkX."""
    pass

class LLMProviderError(NavigatorException):
    """Raised when Groq API interaction fails or rate limits exhaust."""
    pass

class EvidenceValidationError(NavigatorException):
    """Raised when citation or evidence verification fails."""
    pass

class QueryExecutionError(NavigatorException):
    """Raised when Cypher or graph traversal query fails."""
    pass
