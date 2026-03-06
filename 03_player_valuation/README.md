# LIV Player Valuation Model

> Full analysis: [`player_valuation.ipynb`](./player_valuation.ipynb)

---

## Problem

LIV Golf does not publish Strokes Gained (SG) data — the standard skill metric in professional golf analytics. Traditional counting stats (driving distance, fairway %, GIR, scrambling, putting average) are available but don't isolate skill components the way SG does.

## Approach

The PGA Tour provides a decade of seasons where **both** traditional stats and SG values are known for the same player-seasons. A regression ensemble (Ridge + Gradient Boosting, blended via VotingRegressor) is trained on this paired dataset, then applied to LIV stats to produce **estimated SG values** per player per season.

This transfer is methodologically defensible: the underlying shot-value physics don't change between tours. The relationship between fairway percentage and stroke value should be stable across contexts.

## Models

| Target | R² (cross-val) | Notes |
|---|---|---|
| SG: Off the Tee | ~0.72 | Driving distance and accuracy |
| SG: Approach | ~0.68 | GIR, proximity |
| SG: Around Green | ~0.55 | Scrambling |
| SG: Putting | ~0.61 | Putts per GIR, putting average |
| SG: Total | ~0.78 | Ensemble of above |

## Outputs

| File | Description |
|---|---|
| `liv_player_valuation.csv` | Estimated SG per player per LIV season with confidence intervals |
| `liv_2025_sg_ranking.png` | Current season player ranking by estimated SG Total |
| `skill_decomposition.png` | Per-player SG breakdown (OTT / App / ATG / Putt) |
| `yoy_sg_change.png` | Year-over-year SG trajectory for key players |
| `predicted_vs_actual.png` | Model validation on held-out PGA Tour seasons |
| `feature_importance.png` | Which traditional stats drive each SG component |

## Key Finding

Bryson DeChambeau and Jon Rahm carry the highest estimated SG totals on tour. The model identifies several players overperforming their skill profile (results-based variance) and others underperforming — providing a regression-to-mean signal for roster decisions.
