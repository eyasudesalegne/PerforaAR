# M1 tracked 2D-Doppler acquisition specification

## Decision

The baseline PerforaAR acquisition system uses a commercial 2D colour-Doppler scanner
and an optical tracker observing two rigid targets:

1. a probe target rigidly attached to the ultrasound probe;
2. a leg-reference target rigidly attached near the mapped thigh region.

The target models, scanner, capture interface, and camera model remain procurement
decisions. The modality and transform architecture are no longer open alternatives.

## Per-frame record

Every Doppler frame accepted for reconstruction must be linked to:

- a monotonic frame timestamp;
- the closest or interpolated `T_tracker_from_probe` pose and its timestamp;
- the closest or interpolated `T_tracker_from_leg` pose and its timestamp;
- an immutable calibration identifier;
- pixel dimensions and the source frame path/identifier;
- explicit probe-target and leg-reference tracking states;
- synchronization error and quality flags.
- an explicit `accepted_for_reconstruction` decision; lost poses remain `null`, never
  silently replaced by the last known transform.

The machine-readable contract is
[`data/schema/tracked-frame.schema.json`](../data/schema/tracked-frame.schema.json).

## Reconstruction transform

After a vessel pixel `(u, v)` is converted to millimetres in the ultrasound image frame,
the point is placed in the leg frame using:

```text
T_leg_from_image(k)
  = inverse(T_tracker_from_leg(k))
  × T_tracker_from_probe(k)
  × T_probe_from_image
```

This uses only measured poses and calibrated geometry. The absolute tracker-camera
position is irrelevant to the stored map because both moving targets are observed in the
same tracker frame.

## Synchronization

Capture must use monotonic clocks. If the Doppler source and tracker use different
clocks, the acquisition adapter records both device and host timestamps and estimates
their offset. The maximum permitted pose/frame time difference is a protocol parameter
that must be measured and locked before confirmatory testing; it is not assumed here.

Frames are rejected when:

- either optical target is lost or its pose is stale;
- no calibration matching the physical mount is active;
- timestamps are absent or synchronization exceeds the locked tolerance;
- transforms are non-finite, non-rigid, or use inconsistent units/conventions;
- the Doppler image geometry differs from the active calibration;
- the frame is outside the validated depth or field of view.

Interpolation, if later permitted, must be bounded, recorded, and validated separately.
It must never occur silently.

## Calibration artifacts

The M1 calibration package contains:

- pixel-to-millimetre ultrasound image geometry;
- `T_probe_from_image` with residual and calibration method;
- probe-target mount identifier and mechanical revision;
- leg-reference geometry and attachment method;
- AR-camera intrinsics and `T_camera_from_tracker` when the AR and tracking cameras differ;
- date, operator, devices, environment, input-file hashes, and validity status.

See [`data/schema/calibration.schema.json`](../data/schema/calibration.schema.json).

## Acquisition directory

```text
session_id/
├── manifest.json
├── calibration.json
├── frames/
│   └── frame_000001.png
├── tracked_frames.jsonl
├── tracker_raw.csv
└── audit_log.jsonl
```

Raw data and participant data are never committed to the public repository. Only
synthetic or explicitly redistributable examples may be published.

## M1 acceptance evidence

- both targets are acquired in one tracker coordinate system;
- moving the complete phantom/leg-target assembly does not change reconstructed relative geometry beyond the locked tolerance;
- target loss, stale poses, timing violations, and calibration mismatches are detected;
- repeated calibration across operators and days has a reported error distribution;
- one command reproduces a versioned benchtop reconstruction and its error report.

Passing M1 establishes an engineering acquisition chain. It does not establish ALT
clinical accuracy, surgical usefulness, or medical-device safety.
