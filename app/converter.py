import pandas as pd
from pathlib import Path

INPUT_CSV = "scripts/datasets/ArgoFloats-index_712b_5843_9069.csv"
OUTPUT_PARQUET = "data_cache/argo_index_indian.parquet"

# Load with safe typing
df = pd.read_csv(INPUT_CSV, low_memory=False)

# Columns we want to keep (if they exist)
wanted_cols = [
    "file",
    "date",
    "latitude",
    "longitude",
    "platform_number",   # 👈 important fix
    "ocean",
    "profiler_type",
    "institution",
    "date_update",
]

# Keep only available columns
available_cols = [c for c in wanted_cols if c in df.columns]
df = df[available_cols]

# Clean numeric fields (if present)
coord_cols = [col for col in ["latitude", "longitude"] if col in df.columns]
for col in coord_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Drop rows with missing coordinates only when columns exist
if coord_cols:
    df = df.dropna(subset=coord_cols)
else:
    print("⚠️ Warning: latitude/longitude columns not found in source CSV; skipping coordinate cleanup.")

# Save
Path("data_cache").mkdir(exist_ok=True)
df.to_parquet(OUTPUT_PARQUET, index=False)

print(f"✅ Saved parquet with {len(df)} rows -> {OUTPUT_PARQUET}")
print("📌 Columns kept:", list(df.columns))
