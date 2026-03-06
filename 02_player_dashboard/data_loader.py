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
    'Jed Morgan':      'Jed Morgan',   # canonical; "Jediah Morgan" was erroneous
}

# Season-accurate team rosters (first event of each season)
HISTORICAL_ROSTER: dict[int, dict[str, list[str]]] = {
    2022: {
        "4Aces GC":             ["Dustin Johnson", "Talor Gooch", "Pat Perez", "Patrick Reed"],
        "Southern Guards GC":   ["Louis Oosthuizen", "Hennie Du Plessis", "Branden Grace", "Charl Schwartzel"],
        "Fireballs GC":         ["Sergio Garcia", "Abraham Ancer", "Eugenio Chacarra", "Carlos Ortiz"],
        "Torque GC":            ["Yuki Inamori", "Ryosuke Kinoshita", "Jinichiro Kozuma", "Hideto Tanihara"],
        "Korean Golf Club":     ["Kevin Na", "Sadom Kaewkanjana", "Phachara Khongwatmai", "Sihwan Kim"],
        "Smash GC":             ["Brooks Koepka", "Richard Bland", "Chase Koepka", "Adrian Otaegui"],
        "RangeGoats GC":        ["Graeme McDowell", "James Piot", "Travis Smyth", "Hudson Swafford"],
        "Majesticks Golf Club": ["Lee Westwood", "Laurie Canter", "Sam Horsfield", "Ian Poulter"],
        "Crushers GC":          ["Bryson DeChambeau", "Justin Harding", "Shaun Norris", "Peter Uihlein"],
        "Cleeks Golf Club":     ["Martin Kaymer", "Turk Pettit", "Ian Snyman", "Scott Vincent"],
        "HyFlyers GC":          ["Phil Mickelson", "Itthipat Buranatanyarat", "Bernd Wiesberger", "Matthew Wolff"],
        "Ripper GC":            ["Wade Ormsby", "Matt Jones", "Jed Morgan", "Blake Windred"],
    },
    2023: {
        "Crushers GC":          ["Bryson DeChambeau", "Paul Casey", "Charles Howell III", "Anirban Lahiri"],
        "4Aces GC":             ["Dustin Johnson", "Pat Perez", "Patrick Reed", "Peter Uihlein"],
        "Torque GC":            ["Joaquin Niemann", "Sebastian Munoz", "Mito Pereira", "David Puig"],
        "Southern Guards GC":   ["Louis Oosthuizen", "Dean Burmester", "Branden Grace", "Charl Schwartzel"],
        "Ripper GC":            ["Cameron Smith", "Matt Jones", "Marc Leishman", "Jed Morgan"],
        "Fireballs GC":         ["Sergio Garcia", "Abraham Ancer", "Eugenio Chacarra", "Carlos Ortiz"],
        "HyFlyers GC":          ["Phil Mickelson", "James Piot", "Brendan Steele", "Cameron Tringale"],
        "RangeGoats GC":        ["Bubba Watson", "Talor Gooch", "Thomas Pieters", "Harold Varner III"],
        "Smash GC":             ["Brooks Koepka", "Chase Koepka", "Jason Kokrak", "Matthew Wolff"],
        "Korean Golf Club":     ["Kevin Na", "Sihwan Kim", "Danny Lee", "Scott Vincent"],
        "Majesticks Golf Club": ["Ian Poulter", "Henrik Stenson", "Lee Westwood", "Sam Horsfield"],
        "Cleeks Golf Club":     ["Richard Bland", "Laurie Canter", "Graeme McDowell", "Bernd Wiesberger"],
    },
    2024: {
        "Legion XIII":          ["Jon Rahm", "Tyrrell Hatton", "Caleb Surratt", "Kieran Vincent"],
        "Crushers GC":          ["Bryson DeChambeau", "Paul Casey", "Charles Howell III", "Anirban Lahiri"],
        "Torque GC":            ["Joaquin Niemann", "Sebastian Munoz", "Carlos Ortiz", "Mito Pereira"],
        "Ripper GC":            ["Cameron Smith", "Lucas Herbert", "Matt Jones", "Marc Leishman"],
        "Southern Guards GC":   ["Louis Oosthuizen", "Dean Burmester", "Branden Grace", "Charl Schwartzel"],
        "Fireballs GC":         ["Sergio Garcia", "Abraham Ancer", "Eugenio Chacarra", "David Puig"],
        "Smash GC":             ["Brooks Koepka", "Talor Gooch", "Jason Kokrak", "Graeme McDowell"],
        "Cleeks Golf Club":     ["Martin Kaymer", "Richard Bland", "Adrian Meronk", "Kalle Samooja"],
        "Majesticks Golf Club": ["Ian Poulter", "Henrik Stenson", "Lee Westwood", "Sam Horsfield"],
        "HyFlyers GC":          ["Phil Mickelson", "Andy Ogletree", "Brendan Steele", "Cameron Tringale"],
        "RangeGoats GC":        ["Bubba Watson", "Thomas Pieters", "Peter Uihlein", "Matthew Wolff"],
        "4Aces GC":             ["Dustin Johnson", "Pat Perez", "Patrick Reed", "Harold Varner III"],
        "Korean Golf Club":     ["Kevin Na", "Jinichiro Kozuma", "Danny Lee", "Scott Vincent"],
    },
    2025: {
        "Legion XIII":          ["Jon Rahm", "Tyrrell Hatton", "Tom McKibbin", "Caleb Surratt"],
        "Ripper GC":            ["Cameron Smith", "Lucas Herbert", "Matt Jones", "Marc Leishman"],
        "RangeGoats GC":        ["Bubba Watson", "Ben Campbell", "Peter Uihlein", "Matthew Wolff"],
        "Crushers GC":          ["Bryson DeChambeau", "Paul Casey", "Charles Howell III", "Anirban Lahiri"],
        "Fireballs GC":         ["Sergio Garcia", "Abraham Ancer", "Luis Masaveu", "David Puig"],
        "Cleeks Golf Club":     ["Martin Kaymer", "Richard Bland", "Frederik Kjettrup", "Adrian Meronk"],
        "Torque GC":            ["Joaquin Niemann", "Sebastian Munoz", "Carlos Ortiz", "Mito Pereira"],
        "Southern Guards GC":   ["Louis Oosthuizen", "Dean Burmester", "Branden Grace", "Charl Schwartzel"],
        "Majesticks Golf Club": ["Ian Poulter", "Henrik Stenson", "Lee Westwood", "Sam Horsfield"],
        "Smash GC":             ["Brooks Koepka", "Talor Gooch", "Jason Kokrak", "Graeme McDowell"],
        "4Aces GC":             ["Dustin Johnson", "Thomas Pieters", "Patrick Reed", "Harold Varner III"],
        "HyFlyers GC":          ["Andy Ogletree", "Ollie Schniederjans", "Brendan Steele", "Cameron Tringale"],
        "Korean Golf Club":     ["Kevin Na", "Yubin Jang", "Danny Lee", "Wade Ormsby"],
    },
    2026: {
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
    },
}

