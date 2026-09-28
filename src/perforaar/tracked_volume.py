from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import h5py
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
        if any(part in {".git", "results", "src", "scripts", "tests", "docs", "configs", "data"} for part in path.parts):
            continue
        item: dict[str, Any] = {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
        }
        if hash_contents:
            item.update(hash_file(path))
        files.append(item)
    return {
        "dataset": "Trackerless 3D Freehand Ultrasound Reconstruction Challenge 2024 - Train Dataset (Part 1)",
        "source": "https://zenodo.org/records/11178509",
        "doi": "10.5281/zenodo.11178509",
        "version": "1.0.0",
        "source_archive": {
            "name": "train_part1.zip",
            "bytes": 43_400_000_000,
            "md5": "7226991c6b04ef85e3cfb6f4e0ea7ad2",
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
) -> GridSpec:
    height, width = image_shape_hw
    corners = np.asarray(
        [
            [0, 0, 0, 1],
            [width - 1, 0, 0, 1],
            [0, height - 1, 0, 1],
            [width - 1, height - 1, 0, 1],
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
    for i, (axis, angle) in enumerate(zip(axes, angles)):
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
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    with h5py.File(frames_file, "r") as ff:
        frames = ff["frames"]
        n, height, width = frames.shape
        indices = _frame_indices(n, frame_step, dropout_fraction, rng)
        if grid is None:
            grid = compute_grid(transforms[indices], (height, width), calib, voxel_size_mm, margin_mm)

        sums = np.zeros(grid.shape_zyx, dtype=np.float32)
        counts = np.zeros(grid.shape_zyx, dtype=np.uint16)
        pix = _pixel_grid(height, width, pixel_stride)

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
            values = np.asarray(frames[frame_idx, ::pixel_stride, ::pixel_stride], dtype=np.float32).ravel()[valid]
            z, y, x = vox[:, 2], vox[:, 1], vox[:, 0]
            np.add.at(sums, (z, y, x), values)
            np.add.at(counts, (z, y, x), 1)

    volume = np.zeros_like(sums, dtype=np.float32)
    covered = counts > 0
    volume[covered] = sums[covered] / counts[covered]
    filled = volume.copy()
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
        "grid": grid,
        "frames_processed": int(len(indices)),
        "pixels_per_frame": int(pix.shape[1]),
        "covered_voxels": int(np.count_nonzero(covered)),
        "filled_voxels": filled_voxels,
        "coverage_fraction": float(np.count_nonzero(covered) / counts.size),
        "hole_fraction": float(1.0 - np.count_nonzero(covered) / counts.size),
    }


def write_nifti_gz(path: Path, volume_zyx: np.ndarray, grid: GridSpec) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(volume_zyx, 0, 255).astype(np.uint8).transpose(2, 1, 0)
    nx, ny, nz = data.shape
    header = bytearray(348)
    struct.pack_into("<i", header, 0, 348)
    struct.pack_into("<8h", header, 40, 3, nx, ny, nz, 1, 1, 1, 1)
    struct.pack_into("<h", header, 70, 2)
    struct.pack_into("<h", header, 72, 8)
    struct.pack_into("<8f", header, 76, 0.0, grid.voxel_size_mm, grid.voxel_size_mm, grid.voxel_size_mm, 1, 1, 1, 1)
    struct.pack_into("<f", header, 108, 352.0)
    struct.pack_into("<h", header, 252, 1)
    struct.pack_into("<h", header, 254, 1)
    struct.pack_into("<4f", header, 280, grid.voxel_size_mm, 0, 0, float(grid.origin_mm[0]))
    struct.pack_into("<4f", header, 296, 0, grid.voxel_size_mm, 0, float(grid.origin_mm[1]))
    struct.pack_into("<4f", header, 312, 0, 0, grid.voxel_size_mm, float(grid.origin_mm[2]))
    header[344:348] = b"n+1\0"
    with gzip.open(path, "wb") as fh:
        fh.write(header)
        fh.write(b"\0\0\0\0")
        fh.write(np.ascontiguousarray(data).tobytes(order="C"))


def compare_volumes(
    reference: np.ndarray,
    candidate: np.ndarray,
    ref_counts: np.ndarray,
    cand_counts: np.ndarray,
) -> dict[str, float]:
    overlap = (ref_counts > 0) & (cand_counts > 0)
    if not np.any(overlap):
        return {"overlap_voxels": 0, "nrmse": float("nan"), "ssim_mean": float("nan")}
    ref = reference[overlap].astype(np.float64)
    cand = candidate[overlap].astype(np.float64)
    data_range = max(float(reference.max() - reference.min()), 1.0)
    nrmse = float(np.sqrt(np.mean((ref - cand) ** 2)) / data_range)

    ssims: list[float] = []
    for axis in range(3):
        idx = reference.shape[axis] // 2
        ref_slice = np.take(reference, idx, axis=axis)
        cand_slice = np.take(candidate, idx, axis=axis)
        if min(ref_slice.shape) >= 7:
            ssims.append(float(structural_similarity(ref_slice, cand_slice, data_range=data_range)))
    return {
        "overlap_voxels": int(np.count_nonzero(overlap)),
        "nrmse": nrmse,
        "ssim_mean": float(np.mean(ssims)) if ssims else float("nan"),
    }


def pose_point_error_mm(
    reference: np.ndarray,
    candidate: np.ndarray,
    image_shape_hw: tuple[int, int],
    calib: Calibration,
    pixel_stride: int = 80,
) -> dict[str, float]:
    pts = _pixel_grid(image_shape_hw[0], image_shape_hw[1], pixel_stride)
    errors = []
    for ref_t, cand_t in zip(reference, candidate):
        ref_pts = transform_pixels(ref_t, pts, calib.pixel_to_mm)
        cand_pts = transform_pixels(cand_t, pts, calib.pixel_to_mm)
        errors.append(np.linalg.norm(ref_pts - cand_pts, axis=1))
    err = np.concatenate(errors)
    local = np.asarray([np.mean(e) for e in errors], dtype=np.float64)
    return {
        "global_pixel_reconstruction_error_mm_mean": float(np.mean(err)),
        "global_pixel_reconstruction_error_mm_p95": float(np.percentile(err, 95)),
        "local_pixel_reconstruction_error_mm_mean": float(np.mean(local)),
        "local_pixel_reconstruction_error_mm_max": float(np.max(local)),
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
        "final_accumulated_drift_mm": float(trans[-1]),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
