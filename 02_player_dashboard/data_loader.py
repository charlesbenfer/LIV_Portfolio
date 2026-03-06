"""
data_loader.py — LIV Player Analytics data loading and processing utilities.

Loads PGA Tour historical SG stats, ESPN leaderboard results, and scraped
LIV Golf data (event results + estimated SG from the valuation model).
"""

import os
import pandas as pd
import numpy as np

# ── Path resolution ────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, 'data')

STATS_CSV  = os.path.join(_DATA, 'individual_yoy_statistics.csv')
BOARDS_CSV = os.path.join(_DATA, 'espn_full_leaderboards_2015_2026.csv')

# ── LIV scraped data paths ─────────────────────────────────────────────────────
LIV_EVENTS_CSV       = os.path.join(_HERE, 'data', 'liv_event_results.csv')
LIV_VAL_CSV          = os.path.join(_HERE, '..', '03_player_valuation', 'liv_player_valuation.csv')
LIV_EVENT_STATS_CSV  = os.path.join(_HERE, 'data', 'liv_event_stats.csv')
LIV_SEASON_STATS_CSV = os.path.join(_HERE, 'data', 'liv_season_stats.csv')

# ── LIV Golf Player Roster ─────────────────────────────────────────────────────
# Used for PGA Tour last-name matching.  Keep in sync with actual 2025 roster.
LIV_ROSTER = {
    "4Aces GC":             ["Dustin Johnson", "Thomas Detry", "Anthony Kim", "Thomas Pieters"],
    "Cleeks Golf Club":     ["Martin Kaymer", "Richard Bland", "Adrian Meronk", "Victor Perez"],
    "Crushers GC":          ["Bryson DeChambeau", "Paul Casey", "Charles Howell III", "Anirban Lahiri"],
    "Fireballs GC":         ["Sergio Garcia", "Josele Ballester", "Luis Masaveu", "David Puig"],
    "HyFlyers GC":          ["Phil Mickelson", "Michael LaSasso", "Brendan Steele", "Cameron Tringale"],
    "Korean Golf Club":     ["Byeong Hun An", "Minkyu Kim", "Danny Lee", "Younghan Song"],
    "Legion XIII":          ["Jon Rahm", "Tyrrell Hatton", "Tom McKibbin", "Caleb Surratt"],
    "Majesticks Golf Club": ["Ian Poulter", "Lee Westwood", "Laurie Canter", "Sam Horsfield"],
    "RangeGoats GC":        ["Bubba Watson", "Ben Campbell", "Peter Uihlein", "Matthew Wolff"],
    "Ripper GC":            ["Cameron Smith", "Lucas Herbert", "Marc Leishman", "Elvis Smylie"],
    "Smash GC":             ["Talor Gooch", "Jason Kokrak", "Graeme McDowell", "Harold Varner III"],
    "Southern Guards GC":   ["Louis Oosthuizen", "Dean Burmester", "Branden Grace", "Charl Schwartzel"],
    "Torque GC":            ["Joaquin Niemann", "Abraham Ancer", "Sebastian Munoz", "Carlos Ortiz"],
    "Wild Card":            ["Yosuke Asaji", "Bjorn Hellgren", "Richard T. Lee", "Miguel Tabuena"],
}

ALL_LIV_PLAYERS = sorted(set(
    p for team_players in LIV_ROSTER.values() for p in team_players
))

PLAYER_TEAM = {
    player: team
    for team, players in LIV_ROSTER.items()
    for player in players
}

# Scraped playerName variants that don't match the canonical roster name above
NAME_OVERRIDES = {
    'Young-han Song': 'Younghan Song',
    'Sebastian Muñoz': 'Sebastian Munoz',
    'Byeong-Hun An':   'Byeong Hun An',
}

# SG categories tracked
SG_CATEGORIES = {
    'SG: Total':        'SG_Total_Avg',
    'SG: Off the Tee':  'SG_Off_the_Tee_Avg',
    'SG: Approach':     'SG_Approach_the_Green_Avg',
    'SG: Around Green': 'SG_Around_the_Green_Avg',
    'SG: Tee to Green': 'SG_Tee_to_Green_Avg',
}

YEARS = list(range(2015, 2026))


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_stats_wide() -> pd.DataFrame:
    return pd.read_csv(STATS_CSV, low_memory=False)


def load_leaderboards() -> pd.DataFrame:
    return pd.read_csv(BOARDS_CSV, low_memory=False)


