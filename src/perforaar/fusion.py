"""Spatial fusion of repeated candidate detections."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "detection_id",
    "x_mm",
    "y_mm",
    "z_mm",
    "diameter_mm",
    "flow_score",
    "confidence",
}


def _validate(detections: pd.DataFrame, radius_mm: float) -> None:
    missing = REQUIRED_COLUMNS.difference(detections.columns)
    if missing:
        raise ValueError(f"Missing detection columns: {sorted(missing)}")
    if radius_mm <= 0:
        raise ValueError("radius_mm must be positive")
    numeric = detections[list(REQUIRED_COLUMNS - {"detection_id"})]
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Detection values must be finite and non-missing")
    if (detections["z_mm"] < 0).any() or (detections["diameter_mm"] <= 0).any():
        raise ValueError("Depth must be non-negative and diameter must be positive")
    for column in ("flow_score", "confidence"):
        if not detections[column].between(0, 1).all():
            raise ValueError(f"{column} must be in [0, 1]")


def fuse_detections(detections: pd.DataFrame, radius_mm: float = 5.0) -> pd.DataFrame:
    """Greedily fuse nearby observations using confidence-weighted centroids.

    This deterministic baseline is intentionally simple. It gives the phantom
    experiments a transparent comparator before probabilistic tracking is added.
    """
    _validate(detections, radius_mm)
    if detections.empty:
        return pd.DataFrame(
            columns=[
                "candidate_id",
                "x_mm",
                "y_mm",
                "z_mm",
                "diameter_mm",
                "flow_score",
                "confidence",
                "observations",
            ]
        )

    rows = detections.sort_values("detection_id").reset_index(drop=True)
    points = rows[["x_mm", "y_mm", "z_mm"]].to_numpy(dtype=float)
    unassigned = set(range(len(rows)))
    clusters: list[list[int]] = []

    while unassigned:
        seed = min(unassigned)
        cluster = {seed}
        frontier = [seed]
        unassigned.remove(seed)
        while frontier:
            current = frontier.pop()
            neighbors = [
                idx
                for idx in sorted(unassigned)
                if np.linalg.norm(points[idx] - points[current]) <= radius_mm
            ]
            for idx in neighbors:
                unassigned.remove(idx)
                cluster.add(idx)
                frontier.append(idx)
        clusters.append(sorted(cluster))

    fused = []
    for number, indices in enumerate(clusters, start=1):
        group = rows.iloc[indices]
        weights = np.clip(group["confidence"].to_numpy(dtype=float), 1e-6, None)
        centroid = np.average(group[["x_mm", "y_mm", "z_mm"]], axis=0, weights=weights)
        fused.append(
            {
                "candidate_id": f"P{number:02d}",
                "x_mm": centroid[0],
                "y_mm": centroid[1],
                "z_mm": centroid[2],
                "diameter_mm": np.average(group["diameter_mm"], weights=weights),
                "flow_score": np.average(group["flow_score"], weights=weights),
                "confidence": 1.0 - float(np.prod(1.0 - group["confidence"])),
                "observations": len(group),
            }
        )
    return pd.DataFrame(fused)
