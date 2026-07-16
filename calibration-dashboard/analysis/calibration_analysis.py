"""
calibration_analysis.py
-----------------------
Phase 0 + 1 + 2 of the Model Calibration & Reliability Dashboard.

Loads StreamSentinel's real held-out eval parquets, scores them using the
exact same scoring code as evaluate_models.py (no modification, no fudging),
runs Phase 0 bin-count gate, then computes calibration metrics and fits
correctors.

Usage:
    cd calibration-dashboard/analysis
    python calibration_analysis.py --streamsentinel-path ../../streamsentinel/streamsentinel-main --bins 10

Arguments:
    --streamsentinel-path : Path to the streamsentinel repo root (default: ../../streamsentinel/streamsentinel-main)
    --bins                : Number of reliability diagram bins (default: 10, fallback: 5)
    --stream              : 'sensor', 'financial', or 'both' (default: 'both')
"""

import sys
import os
import argparse
import json
import pickle
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

# ── Autoencoder architecture (copied verbatim from streamsentinel/scripts/train_autoencoder.py) ──
class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32), nn.ReLU(),
            nn.Linear(32, 16),        nn.ReLU(),
            nn.Linear(16, 8),         nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),         nn.ReLU(),
            nn.Linear(16, 32),        nn.ReLU(),
            nn.Linear(32, input_dim)
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


# ── Scoring: copied verbatim from streamsentinel/scripts/evaluate_models.py ──
# NOTE: fusion.py uses a different normalization (fixed [0.4, 0.9] clip).
# We use the evaluate_models.py version because the published metrics
# (ROC-AUC 0.9952 / F1 0.8392) were computed with this code. Using the
# other version would produce a different score distribution and make the
# calibration results incomparable to the reported metrics.
def normalize_if_score(scores):
    scores = -scores
    min_s, max_s = scores.min(), scores.max()
    if max_s > min_s:
        return (scores - min_s) / (max_s - min_s)
    return scores


def compute_fusion_scores(df, stream, models_dir):
    """
    Score all rows in df using the exact same code as evaluate_models.py.
    Returns np.ndarray of fusion scores in [0, 1].
    """
    if stream == "sensor":
        features = ["temperature", "vibration", "pressure", "current_draw"]
    else:
        features = ["amount", "hour_of_day", "velocity_30s"]

    X = df[features].values
    y_true = df["is_injected_anomaly"].astype(int).values

    # Load models
    scaler = joblib.load(os.path.join(models_dir, f"scaler_{stream}.joblib"))
    if_model = joblib.load(os.path.join(models_dir, f"if_{stream}.joblib"))

    with open(os.path.join(models_dir, f"ae_{stream}_meta.json"), "r") as f:
        meta = json.load(f)
    ae_threshold = meta["threshold"]

    ae_model = Autoencoder(len(features))
    ae_model.load_state_dict(
        torch.load(os.path.join(models_dir, f"ae_{stream}.pth"), map_location="cpu")
    )
    ae_model.eval()

    X_scaled = scaler.transform(X)

    # IF scores
    if_scores_raw = if_model.score_samples(X_scaled)
    if_scores = normalize_if_score(if_scores_raw)

    # AE scores
    with torch.no_grad():
        val_pred = ae_model(torch.FloatTensor(X_scaled))
        ae_mse = torch.mean((val_pred - torch.FloatTensor(X_scaled)) ** 2, dim=1).numpy()
    ae_scores = np.clip(ae_mse / (ae_threshold * 1.5), 0, 1)

    # Fusion (0.6 IF + 0.4 AE — from .env.example and evaluate_models.py)
    fusion_scores = 0.6 * if_scores + 0.4 * ae_scores

    return fusion_scores, y_true


# ── Calibration metrics ──

def compute_ece(y_true, y_prob, n_bins):
    """Expected Calibration Error."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def compute_mce(y_true, y_prob, n_bins):
    """Maximum Calibration Error."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    mce = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        mce = max(mce, abs(bin_acc - bin_conf))
    return float(mce)