# Inverted lookup: (playerName, season) → team
_HIST_PLAYER_TEAM: dict[tuple[str, int], str] = {
    (player, season): team
    for season, teams in HISTORICAL_ROSTER.items()
    for team, players in teams.items()
    for player in players
}

# All players who have ever been on LIV (any season)
ALL_LIV_PLAYERS = sorted({
    player
    for season_roster in HISTORICAL_ROSTER.values()
    for team_players in season_roster.values()
    for player in team_players
})

# ── Prize money structure ──────────────────────────────────────────────────────
# Approximate individual payouts based on ~$25M total purse per LIV event (2022–2025).
LIV_PAYOUT: dict[int, int] = {
    1:  4_000_000, 2:  2_175_000, 3:  1_575_000,
    4:  1_175_000, 5:    875_000, 6:    750_000,
    7:    650_000, 8:    550_000, 9:    475_000,
    10:   425_000, 11:   375_000, 12:   325_000,
    13:   300_000, 14:   275_000, 15:   250_000,
    16:   225_000, 17:   200_000, 18:   200_000,
    19:   175_000, 20:   175_000, 21:   175_000,
    22:   150_000, 23:   150_000, 24:   150_000,
}
_PAYOUT_FLOOR = 125_000  # positions 25–48


def calc_prize_money(position_str) -> int:
    """Estimate individual event prize money from a finish position string (e.g. '1', 'T14', '32')."""
    try:
        pos = int(str(position_str).replace('T', '').strip())
    except (ValueError, AttributeError):
        return 0
    return LIV_PAYOUT.get(pos, _PAYOUT_FLOOR if 1 <= pos <= 48 else 0)


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

    # Fill missing team assignments using season-accurate historical roster first,
    # then fall back to the current roster for any remaining gaps.
    missing = df['team'].isna() | (df['team'].astype(str).str.strip() == '')
    df.loc[missing, 'team'] = df.loc[missing].apply(
        lambda r: _HIST_PLAYER_TEAM.get((r['playerName'], int(r['season'])))
                  or PLAYER_TEAM.get(r['playerName']),
        axis=1,
    )

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
        # Exact full-name match first, then first+last, then last-name fallback
        exact = stats_df[stats_df['playerName'].str.lower() == player.lower()]
        if not exact.empty:
            row = exact.iloc[0]
        else:
            lname = _last_name(player)
            fname = player.split()[0].lower()
            by_last = stats_df[stats_df['playerName'].str.lower().str.contains(
                lname, na=False, regex=False)]
            if by_last.empty:
                continue
            by_first = by_last[by_last['playerName'].str.lower().str.contains(
                fname, na=False, regex=False)]
            row = by_first.iloc[0] if not by_first.empty else by_last.iloc[0]

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


