"""Check which stats have per-event data for 2026 Riyadh."""
from playwright.sync_api import sync_playwright
from liv_scraper import _new_page, BASE_URL
import time

def apply_filter(page, season_str, event_display):
    year_btns = [b for b in page.query_selector_all('button')
                 if b.inner_text().strip() in ('2022','2023','2024','2025','2026')]
    # 2026 is already the default, so season switch may not be needed
    if year_btns and year_btns[0].inner_text().strip() != season_str:
        year_btns[0].click()
        time.sleep(0.8)
        for b in page.query_selector_all('button, li'):
            if b.inner_text().strip() == season_str:
                b.click()
                try:
                    page.wait_for_load_state('networkidle', timeout=6000)
                except Exception:
                    pass
                time.sleep(1.5)
                break
    for b in page.query_selector_all('button'):
        if b.inner_text().strip().lower() in ('all events', event_display.lower()):
            b.click()
            time.sleep(0.8)
            break
    for b in page.query_selector_all('button, li'):
        if b.inner_text().strip() == event_display:
            b.click()
            try:
                page.wait_for_load_state('networkidle', timeout=8000)
            except Exception:
                pass
            time.sleep(2.5)
            return True
    return False

stats = [
    ('drive-distance',       'Drive Dist'),
    ('fairway-hits',         'Fairway'),
    ('greens-in-regulation', 'GIR'),
    ('scrambling',           'Scrambling'),
    ('birdies',              'Birdies'),
    ('putting-average',      'Putting'),
    ('eagles',               'Eagles'),
]

with sync_playwright() as pw:
    browser, page = _new_page(pw)
    for slug, label in stats:
        page.goto(f'{BASE_URL}/stats/{slug}', wait_until='networkidle', timeout=35000)
        time.sleep(2)
        apply_filter(page, '2026', 'Riyadh')
        text = page.inner_text('main')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        n_data = max(0, len(lines) - 6)
        print(f'{label}: {n_data} player rows {"✓" if n_data > 0 else "✗ (empty)"}')
        if n_data > 0:
            print(f'  Sample: {lines[6:10]}')
    browser.close()