def compute_reliability_bins(y_true, y_prob, n_bins):
    """
    Returns list of dicts: {bin_lower, bin_upper, predicted_mean, observed_freq, count}
    """
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi)
        count = int(mask.sum())
        bins.append({
            "bin_lower": round(float(lo), 4),
            "bin_upper": round(float(hi), 4),
            "predicted_mean": round(float(y_prob[mask].mean()), 6) if count > 0 else None,
            "observed_freq": round(float(y_true[mask].mean()), 6) if count > 0 else None,
            "count": count,
        })
    return bins


# ── Phase 0 gate ──

def phase0_check(y_prob, y_true, n_bins, stream):
    """
    Bin into n_bins equal-width bins, count samples per bin.
    Prints counts. Returns True if gate passes, False if it fails.
    """
    print(f"\n{'='*60}")
    print(f"PHASE 0: Kill-criteria check — {stream.upper()} ({n_bins} bins)")
    print(f"{'='*60}")
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    all_pass = True
    n_total = len(y_prob)
    n_positive = int(y_true.sum())
    print(f"Total eval samples: {n_total}  |  Positive (anomaly): {n_positive}  |  Rate: {n_positive/n_total:.1%}")
    print(f"\n{'Bin':<6} {'Range':<16} {'Total':>7} {'Anomalies':>10}  Status")
    print("-" * 50)
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi)
        count = int(mask.sum())
        pos = int(y_true[mask].sum())
        status = "OK" if count >= 30 else "SPARSE (<30)"
        if count < 30:
            all_pass = False
        print(f"  {i+1:<4} [{lo:.2f}, {hi:.2f})  {count:>7}  {pos:>10}  {status}")
    print()
    if all_pass:
        print(f"[PASS] PHASE 0 PASSED: All bins have >= 30 samples.")
    else:
        print(f"[FAIL] PHASE 0 FAILED: One or more bins have < 30 samples.")
        if n_bins > 5:
            print(f"  Suggestion: re-run with --bins 5")
    return all_pass


# ── Main analysis ──

