# Scientific basis and gap

Perforator mapping is already performed using handheld Doppler and cross-sectional imaging. PerforaAR is therefore not based on the claim that surgeons cannot find perforators. Its research gap is the combination of tracked non-invasive observations, a persistent uncertainty-aware map, measured re-registration, and a workflow designed for a lower-cost engineering pre-prototype.

Relevant prior work includes:

- A [2025 systematic review and meta-analysis](https://pubmed.ncbi.nlm.nih.gov/40147250/) found promising AR mapping results but concluded that larger, higher-quality studies are still needed.
- Tang et al. reconstructed ALT vessels from CTA and projected emergence locations in a [2022 ALT flap study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9716696/), demonstrating feasibility while using ionizing/contrast imaging rather than the planned Doppler-first workflow.
- Pratt et al. described headset-based AR for extremity reconstruction in a [2018 study](https://pmc.ncbi.nlm.nih.gov/articles/PMC5909360/), an important precedent for spatial overlay.
- Berger et al. reported technical workload, usability, processing time, and alignment limitations in a [2023 workflow assessment](https://pmc.ncbi.nlm.nih.gov/articles/PMC10170605/), supporting the need to measure the full workflow rather than publish overlay images alone.

## Proposed contribution

1. Spatially track a commercial Doppler sweep without modifying its diagnostic function.
2. Combine repeated observations into an auditable three-dimensional candidate map.
3. Represent depth and uncertainty explicitly instead of painting deep anatomy as if it lies on the skin.
4. Measure calibration, relocation error, latency, repeatability, and failure states on known phantom truth.
5. Evaluate non-invasive feasibility in healthy volunteers and usability with surgical advisors, without claiming clinical effectiveness.

## Novelty test

The project should be considered successful scientifically only if it produces a reproducible improvement or new capability over clear baselines. A visually attractive overlay alone is not sufficient. The proposal must report what the baseline is, which component produces the improvement, and where the system fails.

