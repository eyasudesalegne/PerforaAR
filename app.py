"""Interactive M0 demonstration using synthetic tracked detections."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from perforaar import fuse_detections, rank_candidates

st.set_page_config(page_title="PerforaAR M0", page_icon="🩻", layout="wide")
st.title("PerforaAR · tracked perforator-map prototype")
st.caption("Synthetic-data engineering demonstration — not for diagnosis or patient care")

settings = yaml.safe_load(Path("configs/demo.yaml").read_text(encoding="utf-8"))
detections = pd.read_csv("data/sample/synthetic_detections.csv")

st.sidebar.header("Transparent candidate weights")
diameter = st.sidebar.slider(
    "Diameter", 0.0, 1.0, float(settings["ranking"]["weights"]["diameter"]), 0.05
)
depth = st.sidebar.slider(
    "Shallow depth", 0.0, 1.0, float(settings["ranking"]["weights"]["shallow_depth"]), 0.05
)
flow = st.sidebar.slider(
    "Flow evidence", 0.0, 1.0, float(settings["ranking"]["weights"]["flow"]), 0.05
)
confidence = st.sidebar.slider(
    "Detection confidence", 0.0, 1.0, float(settings["ranking"]["weights"]["confidence"]), 0.05
)
radius = st.sidebar.slider(
    "Fusion radius (mm)", 1.0, 10.0, float(settings["fusion"]["radius_mm"]), 0.5
)

weights = {
    "diameter": diameter,
    "shallow_depth": depth,
    "flow": flow,
    "confidence": confidence,
}
if sum(weights.values()) == 0:
    st.error("At least one score weight must be greater than zero.")
    st.stop()

fused = fuse_detections(detections, radius_mm=radius)
ranked = rank_candidates(fused, weights=weights)
top = ranked.iloc[0]

left, middle, right = st.columns(3)
left.metric("Raw observations", len(detections))
middle.metric("Fused candidates", len(ranked))
right.metric("Highest research score", f"{top['score']:.3f} ({top['candidate_id']})")

figure = px.scatter(
    ranked,
    x="x_mm",
    y="y_mm",
    color="score",
    size="diameter_mm",
    text="candidate_id",
    hover_data=["rank", "z_mm", "flow_score", "confidence", "observations"],
    color_continuous_scale="Turbo",
    labels={"x_mm": "Medial → lateral (mm)", "y_mm": "Distal → proximal (mm)"},
    title="Fused candidate map on the reference thigh surface",
)
figure.update_traces(textposition="top center")
figure.update_yaxes(scaleanchor="x", scaleratio=1)
st.plotly_chart(figure, width="stretch")

st.subheader("Explainable ranking")
columns = [
    "rank",
    "candidate_id",
    "x_mm",
    "y_mm",
    "z_mm",
    "diameter_mm",
    "flow_score",
    "confidence",
    "observations",
    "score",
]
st.dataframe(ranked[columns].round(3), hide_index=True, width="stretch")

with st.expander("What this demo does—and does not do"):
    st.markdown(
        """
        It clusters repeated three-dimensional observations and calculates an auditable score.
        The inputs are fictional. A higher score is not proof that a vessel is clinically suitable.
        Live Doppler parsing, participant-specific surface registration, deformation tracking, and
        clinical validation remain future milestones.
        """
    )
