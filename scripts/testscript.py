import pandas as pd
from pathlib import Path

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names for index vs profile parquet files.
    """
    rename_map = {
        "time (UTC)": "time",
        "latitude (degrees_north)": "latitude",
        "longitude (degrees_east)": "longitude",
        "pres (decibar)": "pres",
        "temp (degree_Celsius)": "temp",
        "psal (PSU)": "psal",
    }
    df = df.rename(columns=rename_map)
    return df


if __name__ == "__main__":
    # Change file here for testing
    path = Path("data_cache/argo_equator_mar2023.parquet")

    print(f"🔄 Loading {path}")
    df = pd.read_parquet(path)
    df = normalize_columns(df)

    print("📌 Columns available:", df.columns.tolist())
    print("📊 Shape:", df.shape)

    # Decide schema type
    if {"time", "latitude", "longitude", "pres", "temp", "psal"}.issubset(df.columns):
        print("\n✅ Detected RAW / MULTI-RAW profile data")
        print(df[["time", "latitude", "longitude", "platform_number", "pres", "temp", "psal"]].head())
    elif {"latitude", "longitude", "file"}.issubset(df.columns):
        print("\n✅ Detected INDEX metadata")
        print(df[["file", "date", "latitude", "longitude", "ocean"]].head())
    else:
        print("\n⚠️ Unknown schema, showing first 5 rows")
        print(df.head())