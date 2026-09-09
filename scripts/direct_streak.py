"""Build the streak card directly from GitHub, without a card-service cache."""

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

TAIPEI = timezone(timedelta(hours=8))
SVG = '{http://www.w3.org/2000/svg}'
USER = 'Yen-Lung-Huang'


def graphql(query):
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError('GitHub API token is required')
    request = Request('https://api.github.com/graphql',
                      data=json.dumps({'query': query}).encode(), headers={
                          'Authorization': 'Bearer ' + token,
                          'Content-Type': 'application/json',
                          'User-Agent': 'direct-profile-streak',
                          'Cache-Control': 'no-cache',
                      })
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    if payload.get('errors') or not payload.get('data', {}).get('user'):
        raise ValueError('Incomplete GitHub GraphQL response')
    return payload['data']['user']


def fetch_days(now, query=graphql):
    identity = query('query { user(login: "' + USER + '") { createdAt '
                     'contributionsCollection { contributionYears } } }')
    created = date.fromisoformat(identity['createdAt'][:10])
    years = set(range(created.year, now.year + 1))
    years.update(identity['contributionsCollection']['contributionYears'])
    fields = []
    for year in sorted(years):
        end = f'{year}-12-31T23:59:59Z'
        if year == now.year:
            end = now.astimezone(timezone.utc).isoformat(timespec='seconds')
        fields.append(f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", '
                      f'to: "{end}") {{ contributionCalendar {{ weeks {{ '
                      'contributionDays { date contributionCount } } } }')
    data = query('query { user(login: "' + USER + '") { ' + ' '.join(fields) + ' } }')
    days = {}
    for year in sorted(years):
        calendar = data[f'y{year}']['contributionCalendar']
        year_days = {}
        for week in calendar['weeks']:
            for item in week['contributionDays']:
                day = date.fromisoformat(item['date'])
                count = item['contributionCount']
                if type(count) is not int or count < 0:
                    raise ValueError('Invalid contribution count')
                if day.year == year and day <= now.date():
                    year_days[day] = count
        # Reject partial calendars, rather than silently treating missing data as zero.
        required_end = (now.astimezone(timezone.utc).date() if year == now.year
                        else date(year, 12, 31))
        cursor = date(year, 1, 1)
        while cursor <= required_end:
            if cursor not in year_days:
                raise ValueError('Incomplete contribution calendar')
            cursor += timedelta(days=1)
        days.update(year_days)
    # Taipei can be one calendar day ahead of the GitHub UTC collection.
    days.setdefault(now.date(), 0)
    return days, created


def calculate(days, today):
    first = min(days)
    longest = (0, None, None)
    run = 0
    start = None
    cursor = first
    while cursor <= today:
        if days.get(cursor, 0) > 0:
            if not run:
                start = cursor
            run += 1
            if run > longest[0]:
                longest = (run, start, cursor)
        else:
            run = 0
        cursor += timedelta(days=1)
    end = today if days.get(today, 0) else today - timedelta(days=1)
    cursor = end
    current = 0
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return {
        'total': sum(value for day, value in days.items() if day <= today),
        'current': (current, cursor + timedelta(days=1), end) if current else (0, None, None),
        'longest': longest,
    }


def date_label(day):
    return f'{day:%b} {day.day}, {day.year}'


def range_label(streak):
    _, start, end = streak
    if start is None:
        return 'No active streak'
    return date_label(start) if start == end else f'{date_label(start)} - {date_label(end)}'


def build_card(_url=None):
    now = datetime.now(TAIPEI)
    days, created = fetch_days(now)
    stats = calculate(days, now.date())
    root = ET.fromstring((Path(__file__).parent / 'templates/streak.svg').read_bytes())
    texts = list(root.iter(SVG + 'text'))
    if len(texts) != 9:
        raise ValueError('Unexpected streak template')
    for index, value in {
        0: f"{stats['total']:,}", 2: f'{date_label(created)} - Present',
        4: range_label(stats['current']), 5: str(stats['current'][0]),
        6: str(stats['longest'][0]), 8: range_label(stats['longest']),
    }.items():
        texts[index].text = value
    texts[4].set('font-size', '10px')
    root.set('height', '206px')
    root.set('viewBox', '0 0 478 206')
    ET.SubElement(root, SVG + 'rect', {'x': '0', 'y': '186', 'width': '478',
                                     'height': '20', 'fill': '#151515'})
    fetched = datetime.now(TAIPEI).isoformat(timespec='seconds')
    footer = ET.SubElement(root, SVG + 'text', {
        'x': '239', 'y': '199', 'text-anchor': 'middle', 'fill': '#9E9E9E',
        'font-family': 'Segoe UI, sans-serif', 'font-size': '10px',
    })
    footer.text = 'GitHub API checked: ' + fetched.replace('T', ' ')
    metadata = ET.SubElement(root, SVG + 'metadata')
    metadata.text = json.dumps({'source': 'GitHub GraphQL', 'fetched_at': fetched,
                                'today': now.date().isoformat(),
                                'recent_days': {day.isoformat(): count for day, count in sorted(days.items())
                                                if day >= now.date() - timedelta(days=7)}})
    ET.register_namespace('', SVG[1:-1])
    return ('\n'.join(line.rstrip() for line in ET.tostring(root, encoding='unicode').splitlines()) + '\n').encode()
