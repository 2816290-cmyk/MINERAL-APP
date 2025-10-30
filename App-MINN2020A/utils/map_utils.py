"""
utils/map_utils.py
Generates Folium maps for African mineral sites.
"""

import folium
import os
from config import DATA_DIR


def generate_africa_mineral_map(minerals):
    """
    Build a Folium map showing mineral deposits across Africa.
    Each mineral entry may include 'deposits' with lat/lon coordinates.
    Returns the absolute path to the generated HTML map.
    """
    map_path = os.path.join(DATA_DIR, "africa_minerals_map.html")

    # Center the map on Africa
    m = folium.Map(location=[0, 20], zoom_start=3, tiles="cartodb positron")

    # Add deposits (only if coordinates exist)
    for mineral in minerals:
        color = "#007bff"
        for dep in mineral.get("deposits", []):
            lat = dep.get("lat")
            lon = dep.get("lon")
            if lat and lon:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    popup=f"{mineral['name']}<br>{dep.get('site','Unknown')}, {dep.get('country','')}",
                    color=color,
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)

    m.save(map_path)
    return map_path
