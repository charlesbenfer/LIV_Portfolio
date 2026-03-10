"""
liv_scraper.py — LIV Golf data scraper using Playwright.

Scrapes three data sources from livgolf.com (robots.txt: Allow /stats, /schedule):
  1. Season stats  (/stats/{category}?season=YYYY)  — full-season aggregates
  2. Per-event stats (/stats/{category}, then UI-select event) — single-event stats
  3. Event leaderboards (/schedule/{slug}/leaderboard) — round scores, all events 2022–present

Both stats and leaderboard pages render via Next.js RSC; we use a headless
Chromium browser to hydrate the page, then parse the inner text of <main>.
Per-event stats require a UI interaction: click the season dropdown → select
year, then click the "All events" dropdown → select the event name.

Usage:
    python liv_scraper.py                          # full run: season stats + all leaderboards
    python liv_scraper.py --stats-only             # season stats only
    python liv_scraper.py --leaderboards-only      # leaderboards only
    python liv_scraper.py --event-stats-only       # per-event stats only
    python liv_scraper.py --season 2025            # leaderboards for one season
    python liv_scraper.py --seasons 2024 2025      # leaderboards for multiple seasons
    python liv_scraper.py --event riyadh-2025      # per-event stats for one event

Output (saved to ./data/):
    liv_season_stats.csv     — one row per player per season, wide on stat category
    liv_event_stats.csv      — one row per player per event, wide on stat category
    liv_event_results.csv    — one row per player per event, with R1/R2/R3/total
"""

import argparse
import re
import os
import time
import unicodedata
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

STATS_CSV   = os.path.join(DATA_DIR, 'liv_season_stats.csv')
RESULTS_CSV = os.path.join(DATA_DIR, 'liv_event_results.csv')

BASE_URL = 'https://www.livgolf.com'

# ── Known event slugs ─────────────────────────────────────────────────────────
KNOWN_EVENTS: dict[int, list[str]] = {
    2022: [
        'london-2022',
        'portland-2022',
        'bedminster-2022',
        'boston-2022',
        'chicago-2022',
        'bangkok-2022',
        'jeddah-2022',
    ],
    2023: [
        'mayakoba-2023',
        'tucson-2023',
        'orlando-2023',
        'adelaide-2023',
        'singapore-2023',
        'tulsa-2023',
        'dc-2023',
        'valderrama-2023',  # Andalucía
        'london-2023',
        'greenbrier-2023',
        'bedminster-2023',
        'chicago-2023',
        'jeddah-2023',
    ],
    2024: [
        'mayakoba-2024',
        'las-vegas-2024',
        'riyadh-2024',      # Saudi event; dropdown shows "Jeddah"
        'hong-kong-2024',
        'miami-2024',
        'adelaide-2024',
        'singapore-2024',
        'houston-2024',
        'nashville-2024',
        'greenbrier-2024',
        'andalucia-2024',
        'uk-2024',
        'chicago-2024',
    ],
    2025: [
        'riyadh-2025', 'adelaide-2025', 'hong-kong-2025', 'singapore-2025',
        'miami-2025', 'mexico-city-2025', 'korea-2025', 'va-2025',
        'dallas-2025', 'andalucia-2025', 'uk-2025', 'chicago-2025',
        'indianapolis-2025', 'team-championship-michigan-2025',
    ],
    2026: [
        'riyadh-2026', 'adelaide-2026', 'hong-kong-2026',
    ],
}

# ── Stats categories ───────────────────────────────────────────────────────────
STAT_PAGES: dict[str, str] = {
    'drive_distance':       '/stats/drive-distance',
    'fairway_pct':          '/stats/fairway-hits',
    'gir_pct':              '/stats/greens-in-regulation',
    'scrambling_pct':       '/stats/scrambling',
    'birdies_per_round':    '/stats/birdies',
    'putting_avg':          '/stats/putting-average',
    'eagles':               '/stats/eagles',
}

EVENT_STATS_CSV = os.path.join(DATA_DIR, 'liv_event_stats.csv')

