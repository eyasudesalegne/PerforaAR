"""Coordinate transforms, landmark registration, and camera projection."""

from __future__ import annotations

import numpy as np


def _as_points(points: np.ndarray) -> np.ndarray:
    array = np.asarray(points, dtype=float)
    if array.ndim != 2 or array.shape[1] != 3 or not np.isfinite(array).all():
        raise ValueError("points must be a finite Nx3 array")
    return array


def transform_points(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    """Apply a 4x4 homogeneous transform to Nx3 points."""
    array = _as_points(points)
    matrix = np.asarray(transform, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("transform must be a finite 4x4 matrix")
    if not np.allclose(matrix[3], [0, 0, 0, 1]):
        raise ValueError("transform must have homogeneous final row [0, 0, 0, 1]")
    homogeneous = np.c_[array, np.ones(len(array))]
    return (matrix @ homogeneous.T).T[:, :3]


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
