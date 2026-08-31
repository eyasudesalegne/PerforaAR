"""Run the transparent M0 fusion and ranking pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from perforaar import fuse_detections, rank_candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/demo.yaml"))
    args = parser.parse_args()

    settings = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    detections = pd.read_csv(args.input)
    fused = fuse_detections(detections, radius_mm=float(settings["fusion"]["radius_mm"]))
    ranked = rank_candidates(fused, weights=settings["ranking"]["weights"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(args.output, index=False)
    print(f"Wrote {len(ranked)} ranked candidates to {args.output}")


if __name__ == "__main__":
    main()
