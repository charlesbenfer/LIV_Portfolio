"""
Diagnostic: dump raw <main> text for each stat after applying 2025 Riyadh filter.
This tells us whether data is present but in a different format, or truly absent.
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from liv_scraper import _new_page, BASE_URL, STAT_PAGES
import time


def apply_filter(page, season_str, event_display):
    # Season switch
    year_btns = [b for b in page.query_selector_all('button')
                 if b.inner_text().strip() in ('2022','2023','2024','2025','2026')]
    cur = year_btns[0].inner_text().strip() if year_btns else 'none'
    print(f'    Season button shows: {cur!r}')
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
                time.sleep(1.5)
                break

    # Check what event button shows after season switch
    event_btns = [b for b in page.query_selector_all('button')
                  if b.inner_text().strip().lower() in ('all events', event_display.lower())]
    cur_event = event_btns[0].inner_text().strip() if event_btns else 'NONE FOUND'
    print(f'    Event button shows:  {cur_event!r}')

    # Open event dropdown
    for b in page.query_selector_all('button'):
        txt = b.inner_text().strip().lower()
        if txt == 'all events' or txt == event_display.lower():
            b.click()
            time.sleep(1.0)
            break

    # Find and click event in dropdown
    found = False
    dropdown_items = [b.inner_text().strip() for b in page.query_selector_all('button, li, option')
                      if b.inner_text().strip() and len(b.inner_text().strip()) < 50]
    print(f'    Dropdown items after open: {dropdown_items[:20]}')

    for b in page.query_selector_all('button, li, option'):
        if b.inner_text().strip() == event_display:
            b.click()
            found = True
            try:
                page.wait_for_load_state('networkidle', timeout=8000)
            except PlaywrightTimeout:
                pass
            # Wait until player data actually renders
            try:
                page.wait_for_function(
                    "() => { const m = document.querySelector('main'); "
                    "return m && m.innerText.split('\\n').filter(l => l.trim()).length > 10; }",
                    timeout=12000,
                )
            except PlaywrightTimeout:
                pass
            break

    return found


with sync_playwright() as pw:
    browser, page = _new_page(pw)

    for stat_key, path in STAT_PAGES.items():
        url = f'{BASE_URL}{path}'
        print(f'\n{"="*60}')
        print(f'[{stat_key}] {url}')

        try:
            page.goto(url, wait_until='networkidle', timeout=35000)
        except PlaywrightTimeout:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(2.0)

        ok = apply_filter(page, '2025', 'Riyadh')
        print(f'    Filter applied: {ok}')

        # Dump raw main text
        try:
            text = page.inner_text('main')
        except Exception:
            text = page.inner_text('body')

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        print(f'    Total lines after filter: {len(lines)}')
        print(f'    First 30 lines:')
        for i, l in enumerate(lines[:30]):
            print(f'      [{i:2d}] {l!r}')

    browser.close()
