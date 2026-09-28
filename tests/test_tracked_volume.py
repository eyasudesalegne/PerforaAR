import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.tracked_volume import (
    Calibration,
    GridSpec,
    compare_volumes,
    derive_valid_pixel_mask,
    parse_scan_metadata,
    perturb_calibration,
    reference_from_image_transforms,
    write_nifti_gz,
)


class TrackedVolumeTests(unittest.TestCase):
    def test_parse_scan_metadata(self):
        meta = parse_scan_metadata("050", "RH_Per_S_PtD")
        self.assertEqual(meta["arm"], "right")
        self.assertEqual(meta["probe_orientation"], "perpendicular")
        self.assertEqual(meta["trajectory"], "S-shaped")
        self.assertEqual(meta["direction"], "proximal-to-distal")

    def test_reference_transform_starts_at_identity(self):
        tforms = np.repeat(np.eye(4)[None, :, :], 3, axis=0)
        tforms[1, 0, 3] = 5
        calib = Calibration(pixel_to_mm=np.eye(4), tool_from_image=np.eye(4))
        ref = reference_from_image_transforms(tforms, calib)
        np.testing.assert_allclose(ref[0], np.eye(4))
        self.assertAlmostEqual(ref[1, 0, 3], 5.0)

    def test_write_nifti_gz(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiny.nii.gz"
            origin = np.asarray([-12.5, 8.0, 42.25])
            grid = GridSpec(origin, 2.0, (3, 4, 5))
            write_nifti_gz(path, np.zeros((3, 4, 5), dtype=np.float32), grid)
            image = nib.load(path)
            qform, qform_code = image.get_qform(coded=True)
            sform, sform_code = image.get_sform(coded=True)
            self.assertEqual(image.header.get_xyzt_units()[0], "mm")
            self.assertGreater(qform_code, 0)
            self.assertGreater(sform_code, 0)
            np.testing.assert_allclose(qform, sform)
            np.testing.assert_allclose(qform[:3, 3], origin)
            np.testing.assert_allclose(image.header.get_zooms()[:3], (2.0, 2.0, 2.0))

    def test_persistent_nonblack_mask_excludes_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frames.h5"
            frames = np.zeros((10, 8, 9), dtype=np.uint8)
            frames[:, 2:7, 1:8] = 20
            frames[0, 3, 3] = 0
            with h5py.File(path, "w") as frame_file:
                frame_file.create_dataset("frames", data=frames)
            mask = derive_valid_pixel_mask(path, min_nonzero_fraction=0.8)
            self.assertFalse(mask[0, 0])
            self.assertTrue(mask[3, 3])
            self.assertEqual(int(mask.sum()), 35)

    def test_union_metrics_penalize_missing_coverage(self):
        reference = np.zeros((8, 8, 8), dtype=np.float32)
        reference[2:6, 2:6, 2:6] = 100
        candidate = reference.copy()
        reference_mask = reference > 0
        candidate_mask = reference_mask.copy()
        candidate_mask[2:4] = False
        candidate[~candidate_mask] = 0
        reference_result = {
            "raw_volume": reference,
            "volume": reference,
            "raw_mask": reference_mask,
            "filled_mask": reference_mask,
        }
        candidate_result = {
            "raw_volume": candidate,
            "volume": candidate,
            "raw_mask": candidate_mask,
            "filled_mask": candidate_mask,
        }
        metrics = compare_volumes(reference_result, candidate_result)
        self.assertEqual(metrics["raw_nrmse_intersection"], 0.0)
        self.assertGreater(metrics["raw_nrmse_union"], 0.0)
        self.assertEqual(metrics["raw_reference_coverage_retained"], 0.5)
        self.assertLess(metrics["raw_occupied_volume_dice"], 1.0)

    def test_calibration_perturbation_includes_rotation(self):
        calibration = Calibration(np.eye(4), np.eye(4))
        perturbed = perturb_calibration(calibration, [1, 2, 3], [1, -2, 3])
        np.testing.assert_allclose(perturbed.tool_from_image[:3, 3], [1, 2, 3])
        self.assertFalse(np.allclose(perturbed.tool_from_image[:3, :3], np.eye(3)))
        np.testing.assert_allclose(
            perturbed.tool_from_image[:3, :3].T @ perturbed.tool_from_image[:3, :3],
            np.eye(3),
            atol=1e-12,
        )


if __name__ == "__main__":
    unittest.main()
