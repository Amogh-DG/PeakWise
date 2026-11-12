from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
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


def get_features_path() -> Path:
    p = paths.processed_dir() / "features_known.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "data" / "processed_mock" / "features_known.parquet"
        if mock_p.exists():
            return mock_p
    return p


@register("linear")
class LinearForecaster:
    name: str = "linear"

    feature_cols = [
        "cal_hour_sin",
        "cal_hour_cos",
        "cal_dow_sin",
        "cal_dow_cos",
        "cal_is_weekend",
        "cal_is_holiday",
        "cal_is_festival_window",
        "evt_lockdown",
        "evt_odd_even",
        "wx_cdh_24",
        "wx_heat_index_c",
        "wx_temp_c",
        "wx_temp_lag_1",
        "wx_temp_lag_24",
        "wx_temp_roll_24",
        "trend_t",
        "ar_same_hour_last_known_week",
        "horizon_h",
    ]

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model = LinearRegression()
        self.train_end: pd.Timestamp | None = None
        self.hour_residuals: dict[int, np.ndarray] = {
            h: np.array([0.0]) for h in range(24)
        }
        self.is_fitted = False

    def _build_features_df(
        self,
        target_ts_series: pd.Series,
        features_known_df: pd.DataFrame,
        load_map: dict[pd.Timestamp, float],
        fallback_load: float,
        origin: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        feat_subset = features_known_df[features_known_df["ts"].isin(target_ts_series)].copy()
        if feat_subset.empty:
            feat_subset = pd.DataFrame({"ts": target_ts_series})
            for col in self.feature_cols:
                feat_subset[col] = 0.0

        ts_list = feat_subset["ts"].tolist()
        ar_vals = []
        horizon_h_vals = []

        for t in ts_list:
            if origin is not None:
                h_h = int((t - origin).total_seconds() // 3600)
                horizon_h_vals.append(h_h)

                lookup_ts = t - pd.Timedelta(days=7)
                while lookup_ts >= origin:
                    lookup_ts = lookup_ts - pd.Timedelta(days=7)
                ar_vals.append(load_map.get(lookup_ts, fallback_load))
            else:
                horizon_h_vals.append(24)
                lookup_ts = t - pd.Timedelta(days=7)
                ar_vals.append(load_map.get(lookup_ts, fallback_load))

        feat_subset["horizon_h"] = horizon_h_vals
        feat_subset["ar_same_hour_last_known_week"] = ar_vals

        for col in self.feature_cols:
            if col not in feat_subset.columns:
                feat_subset[col] = 0.0
            feat_subset[col] = feat_subset[col].astype(float).fillna(0.0)

        return feat_subset

    def fit(self, train_end: pd.Timestamp) -> None:
        self.train_end = train_end
        load_path = get_load_path()
        feat_path = get_features_path()
        if not load_path.exists() or not feat_path.exists():
            return

        load_df = pd.read_parquet(load_path)
        feat_df = pd.read_parquet(feat_path)

        train_load = load_df[load_df["ts"] < train_end].copy()
        if len(train_load) < 336:
            return

        load_map = dict(zip(train_load["ts"], train_load["load_mw"]))
        fallback_load = float(train_load["load_mw"].iloc[0])

        valid_targets = train_load["ts"].iloc[168:]
        features_mat = self._build_features_df(
            valid_targets, feat_df, load_map, fallback_load, origin=None
        )

        y = train_load["load_mw"].iloc[168:].to_numpy()
        x = features_mat[self.feature_cols].to_numpy()

        self.model.fit(x, y)
        self.is_fitted = True

        preds = self.model.predict(x)
        residuals = y - preds

        res_by_h = {h: [] for h in range(24)}
        for ts, res in zip(valid_targets, residuals):
            res_by_h[ts.hour].append(res)

        for h in range(24):
            vals = res_by_h[h]
            if len(vals) > 0:
                self.hour_residuals[h] = np.array(vals)
            else:
                self.hour_residuals[h] = np.array([0.0])

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        load_path = get_load_path()
        feat_path = get_features_path()
        load_map = {}
        fallback_load = 4000.0

        if load_path.exists():
            load_df = pd.read_parquet(load_path)
            known_load = load_df[load_df["ts"] < origin]
            if not known_load.empty:
                load_map = dict(zip(known_load["ts"], known_load["load_mw"]))
                fallback_load = float(known_load["load_mw"].iloc[-1])

        start_target = (origin + pd.Timedelta(days=1)).floor("D")
        target_hours = pd.date_range(start=start_target, periods=168, freq="h", tz=constants.TZ)

        if feat_path.exists():
            feat_df = pd.read_parquet(feat_path)
        else:
            feat_df = pd.DataFrame({"ts": target_hours})

        x_df = self._build_features_df(
            pd.Series(target_hours), feat_df, load_map, fallback_load, origin=origin
        )
        x = x_df[self.feature_cols].to_numpy()

        if self.is_fitted:
            p50_raw = self.model.predict(x)
        else:
            p50_raw = np.array([fallback_load] * 168)

        p05_list = []
        p10_list = []
        p50_list = []
        p90_list = []
        p95_list = []
        horizon_h_list = []
        horizon_day_list = []

        for h_step, (target_ts, p50_val) in enumerate(zip(target_hours, p50_raw)):
            horizon_h = int((target_ts - origin).total_seconds() // 3600)
            horizon_day = int(h_step // 24 + 1)
            horizon_h_list.append(horizon_h)
            horizon_day_list.append(horizon_day)

            res = self.hour_residuals[target_ts.hour]
            q05, q10, q50_offset, q90, q95 = np.quantile(
                res, [0.05, 0.1, 0.5, 0.9, 0.95]
            )

            p05_list.append(round(p50_val + q05, 1))
            p10_list.append(round(p50_val + q10, 1))
            p50_list.append(round(p50_val + q50_offset, 1))
            p90_list.append(round(p50_val + q90, 1))
            p95_list.append(round(p50_val + q95, 1))

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
