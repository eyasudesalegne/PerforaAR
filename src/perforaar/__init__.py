"""Quantitative core for the PerforaAR research prototype."""

from .fusion import fuse_detections
from .geometry import (
    image_to_leg_transform,
    invert_rigid_transform,
    linear_probe_pixels_to_points,
    project_points,
    rigid_transform_svd,
    transform_points,
)
from .ranking import rank_candidates

__all__ = [
    "fuse_detections",
    "image_to_leg_transform",
    "invert_rigid_transform",
    "linear_probe_pixels_to_points",
    "project_points",
    "rank_candidates",
    "rigid_transform_svd",
    "transform_points",
]
__version__ = "0.1.0"
