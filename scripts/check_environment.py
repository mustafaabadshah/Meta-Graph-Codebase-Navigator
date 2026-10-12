import sys
import subprocess
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

def main():
    print("=======================================================")
    print("Meta-Graph Codebase Navigator - Environment Diagnostic")
    print("=======================================================\n")

    # 1. Python version
    py_ver = sys.version_info
    print(f"[*] Python: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 11):
        print("    [!] Warning: Python 3.11+ is strongly recommended.")
    else:
        print("    [+] Python version compatible.")

    # 2. Node & npm
    for cmd in ["node", "npm", "git"]:
        try:
            res = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                print(f"[+] {cmd.capitalize()}: {res.stdout.strip()}")
            else:
                print(f"[!] {cmd.capitalize()}: Not found or error")
        except Exception:
            print(f"[!] {cmd.capitalize()}: Command unavailable")

    # 3. Settings & Configuration
    try:
        from app.core.config import settings
        from app.graph import get_backend_status
        print(f"\n[*] Loaded Settings from {settings.BASE_DIR}")
        print(f"    - Default Target Repo: {settings.DEFAULT_REPOSITORY_PATH}")
        print(f"    - Target Exists: {Path(settings.DEFAULT_REPOSITORY_PATH).exists()}")
        print(f"    - Groq API Key: {'Configured (Present)' if settings.GROQ_API_KEY else 'Missing (Deterministic mode active)'}")
        print(f"    - Groq Model: {settings.GROQ_MODEL}")

        status = get_backend_status()
        print(f"\n[*] Graph Storage Status:")
        print(f"    - Active Backend: {status['active_backend']}")
        print(f"    - Details: {status['active_status'].get('message')}")
        if status['neo4j_status'].get('troubleshooting'):
            print(f"    - Neo4j Info: {status['neo4j_status'].get('troubleshooting')}")
    except Exception as e:
        print(f"[!] Error inspecting settings: {e}")

    print("\n=======================================================")
    print("Diagnostic Complete.")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
