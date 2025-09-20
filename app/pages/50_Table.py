"""Tabular preview page."""
import streamlit as st

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Table", layout="wide")

render_header("Table")
run_data_interface("Table")
