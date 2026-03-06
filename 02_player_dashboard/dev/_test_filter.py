from playwright.sync_api import sync_playwright
from liv_scraper import _new_page, BASE_URL, STAT_PAGES, _parse_stats_text, PlaywrightTimeout
import time

season_str, event_display = '2025', 'Riyadh'

def apply_filter_verbose(page, season_str, event_display):
    year_btns = [b for b in page.query_selector_all('button')
                 if b.inner_text().strip() in ('2022','2023','2024','2025','2026')]
    cur_yr = year_btns[0].inner_text().strip() if year_btns else 'none'
    print(f'    Season before: {cur_yr}', end=' ')

    if year_btns and cur_yr != season_str:
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

    event_btns = [b for b in page.query_selector_all('button')
                  if b.inner_text().strip().lower() in ('all events', event_display.lower())]
    cur_event = event_btns[0].inner_text().strip() if event_btns else 'none'
    print(f'| Event filter shows: {cur_event!r}')

    for b in page.query_selector_all('button'):
        txt = b.inner_text().strip().lower()
        if txt == 'all events' or txt == event_display.lower():
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
            time.sleep(1.5)
            return True

    print(f'    WARNING: {event_display!r} not found in dropdown')
    return False

with sync_playwright() as pw:
    browser, page = _new_page(pw)

    for stat_key, path in list(STAT_PAGES.items())[:3]:
        url = f'{BASE_URL}{path}'
        print(f'[{stat_key}] -> {url}')
        try:
            page.goto(url, wait_until='networkidle', timeout=35000)
        except Exception:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(2)

        ok = apply_filter_verbose(page, season_str, event_display)
        header = [l.strip() for l in page.inner_text('main').split('\n') if l.strip()][:6]
        records = _parse_stats_text(page.inner_text('main'), stat_key, season_str)
        print(f'    Filter ok={ok}, header={header[2:4]}, players={len(records)}')
        print()

    browser.close()
