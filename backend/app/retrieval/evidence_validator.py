from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.utils.paths import resolve_safe_subpath, validate_repo_path
from app.utils.identifiers import compute_file_hash
from app.core.logging import logger

class SourceEvidence(BaseModel):
    repository_id: str
    file: str
    symbol: Optional[str] = None
    start_line: int
    end_line: int
    snippet: str
    file_hash: str
    evidence_type: str = "source_snippet"
    is_valid: bool = True
    validation_notes: Optional[str] = None

class EvidenceValidator:
    """
    Validates citations and retrieves authentic source snippets directly
    from registered repository paths, preventing hallucinated lines or files.
    """
    @classmethod
    def get_source_snippet(
        cls,
        repo_root: Path,
        repo_id: str,
        rel_path: str,
        start_line: int,
        end_line: int,
        symbol_name: Optional[str] = None,
        context_padding: int = 2
    ) -> Optional[SourceEvidence]:
        try:
            full_path = resolve_safe_subpath(repo_root, rel_path)
            if not full_path.is_file():
                return None

            content_bytes = full_path.read_bytes()
            file_hash = compute_file_hash(content_bytes)
            all_lines = content_bytes.decode("utf-8", errors="replace").splitlines()
            total_lines = len(all_lines)

            # Clamp line numbers safely (1-indexed)
            clamped_start = max(1, min(start_line, total_lines))
            clamped_end = max(clamped_start, min(end_line, total_lines))

            # Add context padding
            padded_start = max(1, clamped_start - context_padding)
            padded_end = min(total_lines, clamped_end + context_padding)

            selected_slice = all_lines[padded_start - 1 : padded_end]
            numbered_snippet = "\n".join(
                f"{i:4d} | {line}"
                for i, line in enumerate(selected_slice, start=padded_start)
            )

            return SourceEvidence(
                repository_id=repo_id,
                file=rel_path.replace("\\", "/"),
                symbol=symbol_name,
                start_line=clamped_start,
                end_line=clamped_end,
                snippet=numbered_snippet,
                file_hash=file_hash,
                is_valid=True
            )
        except Exception as e:
            logger.warning(f"Failed to extract source evidence for {rel_path}: {e}")
            return None

    @classmethod
    def validate_citations(
        cls,
        repo_root: Path,
        repo_id: str,
        citations: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validates citation paths and line ranges against repository files.
        Returns (valid_citations, validation_warnings).
        """
        valid_citations = []
        warnings = []

        for c in citations:
            rel_file = c.get("file", "")
            start = c.get("start_line", 1)
            end = c.get("end_line", start)
            symbol = c.get("symbol", "")

            try:
                full_path = resolve_safe_subpath(repo_root, rel_file)
                if not full_path.is_file():
                    warnings.append(f"Rejected citation: file '{rel_file}' does not exist.")
                    continue

                total_lines = len(full_path.read_bytes().decode("utf-8", errors="replace").splitlines())
                if start > total_lines or end < 1 or start > end:
                    warnings.append(
                        f"Adjusted citation line bounds for {rel_file}: requested {start}-{end}, max {total_lines}"
                    )
                    start = max(1, min(start, total_lines))
                    end = max(start, min(end, total_lines))

                valid_citations.append({
                    "repository": repo_id,
                    "file": rel_file.replace("\\", "/"),
                    "symbol": symbol,
                    "start_line": start,
                    "end_line": end,
                    "evidence_type": "verified_source"
                })
            except Exception as e:
                warnings.append(f"Invalid citation path '{rel_file}': {e}")

        return valid_citations, warnings
