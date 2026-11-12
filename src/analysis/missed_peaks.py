import json
from datetime import date, datetime
import numpy as np
import pandas as pd

from src.common.config import load_config
from src.common.paths import artifacts_dir, processed_dir
from src.common.seasons import SEASONS, season_of
from src.features.weather_noise import noisy_weather


def _format_timestamp(val) -> str | None:
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    return str(val)


def classify_tags(
    day_features: pd.DataFrame | None,
    target_date: date,
    origin_ts: pd.Timestamp | None,
    season: str,
    past_season_daily_max_temps: np.ndarray | None,
    cfg: dict,
) -> tuple[list[str], float | None, float | None]:
    if day_features is None or len(day_features) == 0:
        is_weekend = target_date.weekday() >= 5
        tags = ["weekend"] if is_weekend else ["other"]
        return tags, None, None

    is_festival = (
        bool(day_features["cal_is_festival_window"].any())
        if "cal_is_festival_window" in day_features.columns
        else False
    )
    is_holiday = (
        bool(day_features["cal_is_holiday"].any())
        if "cal_is_holiday" in day_features.columns
        else False
    )
    is_weekend = (
        bool(day_features["cal_is_weekend"].any())
        if "cal_is_weekend" in day_features.columns
        else (target_date.weekday() >= 5)
    )

    actual_max_temp: float | None = None
    is_heatwave = False
    if "wx_temp_c" in day_features.columns:
        actual_max_temp = float(day_features["wx_temp_c"].max())
        if past_season_daily_max_temps is not None and len(past_season_daily_max_temps) >= 5:
            heatwave_threshold = float(np.quantile(past_season_daily_max_temps, 0.95))
            is_heatwave = actual_max_temp > heatwave_threshold

    temp_diff: float | None = None
    is_weather_miss = False
    if (
        actual_max_temp is not None
        and origin_ts is not None
        and "wx_rh_pct" in day_features.columns
    ):
        horizon_day = (target_date - origin_ts.date()).days
        if horizon_day >= 1:
            try:
                seed = int(cfg.get("seed", 42))
                proxy_df = noisy_weather(day_features, origin_ts, horizon_day, seed)
                proxy_max_temp = float(proxy_df["wx_temp_c"].max())
                temp_diff = round(actual_max_temp - proxy_max_temp, 2)
                is_weather_miss = abs(temp_diff) > 2.0
            except Exception:
                temp_diff = None
                is_weather_miss = False

    tags: list[str] = []
    if is_festival:
        tags.append("festival")
    if is_holiday:
        tags.append("holiday")
    if is_heatwave:
        tags.append("heatwave")
    if is_weather_miss:
        tags.append("weather_miss")
    if is_weekend:
        tags.append("weekend")
    if not tags:
        tags.append("other")

    return tags, temp_diff, actual_max_temp


def generate_note(
    tags: list[str],
    temp_diff: float | None,
    timing_error_min: int | None,
    magnitude_error_mw: float | None,
    actual_max_temp: float | None,
) -> str:
    if temp_diff is not None and abs(temp_diff) > 0.0:
        diff_val = round(abs(temp_diff), 1)
        if temp_diff >= 0:
            primary = f"Actual max temp {diff_val:.1f} °C above the weather proxy"
        else:
            primary = f"Actual max temp {diff_val:.1f} °C below the weather proxy"
    elif "heatwave" in tags and actual_max_temp is not None:
        primary = f"Heatwave conditions with max temp reaching {actual_max_temp:.1f} °C"
    elif "festival" in tags:
        primary = "Festival window effect impacted peak demand pattern"
    elif "holiday" in tags:
        primary = "Holiday schedule suppressed commercial and industrial demand"
    elif "weekend" in tags:
        primary = "Weekend load shape deviated from weekday forecast"
    elif magnitude_error_mw is not None:
        if magnitude_error_mw < 0:
            primary = f"Peak load under-forecasted by {abs(magnitude_error_mw):.0f} MW"
        else:
            primary = f"Peak load over-forecasted by {abs(magnitude_error_mw):.0f} MW"
    else:
        primary = "Unpredicted peak load variation"

    if timing_error_min is not None and timing_error_min != 0:
        shift_h = abs(timing_error_min) / 60.0
        shift_str = f"{int(shift_h)}" if shift_h.is_integer() else f"{shift_h:.1f}"
        if timing_error_min < 0:
            secondary = f"peak shifted {shift_str} h later than predicted"
        else:
            secondary = f"peak shifted {shift_str} h earlier than predicted"
        return f"{primary}; {secondary}."

    return f"{primary}."


