# LIV Player Analytics Dashboard

An interactive Streamlit application for exploring LIV Golf player skill profiles,
career trajectories, and comparative analytics using PGA Tour Strokes Gained data.

---

## Running the Dashboard

```bash
cd 02_player_dashboard
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Pages

### Field Overview
- Full LIV player skill rankings table with sortable columns
- SG Total distribution histogram across the field
- Average SG by category (Off Tee, Approach, Around Green)
- Team-by-team average SG comparison with roster range error bars

### Player Profile
- Per-player skill metrics: recent SG Total, peak SG, SG by category
- Career SG trajectory chart (all SG categories over time, with LIV era shaded)
- Skill radar chart (normalized to percentile vs LIV field)
- Tournament history scatter (PGA Tour finishes by year)
- Career statistics (wins, top 10s, top 25s by year range)

### Head-to-Head
- Side-by-side skill radar comparison for any two players
- Grouped bar chart: raw SG values by category
- Overlaid career SG Total trajectories
- Stat-by-stat comparison table with edge calculation

### Team Analysis
- Team-level skill heatmap (percentiles vs LIV field)
- Team balance radar chart vs median LIV team
- Roster detail table with all SG metrics
- Strength/gap identification by skill category

---

## Data

All data comes from the `PGA_Prediction_Tools` project:

| Source | Description |
|---|---|
| `individual_yoy_statistics.csv` | PGA Tour SG stats by player and year (2010–2025) |
| `espn_full_leaderboards_2015_2026.csv` | Tournament results (73,885 player-event rows) |

**Players covered**: 38 current LIV Golf players with PGA Tour historical data
**Stat range**: 2015–2025 (or until player's last PGA Tour season)

---

## Key Design Decisions

- **Strokes Gained as currency**: SG is the gold standard for golf analytics — it isolates each skill category independently of course difficulty and field quality
- **Percentile normalization**: Radar charts show percentile rank vs the LIV field, not raw values, making cross-player comparisons intuitive
- **Transparent LIV data gap**: Career charts clearly shade the "LIV era" where PGA Tour SG data is unavailable, avoiding misleading impressions
- **Recent form weighted**: Skill profiles use the last 3 PGA Tour seasons to capture current ability rather than inflating or deflating based on career trajectory
