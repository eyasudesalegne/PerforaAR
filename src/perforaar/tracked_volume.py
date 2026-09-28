from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import nibabel as nib
import numpy as np
from scipy import ndimage
from skimage.metrics import structural_similarity

SCAN_RE = re.compile(
    r"^(?P<arm>LH|RH)_(?P<orientation>Par|Per)_(?P<trajectory>C|L|S)_(?P<direction>DtP|PtD)$"
)


@dataclass(frozen=True)
class ScanId:
    subject: str
    name: str

    @property
    def key(self) -> str:
        return f"{self.subject}/{self.name}"


@dataclass(frozen=True)
class Calibration:
    pixel_to_mm: np.ndarray
    tool_from_image: np.ndarray


@dataclass(frozen=True)
class GridSpec:
    origin_mm: np.ndarray
    voxel_size_mm: float
    shape_zyx: tuple[int, int, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "origin_mm": self.origin_mm.tolist(),
            "voxel_size_mm": self.voxel_size_mm,
            "shape_zyx": list(self.shape_zyx),
        }


def read_calibration(path: Path) -> Calibration:
    blocks: dict[str, list[list[float]]] = {}
    current: str | None = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(ch.isalpha() for ch in line):
            current = line
            blocks[current] = []
        elif current:
            blocks[current].append([float(x) for x in line.split(",")])
    return Calibration(
        pixel_to_mm=np.asarray(blocks["scaling_from_pixel_to_mm"], dtype=np.float64),
        tool_from_image=np.asarray(
            blocks[
                "spatial_calibration_from_image_coordinate_system_to_tracking_tool_coordinate_system"
            ],
            dtype=np.float64,
        ),
    )


def parse_scan_metadata(subject: str, scan_name: str) -> dict[str, str]:
    match = SCAN_RE.match(scan_name)
    if not match:
        raise ValueError(f"Unexpected scan name: {scan_name}")
    meta = match.groupdict()
    return {
        "subject": subject,
        "scan": scan_name,
        "arm": {"LH": "left", "RH": "right"}[meta["arm"]],
        "probe_orientation": {"Par": "parallel", "Per": "perpendicular"}[
            meta["orientation"]
        ],
        "trajectory": {"C": "C-shaped", "L": "linear", "S": "S-shaped"}[
            meta["trajectory"]
        ],
        "direction": {
            "DtP": "distal-to-proximal",
            "PtD": "proximal-to-distal",
        }[meta["direction"]],
    }


def list_scans(root: Path, subjects: Iterable[str] | None = None) -> list[ScanId]:
    subject_filter = set(subjects or [])
    scans: list[ScanId] = []
    for subject_dir in sorted((root / "frames").glob("*")):
        if not subject_dir.is_dir():
            continue
        if subject_filter and subject_dir.name not in subject_filter:
            continue
        for frame_file in sorted(subject_dir.glob("*.h5")):
            scans.append(ScanId(subject=subject_dir.name, name=frame_file.stem))
    return scans


def frame_path(root: Path, scan: ScanId) -> Path:
    return root / "frames" / scan.subject / f"{scan.name}.h5"


def transform_path(root: Path, scan: ScanId) -> Path:
    return root / "transfs" / scan.subject / f"{scan.name}.h5"


def landmark_path(root: Path, subject: str) -> Path:
    return root / "landmark" / f"landmark_{subject}.h5"


def load_tforms(root: Path, scan: ScanId) -> np.ndarray:
    with h5py.File(transform_path(root, scan), "r") as f:
        return np.asarray(f["tforms"], dtype=np.float64)


