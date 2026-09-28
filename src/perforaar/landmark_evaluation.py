from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from .tracked_volume import Calibration, ScanId, landmark_path, parse_scan_metadata


def load_landmarks(root: Path, scan: ScanId) -> np.ndarray:
    """Load TUS-REC2024 landmarks encoded as [frame_index, x_pixel, y_pixel]."""
    with h5py.File(landmark_path(root, scan.subject), "r") as landmark_file:
        if scan.name not in landmark_file:
            raise KeyError(f"Missing landmarks for {scan.key}")
        landmarks = np.asarray(landmark_file[scan.name], dtype=np.int64)
    if landmarks.ndim != 2 or landmarks.shape[1] != 3:
        raise ValueError(f"Unexpected landmark shape for {scan.key}: {landmarks.shape}")
    return landmarks


def _transform_point(transform: np.ndarray, pixel_to_mm: np.ndarray, x: int, y: int) -> np.ndarray:
    pixel = np.asarray([x, y, 0.0, 1.0], dtype=np.float64)
    return (transform @ pixel_to_mm @ pixel)[:3]


def evaluate_landmark_errors(
    scan: ScanId,
    condition: str,
    landmarks: np.ndarray,
    reference: np.ndarray,
    candidate: np.ndarray,
    calibration: Calibration,
) -> list[dict[str, Any]]:
    """Compare candidate and tracker-reference transforms at annotated image points."""
    if reference.shape != candidate.shape:
        raise ValueError("reference and candidate transforms must have matching shapes")
    metadata = parse_scan_metadata(scan.subject, scan.name)
    records: list[dict[str, Any]] = []
    for landmark_index, (frame_index, x_pixel, y_pixel) in enumerate(landmarks):
        frame_index = int(frame_index)
        if frame_index <= 0 or frame_index >= len(reference):
            raise ValueError(f"Invalid landmark frame {frame_index} for {scan.key}")

        reference_global = _transform_point(
            reference[frame_index], calibration.pixel_to_mm, int(x_pixel), int(y_pixel)
        )
        candidate_global = _transform_point(
            candidate[frame_index], calibration.pixel_to_mm, int(x_pixel), int(y_pixel)
        )
        reference_local = np.linalg.inv(reference[frame_index - 1]) @ reference[frame_index]
        candidate_local = np.linalg.inv(candidate[frame_index - 1]) @ candidate[frame_index]
        reference_local_point = _transform_point(
            reference_local, calibration.pixel_to_mm, int(x_pixel), int(y_pixel)
        )
        candidate_local_point = _transform_point(
            candidate_local, calibration.pixel_to_mm, int(x_pixel), int(y_pixel)
        )
        records.append(
            {
                "scan": scan.key,
                "condition": condition,
                "subject": scan.subject,
                "direction": metadata["direction"],
                "anatomical_region": f"{metadata['arm']} forearm",
                "probe_orientation": metadata["probe_orientation"],
                "trajectory": metadata["trajectory"],
                "landmark_index": landmark_index,
                "frame_index": frame_index,
                "x_pixel": int(x_pixel),
                "y_pixel": int(y_pixel),
                "transform_point_error_global_mm": float(
                    np.linalg.norm(reference_global - candidate_global)
                ),
                "transform_point_error_local_mm": float(
                    np.linalg.norm(reference_local_point - candidate_local_point)
                ),
            }
        )
    return records


def _error_summary(records: list[dict[str, Any]]) -> dict[str, float | int]:
    summary: dict[str, float | int] = {"landmark_count": len(records)}
    for scope in ("global", "local"):
        key = f"transform_point_error_{scope}_mm"
        values = np.asarray([record[key] for record in records], dtype=np.float64)
        summary.update(
            {
                f"{key}_median": float(np.median(values)),
                f"{key}_mean": float(np.mean(values)),
                f"{key}_p95": float(np.percentile(values, 95)),
                f"{key}_max": float(np.max(values)),
            }
        )
    return summary


def _group_summaries(
    records: list[dict[str, Any]],
    group_fields: Iterable[str],
) -> list[dict[str, Any]]:
    fields = tuple(group_fields)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for record in records:
        key = tuple(str(record[field]) for field in fields)
        groups.setdefault(key, []).append(record)
    rows = []
    for key, group in sorted(groups.items()):
        rows.append({**dict(zip(fields, key, strict=True)), **_error_summary(group)})
    return rows


def summarize_landmark_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("No landmark records to summarize")
    return {
        "metric_definition": (
            "Euclidean discrepancy at supplied TUS-REC2024 landmark pixels between "
            "a degraded transform and the measured tracker transform. Global maps the "
            "landmark to frame 0; local maps it to the immediately previous frame."
        ),
        "overall": _group_summaries(records, ("condition",)),
        "by_subject": _group_summaries(records, ("condition", "subject")),
        "by_scan_direction": _group_summaries(records, ("condition", "direction")),
        "by_anatomical_region": _group_summaries(
            records, ("condition", "anatomical_region")
        ),
        "by_scan": _group_summaries(records, ("condition", "scan")),
        "records": records,
    }
