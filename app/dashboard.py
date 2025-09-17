# dashboard.py  —  Final Judge-Ready Demo
import calendar
import os
import io
import ollama
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

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

# Local LLM + Web Search
from duckduckgo_search import DDGS

def web_search(query: str, num_results: int = 3) -> str:
    """Fetch snippets from DuckDuckGo search (no API key needed)."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=num_results)
            snippets = [
                f"{r['title']}: {r['body']}".strip()
                for r in results
                if r.get("title") and r.get("body")
            ]
        return "\n".join(snippets[:num_results]) if snippets else ""
    except Exception as e:
        return f"(Web search unavailable: {e})"

@lru_cache(maxsize=1)
def _ollama_available() -> bool:
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False

def ollama_answer(query: str, context: str = "", model: str = "llama3") -> str:
    """Ask a local Ollama model (free) with optional web context."""
    if not _ollama_available():
        return "⚠️ Local LLM unavailable: service not reachable on localhost:11434."
    
    
    
    
    
    
    try:
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are an expert assistant on oceans and ARGO data."},
                    {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
                ],
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        message = data.get("message", {}).get("content")
        return message or "(Received empty response from Ollama.)"
    except Exception as e:
        return f"⚠️ Local LLM unavailable: {e}"

def hybrid_fallback_answer(query: str) -> str:
    """Fallback: web search + local LLM."""
    context = web_search(query)
    
    if _ollama_available():
        answer = ollama_answer(query, context)
        if answer:
            return answer

    if context:
        return "🔎 Web snippets:\n" + context

    return "⚠️ Unable to fetch an AI answer right now."

import json

@st.cache_data
def load_example_queries(path="example_queries.json"):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return [
            "Show me salinity profiles near the equator in March 2023",
            "Compare BGC parameters in the Arabian Sea for the last 6 months",
            "What are the nearest ARGO floats to this location?",
            "Show me temperature profiles in the Indian Ocean",
            "Give me salinity vs temperature comparison"
        ]

# -----------------------------
# Page config + tiny CSS polish
# -----------------------------
st.set_page_config(page_title="🌊 FloatChat — Final Dashboard", layout="wide")
st.markdown(
    """
    <style>
      /* Reduce any flicker/ghost effect & tighten top spacing */
      .block-container { padding-top: 1rem; }
      .stPlotlyChart, .stPlotlyChart > div { opacity: 1 !important; transition: none !important; animation: none !important; }
      div[data-testid="stVerticalBlock"] { transition: none !important; }
      .st-emotion-cache-1629p8f { padding-top: 0 !important; } /* Streamlit minor layout fix */
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
INDIA_BBOX = dict(lat_min=-15, lat_max=30, lon_min=40, lon_max=110)  # Indian Ocean focus

PLOTLY_TEMPLATES = {
    "Light": "plotly_white",
    "Dark": "plotly_dark",
}

MAP_STYLES_LIGHT = ["open-street-map", "carto-positron", "stamen-terrain"]
MAP_STYLES_DARK = ["carto-darkmatter", "stamen-toner"]

# -----------------------------
# Query parsing + chat helpers
# -----------------------------
VARIABLE_ALIASES: Dict[str, str] = {
    "temp": "temp",
    "temperature": "temp",
    "temperature profile": "temp",
    "heat": "temp",
    "salinity": "psal",
    "psal": "psal",
    "salt": "psal",
    "oxygen": "doxy",
    "dissolved oxygen": "doxy",
    "chlorophyll": "chlorophyll",
    "nitrate": "nitrate",
}

REGION_BOUNDS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "indian ocean": {"lat_range": (-40, 30), "lon_range": (20, 120)},
    "arabian sea": {"lat_range": (5, 30), "lon_range": (45, 75)},
    "bay of bengal": {"lat_range": (5, 25), "lon_range": (80, 100)},
    "equator": {"lat_range": (-5, 5)},
    "southern ocean": {"lat_range": (-70, -40)},
}

COORD_TOKEN_RE = r"-?\d+(?:\.\d+)?(?:\s*(?:degrees?|deg)?\s*(?:north|south|east|west|[nsew]))?"
MONTH_PATTERN = re.compile(
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(20\d{2}|19\d{2})",
    re.IGNORECASE,
)
DIRECTION_KEYWORDS = {"north": "n", "south": "s", "east": "e", "west": "w"}