def hash_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> dict[str, str]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
            sha256.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def make_manifest(root: Path, hash_contents: bool = True) -> dict[str, Any]:
    files = []
    for path in sorted(root.glob("**/*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        excluded_dirs = {".git", "results", "src", "scripts", "tests", "docs", "configs", "data"}
        if any(part in excluded_dirs for part in path.parts):
            continue
        item: dict[str, Any] = {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
        }
        if hash_contents:
            item.update(hash_file(path))
        files.append(item)
    return {
        "dataset": "TUS-REC2024 Validation Dataset",
        "subjects": ["050", "051", "052"],
        "source": "https://zenodo.org/records/12979481",
        "doi": "10.5281/zenodo.12979481",
        "version": "2.0.0",
        "source_archive": {
            "name": "Freehand_US_data_val.zip",
            "bytes": 4_842_723_858,
            "md5": "487ebe3241678569296e47efeb2ea325",
        },
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_count": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }


def _rotation_angles_deg(rotations: np.ndarray) -> np.ndarray:
    if len(rotations) < 2:
        return np.asarray([], dtype=np.float64)
    rel = np.einsum("nij,njk->nik", np.swapaxes(rotations[:-1], 1, 2), rotations[1:])
    traces = np.trace(rel, axis1=1, axis2=2)
    cosang = np.clip((traces - 1.0) * 0.5, -1.0, 1.0)
    return np.degrees(np.arccos(cosang))


def validate_scan(root: Path, scan: ScanId) -> dict[str, Any]:
    frames_file = frame_path(root, scan)
    tforms_file = transform_path(root, scan)
    meta = parse_scan_metadata(scan.subject, scan.name)

    with h5py.File(frames_file, "r") as ff, h5py.File(tforms_file, "r") as tf:
        frames = ff["frames"]
        tforms = np.asarray(tf["tforms"], dtype=np.float64)

        rotations = tforms[:, :3, :3]
        translations = tforms[:, :3, 3]
        ortho_err = np.linalg.norm(
            np.einsum("nij,nkj->nik", rotations, rotations) - np.eye(3), axis=(1, 2)
        )
        dets = np.linalg.det(rotations)
        trans_delta = (
            np.linalg.norm(np.diff(translations, axis=0), axis=1)
            if len(tforms) > 1
            else np.asarray([])
        )
        rot_delta = _rotation_angles_deg(rotations)

        blank_frames = 0
        duplicate_adjacent = 0
        previous_digest: bytes | None = None
        for idx in range(frames.shape[0]):
            sample = np.asarray(frames[idx, ::8, ::8])
            if sample.max() == sample.min():
                blank_frames += 1
            digest = hashlib.blake2b(sample.tobytes(), digest_size=8).digest()
            if previous_digest == digest:
                duplicate_adjacent += 1
            previous_digest = digest

    problems = []
    if frames.shape[0] != tforms.shape[0]:
        problems.append("frame_transform_count_mismatch")
    if not np.isfinite(tforms).all():
        problems.append("nonfinite_transform")
    if float(np.max(ortho_err)) > 1e-3 or not np.allclose(dets, 1.0, atol=1e-3):
        problems.append("invalid_rotation_matrix")
    if blank_frames:
        problems.append("blank_frames")
    if trans_delta.size and float(np.max(trans_delta)) > 5.0:
        problems.append("large_translation_jump")
    if rot_delta.size and float(np.max(rot_delta)) > 15.0:
        problems.append("large_rotation_jump")

    return {
        **meta,
        "frames_shape": list(frames.shape),
        "tforms_shape": list(tforms.shape),
        "passed": not problems,
        "problems": problems,
        "blank_frames": blank_frames,
        "adjacent_duplicate_frame_samples": duplicate_adjacent,
        "rotation_orthonormal_error_max": float(np.max(ortho_err)),
        "rotation_determinant_min": float(np.min(dets)),
        "rotation_determinant_max": float(np.max(dets)),
        "translation_delta_mm_mean": float(np.mean(trans_delta)) if trans_delta.size else 0.0,
        "translation_delta_mm_max": float(np.max(trans_delta)) if trans_delta.size else 0.0,
        "rotation_delta_deg_mean": float(np.mean(rot_delta)) if rot_delta.size else 0.0,
        "rotation_delta_deg_max": float(np.max(rot_delta)) if rot_delta.size else 0.0,
    }


def reference_from_image_transforms(tforms: np.ndarray, calib: Calibration) -> np.ndarray:
    camera_from_image = np.einsum("nij,jk->nik", tforms, calib.tool_from_image)
    first_inv = np.linalg.inv(camera_from_image[0])
    return np.einsum("ij,njk->nik", first_inv, camera_from_image)


def _pixel_grid(height: int, width: int, stride: int) -> np.ndarray:
    rows = np.arange(0, height, stride, dtype=np.float64)
    cols = np.arange(0, width, stride, dtype=np.float64)
    cc, rr = np.meshgrid(cols, rows)
    pts = np.stack([cc.ravel(), rr.ravel(), np.zeros(cc.size), np.ones(cc.size)], axis=0)
    return pts


def derive_valid_pixel_mask(
    frames_file: Path,
    *,
    min_nonzero_fraction: float = 0.95,
    intensity_threshold: int = 0,
    chunk_size: int = 32,
) -> np.ndarray:
    """Estimate the fixed ultrasound field from pixels persistently above background."""
    if not 0 < min_nonzero_fraction <= 1:
        raise ValueError("min_nonzero_fraction must be in (0, 1]")
    with h5py.File(frames_file, "r") as ff:
        frames = ff["frames"]
        counts = np.zeros(frames.shape[1:], dtype=np.int64)
        for start in range(0, frames.shape[0], chunk_size):
            chunk = np.asarray(frames[start : start + chunk_size])
            counts += np.count_nonzero(chunk > intensity_threshold, axis=0)
        mask = counts / frames.shape[0] >= min_nonzero_fraction

    labels, count = ndimage.label(mask)
    if count:
        component_sizes = np.bincount(labels.ravel())
        component_sizes[0] = 0
        mask = labels == int(np.argmax(component_sizes))
    mask = ndimage.binary_fill_holes(mask)
    if not np.any(mask):
        raise ValueError(f"No valid ultrasound pixels found in {frames_file}")
    return np.asarray(mask, dtype=bool)


def transform_pixels(
    transform: np.ndarray,
    pixel_points: np.ndarray,
    pixel_to_mm: np.ndarray,
) -> np.ndarray:
    image_mm = pixel_to_mm @ pixel_points
    pts = transform @ image_mm
    return pts[:3].T


def compute_grid(
    transforms: np.ndarray,
    image_shape_hw: tuple[int, int],
    calib: Calibration,
    voxel_size_mm: float,
    margin_mm: float,
    valid_mask: np.ndarray | None = None,
) -> GridSpec:
    height, width = image_shape_hw
    if valid_mask is not None:
        if valid_mask.shape != (height, width):
            raise ValueError("valid_mask shape must match the ultrasound frame")
        rows, cols = np.nonzero(valid_mask)
        if not rows.size:
            raise ValueError("valid_mask contains no valid pixels")
        row_min, row_max = int(rows.min()), int(rows.max())
        col_min, col_max = int(cols.min()), int(cols.max())
    else:
        row_min, row_max = 0, height - 1
        col_min, col_max = 0, width - 1
    corners = np.asarray(
        [
            [col_min, row_min, 0, 1],
            [col_max, row_min, 0, 1],
            [col_min, row_max, 0, 1],
            [col_max, row_max, 0, 1],
        ],
        dtype=np.float64,
    ).T
    coords = []
    for transform in transforms:
        coords.append(transform_pixels(transform, corners, calib.pixel_to_mm))
    all_coords = np.concatenate(coords, axis=0)
    mins = all_coords.min(axis=0) - margin_mm
    maxs = all_coords.max(axis=0) + margin_mm
    shape_xyz = np.ceil((maxs - mins) / voxel_size_mm).astype(int) + 1
    return GridSpec(
        origin_mm=mins.astype(np.float64),
        voxel_size_mm=float(voxel_size_mm),
        shape_zyx=(int(shape_xyz[2]), int(shape_xyz[1]), int(shape_xyz[0])),
    )


def _frame_indices(
    n_frames: int,
    frame_step: int,
    dropout_fraction: float,
    rng: np.random.Generator,
) -> np.ndarray:
    indices = np.arange(0, n_frames, frame_step, dtype=np.int64)
    if dropout_fraction > 0:
        keep = rng.random(indices.size) >= dropout_fraction
        keep[0] = True
        indices = indices[keep]
    return indices


def _random_rotations(
    n: int, sigma_deg: float, rng: np.random.Generator
) -> np.ndarray:
    if sigma_deg <= 0:
        return np.repeat(np.eye(3)[None, :, :], n, axis=0)
    axes = rng.normal(size=(n, 3))
    axes /= np.linalg.norm(axes, axis=1, keepdims=True)
    angles = rng.normal(scale=math.radians(sigma_deg), size=n)
    mats = np.empty((n, 3, 3), dtype=np.float64)
    for i, (axis, angle) in enumerate(zip(axes, angles, strict=True)):
        x, y, z = axis
        c = math.cos(angle)
        s = math.sin(angle)
        C = 1 - c
        mats[i] = np.array(
            [
                [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
            ]
        )
    return mats


def perturb_calibration(
    calibration: Calibration,
    translation_mm: Iterable[float],
    rotation_deg_xyz: Iterable[float],
) -> Calibration:
    translation = np.asarray(tuple(translation_mm), dtype=np.float64)
    angles = np.radians(np.asarray(tuple(rotation_deg_xyz), dtype=np.float64))
    if translation.shape != (3,) or angles.shape != (3,):
        raise ValueError("Calibration perturbations must contain three values")
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rotation_x = np.asarray([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    rotation_y = np.asarray([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rotation_z = np.asarray([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    perturbed = calibration.tool_from_image.copy()
    perturbed[:3, :3] = rotation_z @ rotation_y @ rotation_x @ perturbed[:3, :3]
    perturbed[:3, 3] += translation
    return Calibration(calibration.pixel_to_mm.copy(), perturbed)


def condition_transforms(
    ref_from_image: np.ndarray,
    *,
    pose_delay_frames: int = 0,
    translation_noise_mm: float = 0.0,
    rotation_noise_deg: float = 0.0,
    seed: int = 13,
) -> np.ndarray:
    out = ref_from_image.copy()
    if pose_delay_frames:
        source = np.maximum(np.arange(len(out)) - pose_delay_frames, 0)
        out = out[source]
    rng = np.random.default_rng(seed)
    if translation_noise_mm:
        out[:, :3, 3] += rng.normal(scale=translation_noise_mm, size=(len(out), 3))
    if rotation_noise_deg:
        noise = _random_rotations(len(out), rotation_noise_deg, rng)
        out[:, :3, :3] = np.einsum("nij,njk->nik", noise, out[:, :3, :3])
    return out


def reconstruct_volume(
    frames_file: Path,
    transforms: np.ndarray,
    calib: Calibration,
    *,
    grid: GridSpec | None = None,
    voxel_size_mm: float = 2.0,
    margin_mm: float = 2.0,
    frame_step: int = 1,
    pixel_stride: int = 8,
    dropout_fraction: float = 0.0,
    seed: int = 13,
    fill_holes_mm: float = 3.0,
    valid_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    with h5py.File(frames_file, "r") as ff:
        frames = ff["frames"]
        n, height, width = frames.shape
        if valid_mask is None:
            valid_mask = np.ones((height, width), dtype=bool)
        elif valid_mask.shape != (height, width):
            raise ValueError("valid_mask shape must match the ultrasound frame")
        indices = _frame_indices(n, frame_step, dropout_fraction, rng)
        if grid is None:
            grid = compute_grid(
                transforms[indices],
                (height, width),
                calib,
                voxel_size_mm,
                margin_mm,
                valid_mask,
            )

        sums = np.zeros(grid.shape_zyx, dtype=np.float32)
        counts = np.zeros(grid.shape_zyx, dtype=np.uint16)
        sampled_mask = valid_mask[::pixel_stride, ::pixel_stride].ravel()
        pix = _pixel_grid(height, width, pixel_stride)[:, sampled_mask]

        for frame_idx in indices:
            coords = transform_pixels(transforms[frame_idx], pix, calib.pixel_to_mm)
            ijk = np.floor((coords - grid.origin_mm) / grid.voxel_size_mm).astype(np.int64)
            valid = (
                (ijk[:, 0] >= 0)
                & (ijk[:, 0] < grid.shape_zyx[2])
                & (ijk[:, 1] >= 0)
                & (ijk[:, 1] < grid.shape_zyx[1])
                & (ijk[:, 2] >= 0)
                & (ijk[:, 2] < grid.shape_zyx[0])
            )
            vox = ijk[valid]
            sampled_frame = np.asarray(
                frames[frame_idx, ::pixel_stride, ::pixel_stride], dtype=np.float32
            )
            values = sampled_frame.ravel()[sampled_mask][valid]
            z, y, x = vox[:, 2], vox[:, 1], vox[:, 0]
            np.add.at(sums, (z, y, x), values)
            np.add.at(counts, (z, y, x), 1)

    volume = np.zeros_like(sums, dtype=np.float32)
    covered = counts > 0
    volume[covered] = sums[covered] / counts[covered]
    filled = volume.copy()
    fill_mask = np.zeros_like(covered)
    filled_voxels = 0
    if fill_holes_mm > 0 and covered.any():
        distances, nearest = ndimage.distance_transform_edt(
            ~covered, return_indices=True, sampling=grid.voxel_size_mm
        )
        fill_mask = (~covered) & (distances <= fill_holes_mm)
        filled[fill_mask] = volume[tuple(axis[fill_mask] for axis in nearest)]
        filled_voxels = int(np.count_nonzero(fill_mask))

    return {
        "volume": filled,
        "raw_volume": volume,
        "counts": counts,
        "raw_mask": covered,
        "filled_mask": covered | fill_mask,
        "grid": grid,
        "frames_processed": int(len(indices)),
        "pixels_per_frame": int(pix.shape[1]),
        "covered_voxels": int(np.count_nonzero(covered)),
        "filled_voxels": filled_voxels,
        "coverage_fraction": float(np.count_nonzero(covered) / counts.size),
        "hole_fraction": float(1.0 - np.count_nonzero(covered) / counts.size),
        "valid_pixel_fraction": float(np.mean(valid_mask)),
    }


def write_nifti_gz(path: Path, volume_zyx: np.ndarray, grid: GridSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(volume_zyx, 0, 255).astype(np.uint8).transpose(2, 1, 0)
    affine = np.eye(4, dtype=np.float64)
    affine[:3, :3] *= grid.voxel_size_mm
    affine[:3, 3] = grid.origin_mm
    image = nib.Nifti1Image(data, affine)
    image.header.set_xyzt_units("mm")
    image.set_qform(affine, code=1)
    image.set_sform(affine, code=1)
    nib.save(image, path)


def _masked_ssim(
    reference: np.ndarray,
    candidate: np.ndarray,
    mask: np.ndarray,
    data_range: float,
) -> float:
    if not np.any(mask) or min(reference.shape) < 7:
        return float("nan")
    _, ssim_map = structural_similarity(
        reference,
        candidate,
        data_range=data_range,
        full=True,
    )
    return float(np.mean(ssim_map[mask]))


def _comparison_metrics(
    reference: np.ndarray,
    candidate: np.ndarray,
    reference_mask: np.ndarray,
    candidate_mask: np.ndarray,
) -> dict[str, float | int]:
    intersection = reference_mask & candidate_mask
    union = reference_mask | candidate_mask
    reference_count = int(np.count_nonzero(reference_mask))
    candidate_count = int(np.count_nonzero(candidate_mask))
    intersection_count = int(np.count_nonzero(intersection))
    union_count = int(np.count_nonzero(union))
    candidate_only_count = int(np.count_nonzero(candidate_mask & ~reference_mask))
    ref_values = reference[reference_mask]
    data_range = max(float(np.ptp(ref_values)) if ref_values.size else 0.0, 1.0)

    def nrmse(mask: np.ndarray) -> float:
        if not np.any(mask):
            return float("nan")
        error = reference[mask].astype(np.float64) - candidate[mask].astype(np.float64)
        return float(np.sqrt(np.mean(error**2)) / data_range)

    denominator = reference_count + candidate_count
    return {
        "occupied_voxels_reference": reference_count,
        "occupied_voxels_candidate": candidate_count,
        "occupied_voxels_intersection": intersection_count,
        "occupied_voxels_union": union_count,
        "nrmse_union": nrmse(union),
        "nrmse_intersection": nrmse(intersection),
        "occupied_volume_dice": (
            float(2 * intersection_count / denominator) if denominator else 1.0
        ),
        "reference_coverage_retained": (
            float(intersection_count / reference_count) if reference_count else 1.0
        ),
        "false_additional_coverage": (
            float(candidate_only_count / reference_count) if reference_count else 0.0
        ),
        "false_additional_voxels": candidate_only_count,
        "masked_ssim": _masked_ssim(reference, candidate, union, data_range),
    }


def compare_volumes(
    reference: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, float | int]:
    metrics: dict[str, float | int] = {}
    for prefix, volume_key, mask_key in (
        ("raw", "raw_volume", "raw_mask"),
        ("filled", "volume", "filled_mask"),
    ):
        values = _comparison_metrics(
            reference[volume_key],
            candidate[volume_key],
            reference[mask_key],
            candidate[mask_key],
        )
        metrics.update({f"{prefix}_{key}": value for key, value in values.items()})
    return metrics


def transform_point_error_mm(
    reference: np.ndarray,
    candidate: np.ndarray,
    image_shape_hw: tuple[int, int],
    calib: Calibration,
    pixel_stride: int = 80,
) -> dict[str, float]:
    pts = _pixel_grid(image_shape_hw[0], image_shape_hw[1], pixel_stride)
    global_errors = []
    for ref_t, cand_t in zip(reference, candidate, strict=True):
        ref_pts = transform_pixels(ref_t, pts, calib.pixel_to_mm)
        cand_pts = transform_pixels(cand_t, pts, calib.pixel_to_mm)
        global_errors.append(np.linalg.norm(ref_pts - cand_pts, axis=1))
    local_errors = []
    for index in range(1, len(reference)):
        ref_local = np.linalg.inv(reference[index - 1]) @ reference[index]
        candidate_local = np.linalg.inv(candidate[index - 1]) @ candidate[index]
        ref_pts = transform_pixels(ref_local, pts, calib.pixel_to_mm)
        candidate_pts = transform_pixels(candidate_local, pts, calib.pixel_to_mm)
        local_errors.append(np.linalg.norm(ref_pts - candidate_pts, axis=1))
    global_error = np.concatenate(global_errors)
    local_error = np.concatenate(local_errors) if local_errors else np.asarray([0.0])
    return {
        "transform_point_error_global_mm": float(np.mean(global_error)),
        "transform_point_error_global_mm_p95": float(np.percentile(global_error, 95)),
        "transform_point_error_global_mm_max": float(np.max(global_error)),
        "transform_point_error_local_mm": float(np.mean(local_error)),
        "transform_point_error_local_mm_p95": float(np.percentile(local_error, 95)),
        "transform_point_error_local_mm_max": float(np.max(local_error)),
    }


def trajectory_error(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    trans = np.linalg.norm(reference[:, :3, 3] - candidate[:, :3, 3], axis=1)
    rel = np.einsum(
        "nij,njk->nik",
        np.swapaxes(reference[:, :3, :3], 1, 2),
        candidate[:, :3, :3],
    )
    traces = np.trace(rel, axis1=1, axis2=2)
    rot = np.degrees(np.arccos(np.clip((traces - 1) * 0.5, -1.0, 1.0)))
    return {
        "translation_error_mm_mean": float(np.mean(trans)),
        "translation_error_mm_max": float(np.max(trans)),
        "rotation_error_deg_mean": float(np.mean(rot)),
        "rotation_error_deg_max": float(np.max(rot)),
        "final_position_error_mm": float(trans[-1]),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
