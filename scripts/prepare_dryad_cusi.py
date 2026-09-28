#!/usr/bin/env python3
"""Acquire or ingest the Dryad cUSi archive and verify every file."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_report(destination: Path, manifest: dict) -> dict:
    reports = []
    for record in manifest["files"]:
        path = destination / record["path"]
        observed_size = path.stat().st_size if path.exists() else None
        observed_hash = sha256(path) if path.exists() else None
        valid = observed_size == record["bytes"] and observed_hash == record["sha256"]
        reports.append(
            {
                "path": record["path"],
                "dryad_file_id": record["dryad_file_id"],
                "expected_bytes": record["bytes"],
                "observed_bytes": observed_size,
                "expected_sha256": record["sha256"],
                "observed_sha256": observed_hash,
                "verified": valid,
            }
        )
    return {
        "doi": manifest["doi"],
        "destination": str(destination),
        "all_files_verified": all(record["verified"] for record in reports),
        "files": reports,
    }


def ingest_archive(archive: Path, destination: Path, manifest: dict) -> None:
    allowed = {record["path"] for record in manifest["files"]}
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        if names != allowed:
            raise RuntimeError(f"archive members differ from manifest: {sorted(names ^ allowed)}")
        for info in bundle.infolist():
            if Path(info.filename).name != info.filename:
                raise RuntimeError(f"unsafe archive member: {info.filename}")
            target = destination / info.filename
            with bundle.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def download_files(destination: Path, manifest: dict, retries: int = 4) -> None:
    for record in manifest["files"]:
        target = destination / record["path"]
        if target.exists() and sha256(target) == record["sha256"]:
            continue
        url = f"https://datadryad.org/downloads/file_stream/{record['dryad_file_id']}"
        request = urllib.request.Request(url, headers={"User-Agent": "PerforaAR/0.1 research"})
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    with tempfile.NamedTemporaryFile(dir=destination, delete=False) as temporary:
                        shutil.copyfileobj(response, temporary)
                        temporary_path = Path(temporary.name)
                temporary_path.replace(target)
                break
            except Exception as error:  # pragma: no cover - network behavior
                last_error = error
                time.sleep(2**attempt)
        else:
            raise RuntimeError(f"failed to download {url}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, help="Previously downloaded Dryad ZIP archive")
    parser.add_argument("--destination", type=Path, default=Path("data/raw/dryad_cusi"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/external/dryad_cusi_manifest.json")
    )
    parser.add_argument("--report", type=Path, default=Path("results/dryad_thy3/verification.json"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.destination.mkdir(parents=True, exist_ok=True)
    if args.archive:
        observed_archive_hash = sha256(args.archive)
        expected_archive_hash = manifest.get("archive_sha256_observed")
        if expected_archive_hash and observed_archive_hash != expected_archive_hash:
            raise RuntimeError("archive SHA-256 does not match the recorded Dryad download")
        ingest_archive(args.archive, args.destination, manifest)
    else:
        download_files(args.destination, manifest)

    report = verified_report(args.destination, manifest)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["all_files_verified"]:
        raise RuntimeError(f"verification failed; inspect {args.report}")
    print(f"Verified {len(report['files'])} Dryad files in {args.destination}")


if __name__ == "__main__":
    main()
