import time
import socket
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError

from app.graph.base import BaseGraphStore
from app.parser.models import RepositoryGraph
from app.graph.schema import NEO4J_CONSTRAINTS, NEO4J_INDEXES
from app.graph.queries import (
    UNWIND_MERGE_FILES, UNWIND_MERGE_MODULES, UNWIND_MERGE_CLASSES,
    UNWIND_MERGE_FUNCTIONS, UNWIND_MERGE_EXTERNAL_SYMBOLS,
    CYPHER_CREATE_EDGE_TEMPLATE, SEARCH_SYMBOLS_CYPHER,
    CALLERS_CYPHER, CALLEES_CYPHER
)
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import GraphDatabaseError

class Neo4jStore(BaseGraphStore):
    """
    Production Neo4j Graph Store implementation using official Neo4j Python Driver.
    Features idempotent batch ingestion with UNWIND, uniqueness constraints,
    strict parameterized Cypher queries, and bounded multi-hop traversals.
    """
    def __init__(
        self,
        uri: str = settings.NEO4J_URI,
        username: str = settings.NEO4J_USERNAME,
        password: str = settings.NEO4J_PASSWORD,
        database: str = settings.NEO4J_DATABASE
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        self._connected: bool = False
        self._last_error: Optional[str] = None

        self._init_driver()

    def _is_reachable(self, timeout: float = 0.8) -> bool:
        """Fast socket probe to prevent slow TCP timeouts or WinError 10061 dumps."""
        try:
            parsed = urlparse(self.uri)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 7687
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def _init_driver(self):
        if not self._is_reachable(timeout=0.8):
            self._connected = False
            self._last_error = f"Neo4j instance at {self.uri} is offline or unreachable (port 7687 closed)."
            logger.info(f"Neo4j not listening at {self.uri}. Using NetworkX fallback store.")
            return

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
                connection_acquisition_timeout=3.0,
                connection_timeout=3.0
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            self._connected = True
            self._last_error = None
            self._apply_constraints()
            logger.info(f"Connected successfully to Neo4j at {self.uri}")
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.warning(f"Neo4j connection failed ({self.uri}): {e}")

    def check_connection(self) -> Dict[str, Any]:
        """Validates live connectivity and returns diagnostic information."""
        if not self._is_reachable(timeout=0.8):
            self._connected = False
            self._last_error = f"Neo4j instance at {self.uri} is offline (port 7687 closed)."
            return {
                "backend": "neo4j",
                "connected": False,
                "active": False,
                "uri": self.uri,
                "database": self.database,
                "message": f"Neo4j unreachable at {self.uri}. The local port is not open.",
                "troubleshooting": (
                    "To run Neo4j locally: Start Docker Desktop and run 'docker compose up -d neo4j'. "
                    "Alternatively, set GRAPH_BACKEND=networkx in .env to run purely standalone, "
                    "or configure a free Neo4j AuraDB instance in .env."
                )
            }
        if not self.driver:
            self._init_driver()
        else:
            try:
                self.driver.verify_connectivity()
                self._connected = True
                self._last_error = None
            except Exception as e:
                self._connected = False
                self._last_error = str(e)

        return {
            "backend": "neo4j",
            "connected": self._connected,
            "active": self._connected,
            "uri": self.uri,
            "database": self.database,
            "message": "Connected to Neo4j database." if self._connected else f"Neo4j unreachable: {self._last_error}",
            "troubleshooting": (
                "Ensure local Neo4j is running ('docker compose up -d neo4j') or configure valid AuraDB credentials in .env"
                if not self._connected else None
            )
        }

    def _apply_constraints(self):
        if not self._connected or not self.driver:
            return
        try:
            with self.driver.session(database=self.database) as session:
                for c in NEO4J_CONSTRAINTS:
                    session.run(c)
                for idx in NEO4J_INDEXES:
                    session.run(idx)
        except Exception as e:
            logger.warning(f"Failed applying Neo4j schema constraints/indexes: {e}")

    def _ensure_connected(self):
        status = self.check_connection()
        if not status["connected"]:
            raise GraphDatabaseError(
                f"Neo4j database is unreachable at {self.uri}. Details: {self._last_error}",
                details=status
            )

    def register_repository(self, graph: RepositoryGraph) -> None:
        self._ensure_connected()
        cypher = """
        MERGE (r:Repository {id: $id})
        SET r.name = $name,
            r.path = $path,
            r.commit_hash = $commit_hash,
            r.indexed_at = $indexed_at,
            r.parser_version = $parser_version
        """
        with self.driver.session(database=self.database) as session:
            session.run(cypher, {
                "id": f"repo:{graph.repo_id}",
                "name": graph.repo_name,
                "path": graph.repo_path,
                "commit_hash": graph.commit_hash,
                "indexed_at": graph.indexed_at,
                "parser_version": graph.parser_version
            })

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        cypher = "MATCH (r:Repository {id: $id}) RETURN r"
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"id": f"repo:{repo_id}"})
            rec = res.single()
            if rec:
                node = rec["r"]
                return dict(node)
        return None

    def list_repositories(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        cypher = "MATCH (r:Repository) RETURN r"
        results = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher)
            for rec in res:
                results.append(dict(rec["r"]))
        return results

    def create_or_update_index(self, graph: RepositoryGraph) -> None:
        self._ensure_connected()
        # Clean existing repo entities first
        self.delete_repository_index(graph.repo_id)
        self.register_repository(graph)

        batch_size = 500

        with self.driver.session(database=self.database) as session:
            # 1. Ingest Files
            file_dicts = [f.model_dump() for f in graph.files]
            for i in range(0, len(file_dicts), batch_size):
                session.run(UNWIND_MERGE_FILES, {"batch": file_dicts[i:i + batch_size]})

            # Connect Repo to Files
            session.run("""
            MATCH (r:Repository {id: $repo_node_id})
            MATCH (f:File {repo_id: $repo_id})
            MERGE (r)-[:HAS_FILE]->(f)
            """, {"repo_node_id": f"repo:{graph.repo_id}", "repo_id": graph.repo_id})

            # 2. Ingest Modules
            mod_dicts = [m.model_dump() for m in graph.modules]
            for i in range(0, len(mod_dicts), batch_size):
                session.run(UNWIND_MERGE_MODULES, {"batch": mod_dicts[i:i + batch_size]})

            # 3. Ingest Classes
            cls_dicts = [c.model_dump() for c in graph.classes]
            for i in range(0, len(cls_dicts), batch_size):
                session.run(UNWIND_MERGE_CLASSES, {"batch": cls_dicts[i:i + batch_size]})

            # 4. Ingest Functions
            fn_dicts = [fn.model_dump() for fn in graph.functions]
            for i in range(0, len(fn_dicts), batch_size):
                session.run(UNWIND_MERGE_FUNCTIONS, {"batch": fn_dicts[i:i + batch_size]})

            # 5. Ingest External Symbols
            ext_dicts = [e.model_dump() for e in graph.external_symbols]
            for i in range(0, len(ext_dicts), batch_size):
                session.run(UNWIND_MERGE_EXTERNAL_SYMBOLS, {"batch": ext_dicts[i:i + batch_size]})

            # 6. Group edges by type and batch insert
            edges_by_type: Dict[str, List[Dict[str, Any]]] = {}
            for e in graph.edges:
                edges_by_type.setdefault(e.type, []).append({
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "properties": e.properties
                })

            for etype, edges in edges_by_type.items():
                query = CYPHER_CREATE_EDGE_TEMPLATE.format(rel_type=etype)
                for i in range(0, len(edges), batch_size):
                    session.run(query, {"batch": edges[i:i + batch_size]})

        logger.info(f"Ingested index for {graph.repo_id} into Neo4j successfully.")

    def apply_graph_diff(
        self,
        repo_id: str,
        graph: RepositoryGraph,
        added_files: List[str],
        modified_files: List[str],
        deleted_files: List[str]
    ) -> Dict[str, Any]:
        """
        Incrementally modifies Neo4j by only deleting obsolete nodes of modified/deleted files,
        and merging updated nodes/edges for added/modified files.
        """
        self._ensure_connected()
        self.register_repository(graph)

        changed_rels = list(set(modified_files + deleted_files))
        target_rels = set(added_files + modified_files)
        batch_size = 500

        with self.driver.session(database=self.database) as session:
            # 1. Prune nodes belonging to modified and deleted files
            if changed_rels:
                session.run("""
                MATCH (n {repo_id: $repo_id})
                WHERE n.rel_path IN $changed_rels
                DETACH DELETE n
                """, {"repo_id": repo_id, "changed_rels": changed_rels})

            # 2. Ingest only added and modified files
            file_dicts = [f.model_dump() for f in graph.files if f.rel_path in target_rels]
            for i in range(0, len(file_dicts), batch_size):
                session.run(UNWIND_MERGE_FILES, {"batch": file_dicts[i:i + batch_size]})

            # Connect Repo to new Files
            if file_dicts:
                session.run("""
                MATCH (r:Repository {id: $repo_node_id})
                MATCH (f:File {repo_id: $repo_id})
                WHERE f.rel_path IN $target_rels
                MERGE (r)-[:HAS_FILE]->(f)
                """, {
                    "repo_node_id": f"repo:{graph.repo_id}",
                    "repo_id": graph.repo_id,
                    "target_rels": list(target_rels)
                })

            # 3. Ingest Modules
            mod_dicts = [m.model_dump() for m in graph.modules if m.rel_path in target_rels]
            for i in range(0, len(mod_dicts), batch_size):
                session.run(UNWIND_MERGE_MODULES, {"batch": mod_dicts[i:i + batch_size]})

            # 4. Ingest Classes
            cls_dicts = [c.model_dump() for c in graph.classes if c.rel_path in target_rels]
            for i in range(0, len(cls_dicts), batch_size):
                session.run(UNWIND_MERGE_CLASSES, {"batch": cls_dicts[i:i + batch_size]})

            # 5. Ingest Functions
            fn_dicts = [fn.model_dump() for fn in graph.functions if fn.rel_path in target_rels]
            for i in range(0, len(fn_dicts), batch_size):
                session.run(UNWIND_MERGE_FUNCTIONS, {"batch": fn_dicts[i:i + batch_size]})

            # 6. Ingest External Symbols
            ext_dicts = [e.model_dump() for e in graph.external_symbols]
            for i in range(0, len(ext_dicts), batch_size):
                session.run(UNWIND_MERGE_EXTERNAL_SYMBOLS, {"batch": ext_dicts[i:i + batch_size]})

            # 7. Ingest Edges for updated nodes
            edges_by_type: Dict[str, List[Dict[str, Any]]] = {}
            for e in graph.edges:
                edges_by_type.setdefault(e.type, []).append({
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "properties": e.properties
                })

            for etype, edges in edges_by_type.items():
                query = CYPHER_CREATE_EDGE_TEMPLATE.format(rel_type=etype)
                for i in range(0, len(edges), batch_size):
                    session.run(query, {"batch": edges[i:i + batch_size]})

        logger.info(f"Incrementally applied Graph Diff to Neo4j for {repo_id}: {len(file_dicts)} files merged.")
        return {
            "status": "incremental_applied",
            "pruned_files_count": len(changed_rels),
            "merged_files_count": len(file_dicts)
        }

    def get_graph_statistics(self, repo_id: str) -> Dict[str, Any]:
        self._ensure_connected()
        cypher = """
        MATCH (n)
        WHERE n.repo_id = $repo_id OR n.id = $repo_node_id
        WITH labels(n)[0] AS type, count(n) AS cnt
        RETURN type, cnt
        """
        edge_cypher = """
        MATCH (n)-[r]->()
        WHERE n.repo_id = $repo_id OR n.id = $repo_node_id
        WITH type(r) AS rel_type, count(r) AS cnt
        RETURN rel_type, cnt
        """
        node_counts = {}
        edge_counts = {}
        with self.driver.session(database=self.database) as session:
            for rec in session.run(cypher, {"repo_id": repo_id, "repo_node_id": f"repo:{repo_id}"}):
                node_counts[rec["type"]] = rec["cnt"]
            for rec in session.run(edge_cypher, {"repo_id": repo_id, "repo_node_id": f"repo:{repo_id}"}):
                edge_counts[rec["rel_type"]] = rec["cnt"]

        return {
            "repository_id": repo_id,
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(edge_counts.values()),
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts
        }

    def get_symbol(self, symbol_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        cypher = "MATCH (n {id: $id}) RETURN n, labels(n)[0] AS type"
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"id": symbol_id})
            rec = res.single()
            if rec:
                data = dict(rec["n"])
                data["type"] = rec["type"]
                return data
        return None

    def search_symbols(self, repo_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        self._ensure_connected()
        results = []
        with self.driver.session(database=self.database) as session:
            res = session.run(SEARCH_SYMBOLS_CYPHER, {"repo_id": repo_id, "query": query, "limit": limit})
            for rec in res:
                results.append(dict(rec))
        return results

    def get_file_symbols(self, repo_id: str, rel_path: str) -> Dict[str, Any]:
        self._ensure_connected()
        cypher = """
        MATCH (n)
        WHERE n.repo_id = $repo_id AND n.rel_path = $rel_path
        RETURN n, labels(n)[0] AS type
        """
        classes = []
        functions = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"repo_id": repo_id, "rel_path": rel_path})
            for rec in res:
                data = dict(rec["n"])
                if rec["type"] == "Class":
                    classes.append(data)
                elif rec["type"] == "Function":
                    functions.append(data)
        return {"rel_path": rel_path, "classes": classes, "functions": functions}

    def get_incoming_relationships(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        self._ensure_connected()
        cypher = """
        MATCH (source)-[r]->(target {id: $symbol_id})
        RETURN source.id AS source_id, properties(source) AS source_data,
               type(r) AS type, properties(r) AS properties
        LIMIT $limit
        """
        results = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"symbol_id": symbol_id, "limit": limit})
            for rec in res:
                results.append(dict(rec))
        return results

    def get_outgoing_relationships(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        self._ensure_connected()
        cypher = """
        MATCH (source {id: $symbol_id})-[r]->(target)
        RETURN target.id AS target_id, properties(target) AS target_data,
               type(r) AS type, properties(r) AS properties
        LIMIT $limit
        """
        results = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"symbol_id": symbol_id, "limit": limit})
            for rec in res:
                results.append(dict(rec))
        return results

    def get_callers(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        self._ensure_connected()
        results = []
        with self.driver.session(database=self.database) as session:
            res = session.run(CALLERS_CYPHER, {"symbol_id": symbol_id, "limit": limit})
            for rec in res:
                results.append(dict(rec))
        return results

    def get_callees(self, symbol_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        self._ensure_connected()
        results = []
        with self.driver.session(database=self.database) as session:
            res = session.run(CALLEES_CYPHER, {"symbol_id": symbol_id, "limit": limit})
            for rec in res:
                results.append(dict(rec))
        return results

    def get_import_chain(self, repo_id: str, file_or_module: str, max_depth: int = 3) -> Dict[str, Any]:
        self._ensure_connected()
        cypher = f"""
        MATCH path = (start {{id: $start_id}})-[:IMPORTS*1..{max_depth}]->(target)
        RETURN nodes(path) AS ns, relationships(path) AS rs
        LIMIT 50
        """
        nodes = {}
        edges = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"start_id": file_or_module})
            for rec in res:
                for n in rec["ns"]:
                    nodes[n["id"]] = dict(n)
                for r in rec["rs"]:
                    edges.append({
                        "source": r.start_node["id"],
                        "target": r.end_node["id"],
                        "type": r.type,
                        "properties": dict(r)
                    })
        return {"nodes": list(nodes.values()), "edges": edges}

    def get_inheritance_tree(self, repo_id: str, class_name_or_id: str) -> Dict[str, Any]:
        self._ensure_connected()
        cypher = """
        MATCH (c:Class)
        WHERE c.id = $ident OR c.name = $ident
        OPTIONAL MATCH path = (c)-[:INHERITS*1..3]->(ancestor)
        RETURN c, nodes(path) AS ns, relationships(path) AS rs
        """
        nodes = {}
        edges = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"ident": class_name_or_id})
            for rec in res:
                c = rec["c"]
                if c:
                    nodes[c["id"]] = dict(c)
                if rec["ns"]:
                    for n in rec["ns"]:
                        nodes[n["id"]] = dict(n)
                if rec["rs"]:
                    for r in rec["rs"]:
                        edges.append({
                            "source": r.start_node["id"],
                            "target": r.end_node["id"],
                            "type": r.type
                        })
        return {"nodes": list(nodes.values()), "edges": edges}

    def trace_call_path(self, source_id: str, target_id: str, max_depth: int = 4) -> List[Dict[str, Any]]:
        self._ensure_connected()
        cypher = f"""
        MATCH p = (s:Function {{id: $source_id}})-[:CALLS*1..{max_depth}]->(t {{id: $target_id}})
        RETURN [n in nodes(p) | properties(n)] AS node_props,
               [r in relationships(p) | properties(r)] AS rel_props
        LIMIT 5
        """
        paths = []
        with self.driver.session(database=self.database) as session:
            res = session.run(cypher, {"source_id": source_id, "target_id": target_id})
            for rec in res:
                node_list = rec["node_props"]
                rel_list = rec["rel_props"]
                steps = []
                for i in range(len(rel_list)):
                    steps.append({
                        "step": i + 1,
                        "from_data": node_list[i],
                        "to_data": node_list[i + 1],
                        "call_line": rel_list[i].get("line"),
                        "call_expr": rel_list[i].get("call_expr")
                    })
                paths.append({
                    "nodes": [n["id"] for n in node_list],
                    "steps": steps
                })
        return paths

    def get_related_symbols(self, symbol_id: str, max_hops: int = 2, limit: int = 50) -> Dict[str, Any]:
        return self.retrieve_multi_hop_context(
            repo_id="",
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
        self._ensure_connected()
        nodes = {}
        edges = []
        with self.driver.session(database=self.database) as session:
            # First fetch seed nodes themselves to ensure presence even if isolated
            seed_res = session.run(
                "MATCH (seed) WHERE seed.id IN $seed_ids RETURN seed, labels(seed)[0] AS type",
                {"seed_ids": seed_symbol_ids}
            )
            for rec in seed_res:
                s_dict = dict(rec["seed"])
                s_dict["type"] = rec["type"]
                nodes[s_dict["id"]] = s_dict

            # Multi-hop expansion excluding Repository root node and HAS_FILE edge star-bursts
            cypher = f"""
            MATCH (seed)
            WHERE seed.id IN $seed_ids
            MATCH path = (seed)-[r*1..{max_hops}]-(neighbor)
            WHERE ALL(n IN nodes(path) WHERE NOT n:Repository)
              AND ALL(rel IN relationships(path) WHERE type(rel) <> 'HAS_FILE')
            WITH nodes(path) AS ns, relationships(path) AS rs
            RETURN ns, rs
            LIMIT $max_nodes
            """
            res = session.run(cypher, {"seed_ids": seed_symbol_ids, "max_nodes": max_nodes})
            for rec in res:
                for n in rec["ns"]:
                    d = dict(n)
                    if hasattr(n, "labels"):
                        labels = list(n.labels)
                        d["type"] = labels[0] if labels else "Unknown"
                    nodes[n["id"]] = d
                for r in rec["rs"]:
                    edges.append({
                        "source": r.start_node["id"],
                        "target": r.end_node["id"],
                        "type": r.type,
                        "properties": dict(r)
                    })
        return {"nodes": list(nodes.values()), "edges": edges}

    def get_subgraph(
        self,
        repo_id: str,
        view_mode: str = "architecture",
        focus_symbol_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 80
    ) -> Dict[str, Any]:
        self._ensure_connected()

        if focus_symbol_id:
            return self.retrieve_multi_hop_context(
                repo_id=repo_id,
                seed_symbol_ids=[focus_symbol_id],
                max_hops=depth,
                max_nodes=limit
            )

        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        with self.driver.session(database=self.database) as session:
            if view_mode == "architecture":
                # Class & Function call, inheritance, definitions and exceptions graph
                cypher = """
                MATCH (source)-[r:CALLS|INHERITS|DEFINES|HANDLES|RAISES]->(target)
                WHERE (source:Class OR source:Function)
                  AND (target:Class OR target:Function OR target:ExternalSymbol)
                  AND (source.repo_id = $repo_id OR source.repo_id IS NULL)
                  AND (target.repo_id = $repo_id OR target.repo_id IS NULL)
                RETURN source, labels(source)[0] AS source_type,
                       r, type(r) AS rel_type,
                       target, labels(target)[0] AS target_type
                LIMIT $limit
                """
            elif view_mode == "modules":
                # High-level module and file import graph
                cypher = """
                MATCH (source)-[r:IMPORTS]->(target)
                WHERE (source:File OR source:Module)
                  AND (source.repo_id = $repo_id OR source.repo_id IS NULL)
                  AND (target.repo_id = $repo_id OR target.repo_id IS NULL)
                RETURN source, labels(source)[0] AS source_type,
                       r, type(r) AS rel_type,
                       target, labels(target)[0] AS target_type
                LIMIT $limit
                """
            elif view_mode == "hierarchy":
                # File contains Class and Class defines Function
                cypher = """
                MATCH (source)-[r:CONTAINS|DEFINES]->(target)
                WHERE (source:File OR source:Class)
                  AND (target:Class OR target:Function)
                  AND (source.repo_id = $repo_id OR source.repo_id IS NULL)
                  AND (target.repo_id = $repo_id OR target.repo_id IS NULL)
                RETURN source, labels(source)[0] AS source_type,
                       r, type(r) AS rel_type,
                       target, labels(target)[0] AS target_type
                LIMIT $limit
                """
            else:  # "all"
                cypher = """
                MATCH (source)-[r]->(target)
                WHERE type(r) <> 'HAS_FILE' AND NOT source:Repository AND NOT target:Repository
                  AND (source.repo_id = $repo_id OR source.repo_id IS NULL)
                  AND (target.repo_id = $repo_id OR target.repo_id IS NULL)
                RETURN source, labels(source)[0] AS source_type,
                       r, type(r) AS rel_type,
                       target, labels(target)[0] AS target_type
                LIMIT $limit
                """

            res = session.run(cypher, {"repo_id": repo_id, "limit": limit})
            for rec in res:
                s_node = dict(rec["source"])
                s_node["type"] = rec["source_type"]
                nodes[s_node["id"]] = s_node

                t_node = dict(rec["target"])
                t_node["type"] = rec["target_type"]
                nodes[t_node["id"]] = t_node

                r = rec["r"]
                edges.append({
                    "source": s_node["id"],
                    "target": t_node["id"],
                    "type": rec["rel_type"],
                    "properties": dict(r) if r else {}
                })

        return {"nodes": list(nodes.values()), "edges": edges}

    def delete_repository_index(self, repo_id: str) -> None:
        self._ensure_connected()
        cypher = """
        MATCH (n)
        WHERE n.repo_id = $repo_id OR n.id = $repo_node_id
        DETACH DELETE n
        """
        with self.driver.session(database=self.database) as session:
            session.run(cypher, {"repo_id": repo_id, "repo_node_id": f"repo:{repo_id}"})
        logger.info(f"Purged repository index for {repo_id} from Neo4j.")

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self._connected = False
            logger.info("Closed Neo4j driver connection.")
