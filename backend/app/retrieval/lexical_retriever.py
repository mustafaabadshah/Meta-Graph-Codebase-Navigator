from typing import List, Dict, Any
from app.graph.base import BaseGraphStore

class LexicalRetriever:
    """
    Lightweight lexical matching across symbol names, qualified names, and docstrings.
    Provides fast entity discovery without external vector/embedding dependencies.
    """
    def __init__(self, store: BaseGraphStore):
        self.store = store

    def search(self, repo_id: str, terms: List[str], limit: int = 15) -> List[Dict[str, Any]]:
        scored_results: Dict[str, Dict[str, Any]] = {}

        for term in terms:
            matches = self.store.search_symbols(repo_id, term, limit=limit)
            for m in matches:
                sid = m["id"]
                score = scored_results.get(sid, {}).get("score", 0.0)

                name_lower = (m.get("name") or "").lower()
                qname_lower = (m.get("qualified_name") or "").lower()
                term_lower = term.lower()

                # Scoring weights
                if term_lower == name_lower:
                    score += 5.0
                elif term_lower in name_lower:
                    score += 3.0
                elif term_lower in qname_lower:
                    score += 2.0
                else:
                    score += 1.0

                # Boost functions/classes with docstrings or error handling
                if m.get("handles") or m.get("raises"):
                    score += 1.5

                entry = dict(m)
                entry["score"] = score
                scored_results[sid] = entry

        sorted_list = sorted(scored_results.values(), key=lambda x: x["score"], reverse=True)
        return sorted_list[:limit]
