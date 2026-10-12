import os
from pathlib import Path
from app.core.exceptions import RepositoryPathInvalidError, PathTraversalError

def validate_repo_path(raw_path: str | Path) -> Path:
    """
    Validates and resolves a local repository path to a canonical absolute Path.
    Ensures it exists and is an accessible directory.
    """
    if not raw_path:
        raise RepositoryPathInvalidError("Repository path cannot be empty.")
    
    path_obj = Path(raw_path).expanduser().resolve()
    
    if not path_obj.exists():
        raise RepositoryPathInvalidError(f"Directory does not exist: {path_obj}")
    if not path_obj.is_dir():
        raise RepositoryPathInvalidError(f"Specified path is not a directory: {path_obj}")
    
    return path_obj

def resolve_safe_subpath(repo_root: Path, relative_path: str | Path) -> Path:
    """
    Safely resolves a relative file path inside repo_root, strictly preventing
    directory traversal attacks (e.g. ../../windows/system32).
    """
    root_resolved = repo_root.resolve()
    # Normalize slashes
    clean_rel = str(relative_path).replace("\\", "/").lstrip("/")
    target_path = (root_resolved / clean_rel).resolve()

    try:
        # Raises ValueError if target_path is not relative to root_resolved
        target_path.relative_to(root_resolved)
    except ValueError:
        raise PathTraversalError(f"Access denied: path escapes repository root: {relative_path}")

    return target_path

def normalize_posix_relpath(repo_root: Path, file_path: Path) -> str:
    """
    Converts a file path to a normalized relative path with forward slashes (e.g. backend/app/main.py)
    so identifiers and citations are cross-platform compatible and consistent.
    """
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = file_path
    return rel.as_posix()