# Slug → (season_year_str, short_display_name) for the UI dropdowns.
# Display names must match EXACTLY what the event filter dropdown shows on livgolf.com.
SLUG_TO_UI: dict[str, tuple[str, str]] = {
    # 2026
    'riyadh-2026':      ('2026', 'Riyadh'),
    'adelaide-2026':    ('2026', 'Adelaide'),
    'hong-kong-2026':   ('2026', 'Hong Kong'),
    # 2025
    'riyadh-2025':      ('2025', 'Riyadh'),
    'adelaide-2025':    ('2025', 'Adelaide'),
    'hong-kong-2025':   ('2025', 'Hong Kong'),
    'singapore-2025':   ('2025', 'Singapore'),
    'miami-2025':       ('2025', 'Miami'),
    'mexico-city-2025': ('2025', 'Mexico City'),
    'korea-2025':       ('2025', 'Korea'),
    'va-2025':          ('2025', 'Virginia'),
    'dallas-2025':      ('2025', 'Dallas'),
    'andalucia-2025':   ('2025', 'Andalucía'),
    'uk-2025':          ('2025', 'United Kingdom'),
    'chicago-2025':     ('2025', 'Chicago'),
    'indianapolis-2025':('2025', 'Indianapolis'),
    # 2024
    'mayakoba-2024':    ('2024', 'Mayakoba'),
    'las-vegas-2024':   ('2024', 'Las Vegas'),
    'riyadh-2024':      ('2024', 'Jeddah'),   # Saudi event; dropdown shows "Jeddah"
    'hong-kong-2024':   ('2024', 'Hong Kong'),
    'miami-2024':       ('2024', 'Miami'),
    'adelaide-2024':    ('2024', 'Adelaide'),
    'singapore-2024':   ('2024', 'Singapore'),
    'houston-2024':     ('2024', 'Houston'),
    'nashville-2024':   ('2024', 'Nashville'),
    'greenbrier-2024':  ('2024', 'Greenbrier'),
    'andalucia-2024':   ('2024', 'Andalucía'),
    'uk-2024':          ('2024', 'United Kingdom'),
    'chicago-2024':     ('2024', 'Chicago'),
    # 2023
    'mayakoba-2023':    ('2023', 'Mayakoba'),
    'tucson-2023':      ('2023', 'Tucson'),
    'orlando-2023':     ('2023', 'Orlando'),
    'adelaide-2023':    ('2023', 'Adelaide'),
    'singapore-2023':   ('2023', 'Singapore'),
    'tulsa-2023':       ('2023', 'Tulsa'),
    'dc-2023':          ('2023', 'DC'),
    'valderrama-2023':  ('2023', 'Andalucía'),
    'london-2023':      ('2023', 'London'),
    'greenbrier-2023':  ('2023', 'Greenbrier'),
    'bedminster-2023':  ('2023', 'Bedminster'),
    'chicago-2023':     ('2023', 'Chicago'),
    'jeddah-2023':      ('2023', 'Jeddah'),
    # 2022
    'london-2022':      ('2022', 'London'),
    'portland-2022':    ('2022', 'Portland'),
    'bedminster-2022':  ('2022', 'Bedminster'),
    'boston-2022':      ('2022', 'Boston'),
    'chicago-2022':     ('2022', 'Chicago'),
    'bangkok-2022':     ('2022', 'Bangkok'),
    'jeddah-2022':      ('2022', 'Jeddah'),
}

