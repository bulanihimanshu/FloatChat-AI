# dashboard.py  —  Final Judge-Ready Demo
import calendar
import os
import io
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()

try:
    import ollama as _ollama_client
except Exception:
    _ollama_client = None

# Optional deps (handled gracefully)
try:
    import xarray as xr
except Exception:
    xr = None

# Leaflet via folium
try:
    import folium
    from folium.plugins import MarkerCluster, HeatMap
except Exception:
    folium = None
    MarkerCluster = None
    HeatMap = None

# Lightweight geocoding (optional)
try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
except Exception:
    Nominatim = None
    RateLimiter = None

# Live feeds
import requests

# Local LLM + Web Search
from ddgs import DDGS

LLM_SYSTEM_PROMPT = (
    "You are FloatChat, an assistant that analyses the in-app ARGO float dataset and "
    "keeps responses focused on oceanography insights relevant to the FloatChat project."
)
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
    if _ollama_client is not None:
        try:
            _ollama_client.list()
            return True
        except Exception:
            pass

    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False

def ollama_answer(
    query: str,
    context: str = "",
    model: str = os.getenv("OLLAMA_MODEL", "mistral"),
) -> str:
    """Ask a local Ollama model (free) with optional web context."""
    if not _ollama_available():
        return "⚠️ Local LLM unavailable: service not reachable on localhost:11434."

    prompt = f"Question: {query}\n\nContext:\n{context.strip()}".strip()

    if _ollama_client is not None:
        try:
            response = _ollama_client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )
            message = response.get("message", {}).get("content") if isinstance(response, dict) else None
            if message:
                return message.strip()
        except Exception:
            # Fall back to HTTP API below.
            pass

    try:
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        message = data.get("message", {}).get("content")
        if message:
            return message.strip()
        return "(Received empty response from Ollama.)"
    except Exception as e:
        return f"⚠️ Local LLM unavailable: {e}"

def hybrid_fallback_answer(query: str) -> str:
    """Fallback: web search + local LLM."""
    context = web_search(query)
    answer_parts: List[str] = []

    if _ollama_available():
        answer = ollama_answer(query, context)
        if answer:
            answer_parts.append(answer)

    if context:
        answer_parts.append("🔎 FloatChat external context:\n" + context)

    if answer_parts:
        answer_parts.append(
            "🤖 FloatChat note: I'll prioritise answers grounded in our cached ARGO floats whenever data matches your filters."
        )
        return "\n\n".join(answer_parts)

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


def _apply_base_styles() -> None:
    """Common layout tweaks applied regardless of theme."""

    st.markdown(
        """
        <style>
          /* Reduce any flicker/ghost effect & tighten top spacing */
          .block-container { padding-top: 1rem; }
          .stPlotlyChart, .stPlotlyChart > div {
              opacity: 1 !important;
              transition: none !important;
              animation: none !important;
          }
          div[data-testid="stVerticalBlock"] { transition: none !important; }
          .st-emotion-cache-1629p8f { padding-top: 0 !important; } /* Streamlit minor layout fix */
        </style>
        """,
        unsafe_allow_html=True,
    )


_apply_base_styles()

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

LOCATION_COORDINATES: Dict[str, Tuple[float, float]] = {
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "goa": (15.2993, 74.1240),
    "kochi": (9.9312, 76.2673),
}

LOCATION_ALIASES: Dict[str, str] = {
    "mumbai": "mumbai",
    "bombay": "mumbai",
    "chennai": "chennai",
    "madras": "chennai",
    "goa": "goa",
    "kochi": "kochi",
    "cochin": "kochi",
}

LOCATION_DISPLAY_NAMES: Dict[str, str] = {
    "mumbai": "Mumbai",
    "chennai": "Chennai",
    "goa": "Goa",
    "kochi": "Kochi",
}

NEARBY_RADIUS_DEG = 5.0

THEME_OPTIONS = ("Light", "Dark")
THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "Light": {
        "background": "#f5f7fb",
        "surface": "#ffffff",
        "text": "#0f172a",
        "muted_text": "#475569",
        "accent": "#0f82ff",
        "accent_soft": "#e4f0ff",
    },
    "Dark": {
        "background": "#0f1729",
        "surface": "#111c2f",
        "text": "#f8fafc",
        "muted_text": "#cbd5f5",
        "accent": "#4cc9ff",
        "accent_soft": "#1b2a46",
    },
}

PLACE_RADIUS_DEG = 2.5
AGGREGATION_KEYWORDS: Dict[str, str] = {
    "average": "mean",
    "avg": "mean",
    "mean": "mean",
    "median": "median",
    "max": "max",
    "maximum": "max",
    "min": "min",
    "minimum": "min",
    "count": "count",
}


