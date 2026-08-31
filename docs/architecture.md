# Technical architecture

## Coordinate frames

| Symbol | Frame | Example origin |
|---|---|---|
| `U` | Doppler image | image corner or acoustic origin |
| `P` | Probe | calibrated probe marker frame |
| `S` | Subject/phantom surface | anatomical or fiducial reference |
| `C` | AR camera | optical camera center |

A detected image point becomes a surface-frame point through the calibrated transform chain:

`p_S = T_S←P · T_P←U · p_U`

For display, the stored point is transformed and projected:

`q = K · T_C←S · p_S`

where `K` is the camera intrinsic matrix. Every transform must record source frame, destination frame, units, timestamp, calibration version, and residual error.

## Modules

1. **Acquisition adapter** — receives Doppler frames, timestamps, and probe pose.
2. **Vessel evidence** — manual annotation baseline first; learned segmentation only after suitable labeled data exist.
3. **Spatial fusion** — joins repeated observations and preserves uncertainty and observation count.
4. **Candidate map** — stores position, depth, size proxy, flow evidence, confidence, provenance, and rank components.
5. **Registration** — estimates the surface-to-camera relationship from tracked landmarks or surface geometry and reports target registration error.
6. **Visualization** — shows the skin entry region and depth-aware trajectory without pretending that deep anatomy is painted directly on the skin.
7. **Audit log** — records settings, calibration identifiers, warnings, latency, and user actions.

## Overlay design

The overlay should use two complementary views:

- a surface marker for the estimated fascia/skin emergence region, with an uncertainty circle;
- a cutaway, depth gauge, or selectable 3D trajectory for anatomy below the surface.

This avoids the misleading impression that a deep vessel lies on the skin plane. When deformation or tracking quality exceeds a validated limit, the overlay must degrade visibly or stop rather than remain confidently fixed.

## Current implementation

M0 implements deterministic fusion, transparent ranking, rigid landmark registration, and pinhole projection. It does not yet implement Doppler video input, segmentation, temporal tracking, surface reconstruction, deformation correction, or a head-mounted display.

