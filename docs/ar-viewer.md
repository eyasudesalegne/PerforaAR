# Interactive 3D viewer and AR scene contract

The Streamlit application includes a **3D Reconstruction** page for the committed
TUS-REC2024 NIfTI volumes. It is an engineering inspection tool, not a clinical display.

## Run the viewer

```bash
python -m pip install -e ".[demo]"
streamlit run app.py
```

Choose **3D Reconstruction** in Streamlit's page navigation. The interface provides:

- physical-coordinate volume and isosurface rendering;
- X/Y/Z cropping and intensity/opacity controls;
- axial, coronal, and sagittal slice inspection;
- the associated probe-trajectory, mask, coverage, and degradation figures;
- GLB surface export for an AR client; and
- JSON metadata containing millimetre scale, the NIfTI affine, and the required
  registration target.

Pre-generated GLB, metadata, and preview files for all six committed reconstructions are
stored in `results/tus_rec2024/ar_exports/`. They can be regenerated with
`scripts/export_tus_ar_asset.py`.

## Coordinate contract

The GLB vertices remain in the NIfTI physical coordinate system and are measured in
millimetres. The exported `perforaar.ar-scene.v1` JSON records the voxel-to-physical
affine. A headset must not display this asset as a participant overlay until a measured
transform from the reconstruction frame to the participant-specific leg reference frame
has been established and its quality has passed the registration gate.

The intended transform chain is:

```text
volume physical frame -> tracked leg reference -> headset world anchor -> headset view
```

## Division of interface responsibilities

The Streamlit page is the operator/research console. It is deliberately information-rich
so reconstruction quality can be inspected before export.

The glasses interface should be a separate Unity/OpenXR application. Its primary view
should remain sparse and show only:

- registered vessel or anatomy overlay;
- depth and confidence encoding;
- tracking and registration status;
- a visible research-mode indicator;
- hide/show and opacity controls; and
- freeze, re-register, and emergency-clear controls.

The headset client should load the GLB and JSON as one versioned scene package. The exact
deployment project cannot be finalised until the target glasses model and its tracking SDK
are selected.

## Current limitation

The TUS-REC2024 volumes are grayscale B-mode forearm reconstructions. They test 3D
rendering, physical scale, file interchange, and the future registration path, but they do
not contain segmented colour-Doppler perforator vessels. A vascular overlay will require
tracked 2D colour-Doppler data and a validated vessel mask before surface or centreline
export.
