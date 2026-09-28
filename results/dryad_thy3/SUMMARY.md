# Dryad THY3 reconstruction result

**Overall status: PASS**

This is a software-verification experiment. The public Dryad data are already
reconstructed 3D mouse-brain volumes, so the tracked 2D frames below are virtual
slices with known poses—not the original acquisitions and not clinical validation.

| Dataset | Condition | Frames | Raw coverage | Dice | Surface Dice | Flow sign | Status |
|---|---:|---:|---:|---:|---:|---:|---:|
| Awake | exact | 156 | 1.000 | 1.0000 | 1.0000 | 1.0000 | PASS |
| Awake | sparse | 40 | 0.256 | 0.8513 | 0.9732 | 0.9849 | PASS |
| Awake | dropout_20pct | 33 | 0.212 | 0.7080 | 0.8392 | 0.9369 | PASS |
| Anesthetized | exact | 240 | 1.000 | 1.0000 | 1.0000 | 1.0000 | PASS |
| Anesthetized | sparse | 61 | 0.254 | 0.8343 | 0.9631 | 0.9863 | PASS |
| Anesthetized | dropout_20pct | 50 | 0.208 | 0.7253 | 0.8577 | 0.9501 | PASS |

## Interpretation

- `exact`: every source plane is replayed and tests coordinate transforms and compounding.
- `sparse`: every fourth plane (160 μm nominal spacing) is replayed, then linearly filled.
- `dropout_20pct`: 20% of internal sparse frames are removed before reconstruction.
- Flow sign is evaluated only in the reference vessel mask where |velocity| ≥ 0.1 mm/s.
- The README and NIfTI `pixdim` support 40 μm spacing, while the encoded s-form has
  a conflicting 0.025 scale and no declared units. Preprocessed outputs therefore use
  the documented 0.04 mm spacing and record this provenance decision.
