"""Quantitative core for the PerforaAR research prototype."""

from .fusion import fuse_detections
from .geometry import project_points, rigid_transform_svd, transform_points
from .ranking import rank_candidates

__all__ = [
    "fuse_detections",
    "project_points",
    "rank_candidates",
    "rigid_transform_svd",
    "transform_points",
]
__version__ = "0.1.0"