MONTH_NAME_TO_NUM: Dict[str, int] = {}
for idx in range(1, 13):
    MONTH_NAME_TO_NUM[calendar.month_name[idx].lower()] = idx
    MONTH_NAME_TO_NUM[calendar.month_abbr[idx].lower()] = idx


def _normalize_coord(token: str, axis: str) -> Optional[float]:
    """Convert tokens like '10N' or '45 degrees west' into signed floats."""

    if not token:
        return None

    token_clean = token.strip()
    if not token_clean:
        return None

    direction: Optional[str] = None
    for word, short in DIRECTION_KEYWORDS.items():
        if re.search(word, token_clean, flags=re.IGNORECASE):
            direction = short
            token_clean = re.sub(word, "", token_clean, flags=re.IGNORECASE)
            break

    if token_clean and token_clean[-1].lower() in "nsew":
        direction = token_clean[-1].lower()
        token_clean = token_clean[:-1]

    token_clean = re.sub(r"[°º]", "", token_clean)
    token_clean = re.sub(r"\bdeg(?:rees?)?\b", "", token_clean, flags=re.IGNORECASE)
    token_clean = token_clean.strip()
    match = re.search(r"-?\d+(?:\.\d+)?", token_clean)
    if not match:
        return None

    value = float(match.group(0))
    if direction:
        if axis == "lat" and direction in ("s",):
            value = -value
        if axis == "lon" and direction in ("w",):
            value = -value
    return value


def _extract_axis_range(text: str, axis: str) -> Optional[Tuple[float, float]]:
    """Parse latitude/longitude ranges from free-form text."""

    axis_keywords = ["lat", "latitude"] if axis == "lat" else ["lon", "longitude"]
    for keyword in axis_keywords:
        pattern = rf"{keyword}[^\d-]*({COORD_TOKEN_RE})\s*(?:and|to|-)\s*({COORD_TOKEN_RE})"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            v1 = _normalize_coord(match.group(1), axis)
            v2 = _normalize_coord(match.group(2), axis)
            if v1 is not None and v2 is not None:
                low, high = sorted((v1, v2))
                return (low, high)

    if axis == "lat":
        above = re.search(rf"north of\s*({COORD_TOKEN_RE})", text, flags=re.IGNORECASE)
        below = re.search(rf"south of\s*({COORD_TOKEN_RE})", text, flags=re.IGNORECASE)
        if above:
            value = _normalize_coord(above.group(1), axis)
            if value is not None:
                return (value, 90.0)
        if below:
            value = _normalize_coord(below.group(1), axis)
            if value is not None:
                return (-90.0, value)
    else:
        east = re.search(rf"east of\s*({COORD_TOKEN_RE})", text, flags=re.IGNORECASE)
        west = re.search(rf"west of\s*({COORD_TOKEN_RE})", text, flags=re.IGNORECASE)
        if east:
            value = _normalize_coord(east.group(1), axis)
            if value is not None:
                return (value, 180.0)
        if west:
            value = _normalize_coord(west.group(1), axis)
            if value is not None:
                return (-180.0, value)

    return None


def _extract_near_ranges(text: str) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
    """Detect 'near lat, lon' style queries and return a bounding box."""

    pattern = rf"near\s*({COORD_TOKEN_RE})\s*,\s*({COORD_TOKEN_RE})"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None, None

    lat_center = _normalize_coord(match.group(1), "lat")
    lon_center = _normalize_coord(match.group(2), "lon")
    if lat_center is None or lon_center is None:
        return None, None

    padding = 2.5
    return (
        (lat_center - padding, lat_center + padding),
        (lon_center - padding, lon_center + padding),
    )


