from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_step(name: str, cmd: list[str], allow_fail: bool = False, env: dict[str, str] | None = None) -> int:
    print(f"\n== {name} ==")
    print(" ".join(cmd))
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    p = subprocess.run(cmd, cwd=ROOT, env=merged_env)
    if p.returncode != 0 and not allow_fail:
        print(f"[FAIL] {name}")
        return p.returncode
    print(f"[OK] {name}" if p.returncode == 0 else f"[WARN] {name} failed but allowed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Project self-iteration workflow runner.")
    parser.add_argument("--live-api", action="store_true", help="Run live MiMo API e2e checks.")
    parser.add_argument(
        "--include-secret-scan",
        action="store_true",
        help="Run optional secret scan. Disabled by default for normal delivery checks.",
    )
    parser.add_argument(
        "--strict-secrets",
        action="store_true",
        help="When --include-secret-scan is set, run secret scan in strict mode.",
    )
    parser.add_argument(
        "--secret-allowlist-file",
        default="",
        help="Optional regex allowlist file for secret scan.",
    )
    args = parser.parse_args()

    # Karpathy-guidelines style explicit targets.
    print("Targets:")
    print("1) Compile all python files")
    print("2) Run unit tests")
    print("3) Run baseline evaluation on sample data")
    print("4) (Optional) Run live API e2e demo")
    if args.include_secret_scan:
        print("Optional: Secret scan")

    excluded_compile_dirs = {".deps", "__pycache__"}
    python_files = [
        str(p)
        for p in ROOT.rglob("*.py")
        if not any(part in excluded_compile_dirs for part in p.relative_to(ROOT).parts)
    ]
    steps: list[tuple[str, list[str], bool, dict[str, str] | None]] = [
        ("Compile", [sys.executable, "-m", "py_compile", *python_files], False, None),
        ("Unit Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], False, None),
        (
            "Baseline Eval",
            [sys.executable, "experiments/run_baselines.py", "--data", "experiments/data/sample_eval.jsonl"],
            False,
            None,
        ),
    ]

    if args.include_secret_scan:
        secret_scan_cmd = [sys.executable, "scripts/secret_scan.py"]
        if args.strict_secrets:
            secret_scan_cmd.append("--strict")
        else:
            secret_scan_cmd.append("--allow-settings-key")
        if args.secret_allowlist_file:
            secret_scan_cmd.extend(["--allowlist-file", args.secret_allowlist_file])
        steps.append(("Secret Scan", secret_scan_cmd, False, None))

    if args.live_api:
        try:
            from config import load_config

            cfg = load_config()
            if not cfg.mimo.api_key:
                print("[FAIL] Live E2E requires non-empty MiMo API key in effective config.")
                print("Set MIMO_API_KEY in .env or shell environment, then rerun --live-api.")
                return 1
        except Exception as exc:
            print(f"[FAIL] Unable to load config for Live E2E precheck: {exc}")
            return 1
        steps.append(
            (
                "Live E2E",
                [sys.executable, "examples/orchestrator_e2e_example.py"],
                False,
                {"PYTHONPATH": str(ROOT)},
            )
        )

    for name, cmd, allow_fail, env in steps:
        code = run_step(name, cmd, allow_fail=allow_fail, env=env)
        if code != 0:
            return code

    print("\nWorkflow completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
