from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perforaar.volume_viewer import (  # noqa: E402
    export_surface_glb,
    extract_surface_mesh,
    load_reconstruction_volume,
    positive_intensity_percentile,
    scene_metadata,
    scene_metadata_json,
)


def equalise_axes(ax: plt.Axes, vertices: np.ndarray) -> None:
    minimum = vertices.min(axis=0)
    maximum = vertices.max(axis=0)
    centre = (minimum + maximum) / 2
    radius = float(np.max(maximum - minimum) / 2)
    ax.set_xlim(centre[0] - radius, centre[0] + radius)
    ax.set_ylim(centre[1] - radius, centre[1] + radius)
    ax.set_zlim(centre[2] - radius, centre[2] + radius)
    ax.set_box_aspect((1, 1, 1))


def write_preview(path: Path, vertices: np.ndarray, faces: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure = plt.figure(figsize=(15, 5), facecolor="#07111f")
    views = [
        (24, -48, "Oblique"),
        (8, 5, "Lateral"),
        (82, -90, "Superior"),
    ]
    triangles = vertices[faces]
    for index, (elevation, azimuth, label) in enumerate(views, start=1):
        axis = figure.add_subplot(1, 3, index, projection="3d", facecolor="#07111f")
        surface = Poly3DCollection(
            triangles,
            facecolor="#4bbfbe",
            edgecolor="#a8e6e5",
            linewidth=0.015,
            alpha=0.78,
        )
        axis.add_collection3d(surface)
        equalise_axes(axis, vertices)
        axis.view_init(elev=elevation, azim=azimuth)
        axis.set_title(label, color="white", pad=8)
        axis.set_xlabel("X (mm)", color="#d8e6ef")
        axis.set_ylabel("Y (mm)", color="#d8e6ef")
        axis.set_zlabel("Z (mm)", color="#d8e6ef")
        axis.tick_params(colors="#9fb5c5", labelsize=7)
        axis.grid(False)
        for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
            pane.set_alpha(0.0)
    figure.suptitle(title, color="white", fontsize=14, y=0.98)
    figure.text(
        0.5,
        0.02,
        "Tracked grayscale B-mode reconstruction · research visualization, not a vessel model",
        ha="center",
        color="#b7c7d3",
        fontsize=9,
    )
    figure.tight_layout(rect=(0, 0.05, 1, 0.95))
    figure.savefig(path, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a committed TUS-REC2024 reconstruction as GLB plus AR metadata."
    )
    parser.add_argument(
        "--volume",
        type=Path,
        default=Path(
            "results/tus_rec2024/volumes/050__RH_Per_S_PtD__full_20fps.nii.gz"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tus_rec2024/ar_exports"),
    )
    parser.add_argument("--threshold-percentile", type=float, default=35.0)
    parser.add_argument("--smoothing-sigma", type=float, default=1.0)
    parser.add_argument("--mesh-step", type=int, default=2)
    args = parser.parse_args()

    volume = load_reconstruction_volume(args.volume)
    threshold = positive_intensity_percentile(volume, args.threshold_percentile)
    vertices, faces = extract_surface_mesh(
        volume,
        threshold,
        smoothing_sigma=args.smoothing_sigma,
        step_size=args.mesh_step,
    )
    base_name = args.volume.name.removesuffix(".nii.gz")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    glb_path = args.output_dir / f"{base_name}__surface.glb"
    metadata_path = args.output_dir / f"{base_name}__ar_scene.json"
    preview_path = args.output_dir / f"{base_name}__surface_preview.png"

    glb_path.write_bytes(export_surface_glb(vertices, faces))
    metadata = scene_metadata(
        volume,
        threshold=threshold,
        mesh_vertex_count=len(vertices),
        mesh_face_count=len(faces),
    )
    metadata.update(
        {
            "threshold_percentile_nonzero": args.threshold_percentile,
            "smoothing_sigma_voxels": args.smoothing_sigma,
            "marching_cubes_step_size": args.mesh_step,
        }
    )
    metadata_path.write_bytes(scene_metadata_json(metadata))
    write_preview(preview_path, vertices, faces, base_name.replace("__", " · "))

    print(f"Wrote {glb_path} ({len(vertices)} vertices, {len(faces)} faces)")
    print(f"Wrote {metadata_path}")
    print(f"Wrote {preview_path}")


if __name__ == "__main__":
    main()
