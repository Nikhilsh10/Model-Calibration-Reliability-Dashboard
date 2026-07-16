# PRD: Model Calibration & Reliability Dashboard

## 0. Before you build anything — kill criteria
Check this first, not last. Pull the StreamSentinel sensor model's predicted probabilities on the held-out set and bin them into 10 deciles. If any bin has fewer than ~30-50 samples (likely given a 5.5% anomaly rate), your reliability diagram will be visually noisy and a reviewer/interviewer will poke a hole in it in the first minute. If that's the case, either:
- use the Financial dataset instead (check its class balance first), or
- combine bins / use fewer bins (5 instead of 10), or
- don't ship this project.

Don't write a line of dashboard code until this check passes.

## 1. Problem statement
StreamSentinel and the fraud pipeline report ROC-AUC and F1, but neither says whether a "0.92 anomaly score" means what it claims to mean. In production anomaly/fraud systems, miscalibrated confidence scores cause real operational cost — analysts either drown in false-positive-heavy high-confidence alerts or miss real ones bucketed at "medium confidence." This project makes that failure mode visible and fixes it.

## 2. Goal
Take an existing trained model (Isolation Forest + Autoencoder ensemble from StreamSentinel, or the fraud detection model), quantify how miscalibrated its output scores are, apply a correction, and show the before/after in a small interactive dashboard. Not a new model. Not a new pipeline. An analysis layer with a UI.

## 3. Non-goals
- Not retraining the underlying model.
- Not a new data pipeline or Kafka integration.
- Not a general-purpose calibration library — scoped to one or two models you already have.

## 4. Users / audience
Primarily interview panels and recruiters skimming a portfolio. Secondarily, a hypothetical fraud analyst who needs to trust the "confidence" column in an alert queue.

## 5. Core functionality

### 5.1 Analysis layer (Python)
- Load held-out predictions (scores + true labels) from the existing model.
- Compute:
  - Reliability diagram data (predicted probability vs. observed frequency, per bin)
  - Expected Calibration Error (ECE)
  - Maximum Calibration Error (MCE)
  - Brier score
- Fit two calibration correctors: Platt scaling (logistic) and isotonic regression.
- Recompute all four metrics post-calibration for both methods.
- Persist results as JSON (one file per model/method) — this is the API contract for the dashboard, decouples training-time compute from serving.

### 5.2 Serving layer (FastAPI)
- `GET /models` — list available models
- `GET /calibration/{model_id}` — raw + Platt + isotonic curves, ECE/MCE/Brier for all three
- `POST /score` — take a raw model score, return calibrated probability (demonstrates the corrector is a real deployable artifact, not just a plot)

### 5.3 Dashboard (React)
- Reliability diagram: predicted vs. observed, one line per correction method, diagonal reference line
- Metric cards: ECE / MCE / Brier, raw vs. best-corrected, with delta
- Score simulator: slide a raw score, see calibrated output update live (uses `/score`)
- Bin count overlay/toggle — show sample count per bin so the viewer can judge whether the curve is trustworthy (this doubles as your defense against the sparse-bin problem in section 0)

## 6. Success metrics (for the project itself)
- ECE reduced by a measurable, honestly-reported margin after calibration — no target number is set here because it must come from a real run, not be decided in advance (see your own established metrics-fabrication protocol)
- Dashboard loads and the score simulator returns a value consistent with the offline-computed curve (spot-check 3-5 points manually)

## 7. Interview defense points (write these down before you build, so the project is legible in 60 seconds)
- Why calibration matters distinctly from discrimination (ROC-AUC can be excellent while calibration is terrible — these measure different things)
- Platt vs. isotonic tradeoff: Platt assumes a sigmoid-shaped miscalibration and works better with less data; isotonic is non-parametric and more flexible but can overfit with small held-out sets
- Why you used a held-out set separate from the original test set (calibration fit on the same data used to evaluate it is circular)

## 8. Risks / open questions
- **Data volume risk (see section 0)** — the single biggest thing that can sink this.
- Isotonic regression can overfit on small held-out sets — if your held-out set is small, this needs to be stated as a limitation in the writeup, not hidden.
- Scope creep risk: it's tempting to add drift detection, multi-model comparison, etc. Resist — this is a two-week addendum project, not a new flagship.

## 9. Rough build order
1. Kill-criteria check (section 0)
2. Offline analysis script — metrics + both correction methods, dump JSON
3. FastAPI serving layer reading the JSON (+ `/score` using the fitted corrector, pickled)
4. React dashboard consuming the API
5. Manual spot-check of `/score` outputs against the offline curve
6. One paragraph in your portfolio/resume — framed as an addendum to StreamSentinel, not a standalone headline project
