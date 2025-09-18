# 🌊 FloatChat — Conversational Explorer for ARGO Floats

FloatChat is a Streamlit dashboard that lets you explore ARGO float profiles with natural language. The current build focuses on a smooth judge-ready demo for Indian Ocean datasets, quick geospatial insights, and a chat assistant that understands place names and time windows.

## 🚀 Highlights (Current State)

- **Map stability fix** – Leaflet maps now render as static components, so panning/zooming no longer forces the entire Streamlit app to reload.
- **Named-place understanding** – Queries such as “show me floats near Mumbai” or “average PSAL near Odisha in March 2023” are geocoded via OpenStreetMap and translated into latitude/longitude filters automatically.
- **On-demand summaries** – Ask for statistics like average/median/min/max/count for key variables (temperature, salinity, etc.) and see the result along with optional profile plots and maps.
- **Live overlays** – Toggle NOAA buoy stations and INCOIS demo moorings on both Plotly and Leaflet maps.
- **Hybrid chat fallback** – When the local dataset cannot satisfy a request, FloatChat surfaces web snippets and (if available) responds via a local Ollama model.

## 🧪 Try These Queries

Paste these into the chat tab to experience the new parsing logic:

- “Show me ARGO floats near Mumbai.”
- “Average PSAL of the ocean near Odisha in March 2023.”
- “Plot floats around Lakshadweep on the map.”
- “Show me salinity profiles near the equator in March 2023.”

## 📁 Project Layout

```
app/
  dashboard.py          # Streamlit entry-point (charts, chat, maps)
  example_queries.json  # Buttons rendered in the chat tab
  converter.py          # Helper to convert NetCDF → Parquet
scripts/                # Offline data ingestion utilities
requirements.txt        # Python dependencies
```

## ⚙️ Getting Started

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Prepare data**
   - Place Parquet files inside `data_cache/`. A sample `argo_index_indian.parquet` is expected by default.
3. **Run the dashboard**
   ```bash
   streamlit run app/dashboard.py
   ```
4. **(Optional) Enable local LLM answers**
   - Install [Ollama](https://ollama.com/) and pull a model such as `mistral`.
   - Set `OLLAMA_MODEL` in `.env` if you want to override the default.

## 🧠 How Natural-Language Queries Work Now

1. We normalise aliases for temperature, salinity, dissolved oxygen, etc.
2. The parser looks for:
   - Named places (`near Mumbai`, `in Bay of Bengal`) → geocoded to bounding boxes.
   - Explicit latitude/longitude ranges.
   - Temporal windows (`March 2023`, `last 6 months`).
   - Statistical intents (`average`, `median`, `count`, ...).
3. Filters are applied to the cached Parquet frame. Results fan out to:
   - Profile plots when depth variables are available.
   - Scatter maps with sampled points.
   - Aggregated statistics summarised in plain English.
4. If no data matches, a hybrid fallback (DuckDuckGo search + Ollama) is used.

## 🔍 Known Limitations & Future Scope

- **Vector / SQL backends** – The original roadmap mentioned FAISS/Chroma and SQL translation. The current build operates on cached Parquet files only. Future work: plug in a vector index for semantic retrieval, plus SQL generation for large catalogues.
- **Richer analytics** – Only single-variable aggregates are supported right now. Expanding to anomalies, trends, and multi-variable comparisons would add depth.
- **Offline geocoding cache** – We rely on live OpenStreetMap geocoding. Shipping a small cache (or offline gazetteer) would make demos more resilient.
- **Data freshness** – Live NOAA/INCOIS layers are demo endpoints. Integrating authenticated feeds or additional regional datasets is on the backlog.
- **Model integration** – Remote GPT-style models and MCP connectors are not wired in yet; today’s assistant targets local Ollama deployments.

## 🤝 Contributing

Issues and pull requests are welcome! Please lint/format your code and document new data dependencies in `requirements.txt` and this README.

## 📄 License

MIT — see [`LICENSE`](LICENSE).
