from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    # Xiaomi MiMo style keys in code/config
    re.compile(r'api_key\s*=\s*"tp-[^"]+"'),
    re.compile(r"MIMO_API_KEY\s*=\s*tp-[A-Za-z0-9]+"),
    # Generic OpenAI/DeepSeek style secret keys
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    # AWS access key id style
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Bearer token literals in code/docs/env
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.IGNORECASE),
]
SKIP_FILES = {
    ".env",
}
ALLOWLIST_INLINE_TAG = "secret-scan: allow"


def load_allowlist_patterns(path: str | None) -> list[re.Pattern[str]]:
    if not path:
        return []
    allow_path = Path(path)
    if not allow_path.is_absolute():
        allow_path = ROOT / allow_path
    if not allow_path.exists():
        raise FileNotFoundError(f"Allowlist file not found: {allow_path}")
    patterns: list[re.Pattern[str]] = []
    for raw in allow_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(re.compile(line))
    return patterns


def line_allowed(line: str, allow_patterns: Iterable[re.Pattern[str]]) -> bool:
    if ALLOWLIST_INLINE_TAG in line:
        return True
    for allow_pat in allow_patterns:
        if allow_pat.search(line):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for obvious hardcoded secrets.")
    parser.add_argument(
        "--allow-settings-key",
        action="store_true",
        help="Allow API key in config/settings.toml for local testing only.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: do not allow any exception for config/settings.toml.",
    )
    parser.add_argument(
        "--allowlist-file",
        default="",
        help="Path to regex allowlist file. One regex per line; supports comments with '#'.",
    )
    args = parser.parse_args()
    allow_patterns = load_allowlist_patterns(args.allowlist_file)

    files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".toml", ".md", ".py", ".env"}]
    hit_count = 0
    for path in files:
        if path.name in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in PATTERNS:
            matched_line = None
            for line_no, line in enumerate(text.splitlines(), start=1):
                if not pat.search(line):
                    continue
                if line_allowed(line, allow_patterns):
                    continue
                matched_line = (line_no, line.strip())
                break
            if matched_line is None:
                continue
            if (
                not args.strict
                and args.allow_settings_key
                and path.as_posix().endswith("config/settings.toml")
            ):
                break
            line_no, line_text = matched_line
            print(f"[SECRET-HIT] {path}:{line_no} -> {line_text[:120]}")
            hit_count += 1
            break
    if hit_count:
        print(f"Found {hit_count} potential secret leak(s).")
        return 1
    print("No secret leak patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
