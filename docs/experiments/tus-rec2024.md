# TUS-REC2024 Tracked Reconstruction Pilot

Objective: demonstrate that PerforaAR can reconstruct a 3D ultrasound volume from real 2D frames, measured probe poses, and probe calibration.

Scope:
- Validates tracked geometric reconstruction.
- Does not validate Doppler blood-flow reconstruction.
- Does not validate ALT perforator detection because TUS-REC2024 lacks those labels.

Pilot data:
- Subjects: `050`, `051`, `052`.
- Scans cover left/right forearms, perpendicular/parallel probe orientations, C/linear/S trajectories, and both distal-to-proximal and proximal-to-distal directions.

Pipeline:
1. Record manifest with file sizes and MD5/SHA-256 hashes in `data/external/tus_rec2024_manifest.json`.
2. Validate every HDF5 frame/transform pair in `results/tus_rec2024/validation.json`.
3. Compose transforms as `T_camera_from_image = T_camera_from_tool @ T_tool_from_image`.
4. Reconstruct each scan relative to its first frame.
5. Compound overlapping sampled pixels with weighted averaging.
6. Fill only small bounded holes by nearest covered voxel distance.
7. Save reference volumes as NIfTI in `results/tus_rec2024/volumes/`.
8. Run stress tests for sparse sampling, dropout, latency, pose noise, rotation noise, and calibration perturbation.

Primary outputs:
- `results/tus_rec2024/metrics.json`
- `results/tus_rec2024/SUMMARY.md`
- `results/tus_rec2024/figures/`

Acceptance criteria should be frozen after reviewing the pilot ranges in `metrics.json`, before running any locked validation subjects.
