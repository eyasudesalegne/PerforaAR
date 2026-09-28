from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.tracked_volume import list_scans, make_manifest, validate_scan, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the extracted TUS-REC2024 pilot dataset.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--no-hash", action="store_true", help="Skip MD5/SHA-256 content hashes.")
    args = parser.parse_args()

    root = args.root.resolve()
    manifest = make_manifest(root, hash_contents=not args.no_hash)
    write_json(root / "data" / "external" / "tus_rec2024_manifest.json", manifest)

    validations = [validate_scan(root, scan) for scan in list_scans(root)]
    write_json(root / "results" / "tus_rec2024" / "validation.json", validations)

    failed = [row for row in validations if not row["passed"]]
    print(f"Manifest files: {manifest['file_count']}")
    print(f"Validated scans: {len(validations)}")
    print(f"Failed scans: {len(failed)}")
    if failed:
        for row in failed[:10]:
            print(f"  {row['subject']}/{row['scan']}: {', '.join(row['problems'])}")


if __name__ == "__main__":
    main()
