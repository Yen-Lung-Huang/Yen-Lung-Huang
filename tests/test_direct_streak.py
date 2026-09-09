from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from scripts.direct_streak import TAIPEI, calculate, fetch_days, build_card
from scripts.refresh_readme_cards import CARDS, ROOT, SVG, publish_versions, validate


class DirectStreakTests(unittest.TestCase):
    def test_today_can_be_empty_but_yesterday_continues_streak(self):
        today = date(2026, 9, 10)
        stats = calculate({today - timedelta(days=2): 1, today - timedelta(days=1): 2, today: 0}, today)
        self.assertEqual(stats['current'], (2, date(2026, 9, 8), date(2026, 9, 9)))
        self.assertEqual(stats['total'], 3)

    def test_missing_yesterday_breaks_streak(self):
        today = date(2026, 9, 10)
        stats = calculate({date(2026, 9, 8): 2, today: 0}, today)
        self.assertEqual(stats['current'][0], 0)
        self.assertEqual(stats['longest'][0], 1)

    def test_year_boundary_and_future_contributions(self):
        today = date(2026, 1, 1)
        stats = calculate({date(2025, 12, 31): 1, today: 2, date(2026, 1, 2): 99}, today)
        self.assertEqual(stats['current'][0], 2)
        self.assertEqual(stats['total'], 3)

    def test_partial_calendar_is_rejected(self):
        query = Mock(side_effect=[
            {'createdAt': '2026-01-01T00:00:00Z', 'contributionsCollection': {'contributionYears': [2026]}},
            {'y2026': {'contributionCalendar': {'weeks': [{'contributionDays': [
                {'date': '2026-01-02', 'contributionCount': 1}]}]}}},
        ])
        with self.assertRaisesRegex(ValueError, 'Incomplete contribution calendar'):
            fetch_days(datetime(2026, 1, 2, 12, tzinfo=TAIPEI), query)

    def test_card_contains_source_timestamp_and_real_values(self):
        today = datetime.now(TAIPEI).date()
        with patch('scripts.direct_streak.fetch_days', return_value=({today: 3}, today)):
            card = build_card()
        validate(card, CARDS['streak'][1])
        root = ET.fromstring(card)
        texts = [element.text.strip() for element in root.iter(SVG + 'text')]
        self.assertEqual(texts[0], '3')
        self.assertEqual(texts[5], '1')
        self.assertIn('GitHub API checked:', texts[-1])
        self.assertIn('GitHub GraphQL', root.find(SVG + 'metadata').text)

    def test_immutable_paths_change_only_when_bytes_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cards = root / 'assets/readme-cards'
            cards.mkdir(parents=True)
            stems = ['productive-time-animated-v2' if name == 'productive-time' else name for name in CARDS]
            (root / 'README.md').write_text('\n'.join(f'assets/readme-cards/{stem}.svg' for stem in stems))
            for stem in stems:
                (cards / (stem + '.svg')).write_bytes(b'first')
            publish_versions(root)
            initial = (root / 'README.md').read_text()
            publish_versions(root)
            self.assertEqual(initial, (root / 'README.md').read_text())
            (cards / 'streak.svg').write_bytes(b'new data')
            publish_versions(root)
            self.assertNotEqual(initial, (root / 'README.md').read_text())
            self.assertEqual(len(list(cards.glob('streak-*.svg'))), 1)


if __name__ == '__main__':
    unittest.main()
