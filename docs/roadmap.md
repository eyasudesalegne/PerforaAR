# Development roadmap

## M0 — reproducible software baseline (current)

Synthetic detections, deterministic fusion, transparent ranking, rigid geometry, interactive map, tests, and validation documents.

## M1 — calibrated benchtop acquisition

- select exact devices within the fixed 2D colour-Doppler + optical-tracker architecture;
- fabricate and verify rigid probe and leg-reference targets;
- implement timestamped frame capture and simultaneous two-target pose acquisition;
- calibrate image-to-probe, tracker-to-camera, and leg-reference frames;
- reject frames with missing targets, stale calibration, or excessive synchronization error;
- record error budgets and repeatability;
- establish manual vessel annotation as the reference baseline.

## M2 — vascular phantom mapping

- manufacture or procure a documented phantom;
- reconstruct channel centerlines and emergence regions;
- measure fusion, localization, relocation, and latency;
- compare single observations, fused mapping, and alternative registration methods;
- lock a failure-aware AR visualization.

## M3 — non-invasive feasibility

- secure ethics approval and medical-advisor oversight;
- collect consented healthy-volunteer repeatability data;
- analyze subgroups and acquisition failures;
- conduct surgeon-led phantom usability tasks.

## M4 — research pre-prototype

- package calibrated hardware, software, audit logs, and documentation;
- freeze versioned protocols and acceptance results;
- prepare TÜSEB demonstration materials, technical file, and follow-on clinical/regulatory plan.

## Deferred research

Learned live segmentation, sensorless ultrasound reconstruction, true 3D/4D probes,
deformable tracking after flap elevation, CTA/MRA fusion, head-mounted intraoperative
guidance, and clinical outcome studies are separate work packages requiring appropriate
data, approvals, and validation.
