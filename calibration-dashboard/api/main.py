"""
FastAPI serving layer — Model Calibration & Reliability Dashboard
Phase 3 of calibration-dashboard.

Serves frozen artifacts from the analysis script.
No live model inference. No recomputation. Filesystem-backed.
"""

import os
import json
import pickle
import functools
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import CalibrationData, ModelsResponse, ScoreRequest, ScoreResponse

# ── Paths ──
ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"

app = FastAPI(
    title="Model Calibration & Reliability Dashboard API",
    description=(
        "Serves calibration analysis artifacts from StreamSentinel's "
        "Isolation Forest + Autoencoder ensemble. All data is pre-computed "
        "offline — no live model inference in this API."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Corrector cache ──
# LRU cache keyed by (model_id, method). Loads pickle on first call, cached thereafter.

@functools.lru_cache(maxsize=8)
def _load_corrector(model_id: str, method: str):
    """Load and cache a pickled corrector object."""
    filename = f"{method}_{model_id}.pkl"
    path = ARTIFACTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Corrector not found: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


# ── Endpoints ──

@app.get("/models", response_model=ModelsResponse)
def get_models():
    """List available calibrated models."""
    manifest_path = ARTIFACTS_DIR / "models_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(
            status_code=503,
            detail="models_manifest.json not found. Run the analysis script first.",
        )
    with open(manifest_path) as f:
        data = json.load(f)
    return ModelsResponse(**data)


@app.get("/calibration/{model_id}", response_model=CalibrationData)
def get_calibration(model_id: str):
    """
    Return all calibration data for a model: raw + Platt + isotonic curves,
    ECE/MCE/Brier for all three methods.
    Data is read directly from the frozen JSON artifact — no recomputation.
    """
    json_path = ARTIFACTS_DIR / f"calibration_{model_id}.json"
    if not json_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No calibration data found for model '{model_id}'. "
                   "Run the analysis script to generate it.",
        )
    with open(json_path) as f:
        data = json.load(f)
    return CalibrationData(**data)


@app.post("/score", response_model=ScoreResponse)
def score(request: ScoreRequest):
    """
    Apply a calibration corrector to a raw fusion score.

    **IMPORTANT — normalization contract:**
    The corrector was fit on scores produced by `evaluate_models.py`'s
    min-max normalization:

        if_score = (-raw_score - min) / (max - min)   # min-max over eval set

    This differs from `fusion.py`'s fixed-range normalization used in
    production streaming:

        if_score = clip((-raw_score - 0.4) / 0.5, 0, 1)  # fixed clip

    The two produce different score distributions. A score from the live
    fusion.py path is NOT a valid input to this corrector without first
    re-normalizing with the same min-max transform used during calibration.

    For a fully production-deployable corrector, you would need to fit it on
    fusion.py-normalized scores. This corrector is valid as an analysis artifact
    demonstrating the calibration methodology — not as a drop-in for the live
    streaming pipeline without that re-fitting step.

    Input raw_score: float in [0, 1], produced by evaluate_models.py
    normalization applied to a held-out event.
    """
    model_id = request.model_id
    method = request.method

    if method not in ("platt", "isotonic"):
        raise HTTPException(
            status_code=400,
            detail=f"method must be 'platt' or 'isotonic', got '{method}'",
        )

    # Validate model_id
    manifest_path = ARTIFACTS_DIR / "models_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        valid_ids = [m["id"] for m in manifest["models"]]
        if model_id not in valid_ids:
            raise HTTPException(
                status_code=404,
                detail=f"model_id '{model_id}' not found. Valid: {valid_ids}",
            )

    try:
        corrector = _load_corrector(model_id, method)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    raw_score = np.clip(float(request.raw_score), 0.0, 1.0)

    if method == "platt":
        # LogisticRegression — expects 2D input
        calibrated = float(
            corrector.predict_proba(np.array([[raw_score]]))[0, 1]
        )
    else:
        # IsotonicRegression — expects 1D input
        calibrated = float(
            corrector.predict(np.array([raw_score]))[0]
        )

    calibrated = float(np.clip(calibrated, 0.0, 1.0))

    return ScoreResponse(
        model_id=model_id,
        method=method,
        raw_score=raw_score,
        calibrated_probability=calibrated,
    )


@app.get("/health")
def health():
    return {"status": "ok", "artifacts_dir": str(ARTIFACTS_DIR)}
