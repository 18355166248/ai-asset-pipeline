import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from motion_region_lock import run, splice, rectangle_patch


class RegionLockTests(unittest.TestCase):
    def test_per_frame_base_preserves_each_phase_and_protected_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,colors in [('base',[(255,0,0,255),(0,0,255,255)]),('candidate',[(0,255,0,128),(0,255,255,64)])]:
                atlas=Image.new('RGBA',(24,12))
                for i,color in enumerate(colors):
                    atlas.paste(color,(i*12,0,(i+1)*12,12))
                    atlas.putpixel((i*12,0),(0,0,0,0))
                atlas.save(root/(name+'.png'))
                data={'kind':'motion','atlas':name+'.png','anchor':[.5,1],'states':[{'name':'move','loop':True,'frames':[{'x':i*12,'y':0,'w':12,'h':12,'durationMs':ms} for i,ms in enumerate([80,120])]}]}
                (root/(name+'.json')).write_text(json.dumps(data))
            plan={'version':1,'manifest':'candidate.json','action':'move','operation':'rectangle-patch','referenceFrame':0,'referenceManifest':'base.json','rect':[3,3,9,9],'feather':1,'protectedRects':[[4,4,6,6]]}
            (root/'plan.json').write_text(json.dumps(plan));run(root/'plan.json',root/'out')
            for i,color in enumerate([(255,0,0,255),(0,0,255,255)]):
                out=Image.open(root/f'out/bundle/frames/move/{i:04d}.png').convert('RGBA')
                self.assertEqual(out.getpixel((1,1)),color)
                self.assertEqual(out.getpixel((5,5)),color)
                self.assertEqual(out.getpixel((7,7)),[(0,255,0,128),(0,255,255,64)][i])
            source=json.loads((root/'base.json').read_text());source['states'][0]['frames'][1]['durationMs']=100;(root/'base.json').write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,'时长'):run(root/'plan.json',root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_external_head_reuse_preserves_body_bytes_timing_and_detects_clipping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            atlas=Image.new('RGBA',(24,12),(210,30,10,0))
            atlas.paste((255,0,0,255),(2,4,10,11))
            atlas.paste((255,0,0,255),(14,4,22,11))
            atlas.save(root/'atlas.png')
            reference=Image.new('RGBA',(12,12))
            reference.paste((0,255,0,128),(3,2,9,5))
            reference.save(root/'head.png')
            (root/'manifest.json').write_text(json.dumps({'kind':'motion','atlas':'atlas.png','anchor':[.5,1],'states':[{'name':'move','loop':True,'frames':[{'x':x,'y':0,'w':12,'h':12,'durationMs':ms} for x,ms in [(0,80),(12,120)]]}]}))
            plan={'version':1,'manifest':'manifest.json','action':'move','operation':'upper-region','referenceFrame':0,'referenceImage':'head.png','cutY':7,'feather':2,'headOffsetY':[0,1]}
            (root/'plan.json').write_text(json.dumps(plan))
            run(root/'plan.json',root/'out')
            for i,dy in enumerate([0,1]):
                patched=Image.open(root/f'out/bundle/frames/move/{i:04d}.png').convert('RGBA')
                self.assertEqual(patched.getpixel((4,3+dy)),(0,255,0,128))
                self.assertEqual(patched.crop((0,7+dy,12,12)).tobytes(),atlas.crop((i*12,7+dy,(i+1)*12,12)).tobytes())
            m=json.loads((root/'out/bundle/manifest.json').read_text())
            self.assertTrue(m['states'][0]['loop'])
            self.assertEqual([f['durationMs'] for f in m['states'][0]['frames']],[80,120])
            plan['headOffsetY']=[-3,0]
            (root/'plan.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'裁掉'):run(root/'plan.json',root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_external_reference_patch_keeps_other_frames_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atlas = Image.new('RGBA', (24,12), (255,0,0,255))
            atlas.putpixel((0,0),(0,0,0,0))
            atlas.putpixel((12,0),(0,0,0,0))
            atlas.save(root / 'atlas.png')
            base = Image.new('RGBA', (12,12), (0,255,0,255))
            base.putpixel((0,0),(0,0,0,0))
            base.save(root / 'base.png')
            manifest = {'kind':'motion','atlas':'atlas.png','anchor':[.5,1],
                        'states':[{'name':'move','loop':True,'frames':[
                            {'x':x,'y':0,'w':12,'h':12,'durationMs':100} for x in (0,12)]}]}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            plan = {'version':1,'manifest':'manifest.json','action':'move',
                    'operation':'rectangle-patch','referenceFrame':0,
                    'referenceImage':'base.png','frameIndices':[1],
                    'rect':[3,3,9,9],'feather':1}
            (root / 'plan.json').write_text(json.dumps(plan))
            run(root / 'plan.json', root / 'out')
            with Image.open(root / 'out/bundle/frames/move/0000.png') as untouched:
                self.assertEqual(untouched.tobytes(),atlas.crop((0,0,12,12)).tobytes())
            with Image.open(root / 'out/bundle/frames/move/0001.png') as patched:
                self.assertEqual(patched.getpixel((1,1)),(0,255,0,255))
                self.assertEqual(patched.getpixel((5,5)),(255,0,0,255))
            audit = json.loads((root / 'out/provenance.json').read_text())
            self.assertEqual(Path(audit['sources'][-1]['path']),(root / 'base.png').resolve())

    def test_rectangle_patch_only_changes_requested_area_and_keeps_alpha(self):
        base = Image.new('RGBA', (12,12), (0,255,0,255))
        candidate = Image.new('RGBA', (12,12), (255,0,0,128))
        out = rectangle_patch(base,candidate,(3,3,9,9),1)
        self.assertEqual(out.getpixel((5,5)), (255,0,0,128))
        self.assertEqual(out.getpixel((3,3)), base.getpixel((3,3)))
        self.assertEqual(out.getpixel((2,5)), base.getpixel((2,5)))
        self.assertEqual(rectangle_patch(base,base,(3,3,9,9),1).tobytes(),base.tobytes())
        with self.assertRaises(ValueError): rectangle_patch(base,candidate,(-1,3,9,9),1)

    def test_transparent_replacement_clears_old_outline_without_double_alpha(self):
        base = Image.new("RGBA", (12, 12), (0, 255, 0, 255))
        fixed = Image.new("RGBA", (12, 12))
        fixed.putpixel((4, 2), (255, 0, 0, 128))
        out = splice(base, fixed, 8, 3, 0)
        self.assertEqual(out.getpixel((4, 2)), (255, 0, 0, 128))
        self.assertEqual(out.getpixel((3, 2)), (0, 0, 0, 0))
        self.assertEqual(out.getpixel((3, 11)), (0, 255, 0, 255))

    def test_duration_loop_provenance_and_failed_batch_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atlas = Image.new("RGBA", (24, 12))
            for x in range(3, 9):
                for y in range(2, 11):
                    atlas.putpixel((x, y), (255, 0, 0, 180))
                    atlas.putpixel((x+12, y), (0, 255, 0, 180))
            atlas.save(root / "atlas.png")
            manifest = {"kind": "motion", "atlas": "atlas.png", "anchor": [.5, 1], "states": [{"name": "idle", "loop": False, "frames": [{"x": x, "y": 0, "w": 12, "h": 12, "durationMs": ms} for x, ms in ((0, 70), (12, 130))]}]}
            (root / "manifest.json").write_text(json.dumps(manifest))
            plan = {"version": 1, "manifest": "manifest.json", "action": "idle", "referenceFrame": 0, "cutY": 8, "feather": 2, "headOffsetY": [0, 0]}
            path = root / "plan.json"
            path.write_text(json.dumps(plan))
            output = root / "output"
            result = json.loads(run(path, output).read_text())
            state = result["states"][0]
            self.assertEqual([f["durationMs"] for f in state["frames"]], [70, 130])
            self.assertFalse(state["loop"])
            self.assertEqual(result["source"]["operation"], "explicit-upper-region-reuse")
            self.assertEqual(Image.open(output / "bundle/frames/idle/0001.png").getpixel((4, 2)), (255, 0, 0, 180))
            with self.assertRaisesRegex(ValueError, "输出已存在"):
                run(path, output)
            plan["headOffsetY"] = [0, -3]
            path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "裁掉"):
                run(path, root / "invalid")
            self.assertFalse((root / "invalid").exists())
