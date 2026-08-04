import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_package.py"
SPEC = importlib.util.spec_from_file_location("validate_package", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_wav(path: Path, samples: np.ndarray, sample_rate: int = 48000) -> None:
    stereo = np.column_stack([samples, samples]).astype(np.int16)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(stereo.tobytes())


class CarouselSfxRulesTests(unittest.TestCase):
    def test_rejects_exactly_looped_carousel_sound(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = (np.sin(np.linspace(0, 30, 4800)) * 12000).astype(np.int16)
            path = Path(tmp) / "looped.wav"
            write_wav(path, np.concatenate([source, source]))

            self.assertTrue(MODULE.audio_has_repeated_halves(path))

    def test_accepts_single_pass_followed_by_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = (np.sin(np.linspace(0, 30, 4800)) * 12000).astype(np.int16)
            path = Path(tmp) / "single-pass.wav"
            write_wav(path, np.concatenate([source, np.zeros_like(source)]))

            self.assertFalse(MODULE.audio_has_repeated_halves(path))


if __name__ == "__main__":
    unittest.main()
