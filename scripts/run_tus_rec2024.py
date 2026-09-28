from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.landmark_evaluation import (
    evaluate_landmark_errors,
    load_landmarks,
    summarize_landmark_records,
)
from perforaar.tracked_volume import (
    Calibration,
    GridSpec,
    ScanId,
    compare_volumes,
    compute_grid,
    condition_transforms,
    derive_valid_pixel_mask,
    frame_path,
    list_scans,
    parse_scan_metadata,
    perturb_calibration,
    read_calibration,
    reconstruct_volume,
    reference_from_image_transforms,
    trajectory_error,
    transform_path,
    transform_point_error_mm,
    write_json,
    write_nifti_gz,
)


def scan_from_text(text: str) -> ScanId:
    subject, name = text.split("/", 1)
    return ScanId(subject=subject, name=name)


def image_shape(root: Path, scan: ScanId) -> tuple[int, int]:
    with h5py.File(frame_path(root, scan), "r") as f:
        return int(f["frames"].shape[1]), int(f["frames"].shape[2])


def load_ref(root: Path, scan: ScanId, calib: Calibration) -> np.ndarray:
    with h5py.File(transform_path(root, scan), "r") as f:
        tforms = np.asarray(f["tforms"], dtype=np.float64)
    return reference_from_image_transforms(tforms, calib)


def load_camera_from_image(root: Path, scan: ScanId, calib: Calibration) -> np.ndarray:
    with h5py.File(transform_path(root, scan), "r") as f:
        tforms = np.asarray(f["tforms"], dtype=np.float64)
    return np.einsum("nij,jk->nik", tforms, calib.tool_from_image)


