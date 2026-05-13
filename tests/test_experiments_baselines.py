from __future__ import annotations

import unittest

from experiments.run_baselines import proposed, run_one


class TestExperimentBaselines(unittest.TestCase):
    def test_proposed_uses_local_pipeline_without_copying_gold_labels(self) -> None:
        record = {
            "query": "我有点焦虑，怕这次考不好",
            "memory_bank": [
                {"id": "m1", "text": "用户情绪：焦虑", "timestamp": "2026-05-04T20:00:00"},
                {"id": "m2", "text": "用户希望分步骤解释", "timestamp": "2026-05-02T18:00:00"},
            ],
            "relevant_ids": ["m1", "m2"],
            "gold_preference": "copied_preference_would_be_bad",
            "gold_emotion": "copied_emotion_would_be_bad",
            "gold_persona_traits": ["copied_trait_would_be_bad"],
        }

        out = proposed(record)

        self.assertNotEqual(out["pred_preference"], record["gold_preference"])
        self.assertNotEqual(out["pred_emotion"], record["gold_emotion"])
        self.assertNotEqual(out["pred_persona_traits"], record["gold_persona_traits"])
        self.assertIn("m1", out["retrieved_ids"])
        self.assertTrue(out["response"])
        self.assertGreater(out["prompt_tokens"], 0)
        self.assertGreater(out["completion_tokens"], 0)

    def test_run_one_accepts_proposed_pipeline(self) -> None:
        rows = [
            {
                "query": "请给我简洁的复习建议",
                "memory_bank": [
                    {"id": "m1", "text": "用户偏好：回答简洁", "timestamp": "2026-05-01T10:00:00"},
                ],
                "relevant_ids": ["m1"],
                "gold_preference": "concise",
                "gold_emotion": "balanced",
                "gold_persona_traits": ["helpful", "concise"],
            }
        ]

        metrics = run_one("Proposed", proposed, rows, recall_k=1, price_per_1k=0.0)

        self.assertEqual(metrics["baseline"], "Proposed")
        self.assertEqual(metrics["num_samples"], 1)
        self.assertGreaterEqual(metrics["recall_at_k"], 0.0)


if __name__ == "__main__":
    unittest.main()
