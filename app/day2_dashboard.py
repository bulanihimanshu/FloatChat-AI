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
st.title("🌊 FloatChat Dashboard — Day 2")

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

st.write("📌 Columns available:", list(df.columns))

# -----------------------------
# Download options
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
# Handle Index vs Profile schema
# -----------------------------
if {"latitude", "longitude", "file"}.issubset(df.columns):
    st.subheader("🌍 Index View (Float Metadata)")

    hover_col = "platform_number" if "platform_number" in df.columns else "file"

    # Map style toggle
    map_style = st.radio("🗺️ Map Style", ["open-street-map", "carto-positron", "carto-darkmatter"], horizontal=True)

    # Sampling safeguard
    if len(df) > 5000:
        st.info(f"⚡ Showing a random 5000 points out of {len(df)} total for plotting")
        plot_df = df.sample(5000, random_state=42)
    else:
        plot_df = df

    fig_map = px.scatter_mapbox(
        plot_df,
        lat="latitude",
        lon="longitude",
        hover_name=hover_col,
        color="ocean" if "ocean" in plot_df.columns else None,
        zoom=2,
        height=500,
    )
    fig_map.update_layout(mapbox_style=map_style)
    st.plotly_chart(fig_map, use_container_width=True)

elif {"time", "latitude", "longitude", "pres", "temp", "psal"}.issubset(df.columns):
    st.subheader("🌊 Profile View (Ocean Measurements)")

    fig_profile = px.scatter(
        df,
        x="temp",
        y="pres",
        color="psal",
        hover_data=["platform_number"] if "platform_number" in df.columns else None,
        title="Temperature-Salinity Profile",
    )
    fig_profile.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_profile, use_container_width=True)

else:
    st.warning("⚠️ Unknown schema — showing raw data")
    st.dataframe(df.head())