@lru_cache(maxsize=1)
def _get_geocoder():
    if Nominatim is None:
        return None
    try:
        geolocator = Nominatim(user_agent="floatchat-dashboard", timeout=10)
        if RateLimiter is not None:
            return RateLimiter(geolocator.geocode, min_delay_seconds=1)
        return geolocator.geocode
    except Exception:
        return None


def _ensure_min_span(
    bounds: Tuple[float, float],
    min_span: float,
    hard_limits: Tuple[float, float],
) -> Tuple[float, float]:
    """Expand a (min, max) range to at least `min_span` degrees."""

    lower, upper = bounds
    lower, upper = sorted((float(lower), float(upper)))
    if min_span <= 0:
        return (max(hard_limits[0], lower), min(hard_limits[1], upper))

    span = upper - lower
    if span >= min_span:
        return (max(hard_limits[0], lower), min(hard_limits[1], upper))

    center = (upper + lower) / 2.0
    half_span = min_span / 2.0
    expanded_lower = max(hard_limits[0], center - half_span)
    expanded_upper = min(hard_limits[1], center + half_span)
    return (expanded_lower, expanded_upper)


@st.cache_data(show_spinner=False)
def geocode_place(name: str) -> Optional[Dict[str, Any]]:
    """Return a bounding box + metadata for a named location."""

    name = (name or "").strip()
    if not name:
        return None

    geocode_fn = _get_geocoder()
    if geocode_fn is not None:
        try:
            location = geocode_fn(name)
        except Exception:
            location = None
        if location is not None:
            try:
                lat = float(location.latitude)
                lon = float(location.longitude)
                bbox = location.raw.get("boundingbox") if isinstance(location.raw, dict) else None
            except Exception:
                lat, lon, bbox = None, None, None
            if lat is not None and lon is not None:
                if bbox and len(bbox) == 4:
                    lat_min, lat_max, lon_min, lon_max = map(float, bbox)
                else:
                    lat_min, lat_max = lat - PLACE_RADIUS_DEG, lat + PLACE_RADIUS_DEG
                    lon_min, lon_max = lon - PLACE_RADIUS_DEG, lon + PLACE_RADIUS_DEG
                lat_range = _ensure_min_span(
                    (lat_min, lat_max), PLACE_RADIUS_DEG * 2, (-90.0, 90.0)
                )
                lon_range = _ensure_min_span(
                    (lon_min, lon_max), PLACE_RADIUS_DEG * 2, (-180.0, 180.0)
                )
                return {
                    "name": getattr(location, "address", None) or getattr(location, "raw", {}).get("display_name", name),
                    "lat": lat,
                    "lon": lon,
                    "lat_range": lat_range,
                    "lon_range": lon_range,
                }

    # Fallback to simple HTTP request (without geopy dependency)
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": name, "format": "json", "limit": 1},
            headers={"User-Agent": "floatchat-dashboard"},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json()
        if not results:
            return None
        result = results[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        bbox = result.get("boundingbox")
        if bbox and len(bbox) == 4:
            lat_min, lat_max, lon_min, lon_max = map(float, bbox)
        else:
            lat_min, lat_max = lat - PLACE_RADIUS_DEG, lat + PLACE_RADIUS_DEG
            lon_min, lon_max = lon - PLACE_RADIUS_DEG, lon + PLACE_RADIUS_DEG
        lat_range = _ensure_min_span(
            (lat_min, lat_max), PLACE_RADIUS_DEG * 2, (-90.0, 90.0)
        )
        lon_range = _ensure_min_span(
            (lon_min, lon_max), PLACE_RADIUS_DEG * 2, (-180.0, 180.0)
        )
        return {
            "name": result.get("display_name", name),
            "lat": lat,
            "lon": lon,
            "lat_range": lat_range,
            "lon_range": lon_range,
        }
    except Exception:
        return None


def render_leaflet_map(m: "folium.Map", height: int = 620) -> None:
    """Render a folium map without triggering Streamlit reruns on interaction."""

    try:
        html = m.get_root().render()
    except Exception:
        st.warning("Unable to render Leaflet map.")
        return
    st.components.v1.html(html, height=height, scrolling=False)


def _normalize_theme(value: Optional[str]) -> str:
    if not value:
        return THEME_OPTIONS[0]
    value = value.strip().lower()
    for option in THEME_OPTIONS:
        if option.lower() == value:
            return option
    return THEME_OPTIONS[0]


def _load_theme_preference() -> Tuple[str, Dict[str, List[str]]]:
    """Read persisted theme from query params or session state."""

    query_params_proxy = st.query_params
    query_params = {key: query_params_proxy.get_all(key) for key in query_params_proxy.keys()}
    if "theme" in query_params and query_params["theme"]:
        theme_choice = _normalize_theme(query_params["theme"][0])
    elif "theme" in st.session_state:
        theme_choice = _normalize_theme(st.session_state["theme"])
    else:
        theme_choice = THEME_OPTIONS[0]

    st.session_state.setdefault("theme", theme_choice)
    return theme_choice, query_params


def _persist_theme(theme_choice: str, query_params: Dict[str, List[str]]) -> None:
    """Update session + URL query params so theme survives reloads."""

    st.session_state["theme"] = theme_choice
    updated = {}
    for key, values in query_params.items():
        if key == "theme" or not values:
            continue
        if len(values) == 1:
            updated[key] = values[0]
        else:
            updated[key] = values
    updated["theme"] = theme_choice.lower()
    st.query_params.clear()
    st.query_params.update(updated)


def _apply_theme_styles(theme_choice: str) -> None:
    palette = THEME_PALETTES.get(theme_choice, THEME_PALETTES[THEME_OPTIONS[0]])
    st.markdown(
        f"""
        <style>
          :root {{
            color-scheme: {'dark' if theme_choice == 'Dark' else 'light'};
          }}
          [data-testid="stAppViewContainer"] {{
            background: {palette['background']};
            color: {palette['text']};
          }}
          [data-testid="stSidebar"] {{
            background: {palette['surface']};
            color: {palette['text']};
          }}
          [data-testid="stSidebar"] * {{ color: inherit; }}
          .stMarkdown p, .stMarkdown li {{ color: {palette['muted_text']}; }}
          div[data-testid="stMetric"] {{
            background: {palette['surface']};
            border-radius: 14px;
            padding: 0.75rem 1rem;
            border: 1px solid {palette['accent_soft']};
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
          }}
          div[data-testid="stMetric"] label {{ color: {palette['muted_text']}; }}
          div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{ color: {palette['text']}; }}
          .quick-chip {{
            background: {palette['accent_soft']};
            border-radius: 999px;
            color: {palette['accent']};
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.75rem;
            font-size: 0.8rem;
            margin: 0.2rem 0.4rem 0.2rem 0;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

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


PLACE_KEYWORDS = ("near", "around", "close to", "in", "at")


def _extract_place_bbox(text: str) -> Optional[Tuple[Tuple[float, float], Tuple[float, float], str]]:
    """Look for named places (e.g., 'near Mumbai') and geocode them."""

    cleaned = text.lower()
    for keyword in PLACE_KEYWORDS:
        pattern = rf"{keyword}\s+([a-z][a-z\s]+)"
        for match in re.finditer(pattern, cleaned, flags=re.IGNORECASE):
            candidate = match.group(1)
            candidate = re.split(r"[,.;]|\b(for|during|between|within|where|with|and|on|by|to|of|that|which|when)\b", candidate)[0]
            candidate = candidate.strip().strip(",.;:")
            if not candidate or any(char.isdigit() for char in candidate):
                continue
            if candidate.lower() in MONTH_NAME_TO_NUM:
                continue
            # Avoid generic words that are unlikely to be locations
            if candidate.lower() in {"march", "april", "may", "week", "month", "year"}:
                continue
            place_info = geocode_place(candidate)
            if place_info:
                lat_range = place_info.get("lat_range")
                lon_range = place_info.get("lon_range")
                name = place_info.get("name", candidate.title())
                if lat_range and lon_range:
                    return lat_range, lon_range, name
    return None


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

    place_bbox = _extract_place_bbox(lower)
    if place_bbox:
        lat_range, lon_range, place_name = place_bbox
        if "lat_range" not in filters:
            filters["lat_range"] = lat_range
        if "lon_range" not in filters:
            filters["lon_range"] = lon_range
        filters["place_label"] = place_name
        filters.setdefault("wants_map", True)

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

    for keyword, agg in AGGREGATION_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lower):
            filters["aggregation"] = agg
            break

    if any(token in lower for token in (" map", "show ", "plot", "where are", "near")):
        filters.setdefault("wants_map", True)

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

    if filters.get("place_label"):
        applied.append(f"near {filters['place_label']}")

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


def _infer_map_view(df: pd.DataFrame) -> Tuple[Dict[str, float], float]:
    """Return a reasonable map center + zoom for the sample points."""

    lat_min = float(df["latitude"].min())
    lat_max = float(df["latitude"].max())
    lon_min = float(df["longitude"].min())
    lon_max = float(df["longitude"].max())

    center = {
        "lat": (lat_min + lat_max) / 2.0,
        "lon": (lon_min + lon_max) / 2.0,
    }

    span = max(lat_max - lat_min, lon_max - lon_min)
    if span <= 0.25:
        zoom = 9
    elif span <= 1:
        zoom = 7
    elif span <= 3:
        zoom = 5
    elif span <= 8:
        zoom = 4
    elif span <= 20:
        zoom = 3
    else:
        zoom = 1.5

    return center, zoom


def _normalize_location_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", name).lower()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _match_location_key(name: str) -> Optional[str]:
    normalized = _normalize_location_name(name)
    if not normalized:
        return None

    for alias, canonical in LOCATION_ALIASES.items():
        if normalized == alias or normalized.startswith(f"{alias} "):
            return canonical

    return None


def resolve_location(name: str) -> Optional[Tuple[float, float]]:
    """Map a known coastal city name to coordinates."""

    key = _match_location_key(name)
    if key is None:
        return None
    return LOCATION_COORDINATES.get(key)


def _location_display_name(name: str) -> str:
    key = _match_location_key(name)
    if key and key in LOCATION_DISPLAY_NAMES:
        return LOCATION_DISPLAY_NAMES[key]
    return name.strip().title() or "the requested location"


def floats_near_location(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    radius_deg: float = NEARBY_RADIUS_DEG,
) -> pd.DataFrame:
    """Filter floats that sit within ~radius_deg degrees (~111 km/deg) of the location."""

    if df.empty or not {"latitude", "longitude"}.issubset(df.columns):
        return df.iloc[0:0]

    latitudes = pd.to_numeric(df["latitude"], errors="coerce")
    longitudes = pd.to_numeric(df["longitude"], errors="coerce")
    valid_mask = latitudes.notna() & longitudes.notna()

    if not bool(valid_mask.any()):
        return df.iloc[0:0]

    valid_df = df.loc[valid_mask].copy()
    latitudes_rad = np.radians(latitudes[valid_mask].to_numpy())
    longitudes_rad = np.radians(longitudes[valid_mask].to_numpy())

    lat0 = np.radians(lat)
    lon0 = np.radians(lon)

    dlat = latitudes_rad - lat0
    dlon = longitudes_rad - lon0

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat0) * np.cos(latitudes_rad) * np.sin(dlon / 2.0) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    earth_radius_km = 6371.0
    distances_km = earth_radius_km * c

    radius_km = radius_deg * 111.0
    within_mask = distances_km <= radius_km

    nearby_df = valid_df.loc[within_mask].copy()
    if nearby_df.empty:
        return nearby_df

    nearby_df.loc[:, "distance_km"] = distances_km[within_mask]
    return nearby_df


def plot_nearby_floats(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    name: str,
    template: str,
) -> Optional[go.Figure]:
    """Build a Mapbox scatter plot centred on the requested location."""

    if df.empty or not {"latitude", "longitude"}.issubset(df.columns):
        return None

    map_style = st.session_state.get("map_style", MAP_STYLES_LIGHT[0])
    hover_fields = [
        c
        for c in ("platform_number", "date", "distance_km")
        if c in df.columns
    ]

    scatter_kwargs: Dict[str, Any] = {
        "lat": "latitude",
        "lon": "longitude",
        "hover_data": hover_fields if hover_fields else None,
        "template": template,
        "height": 420,
        "title": f"ARGO floats near {name}",
    }
    if "distance_km" in df.columns:
        scatter_kwargs.update(
            {
                "color": "distance_km",
                "color_continuous_scale": "Teal",
            }
        )

    fig = px.scatter_mapbox(df, **scatter_kwargs)

    fig.update_traces(marker=dict(size=10, opacity=0.8))
    fig.update_layout(
        mapbox=dict(style=map_style, center=dict(lat=lat, lon=lon), zoom=5),
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h"),
    )

    fig.add_scattermapbox(
        lat=[lat],
        lon=[lon],
        mode="markers",
        marker=dict(size=16, color="#ff6b6b", symbol="star"),
        name=f"{name} centre",
        hoverinfo="skip",
    )

    return fig


def extract_near_location(query: str) -> Optional[str]:
    match = re.search(r"near\s+([a-zA-Z\s]+)", query, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def build_map_figure(
    df: pd.DataFrame,
    template: str,
    map_style: Optional[str] = None,
    max_points: int = 5000,
) -> Optional[go.Figure]:
    """Create a scatter map for chat responses."""

    if not {"latitude", "longitude"}.issubset(df.columns):
        return None

    clean = df.dropna(subset=["latitude", "longitude"])
    if clean.empty:
        return None

    sample = sampled(clean, min(max_points, len(clean)))
    map_style = map_style or st.session_state.get("map_style", MAP_STYLES_LIGHT[0])

    hover_fields = [
        c
        for c in ("platform_number", "date", "temp", "psal", "pres")
        if c in sample.columns
    ]
    fig = px.scatter_mapbox(
        sample,
        lat="latitude",
        lon="longitude",
        hover_data=hover_fields if hover_fields else None,
        template=template,
        height=420,
        zoom=2,
    )

    center, zoom = _infer_map_view(sample)
    fig.update_layout(
        mapbox=dict(style=map_style, center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


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
        "map_figure": None,
        "float_id": None,
        "reply": "",
        "aggregation": None,
    }

    variable = filters.get("variable")
    aggregation = filters.get("aggregation")

    if aggregation and row_count > 0:
        if variable and variable in filtered_df.columns:
            series = filtered_df[variable].dropna()
            if not series.empty:
                agg_value: Optional[float]
                if aggregation == "count":
                    agg_value = float(series.count())
                else:
                    try:
                        agg_value = float(getattr(series, aggregation)())
                    except Exception:
                        agg_value = None

                if agg_value is not None:
                    result["aggregation"] = {
                        "type": aggregation,
                        "variable": variable,
                        "value": agg_value,
                    }
                    summary = _summarize_filters(applied_filters)
                    if aggregation == "count":
                        value_text = f"{int(agg_value):,}"
                    else:
                        value_text = f"{agg_value:.3f}" if abs(agg_value) < 1000 else f"{agg_value:,.2f}"
                    agg_label = aggregation.capitalize()
                    result["reply"] = f"{agg_label} {variable.upper()} = {value_text}.\n{summary}".strip()
        elif aggregation == "count":
            result["aggregation"] = {"type": aggregation, "variable": None, "value": float(row_count)}
            summary = _summarize_filters(applied_filters)
            result["reply"] = f"Count = {row_count:,}.\n{summary}".strip()

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

    if filters.get("wants_map") and row_count > 0:
        map_fig = build_map_figure(filtered_df, template)
        if map_fig is not None:
            result["map_figure"] = map_fig

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
        if isinstance(df["date"].dtype, pd.DatetimeTZDtype):
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


@st.cache_data
def _export_bytes(df: pd.DataFrame) -> Dict[str, bytes]:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    ascii_bytes = df.head(50_000).to_csv(sep=" ", index=False).encode("utf-8")

    pq_buf = io.BytesIO()
    df.to_parquet(pq_buf, index=False)
    parquet_bytes = pq_buf.getvalue()

    xlsx_buf = io.BytesIO()
    df.head(1_000_000).to_excel(xlsx_buf, index=False, sheet_name="ArgoData")
    excel_bytes = xlsx_buf.getvalue()

    netcdf_bytes: Optional[bytes] = None
    if xr is not None:
        df_nc = df.head(100_000).copy()
        for col in df_nc.select_dtypes(include=["category", "object"]).columns:
            df_nc[col] = df_nc[col].astype(str)

        try:
            nc_buf = io.BytesIO()
            xr.Dataset.from_dataframe(df_nc).to_netcdf(nc_buf)
            netcdf_bytes = nc_buf.getvalue()
        except Exception:
            netcdf_bytes = None

    return {
        "csv": csv_bytes,
        "ascii": ascii_bytes,
        "parquet": parquet_bytes,
        "excel": excel_bytes,
        "netcdf": netcdf_bytes,
    }


@st.cache_data
def _profile_statistics(df: pd.DataFrame) -> Dict[str, pd.Series]:
    if df.empty:
        return {}

    grp = df.groupby("pres")
    mean_t = grp["temp"].mean()
    std_t = grp["temp"].std()
    mean_s = grp["psal"].mean()
    std_s = grp["psal"].std()

    return {
        "mean_temp": mean_t,
        "std_temp": std_t,
        "mean_sal": mean_s,
        "std_sal": std_s,
    }

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

initial_theme, query_params = _load_theme_preference()
map_options = MAP_STYLES_LIGHT + MAP_STYLES_DARK
default_map_from_theme = MAP_STYLES_LIGHT[0] if initial_theme == "Light" else MAP_STYLES_DARK[0]
st.session_state.setdefault("map_style", default_map_from_theme)

with st.sidebar:
    st.header("📂 Data Source")
    names = [p.name for p in parquets]
    default_idx = names.index(DEFAULT_PARQUET) if DEFAULT_PARQUET in names else 0
    file_choice = st.selectbox("Select a parquet", parquets, index=default_idx)
    st.caption(f"Selected: {file_choice.name}")

    st.divider()
    st.header("🎨 Theme")
    theme = st.radio("Theme", THEME_OPTIONS, horizontal=True, index=THEME_OPTIONS.index(initial_theme))
    st.caption("Choose your preferred look — remembered next time you return ✨")

    st.divider()
    st.header("🗺️ Map View")
    focus_india = st.checkbox("🇮🇳 Focus India (default)", value=True)
    world_view = st.checkbox("🌍 World view", value=False)

    # Reset map style when switching between light/dark palettes for readability
    map_style_default = MAP_STYLES_LIGHT[0] if theme == "Light" else MAP_STYLES_DARK[0]
    if theme == "Light" and st.session_state.get("map_style") in MAP_STYLES_DARK:
        st.session_state["map_style"] = map_style_default
    elif theme == "Dark" and st.session_state.get("map_style") in MAP_STYLES_LIGHT:
        st.session_state["map_style"] = map_style_default

    map_style = st.selectbox(
        "Map style",
        map_options,
        index=map_options.index(st.session_state.get("map_style", map_style_default)),
        key="map_style",
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


if theme != st.session_state.get("theme") or query_params.get("theme", [None])[0] != theme.lower():
    _persist_theme(theme, query_params)

_apply_theme_styles(theme)

plotly_template = PLOTLY_TEMPLATES[theme]
map_style_default = MAP_STYLES_LIGHT[0] if theme == "Light" else MAP_STYLES_DARK[0]

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
# Quick insights & highlights
# -----------------------------
st.markdown("### 🔍 Quick Insights")
insight_cols = st.columns((2, 1))

with insight_cols[0]:
    if "date" in df.columns and len(df) > 0:
        timeline = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not timeline.empty:
            monthly = (
                timeline.dt.to_period("M")
                .value_counts()
                .sort_index()
                .rename_axis("month")
                .reset_index(name="profiles")
            )
            monthly["month"] = monthly["month"].astype(str)
            timeline_fig = px.area(
                monthly,
                x="month",
                y="profiles",
                labels={"month": "Month", "profiles": "Profiles"},
                template=plotly_template,
            )
            timeline_fig.update_traces(line_color="#3b82f6")
            timeline_fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(timeline_fig, use_container_width=True)
        else:
            st.info("No valid timestamps available for timeline insights.")
    else:
        st.info("Add a dataset with dates to unlock temporal insights.")

with insight_cols[1]:
    highlight_lines: List[str] = []
    if "temp" in df.columns and not df["temp"].dropna().empty:
        highlight_lines.append(f"🌡️ Avg Temp: {df['temp'].dropna().mean():.1f} °C")
    if "psal" in df.columns and not df["psal"].dropna().empty:
        highlight_lines.append(f"🧂 Avg Salinity: {df['psal'].dropna().mean():.2f} PSU")
    if "pres" in df.columns and not df["pres"].dropna().empty:
        highlight_lines.append(f"📏 Max Depth: {df['pres'].dropna().max():,.0f} dbar")

    if highlight_lines:
        st.markdown("#### Snapshot")
        for line in highlight_lines:
            st.markdown(f"- {line}")

    chips_html = []
    for column_name in ["ocean", "platform_type", "data_mode"]:
        if column_name in df.columns and not df[column_name].dropna().empty:
            top_values = (
                df[column_name]
                .dropna()
                .astype(str)
                .value_counts()
                .head(4)
                .items()
            )
            pretty_name = column_name.replace("_", " ").title()
            chips_html.append(f"<p><strong>{pretty_name}</strong><br>")
            chips_html.append(
                "".join(
                    f"<span class='quick-chip'>{label} · {count:,}</span>" for label, count in top_values
                )
            )
            chips_html.append("</p>")

    if chips_html:
        st.markdown("".join(chips_html), unsafe_allow_html=True)

# Precompute commonly reused slices for snappier tab changes
latlon_available = {"latitude", "longitude"}.issubset(df.columns)
latlon_df = df[["latitude", "longitude"]].dropna() if latlon_available else pd.DataFrame()
leaflet_points = (
    sampled(latlon_df, min(max_points * 2, 50_000)) if not latlon_df.empty else pd.DataFrame()
)
cesium_points = (
    sampled(latlon_df, min(max_points, 10_000)) if not latlon_df.empty else pd.DataFrame()
)

profile_cols_available = {"psal", "temp", "pres"}.issubset(df.columns)
profile_core = df[["psal", "temp", "pres"]].dropna() if profile_cols_available else pd.DataFrame()
ts_subset = sampled(profile_core, 5_000) if not profile_core.empty else profile_core
profile_stats = _profile_statistics(profile_core) if not profile_core.empty else {}

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

        base_fig = px.scatter_map(
            plot_df,
            lat="latitude",
            lon="longitude",
            hover_name=hover_col,
            color="ocean" if "ocean" in plot_df.columns else None,
            height=620,
            zoom=3 if focus_india and not world_view else 1.5,
            center=dict(lat=INDIA_CENTER[0], lon=INDIA_CENTER[1]) if focus_india and not world_view else dict(lat=0, lon=0),
            map_style=map_style,
            template=plotly_template,
        )
        base_fig.update_layout(
            map=dict(style=map_style),
            mapbox=dict(style=map_style),
            margin=dict(l=0, r=0, t=0, b=0),
        )

        # Add live layers
        layers = []
        if show_noaa:
            noaa_df = load_noaa_buoys()
            if not noaa_df.empty:
                layers.append(px.scatter_map(
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

                layers.append(px.scatter_map(
                    incois_hover, lat="latitude", lon="longitude",
                    hover_name=hover_field, color_discrete_sequence=["green"]
                ).data[0])

        fig = go.Figure(data=base_fig.data + tuple(layers))
        fig.update_layout(
            map=dict(style=map_style),
            mapbox=dict(style=map_style),
            margin=dict(l=0, r=0, t=0, b=0),
            template=plotly_template,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No lat/lon columns to plot.")

# -----------------------------
# Leaflet Map (fast clustering)
# -----------------------------
with tab_leaflet:
    st.subheader("🗺️ Leaflet (folium + clustering)")
    if folium is None or MarkerCluster is None:
        st.warning("Install leaflet support:  pip install folium")
    elif latlon_available and len(latlon_df) > 0:
        ldf = leaflet_points
        if ldf.empty:
            st.info("No lat/lon points available for the current filters.")
        else:
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

            if HeatMap is not None and st.checkbox("Heatmap (approx)"):
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

            render_leaflet_map(m)
    else:
        st.info("No lat/lon columns to plot.")

# -----------------------------
# Cesium 3D Globe
# -----------------------------
with tab_cesium:
    st.subheader("🌐 Cesium 3D Globe")
    st.caption("Tip: set CESIUM_ION_TOKEN env variable for premium imagery/terrain.")
    cesium_token = os.getenv("CESIUM_ION_TOKEN", "")

    cdf = cesium_points
    if cdf.empty:
        st.info("No latitude/longitude data available for the 3D globe.")
    else:
        points_js = [
            f'{{ "lat": {float(r.latitude):.6f}, "lon": {float(r.longitude):.6f} }}'
            for r in cdf.itertuples(index=False)
        ]

        html = f"""
        <div id=\"cesiumContainer\" style=\"width:100%;height:620px;\"></div>
        <script src=\"https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Cesium.js\"></script>
        <link href=\"https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Widgets/widgets.css\" rel=\"stylesheet\">
        <script>
          window.CESIUM_BASE_URL = \"https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/\";
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
    if profile_cols_available and len(profile_core) > 0:
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
        if ts_subset.empty:
            st.info("Not enough temperature/salinity samples to draw a TS diagram.")
        else:
            fig_ts = px.scatter(
                ts_subset,
                x="psal",
                y="temp",
                color="pres",
                color_continuous_scale="Viridis",
                labels={"psal": "Salinity (PSU)", "temp": "Temperature (°C)", "pres": "Pressure (dbar)"},
                template=plotly_template,
            )
            st.plotly_chart(fig_ts, use_container_width=True)

        st.markdown("### 📉 Mean Vertical Profiles (±1σ)")
        if not profile_stats:
            st.info("Mean profile statistics are unavailable for the current selection.")
        else:
            mean_t = profile_stats["mean_temp"]
            std_t = profile_stats["std_temp"]
            mean_s = profile_stats["mean_sal"]
            std_s = profile_stats["std_sal"]

            fig_mp = go.Figure()
            fig_mp.add_trace(go.Scatter(x=mean_t, y=mean_t.index, name="Mean Temp", mode="lines", line=dict(color="red")))
            fig_mp.add_trace(go.Scatter(x=(mean_t + std_t), y=mean_t.index, name="Temp +1σ", mode="lines", line=dict(color="red", dash="dot")))
            fig_mp.add_trace(go.Scatter(x=(mean_t - std_t), y=mean_t.index, name="Temp -1σ", mode="lines", line=dict(color="red", dash="dot"),
                                        fill="tonexty", fillcolor="rgba(255,0,0,0.12)"))
            fig_mp.add_trace(go.Scatter(x=mean_s, y=mean_s.index, name="Mean Sal", mode="lines", line=dict(color="blue")))
            fig_mp.add_trace(go.Scatter(x=(mean_s + std_s), y=mean_s.index, name="Sal +1σ", mode="lines", line=dict(color="blue", dash="dot")))
            fig_mp.add_trace(go.Scatter(x=(mean_s - std_s), y=mean_s.index, name="Sal -1σ", mode="lines", line=dict(color="blue", dash="dot"),
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
    with st.spinner("Preparing download files..."):
        export_payloads = _export_bytes(df)

    st.download_button(
        "⬇️ CSV (full)",
        data=export_payloads["csv"],
        file_name=f"{file_choice.stem}_filtered.csv",
        mime="text/csv",
    )

    st.download_button(
        "⬇️ ASCII (first 50k)",
        data=export_payloads["ascii"],
        file_name=f"{file_choice.stem}_filtered.txt",
        mime="text/plain",
    )

    st.download_button(
        "⬇️ Parquet (full)",
        data=export_payloads["parquet"],
        file_name=f"{file_choice.stem}_filtered.parquet",
        mime="application/octet-stream",
    )

    st.download_button(
        "⬇️ Excel (≤1M rows)",
        data=export_payloads["excel"],
        file_name=f"{file_choice.stem}_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if xr is None:
        st.info("Install xarray to enable NetCDF export:  pip install xarray netcdf4")
    elif export_payloads["netcdf"] is None:
        st.warning("⚠️ NetCDF export unavailable for this dataset or conversion failed.")
    else:
        st.download_button(
            "⬇️ NetCDF (first 100k)",
            data=export_payloads["netcdf"],
            file_name=f"{file_choice.stem}_filtered.nc",
            mime="application/octet-stream",
        )
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

        location_fragment = extract_near_location(query)
        if location_fragment:
            display_name = _location_display_name(location_fragment)
            assistant_text = ""
            map_figure: Optional[go.Figure] = None
            with st.spinner(f"📍 Searching floats near {display_name}..."):
                coords = resolve_location(location_fragment)
                if coords is None:
                    assistant_text = (
                        f"I couldn't resolve \"{location_fragment}\" to a supported coastal city yet. "
                        "Try Mumbai, Chennai, Goa, or Kochi."
                    )
                else:
                    lat, lon = coords
                    nearby_df = floats_near_location(df_full, lat, lon, radius_deg=NEARBY_RADIUS_DEG)
                    if nearby_df.empty:
                        assistant_text = (
                            f"I couldn't find any floats within ~{int(NEARBY_RADIUS_DEG * 111)} km of {display_name} "
                            "in the cached dataset."
                        )
                    else:
                        map_figure = plot_nearby_floats(nearby_df, lat, lon, display_name, plotly_template)
                        float_count = (
                            nearby_df["platform_number"].nunique()
                            if "platform_number" in nearby_df.columns
                            else None
                        )
                        record_count = len(nearby_df)
                        radius_km = int(NEARBY_RADIUS_DEG * 111)
                        if float_count is not None:
                            assistant_text = (
                                f"Found {float_count:,} unique floats ({record_count:,} records) within ~{radius_km} km of {display_name}. "
                                "Here's a map you can explore."
                            )
                        else:
                            assistant_text = (
                                f"Found {record_count:,} float records within ~{radius_km} km of {display_name}. "
                                "Here's a map you can explore."
                            )
                        if map_figure is None:
                            assistant_text += (
                                "\n(I couldn't render the map because latitude/longitude columns are missing.)"
                            )

            assistant_chat = st.chat_message("assistant")
            st.session_state["messages"].append({"role": "assistant", "content": assistant_text})
            assistant_chat.write(assistant_text)
            if map_figure is not None:
                assistant_chat.plotly_chart(map_figure, use_container_width=True)
            return

        with st.spinner("⚙️ Running query pipeline..."):
            result = run_query_pipeline(query, df_full, plotly_template)

        assistant_text = result.get("reply") or "I couldn't interpret that request with the available data."
        figure = result.get("figure")
        map_figure = result.get("map_figure")
        fallback_text: Optional[str] = None
        show_no_match_notice = False

        if figure is None:
            if result.get("row_count", 0) == 0 and result.get("applied_filters"):
                show_no_match_notice = True
                fallback_text = hybrid_fallback_answer(query)
            elif not result.get("applied_filters"):
                fallback_response = hybrid_fallback_answer(query)
                if fallback_response:
                    assistant_text = fallback_response
                    fallback_text = None
                    figure = None

        assistant_chat = st.chat_message("assistant")
        st.session_state["messages"].append({"role": "assistant", "content": assistant_text})
        assistant_chat.write(assistant_text)

        if figure is not None:
            assistant_chat.plotly_chart(figure, use_container_width=True)

        if map_figure is not None:
            assistant_chat.plotly_chart(map_figure, use_container_width=True)

        if show_no_match_notice:
            warning_text = "⚠️ Sorry, no matching profiles in dataset."
            st.session_state["messages"].append({"role": "assistant", "content": warning_text})
            st.chat_message("assistant").write(warning_text)

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