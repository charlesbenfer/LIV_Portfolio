"""
Diagnostic: dump the full event dropdown for each season year.
This tells us the EXACT display names the LIV stats page uses —
which is what SLUG_TO_UI display names must match.

Run with:
    python _diag_dropdown.py
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from liv_scraper import _new_page, BASE_URL, _norm, _ALL_KNOWN_EVENT_NAMES
import time

SEASONS = ['2025', '2024', '2023', '2022']


def dump_events_for_season(page, season_str: str):
    """Navigate to drive-distance stats, switch to season_str, dump dropdown."""
    page.goto(f'{BASE_URL}/stats/drive-distance', wait_until='networkidle', timeout=35000)
    time.sleep(2.5)

    # ── Season switch ──────────────────────────────────────────────────────────
    year_btns = [b for b in page.query_selector_all('button')
                 if b.inner_text().strip() in ('2022', '2023', '2024', '2025', '2026')]
    cur = year_btns[0].inner_text().strip() if year_btns else 'NONE'
    print(f'  Season button shows: {cur!r}')

    if year_btns and cur != season_str:
        year_btns[0].click()
        time.sleep(0.8)
        for b in page.query_selector_all('button, li'):
            if b.inner_text().strip() == season_str:
                b.click()
                try:
                    page.wait_for_load_state('networkidle', timeout=6000)
                except PlaywrightTimeout:
                    pass
                time.sleep(2.0)
                break

    # Confirm season switch
    year_btns2 = [b for b in page.query_selector_all('button')
                  if b.inner_text().strip() in ('2022', '2023', '2024', '2025', '2026')]
    cur2 = year_btns2[0].inner_text().strip() if year_btns2 else 'NONE'
    print(f'  Season button after switch: {cur2!r}')

    # ── Find the event dropdown button ─────────────────────────────────────────
    event_btn = None
    for b in page.query_selector_all('button'):
        txt_norm = _norm(b.inner_text()).lower()
        if txt_norm == 'all events' or txt_norm in _ALL_KNOWN_EVENT_NAMES:
            event_btn = b
            break

    if event_btn is None:
        print('  ⚠ Event button NOT FOUND — dumping all buttons:')
        for b in page.query_selector_all('button'):
            txt = b.inner_text().strip()
            if txt and 2 < len(txt) < 60:
                print(f'    button: {txt!r}')
        return

    print(f'  Event button shows: {event_btn.inner_text().strip()!r}')

    # ── Open the dropdown ──────────────────────────────────────────────────────
    event_btn.click()
    time.sleep(1.5)

    # ── Collect all dropdown items ─────────────────────────────────────────────
    seen = set()
    items = []
    for b in page.query_selector_all('button, li, option'):
        txt = b.inner_text().strip()
        if (txt and 2 < len(txt) < 60
                and txt not in ('2022', '2023', '2024', '2025', '2026')
                and txt not in seen):
            seen.add(txt)
            items.append(txt)

    print(f'  Dropdown has {len(items)} items:')
    for item in items:
        in_known = _norm(item).lower() in _ALL_KNOWN_EVENT_NAMES
        marker = '✓' if in_known else '✗ NOT IN SLUG_TO_UI'
        print(f'    {item!r}  {marker}')


with sync_playwright() as pw:
    browser, page = _new_page(pw)

    for season in SEASONS:
        print(f'\n{"=" * 50}')
        print(f'Season: {season}')
        print('=' * 50)
        dump_events_for_season(page, season)

    browser.close()
