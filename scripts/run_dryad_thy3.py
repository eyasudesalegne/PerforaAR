#!/usr/bin/env python3
"""Run the THY3 virtual tracked-sweep test on the public Dryad cUSi volumes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import yaml
from scipy import ndimage

from perforaar.reconstruction import (
    VolumeGrid,
    compound_tracked_frames,
    drop_internal_frames,
    interpolate_parallel_sweep,
    parallel_sweep_indices,
    virtual_parallel_sweep,
)


def dice_score(reference: np.ndarray, candidate: np.ndarray) -> float:
    denominator = int(reference.sum() + candidate.sum())
    intersection = int(np.logical_and(reference, candidate).sum())
    return 1.0 if denominator == 0 else 2.0 * intersection / denominator


def surface_dice(reference: np.ndarray, candidate: np.ndarray, tolerance: float) -> float:
    structure = ndimage.generate_binary_structure(3, 1)
    reference_surface = reference ^ ndimage.binary_erosion(reference, structure=structure)
    candidate_surface = candidate ^ ndimage.binary_erosion(candidate, structure=structure)
    denominator = int(reference_surface.sum() + candidate_surface.sum())
    if denominator == 0:
        return 1.0
    if not reference_surface.any() or not candidate_surface.any():
        return 0.0
    distance_to_candidate = ndimage.distance_transform_edt(~candidate_surface)
    distance_to_reference = ndimage.distance_transform_edt(~reference_surface)
    matches = int((distance_to_candidate[reference_surface] <= tolerance).sum())
    matches += int((distance_to_reference[candidate_surface] <= tolerance).sum())
    return matches / denominator


def evaluate(
    true_power: np.ndarray,
    true_velocity: np.ndarray,
    reconstructed_power: np.ndarray,
    reconstructed_velocity: np.ndarray,
    power_threshold: float,
    velocity_minimum: float,
    surface_tolerance: float,
) -> dict:
    true_mask = true_power >= power_threshold
    reconstructed_mask = reconstructed_power >= power_threshold
    power_error = reconstructed_power.astype(np.float64) - true_power
    velocity_error = reconstructed_velocity.astype(np.float64) - true_velocity
    power_range = float(np.percentile(true_power, 99.9) - np.percentile(true_power, 0.1))
    velocity_evaluable = true_mask & (np.abs(true_velocity) >= velocity_minimum)
    return {
        "vessel_voxels": int(true_mask.sum()),
        "vessel_fraction": float(true_mask.mean()),
        "dice": dice_score(true_mask, reconstructed_mask),
        "surface_dice": surface_dice(true_mask, reconstructed_mask, surface_tolerance),
        "power_mae_db": float(np.mean(np.abs(power_error))),
        "power_rmse_db": float(np.sqrt(np.mean(power_error**2))),
        "power_nrmse": float(np.sqrt(np.mean(power_error**2)) / power_range),
        "velocity_mae_m_s": float(np.mean(np.abs(velocity_error))),
        "velocity_mae_vessel_m_s": float(np.mean(np.abs(velocity_error[true_mask]))),
        "velocity_sign_evaluable_voxels": int(velocity_evaluable.sum()),
        "velocity_sign_agreement": float(
            np.mean(
                np.sign(reconstructed_velocity[velocity_evaluable])
                == np.sign(true_velocity[velocity_evaluable])
            )
        ),
    }


def save_corrected_nifti(data: np.ndarray, spacing_mm: float, output_path: Path) -> None:
    affine = np.diag([spacing_mm, spacing_mm, spacing_mm, 1.0])
    image = nib.Nifti1Image(np.asarray(data, dtype=np.float32), affine)
    image.header.set_xyzt_units("mm")
    image.header.set_data_dtype(np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(image, output_path)


def flow_at_power_peak(power: np.ndarray, velocity: np.ndarray) -> np.ndarray:
    indices = np.argmax(power, axis=1)
    return np.take_along_axis(velocity, indices[:, None, :], axis=1)[:, 0, :]


def save_figure(
    name: str,
    true_power: np.ndarray,
    true_velocity: np.ndarray,
    reconstructed_power: np.ndarray,
    reconstructed_velocity: np.ndarray,
    output_path: Path,
) -> None:
    power_true_projection = np.max(true_power, axis=1)
    power_reconstructed_projection = np.max(reconstructed_power, axis=1)
    flow_true_projection = flow_at_power_peak(true_power, true_velocity)
    flow_reconstructed_projection = flow_at_power_peak(reconstructed_power, reconstructed_velocity)
    power_min, power_max = np.percentile(power_true_projection, [1, 99.8])
    flow_limit = np.percentile(np.abs(flow_true_projection), 99.5)

    figure, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    power_images = [
        (power_true_projection, "Reference power MIP"),
        (power_reconstructed_projection, "Sparse-sweep power MIP"),
        (np.abs(power_reconstructed_projection - power_true_projection), "Absolute power error"),
    ]
    for column, (image, title) in enumerate(power_images):
        kwargs = {"cmap": "magma", "origin": "lower"}
        if column < 2:
            kwargs.update(vmin=power_min, vmax=power_max)
        artist = axes[0, column].imshow(image.T, **kwargs)
        axes[0, column].set_title(title)
        figure.colorbar(artist, ax=axes[0, column], shrink=0.75, label="dB")

    flow_images = [
        (flow_true_projection, "Reference signed flow"),
        (flow_reconstructed_projection, "Sparse-sweep signed flow"),
        (np.abs(flow_reconstructed_projection - flow_true_projection), "Absolute flow error"),
    ]
    for column, (image, title) in enumerate(flow_images):
        if column < 2:
            artist = axes[1, column].imshow(
                image.T, cmap="coolwarm", origin="lower", vmin=-flow_limit, vmax=flow_limit
            )
        else:
            artist = axes[1, column].imshow(image.T, cmap="viridis", origin="lower")
        axes[1, column].set_title(title)
        figure.colorbar(artist, ax=axes[1, column], shrink=0.75, label="m/s")
    for axis in axes.ravel():
        axis.set_xlabel("x voxel")
        axis.set_ylabel("z voxel")
    figure.suptitle(f"{name}: Dryad virtual tracked-sweep reconstruction", fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def markdown_summary(results: dict) -> str:
    lines = [
        "# Dryad THY3 reconstruction result",
        "",
        f"**Overall status: {results['overall_status']}**",
        "",
        "This is a software-verification experiment. The public Dryad data are already",
        "reconstructed 3D mouse-brain volumes, so the tracked 2D frames below are virtual",
        "slices with known poses—not the original acquisitions and not clinical validation.",
        "",
        "| Dataset | Condition | Frames | Raw coverage | Dice | Surface Dice | "
        "Flow sign | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset in results["datasets"]:
        for condition, metrics in dataset["conditions"].items():
            lines.append(
                f"| {dataset['name']} | {condition} | {metrics['frame_count']} | "
                f"{metrics['raw_coverage_fraction']:.3f} | {metrics['dice']:.4f} | "
                f"{metrics['surface_dice']:.4f} | {metrics['velocity_sign_agreement']:.4f} | "
                f"{metrics['status']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `exact`: every source plane is replayed and tests coordinate transforms "
            "and compounding.",
            "- `sparse`: every fourth plane (160 μm nominal spacing) is replayed, "
            "then linearly filled.",
            "- `dropout_20pct`: 20% of internal sparse frames are removed before reconstruction.",
            "- Flow sign is evaluated only in the reference vessel mask where "
            "|velocity| ≥ 0.1 mm/s.",
            "- The README and NIfTI `pixdim` support 40 μm spacing, while the encoded s-form has",
            "  a conflicting 0.025 scale and no declared units. Preprocessed outputs therefore use",
            "  the documented 0.04 mm spacing and record this provenance decision.",
            "",
        ]
    )
    return "\n".join(lines)


def run_dataset(
    name: str,
    data_dir: Path,
    results_dir: Path,
    volume_dir: Path,
    configuration: dict,
) -> tuple[dict, dict]:
    power_path = data_dir / f"{name}_Power_Doppler.nii"
    velocity_path = data_dir / f"{name}_Color_Doppler.nii"
    power_image = nib.load(power_path)
    velocity_image = nib.load(velocity_path)
    power = np.asarray(power_image.dataobj, dtype=np.float32)
    velocity = np.asarray(velocity_image.dataobj, dtype=np.float32)
    invalid_data = not np.isfinite(power).all() or not np.isfinite(velocity).all()
    incompatible_geometry = not np.allclose(power_image.affine, velocity_image.affine)
    if power.shape != velocity.shape or invalid_data or incompatible_geometry:
        raise RuntimeError(f"invalid paired volumes for {name}")

    spacing_mm = float(configuration["dataset"]["voxel_spacing_mm"])
    grid = VolumeGrid(tuple(int(value) for value in power.shape), (spacing_mm,) * 3)
    threshold = float(np.percentile(power, configuration["dataset"]["power_mask_percentile"]))
    sparse_indices = parallel_sweep_indices(
        power.shape[1], int(configuration["virtual_acquisition"]["sparse_step_voxels"])
    )
    dropout_indices = drop_internal_frames(
        sparse_indices,
        float(configuration["virtual_acquisition"]["dropout_fraction"]),
        seed=int(configuration["virtual_acquisition"]["random_seed"]),
    )
    conditions = {
        "exact": np.arange(power.shape[1], dtype=int),
        "sparse": sparse_indices,
        "dropout_20pct": dropout_indices,
    }
    condition_results: dict[str, dict] = {}
    sparse_reconstruction: tuple[np.ndarray, np.ndarray] | None = None

    for condition_name, indices in conditions.items():
        compounded = compound_tracked_frames(
            virtual_parallel_sweep(power, velocity, grid, indices), grid
        )
        if condition_name == "exact":
            reconstructed_power = compounded.power_db
            reconstructed_velocity = compounded.velocity_m_s
        else:
            reconstructed_power = interpolate_parallel_sweep(compounded.power_db, indices)
            reconstructed_velocity = interpolate_parallel_sweep(compounded.velocity_m_s, indices)
        metrics = evaluate(
            power,
            velocity,
            reconstructed_power,
            reconstructed_velocity,
            threshold,
            float(configuration["evaluation"]["minimum_velocity_magnitude_m_s"]),
            float(configuration["evaluation"]["surface_tolerance_voxels"]),
        )
        metrics["frame_count"] = int(indices.size)
        metrics["raw_coverage_fraction"] = float(compounded.observed.mean())
        metrics["interpolated_coverage_fraction"] = 1.0
        metrics["plane_indices"] = indices.tolist()
        condition_results[condition_name] = metrics
        if condition_name == "sparse":
            sparse_reconstruction = (reconstructed_power.copy(), reconstructed_velocity.copy())

    acceptance = configuration["evaluation"]["acceptance"]
    exact = condition_results["exact"]
    sparse = condition_results["sparse"]
    dropout = condition_results["dropout_20pct"]
    exact_pass = (
        exact["raw_coverage_fraction"] >= acceptance["exact_coverage_fraction_min"]
        and exact["power_mae_db"] <= acceptance["exact_power_mae_db_max"]
        and exact["velocity_mae_m_s"] <= acceptance["exact_velocity_mae_m_s_max"]
    )
    sparse_pass = (
        sparse["dice"] >= acceptance["sparse_dice_min"]
        and sparse["surface_dice"] >= acceptance["sparse_surface_dice_min"]
        and sparse["velocity_sign_agreement"] >= acceptance["sparse_velocity_sign_agreement_min"]
    )
    dropout_dice_loss = sparse["dice"] - dropout["dice"]
    dropout_pass = dropout_dice_loss <= acceptance["dropout_dice_loss_max"]
    exact["status"] = "PASS" if exact_pass else "FAIL"
    sparse["status"] = "PASS" if sparse_pass else "FAIL"
    dropout["status"] = "PASS" if dropout_pass else "FAIL"

    assert sparse_reconstruction is not None
    sparse_power, sparse_velocity = sparse_reconstruction
    save_corrected_nifti(
        power, spacing_mm, volume_dir / "preprocessed" / f"{name}_Power_Doppler_0p04mm.nii.gz"
    )
    save_corrected_nifti(
        velocity,
        spacing_mm,
        volume_dir / "preprocessed" / f"{name}_Color_Doppler_0p04mm.nii.gz",
    )
    save_corrected_nifti(
        sparse_power,
        spacing_mm,
        volume_dir / "reconstructed" / f"{name}_Power_Doppler_sparse.nii.gz",
    )
    save_corrected_nifti(
        sparse_velocity,
        spacing_mm,
        volume_dir / "reconstructed" / f"{name}_Color_Doppler_sparse.nii.gz",
    )
    save_figure(
        name,
        power,
        velocity,
        sparse_power,
        sparse_velocity,
        results_dir / "figures" / f"{name.lower()}_sparse_reconstruction.png",
    )

    header_spacing = [float(value) for value in power_image.header.get_zooms()[:3]]
    sform_spacing = [float(np.linalg.norm(power_image.affine[:3, axis])) for axis in range(3)]
    dataset_result = {
        "name": name,
        "shape": list(power.shape),
        "nominal_spacing_mm": spacing_mm,
        "power_threshold_db": threshold,
        "header_pixdim_raw": header_spacing,
        "sform_scale_raw": sform_spacing,
        "nifti_spatial_units": power_image.header.get_xyzt_units()[0],
        "conditions": condition_results,
        "dropout_dice_loss": dropout_dice_loss,
        "status": "PASS" if exact_pass and sparse_pass and dropout_pass else "FAIL",
    }
    preprocessing = {
        "dataset": name,
        "source_affine": power_image.affine.tolist(),
        "source_header_pixdim_raw": header_spacing,
        "source_units": power_image.header.get_xyzt_units()[0],
        "applied_spacing_mm": spacing_mm,
        "operations": [
            "validated paired shape and finite values",
            "preserved original float32 voxel values",
            "replaced ambiguous spatial metadata with documented 0.04 mm isotropic spacing",
        ],
    }
    return dataset_result, preprocessing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw/dryad_cusi"))
    parser.add_argument("--config", type=Path, default=Path("configs/dryad_thy3.yaml"))
    parser.add_argument("--results-dir", type=Path, default=Path("results/dryad_thy3"))
    parser.add_argument("--volume-dir", type=Path, default=Path("outputs/dryad_thy3/volumes"))
    args = parser.parse_args()

    configuration = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.volume_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "experiment": "Dryad THY3 virtual tracked 2D Doppler reconstruction",
        "config": str(args.config),
        "dataset_doi": configuration["dataset"]["doi"],
        "datasets": [],
    }
    preprocessing = []
    for name in ("Awake", "Anesthetized"):
        dataset_result, preprocessing_record = run_dataset(
            name, args.data_dir, args.results_dir, args.volume_dir, configuration
        )
        results["datasets"].append(dataset_result)
        preprocessing.append(preprocessing_record)
    results["overall_status"] = (
        "PASS" if all(dataset["status"] == "PASS" for dataset in results["datasets"]) else "FAIL"
    )
    (args.results_dir / "metrics.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (args.results_dir / "preprocessing.json").write_text(
        json.dumps(preprocessing, indent=2) + "\n", encoding="utf-8"
    )
    (args.results_dir / "SUMMARY.md").write_text(markdown_summary(results), encoding="utf-8")
    print(json.dumps({"overall_status": results["overall_status"]}, indent=2))
    if results["overall_status"] != "PASS":
        sys.exit(2)


if __name__ == "__main__":
    main()
