# Project scope and claims

## Research question

Can a low-cost tracked Doppler workflow preserve repeated perforator observations as a three-dimensional map and relocate that map accurately enough to improve phantom planning efficiency compared with isolated handheld markings?

## Intended users

The current users are biomedical-engineering researchers and collaborating reconstructive surgeons evaluating a prototype. Patients and independent clinical users are outside the current scope.

## Intended use of the prototype

PerforaAR records non-invasive 2D colour-Doppler frames together with synchronized
optical poses for a rigid probe target and a rigid leg reference. It mathematically
places calibrated observations in the leg frame, fuses repeat observations, displays
candidate location, estimated depth, evidence, and uncertainty, and supports phantom or
healthy-volunteer research under an approved protocol.

## Explicit exclusions

The current release does not:

- diagnose vascular anatomy or disease;
- choose a surgical perforator;
- replace Doppler, CTA/MRA, or clinician judgment;
- compensate for tissue deformation after an incision;
- guarantee sterility, latency, accuracy, or clinical safety;
- support intraoperative patient use.

## Testable value propositions

1. Repeated sweeps produce a more repeatable surface location than a single isolated mark.
2. A stored map can be re-registered after movement with measurable target registration error.
3. A ranked map reduces phantom target-localization time without hiding the underlying evidence.
4. The interface communicates uncertainty and failure states clearly enough for trained evaluators.

Each proposition can fail. Results will be reported with uncertainty and without converting phantom or healthy-volunteer findings into clinical-effectiveness claims.

## B3 boundary

The TÜSEB B3 deliverable is a software/pre-prototype and validated engineering workflow. Phantom truth supports accuracy testing. Healthy volunteers support non-invasive feasibility and repeatability only. Clinical effectiveness requires a later protocol, medical-device planning, and appropriate approvals.

Evidence is labelled as **simulated**, **transferred**, **phantom-measured**,
**volunteer-measured**, or **planned**. Results from one category are not used to imply
that another category has been completed.
