import gzip
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.tracked_volume import (
    Calibration,
    GridSpec,
    parse_scan_metadata,
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
            grid = GridSpec(np.zeros(3), 2.0, (3, 4, 5))
            write_nifti_gz(path, np.zeros((3, 4, 5), dtype=np.float32), grid)
            with gzip.open(path, "rb") as fh:
                header = fh.read(348)
            self.assertEqual(header[:4], (348).to_bytes(4, "little"))
            self.assertEqual(header[344:348], b"n+1\0")


if __name__ == "__main__":
    unittest.main()
