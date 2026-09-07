"""Refresh public card snapshots; never replace a good image with a failed response."""

import os
from pathlib import Path
import re
import tempfile
import time
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG = '{http://www.w3.org/2000/svg}'
CARDS = {
    'github-stats': ('https://github-readme-stats-yen-lung-huang.vercel.app/api?username=Yen-Lung-Huang&show_icons=true&theme=radical&title_color=39FF14&ring_color=FF2D55&include_all_commits=true&count_private=true&rank_icon=github&cache_seconds=900', ('Total Stars', 'Total Commits')),
    'top-languages': ('https://github-readme-stats-yen-lung-huang.vercel.app/api/top-langs/?username=Yen-Lung-Huang&layout=compact&theme=ambient_gradient&bg_color=20,0D1B2A,1B263B,415A77&langs_count=8&cache_seconds=900', ('Most Used Languages',)),
    'streak': ('https://github-readme-streak-stats-yen-lung.vercel.app?user=Yen-Lung-Huang&theme=dark&ring=FFB000&fire=FF2D55&currStreakLabel=FFB000&card_width=478&card_height=186', ('Total Contributions', 'Current Streak', 'Longest Streak')),
    'productive-time': ('https://github-profile-summary-cards-yen-lu.vercel.app/api/cards/productive-time?username=Yen-Lung-Huang&theme=dark&utcOffset=8', ('Commits',)),
}


def validate(data, expected):
    if not 100 <= len(data) <= 2_000_000:
        raise ValueError('Invalid image size')
    if re.search(br'<!DOCTYPE|<!ENTITY', data, re.I):
        raise ValueError('XML declarations are not allowed')
    root = ET.fromstring(data)
    if root.tag != SVG + 'svg':
        raise ValueError('Response is not an SVG document')
    for attr in ('width', 'height'):
        value = root.get(attr, '')
        if not re.fullmatch(r'\d+(?:\.\d+)?(?:px)?', value):
            raise ValueError('Missing explicit dimensions')
        if not 1 <= float(value.removesuffix('px')) <= 4096:
            raise ValueError('Invalid dimensions')
    text = ' '.join(root.itertext())
    if re.search(r'bad credentials|rate limit|something went wrong|no more github_token|deployment_paused|could not fetch|error|exception', text, re.I):
        raise ValueError('Upstream returned an error card')
    if any(label not in text for label in expected):
        raise ValueError('Expected card labels are missing')
    if not re.search(r'\d', ' '.join(' '.join(e.itertext()) for e in root.iter(SVG + 'text'))):
        raise ValueError('Card has no numeric data')
    for element in root.iter():
        if element.tag in (SVG + 'script', SVG + 'foreignObject'):
            raise ValueError('Active SVG content is not allowed')
        if any(key.lower().startswith('on') for key in element.attrib):
            raise ValueError('SVG event handlers are not allowed')


def download(url):
    request = Request(url, headers={'User-Agent': 'readme-card-refresh', 'Accept': 'image/svg+xml'})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError('Unexpected HTTP status')
        if response.headers.get_content_type() != 'image/svg+xml':
            raise ValueError('Unexpected Content-Type')
        return response.read(2_000_001)


def refresh(path, url, expected, fetch=download, sleep=time.sleep):
    for attempt in range(3):
        try:
            data = fetch(url)
            validate(data, expected)
            if path.exists() and path.read_bytes() == data:
                return True
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
                    temporary = Path(file.name)
                    file.write(data)
                os.replace(temporary, path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            return True
        except Exception as error:
            # Do not log upstream bodies or URLs that might contain sensitive data.
            print(f'{path.name}: attempt {attempt + 1} failed ({type(error).__name__})')
            if attempt < 2:
                sleep(5 * (attempt + 1))
    print(f'::warning::{path.name}: refresh failed; existing image left untouched')
    return False


def main():
    failed = []
    for name, (url, expected) in CARDS.items():
        if not refresh(ROOT / 'assets/readme-cards' / (name + '.svg'), url, expected):
            failed.append(name)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as file:
            file.write('## README cards\n' + ('Failed (cached images retained): ' + ', '.join(failed) if failed else 'All four images validated successfully.') + '\n')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
