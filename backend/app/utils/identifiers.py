import hashlib
import re

def slugify_repo_name(name: str) -> str:
    """Creates a clean deterministic slug for repository identifiers."""
    slug = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name.strip().lower())
    return re.sub(r'_+', '_', slug).strip('_') or "repo"

def make_repo_id(repo_path: str, repo_name: str | None = None) -> str:
    """Generates a stable repository identifier based on name or path."""
    if repo_name:
        return slugify_repo_name(repo_name)
    normalized = str(repo_path).replace("\\", "/").rstrip("/")
    base_name = normalized.split("/")[-1]
    return slugify_repo_name(base_name)

def make_file_id(repo_id: str, rel_path: str) -> str:
    clean_path = rel_path.replace("\\", "/").lstrip("/")
    return f"{repo_id}:file:{clean_path}"

def make_module_id(repo_id: str, module_name: str) -> str:
    return f"{repo_id}:module:{module_name}"

def make_class_id(repo_id: str, rel_path: str, qualified_name: str) -> str:
    clean_path = rel_path.replace("\\", "/").lstrip("/")
    return f"{repo_id}:class:{clean_path}:{qualified_name}"

def make_function_id(repo_id: str, rel_path: str, qualified_name: str, start_line: int | None = None) -> str:
    clean_path = rel_path.replace("\\", "/").lstrip("/")
    # If standard qualified name
    return f"{repo_id}:func:{clean_path}:{qualified_name}"

def make_external_symbol_id(symbol_name: str) -> str:
    return f"ext:{symbol_name.strip()}"

def compute_file_hash(content_bytes: bytes) -> str:
    """Computes a SHA-256 hash of file contents for change detection."""
    return hashlib.sha256(content_bytes).hexdigest()
