from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from scripts.refresh_readme_cards import CARDS, ROOT, refresh, validate

GOOD = b'<svg xmlns="http://www.w3.org/2000/svg" width="478" height="186"><text>Current Streak 12</text></svg>'


class CardTests(unittest.TestCase):
    def test_valid_svg(self):
        validate(GOOD, ('Current Streak',))

    def test_reject_bad_documents(self):
        for data in (
            b'<html>' + GOOD + b'</html>',
            b'PHP Warning: network failed' + GOOD,
            GOOD.replace(b'12', b'& broken'),
            GOOD.replace(b'12', b'Error: Bad credentials'),
            GOOD.replace(b'Current Streak', b'Unrelated chart'),
            GOOD.replace(b'width="478"', b'width="0"'),
            GOOD.replace(b'12', b''),
            GOOD.replace(b'</svg>', b'<script>alert(1)</script></svg>'),
            GOOD[:60],
        ):
            with self.subTest(data=data), self.assertRaises((ValueError, SyntaxError)):
                validate(data, ('Current Streak',))

    def test_failure_preserves_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'card.svg'
            path.write_bytes(GOOD)
            fetch = Mock(return_value=b'<html>unavailable</html>')
            self.assertFalse(refresh(path, 'unused', ('Current Streak',), fetch, lambda _: None))
            self.assertEqual(path.read_bytes(), GOOD)
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_retry_then_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'card.svg'
            path.write_bytes(GOOD)
            newer = GOOD.replace(b'12', b'13')
            fetch = Mock(side_effect=[TimeoutError(), b'bad response', newer])
            self.assertTrue(refresh(path, 'unused', ('Current Streak',), fetch, lambda _: None))
            self.assertEqual(path.read_bytes(), newer)

    def test_failed_initial_fetch_creates_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing.svg'
            self.assertFalse(refresh(path, 'unused', (), Mock(side_effect=TimeoutError()), lambda _: None))
            self.assertFalse(path.exists())

    def test_committed_fallbacks_are_valid(self):
        for name, (_, labels) in CARDS.items():
            with self.subTest(card=name):
                validate((ROOT / 'assets/readme-cards' / (name + '.svg')).read_bytes(), labels)


if __name__ == '__main__':
    unittest.main()
