"""Utilities for interactive inspection and AR export of reconstructed volumes."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from scipy import ndimage
from skimage import measure


@dataclass(frozen=True)
class ReconstructionVolume:
    """A three-dimensional reconstruction in physical millimetre coordinates."""

    path: Path
    data: np.ndarray
    affine: np.ndarray
    spatial_unit: str

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(int(value) for value in self.data.shape)

    @property
    def voxel_spacing_mm(self) -> tuple[float, float, float]:
        return tuple(float(np.linalg.norm(self.affine[:3, axis])) for axis in range(3))

    @property
    def physical_extent_mm(self) -> tuple[float, float, float]:
        return tuple(
            float((size - 1) * spacing)
            for size, spacing in zip(self.shape, self.voxel_spacing_mm, strict=True)
        )

    @property
    def nonzero_fraction(self) -> float:
        return float(np.count_nonzero(self.data) / self.data.size)


def discover_reconstruction_volumes(root: Path) -> list[Path]:
    """Return committed TUS-REC2024 NIfTI reconstructions in stable order."""
    return sorted((root / "results" / "tus_rec2024" / "volumes").glob("*.nii.gz"))


def load_reconstruction_volume(path: Path) -> ReconstructionVolume:
    """Load and validate a finite 3D NIfTI reconstruction."""
    image = nib.load(path)
    data = np.asarray(image.dataobj, dtype=np.float32)
    if data.ndim != 3:
        raise ValueError(f"Expected a 3D NIfTI volume, received shape {data.shape}")
    if not np.isfinite(data).all():
        raise ValueError(f"Volume contains non-finite values: {path}")
    unit = image.header.get_xyzt_units()[0]
    return ReconstructionVolume(
        path=path,
        data=data,
        affine=np.asarray(image.affine, dtype=np.float64),
        spatial_unit=str(unit),
    )


def positive_intensity_percentile(volume: ReconstructionVolume, percentile: float) -> float:
    """Calculate a display threshold without allowing zero background to dominate."""
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be in [0, 100]")
    positive = volume.data[volume.data > 0]
    if not positive.size:
        raise ValueError("Volume contains no positive voxels")
    return float(np.percentile(positive, percentile))


def crop_slices(
    shape: tuple[int, int, int],
    ranges_percent: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
) -> tuple[slice, slice, slice]:
    """Convert inclusive percentage controls into non-empty array slices."""
    slices = []
    for size, (lower, upper) in zip(shape, ranges_percent, strict=True):
        if not 0 <= lower < upper <= 100:
            raise ValueError("Crop ranges must satisfy 0 <= lower < upper <= 100")
        start = int(math.floor(size * lower / 100))
        stop = int(math.ceil(size * upper / 100))
        slices.append(slice(min(start, size - 1), max(start + 1, min(stop, size))))
    return tuple(slices)  # type: ignore[return-value]


def _sampling_stride(shape: tuple[int, int, int], max_points: int) -> int:
    if max_points <= 0:
        raise ValueError("max_points must be positive")
    stride = 1
    while math.prod(math.ceil(size / stride) for size in shape) > max_points:
        stride += 1
    return stride


def sample_volume_grid(
    volume: ReconstructionVolume,
    ranges_percent: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    max_points: int,
) -> dict[str, Any]:
    """Downsample a cropped volume and map every sample into physical coordinates."""
    slices = crop_slices(volume.shape, ranges_percent)
    cropped = volume.data[slices]
    stride = _sampling_stride(tuple(int(value) for value in cropped.shape), max_points)
    sampled = cropped[::stride, ::stride, ::stride]

    axes = [
        np.arange(axis_slice.start, axis_slice.stop, stride, dtype=np.float64)
        for axis_slice in slices
    ]
    ii, jj, kk = np.meshgrid(*axes, indexing="ij")
    voxel_coordinates = np.column_stack([ii.ravel(), jj.ravel(), kk.ravel()])
    homogeneous = np.column_stack(
        [voxel_coordinates, np.ones(len(voxel_coordinates), dtype=np.float64)]
    )
    physical = (volume.affine @ homogeneous.T).T[:, :3]
    return {
        "x": physical[:, 0],
        "y": physical[:, 1],
        "z": physical[:, 2],
        "value": sampled.ravel(),
        "shape": tuple(int(value) for value in sampled.shape),
        "stride": stride,
    }


def orthogonal_slices(
    volume: ReconstructionVolume,
    indices_xyz: tuple[int, int, int],
) -> dict[str, np.ndarray]:
    """Return axial, coronal and sagittal images for multiplanar review."""
    x, y, z = indices_xyz
    if not (0 <= x < volume.shape[0] and 0 <= y < volume.shape[1] and 0 <= z < volume.shape[2]):
        raise IndexError("Slice index is outside the volume")
    return {
        "sagittal": np.rot90(volume.data[x, :, :]),
        "coronal": np.rot90(volume.data[:, y, :]),
        "axial": np.rot90(volume.data[:, :, z]),
    }


def extract_surface_mesh(
    volume: ReconstructionVolume,
    threshold: float,
    *,
    smoothing_sigma: float = 1.0,
    step_size: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract a physical-coordinate isosurface suitable for GLB export."""
    if step_size < 1:
        raise ValueError("step_size must be at least 1")
    data = volume.data
    if smoothing_sigma > 0:
        data = ndimage.gaussian_filter(data, sigma=smoothing_sigma)
    data_min = float(np.min(data))
    data_max = float(np.max(data))
    if not data_min < threshold < data_max:
        raise ValueError(
            f"Surface threshold must be strictly between {data_min:.3f} and {data_max:.3f}"
        )
    vertices, faces, _, _ = measure.marching_cubes(
        data,
        level=float(threshold),
        step_size=step_size,
        allow_degenerate=False,
    )
    homogeneous = np.column_stack([vertices, np.ones(len(vertices), dtype=np.float64)])
    physical_vertices = (volume.affine @ homogeneous.T).T[:, :3]
    return physical_vertices.astype(np.float32), faces.astype(np.int32)


