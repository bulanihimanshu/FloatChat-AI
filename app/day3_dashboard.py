import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import io

# -----------------------------
# Helper: normalize columns
# -----------------------------
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

# -----------------------------
# Load cached parquet
# -----------------------------
@st.cache_data
def load_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return normalize_columns(df)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="🌊 FloatChat Dashboard — Day 3", layout="wide")
st.title("🌊 FloatChat Dashboard — Day 3")

# Logo in sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Argo_float.png/320px-Argo_float.png", caption="Argo Float", use_container_width=True)

# List available parquet files
data_dir = Path("data_cache")
parquet_files = sorted(data_dir.glob("*.parquet"))

if not parquet_files:
    st.error("❌ No parquet files found in data_cache/. Please run the converter or ingestion first.")
    st.stop()

with st.sidebar:
    st.header("📂 Data Source")
    file_choice = st.selectbox("Select a parquet file", parquet_files)
    st.caption(f"Selected: {file_choice.name}")

# Load data
df = load_parquet(file_choice)
st.success(f"Loaded {len(df)} rows from {file_choice.name}")

# -----------------------------
# Sidebar Filters
# -----------------------------
with st.sidebar:
    st.header("🔎 Filters")

    # Institution filter
    if "institution" in df.columns:
        inst = st.selectbox("Institution", ["All"] + sorted(df["institution"].dropna().unique().tolist()))
        if inst != "All":
            df = df[df["institution"] == inst]

    # Date filter
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if pd.api.types.is_datetime64tz_dtype(df["date"]):
            df["date"] = df["date"].dt.tz_convert(None)

        date_min, date_max = df["date"].min(), df["date"].max()
        date_range = st.date_input("Date range", [date_min, date_max])

        if len(date_range) == 2:
            start, end = pd.to_datetime(date_range)
            if hasattr(start, "tz_localize"):
                start = start.tz_localize(None)
            if hasattr(end, "tz_localize"):
                end = end.tz_localize(None)

            df = df[(df["date"] >= start) & (df["date"] <= end)]

    # Reset filters button
    if st.button("🔄 Reset Filters"):
        st.experimental_rerun()

# -----------------------------
# Tabs for navigation
# -----------------------------
tab1, tab2, tab3 = st.tabs(["🌍 Index View", "🌊 Profile View", "📈 Analytics"])

# -----------------------------
# Download options (global)
# -----------------------------
st.sidebar.header("💾 Download Data")
csv_data = df.to_csv(index=False).encode("utf-8")
parquet_data = io.BytesIO()
df.to_parquet(parquet_data, index=False)
parquet_data.seek(0)
excel_data = io.BytesIO()
df.to_excel(excel_data, index=False, sheet_name="ArgoData")
excel_data.seek(0)
json_data = df.to_json(orient="records").encode("utf-8")

st.sidebar.download_button("⬇️ CSV", data=csv_data, file_name=f"{file_choice.stem}_filtered.csv", mime="text/csv")
st.sidebar.download_button("⬇️ Excel (.xlsx)", data=excel_data, file_name=f"{file_choice.stem}_filtered.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.sidebar.download_button("⬇️ Parquet", data=parquet_data, file_name=f"{file_choice.stem}_filtered.parquet", mime="application/octet-stream")
st.sidebar.download_button("⬇️ JSON", data=json_data, file_name=f"{file_choice.stem}_filtered.json", mime="application/json")

# -----------------------------
# 🌍 Index View (Map)
# -----------------------------
with tab1:
    if {"latitude", "longitude"}.issubset(df.columns):
        st.subheader("🌍 Float Locations")

        hover_col = "platform_number" if "platform_number" in df.columns else df.columns[0]

        # Map style & mode toggle
        col1, col2 = st.columns(2)
        with col1:
            map_style = st.radio("🗺️ Map Style", ["open-street-map", "carto-positron", "carto-darkmatter", "stamen-terrain"], horizontal=True)
        with col2:
            map_mode = st.radio("📌 Visualization Mode", ["Scatter Plot", "Density Heatmap", "Time Animation"], horizontal=True)

        if map_mode == "Scatter Plot":
            plot_df = df.sample(min(len(df), 5000), random_state=42)
            fig_map = px.scatter_mapbox(
                plot_df,
                lat="latitude",
                lon="longitude",
                hover_name=hover_col,
                color=df["ocean"] if "ocean" in df.columns else None,
                zoom=2,
                height=600,
            )
        elif map_mode == "Density Heatmap":
            fig_map = px.density_mapbox(
                df,
                lat="latitude",
                lon="longitude",
                radius=8,
                zoom=1,
                height=600,
            )
        else:  # Time Animation
            if "date" in df.columns:
                df["date_str"] = df["date"].dt.to_period("M").astype(str)
                fig_map = px.scatter_mapbox(
                    df,
                    lat="latitude",
                    lon="longitude",
                    hover_name=hover_col,
                    animation_frame="date_str",
                    zoom=1,
                    height=600,
                )
                # Add play/pause with speed
                fig_map.update_layout(
                    updatemenus=[{
                        "buttons": [
                            {"args": [None, {"frame": {"duration": 800, "redraw": True},
                                             "transition": {"duration": 300}}],
                             "label": "▶ Play", "method": "animate"},
                            {"args": [[None], {"frame": {"duration": 0, "redraw": False},
                                               "mode": "immediate",
                                               "transition": {"duration": 0}}],
                             "label": "⏸ Pause", "method": "animate"}
                        ],
                        "direction": "left", "x": 0.1, "y": 0
                    }]
                )
            else:
                st.warning("⚠️ No date column available for animation.")
                fig_map = None

        if fig_map:
            fig_map.update_layout(mapbox_style=map_style)
            st.plotly_chart(fig_map, use_container_width=True)

        if st.button("🧭 Reset View"):
            st.experimental_rerun()
    else:
        st.info("No geographic columns available.")

# -----------------------------
# 🌊 Profile View
# -----------------------------
with tab2:
    if {"time", "latitude", "longitude", "pres", "temp", "psal"}.issubset(df.columns):
        st.subheader("🌊 Temperature-Salinity Profiles")

        # Classic TS Diagram
        fig_ts = px.scatter(
            df,
            x="psal",
            y="temp",
            color="pres",
            title="TS Diagram (Salinity vs Temperature)",
        )
        st.plotly_chart(fig_ts, use_container_width=True)

        # Depth profile
        fig_profile = px.scatter(
            df,
            x="temp",
            y="pres",
            color="psal",
            title="Temperature vs Pressure (Depth)",
        )
        fig_profile.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_profile, use_container_width=True)
    else:
        st.info("No profile data available.")

# -----------------------------
# 📈 Analytics
# -----------------------------
with tab3:
    st.subheader("📊 Dataset Summary")

    st.metric("Total Rows", f"{len(df):,}")
    if "institution" in df.columns:
        st.metric("Institutions", df["institution"].nunique())
    if "date" in df.columns:
        st.metric("Date Range", f"{df['date'].min().date()} → {df['date'].max().date()}")

    if "institution" in df.columns:
        st.subheader("Floats by Institution")
        fig_inst = px.histogram(df, x="institution")
        st.plotly_chart(fig_inst, use_container_width=True)

    if "date" in df.columns:
        st.subheader("Deployments per Year")
        df["year"] = df["date"].dt.year
        fig_year = px.histogram(df, x="year")
        st.plotly_chart(fig_year, use_container_width=True)
