# PerforaAR

[![CI](https://github.com/eyasudesalegne/PerforaAR/actions/workflows/ci.yml/badge.svg)](https://github.com/eyasudesalegne/PerforaAR/actions/workflows/ci.yml)

**PerforaAR** is an open research prototype for non-invasive three-dimensional perforator mapping and augmented-reality guidance in anterolateral thigh (ALT) flap planning.

The project turns spatially tracked Doppler observations into a fused, ranked map of candidate perforators, then provides the geometry needed to align that map with a camera view. The first public milestone deliberately uses synthetic data so the software can be tested without exposing personal or clinical data.

> **Research use only.** PerforaAR is not a medical device, has not been clinically validated, and must not be used to diagnose, select a vessel, or guide patient care.

## Why this project exists

Handheld Doppler is useful but produces isolated observations that must be remembered or marked manually. PerforaAR investigates whether tracked sweeps can preserve those observations as a spatial map, combine repeated detections, rank candidates transparently, and relocate the map after repositioning. The benefit is a research hypothesis to be measured against existing practice—not an assumed clinical claim.

## Current public milestone: M0

- deterministic synthetic Doppler detections;
- spatial fusion of repeat detections;
- explainable candidate scoring;
- interactive Streamlit planning-map demo;
- rigid registration and camera-projection geometry;
- automated tests and GitHub Actions;
- staged phantom, healthy-volunteer, and clinician-usability validation plan.

Real-time Doppler acquisition, learned vessel segmentation, deformable registration, and a surgical AR interface are planned modules and are not represented as complete.

## System concept

```mermaid
flowchart TD
    A["Tracked Doppler sweep"] --> B["Vessel evidence"]
    B --> C["3D fusion"]
    C --> D["Candidate ranking"]
    D --> E["Patient-to-camera registration"]
    E --> F["AR planning overlay"]
```

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev,demo]"
pytest
streamlit run app.py
```

To run the pipeline without the web interface:

```bash
python scripts/run_demo.py --input data/sample/synthetic_detections.csv --output outputs/ranked_candidates.csv
```

## Repository map

| Path | Purpose |
|---|---|
| `src/perforaar/` | Tested fusion, scoring, geometry, and synthetic-data modules |
| `app.py` | Interactive research demo |
| `configs/` | Versioned, human-readable pipeline settings |
| `data/` | Schema and synthetic sample only |
| `docs/` | Scope, architecture, hardware, data governance, and validation plan |
| `tests/` | Unit tests for quantitative core functions |

## Evidence and scope

Published studies support investigating AR for perforator mapping, while also showing the need for better validation and workflow assessment. PerforaAR therefore separates engineering performance from clinical claims and uses predefined metrics. See [Scientific basis](docs/scientific-basis.md) and [Validation plan](docs/validation-plan.md).

## Intended TÜSEB B3 contribution

The proposed B3 output is a software/pre-prototype demonstrated on synthetic and phantom data, with non-invasive healthy-volunteer feasibility work only after institutional ethics approval. Any clinical study, intraoperative use, or medical-device claim is outside the present milestone.

## Contributing and citation

See [CONTRIBUTING.md](CONTRIBUTING.md). If you use this repository in research, cite the software metadata in [CITATION.cff](CITATION.cff). The source is available under the Apache License 2.0; third-party datasets, models, and anatomical assets retain their own licenses.
