import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import networkx as nx

from app.graph.base import BaseGraphStore
from app.parser.models import RepositoryGraph, Edge
from app.core.config import settings
from app.core.logging import logger

class NetworkXStore(BaseGraphStore):
    """
    In-memory and file-persisted NetworkX Graph Store implementation.
    Fully implements BaseGraphStore interface for zero-friction local development,
    instant testing, and resilient offline execution.
    """
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.INDEXES_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.graph = nx.MultiDiGraph()
        self.repositories: Dict[str, Dict[str, Any]] = {}
        self._load_all_persisted()

    def _get_repo_file(self, repo_id: str) -> Path:
        return self.storage_dir / f"{repo_id}_nx.json"

    def _load_all_persisted(self):
        for path in self.storage_dir.glob("*_nx.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                repo_meta = data.get("repository", {})
                repo_id = repo_meta.get("repo_id")
                if repo_id:
                    self.repositories[repo_id] = repo_meta
                    for node in data.get("nodes", []):
                        nid = node["id"]
                        self.graph.add_node(nid, **node)
                    for edge in data.get("edges", []):
                        self.graph.add_edge(
                            edge["source_id"],
                            edge["target_id"],
                            key=f"{edge['type']}:{edge.get('properties', {}).get('line', 0)}",
                            type=edge["type"],
                            **edge.get("properties", {})
                        )
                logger.info(f"Loaded persisted NetworkX index for repo {repo_id}")
            except Exception as e:
                logger.warning(f"Failed to load persisted graph from {path}: {e}")

    def _persist_repo(self, repo_id: str):
        target_path = self._get_repo_file(repo_id)
        nodes = []
        for n, d in self.graph.nodes(data=True):
            if d.get("repo_id") == repo_id or d.get("category") is not None:
                nodes.append({"id": n, **d})

        edges = []
        for u, v, k, d in self.graph.edges(keys=True, data=True):
            u_data = self.graph.nodes.get(u, {})
            if u_data.get("repo_id") == repo_id:
                props = {k: v for k, v in d.items() if k != "type"}
                edges.append({
                    "source_id": u,
                    "target_id": v,
                    "type": d.get("type", "REFERENCES"),
                    "properties": props
                })

        payload = {
            "repository": self.repositories.get(repo_id, {}),
            "nodes": nodes,
            "edges": edges
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def check_connection(self) -> Dict[str, Any]:
        return {
            "backend": "networkx",
            "connected": True,
            "active": True,
            "message": "Local NetworkX graph store operational.",
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }

    def register_repository(self, graph: RepositoryGraph) -> None:
        self.repositories[graph.repo_id] = {
            "repo_id": graph.repo_id,
            "repo_name": graph.repo_name,
            "repo_path": graph.repo_path,
            "commit_hash": graph.commit_hash,
            "indexed_at": graph.indexed_at,
            "parser_version": graph.parser_version,
            "warnings": graph.warnings
        }

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        return self.repositories.get(repo_id)

    def list_repositories(self) -> List[Dict[str, Any]]:
        return list(self.repositories.values())

    def create_or_update_index(self, graph: RepositoryGraph) -> None:
        self.delete_repository_index(graph.repo_id)
        self.register_repository(graph)

        repo_node_id = f"repo:{graph.repo_id}"
        self.graph.add_node(
            repo_node_id,
            id=repo_node_id,
            type="Repository",
            repo_id=graph.repo_id,
            name=graph.repo_name,
            path=graph.repo_path
        )

        for f in graph.files:
            self.graph.add_node(f.id, type="File", **f.model_dump())
            self.graph.add_edge(repo_node_id, f.id, type="HAS_FILE")

        for m in graph.modules:
            self.graph.add_node(m.id, type="Module", **m.model_dump())

        for c in graph.classes:
            self.graph.add_node(c.id, type="Class", **c.model_dump())

        for fn in graph.functions:
            self.graph.add_node(fn.id, type="Function", **fn.model_dump())

        for ext in graph.external_symbols:
            self.graph.add_node(ext.id, type="ExternalSymbol", **ext.model_dump())

        for e in graph.edges:
            self.graph.add_edge(
                e.source_id,
                e.target_id,
                type=e.type,
                **e.properties
            )

        self._persist_repo(graph.repo_id)
        logger.info(f"Indexed {len(graph.files)} files and {len(graph.edges)} edges in NetworkX for {graph.repo_id}")

    def apply_graph_diff(
        self,
        repo_id: str,
        graph: RepositoryGraph,
        added_files: List[str],
        modified_files: List[str],
        deleted_files: List[str]
    ) -> Dict[str, Any]:
        """
        Incrementally modifies only the nodes and edges belonging to changed files.
        Unchanged files remain untouched in the in-memory graph.
        """
        changed_rels = set(modified_files + deleted_files)
        repo_node_id = f"repo:{repo_id}"

        # 1. Prune nodes associated with modified and deleted files
        nodes_to_remove = []
        for n, d in self.graph.nodes(data=True):
            if d.get("repo_id") == repo_id:
                if d.get("rel_path") in changed_rels:
                    nodes_to_remove.append(n)

        self.graph.remove_nodes_from(nodes_to_remove)

        # 2. Update repository metadata
        self.register_repository(graph)
        if not self.graph.has_node(repo_node_id):
            self.graph.add_node(
                repo_node_id,
                id=repo_node_id,
                type="Repository",
                repo_id=graph.repo_id,
                name=graph.repo_name,
                path=graph.repo_path
            )

        # 3. Add / Update nodes only for added and modified files
        target_rels = set(added_files + modified_files)
        added_node_count = 0

        for f in graph.files:
            if f.rel_path in target_rels:
                self.graph.add_node(f.id, type="File", **f.model_dump())
                self.graph.add_edge(repo_node_id, f.id, type="HAS_FILE")
                added_node_count += 1

        for m in graph.modules:
            if m.rel_path in target_rels:
                self.graph.add_node(m.id, type="Module", **m.model_dump())
                added_node_count += 1

        for c in graph.classes:
            if c.rel_path in target_rels:
                self.graph.add_node(c.id, type="Class", **c.model_dump())
                added_node_count += 1

        for fn in graph.functions:
            if fn.rel_path in target_rels:
                self.graph.add_node(fn.id, type="Function", **fn.model_dump())
                added_node_count += 1

        for ext in graph.external_symbols:
            if not self.graph.has_node(ext.id):
                self.graph.add_node(ext.id, type="ExternalSymbol", **ext.model_dump())

        # 4. Ingest edges that touch the newly added / updated nodes
        added_edge_count = 0
        for e in graph.edges:
            if self.graph.has_node(e.source_id) and self.graph.has_node(e.target_id):
                edge_line = e.properties.get("line", 0)
                edge_key = f"{e.type}:{edge_line}"
                self.graph.add_edge(
                    e.source_id,
                    e.target_id,
                    key=edge_key,
                    type=e.type,
                    **e.properties
                )
                added_edge_count += 1

        self._persist_repo(repo_id)
        logger.info(
            f"Graph Diff applied to NetworkX for {repo_id}: "
            f"pruned {len(nodes_to_remove)} obsolete nodes, ingested {added_node_count} nodes, "
            f"current graph size: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges."
        )

        return {
            "status": "incremental_applied",
            "nodes_pruned": len(nodes_to_remove),
            "nodes_ingested": added_node_count,
            "edges_ingested": added_edge_count,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }

    def get_graph_statistics(self, repo_id: str) -> Dict[str, Any]:
        node_counts: Dict[str, int] = {}
        edge_counts: Dict[str, int] = {}

        relevant_nodes = set()
        for n, d in self.graph.nodes(data=True):
            if d.get("repo_id") == repo_id or n == f"repo:{repo_id}":
                relevant_nodes.add(n)
                ntype = d.get("type", "Unknown")
                node_counts[ntype] = node_counts.get(ntype, 0) + 1

        for u, v, k, d in self.graph.edges(keys=True, data=True):
            if u in relevant_nodes:
                etype = d.get("type", "REFERENCES")
                edge_counts[etype] = edge_counts.get(etype, 0) + 1

        return {
            "repository_id": repo_id,
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(edge_counts.values()),
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts
        }

    def get_symbol(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        if symbol_id in self.graph:
            return {"id": symbol_id, **self.graph.nodes[symbol_id]}
        return None

    def search_symbols(self, repo_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = query.lower().strip()
        results = []
        for n, d in self.graph.nodes(data=True):
            if d.get("repo_id") != repo_id and d.get("type") != "ExternalSymbol":
                continue
            name = (d.get("name") or "").lower()
            qname = (d.get("qualified_name") or "").lower()
            if q in name or q in qname or q == n.lower():
                results.append({"id": n, **d})
                if len(results) >= limit:
                    break
        return results

    def get_file_symbols(self, repo_id: str, rel_path: str) -> Dict[str, Any]:
        classes = []
        functions = []
        for n, d in self.graph.nodes(data=True):
            if d.get("repo_id") == repo_id and d.get("rel_path") == rel_path:
                if d.get("type") == "Class":
                    classes.append({"id": n, **d})
                elif d.get("type") == "Function":
                    functions.append({"id": n, **d})
        return {"rel_path": rel_path, "classes": classes, "functions": functions}

    def get_incoming_relationships(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        res = []
        if symbol_id not in self.graph:
            return res
        for u, v, k, d in self.graph.in_edges(symbol_id, keys=True, data=True):
            res.append({
                "source_id": u,
                "source_data": self.graph.nodes.get(u, {}),
                "type": d.get("type"),
                "properties": {k: val for k, val in d.items() if k != "type"}
            })
            if len(res) >= limit:
                break
        return res

    def get_outgoing_relationships(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        res = []
        if symbol_id not in self.graph:
            return res
        for u, v, k, d in self.graph.out_edges(symbol_id, keys=True, data=True):
            res.append({
                "target_id": v,
                "target_data": self.graph.nodes.get(v, {}),
                "type": d.get("type"),
                "properties": {k: val for k, val in d.items() if k != "type"}
            })
            if len(res) >= limit:
                break
        return res

    def get_callers(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        callers = []
        if symbol_id not in self.graph:
            return callers
        for u, v, k, d in self.graph.in_edges(symbol_id, keys=True, data=True):
            if d.get("type") == "CALLS":
                callers.append({
                    "id": u,
                    **self.graph.nodes.get(u, {}),
                    "call_line": d.get("line"),
                    "call_expr": d.get("call_expr"),
                    "is_in_try": d.get("is_in_try", False),
                    "is_in_except": d.get("is_in_except", False)
                })
                if len(callers) >= limit:
                    break
        return callers

    def get_callees(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        callees = []
        if symbol_id not in self.graph:
            return callees
        for u, v, k, d in self.graph.out_edges(symbol_id, keys=True, data=True):
            if d.get("type") == "CALLS":
                callees.append({
                    "id": v,
                    **self.graph.nodes.get(v, {}),
                    "call_line": d.get("line"),
                    "call_expr": d.get("call_expr"),
                    "is_in_try": d.get("is_in_try", False),
                    "is_in_except": d.get("is_in_except", False)
                })
                if len(callees) >= limit:
                    break
        return callees

    def get_import_chain(self, repo_id: str, file_or_module: str, max_depth: int = 3) -> Dict[str, Any]:
        # Bounded BFS along IMPORTS edges
        visited_nodes = {}
        visited_edges = []
        queue = [(file_or_module, 0)]
        while queue:
            curr, depth = queue.pop(0)
            if depth >= max_depth or curr not in self.graph:
                continue
            if curr not in visited_nodes:
                visited_nodes[curr] = {"id": curr, **self.graph.nodes[curr]}
            for u, v, k, d in self.graph.out_edges(curr, keys=True, data=True):
                if d.get("type") == "IMPORTS":
                    visited_edges.append({"source": u, "target": v, "properties": d})
                    if v not in visited_nodes and depth + 1 <= max_depth:
                        queue.append((v, depth + 1))
        return {"nodes": list(visited_nodes.values()), "edges": visited_edges}

    def get_inheritance_tree(self, repo_id: str, class_name_or_id: str) -> Dict[str, Any]:
        # Find root class node
        target_node = None
        for n, d in self.graph.nodes(data=True):
            if d.get("type") == "Class" and (n == class_name_or_id or d.get("name") == class_name_or_id):
                target_node = n
                break
        if not target_node:
            return {"nodes": [], "edges": []}

        nodes = {target_node: {"id": target_node, **self.graph.nodes[target_node]}}
        edges = []
        # Ancestors (out edges with INHERITS)
        for u, v, k, d in self.graph.out_edges(target_node, keys=True, data=True):
            if d.get("type") == "INHERITS":
                edges.append({"source": u, "target": v, "type": "INHERITS"})
                if v in self.graph:
                    nodes[v] = {"id": v, **self.graph.nodes[v]}

        # Descendants (in edges with INHERITS)
        for u, v, k, d in self.graph.in_edges(target_node, keys=True, data=True):
            if d.get("type") == "INHERITS":
                edges.append({"source": u, "target": v, "type": "INHERITS"})
                if u in self.graph:
                    nodes[u] = {"id": u, **self.graph.nodes[u]}

        return {"nodes": list(nodes.values()), "edges": edges}

    def trace_call_path(self, source_id: str, target_id: str, max_depth: int = 4) -> List[Dict[str, Any]]:
        """
        Finds directed call paths from source function to target function.
        Restricted to CALLS edges.
        """
        if source_id not in self.graph or target_id not in self.graph:
            return []

        call_subgraph = nx.DiGraph()
        for u, v, k, d in self.graph.edges(keys=True, data=True):
            if d.get("type") == "CALLS":
                call_subgraph.add_edge(u, v, **d)

        paths = []
        try:
            for path in nx.all_simple_paths(call_subgraph, source=source_id, target=target_id, cutoff=max_depth):
                path_details = []
                for i in range(len(path) - 1):
                    u = path[i]
                    v = path[i + 1]
                    edge_data = call_subgraph.get_edge_data(u, v) or {}
                    path_details.append({
                        "step": i + 1,
                        "from_id": u,
                        "from_data": self.graph.nodes.get(u, {}),
                        "to_id": v,
                        "to_data": self.graph.nodes.get(v, {}),
                        "call_line": edge_data.get("line"),
                        "call_expr": edge_data.get("call_expr")
                    })
                paths.append({"nodes": path, "steps": path_details})
                if len(paths) >= 5: # Limit paths
                    break
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        return paths

    def get_related_symbols(self, symbol_id: str, max_hops: int = 2, limit: int = 50) -> Dict[str, Any]:
        if symbol_id not in self.graph:
            return {"nodes": [], "edges": []}
        return self.retrieve_multi_hop_context(
            repo_id=self.graph.nodes[symbol_id].get("repo_id", ""),
            seed_symbol_ids=[symbol_id],
            max_hops=max_hops,
            max_nodes=limit
        )

    def retrieve_multi_hop_context(
        self,
        repo_id: str,
        seed_symbol_ids: List[str],
        max_hops: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        Traverses a bounded multi-hop neighborhood around seed symbols.
        Returns deduplicated nodes and edges.
        """
        visited_nodes: Dict[str, Dict[str, Any]] = {}
        visited_edges: List[Dict[str, Any]] = []
        edge_keys_seen = set()

        queue = [(sid, 0) for sid in seed_symbol_ids if sid in self.graph]

        while queue and len(visited_nodes) < max_nodes:
            curr_id, depth = queue.pop(0)
            if curr_id not in visited_nodes:
                visited_nodes[curr_id] = {"id": curr_id, **self.graph.nodes[curr_id]}

            if depth >= max_hops:
                continue

            # Outgoing edges (skip Repository node and HAS_FILE explosion)
            for u, v, k, d in self.graph.out_edges(curr_id, keys=True, data=True):
                if d.get("type") == "HAS_FILE" or self.graph.nodes.get(v, {}).get("type") == "Repository":
                    continue
                edge_key = (u, v, d.get("type"), d.get("line"))
                if edge_key not in edge_keys_seen:
                    edge_keys_seen.add(edge_key)
                    visited_edges.append({
                        "source": u,
                        "target": v,
                        "type": d.get("type", "REFERENCES"),
                        "properties": {k: val for k, val in d.items() if k != "type"}
                    })
                if v not in visited_nodes and len(visited_nodes) < max_nodes:
                    visited_nodes[v] = {"id": v, **self.graph.nodes.get(v, {})}
                    queue.append((v, depth + 1))

            # Incoming edges (skip Repository node and HAS_FILE explosion)
            for u, v, k, d in self.graph.in_edges(curr_id, keys=True, data=True):
                if d.get("type") == "HAS_FILE" or self.graph.nodes.get(u, {}).get("type") == "Repository":
                    continue
                edge_key = (u, v, d.get("type"), d.get("line"))
                if edge_key not in edge_keys_seen:
                    edge_keys_seen.add(edge_key)
                    visited_edges.append({
                        "source": u,
                        "target": v,
                        "type": d.get("type", "REFERENCES"),
                        "properties": {k: val for k, val in d.items() if k != "type"}
                    })
                if u not in visited_nodes and len(visited_nodes) < max_nodes:
                    visited_nodes[u] = {"id": u, **self.graph.nodes.get(u, {})}
                    queue.append((u, depth + 1))

        return {
            "nodes": list(visited_nodes.values()),
            "edges": visited_edges
        }

    def get_subgraph(
        self,
        repo_id: str,
        view_mode: str = "architecture",
        focus_symbol_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 80
    ) -> Dict[str, Any]:
        if focus_symbol_id:
            return self.retrieve_multi_hop_context(
                repo_id=repo_id,
                seed_symbol_ids=[focus_symbol_id],
                max_hops=depth,
                max_nodes=limit
            )

        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        allowed_edge_types = None
        if view_mode == "architecture":
            allowed_edge_types = {"CALLS", "INHERITS", "DEFINES", "HANDLES", "RAISES"}
        elif view_mode == "modules":
            allowed_edge_types = {"IMPORTS"}
        elif view_mode == "hierarchy":
            allowed_edge_types = {"CONTAINS", "DEFINES"}
        elif view_mode in ("diff", "changes"):
            allowed_edge_types = None

        for u, v, k, d in self.graph.edges(keys=True, data=True):
            rel_type = d.get("type")
            if rel_type == "HAS_FILE":
                continue
            if allowed_edge_types is not None and rel_type not in allowed_edge_types:
                continue

            u_node = self.graph.nodes.get(u, {})
            v_node = self.graph.nodes.get(v, {})

            if u_node.get("type") == "Repository" or v_node.get("type") == "Repository":
                continue

            if u_node.get("repo_id") != repo_id and u_node.get("type") != "ExternalSymbol":
                continue
            if v_node.get("repo_id") != repo_id and v_node.get("type") != "ExternalSymbol":
                continue

            if view_mode == "architecture":
                if u_node.get("type") not in ("Class", "Function") and v_node.get("type") not in ("Class", "Function"):
                    continue
            elif view_mode == "modules":
                if u_node.get("type") not in ("File", "Module") and v_node.get("type") not in ("File", "Module"):
                    continue

            nodes[u] = {"id": u, **u_node}
            nodes[v] = {"id": v, **v_node}
            edges.append({
                "source": u,
                "target": v,
                "type": rel_type,
                "properties": {pk: pv for pk, pv in d.items() if pk != "type"}
            })

            if len(edges) >= limit:
                break

        return {"nodes": list(nodes.values()), "edges": edges}

    def delete_repository_index(self, repo_id: str) -> None:
        nodes_to_remove = [
            n for n, d in self.graph.nodes(data=True)
            if d.get("repo_id") == repo_id or n == f"repo:{repo_id}"
        ]
        self.graph.remove_nodes_from(nodes_to_remove)
        if repo_id in self.repositories:
            del self.repositories[repo_id]

        target_file = self._get_repo_file(repo_id)
        if target_file.is_file():
            try:
                target_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete {target_file}: {e}")

    def close(self) -> None:
        pass
