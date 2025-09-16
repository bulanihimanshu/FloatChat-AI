import pandas as pd
from pathlib import Path

CACHE_PATH = Path("data/ArgoFloats-index.parquet")

def fetch_index(use_cache=True):
    """
    Load Argo index from local CSV, clean types, 
    cache as Parquet for faster reloads.
    """

    url = "scripts\datasets\ArgoFloats-index_24d4_2d6b_36a6.csv"

    if use_cache and CACHE_PATH.exists():
        print(f"📂 Loading cached data from {CACHE_PATH}")
        df = pd.read_parquet(CACHE_PATH)
    else:
        print("🔄 Loading CSV from:", url)
        df = pd.read_csv(url, low_memory=False)

        # Ensure lat/lon are floats
        for col in ["latitude", "longitude"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        print("💾 Caching to Parquet:", CACHE_PATH)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CACHE_PATH, index=False)

    print("✅ Loaded", len(df), "records")
    print("📌 Columns available:", list(df.columns))

    # Optional: filter to bounding box
    if "latitude" in df.columns and "longitude" in df.columns:
        df = df[
            (df["latitude"] >= -30) &
            (df["latitude"] <= 30) &
            (df["longitude"] >= 20) &
            (df["longitude"] <= 120)
        ]
        print("📊 Filtered records:", len(df))

    return df


if __name__ == "__main__":
    data = fetch_index()
    print(data.head())