def _extract_date_range(text: str) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Parse relative or absolute date ranges."""

    lower = text.lower()
    now = pd.Timestamp.utcnow().normalize()

    recent = re.search(r"last\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)", lower)
    if recent:
        count = int(recent.group(1))
        unit = recent.group(2)
        if "day" in unit:
            start = now - pd.Timedelta(days=count)
        elif "week" in unit:
            start = now - pd.Timedelta(weeks=count)
        elif "month" in unit:
            start = now - pd.DateOffset(months=count)
        else:
            start = now - pd.DateOffset(years=count)
        return (start.normalize(), now)

    month_matches = list(MONTH_PATTERN.finditer(lower))
    if month_matches:
        start_match = month_matches[0]
        end_match = month_matches[-1]
        start_month = MONTH_NAME_TO_NUM[start_match.group(1).lower()]
        start_year = int(start_match.group(2))
        start = pd.Timestamp(year=start_year, month=start_month, day=1)

        end_month = MONTH_NAME_TO_NUM[end_match.group(1).lower()]
        end_year = int(end_match.group(2))
        end = pd.Timestamp(year=end_year, month=end_month, day=1) + pd.offsets.MonthEnd()
        return (start, end)

    years = [int(y) for y in re.findall(r"(19\d{2}|20\d{2})", lower)]
    if years:
        years.sort()
        start_year = years[0]
        end_year = years[-1]
        start = pd.Timestamp(year=start_year, month=1, day=1)
        end = pd.Timestamp(year=end_year, month=12, day=31)
        return (start, end)

    return None


def llm_parse_query(query: str) -> Dict[str, Any]:
    """Lightweight rule-based parser used when the LLM is unavailable."""

    filters: Dict[str, Any] = {}
    lower = query.lower()

    for keyword, column in VARIABLE_ALIASES.items():
        if keyword in lower:
            filters["variable"] = column
            break

    if "profile" in lower and "variable" not in filters:
        filters["variable"] = "temp"

    near_lat, near_lon = _extract_near_ranges(lower)
    if near_lat and "lat_range" not in filters:
        filters["lat_range"] = near_lat
    if near_lon and "lon_range" not in filters:
        filters["lon_range"] = near_lon

    lat_range = _extract_axis_range(lower, "lat")
    if lat_range:
        filters["lat_range"] = lat_range

    lon_range = _extract_axis_range(lower, "lon")
    if lon_range:
        filters["lon_range"] = lon_range

    for region, bbox in REGION_BOUNDS.items():
        if region in lower:
            filters["region"] = region
            if "lat_range" not in filters and "lat_range" in bbox:
                filters["lat_range"] = bbox["lat_range"]
            if "lon_range" not in filters and "lon_range" in bbox:
                filters["lon_range"] = bbox["lon_range"]
            break

    date_range = _extract_date_range(query)
    if date_range:
        filters["date_range"] = date_range

    return filters


def apply_query_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
    """Apply parsed filters to the dataframe and return a summary."""

    if not filters:
        return df, []

    filtered = df
    applied: List[str] = []

    if "lat_range" in filters and "latitude" in filtered.columns:
        lat_min, lat_max = sorted(tuple(map(float, filters["lat_range"])))
        filtered = filtered[(filtered["latitude"] >= lat_min) & (filtered["latitude"] <= lat_max)]
        applied.append(f"latitude {lat_min:.1f}° to {lat_max:.1f}°")

    if "lon_range" in filters and "longitude" in filtered.columns:
        lon_min, lon_max = sorted(tuple(map(float, filters["lon_range"])))
        filtered = filtered[(filtered["longitude"] >= lon_min) & (filtered["longitude"] <= lon_max)]
        applied.append(f"longitude {lon_min:.1f}° to {lon_max:.1f}°")

    if "date_range" in filters and "date" in filtered.columns:
        start, end = filters["date_range"]
        start = pd.to_datetime(start, errors="coerce")
        end = pd.to_datetime(end, errors="coerce")
        if pd.notna(start) and pd.notna(end):
            if end < start:
                start, end = end, start
            filtered = filtered[(filtered["date"] >= start) & (filtered["date"] <= end)]
            applied.append(f"date {start.date()} → {end.date()}")

    return filtered, applied


def _summarize_filters(applied_filters: List[str]) -> str:
    if not applied_filters:
        return "No additional filters applied."
    return "Filters: " + "; ".join(applied_filters)


def build_profile_figure(
    df: pd.DataFrame, variable: str, template: str
) -> Tuple[Optional[go.Figure], Optional[str]]:
    """Create a depth profile figure for the requested variable."""

    if not {"pres", variable}.issubset(df.columns):
        return None, None

    cols = ["pres", variable]
    if "date" in df.columns:
        cols.append("date")
    if "platform_number" in df.columns:
        cols.append("platform_number")

    plot_df = df[cols].dropna(subset=["pres", variable]).copy()
    if plot_df.empty:
        return None, None

    float_id: Optional[str] = None
    if "platform_number" in plot_df.columns:
        available = plot_df["platform_number"].dropna()
        if not available.empty:
            available_str = available.astype(str)
            mode_val = available_str.mode()
            float_id = mode_val.iloc[0] if not mode_val.empty else available_str.iloc[0]
            plot_df = plot_df[plot_df["platform_number"].astype(str) == float_id]

    plot_df = plot_df.sort_values("pres", kind="mergesort").head(2000)
    color_arg = "date" if "date" in plot_df.columns else None

    fig = px.scatter(
        plot_df,
        x=variable,
        y="pres",
        color=color_arg,
        labels={"pres": "Pressure (dbar)", variable: variable.upper()},
        template=template,
        height=420,
    )
    fig.update_traces(mode="lines+markers", marker=dict(size=6))
    fig.update_yaxes(autorange="reversed")

    return fig, float_id


def run_query_pipeline(query: str, df: pd.DataFrame, template: str) -> Dict[str, Any]:
    """End-to-end pipeline used by the chat tab to answer queries."""

    filters = llm_parse_query(query)
    filtered_df, applied_filters = apply_query_filters(df, filters)
    row_count = int(len(filtered_df))

    result: Dict[str, Any] = {
        "filters": filters,
        "applied_filters": applied_filters,
        "filtered_df": filtered_df,
        "row_count": row_count,
        "figure": None,
        "float_id": None,
        "reply": "",
    }

    variable = filters.get("variable")
    if variable and variable in filtered_df.columns and row_count > 0:
        figure, float_id = build_profile_figure(filtered_df, variable, template)
        if figure:
            result["figure"] = figure
            result["float_id"] = float_id
            summary = _summarize_filters(applied_filters)
            base_text = f"Showing {variable.upper()} profile"
            if float_id:
                base_text += f" for float {float_id}"
            base_text += f" ({row_count:,} records)."
            result["reply"] = base_text + "\n" + summary

    if not result["reply"]:
        summary = _summarize_filters(applied_filters)
        if row_count > 0:
            result["reply"] = f"Found {row_count:,} matching rows.\n" + summary
        elif applied_filters:
            result["reply"] = "No rows matched the requested filters.\n" + summary

    return result

# -----------------------------
# Perf helpers
# -----------------------------
def memory_efficient_cast(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast columns to reduce RAM pressure."""
    out = df.copy()
    for c in out.select_dtypes(include=["float64"]).columns:
        out[c] = pd.to_numeric(out[c], downcast="float")
    for c in out.select_dtypes(include=["int64"]).columns:
        out[c] = pd.to_numeric(out[c], downcast="integer")
    # big text -> category (saves tons of RAM on huge frames)
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
    # Normalize date timezone -> naive for filtering speed/safety
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
# Live Data (cached)
# -----------------------------
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