def export_surface_glb(
    vertices_mm: np.ndarray,
    faces: np.ndarray,
    rgba: tuple[int, int, int, int] = (75, 191, 190, 210),
) -> bytes:
    """Encode a physical-scale surface as a binary glTF asset."""
    import trimesh

    mesh = trimesh.Trimesh(vertices=vertices_mm, faces=faces, process=False)
    mesh.visual.face_colors = np.tile(np.asarray(rgba, dtype=np.uint8), (len(faces), 1))
    payload = mesh.export(file_type="glb")
    if not isinstance(payload, bytes):
        raise TypeError("GLB exporter did not return bytes")
    return payload


def scene_metadata(
    volume: ReconstructionVolume,
    *,
    threshold: float,
    mesh_vertex_count: int | None = None,
    mesh_face_count: int | None = None,
) -> dict[str, Any]:
    """Describe the coordinate contract required by an AR client."""
    return {
        "schema": "perforaar.ar-scene.v1",
        "source_volume": volume.path.name,
        "spatial_unit": volume.spatial_unit,
        "coordinate_convention": "NIfTI physical coordinates; right-handed x/y/z in millimetres",
        "voxel_shape_xyz": list(volume.shape),
        "voxel_spacing_mm": list(volume.voxel_spacing_mm),
        "physical_extent_mm": list(volume.physical_extent_mm),
        "voxel_to_physical_affine": volume.affine.tolist(),
        "surface_threshold": float(threshold),
        "mesh_vertex_count": mesh_vertex_count,
        "mesh_face_count": mesh_face_count,
        "registration_required": True,
        "registration_target": "participant-specific leg reference frame",
        "clinical_status": "research prototype; not validated for patient guidance",
    }


def scene_metadata_json(metadata: dict[str, Any]) -> bytes:
    return (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
