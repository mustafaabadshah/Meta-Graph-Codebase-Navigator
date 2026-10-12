"""
Parameterized Cypher query templates for safe, bounded graph operations.
Never interpolate user-supplied strings directly into Cypher statements.
"""

UNWIND_MERGE_FILES = """
UNWIND $batch AS item
MERGE (f:File {id: item.id})
SET f.repo_id = item.repo_id,
    f.rel_path = item.rel_path,
    f.module_name = item.module_name,
    f.line_count = item.line_count,
    f.file_hash = item.file_hash,
    f.docstring = item.docstring,
    f.parse_status = item.parse_status,
    f.parse_error = item.parse_error
"""

UNWIND_MERGE_MODULES = """
UNWIND $batch AS item
MERGE (m:Module {id: item.id})
SET m.repo_id = item.repo_id,
    m.name = item.name,
    m.rel_path = item.rel_path
"""

UNWIND_MERGE_CLASSES = """
UNWIND $batch AS item
MERGE (c:Class {id: item.id})
SET c.repo_id = item.repo_id,
    c.name = item.name,
    c.qualified_name = item.qualified_name,
    c.rel_path = item.rel_path,
    c.start_line = item.start_line,
    c.end_line = item.end_line,
    c.docstring = item.docstring,
    c.bases = item.bases,
    c.decorators = item.decorators,
    c.is_abstract = item.is_abstract
"""

UNWIND_MERGE_FUNCTIONS = """
UNWIND $batch AS item
MERGE (fn:Function {id: item.id})
SET fn.repo_id = item.repo_id,
    fn.name = item.name,
    fn.qualified_name = item.qualified_name,
    fn.rel_path = item.rel_path,
    fn.start_line = item.start_line,
    fn.end_line = item.end_line,
    fn.docstring = item.docstring,
    fn.is_async = item.is_async,
    fn.is_method = item.is_method,
    fn.parent_class = item.parent_class,
    fn.parameters = item.parameters,
    fn.return_annotation = item.return_annotation,
    fn.decorators = item.decorators,
    fn.raises = item.raises,
    fn.handles = item.handles
"""

UNWIND_MERGE_EXTERNAL_SYMBOLS = """
UNWIND $batch AS item
MERGE (e:ExternalSymbol {id: item.id})
SET e.name = item.name,
    e.category = item.category,
    e.repo_id = item.repo_id
"""

UNWIND_MERGE_EDGES = """
UNWIND $batch AS edge
MATCH (s {id: edge.source_id})
MATCH (t {id: edge.target_id})
CALL apoc.create.relationship(s, edge.type, edge.properties, t) YIELD rel
RETURN count(rel)
"""

# Native edge creation
CYPHER_CREATE_EDGE_TEMPLATE = """
UNWIND $batch AS edge
MATCH (s {{id: edge.source_id}})
MATCH (t {{id: edge.target_id}})
CREATE (s)-[r:{rel_type}]->(t)
SET r += edge.properties
"""

SEARCH_SYMBOLS_CYPHER = """
MATCH (n)
WHERE (n:Function OR n:Class OR n:Module)
  AND n.repo_id = $repo_id
  AND (toLower(n.name) CONTAINS toLower($query) OR toLower(n.qualified_name) CONTAINS toLower($query))
RETURN n.id AS id,
       labels(n)[0] AS type,
       n.name AS name,
       n.qualified_name AS qualified_name,
       n.rel_path AS rel_path,
       n.start_line AS start_line,
       n.end_line AS end_line,
       n.docstring AS docstring
LIMIT $limit
"""

CALLERS_CYPHER = """
MATCH (caller:Function)-[r:CALLS]->(target {id: $symbol_id})
RETURN caller.id AS id,
       caller.name AS name,
       caller.qualified_name AS qualified_name,
       caller.rel_path AS rel_path,
       caller.start_line AS start_line,
       caller.end_line AS end_line,
       r.line AS call_line,
       r.call_expr AS call_expr,
       r.is_in_try AS is_in_try,
       r.is_in_except AS is_in_except
LIMIT $limit
"""

CALLEES_CYPHER = """
MATCH (source {id: $symbol_id})-[r:CALLS]->(callee)
RETURN callee.id AS id,
       labels(callee)[0] AS type,
       callee.name AS name,
       callee.qualified_name AS qualified_name,
       callee.rel_path AS rel_path,
       callee.start_line AS start_line,
       callee.end_line AS end_line,
       r.line AS call_line,
       r.call_expr AS call_expr,
       r.is_in_try AS is_in_try,
       r.is_in_except AS is_in_except
LIMIT $limit
"""

MULTI_HOP_NEIGHBORHOOD_CYPHER = """
MATCH (seed)
WHERE seed.id IN $seed_ids
MATCH path = (seed)-[r*1..{max_hops}]-(neighbor)
WHERE ALL(n IN nodes(path) WHERE n.repo_id = $repo_id OR n:ExternalSymbol)
WITH nodes(path) AS ns, relationships(path) AS rs
UNWIND ns AS node
WITH DISTINCT node, rs
LIMIT $max_nodes
RETURN node, rs
"""
