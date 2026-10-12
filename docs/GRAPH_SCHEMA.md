# Graph Schema & Cypher Catalog: Meta-Graph Codebase Navigator

## 1. Node Labels & Properties

### `Repository`
Represents a registered codebase root.
- `id` (String, Unique): e.g. `repo:agent_chess`
- `name` (String): e.g. `Agent Chess`
- `path` (String): Canonical filesystem path
- `commit_hash` (String, Optional): Git commit SHA
- `indexed_at` (String): ISO 8601 timestamp
- `parser_version` (String): Parser release version

### `File`
Represents an individual Python source file.
- `id` (String, Unique): e.g. `agent_chess:file:backend/app/agents/groq_agent.py`
- `repo_id` (String): Identifier of owning repository
- `rel_path` (String): Normalized relative path with forward slashes
- `module_name` (String): Dot-separated module path
- `line_count` (Integer): Total physical line count
- `file_hash` (String): SHA-256 hash of file content
- `docstring` (String, Optional): Top-level module docstring
- `parse_status` (String): `ok`, `syntax_error`, or `unsupported`

### `Module`
Logical Python module.
- `id` (String, Unique): e.g. `agent_chess:module:backend.app.agents.groq_agent`
- `name` (String): Inferred module name
- `rel_path` (String): Backing source file path

### `Class`
Python class definition.
- `id` (String, Unique): e.g. `agent_chess:class:backend/app/agents/groq_agent.py:GroqChessAgent`
- `name` (String): Simple class name (e.g. `GroqChessAgent`)
- `qualified_name` (String): Lexically scoped name
- `start_line` (Integer): Starting line number (1-indexed)
- `end_line` (Integer): Ending line number
- `docstring` (String, Optional): Class docstring
- `bases` (List[String]): Base class names
- `decorators` (List[String]): Class decorators
- `is_abstract` (Boolean): True if inherits ABC or defines abstract methods

### `Function`
Function or class method definition.
- `id` (String, Unique): e.g. `agent_chess:func:backend/app/agents/groq_agent.py:GroqChessAgent.select_move`
- `name` (String): Function name (e.g. `select_move`)
- `qualified_name` (String): Scope path (e.g. `GroqChessAgent.select_move`)
- `start_line` (Integer): Starting line number
- `end_line` (Integer): Ending line number
- `is_async` (Boolean): True if declared `async def`
- `is_method` (Boolean): True if defined inside a class body
- `parent_class` (String, Optional): Owning class name
- `parameters` (List[String]): Argument list
- `raises` (List[String]): Exceptions explicitly raised in body
- `handles` (List[String]): Exceptions caught by `except` handlers

### `ExternalSymbol`
External library symbol, exception, or framework construct.
- `id` (String, Unique): e.g. `ext:groq.APIError`
- `name` (String): Symbol name
- `category` (String): `library`, `exception`, or `class`

---

## 2. Relationship Types

| Relationship | Source Node | Target Node | Key Properties |
|---|---|---|---|
| `HAS_FILE` | `Repository` | `File` | - |
| `CONTAINS` | `File` | `Module` | `module` |
| `DEFINES` | `File` | `Class` / `Function` | `line` |
| `CONTAINS` | `Class` | `Function` (Method) | `line` |
| `IMPORTS` | `File` | `Module` / `ExternalSymbol` | `line`, `imported_name`, `alias` |
| `INHERITS` | `Class` | `Class` / `ExternalSymbol` | `base_name`, `is_resolved` |
| `CALLS` | `Function` | `Function` / `ExternalSymbol` | `line`, `call_expr`, `is_in_try`, `is_in_except`, `confidence` |
| `HANDLES` | `Function` | `ExternalSymbol` | `line`, `exception` |
| `RAISES` | `Function` | `ExternalSymbol` | `line`, `exception` |

---

## 3. Schema Constraints & Indexes

```cypher
// Uniqueness Constraints
CREATE CONSTRAINT FOR (r:Repository) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT FOR (f:File) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT FOR (m:Module) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT FOR (c:Class) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT FOR (fn:Function) REQUIRE fn.id IS UNIQUE;
CREATE CONSTRAINT FOR (e:ExternalSymbol) REQUIRE e.id IS UNIQUE;

// Performance Indexes
CREATE INDEX FOR (f:File) ON (f.repo_id, f.rel_path);
CREATE INDEX FOR (c:Class) ON (c.repo_id, c.name);
CREATE INDEX FOR (c:Class) ON (c.repo_id, c.qualified_name);
CREATE INDEX FOR (fn:Function) ON (fn.repo_id, fn.name);
CREATE INDEX FOR (fn:Function) ON (fn.repo_id, fn.qualified_name);
```

---

## 4. Primary Cypher Query Templates

### Bounded Multi-Hop Neighborhood Expansion
```cypher
MATCH (seed)
WHERE seed.id IN $seed_ids
MATCH path = (seed)-[r*1..3]-(neighbor)
WHERE ALL(n IN nodes(path) WHERE n.repo_id = $repo_id OR n:ExternalSymbol)
WITH nodes(path) AS ns, relationships(path) AS rs
RETURN ns, rs
LIMIT 60;
```

### Directed Call Path Tracing
```cypher
MATCH p = (s:Function {id: $source_id})-[:CALLS*1..4]->(t {id: $target_id})
RETURN [n in nodes(p) | properties(n)] AS node_props,
       [r in relationships(p) | properties(r)] AS rel_props
LIMIT 5;
```

### Exception & Retry Pathway Detection
```cypher
MATCH (fn:Function)-[h:HANDLES]->(exc:ExternalSymbol)
WHERE fn.repo_id = $repo_id
RETURN fn.qualified_name AS function_name,
       fn.rel_path AS file,
       h.line AS handler_line,
       exc.name AS exception_type;
```
