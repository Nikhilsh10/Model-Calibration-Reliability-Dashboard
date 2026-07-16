# Architecture.md — Model Calibration & Reliability Dashboard

## 1. System overview

Three layers, deliberately decoupled so training-time compute never blocks serving:

```
[Offline Analysis]  →  JSON artifacts  →  [FastAPI serving]  →  [React dashboard]
   (Python, run                              (reads JSON,          (consumes API,
    once per model)                           serves /score)        renders charts)
```

This mirrors the S3-pointer decoupling pattern you already used in the fraud pipeline (`promote_model.py` writes, `app.py` reads) — same principle, smaller scale: compute calibration curves once, serve them cheaply, don't recompute per-request.

## 2. Components

### 2.1 Offline analysis (`/analysis`)
- Input: held-out predictions (score, true_label) from StreamSentinel's sensor/financial model.
- Output per model: `calibration_{model_id}.json` containing:
  - raw reliability bins (predicted_mean, observed_freq, count) per bin
  - Platt-scaled bins (same structure)
  - isotonic-scaled bins (same structure)
  - ECE, MCE, Brier score — raw and both corrected versions
  - fitted corrector objects, pickled separately (`platt_{model_id}.pkl`, `isotonic_{model_id}.pkl`)
- Runs as a standalone script, not inside the API process. Re-run manually when the underlying model changes.

### 2.2 Serving layer (FastAPI)
- `GET /models` — reads a static manifest listing available model_ids
- `GET /calibration/{model_id}` — reads and returns the corresponding JSON file as-is (no recomputation)
- `POST /score` — loads the pickled corrector (cached in memory after first load), applies it to the input raw score, returns calibrated probability
- No database. Filesystem-backed. This is intentionally the simplest thing that works — a DB would be over-engineering for two model artifacts.

### 2.3 Dashboard (React)
- Reliability diagram component (raw vs Platt vs isotonic vs diagonal reference)
- Metric cards (ECE/MCE/Brier, raw vs best-corrected, with delta and directional color)
- Score simulator (slider/input → calls `/score` → live-updates a marker on the diagram)
- Bin-count overlay toggle (bar underlay showing sample count per bin, so a thin/noisy bin is visibly flagged rather than hidden)

## 3. Data flow

1. Analyst (you) runs the offline analysis script against StreamSentinel's held-out set.
2. Script writes JSON + pickled correctors to a shared `/artifacts` directory.
3. FastAPI mounts that directory read-only at startup.
4. Dashboard calls `/calibration/{model_id}` once on load, caches client-side.
5. Score simulator calls `/score` per interaction (lightweight, single float in/out).

## 4. Why this decomposition

- **Analysis and serving are separate processes** — because your established pattern (correctly) treats "did the agent verify state" as separate from "does the artifact exist." Keeping the analysis script's output as a checked-in JSON file means you can `cat` it and verify the actual ECE number before the dashboard ever renders anything, instead of trusting a live computation you can't easily inspect.
- **No live model inference in the API** — the ensemble model itself isn't re-run per request; only the lightweight scalar corrector is. Keeps `/score` fast and avoids re-introducing Kafka/streaming complexity this project explicitly excludes.
- **Filesystem over DB** — two models, a handful of JSON files. A database here would be unjustified complexity for a portfolio-scale project; call this out proactively in an interview before someone else does.

## 5. Known architectural risk
If bin counts are too sparse (see PRD section 0), no architecture choice fixes that — it's a data problem, not a system design problem. Don't let a clean architecture diagram distract from checking that first.

## 6. Stack
- Analysis: Python (scikit-learn for isotonic/Platt, numpy/pandas)
- API: FastAPI, Pydantic models mirroring the JSON schema above
- Frontend: React, Recharts or similar for the reliability diagram, Tailwind for layout
- No auth, no persistence layer beyond flat files — scope stays proportional to a two-week addendum project
