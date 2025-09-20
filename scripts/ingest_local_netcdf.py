"""Convert a local ARGO NetCDF profile to the parquet schema used by the app."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import xarray as xr

from utils import DatasetUnavailableError, ensure_materialised

RENAME_MAP = {
    "LATITUDE": "latitude",
    "LONGITUDE": "longitude",
    "PRES": "pres",
    "TEMP": "temp",
    "PSAL": "psal",
    "PLATFORM_NUMBER": "platform_number",
    "JULD": "time",
}


def _convert_time_column(df: pd.DataFrame) -> pd.DataFrame:
    if "time" not in df.columns:
        return df

    # ARGO stores Julian days since 1950-01-01 00:00:00 UTC.
    origin = pd.Timestamp("1950-01-01", tz="UTC")
    df["time"] = origin + pd.to_timedelta(df["time"], unit="D")
    df["date"] = df["time"].dt.date
    return df


def ingest_local_netcdf(
    source: str | Path,
    out_path: str | Path = "data_cache/argo_single_profile.parquet",
) -> Path:
    """Load ``source`` NetCDF file and persist a flattened parquet file."""

    try:
        resolved_source = ensure_materialised(source)
    except DatasetUnavailableError as exc:
        raise DatasetUnavailableError(
            "The NetCDF demo file is not available locally. "
            "Run `git lfs pull` to download it before ingesting."
        ) from exc

    ds = xr.open_dataset(resolved_source, engine="h5netcdf")

    df = ds.to_dataframe().reset_index()
    df = df.rename(columns=RENAME_MAP)
    df = _convert_time_column(df)

    numeric_cols = [c for c in ("latitude", "longitude", "pres", "temp", "psal") if c in df.columns]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if numeric_cols:
        df = df.dropna(subset=numeric_cols, how="all")

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(target, index=False)
    print(f"✅ Saved parquet with {len(df)} rows -> {target}")
    return target


if __name__ == "__main__":
    ingest_local_netcdf("scripts/datasets/1901096_prof.nc")
