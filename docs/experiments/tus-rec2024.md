# TUS-REC2024 Tracked Reconstruction Pilot

Objective: demonstrate that PerforaAR can reconstruct a 3D ultrasound volume from real 2D frames, measured probe poses, and probe calibration.

Scope:
- Validates tracked geometric reconstruction.
- Does not validate Doppler blood-flow reconstruction.
- Does not validate ALT perforator detection because TUS-REC2024 lacks those labels.
- Treats `full_20fps` as a self-generated tracker-based reference, not anatomical ground truth.

Pilot data:
- Dataset: **TUS-REC2024 Validation Dataset**, version 2.0.0.
- Subjects: `050`, `051`, `052`.
- DOI: `10.5281/zenodo.12979481`.
- Archive: `Freehand_US_data_val.zip` (4,842,723,858 bytes, approximately 4.8 GB).
- Archive MD5: `487ebe3241678569296e47efeb2ea325`.
- Scans cover left/right forearms, perpendicular/parallel probe orientations, C/linear/S trajectories, and both distal-to-proximal and proximal-to-distal directions.

Pipeline:
1. Record manifest with file sizes and MD5/SHA-256 hashes in `data/external/tus_rec2024_manifest.json`.
2. Validate every HDF5 frame/transform pair in `results/tus_rec2024/validation.json`.
3. Compose transforms as `T_camera_from_image = T_camera_from_tool @ T_tool_from_image`.
4. Reconstruct each scan relative to its first frame.
5. Derive a per-scan valid-pixel mask from pixels that are non-black in at least 95% of frames, retain the largest connected component, and fill internal mask holes.
6. Compound only valid ultrasound pixels with weighted averaging.
7. Fill only small bounded volume holes by nearest covered voxel distance.
8. Save NIfTI volumes with millimetre units, 2 mm spacing, the physical grid origin, and identical qform/sform affines.
9. Run stress tests for sparse sampling, dropout, latency, pose noise, rotation noise, and translational plus rotational calibration perturbation.
10. Score raw and hole-filled volumes using union/intersection NRMSE, occupied-volume Dice, retained reference coverage, false additional coverage, and masked SSIM.
11. Evaluate transform discrepancies at all supplied landmark pixels in global frame-0 and local previous-frame coordinates.
12. Compare paired PtD and DtP scans after reconstruction in shared optical-tracker camera coordinates.

Metric interpretation:
- Union NRMSE is primary; intersection NRMSE is secondary and cannot hide missing coverage.
- False additional coverage is candidate-only occupied voxels divided by reference occupied voxels.
- Landmark errors compare perturbed/degraded transforms with measured tracker transforms at annotated pixels. They are named `transform_point_error_global_mm` and `transform_point_error_local_mm`; they are not official trackerless-challenge scores.
- Forward/reverse agreement is a consistency check and assumes the optical-tracker camera coordinate system remained stable between paired sweeps.

Primary outputs:
- `results/tus_rec2024/metrics.json`
- `results/tus_rec2024/landmark_metrics.json`
- `results/tus_rec2024/benchmark.json`
- `results/tus_rec2024/SUMMARY.md`
- `results/tus_rec2024/figures/`

## Pilot freeze and confirmatory evaluation

Subjects `050`, `051`, and `052` are development subjects and must never be described as held out. Reconstruction parameters and the explicit numerical acceptance thresholds in `configs/tus_rec2024.yaml` are frozen as `tus-rec2024-pilot-v2` after this correction round.

A confirmatory run requires subjects from another TUS-REC2024 partition. Before that run, record their identifiers in `locked_validation_subjects`, set `experiment_phase` to `locked_confirmatory`, and update `reconstruction_scans` without changing reconstruction parameters or thresholds. The runner rejects an empty locked set, an unfrozen configuration, or any overlap with `pilot_subjects`. The new partition is not present in this workspace, so no confirmatory result is claimed here.

## Performance benchmark

`scripts/benchmark_tus_rec2024.py` reconstructs `050/RH_Per_S_PtD` at pixel strides 8, 4, 2, and 1 on a fixed grid. It records frames/s, pixels/s, peak and incremental RAM, voxel counts, and raw/filled quality relative to stride 1. Performance thresholds are workstation-specific; the frozen reference-workstation floor for stride 1 is 15 frames/s.
