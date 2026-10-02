"""旧加工入口的像素、帧序与参数边界回归。"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import cutout  # noqa: E402
import pack_action_sheet  # noqa: E402
import pack_sheet  # noqa: E402
from slice_grid import slice_grid  # noqa: E402
from utils import detect_bg_color, list_images, pad_to_square, thumbnail_square  # noqa: E402


class ImagePipelineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "frames"
        self.source.mkdir()
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def frame(self, number, red=100):
        path = self.source / f"frame-{number}.png"
        Image.new("RGBA", (4, 8), (red, 20, 30, 128)).save(path)
        return path

    def test_listing_sorts_frame_numbers_and_ignores_directories(self):
        for number in (10, 2, 1):
            self.frame(number)
        (self.source / "not-an-image.png").mkdir()
        self.assertEqual([p.name for p in list_images(self.source)],
                         ["frame-1.png", "frame-2.png", "frame-10.png"])

    def test_square_padding_and_thumbnail_preserve_alpha_without_upscaling(self):
        image = Image.new("RGBA", (4, 8), (100, 20, 30, 128))
        padded = pad_to_square(image)
        self.assertEqual(padded.getpixel((2, 0)), (100, 20, 30, 128))
        self.assertEqual(padded.getpixel((0, 0))[3], 0)
        thumbnail = thumbnail_square(image, 16)
        self.assertEqual(thumbnail.getchannel("A").getbbox(), (6, 4, 10, 12))
        self.assertEqual(thumbnail.getpixel((6, 4))[3], 128)

    def test_single_action_sheet_keeps_alpha_order_and_metadata(self):
        for number, red in ((10, 60), (2, 40), (1, 20)):
            self.frame(number, red)
        for cell in (None, 8):
            out = self.root / f"single-{cell}.png"
            pack_sheet.build(self.source, out, 3, None, cell, False)
            with Image.open(out) as image:
                width = 4 if cell is None else 8
                offset = 0 if cell is None else 2
                self.assertEqual([image.getpixel((i * width + offset, 0)) for i in range(3)],
                                 [(red, 20, 30, 128) for red in (20, 40, 60)])
            self.assertEqual(json.loads(out.with_suffix(".json").read_text())["frameCount"], 3)

    def test_multi_action_sheet_keeps_alpha_with_and_without_resizing(self):
        self.frame(1)
        for cell in (None, 8):
            out = self.root / f"actions-{cell}.png"
            pack_action_sheet.build([("idle", self.source)], out, 2, cell)
            with Image.open(out) as image:
                offset = 0 if cell is None else 2
                self.assertEqual(image.getpixel((offset, 0))[3], 128)
                width = image.width // 2
                self.assertEqual(image.crop((0, 0, width, 8)).tobytes(),
                                 image.crop((width, 0, width * 2, 8)).tobytes())

    def test_single_column_sampling_and_invalid_columns(self):
        paths = [Path(f"frame-{i}.png") for i in range(4)]
        self.assertEqual(pack_action_sheet.sample_row(paths, 1), paths[:1])
        for cols in (0, -1):
            with self.assertRaises(ValueError):
                pack_action_sheet.sample_row(paths, cols)

    def test_grid_invalid_geometry_leaves_no_output(self):
        source = self.frame(1)
        out = self.root / "slices"
        for rows, cols, gutter in ((0, 1, 0), (1, 0, 0), (1, 1, -1), (1, 1, 2), (9, 1, 0)):
            with self.assertRaises(ValueError):
                slice_grid(str(source), rows, cols, str(out), gutter=gutter)
            self.assertFalse(out.exists())

    def test_background_detection_handles_one_pixel_axes(self):
        for size in ((1, 1), (1, 8), (8, 1)):
            self.assertEqual(detect_bg_color(Image.new("RGB", size, (10, 20, 30))), (10, 20, 30))

    def test_chroma_uses_default_but_respects_explicit_tolerance(self):
        self.frame(1)
        for given, expected in ((None, 60), (32, 32)):
            with patch.object(cutout, "cutout_chroma", return_value=Image.new("RGBA", (4, 8))) as chroma:
                cutout.run(str(self.source), str(self.root / "cutouts"), tolerance=given, chroma=True)
                self.assertEqual(chroma.call_args.args[1], expected)


if __name__ == "__main__":
    unittest.main()
