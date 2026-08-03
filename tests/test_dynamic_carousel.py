import importlib.util
import json
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_book_carousel.py"
LIBRARY_MANIFEST = Path(__file__).resolve().parents[1] / "assets" / "book-card-library" / "manifest.json"


def load_module():
    spec = importlib.util.spec_from_file_location("plan_book_carousel", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DynamicCarouselTests(unittest.TestCase):
    def test_44_frames_use_11_four_frame_cards(self):
        module = load_module()
        card_count = module.choose_card_count(44, 3, 4)
        self.assertEqual(card_count, 11)
        self.assertEqual(module.distribute_frames(44, card_count, 3), [4] * 11)

    def test_target_cover_lands_on_title_voice_frame(self):
        module = load_module()
        plan = module.build_plan(
            title_start=4.373542,
            carousel_start=2.9,
            fps=30,
            target_cover_lead_frames=0,
            min_card_frames=3,
            max_card_frames=4,
            minimum_cards=6,
        )
        self.assertEqual(plan["title_start_frame"], 131)
        self.assertEqual(plan["target_cover_start_frame"], 131)
        self.assertEqual(plan["total_carousel_frames"], 44)
        self.assertEqual(plan["card_count"], 11)
        self.assertEqual(plan["card_frames"], [4] * 11)

    def test_skill_owned_library_has_24_existing_covers_and_excludes_target(self):
        module = load_module()
        manifest = json.loads(LIBRARY_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["cover_count"], 24)
        self.assertEqual(len(manifest["covers"]), 24)
        self.assertTrue(all((LIBRARY_MANIFEST.parent / item["file"]).is_file() for item in manifest["covers"]))
        self.assertEqual(module.available_cover_count(manifest, LIBRARY_MANIFEST, "活着"), 23)


if __name__ == "__main__":
    unittest.main()