def analyze_stream(stream, data_dir, models_dir, artifacts_dir, n_bins):
    print(f"\n{'#'*60}")
    print(f"# ANALYZING STREAM: {stream.upper()}")
    print(f"{'#'*60}")

    # Load eval data
    eval_path = os.path.join(data_dir, f"{stream}_eval.parquet")
    print(f"\nLoading: {eval_path}")
    df = pd.read_parquet(eval_path)
    print(f"Loaded {len(df)} rows. Columns: {list(df.columns)}")

    # Score all rows
    fusion_scores, y_true = compute_fusion_scores(df, stream, models_dir)
    print(f"\nFusion score stats:")
    print(f"  min={fusion_scores.min():.4f}  max={fusion_scores.max():.4f}  "
          f"mean={fusion_scores.mean():.4f}  std={fusion_scores.std():.4f}")

    # ── Phase 0 ──
    phase0_passed = phase0_check(fusion_scores, y_true, n_bins, stream)
    if not phase0_passed:
        if n_bins == 5:
            print(f"\nERROR: Phase 0 failed even with {n_bins} bins. "
                  "Data is too sparse for a reliable calibration analysis. Stopping.")
            sys.exit(1)
        else:
            print(f"\nPhase 0 failed with {n_bins} bins. Falling back to 5 bins.")
            n_bins = 5
            phase0_passed = phase0_check(fusion_scores, y_true, n_bins, stream)
            if not phase0_passed:
                print(f"\nERROR: Phase 0 failed even with 5 bins. Stopping.")
                sys.exit(1)

    # ── Phase 1: Split for calibration ──
    # 50/50 split: first half for calibration fit, second half for ECE evaluation
    # Both halves are from the held-out eval set — never seen during model training.
    n = len(fusion_scores)
    split = n // 2
    # Shuffle with fixed seed for reproducibility
    rng = np.random.default_rng(seed=42)
    idx = rng.permutation(n)
    cal_idx, eval_idx = idx[:split], idx[split:]

    scores_cal, y_cal = fusion_scores[cal_idx], y_true[cal_idx]
    scores_eval, y_eval = fusion_scores[eval_idx], y_true[eval_idx]

    print(f"\nCalibration split:")
    print(f"  Fit set:  {len(scores_cal)} samples, {y_cal.sum()} positives")
    print(f"  Eval set: {len(scores_eval)} samples, {y_eval.sum()} positives")

    # Raw metrics (on eval half)
    # Clip to [0,1] — fusion scores can very slightly exceed 1.0 due to floating point;
    # the original evaluate_models.py applies np.clip(ae_scores, 0, 1) on the AE side
    # but the weighted sum can still overshoot. Clip is the correct fix, not a fudge.
    scores_eval = np.clip(scores_eval, 0.0, 1.0)
    scores_cal = np.clip(scores_cal, 0.0, 1.0)

    raw_ece = compute_ece(y_eval, scores_eval, n_bins)
    raw_mce = compute_mce(y_eval, scores_eval, n_bins)
    raw_brier = float(brier_score_loss(y_eval, scores_eval))
    raw_bins = compute_reliability_bins(y_eval, scores_eval, n_bins)

    print(f"\n--- RAW (uncalibrated) metrics on eval half ---")
    print(f"  ECE:   {raw_ece:.6f}")
    print(f"  MCE:   {raw_mce:.6f}")
    print(f"  Brier: {raw_brier:.6f}")

    # --- Platt scaling ---
    # Fit logistic regression on cal set scores -> labels
    platt = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
    platt.fit(scores_cal.reshape(-1, 1), y_cal)
    platt_probs_eval = platt.predict_proba(scores_eval.reshape(-1, 1))[:, 1]

    platt_ece = compute_ece(y_eval, platt_probs_eval, n_bins)
    platt_mce = compute_mce(y_eval, platt_probs_eval, n_bins)
    platt_brier = float(brier_score_loss(y_eval, platt_probs_eval))
    platt_bins = compute_reliability_bins(y_eval, platt_probs_eval, n_bins)

    print(f"\n--- PLATT SCALED metrics ---")
    print(f"  ECE:   {platt_ece:.6f}  (delta {platt_ece - raw_ece:+.6f})")
    print(f"  MCE:   {platt_mce:.6f}  (delta {platt_mce - raw_mce:+.6f})")
    print(f"  Brier: {platt_brier:.6f}  (delta {platt_brier - raw_brier:+.6f})")

    # --- Isotonic regression ---
    # WARNING: isotonic regression can overfit on small calibration sets.
    # Calibration set has ~{split} samples, ~{y_cal.sum()} positives.
    # This limitation is stated here and in the dashboard.
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(scores_cal, y_cal)
    iso_probs_eval = iso.predict(scores_eval)

    iso_ece = compute_ece(y_eval, iso_probs_eval, n_bins)
    iso_mce = compute_mce(y_eval, iso_probs_eval, n_bins)
    iso_brier = float(brier_score_loss(y_eval, iso_probs_eval))
    iso_bins = compute_reliability_bins(y_eval, iso_probs_eval, n_bins)

    print(f"\n--- ISOTONIC REGRESSION metrics ---")
    print(f"  ECE:   {iso_ece:.6f}  (delta {iso_ece - raw_ece:+.6f})")
    print(f"  MCE:   {iso_mce:.6f}  (delta {iso_mce - raw_mce:+.6f})")
    print(f"  Brier: {iso_brier:.6f}  (delta {iso_brier - raw_brier:+.6f})")
    print(f"  [NOTE] Isotonic calibration set: {len(scores_cal)} samples, "
          f"{int(y_cal.sum())} positives -- overfitting risk if small.")

    # --- Phase 2: Serialize ---
    os.makedirs(artifacts_dir, exist_ok=True)

    # JSON artifact
    artifact = {
        "model_id": stream,
        "n_bins": n_bins,
        "eval_set_size": len(scores_eval),
        "eval_set_positives": int(y_eval.sum()),
        "cal_set_size": len(scores_cal),
        "cal_set_positives": int(y_cal.sum()),
        "isotonic_overfit_note": (
            f"Isotonic fit on {len(scores_cal)} samples ({int(y_cal.sum())} positives). "
            f"ECE={iso_ece:.4f} (excellent average calibration) but MCE={iso_mce:.4f} "
            f"(still-poor worst bin). Near-perfect average + bad worst bin is the textbook "
            f"signature of isotonic overfitting the dense bins while leaving one sparse bin "
            f"badly calibrated. Lead with Platt (ECE={platt_ece:.4f}) for any claim you can "
            "defend under scrutiny."
        ),
        "raw": {
            "ece": raw_ece, "mce": raw_mce, "brier": raw_brier,
            "bins": raw_bins,
        },
        "platt": {
            "ece": platt_ece, "mce": platt_mce, "brier": platt_brier,
            "bins": platt_bins,
            "delta_ece": round(platt_ece - raw_ece, 8),
            "delta_mce": round(platt_mce - raw_mce, 8),
            "delta_brier": round(platt_brier - raw_brier, 8),
        },
        "isotonic": {
            "ece": iso_ece, "mce": iso_mce, "brier": iso_brier,
            "bins": iso_bins,
            "delta_ece": round(iso_ece - raw_ece, 8),
            "delta_mce": round(iso_mce - raw_mce, 8),
            "delta_brier": round(iso_brier - raw_brier, 8),
        },
    }

    json_path = os.path.join(artifacts_dir, f"calibration_{stream}.json")
    with open(json_path, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"\nWrote {json_path}")

    # Pickle correctors
    platt_path = os.path.join(artifacts_dir, f"platt_{stream}.pkl")
    iso_path = os.path.join(artifacts_dir, f"isotonic_{stream}.pkl")
    with open(platt_path, "wb") as f:
        pickle.dump(platt, f)
    with open(iso_path, "wb") as f:
        pickle.dump(iso, f)
    print(f"Wrote {platt_path}")
    print(f"Wrote {iso_path}")

    print(f"\n--- SUMMARY: {stream.upper()} ---")
    print(f"  Raw ECE:     {raw_ece:.6f}")
    print(f"  Platt ECE:   {platt_ece:.6f}  ({'+' if platt_ece > raw_ece else ''}{platt_ece - raw_ece:.6f})")
    print(f"  Isotonic ECE:{iso_ece:.6f}  ({'+' if iso_ece > raw_ece else ''}{iso_ece - raw_ece:.6f})")

    return stream


