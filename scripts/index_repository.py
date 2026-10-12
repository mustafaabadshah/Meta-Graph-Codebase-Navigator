import sys
import json
import argparse
from pathlib import Path

# Add backend to sys.path so app modules import cleanly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.parser.scanner import RepositoryScanner
from app.parser.ast_parser import AstParser
from app.parser.symbol_resolver import SymbolResolver
from app.utils.identifiers import make_repo_id
from app.graph import get_graph_store

def main():
    parser = argparse.ArgumentParser(description="Parse a local Python repository into an AST Code Knowledge Graph.")
    parser.add_argument("--repo-path", default=settings.DEFAULT_REPOSITORY_PATH, help="Path to repository")
    parser.add_argument("--repo-name", default="Agent Chess", help="Human-readable name of repository")
    parser.add_argument("--output", default=None, help="Optional output JSON path for graph data")
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    print(f"\n=======================================================")
    print(f"Meta-Graph Codebase Navigator - Static AST Analyzer")
    print(f"Target Repository : {repo_path}")
    print(f"=======================================================\n")

    if not repo_path.exists():
        print(f"Error: Target path does not exist: {repo_path}")
        sys.exit(1)

    repo_id = make_repo_id(str(repo_path), args.repo_name)
    scanner = RepositoryScanner(repo_path)
    commit = scanner.get_git_commit()

    print(f"[*] Scanning repository files...")
    files, warnings = scanner.scan()
    print(f"[+] Found {len(files)} Python source files.")
    if warnings:
        for w in warnings:
            print(f"    ! Warning: {w}")

    print(f"[*] Parsing AST for {len(files)} files...")
    parsed_files = []
    for f in files:
        parsed = AstParser.parse_file(repo_id, repo_path, f)
        parsed_files.append(parsed)

    print(f"[*] Running cross-file Symbol & Call Resolution...")
    resolver = SymbolResolver(repo_id, args.repo_name, str(repo_path), parsed_files)
    graph = resolver.resolve_all(commit_hash=commit, warnings=warnings)

    print(f"\n[+] Extraction Complete!")
    print(f"    - Files Indexed            : {len(graph.files)}")
    print(f"    - Modules Extracted        : {len(graph.modules)}")
    print(f"    - Classes Extracted        : {len(graph.classes)}")
    print(f"    - Functions/Methods        : {len(graph.functions)}")
    print(f"    - External Symbols         : {len(graph.external_symbols)}")
    print(f"    - Total Graph Edges        : {len(graph.edges)}")

    # Breakdown of edge types
    edge_counts = {}
    for e in graph.edges:
        edge_counts[e.type] = edge_counts.get(e.type, 0) + 1
    
    print("\n[+] Edge Breakdown:")
    for etype, count in sorted(edge_counts.items()):
        print(f"    - {etype:<15}: {count}")

    # Check for Groq agent and tournament symbols
    groq_symbols = [f for f in graph.functions if "groq" in f.rel_path.lower() or "groq" in f.name.lower()]
    print(f"\n[+] Discovered {len(groq_symbols)} Groq Agent functions/methods:")
    for sym in groq_symbols[:10]:
        print(f"    - {sym.qualified_name} (lines {sym.start_line}-{sym.end_line}) in {sym.rel_path}")

    # Output to file if requested or save to data/indexes/
    out_file = Path(args.output) if args.output else settings.INDEXES_DIR / f"{repo_id}_graph.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as out:
        out.write(graph.model_dump_json(indent=2))
    print(f"\n[+] Graph exported to: {out_file}")

    # Ingest into active graph store (Neo4j or NetworkX)
    store = get_graph_store()
    store.create_or_update_index(graph)
    print(f"[+] Ingested graph into active store: {store.__class__.__name__}\n")

if __name__ == "__main__":
    main()
