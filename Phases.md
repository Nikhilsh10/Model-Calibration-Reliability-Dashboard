# Phases.md — Model Calibration & Reliability Dashboard

Each phase has a gate — don't move to the next until the gate is honestly satisfied. If a gate fails, stop and fix at that phase; don't patch it downstream.

## Phase 0 — Kill-criteria check
**Goal:** decide whether this project should exist in its current form.
- Pull held-out predictions from StreamSentinel (sensor and/or financial model).
- Bin into deciles, count samples per bin.
- **Gate:** at least a majority of bins have ≥30 samples. If not, switch dataset, reduce bin count, or stop the project here.

## Phase 1 — Offline analysis
**Goal:** produce real, verified calibration numbers.
- Compute raw reliability bins, ECE, MCE, Brier on held-out data.
- Fit Platt scaling and isotonic regression on a separate calibration split.
- Recompute all three metrics post-correction for both methods.
- Manually print and eyeball every number before writing it anywhere else.
- **Gate:** you can state, from memory, the actual raw ECE and the actual post-calibration ECE, and both came from a run you personally inspected.

## Phase 2 — Serialize artifacts
**Goal:** freeze phase 1's output into the API's data contract.
- Write JSON per model (bins + metrics for all three variants).
- Pickle both fitted correctors.
- **Gate:** `cat` the JSON file and confirm the numbers match what you saw in Phase 1's console output, not a re-run that silently changed them.

## Phase 3 — FastAPI serving layer
**Goal:** serve the frozen artifacts, and one live scoring endpoint.
- `GET /models`, `GET /calibration/{model_id}`, `POST /score`.
- **Gate:** manually call `/score` with 3-5 known raw scores and confirm the output matches manually applying the pickled corrector in a Python shell — not just "the endpoint returns 200."

## Phase 4 — Dashboard
**Goal:** visualize what Phase 1-3 produced, nothing invented.
- Reliability diagram (raw/Platt/isotonic + diagonal reference).
- Metric cards with raw vs. corrected deltas.
- Score simulator wired to `/score`.
- Bin-count overlay toggle.
- **Gate:** every number rendered on screen traces back to a file you can open and read — no client-side approximation standing in for real data.

## Phase 5 — Writeup and integration
**Goal:** position this correctly relative to existing portfolio work.
- One paragraph framing it as a StreamSentinel addendum, not a new flagship.
- State the isotonic overfitting limitation explicitly if the calibration split was small.
- Interview defense points written down (see PRD section 7) before this is called "done."
- **Gate:** re-read every claim in the writeup against Rules.md section 1 — nothing stronger than what Phase 1's actual numbers support.

## Explicit non-phases (do not add later without a new PRD)
- Drift detection
- Multi-model comparison beyond the two you already have
- Auth, persistence layer, user accounts
- Retraining the underlying ensemble model
