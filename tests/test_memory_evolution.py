from __future__ import annotations

import tempfile
import unittest

from memory import LongTermMemory


class TestMemoryEvolution(unittest.TestCase):
    def test_conflict_update_deprecates_old_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            first = ltm.detect_conflict_and_update(
                user_id="u1",
                field="preferred_style",
                old_value=None,
                new_value="详细",
                trigger="seed",
                confidence=0.9,
            )
            second = ltm.detect_conflict_and_update(
                user_id="u1",
                field="preferred_style",
                old_value="详细",
                new_value="简洁",
                trigger="change",
                confidence=0.95,
            )

            self.assertFalse(first["conflict"])
            self.assertTrue(second["conflict"])
            self.assertIsNotNone(second["deprecated_memory_id"])

            old_mem = ltm.get_memory(second["deprecated_memory_id"])
            self.assertIsNotNone(old_mem)
            self.assertEqual(old_mem["status"], "deprecated")

    def test_conflict_lookup_is_scoped_before_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            first = ltm.detect_conflict_and_update(
                user_id="target_user",
                field="learning_goal",
                old_value=None,
                new_value="英语",
                trigger="seed",
                confidence=0.8,
            )
            for idx in range(650):
                ltm.detect_conflict_and_update(
                    user_id=f"other_user_{idx}",
                    field="learning_goal",
                    old_value=None,
                    new_value=f"目标{idx}",
                    trigger="noise",
                    confidence=0.7,
                )

            second = ltm.detect_conflict_and_update(
                user_id="target_user",
                field="learning_goal",
                old_value="英语",
                new_value="数学",
                trigger="change",
                confidence=0.9,
            )

            self.assertTrue(second["conflict"])
            self.assertEqual(second["deprecated_memory_id"], first["new_memory_id"])
            target_rows = ltm.list_memories(
                status="active",
                mtype="profile_field",
                user_id="target_user",
                limit=10,
            )
            self.assertEqual(len(target_rows), 1)


if __name__ == "__main__":
    unittest.main()
