import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from motion_generation import ingest, load_job, pack, prepare, review, review_cycle, select_attempt, default_walk


class GenerationTests(unittest.TestCase):
    def test_both_passing_guides_lift_the_swing_leg_forward(self):
        frames = default_walk()["actions"][0]["frames"]
        for index, swing, stance in ((2, "far", "near"), (6, "near", "far")):
            guide = frames[index]["diagram"]
            self.assertGreater(guide[swing][0], guide[stance][0])
            self.assertLess(guide[swing][1], guide[stance][1])
            self.assertGreater(guide[swing+"Knee"][0], guide[stance+"Knee"][0])

    def test_candidate_does_not_replace_selected_and_explicit_rollback_works(self):
        ingest(self.job, "attack-000", self.image)
        review(self.job, "attack-000", "accept", "first pose checked", "agent")
        ingest(self.job, "attack-000", self.image, offset=(1, 0), candidate_only=True)
        ingest(self.job, "attack-000", self.image, offset=(1, 0), candidate_only=True)
        self.assertEqual(len(load_job(self.job)["frames"]["attack-000"]["attempts"]), 2)
        self.assertEqual(load_job(self.job)["frames"]["attack-000"]["selected"], 0)
        self.assertEqual(select_attempt(self.job, "attack-000", 1)["offset"], [1, 0])
        self.assertIsNone(select_attempt(self.job, "attack-000", 1)["review"])
        self.assertEqual(select_attempt(self.job, "attack-000", 0)["review"]["verdict"], "accept")
        review(self.job, "attack-000", "reject", "candidate pose wrong", "agent", attempt_index=1)
        self.assertEqual(load_job(self.job)["frames"]["attack-000"]["selected"], 0)
        self.assertEqual(load_job(self.job)["frames"]["attack-000"]["attempts"][0]["review"]["verdict"], "accept")

    def test_cycle_review_requires_frame_reviews_and_new_frame_invalidates_it(self):
        for fid in ("attack-000", "attack-001"):
            ingest(self.job, fid, self.image)
        with self.assertRaisesRegex(ValueError, "逐帧审查"):
            review_cycle(self.job, "attack", "accept", "actual playback checked", "agent")
        for fid in ("attack-000", "attack-001"):
            review(self.job, fid, "accept", "pose checked", "agent")
        review_cycle(self.job, "attack", "accept", "actual playback checked", "agent")
        pack(self.job, self.root / "cycle")
        report = json.loads((self.root / "cycle/generation-review.json").read_text())
        self.assertEqual(report["cycleReview"]["attack"]["verdict"], "accept")
        ingest(self.job, "attack-000", self.image)
        self.assertIn("cycleReviews", load_job(self.job))
        ingest(self.job, "attack-000", self.image, offset=(1, 0))
        self.assertNotIn("cycleReviews", load_job(self.job))

    def test_changed_timing_does_not_export_stale_cycle_acceptance(self):
        for fid in ("attack-000", "attack-001"):
            ingest(self.job, fid, self.image)
            review(self.job, fid, "accept", "pose checked", "agent")
        review_cycle(self.job, "attack", "accept", "playback checked", "agent")
        job = load_job(self.job)
        job["frames"]["attack-000"]["durationMs"] = 90
        self.job.write_text(json.dumps(job))
        pack(self.job, self.root / "timing")
        report = json.loads((self.root / "timing/generation-review.json").read_text())
        self.assertEqual(report["cycleReview"], "not-completed")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reference = self.root / "reference.png"
        Image.new("RGB", (32, 32), "white").save(self.reference)
        self.spec = self.root / "spec.json"
        self.spec.write_text(json.dumps({"version": 1, "direction": "right", "canvas": [32, 32], "cell": [32, 32],
            "actions": [{"name": "attack", "loop": False, "frames": [
                {"pose": "anticipation", "durationMs": 70}, {"pose": "follow through", "durationMs": 130}]}]}))
        self.job = prepare(self.reference, "original green adventurer", self.root / "job", self.spec)
        self.image = self.root / "generated.png"
        image = Image.new("RGBA", (64, 64))
        ImageDraw.Draw(image).rectangle((20, 10, 40, 55), fill="green")
        image.save(self.image)

    def test_custom_action_preserves_nonloop_timing_and_portable_actual_sources(self):
        for fid in ("attack-000", "attack-001"):
            ingest(self.job, fid, self.image)
        output = self.root / "pack"
        pack(self.job, output)
        manifest = json.loads((output / "bundle/manifest.json").read_text())
        state = manifest["states"][0]
        self.assertFalse(state["loop"])
        self.assertEqual([f["durationMs"] for f in state["frames"]], [70, 130])
        report = json.loads((output / "generation-review.json").read_text())
        self.assertEqual(report["cycleReview"], "not-completed")
        self.assertIsNone(report["frames"][0]["review"])
        self.assertTrue((output / report["frames"][0]["sourceFiles"]["original"]).is_file())
        self.assertNotIn("walk in place", (self.job.parent / "attack-000-prompt.txt").read_text())

    def test_identical_import_is_idempotent_and_repair_invalidates_verdict(self):
        ingest(self.job, "attack-000", self.image)
        review(self.job, "attack-000", "reject", "bad pose", "agent")
        ingest(self.job, "attack-000", self.image)
        self.assertEqual(len(load_job(self.job)["frames"]["attack-000"]["attempts"]), 1)
        Image.new("RGBA", (64, 64), (255, 0, 0, 0)).save(self.root / "empty.png")
        image = Image.open(self.image)
        image.putpixel((32, 32), (255, 0, 0, 255))
        image.save(self.image)
        ingest(self.job, "attack-000", self.image)
        frame = load_job(self.job)["frames"]["attack-000"]
        self.assertEqual(len(frame["attempts"]), 2)
        self.assertIsNone(frame["attempts"][frame["selected"]]["review"])
        self.assertEqual(frame["attempts"][0]["review"]["verdict"], "reject")

    def test_missing_frames_do_not_publish(self):
        ingest(self.job, "attack-000", self.image)
        with self.assertRaisesRegex(ValueError, "缺生成帧"):
            pack(self.job, self.root / "missing")
        self.assertFalse((self.root / "missing").exists())

    def test_changed_reference_and_actual_frame_rejected(self):
        ingest(self.job, "attack-000", self.image)
        ingest(self.job, "attack-001", self.image)
        record = load_job(self.job)["frames"]["attack-000"]["attempts"][0]
        (self.job.parent / record["frame"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "帧已改变"):
            pack(self.job, self.root / "changed")
        (self.job.parent / "reference.png").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "任务输入已改变"):
            load_job(self.job)

    def test_opaque_and_wrong_aspect_not_recorded(self):
        with self.assertRaises(ValueError):
            ingest(self.job, "attack-000", self.reference)
        image = Image.new("RGBA", (32, 64))
        ImageDraw.Draw(image).rectangle((10, 10, 20, 40), fill="green")
        image.save(self.image)
        with self.assertRaisesRegex(ValueError, "比例不匹配"):
            ingest(self.job, "attack-000", self.image)
        self.assertEqual(load_job(self.job)["frames"]["attack-000"]["attempts"], [])

    def test_interrupted_unindexed_attempt_does_not_block_retry(self):
        (self.job.parent / "attack-000/attempt-001").mkdir(parents=True)
        result = ingest(self.job, "attack-000", self.image)
        self.assertIn("attempt-002", result["frame"])

    def test_changed_actual_prompt_and_clipping_offset_rejected(self):
        image = Image.new("RGBA", (64, 64))
        ImageDraw.Draw(image).rectangle((1, 1, 62, 62), fill="green")
        image.save(self.image)
        with self.assertRaisesRegex(ValueError, "裁掉角色"):
            ingest(self.job, "attack-000", self.image, [8, 0])
        for fid in ("attack-000", "attack-001"):
            ingest(self.job, fid, self.image)
        attempt = load_job(self.job)["frames"]["attack-000"]["attempts"][0]
        (self.job.parent / attempt["actualPrompt"]).write_text("changed request")
        with self.assertRaisesRegex(ValueError, "提示词已改变"):
            pack(self.job, self.root / "bad")


if __name__ == "__main__":
    unittest.main()
