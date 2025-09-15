import pandas as pd
from pathlib import Path

# Path to your parquet file (adjust if needed)
parquet_dir = Path("data_cache")

# Find the most recent parquet file
parquet_files = sorted(parquet_dir.glob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
if not parquet_files:
    raise FileNotFoundError("⚠️ No parquet files found in data_cache/")
parquet_file = parquet_files[0]

print(f"🔄 Loading {parquet_file}")
df = pd.read_parquet(parquet_file)

print("📌 Columns available:", df.columns.tolist())
print("📊 Shape:", df.shape)

# Detect structure
if set(["latitude", "longitude", "temp", "psal"]).issubset(df.columns):
    print("\n✅ Detected RAW / MULTI-RAW profile data")
    print(df[["time", "latitude", "longitude", "pres", "temp", "psal"]].head())

elif set(["XAXIS", "YAXIS"]).issubset(df.columns):
    print("\n📊 Detected FERRET grid data")
    cols = ["XAXIS", "YAXIS"]
    if "S_ANALYZED" in df.columns:
        cols.append("S_ANALYZED")
    print(df[cols].head())

else:
    print("\n⚠️ Unknown schema, showing first 5 rows")
    print(df.head())
