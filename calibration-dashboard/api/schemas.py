from pydantic import BaseModel
from typing import Optional, List


class BinData(BaseModel):
    bin_lower: float
    bin_upper: float
    predicted_mean: Optional[float]
    observed_freq: Optional[float]
    count: int


class MethodData(BaseModel):
    ece: float
    mce: float
    brier: float
    bins: List[BinData]
    delta_ece: Optional[float] = None
    delta_mce: Optional[float] = None
    delta_brier: Optional[float] = None


class CalibrationData(BaseModel):
    model_id: str
    n_bins: int
    eval_set_size: int
    eval_set_positives: int
    cal_set_size: int
    cal_set_positives: int
    isotonic_overfit_note: str
    raw: MethodData
    platt: MethodData
    isotonic: MethodData


class ModelInfo(BaseModel):
    id: str
    label: str


class ModelsResponse(BaseModel):
    models: List[ModelInfo]


class ScoreRequest(BaseModel):
    model_id: str
    raw_score: float
    method: str = "platt"  # "platt" or "isotonic"


class ScoreResponse(BaseModel):
    model_id: str
    method: str
    raw_score: float
    calibrated_probability: float