@st.cache_data(ttl=3600)
def load_incois_buoys():
    # Replace with official INCOIS endpoint if available.
    # Demo static JSON with a few stations:
    url = "https://raw.githubusercontent.com/advay-sinha/public-datasets/main/incois_demo.json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        df.rename(columns={"lat": "latitude", "lon": "longitude"}, inplace=True)
        # expected cols: station_id, latitude, longitude, sst, wind_speed
        keep = [c for c in ["station_id", "latitude", "longitude", "sst", "wind_speed"] if c in df.columns]
        return df[keep]
    except Exception as e:
        st.warning(f"⚠️ INCOIS buoys unavailable: {e}")
        return pd.DataFrame()

# -----------------------------
# Sidebar — Data, Filters, Theme
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
    map_style_default = (MAP_STYLES_LIGHT[0] if theme == "Light" else MAP_STYLES_DARK[0])

    st.header("🗺️ Map View")
    focus_india = st.checkbox("🇮🇳 Focus India (default)", value=True)
    world_view = st.checkbox("🌍 World view", value=False)
    map_style = st.selectbox(
        "Map style",
        (MAP_STYLES_LIGHT + MAP_STYLES_DARK),
        index=(MAP_STYLES_LIGHT + MAP_STYLES_DARK).index(map_style_default),
    )

    st.header("🛰️ Live Layers")
    show_noaa = st.checkbox("NOAA Buoys", value=True)
    show_incois = st.checkbox("INCOIS Moorings", value=True)

    st.header("🔎 Filters")
    # Peek date column cheaply without loading full df again
    try:
        date_cols = pd.read_parquet(file_choice, columns=["date"]).columns.tolist()
    except Exception:
        date_cols = []
    use_date_filter = st.checkbox("Filter by date", value=False) if "date" in date_cols else False
    max_points = st.slider("Plot sample size (points)", 2_000, 50_000, 10_000, step=2_000)

