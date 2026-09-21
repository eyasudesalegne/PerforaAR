import numpy as np

from perforaar.geometry import (
    image_to_leg_transform,
    invert_rigid_transform,
    linear_probe_pixels_to_points,
    project_points,
    rigid_transform_svd,
    transform_points,
)


def test_rigid_registration_recovers_transform():
    source = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [0, 0, 10]], dtype=float)
    expected = np.eye(4)
    expected[:3, 3] = [4, -2, 7]
    target = transform_points(source, expected)
    estimated = rigid_transform_svd(source, target)
    assert np.allclose(transform_points(source, estimated), target, atol=1e-8)


def test_projection_marks_points_behind_camera_invalid():
    points = np.array([[0, 0, 10], [1, 1, -1]], dtype=float)
    intrinsics = np.array([[100, 0, 50], [0, 100, 40], [0, 0, 1]], dtype=float)
    pixels, valid = project_points(points, intrinsics)
    assert valid.tolist() == [True, False]
    assert np.allclose(pixels[0], [50, 40])
    assert np.isnan(pixels[1]).all()


def test_linear_probe_pixel_calibration_returns_lateral_and_depth_mm():
    pixels = np.array([[10, 20], [14, 30]], dtype=float)
    points = linear_probe_pixels_to_points(
        pixels,
        pixel_spacing_mm=(0.5, 0.25),
        image_origin_px=(10, 20),
    )
    assert np.allclose(points, [[0, 0, 0], [2, 0, 2.5]])


def test_image_to_leg_chain_uses_probe_and_leg_markers():
    tracker_from_probe = np.eye(4)
    tracker_from_probe[:3, 3] = [10, 0, 0]
    tracker_from_leg = np.eye(4)
    tracker_from_leg[:3, 3] = [3, 0, 0]
    probe_from_image = np.eye(4)
    probe_from_image[:3, 3] = [0, 0, 2]

    leg_from_image = image_to_leg_transform(
        tracker_from_probe,
        tracker_from_leg,
        probe_from_image,
    )
    point_leg = transform_points(np.array([[1, 0, 4]]), leg_from_image)
    assert np.allclose(point_leg, [[8, 0, 6]])


def test_common_tracker_translation_does_not_change_relative_geometry():
    tracker_from_probe = np.eye(4)
    tracker_from_probe[:3, 3] = [10, 2, 1]
    tracker_from_leg = np.eye(4)
    tracker_from_leg[:3, 3] = [3, 1, 1]
    common_motion = np.eye(4)
    common_motion[:3, 3] = [50, -20, 4]

    before = image_to_leg_transform(tracker_from_probe, tracker_from_leg, np.eye(4))
    after = image_to_leg_transform(
        common_motion @ tracker_from_probe,
        common_motion @ tracker_from_leg,
        np.eye(4),
    )
    assert np.allclose(after, before)


def test_invert_rigid_transform_rejects_scale():
    scaled = np.diag([2.0, 1.0, 1.0, 1.0])
    with np.testing.assert_raises_regex(ValueError, "orthonormal"):
        invert_rigid_transform(scaled)
