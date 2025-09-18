# 🌊 FloatChat — Project Agents & Roadmap Snapshot

The Streamlit dashboard is organised into lightweight “agents” that each own a part of the user journey. The sections below capture what ships today and what remains on deck for future iterations.

## 🔹 Data Agent
- Loads cached ARGO Parquet files from `data_cache/` and applies schema normalisation (`time`, `date`, `latitude`, `longitude`, `temp`, `psal`, `pres`, …).
- Downcasts numeric/text columns to keep memory usage predictable even with ~50k profiles.
- Surfaces dataset snapshots (timeline histogram, quick chips, profile stats) for at-a-glance situational awareness.

### Future scope
- Incremental refresh from ERDDAP/FTP and scripted NetCDF ➜ Parquet pipelines.
- Optional connectors for DuckDB/Postgres once multi-dataset comparisons arrive.

## 🔹 Filter Agent
- Applies geospatial, temporal, and sampling filters across both sidebar widgets and the chat pipeline.
- Recognises **named places** (via OpenStreetMap), latitude/longitude ranges, and “near lat, lon” syntax.
- Detects statistical intents (`average`, `median`, `count`, …) and chart hints (“map”, “profile”) to power inline summaries.

### Future scope
- Multi-variable comparisons (e.g., “difference between temperature and salinity”).
- Polygon uploads / EEZ presets for more precise geographic scoping.

## 🔹 Visualisation Agent
- Powers the multi-tab experience: Plotly map, static Leaflet view, Cesium 3D globe, depth profiles, Hovmöller heatmaps, float comparisons, raw tables, and export workflows.
- Adds live NOAA buoy + INCOIS demo overlays and persists user theme/map preferences between sessions.
- Provides graceful fallbacks when optional libraries (Cesium, Folium, geopy) are absent.

### Future scope
- Persist camera states per tab and surface anomaly layers when climatology data is available.
- Bundle an offline geocoding cache to reduce reliance on live OpenStreetMap calls.

## 🔹 Chat Agent
- Parses free-form queries, applies the filter agent, and returns aggregated statistics, profile charts, or map snippets.
- Falls back to DuckDuckGo snippets and local Ollama completions when cached data cannot satisfy a request.
- Shares the applied filters in plain English so users can refine follow-up prompts quickly.

### Future scope
- Integrate hosted LLMs + retrieval pipelines (FAISS/Chroma) for richer responses.
- Support streaming answers and inline citations for hybrid (data + web) replies.

## 🔹 Integration Agent
- `app/dashboard.py` orchestrates sidebar controls, caching, theme persistence, and tab routing.
- `example_queries.json` feeds the quick-start chat buttons showcased in demos.
- Scripts inside `scripts/` house prototype ingestion utilities and demo datasets.

### Future scope
- Persist lightweight chat transcripts alongside export bundles.
- Add health checks + UI nudges for external dependencies (Ollama, geocoding, live feeds).

---
**Reminder:** Launch the demo with `streamlit run app/dashboard.py` for the full experience.
