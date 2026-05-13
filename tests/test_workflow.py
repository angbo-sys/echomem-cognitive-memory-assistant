from __future__ import annotations

import subprocess
import sys
import unittest


class TestWorkflowScript(unittest.TestCase):
    def test_help_exposes_optional_secret_scan(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/workflow.py", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--include-secret-scan", result.stdout)
        self.assertIn("--strict-secrets", result.stdout)


if __name__ == "__main__":
    unittest.main()
