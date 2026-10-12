from typing import List, Dict, Any

NODE_LABELS = [
    "Repository",
    "File",
    "Module",
    "Class",
    "Function",
    "ExternalSymbol"
]

RELATIONSHIP_TYPES = [
    "HAS_FILE",
    "CONTAINS",
    "DEFINES",
    "IMPORTS",
    "CALLS",
    "INHERITS",
    "DECORATED_BY",
    "RAISES",
    "HANDLES",
    "REFERENCES",
    "TESTS"
]

NEO4J_CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (fn:Function) REQUIRE fn.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:ExternalSymbol) REQUIRE e.id IS UNIQUE"
]

NEO4J_INDEXES = [
    "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.repo_id, f.rel_path)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.repo_id, c.name)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.repo_id, c.qualified_name)",
    "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.repo_id, fn.name)",
    "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.repo_id, fn.qualified_name)",
    "CREATE INDEX IF NOT EXISTS FOR (m:Module) ON (m.repo_id, m.name)"
]
