from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.tracked_volume import write_json  # noqa: E402


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    observed: Any,
    operator: str,
    threshold: Any,
    passed: bool,
) -> None:
    checks.append(
        {
            "name": name,
            "observed": observed,
            "operator": operator,
            "threshold": threshold,
            "passed": bool(passed),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check frozen TUS-REC2024 thresholds.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/tus_rec2024.yaml"))
    args = parser.parse_args()
    root = args.root.resolve()
    config = yaml.safe_load((root / args.config).read_text())
    thresholds = config["acceptance_thresholds"]
    result_dir = root / "results" / "tus_rec2024"
    metrics = json.loads((result_dir / "metrics.json").read_text())
    landmarks = json.loads((result_dir / "landmark_metrics.json").read_text())
    benchmark = json.loads((result_dir / "benchmark.json").read_text())
    checks: list[dict[str, Any]] = []

    failures = metrics["validation_summary"]["failed_scans"]
    limit = thresholds["validation_failures_max"]
    add_check(checks, "validation failures", failures, "<=", limit, failures <= limit)

    full_rows = [row for row in metrics["conditions"] if row["condition"] == "full_20fps"]
    for row in full_rows:
        safe_scan = row["scan"].replace("/", "__")
        path = result_dir / "volumes" / f"{safe_scan}__full_20fps.nii.gz"
        image = nib.load(path)
        qform = image.get_qform()
        sform = image.get_sform()
        units = image.header.get_xyzt_units()[0]
        spacing = tuple(float(value) for value in image.header.get_zooms()[:3])
        expected_spacing = float(thresholds["nifti_voxel_spacing_mm"])
        expected_origin = np.asarray(row["grid"]["origin_mm"])
        add_check(
            checks,
            f"{row['scan']} NIfTI units",
            units,
            "==",
            thresholds["nifti_spatial_units"],
            units == thresholds["nifti_spatial_units"],
        )
        add_check(
            checks,
            f"{row['scan']} qform equals sform",
            bool(np.allclose(qform, sform)),
            "==",
            True,
            bool(np.allclose(qform, sform)),
        )
        add_check(
            checks,
            f"{row['scan']} affine origin",
            qform[:3, 3].tolist(),
            "allclose",
            expected_origin.tolist(),
            bool(np.allclose(qform[:3, 3], expected_origin)),
        )
        add_check(
            checks,
            f"{row['scan']} voxel spacing",
            list(spacing),
            "allclose",
            [expected_spacing] * 3,
            bool(np.allclose(spacing, expected_spacing)),
        )

    full_nrmse = max(row["raw_nrmse_union"] for row in full_rows)
    full_nrmse_limit = thresholds["full_20fps_raw_nrmse_union_max"]
    add_check(
        checks,
        "full_20fps raw union NRMSE",
        full_nrmse,
        "<=",
        full_nrmse_limit,
        full_nrmse <= full_nrmse_limit,
    )

    full_landmarks = next(
        row for row in landmarks["overall"] if row["condition"] == "full_20fps"
    )
    landmark_max = max(
        full_landmarks["transform_point_error_global_mm_max"],
        full_landmarks["transform_point_error_local_mm_max"],
    )
    landmark_limit = thresholds["full_20fps_landmark_error_max_mm"]
    add_check(
        checks,
        "full_20fps landmark transform error",
        landmark_max,
        "<=",
        landmark_limit,
        landmark_max <= landmark_limit,
    )

    for condition, limits in thresholds["condition_limits"].items():
        rows = [row for row in metrics["conditions"] if row["condition"] == condition]
        nrmse_max = max(row["raw_nrmse_union"] for row in rows)
        dice_min = min(row["raw_occupied_volume_dice"] for row in rows)
        add_check(
            checks,
            f"{condition} raw union NRMSE",
            nrmse_max,
            "<=",
            limits["raw_nrmse_union_max"],
            nrmse_max <= limits["raw_nrmse_union_max"],
        )
        add_check(
            checks,
            f"{condition} raw occupied Dice",
            dice_min,
            ">=",
            limits["raw_occupied_volume_dice_min"],
            dice_min >= limits["raw_occupied_volume_dice_min"],
        )

    stride_one = next(row for row in benchmark["benchmarks"] if row["pixel_stride"] == 1)
    fps_limit = thresholds["benchmark_stride_1_fps_min_reference_workstation"]
    add_check(
        checks,
        "stride 1 frames per second",
        stride_one["frames_per_second"],
        ">=",
        fps_limit,
        stride_one["frames_per_second"] >= fps_limit,
    )

    output = {
        "freeze_id": config["parameter_freeze_id"],
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    write_json(result_dir / "acceptance.json", output)
    print(f"Acceptance: {'PASS' if output['passed'] else 'FAIL'} ({len(checks)} checks)")
    if not output["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
