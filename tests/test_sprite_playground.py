import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples'))
from make_sprite_playground import build


class PlaygroundTests(unittest.TestCase):
    def test_portable_copy_preserves_source_bytes_timing_and_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / 'source'; source.mkdir()
            (source / 'atlas.png').write_bytes(b'actual-image-bytes')
            manifest = {'kind': 'motion', 'atlas': 'atlas.png', 'anchor': [.5, 1],
                        'release': {'status': 'draft'}, 'states': [{'name': 'jump', 'loop': False, 'frames': [{'durationMs': 80}]}]}
            path = source / 'manifest.json'; path.write_text(json.dumps(manifest)); original = path.read_bytes()
            result = build(path, root / 'playable')
            self.assertEqual((result / 'bundle/atlas.png').read_bytes(), b'actual-image-bytes')
            self.assertEqual(json.loads((result / 'bundle/manifest.json').read_text()), manifest)
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue((result / 'sprite-controller.mjs').is_file())
            self.assertTrue((result / 'motion.mjs').is_file())

    def test_atlas_cannot_escape_source_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / 'source'; source.mkdir()
            (root / 'private.png').write_bytes(b'not-part-of-pack')
            path = source / 'manifest.json'; path.write_text(json.dumps({'kind': 'motion', 'atlas': '../private.png'}))
            with self.assertRaises(ValueError): build(path, root / 'playable')
            self.assertFalse((root / 'playable').exists())

    def test_existing_preview_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'atlas.png').write_bytes(b'image')
            path = root / 'manifest.json'; path.write_text(json.dumps({'kind': 'motion', 'atlas': 'atlas.png'}))
            out = root / 'playable'; out.mkdir(); (out / 'keep.txt').write_text('previous')
            with self.assertRaises(ValueError): build(path, out)
            self.assertEqual((out / 'keep.txt').read_text(), 'previous')
