from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_opening_picture",
    ROOT / "scripts/render_opening_picture.py",
)
assert SPEC and SPEC.loader
RENDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDER)


class RenderOpeningPictureTests(unittest.TestCase):
    def test_target_cover_occupies_every_frame_until_body_starts(self) -> None:
        opening = {
            "target_flash_end": 0.1,
            "carousel_start": 2.9,
            "carousel_end": 5.833333,
            "target_cover_hold_start": 5.833333,
            "body_voice_start": 6.98,
            "waterdrop_lock_response": {
                "visual_start": 5.933333,
                "visual_end": 6.333333,
            },
        }

        plan = RENDER.build_frame_plan(opening, fps=30)

        self.assertEqual(len(plan), 210)
        self.assertEqual(plan[174], "carousel")
        self.assertEqual(plan[175], "target_cover")
        self.assertEqual(plan[178], "waterwave")
        self.assertEqual(plan[209], "target_cover")
        self.assertNotIn("body", plan)


if __name__ == "__main__":
    unittest.main()
