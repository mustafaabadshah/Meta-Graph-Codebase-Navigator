from typing import List, Dict, Any, Optional, Set
from app.graph.base import BaseGraphStore
from app.retrieval.planner import RetrievalPlan
from app.retrieval.lexical_retriever import LexicalRetriever
from app.core.logging import logger

class GraphRetriever:
    """
    Structural Graph Retrieval Engine.
    Executes multi-stage entity resolution, bounded neighborhood expansion,
    call path tracing, and exception relationship mining.
    """
    def __init__(self, store: BaseGraphStore):
        self.store = store
        self.lexical = LexicalRetriever(store)

    def retrieve(self, plan: RetrievalPlan) -> Dict[str, Any]:
        repo_id = plan.repository_id
        
        # 1. Resolve seed symbols
        seed_symbols = self.lexical.search(repo_id, plan.target_terms, limit=12)
        seed_ids = [s["id"] for s in seed_symbols]

        if not seed_ids:
            # Fallback: search general terms
            fallback_matches = self.store.search_symbols(repo_id, "main", limit=5)
            seed_ids = [f["id"] for f in fallback_matches]

        # 2. Bounded multi-hop neighborhood traversal
        neighborhood = self.store.retrieve_multi_hop_context(
            repo_id=repo_id,
            seed_symbol_ids=seed_ids,
            max_hops=plan.max_hops,
            max_nodes=plan.max_nodes
        )

        nodes_by_id = {n["id"]: n for n in neighborhood["nodes"]}
        edges = neighborhood["edges"]

        # 3. Call path tracing between high-relevance seed endpoints
        call_paths: List[Dict[str, Any]] = []
        function_seeds = [s for s in seed_symbols if s.get("type") == "Function"]

        # Look for source -> target pairs (e.g. tournament -> game -> agent -> select_move)
        for i in range(len(function_seeds)):
            for j in range(len(function_seeds)):
                if i != j:
                    src = function_seeds[i]["id"]
                    dst = function_seeds[j]["id"]
                    discovered = self.store.trace_call_path(src, dst, max_depth=4)
                    if discovered:
                        call_paths.extend(discovered)
                        if len(call_paths) >= 3:
                            break
            if len(call_paths) >= 3:
                break

        # 4. Exception & Retry relationships
        exception_records: List[Dict[str, Any]] = []
        for e in edges:
            if e.get("type") in ("HANDLES", "RAISES"):
                src_node = nodes_by_id.get(e["source"])
                tgt_node = nodes_by_id.get(e["target"])
                exception_records.append({
                    "type": e["type"],
                    "source": src_node.get("qualified_name") if src_node else e["source"],
                    "target": tgt_node.get("name") if tgt_node else e["target"],
                    "properties": e.get("properties", {})
                })

        # 5. Rank symbols by graph connectivity & relevance
        degree_map: Dict[str, int] = {}
        for e in edges:
            degree_map[e["source"]] = degree_map.get(e["source"], 0) + 1
            degree_map[e["target"]] = degree_map.get(e["target"], 0) + 1

        ranked_nodes = sorted(
            nodes_by_id.values(),
            key=lambda n: (degree_map.get(n["id"], 0), 1 if n.get("type") == "Function" else 0),
            reverse=True
        )

        return {
            "repository_id": repo_id,
            "seed_symbols": seed_symbols,
            "nodes": list(nodes_by_id.values()),
            "edges": edges,
            "ranked_nodes": ranked_nodes[:20],
            "call_paths": call_paths,
            "exception_records": exception_records
        }
