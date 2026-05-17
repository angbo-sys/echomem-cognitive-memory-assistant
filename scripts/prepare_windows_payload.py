from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = ROOT / ".build" / "windows_payload" / "payload"

INCLUDE_DIRS = [
    "agent",
    "config",
    "llm",
    "memory",
    "profile",
    "ui",
]
INCLUDE_FILES = [
    ".env.example",
    "README.md",
    "README.en.md",
]
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "chroma_db",
    ".mem0_faiss",
    ".context",
    ".deps",
    "node_modules",
}
EXCLUDED_FILE_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pyc",
    ".pyo",
    ".log",
}
EXCLUDED_FILE_NAMES = {
    ".env",
    ".DS_Store",
}


def _ignore(_: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        if name in EXCLUDED_DIR_NAMES or name in EXCLUDED_FILE_NAMES:
            ignored.add(name)
        elif path.suffix in EXCLUDED_FILE_SUFFIXES:
            ignored.add(name)
    return ignored


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the files embedded in the Windows exe.")
    parser.add_argument(
        "--include-env",
        action="store_true",
        help="Include .env in the payload. Use only for private local testing.",
    )
    args = parser.parse_args()

    if PAYLOAD_ROOT.exists():
        shutil.rmtree(PAYLOAD_ROOT)
    PAYLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    for dirname in INCLUDE_DIRS:
        src = ROOT / dirname
        if not src.exists():
            continue
        shutil.copytree(src, PAYLOAD_ROOT / dirname, ignore=_ignore)

    for filename in INCLUDE_FILES:
        src = ROOT / filename
        if src.exists():
            shutil.copy2(src, PAYLOAD_ROOT / filename)

    if args.include_env:
        env_file = ROOT / ".env"
        if env_file.exists():
            shutil.copy2(env_file, PAYLOAD_ROOT / ".env")
            print("[WARN] Included .env in the Windows payload for private local testing.")
        else:
            print("[WARN] --include-env was set, but .env was not found.")

    print(f"Prepared Windows payload: {PAYLOAD_ROOT}")
    if args.include_env:
        print("Excluded databases, caches, vector stores, and logs. .env was included by request.")
    else:
        print("Excluded local secrets, databases, caches, vector stores, and logs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
