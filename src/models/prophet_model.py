import logging
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from prophet import Prophet

from src.backtest.registry import register
from src.common import constants, paths
from src.models.quantile_utils import sort_quantiles

logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)


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


def load_holidays_df() -> pd.DataFrame:
    dfs = []
    festivals_path = paths.repo_root() / "data" / "external" / "festivals.csv"
    if festivals_path.exists():
        f_df = pd.read_csv(festivals_path)
        if "date" in f_df.columns and "festival" in f_df.columns:
            f_clean = pd.DataFrame(
                {
                    "holiday": f_df["festival"].astype(str),
                    "ds": pd.to_datetime(f_df["date"]),
                }
            )
            dfs.append(f_clean)

    try:
        import holidays

        ind_holidays = holidays.India(years=range(2021, 2026))
        ind_records = [{"holiday": name, "ds": pd.to_datetime(dt)} for dt, name in ind_holidays.items()]
        if ind_records:
            dfs.append(pd.DataFrame(ind_records))
    except Exception:
        pass

    if dfs:
        combined = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["holiday", "ds"])
        return combined
    return pd.DataFrame(columns=["holiday", "ds"])


@register("prophet")
class ProphetForecaster:
    name: str = "prophet"
    calibrate: bool = True

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model: Prophet | None = None
        self.train_end: pd.Timestamp | None = None
        self.residual_quantiles: dict[int, dict[float, float]] = {}
        self.load_df: pd.DataFrame | None = None
        self.features_df: pd.DataFrame | None = None
        self.fallback_load = 4000.0
        self.quantiles = [float(q) for q in self.cfg.get("quantiles", constants.QUANTILES)]

    def _load_data(self) -> None:
        if self.load_df is None:
            l_path = get_load_path()
            if l_path.exists():
                self.load_df = pd.read_parquet(l_path)
        if self.features_df is None:
            f_path = get_features_path()
            if f_path.exists():
                self.features_df = pd.read_parquet(f_path)

    def fit(self, train_end: pd.Timestamp) -> None:
        self.train_end = train_end
        self._load_data()
        if self.load_df is None or self.features_df is None:
            return

        known_load = self.load_df[self.load_df["ts"] < train_end].copy()
        if len(known_load) < 720:
            return

        self.fallback_load = float(known_load["load_mw"].iloc[-1])

        max_history_days = 365
        earliest_allowed = train_end - pd.Timedelta(days=max_history_days)
        recent_load = known_load[known_load["ts"] >= earliest_allowed].copy()
        if len(recent_load) < 720:
            recent_load = known_load.tail(720).copy()

        recent_load = recent_load.sort_values("ts").reset_index(drop=True)

        features_sub = self.features_df[["ts", "wx_temp_c", "wx_cdh_24"]].copy()
        merged = pd.merge(recent_load, features_sub, on="ts", how="left")
        merged["wx_temp_c"] = merged["wx_temp_c"].ffill().bfill().fillna(30.0)
        merged["wx_cdh_24"] = merged["wx_cdh_24"].ffill().bfill().fillna(50.0)

        df_train = pd.DataFrame(
            {
                "ds": merged["ts"].dt.tz_localize(None),
                "y": merged["load_mw"].to_numpy(),
                "wx_temp_c": merged["wx_temp_c"].to_numpy(),
                "wx_cdh_24": merged["wx_cdh_24"].to_numpy(),
            }
        )

        holidays_df = load_holidays_df()
        m = Prophet(
            holidays=holidays_df if not holidays_df.empty else None,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
        )
        m.add_regressor("wx_temp_c")
        m.add_regressor("wx_cdh_24")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m.fit(df_train)

        self.model = m

        in_sample = m.predict(df_train[["ds", "wx_temp_c", "wx_cdh_24"]])
        residuals = df_train["y"].to_numpy() - in_sample["yhat"].to_numpy()
        hours = merged["ts"].dt.hour.to_numpy()

        res_map: dict[int, dict[float, float]] = {}
        for h in range(24):
            h_mask = hours == h
            h_res = residuals[h_mask]
            if len(h_res) == 0:
                h_res = residuals
            q_dict = {}
            for q in self.quantiles:
                q_dict[q] = float(np.quantile(h_res, q))
            res_map[h] = q_dict

        self.residual_quantiles = res_map

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        self._load_data()
        start_target = (origin + pd.Timedelta(days=1)).floor("D")
        target_hours = pd.date_range(start=start_target, periods=168, freq="h", tz=constants.TZ)

        horizon_h_list = [int((t - origin).total_seconds() // 3600) for t in target_hours]
        horizon_day_list = [int(i // 24 + 1) for i in range(168)]

        if self.model is None or self.features_df is None:
            default_val = self.fallback_load
            df = pd.DataFrame(
                {
                    "target_ts": target_hours,
                    "horizon_h": horizon_h_list,
                    "horizon_day": horizon_day_list,
                    "p05": [round(default_val * 0.85, 1)] * 168,
                    "p10": [round(default_val * 0.90, 1)] * 168,
                    "p50": [round(default_val, 1)] * 168,
                    "p90": [round(default_val * 1.10, 1)] * 168,
                    "p95": [round(default_val * 1.15, 1)] * 168,
                }
            )
            return sort_quantiles(df)

        targets_df = pd.DataFrame({"ts": target_hours})
        features_sub = self.features_df[["ts", "wx_temp_c", "wx_cdh_24"]].copy()
        merged = pd.merge(targets_df, features_sub, on="ts", how="left")
        merged["wx_temp_c"] = merged["wx_temp_c"].ffill().bfill().fillna(30.0)
        merged["wx_cdh_24"] = merged["wx_cdh_24"].ffill().bfill().fillna(50.0)

        future_df = pd.DataFrame(
            {
                "ds": merged["ts"].dt.tz_localize(None),
                "wx_temp_c": merged["wx_temp_c"].to_numpy(),
                "wx_cdh_24": merged["wx_cdh_24"].to_numpy(),
            }
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = self.model.predict(future_df)

        yhat = forecast["yhat"].to_numpy()

        q_name_map = {
            0.05: "p05",
            0.10: "p10",
            0.50: "p50",
            0.90: "p90",
            0.95: "p95",
        }

        pred_dict = {
            "target_ts": target_hours,
            "horizon_h": horizon_h_list,
            "horizon_day": horizon_day_list,
        }

        for q in self.quantiles:
            col_name = q_name_map.get(q, f"p{int(q*100):02d}")
            vals = []
            for i, t in enumerate(target_hours):
                h = int(t.hour)
                shift = self.residual_quantiles.get(h, {}).get(q, 0.0)
                vals.append(round(float(yhat[i] + shift), 1))
            pred_dict[col_name] = vals

        df = pd.DataFrame(pred_dict)
        return sort_quantiles(df)
