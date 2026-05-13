from __future__ import annotations

import unittest

from agent.tools import EmotionAnalyzer


class TestEmotionLabels(unittest.TestCase):
    def test_outputs_project_labels(self) -> None:
        analyzer = EmotionAnalyzer()
        labels = {
            analyzer.run("我有点焦虑")["label"],
            analyzer.run("我很有把握")["label"],
            analyzer.run("今天还不错")["label"],
        }
        allowed = {"positive", "neutral", "anxious", "frustrated", "confident"}
        self.assertTrue(labels.issubset(allowed))


if __name__ == "__main__":
    unittest.main()

