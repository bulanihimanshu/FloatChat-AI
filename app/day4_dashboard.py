# app/day4_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO

st.set_page_config(page_title="🌊 FloatChat Dashboard — Day 4", layout="wide")

# -------------------------------
# Load local ARGO parquet
# -------------------------------
@st.cache_data
def load_index():
    return pd.read_parquet("data_cache/argo_index_indian.parquet")

# -------------------------------
# Load NOAA buoys (live)
# -------------------------------
@st.cache_data(ttl=3600)
def load_noaa_buoys():
    url = "https://www.ndbc.noaa.gov/data/stations/stations.json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        df.rename(columns={"lat": "latitude", "lon": "longitude"}, inplace=True)
        return df[["id", "name", "latitude", "longitude"]]
    except Exception as e:
        st.warning(f"⚠️ NOAA buoys unavailable: {e}")
        return pd.DataFrame()

# -------------------------------
# Load INCOIS moorings (live demo — placeholder)
# -------------------------------
@st.cache_data(ttl=3600)
def load_incois_buoys():
    # Replace with INCOIS JSON if available
    # Demo static endpoint for now
    try:
        url = "https://raw.githubusercontent.com/advay-sinha/public-datasets/main/incois_demo.json"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        df.rename(columns={"lat": "latitude", "lon": "longitude"}, inplace=True)
        return df[["station_id", "latitude", "longitude", "sst", "wind_speed"]]
    except Exception as e:
        st.warning(f"⚠️ INCOIS buoys unavailable: {e}")
        return pd.DataFrame()

# -------------------------------
# Download helper
# -------------------------------
def add_download_buttons(df):
    csv = df.to_csv(index=False).encode("utf-8")

    parquet = BytesIO()
    df.to_parquet(parquet, index=False)
    parquet.seek(0)

    # Excel: cap rows to Excel limit
    excel = BytesIO()
    df.head(1_000_000).to_excel(excel, index=False, sheet_name="ArgoData")
    excel.seek(0)

    json = df.to_json(orient="records", indent=2).encode("utf-8")

    st.download_button("⬇️ CSV (Full)", data=csv, file_name="argo_data.csv")
    st.download_button("⬇️ Excel (1M rows max)", data=excel, file_name="argo_data.xlsx")
    st.download_button("⬇️ Parquet (Full)", data=parquet, file_name="argo_data.parquet")
    st.download_button("⬇️ JSON (Full)", data=json, file_name="argo_data.json")


# -------------------------------
# MAIN
# -------------------------------
st.title("🌊 FloatChat Dashboard — Day 4")

df = load_index()
st.success(f"✅ Loaded {len(df):,} rows from **argo_index_indian.parquet**")

# Tabs for clean UI
tab_index, tab_map, tab_profiles, tab_analytics = st.tabs(
    ["📑 Index", "🗺️ Map", "📈 Profiles", "📊 Analytics"]
)

# -------------------------------
# INDEX TAB
# -------------------------------
with tab_index:
    st.subheader("Float Metadata Index View")
    st.dataframe(df.head(500))  # show sample not whole
    add_download_buttons(df)

# -------------------------------
# MAP TAB
# -------------------------------
with tab_map:
    st.subheader("🌍 Interactive Map")

    with st.sidebar:
        st.header("🛰️ Map Settings")
        show_argo = st.checkbox("ARGO Floats", value=True)
        show_noaa = st.checkbox("NOAA Buoys", value=True)
        show_incois = st.checkbox("INCOIS Moorings", value=True)
        basemap = st.selectbox(
            "Map Style",
            ["open-street-map", "carto-positron", "stamen-terrain", "stamen-toner", "carto-darkmatter"],
            index=0,
        )

    # Default map center India
    center = {"lat": 20, "lon": 78}
    zoom = 3.5

    layers = []

    if show_argo and {"latitude", "longitude"}.issubset(df.columns):
        argo_sample = df.sample(min(len(df), 5000), random_state=42)
        layers.append(
            go.Scattermapbox(
                lat=argo_sample["latitude"],
                lon=argo_sample["longitude"],
                mode="markers",
                marker=dict(size=6, color="blue"),
                text=argo_sample["file"],
                name="ARGO Floats",
            )
        )

    if show_noaa:
        noaa_df = load_noaa_buoys()
        if not noaa_df.empty:
            layers.append(
                go.Scattermapbox(
                    lat=noaa_df["latitude"],
                    lon=noaa_df["longitude"],
                    mode="markers",
                    marker=dict(size=9, color="yellow"),
                    text=noaa_df["name"],
                    name="NOAA Buoys",
                )
            )

    if show_incois:
        incois_df = load_incois_buoys()
        if not incois_df.empty:
            popup = [
                f"Station {row['station_id']}<br>SST: {row['sst']} °C<br>Wind: {row['wind_speed']} m/s"
                for _, row in incois_df.iterrows()
            ]
            layers.append(
                go.Scattermapbox(
                    lat=incois_df["latitude"],
                    lon=incois_df["longitude"],
                    mode="markers",
                    marker=dict(size=10, color="green"),
                    text=popup,
                    name="INCOIS Moorings",
                )
            )

    fig_map = go.Figure(data=layers)
    fig_map.update_layout(
        mapbox_style=basemap,
        mapbox=dict(center=center, zoom=zoom),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend=dict(x=0, y=1),
    )

    st.plotly_chart(fig_map, use_container_width=True)

