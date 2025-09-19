# 🌊 FloatChat — Conversational Explorer for ARGO Floats

FloatChat is a Streamlit application that turns the ARGO float archive into an interactive, judge-ready demo. It combines rich visual exploration, lightweight analytics, and a natural-language assistant tailored for the Indian Ocean focus area.

## 🚀 Feature Snapshot

- **Multiple exploration tabs** – Jump between Plotly maps, a static Leaflet view, a Cesium 3D globe, depth profiles, Hovmöller diagrams, float-to-float comparisons, raw tables, and export utilities without leaving the page.
- **Live overlays and quick stats** – Blend cached float data with NOAA buoy metadata, INCOIS demo moorings, and dataset summaries (timeline, quick chips, profile snapshots) directly inside the dashboard.
- **Theme + map controls** – Persisted light/dark themes, India-first or global map focus, and curated Mapbox styles keep the UI responsive on repeated judge walkthroughs.
- **Chat-driven insights** – Natural-language queries understand places, coordinates, time windows, statistics, comparisons, and nearest-float lookups. Matching results trigger inline charts, map snippets, and aggregated summaries.
- **Hybrid fallback** – When cached data cannot answer a question, FloatChat can enrich replies with DuckDuckGo snippets and—if an Ollama model is running—locally generated context-aware answers.

## 🧪 Try These Queries

Use the **💬 Chat** tab or the quick buttons sourced from `app/example_queries.json`:

- “Show me ARGO floats near Mumbai.”
- “Average PSAL of the ocean near Odisha in March 2023.”
- “Plot floats around Lakshadweep on the map.”
- “Compare BGC parameters in the Arabian Sea for the last 6 months.”
- “Show me salinity profiles near the equator in March 2023.”

## 📁 Repository Layout

```
app/
  dashboard.py          # Streamlit entry point orchestrating UI + chat
  example_queries.json  # Pre-baked prompts exposed in the chat tab
  converter.py          # NetCDF ➜ Parquet helper for offline preparation
requirements.txt        # Runtime dependencies (Streamlit, Plotly, DDGS, Ollama…)
scripts/
  datasets/             # Demo assets (e.g. INCOIS buoy metadata)
  ...                   # Data ingestion helpers referenced in roadmap
```

FloatChat expects float profiles to be cached in `data_cache/`. The default configuration looks for `argo_index_indian.parquet`, but any Parquet file with the normalised schema works.

## ⚙️ Getting Started

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Prepare float data**
   - Place one or more Parquet files inside `data_cache/`.
   - Use `app/converter.py` (or your own ETL) to turn NetCDF drops into the slimmed-down Parquet schema with columns such as `time`, `date`, `latitude`, `longitude`, `temp`, `psal`, and `pres`.
3. **Run the dashboard**
   ```bash
   streamlit run app/dashboard.py
   ```
4. **(Optional) Enable the hybrid fallback**
   - Install [Ollama](https://ollama.com/) locally and pull a model such as `mistral`.
   - Optionally set `OLLAMA_MODEL` via `.env` or your shell. Without an Ollama service, web snippets from DuckDuckGo are still displayed when data filters return no rows.

## 🧠 Query Understanding Pipeline

The chat assistant combines rule-based parsing with cached analytics:

1. **Alias normalisation** – Temperature, salinity, oxygen, and other oceanography keywords are mapped to canonical column names.
2. **Spatial detection** – Named places (via OpenStreetMap geocoding), latitude/longitude ranges, and “near lat, lon” phrases translate into bounding boxes plus target points for distance searches.
3. **Temporal parsing** – Absolute dates (`March 2023`), ranges, and “last N months/weeks/days” filters constrain the Parquet frame.
4. **Intent extraction** – Statistical verbs (`average`, `count`, `median`, etc.), comparison keywords, and diagram hints decide whether to build aggregations, depth profiles, float comparisons, nearest-float tables, or Hovmöller heatmaps.
5. **Result rendering** – Matching rows power Plotly charts, inline summaries, and chat replies. When nothing matches, FloatChat surfaces external context and reminds users how to align questions with the cached dataset.

## 🏛️ System Architecture

FloatChat follows a modular architecture that keeps data access, parsing, and presentation concerns isolated:

- **Streamlit front-end** – Hosts the multi-tab experience, session state, and chat interface.
- **Data agent** – Loads cached Parquet files, normalises schemas, and hydrates quick stats used across tabs.
- **Filter/intent agent** – Parses natural-language prompts, geocodes locations, and compiles temporal/spatial filters.
- **Visualisation agent** – Renders Plotly, Folium, and Cesium components alongside specialised builders (profiles, comparisons, Hovmöller diagrams).
- **Chat agent** – Orchestrates the query pipeline, picks the right visual, and escalates to hybrid LLM/web fallbacks when data is missing.
- **Integration layer** – Coordinates sidebar controls, theme persistence, and data exports while sharing cached slices between tabs.

These layers communicate through shared session state and cached DataFrame slices, ensuring that insights discovered via chat mirror what the visual tabs display.

## 🔁 Workflow Flowchart

```text
User Prompt ─┐
             │
             ▼
      Intent & Filter Parser
             │
             ▼
     DataFrame Filter Engine
             │
     ┌───────┴─────────┐
     │                 │
     ▼                 ▼
Chart Builders   Nearest/LLM Fallbacks
 (Profiles,          │
  Comparison,        ▼
  Hovmöller)   Response Composer
             │
             ▼
      Chat + Tab Output
```

## 🔍 Known Limitations & Roadmap

- **Local-first data** – Parquet caches remain the primary data source; incremental refresh, DuckDB/Postgres sinks, and ERDDAP pull automation are future upgrades.
- **Optional dependencies** – Cesium, Folium, geopy, and Ollama integrations are wrapped in graceful fallbacks. Install the optional packages for the best experience.
- **Advanced analytics** – Multi-variable anomalies, climatology comparisons, and richer trend analysis are earmarked for post-demo iterations.
- **Geocoding resilience** – Live OpenStreetMap geocoding is used when no cache is available. Bundling an offline gazetteer is on the backlog.

## 🤝 Contributing

Contributions are welcome! Please format your code, update documentation for new datasets or dependencies, and share reproducible steps when filing issues.

## 📄 License

MIT — see [`LICENSE`](LICENSE).
