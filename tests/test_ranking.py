import pandas as pd
import pytest

from perforaar.ranking import rank_candidates


def test_ranking_prefers_better_candidate_with_equal_weights():
    candidates = pd.DataFrame(
        [
            {
                "candidate_id": "weak",
                "diameter_mm": 1,
                "z_mm": 20,
                "flow_score": 0.2,
                "confidence": 0.3,
            },
            {
                "candidate_id": "strong",
                "diameter_mm": 2,
                "z_mm": 8,
                "flow_score": 0.9,
                "confidence": 0.9,
            },
        ]
    )
    result = rank_candidates(candidates)
    assert result.iloc[0]["candidate_id"] == "strong"
    assert result.iloc[0]["rank"] == 1


def test_zero_weights_are_rejected():
    candidates = pd.DataFrame(
        [{"candidate_id": "p", "diameter_mm": 1, "z_mm": 10, "flow_score": 0.5, "confidence": 0.5}]
    )
    with pytest.raises(ValueError, match="positive"):
        rank_candidates(candidates, {"diameter": 0, "shallow_depth": 0, "flow": 0, "confidence": 0})
