# Hardware and calibration plan

The first system should remain modular so each error source can be measured independently.

| Subsystem | Function | Selection evidence |
|---|---|---|
| Commercial Doppler/ultrasound | Non-invasive vessel evidence | accessible research output, frame timing, image quality, legal interface |
| Probe attachment | Rigidly couples tracking target and probe | repeatable mount, cleanable, does not obstruct contact face or controls |
| Tracking camera and target | Measures probe and surface reference pose | field of view, latency, jitter, occlusion behavior, SDK access |
| RGB/depth camera | Surface observation and AR view | synchronized frames, intrinsic calibration, depth quality at working distance |
| Compute unit | Fusion, registration, visualization | measured latency, thermal behavior, safe cable management |
| Display | Monitor, projector, tablet, or headset | visibility, parallax, hygiene, user workload |
| Vascular phantom | Known ground truth | documented channel geometry, acoustic properties, replaceability |

## Camera orientation

The camera does not have to be physically parallel to the ultrasound beam. A rigid, stable offset can be calibrated mathematically. The practical design should still minimize occlusion, extreme viewing angles, and a long lever arm because these worsen tracking visibility and error sensitivity.

## Probe contact

Only the manufacturer-designated acoustic window/contact face touches coupling gel and the body or phantom. The mount must not cover this face, deform the probe housing, interfere with cable strain relief, or prevent cleaning.

## Fiducial spheres or pins

Small spherical markers provide easy-to-detect reference points from multiple camera angles. They support pose estimation and calibration; they are not measurement electrodes and do not contact the anatomy unless the final protocol explicitly designs them as surface references.

## Calibration records

Maintain versioned camera intrinsics, camera-to-tracker extrinsics, probe-to-image calibration, phantom truth geometry, working distance, residuals, operator, timestamp, and environmental conditions. A calibration file is an input artifact, not a hidden constant in source code.

