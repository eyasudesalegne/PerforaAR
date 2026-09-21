# Technical architecture

## Coordinate frames

| Symbol | Frame | Example origin |
|---|---|---|
| `U` | Doppler image | image corner or acoustic origin |
| `P` | Probe marker | rigid optical target attached to the probe |
| `L` | Leg reference | rigid optical target fixed to the thigh/phantom |
| `R` | Optical tracker | tracker camera coordinate system |
| `C` | AR camera | optical camera center |

All transforms use the convention `T_destination_from_source`. For synchronized frame
`k`, a calibrated ultrasound point becomes a leg-frame point through:

`p_L = inv(T_R_from_L(k)) · T_R_from_P(k) · T_P_from_U · p_U`

For display, the stored point is transformed and projected:

`q = K · T_C_from_L(t) · p_L`

where `K` is the camera intrinsic matrix. `T_P_from_U` comes from ultrasound
image-to-probe calibration. The two time-varying tracker poses must correspond to the
same Doppler frame within a protocol-defined synchronization tolerance. Every transform
records source frame, destination frame, units, timestamp, calibration version, tracking
state, and residual error.

The leg target is mandatory: subtracting its pose makes the vessel map stable in the leg
frame when the leg and probe both move in the tracker view. If either target is occluded,
the frame is invalid unless a separately validated interpolation rule applies.

## Modules

1. **Acquisition adapter** — receives Doppler frames, monotonic timestamps, probe-marker pose, leg-reference pose, and capture status.
2. **Vessel evidence** — manual annotation baseline first; learned segmentation only after suitable labeled data exist.
3. **Spatial fusion** — joins repeated observations and preserves uncertainty and observation count.
4. **Candidate map** — stores position, depth, size proxy, flow evidence, confidence, provenance, and rank components.
5. **Registration** — estimates the leg-reference-to-camera relationship from the persistent target and/or validated surface registration and reports target registration error.
6. **Visualization** — shows the skin entry region and depth-aware trajectory without pretending that deep anatomy is painted directly on the skin.
7. **Audit log** — records settings, calibration identifiers, warnings, latency, and user actions.

## Overlay design

The overlay should use two complementary views:

- a surface marker for the estimated fascia/skin emergence region, with an uncertainty circle;
- a cutaway, depth gauge, or selectable 3D trajectory for anatomy below the surface.

This avoids the misleading impression that a deep vessel lies on the skin plane. When deformation or tracking quality exceeds a validated limit, the overlay must degrade visibly or stop rather than remain confidently fixed.

## Current implementation

M0 implements deterministic fusion, transparent ranking, rigid landmark registration,
and pinhole projection. The geometry module now also implements the selected dual-marker
transform chain and linear-probe pixel calibration. It does not yet implement Doppler
video input, device synchronization, segmentation, live optical tracking, surface
reconstruction, deformation correction, or a head-mounted display.
