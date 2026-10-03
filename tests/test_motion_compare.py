import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from motion_compare import build


class MotionCompareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, durations in [('a', [100, 200]), ('b', [50, 100, 150])]:
            source = self.root / name; source.mkdir()
            Image.new('RGBA', (300, 100), (90, 120, 150, 255)).save(source / 'atlas.png')
            manifest = {'kind': 'motion', 'anchor': [.5, 1], 'atlas': 'atlas.png', 'states': [{'name': 'move', 'loop': True, 'frames': [{'x': i*100, 'y': 0, 'w': 100, 'h': 100, 'durationMs': d} for i, d in enumerate(durations)]}]}
            (source / 'manifest.json').write_text(json.dumps(manifest))
        self.config = {'version': 1, 'action': 'move', 'title': '<角色>', 'inputs': [{'manifest': 'a/manifest.json'}, {'manifest': 'b/manifest.json'}]}
        self.path = self.root / 'config.json'

    def run_build(self):
        self.path.write_text(json.dumps(self.config))
        return build(self.path, self.root / 'result')

    def test_preserves_unequal_frames_and_durations_in_portable_shared_clock_page(self):
        out = self.run_build(); report = json.loads((out / 'comparison.json').read_text())
        self.assertEqual(report['durationMs'], 300)
        self.assertEqual([f['durationMs'] for f in report['sources'][1]['frames']], [50, 100, 150])
        self.assertEqual((out / 'atlas-0.png').read_bytes(), (self.root / 'a/atlas.png').read_bytes())
        self.assertIn('&lt;角色&gt;', (out / 'index.html').read_text())
        with self.assertRaises(ValueError): self.run_build()

    def test_rejects_cycle_length_and_anchor_mismatch(self):
        source = self.root / 'b/manifest.json'; manifest = json.loads(source.read_text())
        manifest['states'][0]['frames'][0]['durationMs'] = 60; source.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, '总时长'): self.run_build()
        manifest['states'][0]['frames'][0]['durationMs'] = 50; manifest['anchor'] = [.5, .9]; source.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'anchor'): self.run_build()
        self.assertFalse((self.root / 'result').exists())

    def test_rejects_missing_or_nonloop_action(self):
        self.config['action'] = 'unknown'
        with self.assertRaises(ValueError): self.run_build()
        self.config['action'] = 'move'; source = self.root / 'b/manifest.json'; manifest = json.loads(source.read_text()); manifest['states'][0]['loop'] = False; source.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): self.run_build()


if __name__ == '__main__': unittest.main()
