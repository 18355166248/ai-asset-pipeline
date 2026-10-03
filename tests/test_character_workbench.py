import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from character_workbench import build, load_glb, load_pivot, load_sprite


class WorkbenchTests(unittest.TestCase):
    def test_preview_jump_curve_is_validated_and_does_not_modify_source_pack(self):
        data = self.sprite()
        data["states"][0].update(name="jump", loop=False)
        source = self.write(self.root / "manifest.json", data)
        original = source.read_bytes()
        curve = {"kind": "jump-arc", "startMs": 40, "endMs": 180, "heightPixels": 4}
        profile = {"version": 1, "characters": [{"id": "hero", "kind": "sprite", "manifest": "manifest.json", "previewMotion": {"jump": curve}}]}
        path = self.write(self.root / "profile.json", profile)
        out = build(path, self.root / "viewer")
        clip = json.loads((out / "manifest.json").read_text())["characters"][0]["clips"][0]
        self.assertEqual(clip["previewMotion"], curve)
        self.assertEqual(source.read_bytes(), original)
        curve["endMs"] = 300
        self.write(path, profile)
        with self.assertRaises(ValueError):
            build(path, self.root / "invalid")
        self.assertFalse((self.root / "invalid").exists())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def sprite(self):
        Image.new("RGBA", (20, 10), (255, 0, 0, 180)).save(self.root / "atlas.png")
        data = {"kind":"motion", "atlas":"atlas.png", "anchor":[0.5,1], "states":[{
            "name":"idle", "loop":True, "frames":[
                {"x":0,"y":0,"w":10,"h":10,"durationMs":40},
                {"x":10,"y":0,"w":10,"h":10,"durationMs":160}]}]}
        self.write(self.root / "manifest.json",data)
        return data

    def glb(self, value):
        document = json.dumps(value).encode()
        document += b" " * (-len(document) % 4)
        path = self.root / "test.glb"
        path.write_bytes(struct.pack("<IIIII",0x46546C67,2,len(document)+20,len(document),0x4E4F534A)+document)
        return path

    def test_sprite_preserves_timing_and_source(self):
        self.sprite()
        data, records = load_sprite({"manifest":"manifest.json"},self.root)
        self.assertEqual(data["clips"][0]["duration"],0.2)
        self.assertTrue(data["clips"][0]["loop"])
        self.assertEqual(len(records),2)
        self.assertTrue(data["atlasData"].startswith("data:image/png;base64,"))

    def test_sprite_rejects_traversal_and_outside_rect(self):
        data = self.sprite()
        data["atlas"] = "../outside.png"
        self.write(self.root / "manifest.json",data)
        with self.assertRaisesRegex(ValueError,"越过"):
            load_sprite({"manifest":"manifest.json"},self.root)
        data = self.sprite(); data["states"][0]["frames"][1]["x"] = 15
        self.write(self.root / "manifest.json",data)
        with self.assertRaisesRegex(ValueError,"越出"):
            load_sprite({"manifest":"manifest.json"},self.root)

    def test_glb_external_sources_and_loop_contract(self):
        self.glb({"asset":{"version":"2.0"},"animations":[{"name":"Walk.001"}]})
        data, _ = load_glb({"model":"test.glb","loops":{"Walk.001":True}},self.root)
        self.assertTrue(data["clips"][0]["loop"])
        self.glb({"asset":{"version":"2.0"},"images":[{"uri":"https://example.org/private.png"}]})
        with self.assertRaisesRegex(ValueError,"外部 URI"):
            load_glb({"model":"test.glb"},self.root)

    def test_glb_invalid_header_and_compression(self):
        path = self.glb({"asset":{"version":"2.0"}})
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError,"无效 GLB"):
            load_glb({"model":"test.glb"},self.root)
        self.glb({"extensionsRequired":["KHR_draco_mesh_compression"]})
        with self.assertRaisesRegex(ValueError,"不支持扩展"):
            load_glb({"model":"test.glb"},self.root)

    def test_build_coverage_atomic_and_no_overwrite(self):
        self.sprite()
        profile = {"version":1,"characters":[{"id":"hero","kind":"sprite","manifest":"manifest.json",
            "requiredActions":["idle","attack"], "requiredDirections":["side","front"],
            "reviewNotes":["左右腿交替未通过"]}]}
        path = self.write(self.root / "profile.json",profile)
        out = build(path,self.root / "viewer")
        report = json.loads((out / "report.json").read_text())
        self.assertEqual(report["characters"][0]["missingActions"],["attack"])
        self.assertEqual(report["characters"][0]["missingDirections"],["front"])
        self.assertIn("左右腿交替未通过", report["characters"][0]["warnings"])
        jobs = json.loads((out / "generation-plan.json").read_text())["jobs"]
        self.assertEqual(len(jobs),3)
        self.assertTrue(all(j["status"]=="not-executed" for j in jobs))
        with self.assertRaisesRegex(ValueError,"输出已存在"):
            build(path,out)
        self.assertTrue((out / "index.html").exists())
        self.assertTrue((out / "vendor/addons/utils/SkeletonUtils.js").exists())

    def test_real_library_and_invalid_numeric_key(self):
        data, records = load_pivot({"library":str(ROOT / "animation-library"),"skeleton":"humanoid-basic"},self.root)
        self.assertEqual(len(data["clips"]),8)
        self.assertEqual(len(records),9)
        library = self.root / "library"
        skeleton = data["skeleton"]
        self.write(library / "skeletons/humanoid-basic.json",skeleton)
        bad = data["clips"][0]; first = next(iter(bad["tracks"].values())); next(iter(first.values()))[0][1][0] = float('nan')
        self.write(library / "clips/humanoid-basic/cast.json",bad)
        with self.assertRaisesRegex(ValueError,"必须在"):
            load_pivot({"library":str(library),"skeleton":"humanoid-basic"},self.root)

    def test_changed_batch_loads_matching_runtime_and_data(self):
        import re
        self.sprite()
        profile = {"version": 1, "title": "first", "characters": [{"id": "hero", "kind": "sprite", "manifest": "manifest.json"}]}
        path = self.write(self.root / "profile.json", profile)
        first = build(path, self.root / "first")
        profile["title"] = "second"
        self.write(path, profile)
        second = build(path, self.root / "second")
        scripts = []
        for out, title in ((first, "first"), (second, "second")):
            script = re.search(r'src="\./(main-[^\"]+\.mjs)"', (out / "index.html").read_text())[1]
            scripts.append(script)
            content = (out / script).read_text()
            manifest = re.search(r"'(manifest-[^']+\.json)'", content)[1]
            motion = re.search(r"from '\./(motion-[^']+\.mjs)'", content)[1]
            self.assertEqual(json.loads((out / manifest).read_text())["title"], title)
            self.assertTrue((out / motion).is_file())
        self.assertNotEqual(*scripts)

    def test_invalid_build_does_not_publish(self):
        self.sprite()
        profile = {"version":1,"characters":[{"id":"hero","kind":"sprite","manifest":"manifest.json","defaultAction":"missing"}]}
        path = self.write(self.root / "profile.json",profile)
        with self.assertRaisesRegex(ValueError,"defaultAction"):
            build(path,self.root / "viewer")
        self.assertFalse((self.root / "viewer").exists())

    def test_invalid_review_notes_do_not_publish(self):
        self.sprite()
        profile = {"version":1,"characters":[{"id":"hero","kind":"sprite","manifest":"manifest.json",
            "reviewNotes":"不要把字符串拆成逐字警告"}]}
        path = self.write(self.root / "profile.json",profile)
        with self.assertRaisesRegex(ValueError,"reviewNotes"):
            build(path,self.root / "viewer")
        self.assertFalse((self.root / "viewer").exists())


if __name__ == "__main__":
    unittest.main()