# -----------------------------
# Load & Filter
# -----------------------------
with st.spinner("⏳ Loading & preparing data..."):
    df_full = load_parquet(file_choice)

df = df_full
if use_date_filter and "date" in df.columns:
    dmin, dmax = pd.to_datetime(df["date"].min()), pd.to_datetime(df["date"].max())
    dr = st.sidebar.date_input("Date range", [dmin, dmax])
    if len(dr) == 2:
        start, end = pd.to_datetime(dr[0]), pd.to_datetime(dr[1])
        df = df[(df["date"] >= start) & (df["date"] <= end)]

# Default India focus unless world view requested
if focus_india and not world_view:
    df = geo_subset(df, INDIA_BBOX)

# -----------------------------
# Metrics header
# -----------------------------
col1, col2, col3 = st.columns(3)
with col1: st.metric("Rows (filtered)", f"{len(df):,}")
with col2:
    if "institution" in df.columns:
        st.metric("Institutions", f"{df['institution'].nunique():,}")
with col3:
    if "date" in df.columns and len(df) > 0:
        st.metric("Date Range", f"{df['date'].min().date()} → {df['date'].max().date()}")

# -----------------------------
# Tabs
# -----------------------------
tab_plotly, tab_leaflet, tab_cesium, tab_profiles, tab_table, tab_export, tab_chat = st.tabs(
    ["🗺️ Plotly Map", "🗺️ Leaflet (fast)", "🌐 Cesium 3D", "🌊 Profiles", "📑 Table", "💾 Export", "💬 Chat"]
)

# -----------------------------
# Plotly Map (with live layers)
# -----------------------------
with tab_plotly:
    st.subheader("🗺️ Plotly Map")
    if {"latitude", "longitude"}.issubset(df.columns) and len(df) > 0:
        hover_col = "platform_number" if "platform_number" in df.columns else ("file" if "file" in df.columns else df.columns[0])
        plot_df = sampled(
            df[["latitude", "longitude", hover_col] + (["ocean"] if "ocean" in df.columns else [])],
            max_points
        )

        base_fig = px.scatter_mapbox(
            plot_df,
            lat="latitude",
            lon="longitude",
            hover_name=hover_col,
            color="ocean" if "ocean" in plot_df.columns else None,
            height=620,
            zoom=3 if focus_india and not world_view else 1.5,
            center=dict(lat=INDIA_CENTER[0], lon=INDIA_CENTER[1]) if focus_india and not world_view else dict(lat=0, lon=0),
            template=plotly_template,
        )
        base_fig.update_layout(mapbox_style=map_style, margin=dict(l=0, r=0, t=0, b=0))

        # Add live layers
        layers = []
        if show_noaa:
            noaa_df = load_noaa_buoys()
            if not noaa_df.empty:
                layers.append(px.scatter_mapbox(
                    noaa_df, lat="latitude", lon="longitude",
                    hover_name="name", color_discrete_sequence=["yellow"]
                ).data[0])
        if show_incois:
            incois_df = load_incois_buoys()
            if not incois_df.empty:
                incois_hover = incois_df.copy()
                if {"sst", "wind_speed"}.issubset(incois_hover.columns):
                    incois_hover["hover"] = (
                        "Station " + incois_hover.get("station_id", pd.Series(["NA"]*len(incois_hover))).astype(str) +
                        "<br>SST: " + incois_hover["sst"].astype(str) +
                        " °C<br>Wind: " + incois_hover["wind_speed"].astype(str) + " m/s"
                    )
                    hover_field = "hover"
                else:
                    hover_field = "station_id" if "station_id" in incois_hover.columns else incois_hover.columns[0]

                layers.append(px.scatter_mapbox(
                    incois_hover, lat="latitude", lon="longitude",
                    hover_name=hover_field, color_discrete_sequence=["green"]
                ).data[0])

        fig = go.Figure(data=base_fig.data + tuple(layers))
        fig.update_layout(mapbox_style=map_style, margin=dict(l=0, r=0, t=0, b=0), template=plotly_template)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No lat/lon columns to plot.")

