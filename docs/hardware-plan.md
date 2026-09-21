# Selected hardware architecture and calibration plan

The acquisition architecture is fixed at the modality level:

> 2D colour Doppler + optical tracking + rigid probe target + persistent leg reference.

Exact commercial models remain to be selected through documented interface tests. A true
3D/4D probe, electromagnetic tracker, or sensorless reconstruction may be studied later,
but is not the baseline architecture.

| Subsystem | Function | Selection evidence |
|---|---|---|
| Commercial Doppler/ultrasound | Non-invasive vessel evidence | accessible research output, frame timing, image quality, legal interface |
| Probe attachment | Rigidly couples tracking target and probe | repeatable mount, cleanable, does not obstruct contact face or controls |
| Probe optical target | Measures the ultrasound image plane pose | rigid geometry, repeatable attachment, visibility, cleanability |
| Leg optical reference | Makes the map invariant to rigid leg motion | secure non-invasive fixation, visibility outside scan/operative area |
| Optical tracking camera | Measures probe and leg-reference poses in one tracker frame | field of view, latency, jitter, occlusion behavior, timestamp and SDK access |
| RGB/depth camera | Surface observation and AR view | synchronized frames, intrinsic calibration, depth quality at working distance |
| Compute unit | Fusion, registration, visualization | measured latency, thermal behavior, safe cable management |
| Display | Monitor, projector, tablet, or headset | visibility, parallax, hygiene, user workload |
| Vascular phantom | Known ground truth | documented channel geometry, acoustic properties, replaceability |

## Camera orientation

The camera does not have to be physically parallel to the ultrasound beam. A rigid, stable offset can be calibrated mathematically. The practical design should still minimize occlusion, extreme viewing angles, and a long lever arm because these worsen tracking visibility and error sensitivity.

## Probe contact

Only the manufacturer-designated acoustic window/contact face touches coupling gel and the body or phantom. The mount must not cover this face, deform the probe housing, interfere with cable strain relief, or prevent cleaning.

## Leg-reference placement

The leg target must be rigid relative to the scanned thigh segment and remain visible to
the tracker. It may be positioned away from the operative region, but excessive distance
or soft-tissue motion between the marker and mapped area increases registration error.
The validation protocol must measure this effect. The marker must not enter the sterile
field unless an approved sterile implementation exists.

## Fiducial spheres or pins

Small spherical markers provide easy-to-detect reference points from multiple camera angles. They support pose estimation and calibration; they are not measurement electrodes and do not contact the anatomy unless the final protocol explicitly designs them as surface references.

## Calibration records

Maintain versioned camera intrinsics, camera-to-tracker extrinsics, probe-to-image calibration, phantom truth geometry, working distance, residuals, operator, timestamp, and environmental conditions. A calibration file is an input artifact, not a hidden constant in source code.

## Required interface proof before purchase

The selected Doppler path must expose original frames or a research-acceptable lossless
capture with stable timing. The tracker must expose timestamped six-degree-of-freedom
poses for both targets. A vendor rendering, screenshot-only export, or an IMU without
position does not satisfy the acquisition contract.
