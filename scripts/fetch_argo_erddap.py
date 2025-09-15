from erddapy import ERDDAP
import pandas as pd
from pathlib import Path
import time


def fetch_argo_subset(
    server="https://erddap.ifremer.fr/erddap",
    dataset_id="ArgoFloats",
    time_min="2023-03-01T00:00:00Z",
    time_max="2023-03-31T23:59:59Z",
    lat_min=-10,
    lat_max=10,
    lon_min=20,
    lon_max=120,
    pres_max=2000,
    out_path="data_cache/argo_equator_mar2023.parquet",
):
    """
    Fetch a subset of ARGO float profiles from ERDDAP and save to Parquet.
    """
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

    for attempt in range(3):
        try:
            df = e.to_pandas(parse_dates=True, requests_kwargs={"timeout": 60.0})
            break
        except Exception as ex:
            print(f"Attempt {attempt+1} failed: {ex}")
            time.sleep(5)

    # Convert numeric columns
    for c in ["latitude", "longitude", "pres", "temp", "psal"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    Path("data_cache").mkdir(exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"✅ Saved {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    fetch_argo_subset()