# -----------------------------
# Leaflet Map (fast clustering)
# -----------------------------
with tab_leaflet:
    st.subheader("🗺️ Leaflet (folium + clustering)")
    if folium is None or st_folium is None:
        st.warning("Install leaflet support:  pip install folium streamlit-folium")
    elif {"latitude", "longitude"}.issubset(df.columns) and len(df) > 0:
        ldf = sampled(df[["latitude", "longitude"]].dropna(), min(max_points*2, 50_000))
        start_loc = INDIA_CENTER if focus_india and not world_view else (0, 0)
        zoom = 5 if focus_india and not world_view else 2

        tiles = "OpenStreetMap" if theme == "Light" else "CartoDB dark_matter"
        m = folium.Map(location=start_loc, zoom_start=zoom, tiles=tiles, control_scale=True)
        cluster = MarkerCluster().add_to(m)
        for lat, lon in zip(ldf["latitude"].values, ldf["longitude"].values):
            folium.CircleMarker(
                location=[float(lat), float(lon)],
                radius=3,
                fill=True,
                fill_opacity=0.7,
                color="#3388ff" if theme == "Light" else "#66aaff",
            ).add_to(cluster)

        if st.checkbox("Heatmap (approx)"):
            HeatMap(ldf[["latitude", "longitude"]].values.tolist(), radius=8).add_to(m)

        # Live overlays
        if show_noaa:
            noaa_df = load_noaa_buoys()
            for _, r in noaa_df.iterrows():
                folium.CircleMarker(
                    location=[float(r["latitude"]), float(r["longitude"])],
                    radius=4, color="#ffcc00", fill=True, fill_opacity=0.9,
                    popup=folium.Popup(f"NOAA: {r.get('name','')}", max_width=200),
                ).add_to(m)

        if show_incois:
            incois_df = load_incois_buoys()
            for _, r in incois_df.iterrows():
                txt = f"INCOIS: {r.get('station_id','')}"
                if "sst" in r and "wind_speed" in r:
                    txt += f"<br>SST: {r['sst']} °C<br>Wind: {r['wind_speed']} m/s"
                folium.CircleMarker(
                    location=[float(r["latitude"]), float(r["longitude"])],
                    radius=5, color="#22aa44", fill=True, fill_opacity=0.9,
                    popup=folium.Popup(txt, max_width=220),
                ).add_to(m)

        st_folium(m, height=620, width=None)
    else:
        st.info("No lat/lon columns to plot.")

# -----------------------------
# Cesium 3D Globe
# -----------------------------
with tab_cesium:
    st.subheader("🌐 Cesium 3D Globe")
    st.caption("Tip: set CESIUM_ION_TOKEN env variable for premium imagery/terrain.")
    cesium_token = os.getenv("CESIUM_ION_TOKEN", "")

    cdf = sampled(df[["latitude", "longitude"]].dropna(), min(max_points, 10000))
    points_js = [
        f'{{ "lat": {float(r.latitude):.6f}, "lon": {float(r.longitude):.6f} }}'
        for r in cdf.itertuples(index=False)
    ]

    html = f"""
    <div id="cesiumContainer" style="width:100%;height:620px;"></div>
    <script src="https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    <script>
      window.CESIUM_BASE_URL = "https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/";
      const viewer = new Cesium.Viewer('cesiumContainer', {{
        timeline: false, animation: false, sceneModePicker: false,
        baseLayerPicker: true
      }});
      {"Cesium.Ion.defaultAccessToken='" + cesium_token + "';" if cesium_token else ""}

      const pts = [{",".join(points_js)}];
      pts.forEach(p => viewer.entities.add({{
        position: Cesium.Cartesian3.fromDegrees(p.lon, p.lat),
        point: {{ pixelSize: 4, color: Cesium.Color.CYAN }}
      }}));

      // Focus India by default
      const center = Cesium.Cartesian3.fromDegrees({INDIA_CENTER[1]}, {INDIA_CENTER[0]}, 2_000_000);
      viewer.camera.flyTo({{ destination: center }});
    </script>
    """
    st.components.v1.html(html, height=640, scrolling=False)

