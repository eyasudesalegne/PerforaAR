"""Reproducible non-human observations for examples and tests."""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_detections(seed: int = 42, observations_per_candidate: int = 5) -> pd.DataFrame:
    """Generate clustered tracked detections around six fictional vessels."""
    if observations_per_candidate < 1:
        raise ValueError("observations_per_candidate must be positive")
    rng = np.random.default_rng(seed)
    centers = np.array(
        [
            [-42.0, 38.0, 12.0],
            [-18.0, 92.0, 18.0],
            [8.0, 58.0, 9.0],
            [31.0, 118.0, 23.0],
            [47.0, 73.0, 15.0],
            [5.0, 145.0, 28.0],
        ]
    )
    diameters = np.array([1.4, 1.9, 2.2, 1.2, 1.7, 1.5])
    flows = np.array([0.62, 0.78, 0.92, 0.58, 0.83, 0.69])
    records = []
    frame = 0
    for vessel, (center, diameter, flow) in enumerate(
        zip(centers, diameters, flows, strict=True), start=1
    ):
        for observation in range(observations_per_candidate):
            frame += 1
            jitter = rng.normal(0, [1.1, 1.1, 0.7])
            records.append(
                {
                    "detection_id": f"D{frame:03d}",
                    "frame_id": f"F{frame:03d}",
                    "timestamp_s": round(frame / 15.0, 3),
                    "x_mm": center[0] + jitter[0],
                    "y_mm": center[1] + jitter[1],
                    "z_mm": max(0.1, center[2] + jitter[2]),
                    "diameter_mm": max(0.2, diameter + rng.normal(0, 0.08)),
                    "flow_score": float(np.clip(flow + rng.normal(0, 0.04), 0, 1)),
                    "confidence": float(np.clip(rng.normal(0.82, 0.07), 0, 1)),
                    "synthetic_source_id": f"S{vessel:02d}",
                    "observation_index": observation,
                }
            )
    return pd.DataFrame(records)
