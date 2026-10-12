# Architecture Blueprint: Meta-Graph Codebase Navigator

## Executive Overview
**Meta-Graph Codebase Navigator** is a local-first, graph-native code intelligence platform. Unlike naive vector similarity search (which retrieves disconnected code chunks based on semantic word embeddings), Meta-Graph builds a deterministic **Code Knowledge Graph** using Python's native `ast` module and performs bounded **multi-hop structural traversal** across call chains, inheritance hierarchies, and exception pathways.

---

## 1. High-Level System Architecture

```
┌────────────────────────────────────────────────────────┐
│             Target Python Repository                   │
│          E:\MM Office\Agent Chess (Read-Only)          │
└──────────────────────────┬─────────────────────────────┘
                           │ (Safe Filesystem Scan)
                           ▼
┌────────────────────────────────────────────────────────┐
│               Static AST Analyzer Engine                │
│  - scanner.py (ignores .venv, git, node_modules)       │
│  - ast_parser.py (pure AST traversal, no code exec)    │
│  - symbol_resolver.py (cross-file import/call mapping) │
│  - incremental.py (SHA-256 change detection)           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Graph Storage Layer                  │
│       BaseGraphStore (Unified Storage Interface)       │
│       ├── Neo4jStore (Official driver, batched UNWIND) │
│       └── NetworkXStore (In-memory & disk persistence) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Retrieval & Grounding Engine             │
│  - planner.py (bounded query planning)                 │
│  - graph_retriever.py (multi-hop traversal, paths)     │
│  - lexical_retriever.py (symbol token matching)        │
│  - evidence_validator.py (authentic source extractor)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            LangGraph Agent State Machine               │
│  Validate -> Plan -> GraphQuery -> Evidence -> Groq    │
│  Groq LLM Engine (qwen/qwen3.8-27b, backoff & OTPM)    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           FastAPI REST API & React Frontend            │
│  - FastAPI Endpoints (Health, Repos, Graph, Assistant) │
│  - React 19 + TypeScript + Vite + React Flow           │
└────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Repository Scanner (`scanner.py`)
- Strictly treats the target repository as **read-only**. Never executes `setup.py`, never imports target code.
- Recursively walks directory trees while excluding `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `dist`, `build`.
- Respects `.gitignore` rules using `pathspec`.
- Enforces boundary protection: prevents symlink cycles and directory traversal outside the configured root.
- Enforces configurable limits (`MAX_REPOSITORY_FILES = 1000`, `MAX_FILE_SIZE_BYTES = 1MB`).

### 2.2 AST Parser (`ast_parser.py`)
- Uses Python's built-in `ast` module for deterministic static analysis.
- Extracts `FileNode`, `ModuleNode`, `ClassNode`, `FunctionNode`, and `ExternalSymbolNode`.
- Captures:
  - Exact start and end line ranges.
  - Parameters, decorators, async flags, return annotations.
  - Exception handling (`try / except / finally`), identifying exact exceptions handled (e.g. `APIError`, `ValueError`).
  - Explicit `raise` statements.
  - Raw function call records (`caller_id`, `receiver`, `method_or_func`, line number, try/except context).

### 2.3 Deterministic Symbol Resolution (`symbol_resolver.py`)
- Builds global symbol tables and per-file import maps.
- Resolves class inheritance (`(Class)-[:INHERITS]->(BaseClass)`).
- Resolves function calls:
  - Dispatches `self.method()` to current class method definitions.
  - Dispatches imported functions to their target module and function nodes.
  - Captures external SDK calls (e.g. `client.chat.completions.create`) as `ExternalSymbol`.
- Prevents ID collisions across different modules and classes using canonical IDs: `{repo_id}:func:{rel_path}:{qualified_name}`.

### 2.4 Graph Storage Abstraction (`BaseGraphStore`)
- Decouples retrieval logic from the underlying graph database.
- **Neo4jStore**: Production implementation using official `neo4j` driver, parameterized Cypher, UNWIND batch insertion, uniqueness constraints.
- **NetworkXStore**: In-memory and JSON-persisted fallback. Allows instant local development and offline test execution without requiring a live Neo4j daemon.
- Never silently switches without diagnostics: reports live status of both backends in `/api/system/status`.

### 2.5 LangGraph Orchestration State Machine (`workflow.py`)
The retrieval and generation workflow executes through 6 sequential nodes:
1. `validate_question`: Checks query length, validates repository selection against registered paths.
2. `plan_retrieval`: Extracts identifiers, detects exception/retry/tournament intents, sets hop bounds (`max_hops=3`, `max_nodes=50`).
3. `execute_graph_queries`: Traverses multi-hop neighborhoods, mines directed call paths (`trace_call_path`), and extracts exception relationships (`HANDLES`, `RAISES`).
4. `retrieve_source_evidence`: Extracts verified source lines from target files, computing SHA-256 hashes.
5. `generate_answer`: Formats structural evidence into strict prompts for Groq LLM with exponential backoff on HTTP 429.
6. `validate_citations`: Validates all citations against actual disk files and line ranges, rejecting hallucinated references.

---

## 3. Security Architecture
1. **Repository Isolation**: Target repository files are accessed strictly via `resolve_safe_subpath()` which throws `PathTraversalError` if a path escapes the repository root.
2. **Zero Code Execution**: Static AST parsing analyzes code structure without executing or importing any target code.
3. **Secret Redaction**: Structured logging filter (`SensitiveDataFilter`) automatically sanitizes `gsk_*` tokens, passwords, and authorization headers.
4. **Parameterized Cypher**: All Neo4j queries use parameterized inputs to prevent Cypher injection.
5. **Prompt Injection Defense**: Repository source snippets and docstrings are treated strictly as passive data, enclosed in unambiguous delimiter blocks with explicit system policies forbidding instruction override.
