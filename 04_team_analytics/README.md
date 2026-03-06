# LIV Team Analytics

Team-level analysis built for LIV Golf's unique format where all 4 player scores count in every event.

---

## Notebooks

### [01 — Team Performance Tracking](./01_performance_tracking/)

Aggregates player-level event results into team scores, rankings, and season summaries across all LIV seasons (2022–2026).

**Outputs:**
- `team_event_results.csv` — team aggregate score and finish rank per event
- `team_season_summary.csv` — wins, podiums, avg rank, avg score per team per season
- `player_team_contribution.csv` — anchor rate / drag rate per player per season
- Heatmaps: per-event finish rank grid for each season (2022–2026)

**Key method:** Within-team contribution analysis — for each event, ranks players within their team to identify consistent anchors (top scorer) vs. consistent drags (bottom scorer).

---

### [02 — Skill Balance vs. Depth](./02_skill_balance_vs_depth/)

Investigates whether team success comes from having one dominant star (depth/ceiling) or a balanced roster with no weak links (floor), using estimated SG profiles from the valuation model.

**Outputs:**
- `team_skill_profiles.csv` — per team per season: SG mean/std/min/max + balance metrics
- Regression analysis: OLS predicting avg finish rank from team SG quality, spread, and floor

**Key finding:** Team SG quality (mean) and off-tee floor are the strongest predictors of win rate. Neither pure star power nor pure balance dominates — floor quality (weakest player) matters as much as ceiling.

---

## All-Time Team Wins (2022–2025 full seasons)

| Team | Wins |
|---|---|
| Crushers GC | 8 |
| Legion XIII | 8 |
| Fireballs GC | 6 |
| Southern Guards GC | 6 |
| Torque GC | 6 |
| 4Aces GC | 5 |
| Ripper GC | 5 |
| Smash GC | 4 |
