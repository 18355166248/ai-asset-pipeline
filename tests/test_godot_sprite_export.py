import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from godot_sprite_export import export


class GodotExportTests(unittest.TestCase):
    def source(self, root):
        source = root / 'source'
        source.mkdir()
        Image.new('RGBA', (16, 8), (20, 40, 80, 100)).save(source / 'atlas.png')
        manifest = {'kind': 'motion', 'atlas': 'atlas.png', 'anchor': [.5, .75],
                    'release': {'status': 'draft'}, 'states': [
                        {'name': 'attack', 'loop': False, 'frames': [
                            {'x': 0, 'y': 0, 'w': 8, 'h': 8, 'durationMs': 110},
                            {'x': 8, 'y': 0, 'w': 8, 'h': 8, 'durationMs': 80}]}]}
        path = source / 'manifest.json'
        path.write_text(json.dumps(manifest))
        return path

    def test_copy_preserves_bytes_and_draft_anchor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = self.source(root)
            before = source.read_bytes()
            out = export(source, root / 'export')
            self.assertEqual((out / 'source-manifest.json').read_bytes(), before)
            self.assertEqual((out / 'atlas.png').read_bytes(), (source.parent / 'atlas.png').read_bytes())
            self.assertEqual(source.read_bytes(), before)
            metadata = json.loads((out / 'export.json').read_text())
            self.assertEqual(metadata['status'], 'draft')
            self.assertEqual(metadata['sourceRelease'], {'status': 'draft'})
            self.assertEqual(metadata['spriteOffset'], [0, -2])

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = self.source(root)
            out = root / 'export'
            out.mkdir()
            (out / 'keep.txt').write_text('previous batch')
            with self.assertRaises(ValueError):
                export(source, out)
            self.assertEqual((out / 'keep.txt').read_text(), 'previous batch')

    def test_external_atlas_rejected_without_publishing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = self.source(root)
            manifest = json.loads(source.read_text())
            manifest['atlas'] = '../external.png'
            source.write_text(json.dumps(manifest))
            Image.new('RGBA', (16, 8)).save(root / 'external.png')
            with self.assertRaises(ValueError):
                export(source, root / 'export')
            self.assertFalse((root / 'export').exists())
