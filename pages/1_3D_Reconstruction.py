"""Interactive 3D and AR-export view for committed PerforaAR reconstructions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from perforaar.volume_viewer import (
    discover_reconstruction_volumes,
    export_surface_glb,
    extract_surface_mesh,
    load_reconstruction_volume,
    orthogonal_slices,
    positive_intensity_percentile,
    sample_volume_grid,
    scene_metadata,
    scene_metadata_json,
)

st.set_page_config(page_title="PerforaAR 3D", page_icon="🧊", layout="wide")

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VOLUME_DIRECTORY = REPOSITORY_ROOT / "results" / "tus_rec2024" / "volumes"
FIGURE_DIRECTORY = REPOSITORY_ROOT / "results" / "tus_rec2024" / "figures"


def display_name(path: Path) -> str:
    stem = path.name.removesuffix(".nii.gz").removesuffix("__full_20fps")
    subject, scan = stem.split("__", 1)
    return f"Subject {subject} · {scan.replace('_', ' ')}"


@st.cache_resource(show_spinner=False)
def cached_volume(path_text: str):
    return load_reconstruction_volume(Path(path_text))


@st.cache_data(show_spinner=False)
def cached_grid(
    path_text: str,
    crop_ranges: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    max_points: int,
):
    return sample_volume_grid(
        load_reconstruction_volume(Path(path_text)),
        crop_ranges,
        max_points,
    )


@st.cache_data(show_spinner=False)
def cached_ar_export(
    path_text: str,
    threshold: float,
    smoothing_sigma: float,
    step_size: int,
) -> tuple[bytes, bytes, int, int]:
    volume = load_reconstruction_volume(Path(path_text))
    vertices, faces = extract_surface_mesh(
        volume,
        threshold,
        smoothing_sigma=smoothing_sigma,
        step_size=step_size,
    )
    glb = export_surface_glb(vertices, faces)
    metadata = scene_metadata(
        volume,
        threshold=threshold,
        mesh_vertex_count=len(vertices),
        mesh_face_count=len(faces),
    )
    return glb, scene_metadata_json(metadata), len(vertices), len(faces)


def volume_figure(
    grid: dict,
    *,
    threshold: float,
    opacity: float,
    surface_count: int,
    colorscale: str,
    rendering: str,
) -> go.Figure:
    maximum = float(np.max(grid["value"]))
    minimum = min(float(threshold), max(maximum - 1e-3, 0.0))
    common = {
        "x": grid["x"],
        "y": grid["y"],
        "z": grid["z"],
        "value": grid["value"],
        "isomin": minimum,
        "isomax": maximum,
        "colorscale": colorscale,
        "showscale": True,
        "colorbar": {"title": "Intensity"},
    }
    if rendering == "Volume":
        trace = go.Volume(
            **common,
            opacity=opacity,
            surface_count=surface_count,
            caps={"x_show": False, "y_show": False, "z_show": False},
        )
    else:
        trace = go.Isosurface(
            **common,
            opacity=max(opacity, 0.35),
            surface_count=max(1, min(surface_count, 6)),
            caps={
                "x": {"show": False},
                "y": {"show": False},
                "z": {"show": False},
            },
        )
    figure = go.Figure(trace)
    figure.update_layout(
        height=720,
        margin={"l": 0, "r": 0, "t": 38, "b": 0},
        paper_bgcolor="#07111f",
        plot_bgcolor="#07111f",
        font={"color": "#eaf2f8"},
        scene={
            "aspectmode": "data",
            "xaxis": {"title": "X (mm)", "showbackground": False},
            "yaxis": {"title": "Y (mm)", "showbackground": False},
            "zaxis": {"title": "Z (mm)", "showbackground": False},
            "camera": {"eye": {"x": 1.45, "y": 1.45, "z": 1.0}},
        },
        title={"text": f"{rendering} rendering · sampled stride {grid['stride']}"},
    )
    return figure


def slice_figure(image: np.ndarray, title: str) -> go.Figure:
    figure = go.Figure(
        go.Heatmap(
            z=image,
            colorscale="Gray",
            showscale=False,
            hovertemplate="column %{x}<br>row %{y}<br>intensity %{z:.1f}<extra></extra>",
        )
    )
    figure.update_yaxes(scaleanchor="x", autorange="reversed")
    figure.update_layout(
        title=title,
        height=360,
        margin={"l": 5, "r": 5, "t": 42, "b": 5},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


st.title("PerforaAR · 3D reconstruction viewer")
st.caption(
    "Interactive inspection and AR asset export for tracked ultrasound reconstructions · "
    "research use only"
)

volume_paths = discover_reconstruction_volumes(REPOSITORY_ROOT)
if not volume_paths:
    st.error(f"No NIfTI reconstructions were found in {VOLUME_DIRECTORY}")
    st.stop()

st.sidebar.header("Reconstruction")
selected_path = st.sidebar.selectbox(
    "Tracked scan",
    volume_paths,
    format_func=display_name,
)
volume = cached_volume(str(selected_path))

rendering = st.sidebar.radio("3D rendering", ["Volume", "Isosurface"], horizontal=True)
detail = st.sidebar.select_slider(
    "Interactive detail",
    options=["Fast", "Balanced", "High"],
    value="Balanced",
)
max_points = {"Fast": 80_000, "Balanced": 200_000, "High": 450_000}[detail]
threshold_percentile = st.sidebar.slider(
    "Visible intensity percentile",
    min_value=1,
    max_value=95,
    value=35,
    help="Calculated from non-zero voxels, so empty background does not set the threshold.",
)
threshold = positive_intensity_percentile(volume, threshold_percentile)
opacity = st.sidebar.slider("Opacity", 0.03, 0.40, 0.10, 0.01)
surface_count = st.sidebar.slider("Intensity layers", 1, 24, 12)
colorscale = st.sidebar.selectbox("Colour map", ["Gray", "Viridis", "Turbo", "IceFire"])

with st.sidebar.expander("Crop / clipping", expanded=False):
    crop_x = st.slider("X range (%)", 0, 100, (0, 100))
    crop_y = st.slider("Y range (%)", 0, 100, (0, 100))
    crop_z = st.slider("Z range (%)", 0, 100, (0, 100))
crop_ranges = (crop_x, crop_y, crop_z)
if any(lower == upper for lower, upper in crop_ranges):
    st.error("Every crop range must have a non-zero width.")
    st.stop()

shape = " × ".join(str(value) for value in volume.shape)
spacing = " × ".join(f"{value:.1f}" for value in volume.voxel_spacing_mm)
extent = " × ".join(f"{value:.0f}" for value in volume.physical_extent_mm)
metric_columns = st.columns(4)
metric_columns[0].metric("Voxel matrix", shape)
metric_columns[1].metric("Voxel spacing", f"{spacing} mm")
metric_columns[2].metric("Physical extent", f"{extent} mm")
metric_columns[3].metric("Non-zero volume", f"{volume.nonzero_fraction:.1%}")

tab_volume, tab_slices, tab_export, tab_quality = st.tabs(
    ["Interactive 3D", "Orthogonal slices", "AR export", "Acquisition QA"]
)

with tab_volume:
    grid = cached_grid(str(selected_path), crop_ranges, max_points)
    st.plotly_chart(
        volume_figure(
            grid,
            threshold=threshold,
            opacity=opacity,
            surface_count=surface_count,
            colorscale=colorscale,
            rendering=rendering,
        ),
        width="stretch",
        config={"displaylogo": False, "scrollZoom": True},
    )
    st.caption(
        f"Rendering {grid['value'].size:,} sampled voxels at stride {grid['stride']}; "
        f"visible threshold = {threshold:.1f}. Drag to rotate, scroll to zoom and use the "
        "crop controls to inspect internal structures."
    )

with tab_slices:
    control_columns = st.columns(3)
    x_index = control_columns[0].slider("Sagittal X", 0, volume.shape[0] - 1, volume.shape[0] // 2)
    y_index = control_columns[1].slider("Coronal Y", 0, volume.shape[1] - 1, volume.shape[1] // 2)
    z_index = control_columns[2].slider("Axial Z", 0, volume.shape[2] - 1, volume.shape[2] // 2)
    slices = orthogonal_slices(volume, (x_index, y_index, z_index))
    image_columns = st.columns(3)
    for column, name in zip(image_columns, ("sagittal", "coronal", "axial"), strict=True):
        column.plotly_chart(slice_figure(slices[name], name.title()), width="stretch")

with tab_export:
    st.subheader("Prepare a headset-ready scene asset")
    st.write(
        "The GLB surface preserves the reconstruction's physical millimetre coordinates. "
        "The accompanying JSON records the affine and explicitly requires registration to "
        "the participant-specific leg reference frame before an overlay may be shown."
    )
    export_columns = st.columns(3)
    smoothing_sigma = export_columns[0].slider("Surface smoothing", 0.0, 2.5, 1.0, 0.1)
    mesh_step = export_columns[1].select_slider("Mesh detail", [4, 3, 2, 1], value=2)
    export_columns[2].metric("Surface threshold", f"{threshold:.1f}")

    export_key = (
        str(selected_path),
        round(threshold, 5),
        round(smoothing_sigma, 2),
        mesh_step,
    )
    if st.button("Generate GLB and metadata", type="primary"):
        with st.spinner("Extracting the physical-coordinate surface…"):
            try:
                glb, metadata_json, vertices, faces = cached_ar_export(*export_key)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state["perforaar_ar_export"] = {
                    "key": export_key,
                    "glb": glb,
                    "metadata": metadata_json,
                    "vertices": vertices,
                    "faces": faces,
                }

    exported = st.session_state.get("perforaar_ar_export")
    if exported and exported["key"] == export_key:
        st.success(
            f"AR asset generated: {exported['vertices']:,} vertices and "
            f"{exported['faces']:,} triangular faces."
        )
        base_name = selected_path.name.removesuffix(".nii.gz")
        download_columns = st.columns(2)
        download_columns[0].download_button(
            "Download 3D model (.glb)",
            data=exported["glb"],
            file_name=f"{base_name}__surface.glb",
            mime="model/gltf-binary",
            width="stretch",
        )
        download_columns[1].download_button(
            "Download coordinate metadata (.json)",
            data=exported["metadata"],
            file_name=f"{base_name}__ar_scene.json",
            mime="application/json",
            width="stretch",
        )

    st.warning(
        "This TUS-REC2024 volume is grayscale B-mode anatomy—not a segmented colour-Doppler "
        "perforator vessel. It is appropriate for testing rendering, scale and registration, "
        "but not for surgical vessel guidance."
    )

with tab_quality:
    safe_name = selected_path.name.removesuffix(".nii.gz").removesuffix("__full_20fps")
    image_paths = {
        "Tracked probe trajectory": FIGURE_DIRECTORY / f"{safe_name}__trajectory.png",
        "Valid ultrasound mask": FIGURE_DIRECTORY / f"{safe_name}__valid_mask.png",
        "Reconstruction slices and coverage": FIGURE_DIRECTORY / f"{safe_name}__slices.png",
        "Stress-test degradation": FIGURE_DIRECTORY / f"{safe_name}__degradation.png",
    }
    qa_columns = st.columns(2)
    for index, (title, image_path) in enumerate(image_paths.items()):
        with qa_columns[index % 2]:
            st.markdown(f"**{title}**")
            if image_path.exists():
                st.image(str(image_path), width="stretch")
            else:
                st.info(f"Not available: {image_path.name}")

st.info(
    "The desktop viewer is the operator/research interface. A glasses interface should be "
    "implemented as a separate Unity/OpenXR client with only the registered overlay, depth, "
    "confidence, tracking status and re-registration controls."
)
