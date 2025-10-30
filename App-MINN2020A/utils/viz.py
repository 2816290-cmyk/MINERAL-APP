"""
utils/viz.py
Simple visualization helper for the African Critical Minerals app.
Generates Plotly charts for mineral production trends (2020–2024).
"""

import json
import os
import pandas as pd
import plotly.graph_objs as go
from config import DATA_DIR


def load_minerals_json():
    """Load minerals data from the JSON file."""
    path = os.path.join(DATA_DIR, "minerals.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("minerals", [])


def get_production_dataframe():
    """Convert the production_history arrays into a DataFrame for all minerals."""
    minerals = load_minerals_json()
    rows = []
    for m in minerals:
        for entry in m.get("production_history", []):
            year = entry.get("year")
            amount = entry.get("production_t") or entry.get("production_contained_t", 0)
            rows.append({
                "mineral": m["name"],
                "year": year,
                "production_t": amount,
                "country": entry.get("country", "Unknown")
            })
    return pd.DataFrame(rows)


def generate_mineral_chart(mineral_name):
    """Generate a Plotly line chart for the selected mineral."""
    df = get_production_dataframe()
    df = df[df["mineral"] == mineral_name]

    if df.empty:
        return "<p>No production data available for this mineral.</p>"

    # Aggregate by year in case of multiple countries
    df = df.groupby("year", as_index=False)["production_t"].sum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df["production_t"],
        mode="lines+markers",
        line=dict(width=3, color="#007bff"),
        marker=dict(size=8),
        name=mineral_name
    ))
    fig.update_layout(
        title=f"{mineral_name} Production (2020–2024)",
        xaxis_title="Year",
        yaxis_title="Production (tonnes)",
        template="plotly_white",
        margin=dict(l=40, r=20, t=60, b=40)
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def generate_overview_chart():
    """Create a multi-line chart comparing all minerals' total production."""
    df = get_production_dataframe()
    if df.empty:
        return "<p>No data available.</p>"

    grouped = df.groupby(["year", "mineral"], as_index=False)["production_t"].sum()

    fig = go.Figure()
    for mineral in grouped["mineral"].unique():
        sub = grouped[grouped["mineral"] == mineral]
        fig.add_trace(go.Scatter(
            x=sub["year"],
            y=sub["production_t"],
            mode="lines+markers",
            name=mineral
        ))

    fig.update_layout(
        title="African Critical Minerals Production (2020–2024)",
        xaxis_title="Year",
        yaxis_title="Production (tonnes)",
        legend_title="Mineral",
        template="plotly_white",
        margin=dict(l=40, r=20, t=60, b=40)
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")
