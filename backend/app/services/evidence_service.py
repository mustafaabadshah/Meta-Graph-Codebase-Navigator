from pathlib import Path
from typing import Dict, Any, Optional

from app.core.exceptions import RepositoryNotFoundError, RepositoryPathInvalidError
from app.services.repository_service import repository_service
from app.utils.paths import resolve_safe_subpath
from app.utils.identifiers import compute_file_hash
from app.schemas.evidence import SourceSnippetResponse
from app.graph import get_graph_store

class EvidenceService:
    def get_source_file_content(
        self,
        repo_id: str,
        rel_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        symbol_name: Optional[str] = None
    ) -> SourceSnippetResponse:
        repo = repository_service.get_repository(repo_id)
        repo_root = Path(repo.path)

        full_path = resolve_safe_subpath(repo_root, rel_path)
        if not full_path.is_file():
            raise RepositoryPathInvalidError(f"File '{rel_path}' not found in repository.")

        raw_bytes = full_path.read_bytes()
        file_hash = compute_file_hash(raw_bytes)
        lines = raw_bytes.decode("utf-8", errors="replace").splitlines()
        total_lines = len(lines)

        s_line = max(1, start_line) if start_line else 1
        e_line = min(total_lines, end_line) if end_line else total_lines

        selected_slice = lines[s_line - 1 : e_line]
        snippet_text = "\n".join(
            f"{i:4d} | {line}"
            for i, line in enumerate(selected_slice, start=s_line)
        )

        return SourceSnippetResponse(
            repository_id=repo_id,
            rel_path=rel_path.replace("\\", "/"),
            symbol=symbol_name,
            start_line=s_line,
            end_line=e_line,
            total_lines=total_lines,
            snippet=snippet_text,
            full_content="\n".join(lines),
            file_hash=file_hash
        )

evidence_service = EvidenceService()
