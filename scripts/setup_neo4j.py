import sys
import argparse
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import settings
from app.graph.neo4j_store import Neo4jStore
from app.graph.schema import NEO4J_CONSTRAINTS, NEO4J_INDEXES

def main():
    parser = argparse.ArgumentParser(description="Configure Neo4j Graph Database Schema & Indexes")
    parser.add_argument("--uri", default=settings.NEO4J_URI, help="Neo4j bolt/neo4j URI")
    parser.add_argument("--username", default=settings.NEO4J_USERNAME, help="Neo4j username")
    parser.add_argument("--password", default=settings.NEO4J_PASSWORD, help="Neo4j password")
    parser.add_argument("--database", default=settings.NEO4J_DATABASE, help="Neo4j database name")
    args = parser.parse_args()

    print(f"\n=======================================================")
    print(f"Meta-Graph Codebase Navigator - Neo4j Setup & Migration")
    print(f"Target URI: {args.uri} (DB: {args.database})")
    print(f"=======================================================\n")

    store = Neo4jStore(
        uri=args.uri,
        username=args.username,
        password=args.password,
        database=args.database
    )

    diag = store.check_connection()
    if not diag["connected"]:
        print(f"[!] ERROR: Could not connect to Neo4j.")
        print(f"    Details: {diag.get('message')}")
        print("\nTroubleshooting:")
        print("  1. If running locally with Docker:")
        print("     docker compose up -d neo4j")
        print("  2. If using Neo4j AuraDB Free cloud:")
        print("     Ensure NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io and passwords are set in .env")
        print("  3. Note: The navigator will automatically use its internal persistent NetworkX store")
        print("     if Neo4j is offline, so you can continue working without interruptions!\n")
        sys.exit(1)

    print("[+] Connection verified successfully!")
    print(f"[*] Applying {len(NEO4J_CONSTRAINTS)} uniqueness constraints...")
    with store.driver.session(database=args.database) as session:
        for c in NEO4J_CONSTRAINTS:
            print(f"    - {c}")
            session.run(c)

        print(f"\n[*] Applying {len(NEO4J_INDEXES)} performance indexes...")
        for idx in NEO4J_INDEXES:
            print(f"    - {idx}")
            session.run(idx)

    print("\n[+] Neo4j schema setup complete! Ready for high-performance graph ingestion.\n")
    store.close()

if __name__ == "__main__":
    main()
