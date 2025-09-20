"""CLI helper to normalise the ARGO index CSV into a cached Parquet file."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import DatasetUnavailableError, ensure_materialised

CACHE_PATH = Path("data/ArgoFloats-index.parquet")
SOURCE_CSV = Path("scripts/datasets/ArgoFloats-index_24d4_2d6b_36a6.csv")


def fetch_index(use_cache: bool = True) -> pd.DataFrame:
    """Load the ARGO index CSV, type clean a subset, and return the frame."""

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

        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE_PATH, index=False)
        print("💾 Caching to Parquet:", CACHE_PATH)

    return df


if __name__ == "__main__":
    frame = fetch_index()
    print("✅ Loaded", len(frame), "records")
