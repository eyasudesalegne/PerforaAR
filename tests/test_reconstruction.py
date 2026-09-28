import numpy as np
import pytest

from perforaar.reconstruction import (
    TrackedDopplerFrame,
    VolumeGrid,
    compound_tracked_frames,
    drop_internal_frames,
    interpolate_parallel_sweep,
    parallel_sweep_indices,
    virtual_parallel_sweep,
)


def test_exact_parallel_sweep_round_trip() -> None:
    x, y, z = np.indices((5, 7, 6), dtype=np.float32)
    power = x + 10 * y + 100 * z
    velocity = (x - 2) * 0.001 + y * 0.0001
    grid = VolumeGrid(power.shape, (0.04, 0.04, 0.04), (-1.0, 2.0, 3.0))
    planes = parallel_sweep_indices(power.shape[1], 1)

    result = compound_tracked_frames(virtual_parallel_sweep(power, velocity, grid, planes), grid)

    np.testing.assert_array_equal(result.power_db, power)
    np.testing.assert_allclose(result.velocity_m_s, velocity, atol=1e-9)
    np.testing.assert_array_equal(result.sample_count, np.ones(power.shape, dtype=np.uint32))


def test_sparse_parallel_sweep_recovers_linear_volume() -> None:
    _, y, _ = np.indices((4, 8, 3), dtype=np.float32)
    volume = 2.5 * y - 4.0
    planes = parallel_sweep_indices(volume.shape[1], 3)
    sparse = np.zeros_like(volume)
    sparse[:, planes, :] = volume[:, planes, :]

    interpolated = interpolate_parallel_sweep(sparse, planes)

    np.testing.assert_allclose(interpolated, volume, atol=1e-6)


def test_frame_dropout_is_deterministic_and_preserves_endpoints() -> None:
    indices = parallel_sweep_indices(25, 3)
    first = drop_internal_frames(indices, 0.25, seed=17)
    second = drop_internal_frames(indices, 0.25, seed=17)

    np.testing.assert_array_equal(first, second)
    assert first[0] == 0
    assert first[-1] == 24
    assert len(first) < len(indices)


def test_invalid_grid_spacing_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        VolumeGrid((2, 2, 2), (0.04, 0.0, 0.04))


def test_non_rigid_tracked_pose_is_rejected() -> None:
    non_rigid = np.eye(4)
    non_rigid[0, 0] = 2.0
    with pytest.raises(ValueError, match="orthonormal"):
        TrackedDopplerFrame(np.ones((2, 2)), np.ones((2, 2)), non_rigid)
