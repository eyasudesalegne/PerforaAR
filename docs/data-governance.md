# Data governance and ethics

## Public repository rule

No identifiable participant data, clinical images, raw DICOM files, voice recordings, consent forms, credentials, or private institutional documents may enter Git history. Deleting a later commit is not an adequate privacy control because history and forks may persist.

## Before collecting volunteer data

The study needs a finalized protocol, risk assessment, institutional ethics approval, information and consent documents, inclusion/exclusion criteria, withdrawal procedure, data-retention period, access list, and incident response. Applicable Turkish personal-data obligations, including KVKK, and institutional rules must be reviewed by the responsible institution.

## Separation of stores

- **Identity key:** encrypted, access-restricted, and held separately.
- **Research measurements:** pseudonymous participant code only.
- **Derived development data:** minimum fields necessary for algorithm work.
- **Public examples:** synthetic or separately approved for redistribution.

The repository stores schemas, loaders, synthetic examples, and aggregate results—not restricted measurements.

## Provenance record

Every dataset version should record source, collection protocol, device and firmware, calibration ID, coordinate convention, units, operator, inclusion/exclusion decisions, transformations, quality flags, license or consent basis, and checksum.

## AI-specific controls

Before training a vessel model, document label definitions, annotator expertise, disagreement handling, subject-level split, subgroup coverage, leakage checks, intended input domain, uncertainty behavior, and an external or held-out evaluation. A model must not silently convert color overlays, device text, or acquisition artifacts into shortcuts.