def load_liv_events() -> pd.DataFrame:
    """
    Load and clean scraped LIV event results.
    Drops junk rows (score headers rendered as data rows).
    Applies NAME_OVERRIDES to canonicalize player names.
    """
    if not os.path.exists(LIV_EVENTS_CSV):
        return pd.DataFrame()

    df = pd.read_csv(LIV_EVENTS_CSV, low_memory=False)

    # Drop rows that are clearly header/separator artefacts
    junk = (
        df['playerName'].isna() |
        df['playerName'].str.startswith('(', na=True) |
        df['playerName'].str.endswith(' -', na=True) |
        df['playerName'].str.strip().eq('- - - - - -') |
        (df['playerName'].str.len() <= 3)
    )
    df = df[~junk].copy()

    df['playerName'] = df['playerName'].map(lambda n: NAME_OVERRIDES.get(n, n))
    df['year'] = df['year'].astype(int)
    return df


def load_liv_valuation() -> pd.DataFrame:
    """
    Load estimated SG values from the player valuation model.
    Excludes 2026 (incomplete/duplicated rows) and applies NAME_OVERRIDES.
    """
    if not os.path.exists(LIV_VAL_CSV):
        return pd.DataFrame()

    df = pd.read_csv(LIV_VAL_CSV, low_memory=False)
    df['playerName'] = df['playerName'].map(lambda n: NAME_OVERRIDES.get(n, n))
    df = df[df['season'].astype(str) != '2026'].copy()
    df = (df.sort_values('season')
            .drop_duplicates(subset=['playerName', 'season'], keep='first'))

    # Fill missing team assignments from the current roster mapping.
    missing = df['team'].isna() | (df['team'].astype(str).str.strip() == '')
    df.loc[missing, 'team'] = df.loc[missing, 'playerName'].map(PLAYER_TEAM)

    return df


def load_liv_event_stats() -> pd.DataFrame:
    """Load per-event stats. Returns empty DF if file missing."""
    if not os.path.exists(LIV_EVENT_STATS_CSV):
        return pd.DataFrame()
    df = pd.read_csv(LIV_EVENT_STATS_CSV, low_memory=False)
    df['season'] = pd.to_numeric(df['season'], errors='coerce')
    df = df[df['season'].notna()].copy()
    df['season'] = df['season'].astype(int)
    df['playerName'] = df['playerName'].map(lambda n: NAME_OVERRIDES.get(n, n))
    return df


def load_liv_season_stats() -> pd.DataFrame:
    """Load per-season aggregated stats. Returns empty DF if file missing."""
    if not os.path.exists(LIV_SEASON_STATS_CSV):
        return pd.DataFrame()
    df = pd.read_csv(LIV_SEASON_STATS_CSV, low_memory=False)
    df['season'] = pd.to_numeric(df['season'], errors='coerce')
    df = df[df['season'].notna()].copy()
    df['season'] = df['season'].astype(int)
    df['playerName'] = df['playerName'].map(lambda n: NAME_OVERRIDES.get(n, n))
    return df


def load_liv_combined_events() -> pd.DataFrame:
    """
    Merge per-event stats with event results on (event_slug, playerName).
    Returns one row per player-event with finish position, round scores,
    AND all raw stat columns.
    """
    results = load_liv_events()
    stats   = load_liv_event_stats()
    if results.empty or stats.empty:
        return results  # graceful fallback
    merged = results.merge(
        stats.drop(columns=['team', 'event_name', 'season'], errors='ignore'),
        on=['event_slug', 'playerName'],
        how='left',
    )
    return merged


def _last_name(full_name: str) -> str:
    return full_name.split()[-1].lower()


# ── Timeseries builder ─────────────────────────────────────────────────────────

