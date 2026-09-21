import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parents[1]


def _load(path: str) -> dict:
    with (ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_valid(schema_path: str, instance_path: str) -> None:
    schema = _load(schema_path)
    instance = _load(instance_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)


def test_synthetic_tracked_frame_matches_contract():
    _assert_valid(
        "data/schema/tracked-frame.schema.json",
        "data/sample/synthetic_tracked_frame.json",
    )


def test_synthetic_calibration_matches_contract():
    _assert_valid(
        "data/schema/calibration.schema.json",
        "data/sample/synthetic_calibration.json",
    )