# ── PGA Tour talent pool builder ───────────────────────────────────────────────

def build_pga_talent_pool(stats_df: pd.DataFrame, n_years: int = 3) -> pd.DataFrame:
    """
    Build a recent skill profile for PGA Tour players NOT on the current LIV roster.
    Only includes players with data in 2022 or later.
    Returns columns: playerName, last_active_yr, recent_sg_total, sg_ott, sg_app, sg_atg.
    """
    liv_last_names = {_last_name(p) for p in ALL_LIV_PLAYERS}
    recent_years = list(range(2025 - n_years + 1, 2026))  # [2023, 2024, 2025]

    records = []
    for _, row in stats_df.iterrows():
        name = str(row.get('playerName', ''))
        if not name or _last_name(name) in liv_last_names:
            continue

        sg_by_yr = {
            yr: float(row[f'{yr}_SG_Total_Avg'])
            for yr in range(2015, 2026)
            if f'{yr}_SG_Total_Avg' in stats_df.columns
            and pd.notna(row.get(f'{yr}_SG_Total_Avg'))
        }
        if not sg_by_yr or max(sg_by_yr) < 2022:
            continue

        recent_sg = [sg_by_yr[yr] for yr in recent_years if yr in sg_by_yr]
        if not recent_sg:
            continue

        def _avg(prefix: str) -> float:
            vals = [
                float(row[f'{yr}_{prefix}'])
                for yr in recent_years
                if f'{yr}_{prefix}' in stats_df.columns
                and pd.notna(row.get(f'{yr}_{prefix}'))
            ]
            return round(float(np.mean(vals)), 3) if vals else np.nan

        records.append({
            'playerName':      name,
            'last_active_yr':  int(max(sg_by_yr)),
            'recent_sg_total': round(float(np.mean(recent_sg)), 3),
            'sg_ott':          _avg('SG_Off_the_Tee_Avg'),
            'sg_app':          _avg('SG_Approach_the_Green_Avg'),
            'sg_atg':          _avg('SG_Around_the_Green_Avg'),
        })

    return (pd.DataFrame(records)
              .sort_values('recent_sg_total', ascending=False)
              .reset_index(drop=True))


# ── Cached entry point ─────────────────────────────────────────────────────────

_cache: dict = {}


def get_data():
    """
    Load and process all data, with simple module-level caching.
    Returns (ts_df, profile_df, boards_df, hist_df,
             liv_results_df, liv_val_df,
             liv_event_stats_df, liv_season_stats_df, liv_combined_df,
             pga_talent_df)
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
        pga_talent_df       = build_pga_talent_pool(stats_df)

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
                          liv_event_stats_df, liv_season_stats_df, liv_combined_df,
                          pga_talent_df)
    return _cache['data']