def build_player_sg_timeseries(stats_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract a long-format SG timeseries for all LIV players.

    PGA Tour rows (data_source='actual') come from the wide stats CSV.
    LIV-era rows (data_source='estimated') are appended from the valuation
    model for seasons where no actual PGA data exists for that player.

    Returns columns:
        playerName, team, year, sg_total, sg_ott, sg_app, sg_atg,
        sg_t2g, rounds, driving_dist, driving_acc, data_source
    """
    records = []
    pga_covered: set[tuple] = set()

    for player in ALL_LIV_PLAYERS:
        lname = _last_name(player)
        mask = stats_df['playerName'].str.lower().str.contains(lname, na=False, regex=False)
        matches = stats_df[mask]
        if matches.empty:
            continue

        if player.split()[0].lower() in matches['playerName'].str.lower().values:
            row = matches[matches['playerName'].str.lower().str.startswith(
                player.split()[0].lower())].iloc[0]
        else:
            row = matches.iloc[0]

        team = PLAYER_TEAM.get(player, 'Unknown')

        for yr in YEARS:
            sg_total_col = f'{yr}_SG_Total_Avg'
            if sg_total_col not in stats_df.columns:
                continue
            sg_total = row.get(sg_total_col)
            if pd.isna(sg_total):
                continue

            records.append({
                'playerName':  player,
                'team':        team,
                'year':        yr,
                'sg_total':    round(float(sg_total), 3),
                'sg_ott':      round(float(row.get(f'{yr}_SG_Off_the_Tee_Avg', np.nan)), 3)
                               if pd.notna(row.get(f'{yr}_SG_Off_the_Tee_Avg')) else np.nan,
                'sg_app':      round(float(row.get(f'{yr}_SG_Approach_the_Green_Avg', np.nan)), 3)
                               if pd.notna(row.get(f'{yr}_SG_Approach_the_Green_Avg')) else np.nan,
                'sg_atg':      round(float(row.get(f'{yr}_SG_Around_the_Green_Avg', np.nan)), 3)
                               if pd.notna(row.get(f'{yr}_SG_Around_the_Green_Avg')) else np.nan,
                'sg_t2g':      round(float(row.get(f'{yr}_SG_Tee_to_Green_Avg', np.nan)), 3)
                               if pd.notna(row.get(f'{yr}_SG_Tee_to_Green_Avg')) else np.nan,
                'rounds':      int(row.get(f'{yr}_SG_Total_Measured_Rounds', 0) or 0),
                'driving_dist': round(float(row.get(f'{yr}_Driving_Distance_Avg', np.nan)), 1)
                                if pd.notna(row.get(f'{yr}_Driving_Distance_Avg')) else np.nan,
                'driving_acc': round(float(str(row.get(
                                f'{yr}_Driving_Accuracy_Percentage_', np.nan)).replace('%', '')), 1)
                               if pd.notna(row.get(f'{yr}_Driving_Accuracy_Percentage_')) else np.nan,
                'data_source': 'actual',
            })
            pga_covered.add((player, yr))

    pga_df = pd.DataFrame(records)

    # ── Append estimated LIV-era rows ─────────────────────────────────────────
    liv_val = load_liv_valuation()

    if not liv_val.empty:
        est_records = []
        for _, vrow in liv_val.iterrows():
            player = vrow['playerName']
            season = int(vrow['season'])
            if season < 2022 or (player, season) in pga_covered:
                continue
            team = PLAYER_TEAM.get(player) or (
                vrow['team'] if pd.notna(vrow.get('team')) else 'Unknown'
            )
            est_records.append({
                'playerName':  player,
                'team':        team,
                'year':        season,
                'sg_total':    round(float(vrow['est_sg_total']), 3),
                'sg_ott':      round(float(vrow['est_sg_ott']), 3),
                'sg_app':      round(float(vrow['est_sg_app']), 3),
                'sg_atg':      round(float(vrow['est_sg_atg']), 3),
                'sg_t2g':      np.nan,
                'rounds':      int(vrow['events_played'] * 3)
                               if pd.notna(vrow.get('events_played')) else 0,
                'driving_dist': round(float(vrow['drive_dist']), 1)
                                if pd.notna(vrow.get('drive_dist')) else np.nan,
                'driving_acc': np.nan,
                'data_source': 'estimated',
            })

        if est_records:
            est_df = pd.DataFrame(est_records)
            return (pd.concat([pga_df, est_df], ignore_index=True)
                      .sort_values(['playerName', 'year'])
                      .reset_index(drop=True))

    return pga_df


# ── Skill profile builder ──────────────────────────────────────────────────────

def build_player_skill_profile(ts_df: pd.DataFrame, n_years: int = 3) -> pd.DataFrame:
    """
    Compute a single-row skill profile per player.

    SG metrics (recent_sg_total, sg_ott, …) are computed exclusively from
    actual PGA data to keep them comparable across players.
    driving_dist falls back to estimated data if no actual data is available.
    last_active_yr is extended to include LIV seasons from estimated data.
    """
    profiles = []

    for player, grp in ts_df.groupby('playerName'):
        grp = grp.sort_values('year')
        actual = grp[grp['data_source'] == 'actual']

        if actual.empty:
            continue  # no actual PGA data — skip (can't compute meaningful profile)

        recent = actual.tail(n_years)
        peak_row = actual.loc[actual['sg_total'].idxmax()]

        # driving_dist: prefer actual recent data, fall back to estimated
        est = grp[grp['data_source'] == 'estimated']
        drv = (recent['driving_dist'].dropna().mean()
               if recent['driving_dist'].notna().any()
               else est['driving_dist'].dropna().mean()
               if not est.empty and est['driving_dist'].notna().any()
               else np.nan)

        profiles.append({
            'playerName':      player,
            'team':            grp['team'].iloc[0],
            'last_active_yr':  int(grp['year'].to_numpy().max()),   # includes LIV estimated years
            'peak_year':       int(peak_row['year']),
            'peak_sg_total':   round(actual['sg_total'].max(), 3),
            'career_avg_sg':   round(actual['sg_total'].mean(), 3),
            'recent_sg_total': round(recent['sg_total'].mean(), 3),
            'sg_ott':          round(recent['sg_ott'].dropna().mean(), 3)
                               if recent['sg_ott'].notna().any() else np.nan,
            'sg_app':          round(recent['sg_app'].dropna().mean(), 3)
                               if recent['sg_app'].notna().any() else np.nan,
            'sg_atg':          round(recent['sg_atg'].dropna().mean(), 3)
                               if recent['sg_atg'].notna().any() else np.nan,
            'sg_t2g':          round(recent['sg_t2g'].dropna().mean(), 3)
                               if recent['sg_t2g'].notna().any() else np.nan,
            'driving_dist':    round(drv, 1) if pd.notna(drv) else np.nan,
            'yrs_data':        len(actual),
        })

    return (pd.DataFrame(profiles)
              .sort_values('recent_sg_total', ascending=False)
              .reset_index(drop=True))


# ── Tournament history builder ─────────────────────────────────────────────────

def build_tournament_history(boards_df: pd.DataFrame) -> pd.DataFrame:
    """Extract PGA Tour tournament results for all LIV players."""
    last_names = [_last_name(p) for p in ALL_LIV_PLAYERS]
    mask = boards_df['playerName'].str.lower().apply(
        lambda x: any(ln in str(x) for ln in last_names)
    )
    subset = boards_df[mask].copy()

    def get_team(name):
        for p in ALL_LIV_PLAYERS:
            if _last_name(p) in str(name).lower():
                return PLAYER_TEAM.get(p, 'Unknown')
        return 'Unknown'

    subset['team'] = subset['playerName'].apply(get_team)
    return subset


# ── Cached entry point ─────────────────────────────────────────────────────────

_cache: dict = {}


def get_data():
    """
    Load and process all data, with simple module-level caching.
    Returns (ts_df, profile_df, boards_df, hist_df,
             liv_results_df, liv_val_df,
             liv_event_stats_df, liv_season_stats_df, liv_combined_df)
    """
    if 'data' not in _cache:
        stats_df            = load_stats_wide()
        boards_df           = load_leaderboards()
        ts_df               = build_player_sg_timeseries(stats_df)
        profile_df          = build_player_skill_profile(ts_df)
        hist_df             = build_tournament_history(boards_df)
        liv_results_df      = load_liv_events()
        liv_val_df          = load_liv_valuation()
        liv_event_stats_df  = load_liv_event_stats()
        liv_season_stats_df = load_liv_season_stats()
        liv_combined_df     = load_liv_combined_events()

        # ── Filter to only player-seasons where events actually occurred ────────
        # The scraper carries forward identical stats into seasons where a player
        # wasn't yet playing (e.g. Anthony Kim 2022/2023). Build valid player-seasons
        # from the raw CSV (before junk filtering) so that names like "Anthony Kim -"
        # are recovered after stripping the trailing " -" suffix.
        valid_ps = None
        if os.path.exists(LIV_EVENTS_CSV):
            _raw = pd.read_csv(LIV_EVENTS_CSV, low_memory=False)
            _raw['playerName'] = (
                _raw['playerName']
                .str.strip()
                .str.replace(r'\s*-\s*$', '', regex=True)
            )
            _raw['playerName'] = _raw['playerName'].map(lambda n: NAME_OVERRIDES.get(n, n))
            _raw_junk = (
                _raw['playerName'].isna() |
                _raw['playerName'].str.startswith('(', na=True) |
                _raw['playerName'].str.strip().eq('- - - - - -') |
                (_raw['playerName'].str.len() <= 3)
            )
            _raw = _raw[~_raw_junk].copy()
            _raw['year'] = pd.to_numeric(_raw['year'], errors='coerce')
            _raw = _raw[_raw['year'].notna()].copy()
            _raw['year'] = _raw['year'].astype(int)
            valid_ps = (
                _raw[['playerName', 'year']]
                .drop_duplicates()
                .rename(columns={'year': 'season'})
            )
        elif not liv_results_df.empty:
            valid_ps = (
                liv_results_df[['playerName', 'year']]
                .drop_duplicates()
                .rename(columns={'year': 'season'})
            )
        if valid_ps is not None:
            if not liv_val_df.empty:
                liv_val_df = (liv_val_df
                              .merge(valid_ps, on=['playerName', 'season'], how='inner')
                              .reset_index(drop=True))
            if not liv_season_stats_df.empty:
                liv_season_stats_df = (liv_season_stats_df
                                       .merge(valid_ps, on=['playerName', 'season'], how='inner')
                                       .reset_index(drop=True))
        _cache['data'] = (ts_df, profile_df, boards_df, hist_df,
                          liv_results_df, liv_val_df,
                          liv_event_stats_df, liv_season_stats_df, liv_combined_df)
    return _cache['data']
