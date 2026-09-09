from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.card_layout import SVG, STEMS, compose, publish_layout


def card(width, height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><title>Checked today</title></svg>'.encode()


class LayoutTests(unittest.TestCase):
    def test_sizes_follow_sources_and_cells_align(self):
        root = ET.fromstring(compose([card(100, 50), card(60, 40), card(110, 55), card(70, 60)], 2))
        cells = root.findall(SVG + 'g')
        self.assertEqual(cells[0].get('transform'), 'translate(0 0) scale(1.1 1)')
        self.assertEqual(cells[1].get('transform'), 'translate(111.5 0) scale(1.16667 1.25)')
        self.assertEqual(cells[2].get('transform'), 'translate(0 51.5) scale(1 1.09091)')
        self.assertEqual(len({e.get('id') for e in cells}), 4)

    def test_mobile_is_one_column(self):
        root = ET.fromstring(compose([card(100, 50)] * 4, 1))
        cells = root.findall(SVG + 'g')
        self.assertTrue(all(e.get('transform').startswith('translate(0 ') for e in cells))
        self.assertEqual(len({e.get('transform') for e in cells}), 4)

    def test_publication_references_existing_versions_and_retains_tooltip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'assets/readme-cards'
            directory.mkdir(parents=True)
            for stem in STEMS:
                (directory / (stem + '.svg')).write_bytes(card(100, 50))
            publish_layout(root)
            first = (root / 'README.md').read_text()
            self.assertIn('title="Checked today"', first)
            self.assertIn('<picture>', first)
            self.assertEqual(len(list(directory.glob('overview-*.svg'))), 2)
            publish_layout(root)
            self.assertEqual(first, (root / 'README.md').read_text())
            (directory / 'streak.svg').write_bytes(card(120, 60))
            publish_layout(root)
            self.assertNotEqual(first, (root / 'README.md').read_text())
            self.assertEqual(len(list(directory.glob('overview-*.svg'))), 4)