def plot_trajectory(path: Path, transforms: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    xyz = transforms[:, :3, 3]
    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2], lw=1.8)
    ax.scatter(xyz[0, 0], xyz[0, 1], xyz[0, 2], s=30, label="start")
    ax.scatter(xyz[-1, 0], xyz[-1, 1], xyz[-1, 2], s=30, label="end")
    ax.set_title(title)
    ax.set_xlabel("x mm")
    ax.set_ylabel("y mm")
    ax.set_zlabel("z mm")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_slices(path: Path, volume: np.ndarray, counts: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    z, y, x = [s // 2 for s in volume.shape]
    fig, axes = plt.subplots(1, 4, figsize=(12, 4))
    axes[0].imshow(volume[z], cmap="gray")
    axes[0].set_title("axial")
    axes[1].imshow(volume[:, y, :], cmap="gray", aspect="auto")
    axes[1].set_title("coronal")
    axes[2].imshow(volume[:, :, x], cmap="gray", aspect="auto")
    axes[2].set_title("sagittal")
    axes[3].imshow(counts.max(axis=0), cmap="magma")
    axes[3].set_title("coverage")
    for ax in axes:
        ax.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_valid_mask(path: Path, frames_file: Path, mask: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(frames_file, "r") as frame_file:
        representative = np.asarray(frame_file["frames"][frame_file["frames"].shape[0] // 2])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].imshow(representative, cmap="gray")
    axes[0].contour(mask, levels=[0.5], colors=["#e53935"], linewidths=0.8)
    axes[0].set_title("representative frame")
    axes[1].imshow(mask, cmap="gray", vmin=0, vmax=1)
    axes[1].set_title(f"valid mask ({np.mean(mask):.1%})")
    for axis in axes:
        axis.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_degradation(path: Path, condition_rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in condition_rows if r["condition"] != "full_20fps"]
    labels = [r["condition"] for r in rows]
    values = [r.get("raw_nrmse_union", np.nan) for r in rows]
    fig, ax = plt.subplots(figsize=(max(8, len(rows) * 0.5), 4))
    ax.bar(range(len(rows)), values, color="#2b7a78")
    ax.set_xticks(range(len(rows)), labels, rotation=45, ha="right")
    ax.set_ylabel("Raw union NRMSE vs full")
    ax.set_title("Stress-test degradation")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def transforms_for_condition(
    root: Path,
    scan: ScanId,
    calib: Calibration,
    base_ref: np.ndarray,
    cfg: dict,
    condition: dict,
) -> np.ndarray:
    if condition.get("calibration_perturbation"):
        perturbed = perturb_calibration(
            calib,
            condition.get("calibration_translation_mm", [1.0, -1.0, 0.5]),
            condition.get("calibration_rotation_deg_xyz", [0.5, -0.5, 1.0]),
        )
        with h5py.File(transform_path(root, scan), "r") as transform_file:
            raw_tforms = np.asarray(transform_file["tforms"], dtype=np.float64)
        starting_transforms = reference_from_image_transforms(raw_tforms, perturbed)
    else:
        starting_transforms = base_ref
    return condition_transforms(
        starting_transforms,
        pose_delay_frames=int(condition.get("pose_delay_frames", 0)),
        translation_noise_mm=float(condition.get("translation_noise_mm", 0.0)),
        rotation_noise_deg=float(condition.get("rotation_noise_deg", 0.0)),
        seed=int(condition.get("seed", cfg.get("seed", 13))),
    )


def run_condition(
    root: Path,
    scan: ScanId,
    calib: Calibration,
    base_ref: np.ndarray,
    grid: GridSpec,
    cfg: dict,
    condition: dict,
    reference_result: dict | None,
    valid_mask: np.ndarray,
) -> tuple[dict, dict, np.ndarray]:
    transforms = transforms_for_condition(root, scan, calib, base_ref, cfg, condition)

    t0 = time.perf_counter()
    result = reconstruct_volume(
        frame_path(root, scan),
        transforms,
        calib,
        grid=grid,
        frame_step=int(condition.get("frame_step", 1)),
        dropout_fraction=float(condition.get("dropout_fraction", 0.0)),
        pixel_stride=int(cfg["pixel_stride"]),
        fill_holes_mm=float(cfg["fill_holes_mm"]),
        valid_mask=valid_mask,
        seed=int(condition.get("seed", cfg.get("seed", 13))),
    )
    elapsed = time.perf_counter() - t0

    meta = parse_scan_metadata(scan.subject, scan.name)
    scan_name = meta.pop("scan")
    row = {
        "scan": scan.key,
        "scan_name": scan_name,
        "condition": condition["name"],
        **meta,
        "grid": result["grid"].as_dict(),
        **{
            key: value
            for key, value in result.items()
            if key
            not in {"volume", "raw_volume", "counts", "raw_mask", "filled_mask", "grid"}
        },
        "runtime_seconds": elapsed,
        "frames_per_second": result["frames_processed"] / elapsed if elapsed else float("inf"),
        "pixels_processed_per_second": (
            result["frames_processed"] * result["pixels_per_frame"] / elapsed
            if elapsed
            else float("inf")
        ),
        **trajectory_error(base_ref, transforms),
        **transform_point_error_mm(base_ref, transforms, image_shape(root, scan), calib),
    }
    if reference_result is not None:
        row.update(compare_volumes(reference_result, result))
    else:
        row.update(compare_volumes(result, result))
    return row, result, transforms


def forward_reverse_consistency(
    root: Path,
    cfg: dict,
    calib: Calibration,
    masks: dict[str, np.ndarray],
) -> list[dict]:
    configured = [scan_from_text(text) for text in cfg["reconstruction_scans"]]
    scans = {
        (scan.subject, scan.name.rsplit("_", 1)[0], scan.name.rsplit("_", 1)[1]): scan
        for scan in configured
    }
    rows = []
    for subject, stem, direction in sorted(scans):
        if direction != "PtD":
            continue
        forward = scans[(subject, stem, "PtD")]
        reverse = scans.get((subject, stem, "DtP"))
        if reverse is None:
            continue
        forward_transforms = load_camera_from_image(root, forward, calib)
        reverse_transforms = load_camera_from_image(root, reverse, calib)
        mask_union = masks[forward.key] | masks[reverse.key]
        transforms = np.concatenate([forward_transforms, reverse_transforms])
        shape = image_shape(root, forward)
        grid = compute_grid(
            transforms,
            shape,
            calib,
            float(cfg["voxel_size_mm"]),
            float(cfg["grid_margin_mm"]),
            mask_union,
        )
        results = []
        for scan, scan_transforms in (
            (forward, forward_transforms),
            (reverse, reverse_transforms),
        ):
            results.append(
                reconstruct_volume(
                    frame_path(root, scan),
                    scan_transforms,
                    calib,
                    grid=grid,
                    pixel_stride=int(cfg["pixel_stride"]),
                    fill_holes_mm=float(cfg["fill_holes_mm"]),
                    valid_mask=masks[scan.key],
                    seed=int(cfg.get("seed", 13)),
                )
            )
        rows.append(
            {
                "subject": subject,
                "scan_pair": stem,
                "proximal_to_distal_scan": forward.key,
                "distal_to_proximal_scan": reverse.key,
                "coordinate_system": "shared optical-tracker camera space",
                **compare_volumes(results[0], results[1]),
            }
        )
    return rows


def evaluate_all_landmarks(root: Path, cfg: dict, calib: Calibration) -> dict:
    records: list[dict] = []
    for scan in list_scans(root, cfg["subjects"]):
        reference = load_ref(root, scan, calib)
        landmarks = load_landmarks(root, scan)
        for condition in cfg["conditions"]:
            candidate = transforms_for_condition(root, scan, calib, reference, cfg, condition)
            records.extend(
                evaluate_landmark_errors(
                    scan,
                    condition["name"],
                    landmarks,
                    reference,
                    candidate,
                    calib,
                )
            )
    return summarize_landmark_records(records)


def validate_experiment_phase(cfg: dict) -> None:
    if cfg.get("experiment_phase") != "locked_confirmatory":
        return
    pilot_subjects = set(cfg.get("pilot_subjects", []))
    locked_subjects = set(cfg.get("locked_validation_subjects", []))
    if not cfg.get("parameters_frozen"):
        raise ValueError("Locked evaluation requires parameters_frozen: true")
    if not locked_subjects:
        raise ValueError("Locked evaluation requires new locked_validation_subjects")
    overlap = pilot_subjects & locked_subjects
    if overlap:
        raise ValueError(f"Locked subjects overlap pilot subjects: {sorted(overlap)}")


def write_summary(path: Path, metrics: dict) -> None:
    validations = metrics["validation_summary"]
    conditions = metrics["conditions"]
    best = min(
        (r for r in conditions if r["condition"] != "full_20fps"),
        key=lambda row: row["raw_nrmse_union"],
    )
    worst = max(
        (r for r in conditions if r["condition"] != "full_20fps"),
        key=lambda row: row["raw_nrmse_union"],
    )
    text = [
        "# TUS-REC2024 Pilot Summary",
        "",
        "- Dataset: TUS-REC2024 Validation Dataset (subjects 050, 051, 052)",
        "- DOI: `10.5281/zenodo.12979481`",
        (
            "- Archive: `Freehand_US_data_val.zip` (approximately 4.8 GB; "
            "MD5 `487ebe3241678569296e47efeb2ea325`)"
        ),
        f"- Scans validated: {validations['total_scans']}",
        f"- Validation failures: {validations['failed_scans']}",
        f"- Reconstruction conditions run: {len(conditions)}",
        (
            f"- Best non-reference raw union NRMSE: {best['condition']} on "
            f"{best['scan']} = {best['raw_nrmse_union']:.4f}"
        ),
        (
            f"- Worst non-reference raw union NRMSE: {worst['condition']} on "
            f"{worst['scan']} = {worst['raw_nrmse_union']:.4f}"
        ),
        "",
        (
            "`full_20fps` is a self-generated reconstruction reference using measured "
            "tracker poses; it is not anatomical ground truth."
        ),
        "",
        (
            "This run validates the tracked geometric reconstruction pipeline. It does not "
            "validate Doppler blood flow or ALT perforator detection because those "
            "labels/modalities are not present in TUS-REC2024."
        ),
    ]
    path.write_text("\n".join(text) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the TUS-REC2024 tracked reconstruction pilot."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/tus_rec2024.yaml"))
    args = parser.parse_args()

    root = args.root.resolve()
    cfg = yaml.safe_load((root / args.config).read_text())
    validate_experiment_phase(cfg)
    out_dir = root / "results" / "tus_rec2024"
    figures = out_dir / "figures"
    volumes = out_dir / "volumes"

    calib = read_calibration(root / cfg["calibration_file"])
    validation_path = out_dir / "validation.json"
    validations = []
    if validation_path.exists():
        import json

        validations = json.loads(validation_path.read_text())

    all_rows: list[dict] = []
    masks: dict[str, np.ndarray] = {}
    for scan_text in cfg["reconstruction_scans"]:
        scan = scan_from_text(scan_text)
        base_ref = load_ref(root, scan, calib)
        mask = derive_valid_pixel_mask(
            frame_path(root, scan),
            min_nonzero_fraction=float(cfg["valid_mask"]["min_nonzero_fraction"]),
            intensity_threshold=int(cfg["valid_mask"]["intensity_threshold"]),
        )
        masks[scan.key] = mask
        grid = None
        reference_result = None
        scan_rows: list[dict] = []
        for condition in cfg["conditions"]:
            if grid is None:
                with h5py.File(frame_path(root, scan), "r") as f:
                    h, w = int(f["frames"].shape[1]), int(f["frames"].shape[2])
                grid = compute_grid(
                    base_ref,
                    (h, w),
                    calib,
                    float(cfg["voxel_size_mm"]),
                    float(cfg["grid_margin_mm"]),
                    mask,
                )
            row, result, transforms = run_condition(
                root,
                scan,
                calib,
                base_ref,
                grid,
                cfg,
                condition,
                reference_result,
                mask,
            )
            scan_rows.append(row)
            all_rows.append(row)
            if condition["name"] == "full_20fps":
                reference_result = result
                safe_name = scan.key.replace("/", "__")
                write_nifti_gz(volumes / f"{safe_name}__full_20fps.nii.gz", result["volume"], grid)
                plot_trajectory(figures / f"{safe_name}__trajectory.png", base_ref, scan.key)
                plot_slices(
                    figures / f"{safe_name}__slices.png",
                    result["volume"],
                    result["counts"],
                    scan.key,
                )
                plot_valid_mask(
                    figures / f"{safe_name}__valid_mask.png",
                    frame_path(root, scan),
                    mask,
                    scan.key,
                )
        plot_degradation(figures / f"{scan.key.replace('/', '__')}__degradation.png", scan_rows)

    landmark_metrics = evaluate_all_landmarks(root, cfg, calib)
    reverse_consistency = forward_reverse_consistency(root, cfg, calib, masks)
    metrics = {
        "config": cfg,
        "reference_definition": (
            "full_20fps is reconstructed from every frame using measured tracker poses; "
            "it is a self-generated reference, not anatomical ground truth"
        ),
        "metric_definitions": {
            "reference_coverage_retained": (
                "intersection occupied voxels / reference occupied voxels"
            ),
            "false_additional_coverage": (
                "candidate-only occupied voxels / reference occupied voxels"
            ),
            "masked_ssim": "mean 3D SSIM map within the union of occupied voxels",
        },
        "validation_summary": {
            "total_scans": len(validations),
            "failed_scans": sum(1 for row in validations if not row.get("passed")),
        },
        "conditions": all_rows,
        "forward_reverse_consistency": reverse_consistency,
    }
    write_json(out_dir / "metrics.json", metrics)
    write_json(out_dir / "landmark_metrics.json", landmark_metrics)
    write_summary(out_dir / "SUMMARY.md", metrics)
    print(f"Wrote {out_dir / 'metrics.json'}")
    print(f"Wrote {out_dir / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
