from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


APP_NAME = "EchoMem"
PAYLOAD_DIR_NAME = "payload"
RUNTIME_DIR_NAME = "runtime"


def _pyinstaller_import_hints() -> None:
    """Help PyInstaller discover runtime dependencies used by Streamlit app.py."""
    import chromadb  # noqa: F401
    import cognee  # noqa: F401
    import llama_cloud  # noqa: F401
    import mem0  # noqa: F401
    import pandas  # noqa: F401
    import streamlit  # noqa: F401
    from llama_index.core.memory import Memory  # noqa: F401


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _bundle_root() -> Path:
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parents[1]


def _exe_dir() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _user_home() -> Path:
    configured = os.environ.get("ECHOMEM_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data).resolve() / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def _copy_payload(payload_root: Path, runtime_root: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    for item in payload_root.iterdir():
        target = runtime_root / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _ensure_env_file(exe_dir: Path, runtime_root: Path) -> None:
    external_env = exe_dir / ".env"
    runtime_env = runtime_root / ".env"
    if external_env.exists():
        shutil.copy2(external_env, runtime_env)
        return
    if runtime_env.exists():
        return
    example = runtime_root / ".env.example"
    if example.exists():
        shutil.copy2(example, runtime_env)
    print("[WARN] .env was not found next to the exe.")
    print(f"[WARN] A template was created at: {runtime_env}")
    print("[WARN] Fill in your API keys, then restart EchoMem.")


def main() -> int:
    bundle_root = _bundle_root()
    payload_root = bundle_root / PAYLOAD_DIR_NAME
    if not payload_root.exists():
        payload_root = bundle_root

    runtime_root = _user_home() / RUNTIME_DIR_NAME
    _copy_payload(payload_root, runtime_root)
    _ensure_env_file(_exe_dir(), runtime_root)

    os.chdir(runtime_root)
    sys.path.insert(0, str(runtime_root))

    port = os.environ.get("ECHOMEM_PORT", "8501").strip() or "8501"
    app_path = runtime_root / "ui" / "app.py"
    if not app_path.exists():
        print(f"[ERROR] Streamlit app not found: {app_path}")
        return 1

    print("========================================")
    print("EchoMem Windows UI")
    print("========================================")
    print(f"Runtime: {runtime_root}")
    print(f"URL: http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    print()

    from streamlit.web import cli as streamlit_cli

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        port,
        "--server.headless",
        "false",
        "--global.developmentMode",
        "false",
    ]
    streamlit_cli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
