"""Cesium 3D map page."""
import streamlit as st

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Cesium 3D", layout="wide")

map_choice = render_header("Maps", current_map="Cesium 3D")
run_data_interface("Maps", map_choice or "Cesium 3D")
