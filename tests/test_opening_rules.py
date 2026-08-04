from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_static_motion_final",
    ROOT / "scripts/render_static_motion_final.py",
)
assert SPEC and SPEC.loader
RENDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDER)


class OpeningRulesTest(unittest.TestCase):
    def test_mask_stage_can_select_a_narration_caption(self) -> None:
        captions = [
            {"id": "cap-opening", "start": 0.10, "end": 2.90, "zh": "别急着跟着所有人走"},
            {"id": "cap-body", "start": 5.55, "end": 8.00, "zh": "正文"},
        ]

        caption = RENDER.active_caption(captions, 1.50)

        self.assertIsNotNone(caption)
        self.assertEqual(caption["id"], "cap-opening")

    def test_book_cover_stays_visible_until_body_voice_starts(self) -> None:
        opening = {
            "target_hero_asset": "10-片头字幕/target-hero.mp4",
            "masked_keyword_video_asset": "10-片头字幕/masked-keyword.mp4",
            "carousel_start": 2.9,
            "carousel_cards": [
                {"asset": f"10-片头字幕/carousel/card-{index:02d}.png"}
                for index in range(1, 21)
            ],
            "card_durations": [0.1, 0.133] * 10,
            "target_cover_hold_start": 5.233,
            "target_cover_hold_end": 5.983,
            "target_cover_base_asset": "10-片头字幕/target-cover-base.png",
            "target_cover_title_page_asset": "10-片头字幕/target-cover-title-page.png",
            "target_cover_title_binding": {"mode": "same_page_as_cover"},
            "waterdrop_lock_response": {
                "visual_start": 5.583,
                "visual_end": 5.983,
                "wave_trigger_at": 5.583,
                "effect_asset": "10-片头字幕/waterwave.mp4",
                "source_page_asset": "10-片头字幕/target-cover-title-page.png",
                "includes_title_layer": True,
            },
            "target_lock_start": 5.983,
            "target_lock_end": 6.65,
            "body_voice_start": 6.65,
            "title_motion": {"type": "cover_page_title_settle"},
        }

        target_lock = next(
            item for item in RENDER.build_opening_track(opening) if item["id"] == "target-lock"
        )

        self.assertEqual(target_lock["asset"], opening["target_cover_title_page_asset"])
        self.assertEqual(target_lock["end"], opening["body_voice_start"])
        self.assertEqual(target_lock["motion"]["type"], "cover_title_hold")

    def test_rejects_hero_cut_before_body_voice_starts(self) -> None:
        opening = {
            "target_hero_asset": "10-片头字幕/target-hero.mp4",
            "masked_keyword_video_asset": "10-片头字幕/masked-keyword.mp4",
            "carousel_start": 2.9,
            "carousel_cards": [],
            "card_durations": [],
            "target_cover_hold_start": 5.83,
            "target_cover_hold_end": 6.58,
            "target_cover_title_page_asset": "10-片头字幕/target-cover-title-page.png",
            "target_cover_title_binding": {"mode": "same_page_as_cover"},
            "waterdrop_lock_response": {
                "visual_start": 5.93,
                "visual_end": 6.33,
                "wave_trigger_at": 5.93,
                "effect_asset": "10-片头字幕/waterwave.mp4",
            },
            "target_lock_start": 6.58,
            "target_lock_end": 6.98,
            "body_voice_start": 6.98,
            "title_motion": {"type": "cover_page_title_settle"},
            "hero_cut_at": 6.10,
        }

        with self.assertRaisesRegex(ValueError, "hero_cut_at"):
            RENDER.build_opening_track(opening)


if __name__ == "__main__":
    unittest.main()
