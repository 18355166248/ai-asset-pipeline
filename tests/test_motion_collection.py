import json
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from motion_collection import assemble
from character_workbench import load_sprite


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write_pack("idle", [90], True)
        self.write_pack("attack", [70, 130], False)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"version": 1, "inputs": [{"manifest": "idle/manifest.json"}, {"manifest": "attack/manifest.json"}]}))

    def write_pack(self, name, durations, loop, anchor=None):
        folder = self.root / name
        folder.mkdir(exist_ok=True)
        atlas = Image.new("RGBA", (12*len(durations), 12))
        for index in range(len(durations)):
            atlas.paste(Image.new("RGBA", (8, 8), (255, 0, 0, 128)), (12*index+1, 1))
        atlas.save(folder / "atlas.png")
        manifest = {"kind": "motion", "atlas": "atlas.png", "anchor": anchor or [.5, 1], "states": [{"name": name, "loop": loop,
            "frames": [{"x": 12*i, "y": 0, "w": 12, "h": 12, "durationMs": ms} for i, ms in enumerate(durations)]}]}
        (folder / "manifest.json").write_text(json.dumps(manifest))

    def test_preserves_pixels_timing_loop_and_portable_source_packs(self):
        (self.root / "idle/generation-review.json").write_text(json.dumps({"cycleReview": {"idle": {"verdict": "reject"}}}))
        out = self.root / "collection"
        manifest = json.loads(assemble(self.config, out).read_text())
        for record in manifest["source"]["inputs"]:
            self.assertEqual(hashlib.sha256((out / record["originalManifest"]).read_bytes()).hexdigest(), record["originalManifestSha256"])
        audit = manifest["source"]["inputs"][0]["auditCopies"][0]
        self.assertEqual(json.loads((out / audit["path"]).read_text())["cycleReview"]["idle"]["verdict"], "reject")
        self.assertEqual(manifest["source"]["status"], "draft")
        self.assertEqual([(s["name"], s["loop"], [f["durationMs"] for f in s["frames"]]) for s in manifest["states"]], [("idle", True, [90]), ("attack", False, [70, 130])])
        self.assertEqual(Image.open(out / "bundle/atlas.png").getpixel((1, 1)), (255, 0, 0, 128))
        relocated = self.root / "relocated"
        shutil.move(out, relocated)
        shutil.rmtree(self.root / "idle")
        shutil.rmtree(self.root / "attack")
        load_sprite({"manifest": "inputs/001/manifest.json"}, relocated)
        load_sprite({"manifest": "bundle/manifest.json"}, relocated)

    def test_rejects_duplicate_actions_and_incompatible_anchor_without_publishing(self):
        self.write_pack("attack", [70, 130], False, [.5, .9])
        with self.assertRaisesRegex(ValueError, "锚点不一致"):
            assemble(self.config, self.root / "invalid")
        self.assertFalse((self.root / "invalid").exists())
        self.config.write_text(json.dumps({"version": 1, "inputs": [{"manifest": "idle/manifest.json"}, {"manifest": "idle/manifest.json"}]}))
        with self.assertRaisesRegex(ValueError, "动作重复"):
            assemble(self.config, self.root / "invalid")
        self.assertFalse((self.root / "invalid").exists())
