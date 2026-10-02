from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from asset_bundle import build  # noqa: E402


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()

    def recipe(self, **extra):
        recipe = {"version": 1, "kind": "motion", "title": "Test", "cell": [16, 16],
                  "resample": "nearest", "states": [{"name": "idle", "loop": True, "fps": 8}]}
        recipe.update(extra)
        path = self.root / "recipe.json"
        path.write_text(json.dumps(recipe))
        return path

    def frame(self, name="idle/frame-1.png", value=(100, 200, 50, 128), size=(16, 16)):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGBA", size)
        image.paste(value, (4, 4, 10, 12))
        image.save(path)
        return path

    def run_build(self, recipe, source=None, out=None, aseprite=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return build(recipe, source or self.source, out or self.root / "bundle", aseprite)

    def test_alpha_and_natural_order_survive_packing(self):
        for number, red in ((1, 20), (10, 60), (2, 40)):
            self.frame(f"idle/frame-{number}.png", (red, 100, 100, 128))
        out = self.run_build(self.recipe())
        with Image.open(out / "atlas.png") as atlas:
            self.assertEqual([atlas.getpixel((4 + i * 16, 4)) for i in range(3)],
                             [(r, 100, 100, 128) for r in (20, 40, 60)])
        manifest = json.loads((out / "manifest.json").read_text())
        self.assertEqual(manifest["states"][0]["sourceFrames"], ["idle/frame-1.png", "idle/frame-2.png", "idle/frame-10.png"])
        self.assertEqual(manifest["release"]["status"], "draft")

    def test_static_keeps_alpha_aspect_and_input(self):
        source = self.frame("logo.png", size=(16, 32))
        original = source.read_bytes()
        out = self.run_build(self.recipe(kind="static", sizes=[32]), source)
        with Image.open(out / "images/32/001.png") as image:
            self.assertEqual(image.size, (32, 32))
            self.assertEqual(image.getpixel((12, 4))[3], 128)
            self.assertEqual(image.getpixel((0, 4))[3], 0)
        self.assertEqual(source.read_bytes(), original)
        provenance = json.loads((out / "provenance.json").read_text())
        self.assertEqual(len(provenance["inputs"]), 2)

    def test_mismatched_canvas_fails_without_partial_output(self):
        self.frame()
        self.frame("idle/frame-2.png", size=(32, 32))
        with self.assertRaisesRegex(ValueError, "源画布必须一致"):
            self.run_build(self.recipe())
        self.assertFalse((self.root / "bundle").exists())
        self.assertEqual(list(self.root.glob(".asset-bundle-*")), [])

    def test_downscaling_cannot_silently_erase_subject(self):
        source = self.frame("tiny.png", size=(64, 64))
        with self.assertRaisesRegex(ValueError, "全透明素材"):
            self.run_build(self.recipe(kind="static", sizes=[1]), source)
        self.assertFalse((self.root / "bundle").exists())

    def test_empty_and_opaque_frames_rejected(self):
        path = self.frame()
        for color, message in (((0, 0, 0, 0), "全透明"), ((1, 2, 3, 255), "缺少透明背景")):
            Image.new("RGBA", (16, 16), color).save(path)
            with self.assertRaisesRegex(ValueError, message):
                self.run_build(self.recipe())

    def test_rerun_never_overwrites_a_bundle(self):
        self.frame()
        recipe = self.recipe()
        out = self.run_build(recipe)
        original = (out / "manifest.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "输出已存在"):
            self.run_build(recipe)
        self.assertEqual((out / "manifest.json").read_bytes(), original)

    def test_aseprite_roundtrip_keeps_timing_alpha_and_loop(self):
        self.frame()
        self.frame("idle/frame-2.png", (20, 60, 100, 192))
        recipe = self.recipe(states=[{"name": "idle", "fps": 8, "loop": False}])
        first = self.run_build(recipe)
        export = first / "aseprite.json"
        data = json.loads(export.read_text())
        data["frames"][0]["duration"] = 70
        data["frames"][1]["duration"] = 230
        export.write_text(json.dumps(data))
        second = self.run_build(recipe, export, self.root / "roundtrip", True)
        manifest = json.loads((second / "manifest.json").read_text())
        self.assertEqual([f["durationMs"] for f in manifest["states"][0]["frames"]], [70, 230])
        self.assertFalse(manifest["states"][0]["loop"])
        self.assertEqual((first / "atlas.png").read_bytes(), (second / "atlas.png").read_bytes())

    def test_aseprite_rejects_escape_trim_and_outside_rect(self):
        self.frame()
        recipe = self.recipe()
        first = self.run_build(recipe)
        export = first / "aseprite.json"
        original = json.loads(export.read_text())
        cases = [("path", "越过素材目录"), ("trim", "未 trim"), ("rect", "越过图集边界")]
        for mode, message in cases:
            data = json.loads(json.dumps(original))
            if mode == "path":
                data["meta"]["image"] = "../outside.png"
            elif mode == "trim":
                data["frames"][0]["trimmed"] = True
            else:
                data["frames"][0]["frame"]["x"] = 1
            export.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, message):
                self.run_build(recipe, export, self.root / "bad", True)

    def test_preview_escapes_untrusted_title(self):
        self.frame()
        out = self.run_build(self.recipe(title="</script><script>alert(1)</script>"))
        html = (out / "preview.html").read_text()
        self.assertNotIn("</script><script>alert(1)", html)
        self.assertIn("\\u003c/script>", html)

    def test_invalid_recipe_and_frame_directory_fail_before_publication(self):
        for updates in ({"cell": [0, 16]}, {"states": [{"name": "idle", "loop": "false"}]},
                        {"states": [{"name": "idle", "loop": True, "directory": "../outside"}]}):
            with self.assertRaises(ValueError):
                self.run_build(self.recipe(**updates))
            self.assertFalse((self.root / "bundle").exists())

    def test_padding_does_not_invent_animation_frames(self):
        self.frame()
        self.frame("attack/frame-1.png")
        self.frame("attack/frame-2.png", (20, 30, 40, 255))
        states = [{"name": "idle", "loop": True}, {"name": "attack", "loop": False}]
        out = self.run_build(self.recipe(states=states))
        manifest = json.loads((out / "manifest.json").read_text())
        self.assertEqual([len(s["frames"]) for s in manifest["states"]], [1, 2])
        with Image.open(out / "atlas.png") as image:
            self.assertEqual(image.crop((0, 0, 16, 16)).tobytes(), image.crop((16, 0, 32, 16)).tobytes())


if __name__ == "__main__":
    unittest.main()
