import numpy as np

from perforaar.geometry import project_points, rigid_transform_svd, transform_points


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
