# Model Calibration & Reliability Dashboard

<div align="center">
  <p><strong>A Reliability Addendum for StreamSentinel</strong></p>
</div>

---

This project serves as a standalone calibration analysis and reliability dashboard for [StreamSentinel](https://github.com/Nikhilsh10/streamsentinel). 

While StreamSentinel achieves a high ROC-AUC (0.9952), discrimination only proves the model can rank anomalies above normal events. It does not mean the raw score maps to a true probability. This project diagnoses the raw model's miscalibration using real held-out data and implements post-hoc correction (Platt Scaling and Isotonic Regression) to convert raw fusion scores into trustworthy probabilities.

## 📊 The Results

The raw ensemble exhibited significant overconfidence (expected calibration error of 0.2221 on the sensor stream). **Platt scaling** corrected this robustly, providing an 86% reduction in calibration error on unseen data.

*Metrics generated from a 50/50 split of the `sensor_eval.parquet` (1,250 held-out samples).*

| Metric | Raw | Platt Scaling | Isotonic Regression |
|---|---|---|---|
| **ECE** | 0.2221 | **0.0307** | 0.0018* |
| **MCE** | 0.5465 | **0.4572** | 0.2585 |
| **Brier** | 0.0787 | **0.0161** | 0.0103 |

> [!WARNING]
> ***Why we lead with Platt and distrust Isotonic here**: With only 52 positive anomaly samples in the calibration fit set, Isotonic Regression's non-parametric flexibility achieved a functionally perfect average ECE (0.0018) but left severe max errors on sparse bins (seen clearly in the Financial stream's MCE). This is textbook overfitting. Platt's parametric assumption utilizes sparse data much more safely and is the defensible result.*

## 🏗️ Architecture

The project is split into three layers:

1. **Analysis Script (`analysis/`)**: A Python pipeline that ingests StreamSentinel's real evaluation parquets, passes them through a 10-bin kill-criteria gate (ensuring all bins have ≥ 30 samples), fits the correctors, and emits JSON metrics + pickled artifacts.
2. **Serving API (`api/`)**: A FastAPI layer that serves the pre-computed metrics and exposes a `/score` endpoint backed by the actual pickled correctors (not a hardcoded approximation).
3. **Dashboard (`dashboard/`)**: A React + Vite frontend built without UI libraries (pure CSS design system) providing live metric comparisons, a reliability diagram, and an interactive score simulator.

## 🚀 Quick Start

### 1. Run the API
```powershell
cd calibration-dashboard/api
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

### 2. Run the Dashboard
```powershell
cd calibration-dashboard/dashboard
npm install
npm run dev
```
*(Note: If your project path contains an `&`, PowerShell may fail to run `npm run dev`. Work around this by invoking node directly: `node node_modules\vite\bin\vite.js . --port 5173`)*

Open **http://localhost:5173** to view the dashboard.

## ⚠️ Normalization Contract (The `/score` Endpoint)

The calibration correctors were fit on scores produced by `evaluate_models.py`'s **min-max normalization**. This differs from `fusion.py`'s fixed-range clip (`[0.4, 0.9] → [0, 1]`) used in the production streaming path.

A score directly from the live `fusion.py` path is **NOT a valid input** to this corrector without first re-normalizing. The `/score` API and the dashboard simulator explicitly document this contract. For a truly production-deployable corrector, it must be refit on `fusion.py`-normalized scores.

---
*Built as an analytical addendum to [StreamSentinel](https://github.com/Nikhilsh10/streamsentinel).*