def build_missed_peaks(
    peak_df: pd.DataFrame,
    load_df: pd.DataFrame | None = None,
    features_df: pd.DataFrame | None = None,
    cfg: dict | None = None,
) -> list[dict]:
    if cfg is None:
        cfg = load_config()

    miss_df = peak_df[peak_df["outcome"] == "miss"].copy()
    if len(miss_df) == 0:
        return []

    features_daily_max: pd.DataFrame | None = None
    if features_df is not None and len(features_df) > 0 and "wx_temp_c" in features_df.columns:
        f_df = features_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(f_df["ts"]):
            f_df["ts"] = pd.to_datetime(f_df["ts"])
        f_df["_date"] = f_df["ts"].dt.date
        f_df["_season"] = f_df["ts"].dt.month.map(season_of)
        features_daily_max = (
            f_df.groupby(["_date", "_season"])["wx_temp_c"].max().reset_index()
        )

    items: list[dict] = []
    for _, row in miss_df.iterrows():
        raw_date = row["date"]
        target_date = (
            raw_date
            if isinstance(raw_date, date)
            else pd.to_datetime(raw_date).date()
        )
        season = season_of(target_date.month)

        origin_ts = (
            pd.to_datetime(row["origin_ts"])
            if pd.notna(row.get("origin_ts"))
            else None
        )

        past_temps: np.ndarray | None = None
        if features_daily_max is not None and origin_ts is not None:
            past_mask = (
                (features_daily_max["_date"] < origin_ts.date())
                & (features_daily_max["_season"] == season)
            )
            past_temps = features_daily_max.loc[past_mask, "wx_temp_c"].to_numpy()

        day_feat: pd.DataFrame | None = None
        if features_df is not None and len(features_df) > 0:
            if not pd.api.types.is_datetime64_any_dtype(features_df["ts"]):
                f_ts = pd.to_datetime(features_df["ts"])
            else:
                f_ts = features_df["ts"]
            day_feat = features_df[f_ts.dt.date == target_date]

        tags, temp_diff, actual_max_temp = classify_tags(
            day_features=day_feat,
            target_date=target_date,
            origin_ts=origin_ts,
            season=season,
            past_season_daily_max_temps=past_temps,
            cfg=cfg,
        )

        timing_error_min = (
            int(row["timing_error_min"])
            if pd.notna(row.get("timing_error_min"))
            else None
        )
        magnitude_error_mw = (
            float(row["magnitude_error_mw"])
            if pd.notna(row.get("magnitude_error_mw"))
            else None
        )

        note = generate_note(
            tags=tags,
            temp_diff=temp_diff,
            timing_error_min=timing_error_min,
            magnitude_error_mw=magnitude_error_mw,
            actual_max_temp=actual_max_temp,
        )

        pred_peak_ts_str = _format_timestamp(row.get("pred_peak_ts"))
        actual_peak_ts_str = _format_timestamp(row.get("actual_peak_ts"))

        item = {
            "model": str(row["model"]),
            "date": target_date.strftime("%Y-%m-%d"),
            "season": season,
            "threshold_mw": float(row["threshold_mw"]),
            "peak_probability": round(float(row["peak_probability"]), 4),
            "pred_peak_ts": pred_peak_ts_str,
            "pred_peak_mw_p50": round(float(row["pred_peak_mw_p50"]), 2),
            "actual_peak_ts": actual_peak_ts_str,
            "actual_peak_mw": (
                round(float(row["actual_peak_mw"]), 2)
                if pd.notna(row.get("actual_peak_mw"))
                else None
            ),
            "magnitude_error_mw": (
                round(magnitude_error_mw, 2)
                if magnitude_error_mw is not None
                else None
            ),
            "timing_error_min": timing_error_min,
            "tags": tags,
            "note": note,
        }
        items.append(item)

    items.sort(
        key=lambda x: abs(x["magnitude_error_mw"]) if x["magnitude_error_mw"] is not None else 0.0,
        reverse=True,
    )
    return items


def main() -> None:
    cfg = load_config()
    art_dir = artifacts_dir()
    proc_dir = processed_dir()

    peak_path = art_dir / "peak_predictions.parquet"
    load_path = proc_dir / "load_hourly.parquet"
    feat_path = proc_dir / "features_known.parquet"

    peak_df = pd.read_parquet(peak_path)
    load_df = pd.read_parquet(load_path) if load_path.exists() else None
    feat_df = pd.read_parquet(feat_path) if feat_path.exists() else None

    items = build_missed_peaks(
        peak_df=peak_df,
        load_df=load_df,
        features_df=feat_df,
        cfg=cfg,
    )

    out = {"items": items}
    out_path = art_dir / "missed_peaks.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, allow_nan=False)

    print(f"Wrote {len(items)} missed peaks to {out_path}")


if __name__ == "__main__":
    main()

