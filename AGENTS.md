# 🌊 FloatChat — Project Agents & Roadmap Snapshot

This document summarises the modules that power the Streamlit dashboard and highlights new additions introduced in this iteration.

## 🔹 Data Agent
- Loads cached ARGO Parquet files from `data_cache/`.
- Normalises column names (`time`, `date`, `latitude`, `longitude`, `temp`, `psal`, `pres`).
- Downcasts numeric columns for memory efficiency.

### Future scope
- Support incremental refresh of the cache from ERDDAP/FTP without manual scripts.
- Offer a plug-in layer for alternative storage (DuckDB, Postgres) once datasets grow.

## 🔹 Filter Agent
- Applies geospatial, temporal, and sampling filters.
- Understands **named places** via OpenStreetMap geocoding (e.g., “near Mumbai”).
- Detects statistical intents (`average`, `median`, `count`, …) from chat queries.

### Future scope
- Expand to multi-variable comparisons (e.g., “difference between temp and psal”).
- Allow polygon uploads or EEZ presets beyond bounding boxes.

## 🔹 Visualisation Agent
- Plotly scatter maps with optional NOAA/INCOIS overlays.
- Leaflet map rendered as a static component to stop unwanted Streamlit reloads.
- Cesium 3D globe, TS diagrams, and profile plots.

### Future scope
- Persist user-selected map styles & camera views per session.
- Add anomaly layers (e.g., climatology deviations) when data becomes available.

## 🔹 Chat Agent
- Parses free-form queries, applies filters, and returns:
  - Aggregated statistics.
  - Optional profile or map plots.
- Falls back to DuckDuckGo + local Ollama when data filters return no rows.

### Future scope
- Integrate hosted LLMs and retrieval pipelines (FAISS/Chroma) for richer answers.
- Provide streaming responses and source citation for hybrid answers.

## 🔹 Integration Agent
- Streamlit `dashboard.py` orchestrates sidebar controls, caching, and tab layout.
- Example queries in `example_queries.json` showcase named-place and aggregation requests.

### Future scope
- Persist lightweight session summaries for exporting chat transcripts.
- Add health checks for external services (Ollama, geocoding) with graceful UI notices.

---
**Reminder:** Run Streamlit via `streamlit run app/dashboard.py` for the complete experience.
