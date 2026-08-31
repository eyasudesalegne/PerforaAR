# Staged validation plan

This plan prevents technical feasibility, usability, and clinical effectiveness from being mixed into one claim. Thresholds below are provisional design targets and must be frozen in a dated protocol before confirmatory testing.

## Stage 0 — software verification

Use synthetic transforms and known clusters to verify units, coordinate direction, fusion behavior, ranking calculations, invalid-input rejection, and projection. Continuous integration must pass on supported Python versions.

## Stage 1 — benchtop calibration

Use a calibrated grid and tracked probe mount.

Primary measurements:

- camera reprojection error in pixels;
- probe-to-image calibration residual in millimetres;
- tracker static jitter and drift;
- end-to-end latency and dropped-frame rate;
- repeated calibration variability across operators and days.

No downstream experiment proceeds when calibration identity is missing or residuals exceed the protocol limit.

## Stage 2 — vascular phantom ground truth

Use channels with known centerlines, depths, diameters, and emergence locations. Randomize targets and repeat acquisition after repositioning.

Primary outcomes:

- three-dimensional centerline distance;
- surface target registration error (median, 95th percentile, and maximum);
- detection sensitivity and false candidates per mapped area;
- repeated-sweep localization variability;
- map relocation error after rigid movement;
- processing latency.

Initial engineering targets are median surface error no greater than 3 mm and 95th-percentile error no greater than 5 mm under the tested phantom configuration. These are project targets, not established clinical acceptance limits.

## Stage 3 — non-invasive healthy-volunteer feasibility

After ethics approval and consent, recruit approximately 30–40 adult volunteers. Record non-invasive Doppler sweeps only. Do not infer surgical suitability and do not perform an intervention.

Compare:

- within-session and between-session map repeatability;
- single-mark versus fused-map positional variation;
- acquisition time, failure rate, and operator workload;
- robustness across body habitus and surface curvature;
- participant discomfort or adverse events.

Because no intraoperative truth exists in healthy volunteers, label the findings as repeatability and feasibility—not anatomical accuracy or sensitivity.

## Stage 4 — surgeon-led phantom usability pilot

One or more reconstructive-surgery advisors perform counterbalanced phantom tasks using conventional markings and PerforaAR. Measure target-localization time, position error, corrections, task completion, System Usability Scale, NASA-TLX or a concise workload measure, and structured failure feedback.

The purpose is to refine the pre-prototype and protocol. The sample is not powered to claim improved patient outcomes.

## Statistical reporting

- preregister primary outcomes and exclusion rules;
- report distributions, paired differences, confidence intervals, and all failures;
- separate development data from locked evaluation data;
- avoid frame-level pseudo-replication by treating participant or phantom run as the experimental unit;
- publish configuration, calibration version, and code commit for every reported run.

## Stop conditions

Stop or suppress the overlay when calibration is missing, tracking is lost, latency exceeds the approved limit, uncertainty is not finite, the surface moves outside the validated range, or coordinate-frame consistency checks fail.