# -----------------------------
# Profiles (TS, Depth)
# -----------------------------
with tab_profiles:
    st.subheader("🌊 Profiles")
    if {"pres", "temp", "psal"}.issubset(df.columns) and len(df) > 0:
        # Choose float/profile if available
        if "platform_number" in df.columns:
            ids = df["platform_number"].dropna().unique().tolist()
            pid = st.selectbox("Choose Float / Platform", ids)
            pdf = df[df["platform_number"] == pid]

            c1, c2 = st.columns(2)
            with c1:
                fig_t = px.line(
                    pdf, x="temp", y="pres",
                    labels={"temp":"Temperature (°C)","pres":"Pressure (dbar)"},
                    title=f"Temp vs Depth — {pid}", template=plotly_template
                )
                fig_t.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_t, use_container_width=True)
            with c2:
                fig_s = px.line(
                    pdf, x="psal", y="pres",
                    labels={"psal":"Salinity (PSU)","pres":"Pressure (dbar)"},
                    title=f"Salinity vs Depth — {pid}", template=plotly_template
                )
                fig_s.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_s, use_container_width=True)

        st.markdown("### 🌡️ TS Diagram (subset for speed)")
        ts_df = sampled(df[["psal", "temp", "pres"]].dropna(), 5000)
        fig_ts = px.scatter(
            ts_df, x="psal", y="temp", color="pres",
            color_continuous_scale="Viridis",
            labels={"psal":"Salinity (PSU)", "temp":"Temperature (°C)", "pres":"Pressure (dbar)"},
            template=plotly_template
        )
        st.plotly_chart(fig_ts, use_container_width=True)

        st.markdown("### 📉 Mean Vertical Profiles (±1σ)")
        grp = df.dropna(subset=["pres","temp","psal"]).groupby("pres")
        mean_t, std_t = grp["temp"].mean(), grp["temp"].std()
        mean_s, std_s = grp["psal"].mean(), grp["psal"].std()

        fig_mp = go.Figure()
        fig_mp.add_trace(go.Scatter(x=mean_t, y=mean_t.index, name="Mean Temp", mode="lines", line=dict(color="red")))
        fig_mp.add_trace(go.Scatter(x=(mean_t+std_t), y=mean_t.index, name="Temp +1σ", mode="lines", line=dict(color="red", dash="dot")))
        fig_mp.add_trace(go.Scatter(x=(mean_t-std_t), y=mean_t.index, name="Temp -1σ", mode="lines", line=dict(color="red", dash="dot"),
                                    fill="tonexty", fillcolor="rgba(255,0,0,0.12)"))
        fig_mp.add_trace(go.Scatter(x=mean_s, y=mean_s.index, name="Mean Sal", mode="lines", line=dict(color="blue")))
        fig_mp.add_trace(go.Scatter(x=(mean_s+std_s), y=mean_s.index, name="Sal +1σ", mode="lines", line=dict(color="blue", dash="dot")))
        fig_mp.add_trace(go.Scatter(x=(mean_s-std_s), y=mean_s.index, name="Sal -1σ", mode="lines", line=dict(color="blue", dash="dot"),
                                    fill="tonexty", fillcolor="rgba(0,0,255,0.12)"))
        fig_mp.update_layout(yaxis=dict(title="Pressure (dbar)", autorange="reversed"), height=600, template=plotly_template)
        st.plotly_chart(fig_mp, use_container_width=True)
    else:
        st.info("ℹ️ This dataset has no profile data. "
                "Please load a raw ARGO profile parquet "
                "(e.g., *_prof.parquet) to see TS diagrams and vertical profiles.")

