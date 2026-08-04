import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_static_motion_final.py"
SPEC = importlib.util.spec_from_file_location("render_static_motion_final", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VersionedAssetResolutionTests(unittest.TestCase):
    def test_uses_newest_existing_asset_not_newer_than_requested_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            directory = project / "06-配乐音效"
            directory.mkdir()
            (directory / "bgm-v003.wav").touch()
            expected = directory / "bgm-v004.wav"
            expected.touch()

            resolved = MODULE.resolve_versioned_asset(project, "06-配乐音效", "bgm", "v005", ".wav")

            self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()
