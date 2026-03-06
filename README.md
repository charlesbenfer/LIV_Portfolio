# LIV Golf Analytics Portfolio
### Charles Benfer — Data Science & Analytics

---

## Overview

This portfolio demonstrates applied data science and analytics work focused on professional golf — with specific emphasis on the problems and opportunities most relevant to LIV Golf: player performance modeling, player valuation and acquisition analytics, team optimization, and business intelligence.

The work here spans the full analytics stack: data engineering and scraping, feature engineering, machine learning modeling, diagnostic evaluation, and interactive dashboards for decision-makers.

---

## Projects

### [01 — PGA Tour Performance Prediction Engine](./01_performance_prediction/)

A production-grade machine learning pipeline for predicting professional golf tournament outcomes.

- **Data**: 10+ years of PGA Tour leaderboards (ESPN API) and granular player statistics (PGA Tour GraphQL) across 73,000+ player-tournament rows
- **Models**: Four calibrated XGBoost models — cut probability, top-10, top-20, and finish percentile — with temporal train/val/test splits
- **Features**: Strokes gained (SG Total, OTT, App, ATG, Putting), course history (3-year rolling), course signature correlations, SG momentum trends, hot/cold streak deltas
- **Evaluation**: SHAP feature importance, precision@K, ROC/PR curves, per-tournament AUC breakdown, calibration curves
- **Output**: Weekly ranked prediction tables for any upcoming PGA Tour event

> **LIV Relevance**: Every major LIV player has a full PGA Tour career in this dataset. The model quantifies their underlying skill level independent of tour affiliation, providing an objective baseline for performance expectations.

---

### [02 — LIV Player Analytics Dashboard](./02_player_dashboard/)

An interactive Streamlit application for exploring individual LIV player skill profiles, career trajectories, and head-to-head comparisons.

- **Player Profiles**: SG skill breakdowns (off-tee, approach, around-the-green, putting) across full career
- **Trajectory Analysis**: Year-over-year skill evolution, prime years identification, aging curves
- **Head-to-Head Comparison**: Side-by-side skill radar charts for any two players
- **Prediction Integration**: Model-derived probability scores for cut/top-10/top-20 outcomes
- **LIV Player Coverage**: Full historical profiles for all current LIV players using their PGA Tour career data

> **LIV Relevance**: Gives front office staff and coaches an intuitive tool to understand player skill composition — who drives it, who putts it, who contributes what to their team.

---

### [03 — LIV Player Valuation Model](./03_player_valuation/)

A comps-based player valuation framework for estimating market value and performance projection.

- **Similarity Engine**: Multi-dimensional skill similarity scoring using SG categories, age, and trajectory
- **Historical Comps**: Finds the 10 closest historical player-seasons as analogs for any player
- **Value Projection**: Projects future performance based on how comparable players aged
- **Contract Tiers**: Clusters players into value tiers (franchise anchor, tier 1, developmental, etc.)
- **Acquisition Rankings**: Identifies unsigned/unsigned-equivalent players with the highest value upside

> **LIV Relevance**: Directly applicable to player acquisition decisions. Who is the best value for a given budget? Which aging stars still have productive years left? Which younger players are trending toward star status?

---

### [04 — LIV Team Analytics](./04_team_analytics/)

Team-level analysis built for LIV Golf's unique team competition format.

- **Skill Balance Scoring**: Measures team composition across SG categories (are you driver-heavy? putter-weak?)
- **Floor vs. Ceiling Analysis**: Quantifies whether weak-link elimination or star power drives wins
- **SG Component Importance**: Regression analysis of which skill categories most predict team wins
- **Current Team Profiles**: Analysis of all current LIV teams with skill heatmaps and balance metrics
- **Contribution Analysis**: Identifies team anchors vs. drag players using within-team rank rates

> **LIV Relevance**: No other golf league has a comparable team structure. This framework provides genuine strategic value for team captains and front office in roster construction.

---

### [05 — Business Intelligence Report](./05_business_intelligence/)

Executive-level analytics on LIV Golf's competitive landscape and business metrics.

- **Field Quality Analysis**: How does LIV's player talent pool compare to PGA Tour, DP World Tour over time?
- **Prize Pool ROI**: Performance-per-dollar analysis across tours and players
- **Player Acquisition Targets**: Data-driven ranking of players who would improve LIV's competitive quality
- **Aging Curve Risk**: Portfolio view of current LIV player base — where are the age risks?
- **Star Power Index**: Quantified measure of marquee talent concentration by team

> **LIV Relevance**: The business intelligence layer that puts all the player-level analytics in strategic context for league leadership.

---

## Technical Stack

| Layer | Tools |
|---|---|
| Data Collection | Python (requests, BeautifulSoup), ESPN API, PGA Tour GraphQL API |
| Data Processing | pandas, numpy, scikit-learn |
| Machine Learning | XGBoost, CalibratedClassifierCV, SHAP |
| Visualization | matplotlib, seaborn, plotly |
| Dashboard | Streamlit |
| Notebooks | Jupyter |

---

## Data Sources

- **PGA Tour Leaderboards**: ESPN Scoreboard API (`site.api.espn.com`) — 2015–2026
- **Player Statistics**: PGA Tour GraphQL API — Strokes Gained, Driving, Approach, Putting
- **LIV Golf Results**: LIV Golf official website and public APIs
- **World Golf Rankings**: Official OWGR public data

---

## About

Charles Benfer is a data scientist with experience building end-to-end sports analytics systems, from data infrastructure through machine learning modeling and interactive dashboards. Prior work spans baseball (MLB teams), PGA Tour analytics, and financial modeling.

Contact: [charlesbenfer@gmail.com]
