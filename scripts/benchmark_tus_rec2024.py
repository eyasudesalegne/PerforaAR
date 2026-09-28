from __future__ import annotations

import argparse
import gc
import sys
import threading
import time
from pathlib import Path

import matplotlib.pyplot as plt
import psutil
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import h5py  # noqa: E402
import numpy as np  # noqa: E402
from run_tus_rec2024 import image_shape, scan_from_text  # noqa: E402

from perforaar.tracked_volume import (  # noqa: E402
    compare_volumes,
    compute_grid,
    derive_valid_pixel_mask,
    frame_path,
    read_calibration,
    reconstruct_volume,
    reference_from_image_transforms,
    transform_path,
    write_json,
)


class PeakMemoryMonitor:
    def __init__(self, interval_seconds: float = 0.01):
        self.process = psutil.Process()
        self.interval_seconds = interval_seconds
        self.baseline_bytes = self.process.memory_info().rss
        self.peak_bytes = self.baseline_bytes
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self.stop_event.wait(self.interval_seconds):
            self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)

    def __enter__(self) -> PeakMemoryMonitor:
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop_event.set()
        self.thread.join()
        self.peak_bytes = max(self.peak_bytes, self.process.memory_info().rss)


def plot_benchmark(path: Path, rows: list[dict]) -> None:
    ordered = sorted(rows, key=lambda row: row["pixel_stride"])
    strides = [row["pixel_stride"] for row in ordered]
    fps = [row["frames_per_second"] for row in ordered]
    quality = [row["raw_nrmse_union_vs_stride_1"] for row in ordered]
    fig, left = plt.subplots(figsize=(7, 4))
    right = left.twinx()
    left.plot(strides, fps, marker="o", color="#1565c0", label="frames/s")
    right.plot(strides, quality, marker="s", color="#c62828", label="union NRMSE")
    left.set_xlabel("Pixel stride")
    left.set_ylabel("Frames per second", color="#1565c0")
    right.set_ylabel("Raw union NRMSE vs stride 1", color="#c62828")
    left.set_xticks(strides)
    left.grid(alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark TUS-REC2024 reconstruction strides.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/tus_rec2024.yaml"))
    args = parser.parse_args()

    root = args.root.resolve()
    config = yaml.safe_load((root / args.config).read_text())
    scan = scan_from_text(config["benchmark"]["scan"])
    calibration = read_calibration(root / config["calibration_file"])
    with h5py.File(transform_path(root, scan), "r") as transform_file:
        transforms = reference_from_image_transforms(
            np.asarray(transform_file["tforms"], dtype=np.float64), calibration
        )
    mask = derive_valid_pixel_mask(
        frame_path(root, scan),
        min_nonzero_fraction=float(config["valid_mask"]["min_nonzero_fraction"]),
        intensity_threshold=int(config["valid_mask"]["intensity_threshold"]),
    )
    grid = compute_grid(
        transforms,
        image_shape(root, scan),
        calibration,
        float(config["voxel_size_mm"]),
        float(config["grid_margin_mm"]),
        mask,
    )

    strides = [int(value) for value in config["benchmark"]["pixel_strides"]]
    run_order = [1, *sorted(stride for stride in strides if stride != 1)]
    results: dict[int, dict] = {}
    rows_by_stride: dict[int, dict] = {}
    for stride in run_order:
        gc.collect()
        with PeakMemoryMonitor() as memory:
            start = time.perf_counter()
            result = reconstruct_volume(
                frame_path(root, scan),
                transforms,
                calibration,
                grid=grid,
                pixel_stride=stride,
                fill_holes_mm=float(config["fill_holes_mm"]),
                valid_mask=mask,
                seed=int(config["seed"]),
            )
            elapsed = time.perf_counter() - start
        results[stride] = result
        pixels_processed = result["frames_processed"] * result["pixels_per_frame"]
        rows_by_stride[stride] = {
            "pixel_stride": stride,
            "runtime_seconds": elapsed,
            "frames_processed": result["frames_processed"],
            "frames_per_second": result["frames_processed"] / elapsed,
            "pixels_processed": pixels_processed,
            "pixels_processed_per_second": pixels_processed / elapsed,
            "peak_ram_mb": memory.peak_bytes / 1024**2,
            "incremental_peak_ram_mb": (memory.peak_bytes - memory.baseline_bytes) / 1024**2,
            "output_voxel_count": int(np.prod(grid.shape_zyx)),
            "occupied_voxel_count": result["covered_voxels"],
        }

    reference = results[1]
    for stride in strides:
        comparison = compare_volumes(reference, results[stride])
        rows_by_stride[stride].update(
            {f"{key}_vs_stride_1": value for key, value in comparison.items()}
        )
    rows = [rows_by_stride[stride] for stride in strides]
    output = {
        "scan": scan.key,
        "reference_stride": 1,
        "voxel_size_mm": grid.voxel_size_mm,
        "grid": grid.as_dict(),
        "valid_pixel_fraction": float(np.mean(mask)),
        "benchmarks": rows,
    }
    output_path = root / "results" / "tus_rec2024" / "benchmark.json"
    write_json(output_path, output)
    plot_benchmark(root / "results" / "tus_rec2024" / "figures" / "benchmark_stride.png", rows)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
