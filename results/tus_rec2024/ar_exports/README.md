# TUS-REC2024 AR-ready visualization assets

Each committed reconstruction has three derived visualization files:

- `*__surface.glb`: a physical-scale triangular surface for interactive or OpenXR use;
- `*__ar_scene.json`: millimetre units, NIfTI affine, export parameters, and the
  registration contract; and
- `*__surface_preview.png`: three static views for rapid inspection.

The assets use the 35th percentile of non-zero grayscale intensity, Gaussian smoothing
with sigma 1 voxel, and marching-cubes step size 2. These are visualization parameters,
not anatomical segmentation settings. Regenerate an individual asset with:

```bash
python scripts/export_tus_ar_asset.py --volume path/to/reconstruction.nii.gz
```

These are grayscale B-mode forearm surfaces. They are suitable for demonstrating 3D
rendering, scale preservation, interchange, and the future registration path. They are
not colour-Doppler vessels and must not be used for surgical guidance.
