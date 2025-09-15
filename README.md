# 🌊 FloatChat: AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization

## 📘 Background

Oceanographic data is vast, complex, and heterogeneous — spanning satellite observations, CTD casts, Argo floats, and BGC sensors. The **Argo program** deploys autonomous profiling floats across the world’s oceans, generating rich datasets in **NetCDF** format that include temperature, salinity, and other essential ocean variables.

Accessing and interpreting this data traditionally requires domain expertise and technical proficiency. With the advent of **AI** and **Large Language Models (LLMs)**, it's now possible to build intuitive systems that democratize access to ocean data for researchers, policymakers, and curious minds alike.

---

## 💡 Project Overview

**FloatChat** is an AI-powered conversational system designed to simplify the exploration and visualization of ARGO float data using natural language. It bridges the gap between raw oceanographic data and actionable insights.

### 🔧 Key Features

- **NetCDF Ingestion**: Converts ARGO float data into structured formats (SQL/Parquet).
- **Vector Database Integration**: Stores metadata and summaries using FAISS or Chroma for fast retrieval.
- **LLM-Powered Querying**: Uses Retrieval-Augmented Generation (RAG) pipelines with multimodal models (GPT, QWEN, LLaMA, Mistral) via Model Context Protocol (MCP).
- **Interactive Dashboards**: Built with Streamlit or Dash to visualize:
  - Float trajectories
  - Depth-time plots
  - Profile comparisons
- **Conversational Interface**: Chatbot-style UI that understands queries like:
  - “Show me salinity profiles near the equator in March 2023”
  - “Compare BGC parameters in the Arabian Sea for the last 6 months”
  - “What are the nearest ARGO floats to this location?”

---

## 🚀 Expected Solution Architecture

| Component            | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| 🗂️ Data Pipeline     | Ingests NetCDF files → Converts to SQL/Parquet → Stores in PostgreSQL & FAISS |
| 🧠 Backend LLM       | Translates user queries → SQL → Generates responses via RAG                  |
| 📊 Visualization     | Dashboards with Plotly, Leaflet, or Cesium for geospatial and tabular views |
| 💬 Chat Interface    | Natural language interaction for guided data discovery                      |
| 🌍 PoC Deployment    | Demonstrates functionality using Indian Ocean ARGO data                      |

---

## 🧪 Proof-of-Concept Goals

- ✅ End-to-end ingestion and transformation of ARGO NetCDF data
- ✅ Conversational querying with LLMs and vector search
- ✅ Interactive geospatial and profile visualizations
- ✅ Extensibility to BGC floats, gliders, buoys, and satellite datasets

---

## 🔤 Acronyms

| Term     | Meaning                                      |
|----------|----------------------------------------------|
| NetCDF   | Network Common Data Format                   |
| CTD      | Conductivity, Temperature, and Depth         |
| BGC      | Bio-Geo-Chemical Floats                      |
| RAG      | Retrieval-Augmented Generation               |
| MCP      | Model Context Protocol                       |

---

## 📎 License

This project is released under the MIT License. See `LICENSE` for details.

---

## 🤝 Contributing

We welcome contributions! Please open issues or submit pull requests to improve functionality, add new visualizations, or expand dataset support.

---

## 📬 Contact

For questions, collaborations, or feedback, reach out via [GitHub Issues](https://github.com/your-repo/issues) or email the maintainers.

## 📅 Project Timeline

### 🟢 FloatChat – Day 1: Data Ingestion & Setup

**🎯 Goal**  
Prepare real ARGO float data in a **structured, analysis-ready format** to use for chat-driven exploration and visualization in later days.

**✅ Steps Completed**
- Pulled subset of ARGO float profiles from **Ifremer ERDDAP** (`ArgoFloats`, `ArgoFloats-index`)
- Extracted key fields: `time`, `latitude`, `longitude`, `platform_number`, `pres`, `temp`, `psal`
- Saved data as **Parquet** in `data_cache/` for fast local access
- Added optional ingestion of **NetCDF** files into Parquet format

**🛠️ Scripts Used**
- `fetch_argo_erddap.py` → Downloads profile data
- `fetch_index.py` → Downloads lightweight metadata index
- `ingest_local_netcdf.py` → Converts local NetCDF → Parquet
- `check_cache.py` → Sanity check for saved datasets

**🔜 Next Steps (Day 2 Preview)**
- Build basic visualizations using cached data:
  - 🌍 Map of float locations
  - 📈 Depth vs temperature/salinity plots

---
