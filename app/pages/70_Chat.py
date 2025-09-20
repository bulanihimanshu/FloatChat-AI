"""Dedicated chat experience."""
import streamlit as st

from app.app_layout import run_data_interface
from app.navigation import render_header

st.set_page_config(page_title="🌊 FloatChat AI — Chat", layout="wide")

render_header("Chat")
run_data_interface("Chat")
