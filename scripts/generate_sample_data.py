"""Regenerate the repository's synthetic example table."""

from pathlib import Path

from perforaar.synthetic import generate_detections


def main() -> None:
    output = Path("data/sample/synthetic_detections.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    generate_detections(seed=42, observations_per_candidate=5).to_csv(output, index=False)
    print(f"Wrote synthetic records to {output}")


if __name__ == "__main__":
    main()
