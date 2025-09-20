"""Ad-hoc script to inspect cached parquet files and their schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import DatasetUnavailableError, ensure_materialised


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names for index vs profile parquet files."""

    rename_map = {
        "time (UTC)": "time",
        "latitude (degrees_north)": "latitude",
        "longitude (degrees_east)": "longitude",
        "pres (decibar)": "pres",
        "temp (degree_Celsius)": "temp",
        "psal (PSU)": "psal",
    }
    return df.rename(columns=rename_map)


def main(path: Path) -> None:
    try:
        resolved = ensure_materialised(path)
    except (FileNotFoundError, DatasetUnavailableError) as exc:
        raise SystemExit(str(exc))

    print(f"🔄 Loading {resolved}")
    df = pd.read_parquet(resolved)
    df = normalize_columns(df)

    print("📌 Columns available:", df.columns.tolist())
    print("📊 Shape:", df.shape)

    if {"time", "latitude", "longitude", "pres", "temp", "psal"}.issubset(df.columns):
        print("\n✅ Detected RAW / MULTI-RAW profile data")
        preview_cols = [
            col
            for col in ["time", "latitude", "longitude", "platform_number", "pres", "temp", "psal"]
            if col in df.columns
        ]
        print(df[preview_cols].head())
    elif {"latitude", "longitude", "file"}.issubset(df.columns):
        print("\n✅ Detected INDEX metadata")
        preview_cols = [col for col in ["file", "date", "latitude", "longitude", "ocean"] if col in df.columns]
        print(df[preview_cols].head())
    else:
        print("\n⚠️ Unknown schema, showing first 5 rows")
        print(df.head())


if __name__ == "__main__":
    main(Path("data_cache/argo_equator_mar2023.parquet"))
