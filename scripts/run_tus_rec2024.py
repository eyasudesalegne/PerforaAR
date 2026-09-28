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

from perforaar.tracked_volume import (
    Calibration,
    GridSpec,
    ScanId,
    compare_volumes,
    condition_transforms,
    frame_path,
    parse_scan_metadata,
    pose_point_error_mm,
    read_calibration,
    reconstruct_volume,
    reference_from_image_transforms,
    trajectory_error,
    transform_path,
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


def plot_degradation(path: Path, condition_rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in condition_rows if r["condition"] != "full_20fps"]
    labels = [r["condition"] for r in rows]
    values = [r.get("nrmse", np.nan) for r in rows]
    fig, ax = plt.subplots(figsize=(max(8, len(rows) * 0.5), 4))
    ax.bar(range(len(rows)), values, color="#2b7a78")
    ax.set_xticks(range(len(rows)), labels, rotation=45, ha="right")
    ax.set_ylabel("NRMSE vs full")
    ax.set_title("Stress-test degradation")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_condition(
    root: Path,
    scan: ScanId,
    calib: Calibration,
    base_ref: np.ndarray,
    grid: GridSpec,
    cfg: dict,
    condition: dict,
    reference_result: dict | None,
) -> dict:
    if condition.get("calibration_perturbation"):
        perturbed = Calibration(calib.pixel_to_mm.copy(), calib.tool_from_image.copy())
        perturbed.tool_from_image[:3, 3] += np.array([1.0, -1.0, 0.5])
        with h5py.File(transform_path(root, scan), "r") as f:
            raw_tforms = np.asarray(f["tforms"], dtype=np.float64)
        starting_transforms = reference_from_image_transforms(raw_tforms, perturbed)
    else:
        starting_transforms = base_ref

    transforms = condition_transforms(
        starting_transforms,
        pose_delay_frames=int(condition.get("pose_delay_frames", 0)),
        translation_noise_mm=float(condition.get("translation_noise_mm", 0.0)),
        rotation_noise_deg=float(condition.get("rotation_noise_deg", 0.0)),
        seed=int(condition.get("seed", cfg.get("seed", 13))),
    )

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
        **{k: v for k, v in result.items() if k not in {"volume", "raw_volume", "counts", "grid"}},
        "runtime_seconds": elapsed,
        "frames_per_second": result["frames_processed"] / elapsed if elapsed else float("inf"),
        **trajectory_error(base_ref, transforms),
        **pose_point_error_mm(base_ref, transforms, image_shape(root, scan), calib),
    }
    if reference_result is not None:
        row.update(
            compare_volumes(
                reference_result["raw_volume"],
                result["raw_volume"],
                reference_result["counts"],
                result["counts"],
            )
        )
    else:
        row.update({"overlap_voxels": result["covered_voxels"], "nrmse": 0.0, "ssim_mean": 1.0})
    return row, result


def write_summary(path: Path, metrics: dict) -> None:
    validations = metrics["validation_summary"]
    conditions = metrics["conditions"]
    best = min((r for r in conditions if r["condition"] != "full_20fps"), key=lambda r: r["nrmse"])
    worst = max((r for r in conditions if r["condition"] != "full_20fps"), key=lambda r: r["nrmse"])
    text = [
        "# TUS-REC2024 Pilot Summary",
        "",
        f"- Scans validated: {validations['total_scans']}",
        f"- Validation failures: {validations['failed_scans']}",
        f"- Reconstruction conditions run: {len(conditions)}",
        f"- Best non-reference NRMSE: {best['condition']} on {best['scan']} = {best['nrmse']:.4f}",
        f"- Worst non-reference NRMSE: {worst['condition']} on {worst['scan']} = {worst['nrmse']:.4f}",
        "",
        "This run validates the tracked geometric reconstruction pipeline. It does not validate Doppler blood flow or ALT perforator detection because those labels/modalities are not present in TUS-REC2024.",
    ]
    path.write_text("\n".join(text) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TUS-REC2024 tracked reconstruction pilot.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/tus_rec2024.yaml"))
    args = parser.parse_args()

    root = args.root.resolve()
    cfg = yaml.safe_load((root / args.config).read_text())
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
    for scan_text in cfg["reconstruction_scans"]:
        scan = scan_from_text(scan_text)
        base_ref = load_ref(root, scan, calib)
        grid = None
        reference_result = None
        scan_rows: list[dict] = []
        for condition in cfg["conditions"]:
            if grid is None:
                with h5py.File(frame_path(root, scan), "r") as f:
                    h, w = int(f["frames"].shape[1]), int(f["frames"].shape[2])
                from perforaar.tracked_volume import compute_grid

                grid = compute_grid(
                    base_ref,
                    (h, w),
                    calib,
                    float(cfg["voxel_size_mm"]),
                    float(cfg["grid_margin_mm"]),
                )
            row, result = run_condition(root, scan, calib, base_ref, grid, cfg, condition, reference_result)
            scan_rows.append(row)
            all_rows.append(row)
            if condition["name"] == "full_20fps":
                reference_result = result
                safe_name = scan.key.replace("/", "__")
                write_nifti_gz(volumes / f"{safe_name}__full_20fps.nii.gz", result["volume"], grid)
                plot_trajectory(figures / f"{safe_name}__trajectory.png", base_ref, scan.key)
                plot_slices(figures / f"{safe_name}__slices.png", result["volume"], result["counts"], scan.key)
        plot_degradation(figures / f"{scan.key.replace('/', '__')}__degradation.png", scan_rows)

    metrics = {
        "config": cfg,
        "validation_summary": {
            "total_scans": len(validations),
            "failed_scans": sum(1 for row in validations if not row.get("passed")),
        },
        "conditions": all_rows,
    }
    write_json(out_dir / "metrics.json", metrics)
    write_summary(out_dir / "SUMMARY.md", metrics)
    print(f"Wrote {out_dir / 'metrics.json'}")
    print(f"Wrote {out_dir / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