# -------------------------------
# PROFILES TAB
# -------------------------------
with tab_profiles:
    st.subheader("📈 Float Profile Visualizations")

    if {"pres", "temp", "psal"}.issubset(df.columns):
        st.success("✅ Detected profile variables (pres, temp, psal)")

        # -----------------------
        # Profile Selector
        # -----------------------
        if "platform_number" in df.columns:
            unique_ids = df["platform_number"].unique().tolist()
            selected_id = st.selectbox("🔎 Choose a Float / Platform ID", unique_ids)

            profile_df = df[df["platform_number"] == selected_id]
            st.info(f"Showing {len(profile_df):,} rows for float **{selected_id}**")

            # Temp vs Depth
            fig_temp = px.line(
                profile_df, x="temp", y="pres",
                labels={"temp": "Temperature (°C)", "pres": "Pressure (dbar)"},
                title=f"Temperature Profile — Float {selected_id}"
            )
            fig_temp.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_temp, use_container_width=True)

            # Salinity vs Depth
            fig_psal = px.line(
                profile_df, x="psal", y="pres",
                labels={"psal": "Salinity (PSU)", "pres": "Pressure (dbar)"},
                title=f"Salinity Profile — Float {selected_id}"
            )
            fig_psal.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_psal, use_container_width=True)

        # -----------------------
        # TS Diagram
        # -----------------------
        st.markdown("### 🌡️ TS Diagram (Temp vs Salinity)")
        fig_ts = px.scatter(
            df.sample(min(len(df), 5000), random_state=42),  # sample for speed
            x="psal", y="temp",
            color="pres",
            color_continuous_scale="Viridis",
            labels={"psal": "Salinity (PSU)", "temp": "Temperature (°C)", "pres": "Pressure (dbar)"},
            title="Temperature-Salinity Diagram"
        )
        fig_ts.update_layout(height=500)
        st.plotly_chart(fig_ts, use_container_width=True)

        # -----------------------
        # Mean Profiles
        # -----------------------
        st.markdown("### 📉 Mean Vertical Profiles (All Floats)")
        mean_temp = df.groupby("pres")["temp"].mean()
        std_temp = df.groupby("pres")["temp"].std()
        mean_psal = df.groupby("pres")["psal"].mean()
        std_psal = df.groupby("pres")["psal"].std()

        fig_profile = go.Figure()
        # Temp profile
        fig_profile.add_trace(go.Scatter(
            x=mean_temp, y=mean_temp.index,
            mode="lines", name="Mean Temp", line=dict(color="red")
        ))
        fig_profile.add_trace(go.Scatter(
            x=mean_temp + std_temp, y=mean_temp.index,
            mode="lines", name="Temp +1σ", line=dict(color="red", dash="dot")
        ))
        fig_profile.add_trace(go.Scatter(
            x=mean_temp - std_temp, y=mean_temp.index,
            mode="lines", name="Temp -1σ", line=dict(color="red", dash="dot"),
            fill="tonexty", fillcolor="rgba(255,0,0,0.1)"
        ))
        # Salinity profile
        fig_profile.add_trace(go.Scatter(
            x=mean_psal, y=mean_psal.index,
            mode="lines", name="Mean Sal", line=dict(color="blue")
        ))
        fig_profile.add_trace(go.Scatter(
            x=mean_psal + std_psal, y=mean_psal.index,
            mode="lines", name="Sal +1σ", line=dict(color="blue", dash="dot")
        ))
        fig_profile.add_trace(go.Scatter(
            x=mean_psal - std_psal, y=mean_psal.index,
            mode="lines", name="Sal -1σ", line=dict(color="blue", dash="dot"),
            fill="tonexty", fillcolor="rgba(0,0,255,0.1)"
        ))

        fig_profile.update_layout(
            yaxis=dict(title="Pressure (dbar)", autorange="reversed"),
            xaxis_title="Value",
            height=600
        )
        st.plotly_chart(fig_profile, use_container_width=True)

    else:
        st.warning("⚠️ No profile data (pres/temp/psal) found in this dataset. Load a raw ARGO profile parquet.")

# -------------------------------
# ANALYTICS TAB
# -------------------------------
with tab_analytics:
    st.subheader("📊 Analytics & Stats")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Entries", f"{len(df):,}")
    with col2:
        st.metric("Institutions", df["institution"].nunique())
    with col3:
        st.metric("Profiler Types", df["profiler_type"].nunique())

    st.bar_chart(df["institution"].value_counts().head(10))