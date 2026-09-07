from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import xml.etree.ElementTree as ET

from scripts.refresh_readme_cards import CARDS, ROOT, SVG, animate_productive_time, refresh, validate

GOOD = b'<svg xmlns="http://www.w3.org/2000/svg" width="478" height="186"><text>Current Streak 12</text></svg>'


class CardTests(unittest.TestCase):
    def test_valid_svg(self):
        validate(GOOD, ('Current Streak',))

    def test_animation_preserves_geometry_and_is_idempotent(self):
        original = (ROOT / 'assets/readme-cards/productive-time.svg').read_bytes()
        animated = animate_productive_time(original)
        validate(animated, ('Commits',))
        self.assertEqual(animated, animate_productive_time(animated))
        before = ET.fromstring(original)
        after = ET.fromstring(animated)
        self.assertEqual(before.attrib, after.attrib)
        self.assertEqual([e.attrib for e in before.iter(SVG + 'rect')],
                         [e.attrib for e in after.iter(SVG + 'rect')])
        styles = [e for e in after if e.get('id') == 'readme-bar-animation']
        self.assertEqual(len(styles), 1)
        self.assertIn('prefers-reduced-motion: no-preference', styles[0].text)
        self.assertIn('0.6s', styles[0].text)

    def test_animation_is_applied_on_refresh(self):
        original = (ROOT / 'assets/readme-cards/productive-time.svg').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'productive-time.svg'
            self.assertTrue(refresh(path, 'unused', ('Commits',), Mock(return_value=original)))
            self.assertEqual(path.read_bytes(), animate_productive_time(original))

    def test_changed_bar_structure_preserves_last_good(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'productive-time.svg'
            path.write_bytes(GOOD)
            self.assertFalse(refresh(path, 'unused', ('Current Streak',), Mock(return_value=GOOD), lambda _: None))
            self.assertEqual(path.read_bytes(), GOOD)

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
