# PGA Tour Performance Prediction Engine

> Full project source: [`../../PGA_Prediction_Tools/`](../../PGA_Prediction_Tools/)

---

## What It Does

A machine learning pipeline that ingests 10+ years of PGA Tour data and predicts player outcomes for any upcoming tournament. Four calibrated XGBoost models cover the core prediction targets that matter for betting, fantasy, and roster decisions:

| Model | Type | Target |
|---|---|---|
| `made_cut` | Binary classifier | Will the player make the cut? |
| `top_20` | Binary classifier | Will the player finish top 20? |
| `top_10` | Binary classifier | Will the player finish top 10? |
| `percentile_finish` | Regressor | Where in the field will they finish? |

---

## Data Pipeline

```
ESPN API (leaderboards)          PGA Tour GraphQL API (stats)
       ↓                                    ↓
 73,885 player-event rows        SG stats by year (2010–2025)
       ↓                                    ↓
              [01_data_prep.ipynb]
                     ↓
         master_training_data.pkl
                     ↓
         [01b/01c feature engineering]
                     ↓
     +13 engineered features (SG momentum, course signatures,
      hot/cold streak deltas, trend slopes, course history)
                     ↓
         [03_modeling.ipynb]
                     ↓
     4 XGBoost models + Platt scaling + SHAP analysis
                     ↓
         [05_predictions_2026.ipynb]
                     ↓
     Weekly ranked prediction tables
```

---

## Key Features

**Strokes Gained (SG) Categories**
- SG Off the Tee, Approach the Green, Around the Green, Putting
- Prior-season averages as stable baseline
- Rolling windows (1/3/5 events) for recent form

**Course-Specific Intelligence**
- 3-year rolling course history (average finish, appearances, cut rate)
- Course signature correlations — which SG categories correlate with success at each venue
- Course fit score derived from player skill profile vs. course signature

**Momentum Features**
- `sg_delta`: Recent SG vs. season average (hot/cold streak detection)
- `roll5_sg_total_slope`: Linear trend over last 5 events (improving vs. declining)

**Temporal Integrity**
- Train: ≤2022 | Validation: 2023 | Test: 2024–2025
- No data leakage — features always built from data prior to the prediction date

---

## Model Performance

From `04_diagnostics.ipynb`:

| Model | Test AUC | Precision@10 |
|---|---|---|
| `made_cut` | ~0.73 | — |
| `top_20` | ~0.71 | ~38% |
| `top_10` | ~0.70 | ~29% |
| `percentile_finish` | R² ~0.18 | — |

SHAP analysis confirms SG Total, course history, and SG momentum are the top predictors.

---

## Live Prediction Usage

```bash
cd ../../PGA_Prediction_Tools
source .venv/bin/activate
python predict_week.py --top 30
```

This auto-detects the next PGA Tour event from the ESPN schedule and outputs ranked predictions.

---

## LIV Relevance

Every major LIV player has a full PGA Tour career in this dataset:

| LIV Player | PGA Tour Events in Dataset |
|---|---|
| Dustin Johnson | 675 |
| Cameron Smith | 533 |
| Hideki Matsuyama | 292 |
| Brooks Koepka | 207 |
| Sergio Garcia | 165 |
| Phil Mickelson | 188 |
| Jon Rahm | 176 |
| Bryson DeChambeau | 172 |

The model provides **objective, tour-agnostic skill ratings** for all LIV players based on their SG data — a baseline for performance expectations regardless of where they're playing.