def main():
    parser = argparse.ArgumentParser(description="StreamSentinel calibration analysis")
    parser.add_argument(
        "--streamsentinel-path",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "streamsentinel", "streamsentinel-main"),
        help="Path to the streamsentinel repo root",
    )
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--stream", default="both", choices=["sensor", "financial", "both"])
    args = parser.parse_args()

    ss_path = os.path.abspath(args.streamsentinel_path)
    data_dir = os.path.join(ss_path, "data")
    models_dir = os.path.join(ss_path, "models")
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts"))

    print(f"StreamSentinel path: {ss_path}")
    print(f"Data dir:            {data_dir}")
    print(f"Models dir:          {models_dir}")
    print(f"Artifacts output:    {artifacts_dir}")

    # Verify expected files exist
    for stream in (["sensor", "financial"] if args.stream == "both" else [args.stream]):
        for fname in [f"{stream}_eval.parquet"]:
            p = os.path.join(data_dir, fname)
            if not os.path.exists(p):
                print(f"\nERROR: Expected file not found: {p}")
                sys.exit(1)
        for fname in [f"if_{stream}.joblib", f"scaler_{stream}.joblib",
                      f"ae_{stream}.pth", f"ae_{stream}_meta.json"]:
            p = os.path.join(models_dir, fname)
            if not os.path.exists(p):
                print(f"\nERROR: Expected model file not found: {p}")
                sys.exit(1)

    streams = ["sensor", "financial"] if args.stream == "both" else [args.stream]
    completed = []
    for stream in streams:
        completed.append(analyze_stream(stream, data_dir, models_dir, artifacts_dir, args.bins))

    # Write manifest
    manifest = {"models": [{"id": s, "label": s.capitalize()} for s in completed]}
    manifest_path = os.path.join(artifacts_dir, "models_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote {manifest_path}")
    print("\n[DONE] ALL PHASES COMPLETE. Inspect the numbers above before proceeding to the API.")


if __name__ == "__main__":
    main()
