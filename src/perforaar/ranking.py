"""Explainable ranking of candidate perforators."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {
    "diameter": 0.30,
    "shallow_depth": 0.20,
    "flow": 0.25,
    "confidence": 0.25,
}


def _minmax(values: pd.Series) -> pd.Series:
    low, high = float(values.min()), float(values.max())
    if np.isclose(low, high):
        return pd.Series(np.ones(len(values)), index=values.index, dtype=float)
    return (values - low) / (high - low)


def rank_candidates(
    candidates: pd.DataFrame,
    weights: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Return candidates with normalized component scores, total score, and rank.

    The score is a planning aid for experiments. Its weights are hypotheses and
    must be agreed with surgeons and validated; it is not a clinical decision rule.
    """
    required = {"candidate_id", "diameter_mm", "z_mm", "flow_score", "confidence"}
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"Missing candidate columns: {sorted(missing)}")
    if candidates.empty:
        result = candidates.copy()
        result["score"] = pd.Series(dtype=float)
        result["rank"] = pd.Series(dtype=int)
        return result
    if candidates[list(required - {"candidate_id"})].isna().any().any():
        raise ValueError("Candidate values must not be missing")

    selected = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(selected) != set(DEFAULT_WEIGHTS):
        raise ValueError(f"Weights must contain exactly: {sorted(DEFAULT_WEIGHTS)}")
    if any((not np.isfinite(value) or value < 0) for value in selected.values()):
        raise ValueError("Weights must be finite and non-negative")
    total = sum(selected.values())
    if total <= 0:
        raise ValueError("At least one weight must be positive")
    selected = {key: value / total for key, value in selected.items()}

    result = candidates.copy()
    result["diameter_component"] = _minmax(result["diameter_mm"])
    result["depth_component"] = 1.0 - _minmax(result["z_mm"])
    result["flow_component"] = result["flow_score"].clip(0, 1)
    result["confidence_component"] = result["confidence"].clip(0, 1)
    result["score"] = (
        selected["diameter"] * result["diameter_component"]
        + selected["shallow_depth"] * result["depth_component"]
        + selected["flow"] * result["flow_component"]
        + selected["confidence"] * result["confidence_component"]
    )
    result = result.sort_values(["score", "candidate_id"], ascending=[False, True]).reset_index(
        drop=True
    )
    result["rank"] = np.arange(1, len(result) + 1)
    return result
