import pandas as pd
import pytest

from perforaar.fusion import fuse_detections


def test_fuses_nearby_and_separates_distant_points():
    rows = pd.DataFrame(
        [
            {
                "detection_id": "a",
                "x_mm": 0,
                "y_mm": 0,
                "z_mm": 10,
                "diameter_mm": 1,
                "flow_score": 0.7,
                "confidence": 0.8,
            },
            {
                "detection_id": "b",
                "x_mm": 1,
                "y_mm": 1,
                "z_mm": 10,
                "diameter_mm": 1.2,
                "flow_score": 0.8,
                "confidence": 0.9,
            },
            {
                "detection_id": "c",
                "x_mm": 20,
                "y_mm": 20,
                "z_mm": 10,
                "diameter_mm": 1.5,
                "flow_score": 0.6,
                "confidence": 0.7,
            },
        ]
    )
    fused = fuse_detections(rows, radius_mm=3)
    assert len(fused) == 2
    assert sorted(fused["observations"].tolist()) == [1, 2]


def test_rejects_invalid_probability():
    row = pd.DataFrame(
        [
            {
                "detection_id": "a",
                "x_mm": 0,
                "y_mm": 0,
                "z_mm": 10,
                "diameter_mm": 1,
                "flow_score": 1.2,
                "confidence": 0.8,
            }
        ]
    )
    with pytest.raises(ValueError, match="flow_score"):
        fuse_detections(row)