# All NFC-normalized lowercase display names — used to identify the event
# dropdown button regardless of which event the SPA currently shows.
_ALL_KNOWN_EVENT_NAMES: frozenset[str] = frozenset(
    unicodedata.normalize('NFC', v[1]).lower() for v in SLUG_TO_UI.values()
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """NFC-normalize and strip a string for reliable Unicode comparison.

    LIV site may render accented characters (e.g. Andalucía) with a different
    Unicode normalization form than our Python string literals. NFC normalization
    ensures both sides use precomposed characters before comparing.
    """
    return unicodedata.normalize('NFC', s.strip())


# ── Browser factory ────────────────────────────────────────────────────────────

def _new_page(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        extra_http_headers={
            'Referer':        'https://www.livgolf.com/',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    )
    return browser, context.new_page()


def _load_page(page, url: str, settle_secs: float = 2.5) -> str:
    """Navigate to URL, wait for network idle, return <main> inner text."""
    try:
        page.goto(url, wait_until='networkidle', timeout=35000)
    except PlaywrightTimeout:
        # Fallback: wait for DOM load + fixed delay
        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(settle_secs + 1)
    time.sleep(settle_secs)
    try:
        return page.inner_text('main')
    except Exception:
        return page.inner_text('body')


# ── Stats parser ───────────────────────────────────────────────────────────────

def _parse_stats_text(text: str, stat_key: str, season: str) -> list[dict]:
    """
    Parse the raw inner-text from a stats page into player records.

    Observed DOM layout (each separated by newlines):
        POS  Player  Average yards
        1
        Josele
        Ballester
        Fireballs GC
        314.4
        2
        Victor
        ...
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Drop header lines up to and including the column labels
    # Find the first integer line — that's where data begins
    start = 0
    for i, line in enumerate(lines):
        if re.match(r'^\d+$', line):
            start = i
            break

    records = []
    i = start
    while i < len(lines):
        line = lines[i]

        # Position line: plain integer or T+integer
        if not re.match(r'^T?\d+$', line):
            i += 1
            continue

        pos = line
        i += 1

        # Collect the next 2-4 non-numeric lines as name parts
        name_parts = []
        team = None
        while i < len(lines) and len(name_parts) < 4:
            tok = lines[i]
            # Stop at a numeric value (the stat value)
            clean = tok.replace(',', '').replace('%', '').replace('+', '')
            try:
                float(clean)
                break
            except ValueError:
                pass
            # "C" alone = captain marker, skip
            if tok == 'C':
                i += 1
                continue
            # Looks like a name word (starts with capital, reasonable length)
            if re.match(r'^[A-Z][a-zA-Z\s\'\-\.]+$', tok) and len(tok) > 1:
                name_parts.append(tok)
                i += 1
            else:
                i += 1

        # The last name part that contains "GC", "Club", "Guards", etc. is team
        if len(name_parts) >= 2:
            # Heuristic: team contains golf-club keywords or is the last element after ≥2 name words
            team_kws = ['gc', 'club', 'guards', 'ripper', 'smash', 'torque', 'legion',
                        'crushers', 'aces', 'goats', 'majesticks', 'hyflyers', 'stinger',
                        'niblicks', 'punch', 'iron', 'range', 'fireballs', 'cleeks',
                        'southern', 'korean', 'wild', 'card']
            for j in range(len(name_parts) - 1, -1, -1):
                if any(kw in name_parts[j].lower() for kw in team_kws):
                    team = name_parts.pop(j)
                    break

        player_name = ' '.join(name_parts).strip()

        # Next numeric token = stat value.
        # Some stat pages render extra tokens between the team name and the stat
        # value — e.g. a fraction "17/26" (scrambling attempts/made) or a dash
        # "—" (no data).  We skip up to 3 such non-parseable tokens before
        # giving up so that the following percentage/average is still captured.
        # Fractions X/Y are also converted directly (→ percentage) as a fallback
        # in case no separate decimal value follows.
        value = None
        skipped = 0
        while i < len(lines) and skipped < 4:
            tok = lines[i]
            clean = tok.replace(',', '').replace('%', '').replace('+', '').replace('−', '-').replace('–', '-')
            try:
                value = float(clean)
                i += 1
                break
            except ValueError:
                # Fraction token "X/Y" — convert to percentage as fallback value,
                # but continue scanning in case a decimal percentage follows.
                if '/' in tok:
                    parts = tok.split('/')
                    if len(parts) == 2:
                        try:
                            num, den = float(parts[0]), float(parts[1])
                            if den > 0:
                                value = round(num / den * 100, 2)
                        except ValueError:
                            pass
                    i += 1
                    skipped += 1
                    continue
                # Dash / no-data markers — skip silently.
                if tok in ('—', '–', '-', 'N/A', 'DNP'):
                    i += 1
                    skipped += 1
                    continue
                # Any other non-numeric token means we've drifted into the
                # next player's data; stop here.
                i += 1
                break

        # Special handling: the putting-average page shows two numbers per player —
        # (1) GIR putts count (~218 total) then (2) per-hole average (~1.77).
        # The first pass captures the count; advance past it to get the average.
        if stat_key == 'putting_avg' and value is not None and value > 10 and i < len(lines):
            tok = lines[i]
            if '.' in tok:  # per-hole averages always contain a decimal point
                clean = tok.replace(',', '').replace('%', '').replace('+', '')
                try:
                    second = float(clean)
                    if 1.0 <= second <= 3.0:  # sanity: professional putts/hole range
                        value = second
                        i += 1
                except ValueError:
                    pass

        if player_name and value is not None and len(player_name) > 3:
            records.append({
                'playerName': player_name,
                'team':       team or '',
                'position':   pos,
                'stat':       stat_key,
                'value':      value,
                'season':     season,
            })

    return records


# ── Leaderboard parser ─────────────────────────────────────────────────────────

def _parse_leaderboard_text(text: str, slug: str) -> list[dict]:
    """
    Parse the raw inner-text of a leaderboard page.

    Observed DOM layout:
        1
        Adrian
        Meronk
        Cleeks Golf Club
        F          ← status (F = finished, or hole number for live)
        -10        ← R1
        -6         ← R2
        -1         ← R3
        -17        ← total
        T2
        Jon
        Rahm
        C          ← captain marker (optional)
        Legion XIII
        ...
    """
    m = re.search(r'(\d{4})', slug)
    year = int(m.group(1)) if m else 0
    event_name = slug.replace('-', ' ').title()

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Find start: first position token after the header section
    # Header contains "Pos", "Player", "R1", "R2", "R3", "Tot" labels
    start = 0
    for i, line in enumerate(lines):
        if re.match(r'^T?\d+$', line) and i > 3:
            start = i
            break

    records = []
    i = start

    def is_score(s: str) -> bool:
        """True if string looks like a to-par score: -12, +3, E, 0"""
        return bool(re.match(r'^[+\-−–]?\d+$', s)) or s in ('E', '0')

    def score_val(s: str) -> int | None:
        if s == 'E':
            return 0
        clean = s.replace('−', '-').replace('–', '-')
        try:
            return int(clean)
        except ValueError:
            return None

    while i < len(lines):
        line = lines[i]
        if not re.match(r'^T?\d+$', line):
            i += 1
            continue

        pos = line
        i += 1

        # Collect name parts and team
        raw = []
        while i < len(lines) and len(raw) < 6:
            tok = lines[i]
            # Stop when we hit a score-like token or 'F' (finished)
            if is_score(tok) or tok == 'F':
                break
            raw.append(tok)
            i += 1

        # Skip 'F' / status token
        if i < len(lines) and (lines[i] == 'F' or re.match(r'^\d+$', lines[i]) and int(lines[i]) <= 18):
            i += 1

        # Collect up to 3 round scores + total
        scores = []
        while i < len(lines) and len(scores) < 4:
            tok = lines[i]
            if is_score(tok):
                scores.append(score_val(tok))
                i += 1
            else:
                break

        # Parse name / team from raw tokens
        # "C" = captain marker, skip; team keywords same as stats parser
        team_kws = ['gc', 'club', 'guards', 'ripper', 'smash', 'torque', 'legion',
                    'crushers', 'aces', 'goats', 'majesticks', 'hyflyers', 'stinger',
                    'niblicks', 'punch', 'iron', 'range', 'fireballs', 'cleeks',
                    'southern', 'korean', 'wild']
        name_parts = []
        team = None
        for tok in raw:
            if tok == 'C':
                continue
            if any(kw in tok.lower() for kw in team_kws) and len(tok) > 3:
                team = tok
            else:
                name_parts.append(tok)

        player_name = ' '.join(name_parts).strip()

        if player_name and len(player_name) > 3:
            r1 = scores[0] if len(scores) > 0 else None
            r2 = scores[1] if len(scores) > 1 else None
            r3 = scores[2] if len(scores) > 2 else None
            total = scores[3] if len(scores) > 3 else (
                sum(s for s in [r1, r2, r3] if s is not None) if any(s is not None for s in [r1, r2, r3]) else None
            )
            records.append({
                'event_slug':  slug,
                'event_name':  event_name,
                'year':        year,
                'playerName':  player_name,
                'team':        team or '',
                'position':    pos,
                'R1':          r1,
                'R2':          r2,
                'R3':          r3,
                'total_to_par': total,
                'scraped_at':  datetime.now().isoformat(),
            })

    return records


# ── Orchestrators ──────────────────────────────────────────────────────────────

def _apply_season_filter(page, season_str: str) -> bool:
    """
    Click the season-year dropdown and select season_str.

    The LIV stats site is a Next.js SPA — adding ?season=YYYY to the URL does
    NOT change the displayed data. The year must be selected via the UI button.
    Returns True if the target season is active after the call.
    """
    year_btns = [b for b in page.query_selector_all('button')
                 if b.inner_text().strip() in ('2022', '2023', '2024', '2025', '2026')]
    if not year_btns:
        return False

    cur_year = year_btns[0].inner_text().strip()
    if cur_year == season_str:
        return True  # already on the correct year

    # Open the year dropdown and select the target year
    year_btns[0].click()
    time.sleep(0.8)
    for b in page.query_selector_all('button, li'):
        if b.inner_text().strip() == season_str:
            b.click()
            try:
                page.wait_for_load_state('networkidle', timeout=6000)
            except PlaywrightTimeout:
                pass
            time.sleep(1.5)
            return True

    return False


def scrape_all_stats(season: str = '2025') -> pd.DataFrame:
    """Scrape all 7 stat categories for a given season. Returns wide DataFrame."""
    all_records = []

    with sync_playwright() as pw:
        browser, page = _new_page(pw)

        for stat_key, path in STAT_PAGES.items():
            # Do NOT use ?season= URL param — LIV's SPA ignores it.
            # Navigate to the base URL and apply the season via the UI dropdown.
            url = f'{BASE_URL}{path}'
            print(f'  [{stat_key}]', end=' ', flush=True)

            try:
                page.goto(url, wait_until='networkidle', timeout=35000)
            except PlaywrightTimeout:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(2.0)

            ok = _apply_season_filter(page, season)
            if not ok:
                print(f'(season filter failed — skipping)', flush=True)
                continue

            # Wait for player position numbers to appear (confirms data has rendered)
            try:
                page.wait_for_function(
                    "() => { "
                    "  const m = document.querySelector('main'); "
                    "  if (!m) return false; "
                    "  const lines = m.innerText.split('\\n').map(l => l.trim()).filter(l => l); "
                    "  return lines.some(l => /^\\d+$/.test(l) && +l > 0 && +l < 100); "
                    "}",
                    timeout=15000,
                )
            except PlaywrightTimeout:
                pass

            try:
                text = page.inner_text('main')
            except Exception:
                text = page.inner_text('body')

            records = _parse_stats_text(text, stat_key, season)
            print(f'→ {len(records)} players')
            all_records.extend(records)

        browser.close()

    if not all_records:
        print('WARNING: no stats data captured')
        return pd.DataFrame()

    long_df = pd.DataFrame(all_records)
    # Pivot: one row per player+season, one column per stat
    wide_df = long_df.pivot_table(
        index=['playerName', 'team', 'season'],
        columns='stat',
        values='value',
        aggfunc='first',
    ).reset_index()
    wide_df.columns.name = None
    return wide_df


def _apply_event_filter(page, season_str: str, event_display: str) -> bool:
    """
    Apply the season + event filter dropdowns on the current stats page.

    Always opens the event dropdown and re-selects the target — we do NOT skip
    based on button text because the SPA may retain a stale button label while
    displaying unfiltered data, leading to 0-player results.

    Returns True if the event was successfully selected, False otherwise.
    """
    target_norm = _norm(event_display)

    # ── Season switch ─────────────────────────────────────────────────────────
    # Year picker is a dropdown — clicking the trigger reveals year options.
    # Always re-click the target year; DOM button order doesn't reliably indicate
    # which year is currently active in the SPA.

    def _wait_for_year_data(timeout_s: float = 35.0) -> None:
        """
        Wait until player position numbers appear in <main>.

        The "All events" button can persist from the previous year's state, so
        position numbers (1, 2, 3…) are the reliable signal that data has loaded.
        """
        try:
            page.wait_for_function(
                "() => {"
                "  const m = document.querySelector('main');"
                "  if (!m) return false;"
                "  const lines = m.innerText.split('\\n').map(l => l.trim()).filter(l => l);"
                "  return lines.some(l => /^\\d+$/.test(l) && +l > 0 && +l < 200);"
                "}",
                timeout=int(timeout_s * 1000),
            )
        except PlaywrightTimeout:
            pass
        time.sleep(2.0)  # buffer after data appears

    def _click_year_option() -> bool:
        """Scan visible buttons and list items for the target year and click it."""
        for b in page.query_selector_all('button, li'):
            if b.inner_text().strip() == season_str:
                b.click()
                _wait_for_year_data()
                return True
        return False

    year_switched = False
    for _ in range(3):
        # Find the year dropdown trigger (the button that currently shows a year).
        year_trigger = None
        for b in page.query_selector_all('button'):
            if b.inner_text().strip() in ('2022', '2023', '2024', '2025', '2026'):
                year_trigger = b
                break

        if year_trigger is None:
            time.sleep(3.0)
            continue

        # Always open picker and re-select — avoids stale-state reads.
        year_trigger.click()
        time.sleep(3.5)  # wait for the dropdown list to render

        if _click_year_option():
            year_switched = True
            break

        # Year option not found in opened dropdown — close and retry.
        try:
            page.keyboard.press('Escape')
        except Exception:
            pass
        time.sleep(2.0)

    if not year_switched:
        print(f'\n    (season switch to {season_str} failed — '
              f'year option not found in picker)', flush=True)
        return False

    # ── Find event dropdown button ────────────────────────────────────────────
    # Recognise by matching against ALL known display names or "All Events".
    def _find_event_btn():
        for b in page.query_selector_all('button'):
            txt_norm = _norm(b.inner_text()).lower()
            if txt_norm == 'all events' or txt_norm in _ALL_KNOWN_EVENT_NAMES:
                return b
        return None

    event_btn = None
    for _ in range(4):
        event_btn = _find_event_btn()
        if event_btn is not None:
            break
        time.sleep(3.0)

    if event_btn is None:
        return False

    current_label = _norm(event_btn.inner_text())

    # If label already matches, confirm data has rendered before returning.
    if current_label == target_norm:
        try:
            page.wait_for_function(
                "() => { "
                "  const m = document.querySelector('main'); "
                "  if (!m) return false; "
                "  const lines = m.innerText.split('\\n').map(l => l.trim()).filter(l => l); "
                "  return lines.some(l => /^\\d+$/.test(l) && +l > 0 && +l < 100); "
                "}",
                timeout=8000,
            )
            return True
        except PlaywrightTimeout:
            # Data not visible even though label matches — fall through to re-select.
            pass

    # Open dropdown and select the target event.
    # 2025 has 13+ events; give extra time for the list to fully render.
    event_btn.click()
    time.sleep(4.0)

    found = False
    available = []
    for b in page.query_selector_all('button, li'):
        b_norm = _norm(b.inner_text())
        b_lower = b_norm.lower()
        if b_lower in _ALL_KNOWN_EVENT_NAMES or b_lower == 'all events':
            available.append(b_norm)
        if b_norm == target_norm:
            b.click()
            found = True
            try:
                page.wait_for_load_state('networkidle', timeout=8000)
            except PlaywrightTimeout:
                pass
            break

    if not found:
        # Close the open dropdown by pressing Escape, then report failure.
        try:
            page.keyboard.press('Escape')
        except Exception:
            pass
        print(f'\n    (event "{event_display}" not in dropdown; '
              f'available: {available})', flush=True)
        return False

    # Confirm player data has rendered after the selection.
    try:
        page.wait_for_function(
            "() => { "
            "  const m = document.querySelector('main'); "
            "  if (!m) return false; "
            "  const lines = m.innerText.split('\\n').map(l => l.trim()).filter(l => l); "
            "  return lines.some(l => /^\\d+$/.test(l) && +l > 0 && +l < 100); "
            "}",
            timeout=15000,
        )
    except PlaywrightTimeout:
        pass

    return True


def _scrape_slug_on_page(page, slug: str) -> pd.DataFrame:
    """
    Scrape per-event stats for one slug, reusing an already-open page.

    For each stat category:
      1. Navigate to the stat URL
      2. Apply season + event filter via _apply_event_filter
      3. If 0 players returned, reload and retry once
    """
    if slug not in SLUG_TO_UI:
        raise ValueError(f'Unknown slug: {slug!r}. Add it to SLUG_TO_UI.')

    season_str, event_display = SLUG_TO_UI[slug]
    print(f'  Per-event stats: {slug} → season={season_str}, event="{event_display}"')

    all_records = []

    for stat_key, path in STAT_PAGES.items():
        url = f'{BASE_URL}{path}'
        print(f'  [{stat_key}]', end=' ', flush=True)

        for attempt in range(2):  # up to 2 attempts per stat
            try:
                page.goto(url, wait_until='networkidle', timeout=35000)
            except PlaywrightTimeout:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(4.0)

            ok = _apply_event_filter(page, season_str, event_display)
            if not ok:
                if attempt == 0:
                    print(f'(filter failed, retrying…)', end=' ', flush=True)
                    time.sleep(5.0)
                    continue
                print(f'(filter failed — skipping)', flush=True)
                break

            try:
                text = page.inner_text('main')
            except Exception:
                text = page.inner_text('body')

            records = _parse_stats_text(text, stat_key, season_str)

            if len(records) == 0 and attempt == 0:
                # Got 0 players on first attempt — reload and retry once.
                print(f'(0 players, retrying…)', end=' ', flush=True)
                time.sleep(5.0)
                continue

            for r in records:
                r['event_slug'] = slug
                r['event_name'] = event_display
            print(f'→ {len(records)} players')
            all_records.extend(records)
            break

    if not all_records:
        print(f'  WARNING: no per-event stats captured for {slug}')
        return pd.DataFrame()

    long_df = pd.DataFrame(all_records)
    wide_df = long_df.pivot_table(
        index=['playerName', 'team', 'event_slug', 'event_name', 'season'],
        columns='stat',
        values='value',
        aggfunc='first',
    ).reset_index()
    wide_df.columns.name = None
    return wide_df


def scrape_event_stats(slug: str) -> pd.DataFrame:
    """
    Scrape per-event stats for a single event (standalone, opens its own browser).
    Used by --event CLI flag.
    """
    with sync_playwright() as pw:
        browser, page = _new_page(pw)
        df = _scrape_slug_on_page(page, slug)
        browser.close()
    return df


def scrape_all_event_stats(slugs: list[str] | None = None) -> pd.DataFrame:
    """
    Scrape per-event stats for all (or a specified list of) events.

    Reuses a single browser session for all events to avoid the cost of
    launching 49+ separate Chromium instances (which also triggers rate limiting).
    """
    if slugs is None:
        slugs = list(SLUG_TO_UI.keys())

    all_frames = []
    failed: list[str] = []

    with sync_playwright() as pw:
        browser, page = _new_page(pw)

        for i, slug in enumerate(slugs):
            print(f'\n[{i+1}/{len(slugs)}] {slug}')
            try:
                df = _scrape_slug_on_page(page, slug)
            except Exception as exc:
                print(f'  ERROR scraping {slug}: {exc}')
                failed.append(slug)
                df = pd.DataFrame()

            if not df.empty:
                all_frames.append(df)
            else:
                failed.append(slug)

            # Polite inter-event delay to avoid hammering the server.
            time.sleep(2.5)

        browser.close()

    if failed:
        # Deduplicate (empty df + exception both append to failed)
        unique_failed = list(dict.fromkeys(failed))
        print(f'\nEvents with no data captured: {unique_failed}')

    if not all_frames:
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    print(f'\nEvent stats total: {len(combined)} rows across {combined["event_slug"].nunique()} events')
    return combined


def scrape_all_leaderboards(seasons: list[int] | None = None) -> pd.DataFrame:
    """Scrape all event leaderboards. Returns long DataFrame (one row per player-event)."""
    if seasons is None:
        seasons = list(KNOWN_EVENTS.keys())

    slugs = [slug for s in seasons for slug in KNOWN_EVENTS.get(s, [])]
    print(f'  Scraping {len(slugs)} events across seasons {seasons}')

    all_records = []

    with sync_playwright() as pw:
        browser, page = _new_page(pw)

        for idx, slug in enumerate(slugs):
            url = f'{BASE_URL}/schedule/{slug}/leaderboard'
            print(f'  [{idx+1}/{len(slugs)}] {slug}')
            text = _load_page(page, url, settle_secs=2.0)
            records = _parse_leaderboard_text(text, slug)
            print(f'    → {len(records)} player rows')
            all_records.extend(records)
            time.sleep(1.2)  # polite delay

        browser.close()

    if not all_records:
        print('WARNING: no leaderboard data captured')
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f'  Total: {len(df)} rows, {df["event_slug"].nunique()} events, '
          f'{df["playerName"].nunique()} unique players')
    return df


# ── Save helpers ───────────────────────────────────────────────────────────────

def _validate_df(df: pd.DataFrame, key_cols: list[str], label: str) -> None:
    """Print shape, duplicate counts, and per-key-col value counts for QA."""
    print(f'\n  [QA] {label}: {len(df)} rows, {df.shape[1]} columns')
    dup_mask = df.duplicated(subset=key_cols, keep=False)
    n_dup = dup_mask.sum()
    if n_dup:
        print(f'  [QA] WARNING: {n_dup} rows share a duplicate key ({key_cols})')
        print(df[dup_mask][key_cols].drop_duplicates().head(10).to_string(index=False))
    else:
        print(f'  [QA] No duplicate keys — clean.')
    for col in key_cols:
        if col in df.columns:
            vals = df[col].value_counts(dropna=False)
            top = vals.head(5).to_dict()
            print(f'  [QA]   {col} top values: {top}')
    # Per-season player counts if 'season' is a key
    if 'season' in df.columns:
        season_counts = df.groupby('season')['playerName' if 'playerName' in df.columns else key_cols[0]].nunique()
        print(f'  [QA]   Unique players per season:\n{season_counts.to_string()}')


def save_and_merge(new_df: pd.DataFrame, path: str, key_cols: list[str]) -> pd.DataFrame:
    if new_df.empty:
        print(f'  No data to save → {path}')
        return new_df

    # Deduplicate incoming data before anything else.
    n_before = len(new_df)
    new_df = new_df.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
    if len(new_df) < n_before:
        print(f'  [QA] Dropped {n_before - len(new_df)} duplicate rows from new data before merge.')

    if os.path.exists(path):
        existing = pd.read_csv(path, low_memory=False)
        n_existing_before = len(existing)
        # Deduplicate existing first so combine_first gets a unique index.
        existing = existing.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
        if len(existing) < n_existing_before:
            print(f'  [QA] Dropped {n_existing_before - len(existing)} pre-existing duplicate rows.')

        # New values take priority; existing fills NaN gaps.
        # Both indices must be unique — duplicate keys cause a Cartesian expansion.
        new_idx = new_df.set_index(key_cols)
        existing_idx = existing.set_index(key_cols)
        combined = new_idx.combine_first(existing_idx).reset_index()

        # Final dedup guard — catches any edge cases from combine_first.
        n_combined_before = len(combined)
        combined = combined.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
        if len(combined) < n_combined_before:
            print(f'  [QA] Post-merge dedup removed {n_combined_before - len(combined)} extra rows.')
    else:
        combined = new_df

    _validate_df(combined, key_cols, os.path.basename(path))
    combined.to_csv(path, index=False)
    print(f'  Saved {len(combined)} rows → {path}')
    return combined


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Scrape LIV Golf data from livgolf.com')

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--stats-only',         action='store_true',
                      help='Season stats pages only')
    mode.add_argument('--leaderboards-only',  action='store_true',
                      help='Event leaderboards only')
    mode.add_argument('--event-stats-only',   action='store_true',
                      help='Per-event stats only (all known events in SLUG_TO_UI)')

    parser.add_argument('--season',  type=int, default=None,
                        help='Single season for leaderboards (e.g. 2025)')
    parser.add_argument('--seasons', type=int, nargs='+', default=None,
                        help='Multiple seasons for leaderboards (e.g. --seasons 2024 2025)')
    parser.add_argument('--stats-season', default=None,
                        help='Single season year for full-season stats (default: all years 2022–2026)')
    parser.add_argument('--stats-seasons', type=int, nargs='+', default=None,
                        help='Multiple season years for full-season stats (e.g. --stats-seasons 2024 2025)')
    parser.add_argument('--event', default=None,
                        help='Single event slug for per-event stats (e.g. riyadh-2025)')
    parser.add_argument('--events', nargs='+', default=None,
                        help='Multiple event slugs for per-event stats')
    args = parser.parse_args()

    targeting_specific_event = bool(args.event or args.events)
    do_season_stats  = not args.leaderboards_only and not args.event_stats_only and not targeting_specific_event
    do_leaderboards  = not args.stats_only and not args.event_stats_only and not targeting_specific_event
    do_event_stats   = args.event_stats_only or targeting_specific_event

    lb_seasons = [args.season] if args.season else (args.seasons or None)
    ev_slugs   = ([args.event] if args.event else None) or args.events or None

    print('=' * 60)
    print('LIV Golf Scraper')
    print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    if do_season_stats:
        if args.stats_season:
            stat_seasons = [args.stats_season]
        elif args.stats_seasons:
            stat_seasons = [str(y) for y in args.stats_seasons]
        else:
            stat_seasons = ['2022', '2023', '2024', '2025', '2026']
        for season_yr in stat_seasons:
            print(f'\n[Season Stats] season={season_yr}')
            stats_df = scrape_all_stats(season=season_yr)
            save_and_merge(stats_df, STATS_CSV, ['playerName', 'season'])

    if do_event_stats:
        slugs_to_run = ev_slugs or list(SLUG_TO_UI.keys())
        print(f'\n[Per-Event Stats] {len(slugs_to_run)} events')
        ev_stats_df = scrape_all_event_stats(slugs=slugs_to_run)
        save_and_merge(ev_stats_df, EVENT_STATS_CSV, ['event_slug', 'playerName'])

    if do_leaderboards:
        print(f'\n[Leaderboards] seasons={lb_seasons or "all"}')
        results_df = scrape_all_leaderboards(seasons=lb_seasons)
        save_and_merge(results_df, RESULTS_CSV, ['event_slug', 'playerName'])

    print('\n' + '=' * 60)
    print(f'Done: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Season stats:  {STATS_CSV}')
    print(f'  Event stats:   {EVENT_STATS_CSV}')
    print(f'  Leaderboards:  {RESULTS_CSV}')

    # ── Post-run data quality report ──────────────────────────────────────────
    print('\n' + '─' * 60)
    print('Post-run Data Quality Report')
    print('─' * 60)
    for csv_path, keys in [
        (STATS_CSV,    ['playerName', 'season']),
        (EVENT_STATS_CSV, ['event_slug', 'playerName']),
        (RESULTS_CSV,  ['event_slug', 'playerName']),
    ]:
        if not os.path.exists(csv_path):
            print(f'  {os.path.basename(csv_path)}: NOT FOUND')
            continue
        df = pd.read_csv(csv_path, low_memory=False)
        dup_count = df.duplicated(subset=keys, keep=False).sum()
        status = f'✓ clean' if dup_count == 0 else f'⚠ {dup_count} duplicate rows'
        print(f'  {os.path.basename(csv_path)}: {len(df)} rows — {status}')
        if 'season' in df.columns and 'playerName' in df.columns:
            season_summary = df.groupby('season')['playerName'].nunique()
            for yr, cnt in season_summary.items():
                print(f'    {yr}: {cnt} players')


if __name__ == '__main__':
    main()
