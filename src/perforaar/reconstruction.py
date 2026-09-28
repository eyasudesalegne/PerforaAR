"""Tracked 2D Doppler frame compounding on a regular 3D grid.

The module uses the project-wide ``T_destination_from_source`` convention.  A
tracked frame stores ``T_leg_from_image`` and its pixels lie in the image-frame
``(lateral, elevational, depth)`` plane, where elevational is zero.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from .geometry import transform_points


def _triple(values: tuple[float, float, float], name: str) -> tuple[float, float, float]:
    array = np.asarray(values, dtype=float)
    if array.shape != (3,) or not np.isfinite(array).all():
        raise ValueError(f"{name} must contain three finite values")
    return tuple(float(value) for value in array)


@dataclass(frozen=True)
class VolumeGrid:
    """Regular reconstruction grid expressed in the leg-reference frame."""

    shape: tuple[int, int, int]
    spacing_mm: tuple[float, float, float]
    origin_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if len(self.shape) != 3 or any(
            not isinstance(value, (int, np.integer)) or value < 1 for value in self.shape
        ):
            raise ValueError("shape must contain three positive integers")
        spacing = _triple(self.spacing_mm, "spacing_mm")
        if any(value <= 0 for value in spacing):
            raise ValueError("spacing_mm values must be positive")
        _triple(self.origin_mm, "origin_mm")


@dataclass(frozen=True)
class TrackedDopplerFrame:
    """One power/velocity image pair and its pose in the leg frame."""

    power_db: np.ndarray
    velocity_m_s: np.ndarray
    leg_from_image: np.ndarray

    def __post_init__(self) -> None:
        power = np.asarray(self.power_db)
        velocity = np.asarray(self.velocity_m_s)
        if power.ndim != 2 or velocity.shape != power.shape:
            raise ValueError("power_db and velocity_m_s must be matching 2D arrays")
        if not np.isfinite(power).all() or not np.isfinite(velocity).all():
            raise ValueError("Doppler frames must contain only finite values")
        transform = np.asarray(self.leg_from_image, dtype=float)
        if transform.shape != (4, 4) or not np.isfinite(transform).all():
            raise ValueError("leg_from_image must be a finite 4x4 transform")
        if not np.allclose(transform[3], [0.0, 0.0, 0.0, 1.0]):
            raise ValueError("leg_from_image must have a homogeneous final row")
        rotation = transform[:3, :3]
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6):
            raise ValueError("leg_from_image rotation must be orthonormal")
        if not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-6):
            raise ValueError("leg_from_image rotation must have determinant +1")


@dataclass(frozen=True)
class CompoundedVolume:
    """Mean-compounded channels and the number of samples in each voxel."""

    power_db: np.ndarray
    velocity_m_s: np.ndarray
    sample_count: np.ndarray

    @property
    def observed(self) -> np.ndarray:
        return self.sample_count > 0


def parallel_sweep_indices(length: int, step: int) -> np.ndarray:
    """Return regularly spaced plane indices while always including both endpoints."""
    if length < 1 or step < 1:
        raise ValueError("length and step must be positive")
    indices = np.arange(0, length, step, dtype=int)
    if indices[-1] != length - 1:
        indices = np.append(indices, length - 1)
    return indices


def drop_internal_frames(indices: np.ndarray, fraction: float, *, seed: int) -> np.ndarray:
    """Drop a deterministic fraction of internal frames, preserving sweep endpoints."""
    planes = np.asarray(indices, dtype=int)
    if planes.ndim != 1 or planes.size < 2 or np.any(np.diff(planes) <= 0):
        raise ValueError("indices must be a strictly increasing 1D array")
    if not 0 <= fraction < 1:
        raise ValueError("fraction must be in [0, 1)")
    internal = planes[1:-1]
    drop_count = int(np.floor(internal.size * fraction))
    if drop_count == 0:
        return planes.copy()
    rng = np.random.default_rng(seed)
    dropped = rng.choice(internal, size=drop_count, replace=False)
    return planes[~np.isin(planes, dropped)]


def virtual_parallel_sweep(
    power_db: np.ndarray,
    velocity_m_s: np.ndarray,
    grid: VolumeGrid,
    plane_indices: Iterable[int],
) -> Iterable[TrackedDopplerFrame]:
    """Yield tracked x-z frames sampled along the grid's y axis.

    This is a simulation adapter for reconstructed public volumes.  It produces
    virtual 2D acquisitions with known poses; it does not claim that the source
    dataset contains original tracked frames.
    """
    power = np.asarray(power_db)
    velocity = np.asarray(velocity_m_s)
    if power.shape != grid.shape or velocity.shape != grid.shape:
        raise ValueError("source volumes must match grid.shape")
    if not np.isfinite(power).all() or not np.isfinite(velocity).all():
        raise ValueError("source volumes must contain only finite values")

    spacing = np.asarray(grid.spacing_mm, dtype=float)
    origin = np.asarray(grid.origin_mm, dtype=float)
    for plane_index in plane_indices:
        index = int(plane_index)
        if index < 0 or index >= grid.shape[1]:
            raise ValueError("plane index is outside the grid")
        transform = np.eye(4)
        transform[:3, 3] = origin + np.array([0.0, index * spacing[1], 0.0])
        yield TrackedDopplerFrame(
            power_db=power[:, index, :],
            velocity_m_s=velocity[:, index, :],
            leg_from_image=transform,
        )


def compound_tracked_frames(
    frames: Iterable[TrackedDopplerFrame], grid: VolumeGrid
) -> CompoundedVolume:
    """Nearest-voxel compound tracked Doppler frames into ``grid``."""
    shape = tuple(int(value) for value in grid.shape)
    spacing = np.asarray(grid.spacing_mm, dtype=float)
    origin = np.asarray(grid.origin_mm, dtype=float)
    power_sum = np.zeros(shape, dtype=np.float64)
    velocity_sum = np.zeros(shape, dtype=np.float64)
    sample_count = np.zeros(shape, dtype=np.uint32)
    coordinate_cache: dict[tuple[int, int], np.ndarray] = {}
    frame_count = 0

    for frame in frames:
        frame_count += 1
        power = np.asarray(frame.power_db, dtype=float)
        velocity = np.asarray(frame.velocity_m_s, dtype=float)
        if power.shape not in coordinate_cache:
            lateral, depth = np.indices(power.shape, dtype=float)
            coordinate_cache[power.shape] = np.column_stack(
                (
                    lateral.ravel() * spacing[0],
                    np.zeros(power.size),
                    depth.ravel() * spacing[2],
                )
            )
        points_leg = transform_points(coordinate_cache[power.shape], frame.leg_from_image)
        voxels = np.rint((points_leg - origin) / spacing).astype(np.int64)
        valid = np.all((voxels >= 0) & (voxels < np.asarray(shape)), axis=1)
        flat_indices = np.ravel_multi_index(voxels[valid].T, shape)
        np.add.at(power_sum.ravel(), flat_indices, power.ravel()[valid])
        np.add.at(velocity_sum.ravel(), flat_indices, velocity.ravel()[valid])
        np.add.at(sample_count.ravel(), flat_indices, 1)

    if frame_count == 0:
        raise ValueError("at least one frame is required")
    observed = sample_count > 0
    compounded_power = np.zeros(shape, dtype=np.float32)
    compounded_velocity = np.zeros(shape, dtype=np.float32)
    compounded_power[observed] = (power_sum[observed] / sample_count[observed]).astype(np.float32)
    compounded_velocity[observed] = (velocity_sum[observed] / sample_count[observed]).astype(
        np.float32
    )
    return CompoundedVolume(compounded_power, compounded_velocity, sample_count)


def interpolate_parallel_sweep(
    volume: np.ndarray, observed_plane_indices: np.ndarray
) -> np.ndarray:
    """Linearly interpolate unobserved y planes between tracked sweep frames."""
    array = np.asarray(volume)
    if array.ndim != 3:
        raise ValueError("volume must be three-dimensional")
    indices = np.asarray(observed_plane_indices, dtype=int)
    if (
        indices.ndim != 1
        or indices.size < 2
        or indices[0] != 0
        or indices[-1] != array.shape[1] - 1
        or np.any(np.diff(indices) <= 0)
    ):
        raise ValueError("observed planes must be increasing and include both endpoints")

    output = np.asarray(array, dtype=np.float32).copy()
    for left, right in zip(indices[:-1], indices[1:], strict=True):
        distance = right - left
        if distance == 1:
            continue
        alpha = np.arange(1, distance, dtype=np.float32) / distance
        output[:, left + 1 : right, :] = (
            output[:, left : left + 1, :] * (1.0 - alpha[None, :, None])
            + output[:, right : right + 1, :] * alpha[None, :, None]
        )
    return output
