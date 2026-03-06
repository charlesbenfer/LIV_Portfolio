# LIV Golf Business Intelligence

> Full analysis: [`business_intelligence.ipynb`](./business_intelligence.ipynb)

Executive-level analytics on LIV Golf's competitive landscape across three dimensions.

---

## Part 1 — Competitive Parity

Measures win concentration using the Herfindahl-Hirschman Index (HHI), standard in economics for measuring market concentration. Normalized HHI of 0 = perfect parity (every team wins equally), 1 = one team wins everything.

**Finding:** LIV's normalized HHI ranges from 0.17–0.23 across full seasons (2023–2025), indicating moderate parity. An average of 6.7 distinct teams won at least one event per season. The pre-season SG favourite (Crushers GC all three years) failed to win the season championship each time — suggesting meaningful competitive unpredictability.

---

## Part 2 — Star Player Delivery

Compares each marquee player's estimated LIV SG against their PGA Tour baseline (avg of last 2 seasons before joining).

**Finding:** 16 of 35 players declined vs. their PGA baseline, 12 improved, 7 maintained. Mean SG delta = −0.10 strokes. Jon Rahm and Bryson DeChambeau are clear overperformers vs. their cohort.

---

## Part 3 — Event Excitement Index

Composite metric (60% team winning margin closeness + 40% individual score spread) to identify which events generated the most competitive drama.

**Finding:** 62% of events decided within 5 strokes (team score). UK 2024, Houston 2024, and DC 2023 rank as the most competitive events. Tucson 2023 scored highest overall on the combined excitement index.

---

## Outputs

| File | Description |
|---|---|
| `parity_hhi.csv` | HHI by season |
| `star_delivery.csv` | Per-player PGA baseline vs LIV performance |
| `event_excitement.csv` | Per-event excitement index |
| `parity_overview.png` | HHI trend, unique winners, cumulative win distribution |
| `margins_and_drama.png` | Avg winning margin and close-finish rate by season |
| `star_player_trajectories.png` | PGA → LIV SG trajectory for 12 marquee players |
| `star_delivery_scatter.png` | Field-wide PGA baseline vs LIV avg SG |
| `event_excitement.png` | Excitement index trends by season |
| `top_exciting_events.png` | Top 15 most competitive events all-time |
