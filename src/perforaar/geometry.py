"""Coordinate transforms, landmark registration, and camera projection."""

from __future__ import annotations

import numpy as np


def _as_points(points: np.ndarray) -> np.ndarray:
    array = np.asarray(points, dtype=float)
    if array.ndim != 2 or array.shape[1] != 3 or not np.isfinite(array).all():
        raise ValueError("points must be a finite Nx3 array")
    return array


def _as_transform(transform: np.ndarray) -> np.ndarray:
    matrix = np.asarray(transform, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("transform must be a finite 4x4 matrix")
    if not np.allclose(matrix[3], [0, 0, 0, 1]):
        raise ValueError("transform must have homogeneous final row [0, 0, 0, 1]")
    return matrix


def _as_rigid_transform(transform: np.ndarray, *, atol: float = 1e-6) -> np.ndarray:
    matrix = _as_transform(transform)
    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=atol):
        raise ValueError("transform rotation must be orthonormal")
    if not np.isclose(np.linalg.det(rotation), 1.0, atol=atol):
        raise ValueError("transform rotation must have determinant +1")
    return matrix


def transform_points(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    """Apply a 4x4 homogeneous transform to Nx3 points."""
    array = _as_points(points)
    matrix = _as_transform(transform)
    homogeneous = np.c_[array, np.ones(len(array))]
    return (matrix @ homogeneous.T).T[:, :3]


def invert_rigid_transform(transform: np.ndarray, *, atol: float = 1e-6) -> np.ndarray:
    """Invert a rigid 4x4 transform after validating its rotation matrix."""
    matrix = _as_rigid_transform(transform, atol=atol)
    rotation = matrix[:3, :3]
    inverse = np.eye(4)
    inverse[:3, :3] = rotation.T
    inverse[:3, 3] = -(rotation.T @ matrix[:3, 3])
    return inverse


def linear_probe_pixels_to_points(
    pixels: np.ndarray,
    pixel_spacing_mm: tuple[float, float],
    image_origin_px: tuple[float, float] = (0.0, 0.0),
) -> np.ndarray:
    """Map ``(u, v)`` pixels to lateral/depth points in a linear-probe image frame.

    The returned axes are ``(lateral, elevational, depth)`` in millimetres. The
    elevational coordinate is zero because a single 2D frame does not measure it.
    """
    array = np.asarray(pixels, dtype=float)
    if array.ndim != 2 or array.shape[1] != 2 or not np.isfinite(array).all():
        raise ValueError("pixels must be a finite Nx2 array")
    spacing = np.asarray(pixel_spacing_mm, dtype=float)
    origin = np.asarray(image_origin_px, dtype=float)
    if spacing.shape != (2,) or not np.isfinite(spacing).all() or np.any(spacing <= 0):
        raise ValueError("pixel_spacing_mm must contain two positive finite values")
    if origin.shape != (2,) or not np.isfinite(origin).all():
        raise ValueError("image_origin_px must contain two finite values")
    lateral_depth = (array - origin) * spacing
    return np.column_stack((lateral_depth[:, 0], np.zeros(len(lateral_depth)), lateral_depth[:, 1]))


def image_to_leg_transform(
    tracker_from_probe: np.ndarray,
    tracker_from_leg: np.ndarray,
    probe_from_image: np.ndarray,
) -> np.ndarray:
    """Build ``T_leg_from_image`` for one synchronized ultrasound frame.

    The optical tracker observes both a rigid probe marker and a rigid leg-reference
    marker. Using the ``T_destination_from_source`` convention, the transform is::

        inv(T_tracker_from_leg) @ T_tracker_from_probe @ T_probe_from_image
    """
    return (
        invert_rigid_transform(tracker_from_leg)
        @ _as_rigid_transform(tracker_from_probe)
        @ _as_rigid_transform(probe_from_image)
    )


def rigid_transform_svd(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Estimate the least-squares rigid transform from paired 3D landmarks."""
    source_points, target_points = _as_points(source), _as_points(target)
    if source_points.shape != target_points.shape or len(source_points) < 3:
        raise ValueError("source and target need matching shapes and at least three landmarks")
    source_center = source_points.mean(axis=0)
    target_center = target_points.mean(axis=0)
    covariance = (source_points - source_center).T @ (target_points - target_center)
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1] *= -1
        rotation = vt.T @ u.T
    translation = target_center - rotation @ source_center
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation
    return transform


def project_points(
    points_camera: np.ndarray, intrinsics: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Project camera-frame 3D points, returning pixels and a positive-depth mask."""
    points = _as_points(points_camera)
    camera = np.asarray(intrinsics, dtype=float)
    if camera.shape != (3, 3) or not np.isfinite(camera).all():
        raise ValueError("intrinsics must be a finite 3x3 matrix")
    valid = points[:, 2] > 0
    pixels = np.full((len(points), 2), np.nan, dtype=float)
    projected = (camera @ points[valid].T).T
    pixels[valid] = projected[:, :2] / projected[:, 2, None]
    return pixels, valid
