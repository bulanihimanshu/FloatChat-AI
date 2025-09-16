import os
import io
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Optional deps (handled gracefully)
try:
    import xarray as xr
except Exception:
    xr = None

# Leaflet via folium
try:
    import folium
    from folium.plugins import MarkerCluster, HeatMap
    from streamlit_folium import st_folium
except Exception:
    folium = None
    st_folium = None

# Live feeds
import requests

# -----------------------------
# Page config + CSS
# -----------------------------
st.set_page_config(page_title="🌊 FloatChat — Final Dashboard", layout="wide")
st.markdown(
    """
    <style>
      .block-container { padding-top: 1rem; }
      .stPlotlyChart { opacity: 1 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Constants
# -----------------------------
DATA_DIR = Path("data_cache")
DEFAULT_PARQUET = "argo_index_indian.parquet"
INDIA_CENTER = (20.5937, 78.9629)
INDIA_BBOX = dict(lat_min=-15, lat_max=30, lon_min=40, lon_max=110)

PLOTLY_TEMPLATES = {"Light": "plotly_white", "Dark": "plotly_dark"}
MAP_STYLES_LIGHT = ["open-street-map", "carto-positron", "stamen-terrain"]
MAP_STYLES_DARK = ["carto-darkmatter", "stamen-toner"]

# -----------------------------
# Helpers
# -----------------------------
def memory_efficient_cast(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.select_dtypes(include=["float64"]).columns:
        out[c] = pd.to_numeric(out[c], downcast="float")
    for c in out.select_dtypes(include=["int64"]).columns:
        out[c] = pd.to_numeric(out[c], downcast="integer")
    for c in out.select_dtypes(include=["object"]).columns:
        try:
            nun = out[c].nunique(dropna=True)
            if 0 < nun < 0.5 * len(out[c]):
                out[c] = out[c].astype("category")
        except Exception:
            pass
    return out

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "time (UTC)": "time",
        "latitude (degrees_north)": "latitude",
        "longitude (degrees_east)": "longitude",
        "pres (decibar)": "pres",
        "temp (degree_Celsius)": "temp",
        "psal (PSU)": "psal",
    }
    return df.rename(columns=rename_map)

@st.cache_data
def list_parquets(data_dir: Path):
    return sorted([p for p in data_dir.glob("*.parquet")])

@st.cache_data
def load_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = normalize_columns(df)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if pd.api.types.is_datetime64tz_dtype(df["date"]):
            df["date"] = df["date"].dt.tz_convert(None)
    return memory_efficient_cast(df)

@st.cache_data
def geo_subset(df: pd.DataFrame, bbox: Dict) -> pd.DataFrame:
    if not {"latitude", "longitude"}.issubset(df.columns):
        return df
    m = (
        (df["latitude"] >= bbox["lat_min"]) & (df["latitude"] <= bbox["lat_max"]) &
        (df["longitude"] >= bbox["lon_min"]) & (df["longitude"] <= bbox["lon_max"])
    )
    return df[m]

@st.cache_data
def sampled(df: pd.DataFrame, n: int = 10000, seed: int = 42) -> pd.DataFrame:
    if len(df) <= n:
        return df
    return df.sample(n, random_state=seed)

# -----------------------------
# Load data choice
# -----------------------------
st.title("🌊 FloatChat — Final Dashboard")

parquets = list_parquets(DATA_DIR)
if not parquets:
    st.error("❌ No parquet files found in data_cache/.")
    st.stop()

with st.sidebar:
    st.header("📂 Data Source")
    names = [p.name for p in parquets]
    default_idx = names.index(DEFAULT_PARQUET) if DEFAULT_PARQUET in names else 0
    file_choice = st.selectbox("Select a parquet", parquets, index=default_idx)
    st.caption(f"Selected: {file_choice.name}")

    st.header("🎨 Theme")
    theme = st.radio("Theme", ["Light", "Dark"], horizontal=True)
    plotly_template = PLOTLY_TEMPLATES[theme]

    st.header("🗺️ Map View")
    focus_india = st.checkbox("🇮🇳 Focus India (default)", value=True)
    world_view = st.checkbox("🌍 World view", value=False)

# -----------------------------
# Load dataframe
# -----------------------------
with st.spinner("⏳ Loading data..."):
    df_full = load_parquet(file_choice)

df = df_full.copy()
if focus_india and not world_view:
    df = geo_subset(df, INDIA_BBOX)

# -----------------------------
# Tabs (added Chat at end)
# -----------------------------
tab_plotly, tab_leaflet, tab_cesium, tab_profiles, tab_table, tab_export, tab_chat = st.tabs(
    ["🗺️ Plotly Map", "🗺️ Leaflet", "🌐 Cesium", "🌊 Profiles", "📑 Table", "💾 Export", "💬 Chat"]
)

# -----------------------------
# Chatbot Tab
# -----------------------------
with tab_chat:
    st.subheader("💬 FloatChat – Conversational Interface")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    if user_query := st.chat_input("Ask about ARGO floats..."):
        st.session_state["messages"].append({"role": "user", "content": user_query})
        st.chat_message("user").write(user_query)

        # --- Simple parser (demo-level) ---
        variable = "psal" if "sal" in user_query.lower() else "temp"
        lat_filter = (-10, 10) if "equator" in user_query.lower() else (-30, 30)
        date_filter = ("2023-03-01", "2023-03-31") if "march 2023" in user_query.lower() else None

        df_chat = df_full.copy()
        if date_filter and "date" in df_chat.columns:
            start, end = pd.to_datetime(date_filter[0]), pd.to_datetime(date_filter[1])
            df_chat = df_chat[(df_chat["date"] >= start) & (df_chat["date"] <= end)]

        if {"latitude", "longitude"}.issubset(df_chat.columns):
            df_chat = df_chat[(df_chat["latitude"] >= lat_filter[0]) & (df_chat["latitude"] <= lat_filter[1])]

        if df_chat.empty:
            bot_reply = "⚠️ Sorry, no matching profiles."
            st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
            st.chat_message("assistant").write(bot_reply)
        else:
            if "platform_number" in df_chat.columns:
                float_id = df_chat["platform_number"].dropna().unique()[0]
                df_float = df_chat[df_chat["platform_number"] == float_id]
            else:
                float_id = "Unknown"
                df_float = df_chat.head(500)

            fig = px.scatter(
                df_float, x=variable, y="pres",
                color="date" if "date" in df_float.columns else None,
                labels={"pres": "Pressure (dbar)", variable: variable.upper()},
                title=f"{variable.upper()} vs Depth for Float {float_id}",
                template=plotly_template
            )
            fig.update_yaxes(autorange="reversed")

            bot_reply = f"Here’s the {variable.upper()} profile for float {float_id}."
            st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
            st.chat_message("assistant").write(bot_reply)
            st.chat_message("assistant").plotly_chart(fig, use_container_width=True)