# -----------------------------
# Tabular preview (paged-ish)
# -----------------------------
with tab_table:
    st.subheader("📑 Tabular Preview")
    default_cols = [c for c in df.columns][:8]
    show_cols = st.multiselect("Columns", options=list(df.columns), default=default_cols)
    page_size = st.slider("Rows to show", 50, 2000, 200, step=50)
    st.dataframe(df[show_cols].head(page_size))

# -----------------------------
# Export options
# -----------------------------
with tab_export:
    st.subheader("💾 Export (filtered)")
    # CSV full
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ CSV (full)", data=csv_bytes, file_name=f"{file_choice.stem}_filtered.csv", mime="text/csv")

    # ASCII (space-delimited) — first 50k rows
    ascii_bytes = df.head(50_000).to_csv(sep=" ", index=False).encode("utf-8")
    st.download_button("⬇️ ASCII (first 50k)", data=ascii_bytes, file_name=f"{file_choice.stem}_filtered.txt", mime="text/plain")

    # Parquet full
    pq_buf = io.BytesIO()
    df.to_parquet(pq_buf, index=False)
    pq_buf.seek(0)
    st.download_button("⬇️ Parquet (full)", data=pq_buf, file_name=f"{file_choice.stem}_filtered.parquet", mime="application/octet-stream")

    # Excel limited to 1,000,000 rows (Excel limit ~1,048,576)
    xlsx_buf = io.BytesIO()
    df.head(1_000_000).to_excel(xlsx_buf, index=False, sheet_name="ArgoData")
    xlsx_buf.seek(0)
    st.download_button("⬇️ Excel (≤1M rows)", data=xlsx_buf, file_name=f"{file_choice.stem}_filtered.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # NetCDF (needs xarray) — cap rows to keep file size sane
    if xr is None:
        st.info("Install xarray to enable NetCDF export:  pip install xarray netcdf4")
    else:
        nc_buf = io.BytesIO()
        df_nc = df.head(100_000).copy()

        # 🔧 Ensure categorical/object cols are converted before NetCDF export
        for col in df_nc.select_dtypes(include=["category", "object"]).columns:
            df_nc[col] = df_nc[col].astype(str)

        try:
            xr.Dataset.from_dataframe(df_nc).to_netcdf(nc_buf)
            nc_buf.seek(0)
            st.download_button(
                "⬇️ NetCDF (first 100k)",
                data=nc_buf,
                file_name=f"{file_choice.stem}_filtered.nc",
                mime="application/octet-stream",
            )
        except Exception as e:
            st.error(f"⚠️ NetCDF export failed: {e}")
# -----------------------------
# Chatbot Tab (Hybrid Mode, Cleaned)
# -----------------------------
with tab_chat:
    st.subheader("💬 FloatChat – Conversational Interface")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Function to process both typed queries and example queries
    def process_query(query: str):
        st.session_state["messages"].append({"role": "user", "content": query})
        st.chat_message("user").write(query)

        with st.spinner("⚙️ Running query pipeline..."):
            result = run_query_pipeline(query, df_full, plotly_template)

        assistant_text = result.get("reply") or "I couldn't interpret that request with the available data."
        st.session_state["messages"].append({"role": "assistant", "content": assistant_text})
        assistant_chat = st.chat_message("assistant")
        assistant_chat.write(assistant_text)

        figure = result.get("figure")
        fallback_text = ""
        if figure is not None:
            assistant_chat.plotly_chart(figure, use_container_width=True)
        else:
            if result.get("row_count", 0) == 0 and result.get("applied_filters"):
                st.chat_message("assistant").write("⚠️ Sorry, no matching profiles in dataset.")
                
                fallback_text = hybrid_fallback_answer(query)
            if fallback_text:
                st.session_state["messages"].append({"role": "assistant", "content": fallback_text})
                st.chat_message("assistant").write(fallback_text)
    # Render history
    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).write(msg["content"])

    # User input
    if user_query := st.chat_input("Ask about ARGO floats..."):
        process_query(user_query)

    # Example Queries
    st.markdown("### 💡 Try asking these example questions:")
    example_queries = load_example_queries()
    cols = st.columns(2)
    for i, q in enumerate(example_queries):
        if cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
            process_query(q)