"""Download a subset of ARGO float profiles from an ERDDAP instance."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from erddapy import ERDDAP


def fetch_argo_subset(
    server: str = "https://erddap.ifremer.fr/erddap",
    dataset_id: str = "ArgoFloats",
    time_min: str = "2023-03-01T00:00:00Z",
    time_max: str = "2023-03-31T23:59:59Z",
    lat_min: float = -10,
    lat_max: float = 10,
    lon_min: float = 20,
    lon_max: float = 120,
    pres_max: float = 2000,
    out_path: str | Path = "data_cache/argo_equator_mar2023.parquet",
) -> Path:
    """Fetch a filtered ARGO subset and persist it as Parquet."""

    e = ERDDAP(server=server, protocol="tabledap", response="csv")
    e.dataset_id = dataset_id
    e.constraints = {
        "time>=": time_min,
        "time<=": time_max,
        "latitude>=": lat_min,
        "latitude<=": lat_max,
        "longitude>=": lon_min,
        "longitude<=": lon_max,
        "pres<=": pres_max,
    }
    e.variables = [
        "time",
        "latitude",
        "longitude",
        "platform_number",
        "pres",
        "temp",
        "psal",
    ]

    df = None
    for attempt in range(1, 4):
        try:
            df = e.to_pandas(parse_dates=True, requests_kwargs={"timeout": 60.0})
            break
        except Exception as exc:  # pragma: no cover - used in ad-hoc scripts
            print(f"Attempt {attempt} failed: {exc}")
            time.sleep(5)

    if df is None:
        raise RuntimeError("Failed to download data from ERDDAP after 3 attempts")

    # Convert numeric columns where possible.
    for col in ("latitude", "longitude", "pres", "temp", "psal"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(target, index=False)
    print(f"✅ Saved {len(df)} rows -> {target}")
    return target


if __name__ == "__main__":
    fetch_argo_subset()
