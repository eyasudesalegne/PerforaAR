from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

from perforaar.volume_viewer import (
    crop_slices,
    export_surface_glb,
    extract_surface_mesh,
    load_reconstruction_volume,
    orthogonal_slices,
    positive_intensity_percentile,
    sample_volume_grid,
    scene_metadata,
    scene_metadata_json,
)


def write_test_volume(path: Path) -> Path:
    axes = np.indices((12, 10, 8), dtype=np.float32)
    centre = np.asarray([5.5, 4.5, 3.5], dtype=np.float32).reshape(3, 1, 1, 1)
    distance = np.sqrt(np.sum((axes - centre) ** 2, axis=0))
    data = np.clip(6.0 - distance, 0.0, None).astype(np.float32)
    affine = np.asarray(
        [
            [2.0, 0.0, 0.0, -10.0],
            [0.0, 2.0, 0.0, 5.0],
            [0.0, 0.0, 2.0, 20.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    image = nib.Nifti1Image(data, affine)
    image.header.set_xyzt_units("mm")
    image.set_qform(affine, code=1)
    image.set_sform(affine, code=1)
    nib.save(image, path)
    return path


def test_load_sample_and_slice_volume(tmp_path: Path) -> None:
    volume = load_reconstruction_volume(write_test_volume(tmp_path / "test.nii.gz"))

    assert volume.shape == (12, 10, 8)
    assert volume.voxel_spacing_mm == (2.0, 2.0, 2.0)
    assert volume.physical_extent_mm == (22.0, 18.0, 14.0)
    assert volume.spatial_unit == "mm"
    assert positive_intensity_percentile(volume, 50) > 0

    sampled = sample_volume_grid(volume, ((0, 100), (0, 100), (0, 100)), max_points=100)
    assert sampled["value"].size <= 100
    assert sampled["stride"] > 1
    assert np.allclose(
        [sampled["x"][0], sampled["y"][0], sampled["z"][0]],
        [-10.0, 5.0, 20.0],
    )

    slices = orthogonal_slices(volume, (6, 5, 4))
    assert slices["sagittal"].shape == (8, 10)
    assert slices["coronal"].shape == (8, 12)
    assert slices["axial"].shape == (10, 12)


def test_crop_surface_and_ar_metadata(tmp_path: Path) -> None:
    volume = load_reconstruction_volume(write_test_volume(tmp_path / "test.nii.gz"))
    assert crop_slices(volume.shape, ((25, 75), (0, 100), (10, 90))) == (
        slice(3, 9),
        slice(0, 10),
        slice(0, 8),
    )

    threshold = positive_intensity_percentile(volume, 50)
    vertices, faces = extract_surface_mesh(
        volume,
        threshold,
        smoothing_sigma=0.5,
        step_size=1,
    )
    assert vertices.shape[1] == 3
    assert faces.shape[1] == 3
    assert len(vertices) > 0
    assert export_surface_glb(vertices, faces)[:4] == b"glTF"

    metadata = scene_metadata(
        volume,
        threshold=threshold,
        mesh_vertex_count=len(vertices),
        mesh_face_count=len(faces),
    )
    decoded = json.loads(scene_metadata_json(metadata))
    assert decoded["schema"] == "perforaar.ar-scene.v1"
    assert decoded["spatial_unit"] == "mm"
    assert decoded["registration_required"] is True
