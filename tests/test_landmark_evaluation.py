import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.landmark_evaluation import (  # noqa: E402
    evaluate_landmark_errors,
    summarize_landmark_records,
)
from perforaar.tracked_volume import Calibration, ScanId  # noqa: E402


def test_landmark_errors_use_annotated_frame_and_pixel():
    reference = np.repeat(np.eye(4)[None, :, :], 3, axis=0)
    candidate = reference.copy()
    candidate[2, 0, 3] = 2.0
    landmarks = np.asarray([[2, 10, 20]])
    records = evaluate_landmark_errors(
        ScanId("050", "RH_Per_S_PtD"),
        "translation",
        landmarks,
        reference,
        candidate,
        Calibration(np.eye(4), np.eye(4)),
    )
    assert records[0]["transform_point_error_global_mm"] == 2.0
    assert records[0]["transform_point_error_local_mm"] == 2.0
    summary = summarize_landmark_records(records)
    assert summary["overall"][0]["landmark_count"] == 1
    assert summary["by_subject"][0]["subject"] == "050"
