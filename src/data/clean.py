import sys

import numpy as np
import pandas as pd

from src.common import constants
from src.common.config import load_config
from src.common.paths import processed_dir


def _load_raw() -> pd.DataFrame:
    path = processed_dir() / "load_raw_hourly.parquet"
    df = pd.read_parquet(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=False)
    if df["ts"].dt.tz is None:
        df["ts"] = df["ts"].dt.tz_localize(constants.TZ)
    else:
        df["ts"] = df["ts"].dt.tz_convert(constants.TZ)
    return df


def _detect_source_issues(df: pd.DataFrame) -> dict:
    duplicates = int(df["ts"].duplicated().sum())
    non_hour_aligned = int((df["ts"].dt.minute != 0).sum() + (df["ts"].dt.second != 0).sum())
    diffs = df["ts"].diff().dropna()
    expected = pd.Timedelta(hours=1)
    clock_shifts = int((diffs != expected).sum())
    return {
        "duplicates": duplicates,
        "non_hour_aligned": non_hour_aligned,
        "clock_shifts": clock_shifts,
    }


def _resolve_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df["ts"].duplicated().any():
        df = df.groupby("ts", as_index=False)["load_mw"].mean()
    return df.sort_values("ts").reset_index(drop=True)


def _reindex_to_complete(df: pd.DataFrame) -> pd.DataFrame:
    full_index = pd.date_range(
        start=df["ts"].min(),
        end=df["ts"].max(),
        freq="h",
        tz=constants.TZ,
    )
    df = df.set_index("ts").reindex(full_index)
    df.index.name = "ts"
    df = df.reset_index()
    return df


def _gap_runs(mask: pd.Series) -> list[tuple[int, int]]:
    runs = []
    in_gap = False
    start = 0
    for i, v in enumerate(mask):
        if v and not in_gap:
            start = i
            in_gap = True
        elif not v and in_gap:
            runs.append((start, i - 1))
            in_gap = False
    if in_gap:
        runs.append((start, len(mask) - 1))
    return runs


def _impute_hour_of_week(
    series: pd.Series,
    ts: pd.Series,
    idx: int,
    n_weeks: int,
) -> float:
    target_ts = ts.iloc[idx]
    how = target_ts.dayofweek * 24 + target_ts.hour
    candidates = []
    k = 1
    while len(candidates) < n_weeks:
        for sign in (-1, 1):
            offset = sign * k
            candidate_ts = target_ts + pd.Timedelta(hours=offset * 168)
            if candidate_ts < ts.iloc[0] or candidate_ts > ts.iloc[-1]:
                continue
            pos = ts.searchsorted(candidate_ts)
            if pos < len(ts) and ts.iloc[pos] == candidate_ts:
                val = series.iloc[pos]
                if not pd.isna(val):
                    cand_how = candidate_ts.dayofweek * 24 + candidate_ts.hour
                    if cand_how == how:
                        candidates.append(val)
        k += 1
        if k > 500:
            break
    if candidates:
        return float(np.mean(candidates[:n_weeks]))
    nearby = series[
        (ts.dt.dayofweek == target_ts.dayofweek)
        & (ts.dt.hour == target_ts.hour)
        & series.notna()
    ]
    if not nearby.empty:
        return float(nearby.mean())
    return float(series.dropna().mean())


def _impute(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    max_linear = int(cfg.get("linear_gap_max_hours", 3))
    n_weeks = int(cfg.get("hour_of_week_weeks", 4))

    is_imputed = np.zeros(len(df), dtype=bool)
    imputation_method = np.full(len(df), None, dtype=object)
    load = df["load_mw"].copy()
    raw_null = load.isna()

    gaps = _gap_runs(raw_null.tolist())

    for start, end in gaps:
        length = end - start + 1
        if length <= max_linear:
            load.iloc[start : end + 1] = np.nan
            load = load.interpolate(method="linear", limit_area="inside")
            is_imputed[start : end + 1] = True
            imputation_method[start : end + 1] = "linear"
        else:
            orig = load.copy()
            for i in range(start, end + 1):
                val = _impute_hour_of_week(orig, df["ts"], i, n_weeks)
                load.iloc[i] = val
                is_imputed[i] = True
                imputation_method[i] = "hour_of_week"

    if load.isna().any():
        load = load.interpolate(method="linear").ffill().bfill()
        for i in range(len(load)):
            if raw_null.iloc[i] and not is_imputed[i]:
                is_imputed[i] = True
                imputation_method[i] = "hour_of_week"

    df = df.copy()
    df["load_mw"] = load
    df["is_imputed"] = is_imputed
    df["imputation_method"] = imputation_method
    return df


def _flag_outages(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    threshold = float(cfg.get("outage_mad_z", 6.0))
    how = df["ts"].dt.dayofweek * 24 + df["ts"].dt.hour
    how_median = df["load_mw"].groupby(how).transform("median")
    resid = df["load_mw"] - how_median
    med_resid = resid.median()
    mad = float(np.median(np.abs(resid - med_resid)))
    if mad == 0:
        df["is_outage_suspect"] = False
        return df
    z = np.abs(resid - med_resid) / mad
    df = df.copy()
    df["is_outage_suspect"] = z >= threshold
    return df


def _print_summary(df: pd.DataFrame) -> None:
    total = len(df)
    n_imputed_linear = int((df["imputation_method"] == "linear").sum())
    n_imputed_how = int((df["imputation_method"] == "hour_of_week").sum())
    n_outage = int(df["is_outage_suspect"].sum())
    pct_linear = 100 * n_imputed_linear / total
    pct_how = 100 * n_imputed_how / total
    print(f"Total hours     : {total}")
    print(f"Date range      : {df['ts'].min()} — {df['ts'].max()}")
    print(f"NaN remaining   : {df['load_mw'].isna().sum()}")
    print(f"Imputed linear  : {n_imputed_linear} ({pct_linear:.2f}%)")
    print(f"Imputed hour-of-week: {n_imputed_how} ({pct_how:.2f}%)")
    print(f"Outage suspects : {n_outage}")


def clean() -> None:
    cfg = load_config().get("cleaning", {})

    raw = _load_raw()
    issues = _detect_source_issues(raw)
    print(f"Source issues — duplicates: {issues['duplicates']}, "
          f"non-hour-aligned: {issues['non_hour_aligned']}, "
          f"clock shifts (unexpected step): {issues['clock_shifts']}")

    df = _resolve_duplicates(raw)
    df = _reindex_to_complete(df)

    df = _impute(df, cfg)
    df = _flag_outages(df, cfg)

    df = df[["ts", "load_mw", "is_imputed", "imputation_method", "is_outage_suspect"]]
    df["load_mw"] = df["load_mw"].astype(float)
    df["is_imputed"] = df["is_imputed"].astype(bool)
    df["is_outage_suspect"] = df["is_outage_suspect"].astype(bool)

    assert df["load_mw"].isna().sum() == 0, "NaNs remain in load_mw after imputation"

    out_path = processed_dir() / "load_hourly.parquet"
    df.to_parquet(out_path, index=False, compression="snappy")
    _print_summary(df)
    print(f"Written: {out_path}")


if __name__ == "__main__":
    clean()
    sys.exit(0)
