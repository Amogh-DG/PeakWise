from pathlib import Path
import numpy as np
import pandas as pd
from src.backtest.registry import register
from src.common import constants, paths
from src.models.quantile_utils import sort_quantiles


def get_load_path() -> Path:
    p = paths.processed_dir() / "load_hourly.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
        if mock_p.exists():
            return mock_p
    return p


@register("seasonal_naive")
class SeasonalNaiveForecaster:
    name: str = "seasonal_naive"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.train_end: pd.Timestamp | None = None
        self.hour_residuals: dict[int, np.ndarray] = {
            h: np.array([0.0]) for h in range(24)
        }

    def fit(self, train_end: pd.Timestamp) -> None:
        self.train_end = train_end
        load_path = get_load_path()
        if not load_path.exists():
            return

        load_df = pd.read_parquet(load_path)
        train_df = load_df[load_df["ts"] < train_end].copy()
        if len(train_df) < 168:
            return

        ts_series = train_df["ts"]
        load_map = dict(zip(ts_series, train_df["load_mw"]))

        res_by_h = {h: [] for h in range(24)}
        for ts, actual in zip(ts_series[168:], train_df["load_mw"][168:]):
            prev_ts = ts - pd.Timedelta(days=7)
            prev_val = load_map.get(prev_ts, None)
            if prev_val is not None:
                residual = actual - prev_val
                res_by_h[ts.hour].append(residual)

        for h in range(24):
            vals = res_by_h[h]
            if len(vals) > 0:
                self.hour_residuals[h] = np.array(vals)
            else:
                self.hour_residuals[h] = np.array([0.0])

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        load_path = get_load_path()
        load_map = {}
        fallback_load = 4000.0
        if load_path.exists():
            load_df = pd.read_parquet(load_path)
            known_df = load_df[load_df["ts"] < origin]
            if not known_df.empty:
                load_map = dict(zip(known_df["ts"], known_df["load_mw"]))
                fallback_load = float(known_df["load_mw"].iloc[-1])

        start_target = (origin + pd.Timedelta(days=1)).floor("D")
        target_hours = pd.date_range(start=start_target, periods=168, freq="h", tz=constants.TZ)

        p50_list = []
        p05_list = []
        p10_list = []
        p90_list = []
        p95_list = []
        horizon_h_list = []
        horizon_day_list = []

        for h_step, target_ts in enumerate(target_hours):
            horizon_h = int((target_ts - origin).total_seconds() // 3600)
            horizon_day = int(h_step // 24 + 1)
            horizon_h_list.append(horizon_h)
            horizon_day_list.append(horizon_day)

            lookup_ts = target_ts - pd.Timedelta(days=7)
            while lookup_ts >= origin:
                lookup_ts = lookup_ts - pd.Timedelta(days=7)

            naive_pred = load_map.get(lookup_ts, fallback_load)
            p50 = float(naive_pred)

            res = self.hour_residuals[target_ts.hour]
            q05, q10, q50_offset, q90, q95 = np.quantile(
                res, [0.05, 0.1, 0.5, 0.9, 0.95]
            )

            p05_list.append(round(p50 + q05, 1))
            p10_list.append(round(p50 + q10, 1))
            p50_list.append(round(p50 + q50_offset, 1))
            p90_list.append(round(p50 + q90, 1))
            p95_list.append(round(p50 + q95, 1))

        df = pd.DataFrame(
            {
                "target_ts": target_hours,
                "horizon_h": horizon_h_list,
                "horizon_day": horizon_day_list,
                "p05": p05_list,
                "p10": p10_list,
                "p50": p50_list,
                "p90": p90_list,
                "p95": p95_list,
            }
        )
        return sort_quantiles(df)
