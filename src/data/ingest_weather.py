import json
import sys
import urllib.error
import urllib.request

import pandas as pd

from src.common import constants, paths

LATITUDE = 28.61
LONGITUDE = 77.21
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_load_date_range() -> tuple[str, str]:
    proc_dir = paths.processed_dir()
    load_path = proc_dir / "load_raw_hourly.parquet"
    if load_path.exists():
        df_load = pd.read_parquet(load_path)
        min_date = df_load["ts"].min().strftime("%Y-%m-%d")
        max_date = df_load["ts"].max().strftime("%Y-%m-%d")
        return min_date, max_date
    return "2023-04-01", "2026-01-13"


def build_api_url(start_date: str, end_date: str) -> str:
    params = [
        f"latitude={LATITUDE}",
        f"longitude={LONGITUDE}",
        f"start_date={start_date}",
        f"end_date={end_date}",
        "hourly=temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m,cloud_cover",
        "timezone=Asia%2FKolkata",
    ]
    return f"{OPEN_METEO_ARCHIVE_URL}?{'&'.join(params)}"


def ingest_weather() -> pd.DataFrame:
    raw_weather_dir = paths.raw_dir() / "weather"
    raw_weather_dir.mkdir(parents=True, exist_ok=True)

    start_date, end_date = get_load_date_range()
    cache_file = raw_weather_dir / f"open_meteo_{start_date}_{end_date}.json"

    api_url = build_api_url(start_date, end_date)

    if cache_file.exists():
        print(f"Loading cached weather response from: {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"Fetching weather from Open-Meteo API: {api_url}")
        req = urllib.request.Request(api_url, headers={"User-Agent": "PeakWise/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"Cached raw weather response at: {cache_file}")
        except urllib.error.URLError as err:
            print("\n[ERROR] Unable to reach the Open-Meteo API from current environment.")
            print(f"Reason: {err}")
            print("\nRun the following command locally to download and cache the weather payload:")
            print(f'curl -o "{cache_file}" "{api_url}"\n')
            print("Or with Python:")
            print("python -c \"import urllib.request; "
                  f"urllib.request.urlretrieve('{api_url}', r'{cache_file}')\"")
            sys.exit(1)

    hourly = data["hourly"]
    times = pd.to_datetime(hourly["time"]).tz_localize(constants.TZ)

    df_weather = pd.DataFrame(
        {
            "ts": times,
            "wx_temp_c": hourly["temperature_2m"],
            "wx_rh_pct": hourly["relative_humidity_2m"],
            "wx_dewpoint_c": hourly["dew_point_2m"],
            "wx_wind_ms": hourly["wind_speed_10m"],
            "wx_cloud_pct": hourly["cloud_cover"],
        }
    )

    df_weather = df_weather.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)

    proc_dir = paths.processed_dir()
    proc_dir.mkdir(parents=True, exist_ok=True)
    out_path = proc_dir / "weather_hourly.parquet"
    df_weather.to_parquet(out_path, index=False)
    print(f"Saved hourly weather data to: {out_path}")

    total_rows = len(df_weather)
    missing_count = int(df_weather.isna().sum().sum())
    start_ts = df_weather["ts"].min()
    end_ts = df_weather["ts"].max()
    min_temp = float(df_weather["wx_temp_c"].min())
    max_temp = float(df_weather["wx_temp_c"].max())

    print("\n--- Weather Ingestion Summary ---")
    print(f"Date range: {start_ts} to {end_ts}")
    print(f"Total hourly rows: {total_rows}")
    print(f"Total missing values across weather columns: {missing_count}")
    print(f"Min temperature: {min_temp:.2f} °C, Max temperature: {max_temp:.2f} °C")

    return df_weather


if __name__ == "__main__":
    ingest_weather()
