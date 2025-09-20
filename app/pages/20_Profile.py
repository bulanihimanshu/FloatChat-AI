"""Profile analysis page."""
import streamlit as st

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Profiles", layout="wide")

render_header("Profile")
run_data_interface("Profile")
