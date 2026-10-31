import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class CaptionTests(unittest.TestCase):
    def test_rounding_carries_to_next_minute(self):
        captions = module('captions')
        self.assertEqual(captions.timestamp(59.9999), '00:01:00,000')
        self.assertEqual(captions.timestamp(-0.1), '00:00:00,000')
        self.assertEqual(captions.timestamp(3600.125), '01:00:00,125')


class BudgetTests(unittest.TestCase):
    def test_reservations_enforce_cap_and_reject_nonfinite_values(self):
        review = module('review')
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / 'spend.jsonl'
            review.reserve(ledger, 0.4, 1)
            review.reserve(ledger, 0.4, 1)
            with self.assertRaisesRegex(ValueError, 'exceeded'):
                review.reserve(ledger, 0.4, 1)
            for value in [math.nan, math.inf, -1, 0]:
                with self.assertRaises(ValueError):
                    review.reserve(ledger, value, 1)
            self.assertEqual(len(ledger.read_text().splitlines()), 2)
            self.assertFalse(ledger.with_suffix('.lock').exists())

    def test_simultaneous_reservation_is_refused_without_deleting_other_lock(self):
        review = module('review')
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / 'spend.jsonl'
            lock = ledger.with_suffix('.lock')
            lock.touch()
            with self.assertRaisesRegex(ValueError, 'Another review'):
                review.reserve(ledger, 0.1, 1)
            self.assertTrue(lock.exists())
            self.assertFalse(ledger.exists())


class MuxTests(unittest.TestCase):
    def test_offset_detects_a_shift_and_refuses_silence(self):
        import numpy as np
        import soundfile as sf
        from unittest.mock import patch
        render = module('render_and_verify')
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            reference = np.random.default_rng(7).normal(0, 0.1, 22050)
            shifted = np.concatenate([np.zeros(2205), reference[:-2205]])
            sf.write(base / 'mux.wav', shifted, 22050)
            sf.write(base / 'reference.wav', reference, 22050)
            with patch.object(render, 'run'):
                self.assertAlmostEqual(render.offset_ms('unused', 'unused', base), 100, places=1)
                sf.write(base / 'reference.wav', np.zeros(22050), 22050)
                with self.assertRaisesRegex(ValueError, 'silent'):
                    render.offset_ms('unused', 'unused', base)


if __name__ == '__main__':
    unittest.main()
