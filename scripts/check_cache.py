"""Utility to inspect and cache the bundled ARGO index demo dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import DatasetUnavailableError, ensure_materialised

CACHE_PATH = Path("data/ArgoFloats-index.parquet")
SOURCE_CSV = Path("scripts/datasets/ArgoFloats-index_712b_5843_9069.csv")


def fetch_index(use_cache: bool = True) -> pd.DataFrame:
    """Load the ARGO index demo file and return a filtered ``DataFrame``."""

    if use_cache and CACHE_PATH.exists():
        print(f"📂 Loading cached data from {CACHE_PATH}")
        df = pd.read_parquet(CACHE_PATH)
    else:
        try:
            csv_path = ensure_materialised(SOURCE_CSV)
        except DatasetUnavailableError as exc:
            raise DatasetUnavailableError(
                "Local cache refresh requires the demo CSV dataset. "
                "See README instructions for fetching large assets."
            ) from exc

        print("🔄 Loading CSV from:", csv_path)
        df = pd.read_csv(csv_path, low_memory=False)

        # Ensure lat/lon are floats when available.
        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        print("💾 Caching to Parquet:", CACHE_PATH)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE_PATH, index=False)

    print("✅ Loaded", len(df), "records")
    print("📌 Columns available:", list(df.columns))

    # Optional: filter to bounding box
    if {"latitude", "longitude"}.issubset(df.columns):
        df = df[
            (df["latitude"] >= -30)
            & (df["latitude"] <= 30)
            & (df["longitude"] >= 20)
            & (df["longitude"] <= 120)
        ]
        print("📊 Filtered records:", len(df))

    return df


if __name__ == "__main__":
    data = fetch_index()
    print(data.head())
