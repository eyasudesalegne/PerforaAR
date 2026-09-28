# Data policy

Only synthetic, de-identified, or explicitly redistributable data may be committed here.

- `sample/` contains generated demonstration records with no link to a person.
- `sample/synthetic_calibration.json` and `sample/synthetic_tracked_frame.json` provide
  schema-valid examples for the selected architecture.
- `schema/detection.schema.json` defines fused/detected vessel evidence.
- `schema/tracked-frame.schema.json` defines the per-frame Doppler and two-target pose contract.
- `schema/calibration.schema.json` defines versioned transform and residual records.
- `external/dryad_cusi_manifest.json` pins the public Dryad dataset version, file IDs,
  sizes, license, and SHA-256 digests used by the THY3 experiment.
- `private/` and `raw/` are ignored and must never be pushed.

The Dryad input is acquired into `raw/dryad_cusi/` with
`scripts/prepare_dryad_cusi.py`. Its CC0 license permits redistribution, but the 113 MB
archive and generated NIfTI volumes are intentionally kept out of Git; the public DOI,
verified manifest, derived metrics, figures, and provenance are sufficient to reproduce
the run without bloating the repository.

The project does not currently distribute ultrasound video, CTA/MRA, participant measurements, or intraoperative data. Future datasets require ethics approval where applicable, participant consent or a lawful basis, de-identification, a data dictionary, provenance, and a written redistribution decision.
