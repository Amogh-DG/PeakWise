from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import xgboost as xgb

from src.backtest.registry import register
from src.common import constants, paths
from src.models.quantile_utils import sort_quantiles
from src.models.training_table import build_features_for_origin, build_training_table


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


@register("xgboost")
class XGBoostQuantileForecaster:
    name: str = "xgboost"
    calibrate: bool = True

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.models: dict[float, xgb.Booster] = {}
        self.train_end: pd.Timestamp | None = None
        self.quantiles = [float(q) for q in self.cfg.get("quantiles", constants.QUANTILES)]
        self.load_df: pd.DataFrame | None = None
        self.features_df: pd.DataFrame | None = None
        self.fallback_load = 4000.0

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

        xgb_cfg = self.cfg.get("models", {}).get("xgboost", {})
        num_leaves = int(xgb_cfg.get("num_leaves", 63))
        learning_rate = float(xgb_cfg.get("learning_rate", 0.05))
        n_estimators = int(xgb_cfg.get("n_estimators", 500))
        early_stopping_rounds = int(xgb_cfg.get("early_stopping_rounds", 50))
        stride = int(xgb_cfg.get("origin_stride", 2))
        seed = int(self.cfg.get("seed", 42))

        start_origin = known_load["ts"].min().floor("D") + pd.Timedelta(days=35, hours=10)
        end_origin = train_end.floor("D") - pd.Timedelta(days=8) + pd.Timedelta(hours=10)

        if start_origin >= end_origin:
            return

        all_candidate_origins = pd.date_range(
            start=start_origin,
            end=end_origin,
            freq="D",
            tz=constants.TZ,
        )

        sampled_origins = [all_candidate_origins[i] for i in range(0, len(all_candidate_origins), stride)]
        if len(sampled_origins) < 10:
            return

        n_val = max(3, int(len(sampled_origins) * 0.15))
        train_origins = sampled_origins[:-n_val]
        val_origins = sampled_origins[-n_val:]

        x_train, y_train, w_train = build_training_table(
            known_load, self.features_df, train_origins, self.cfg
        )
        x_val, y_val, w_val = build_training_table(
            known_load, self.features_df, val_origins, self.cfg
        )

        if len(x_train) == 0 or len(x_val) == 0:
            return

        x_tr_arr = np.ascontiguousarray(x_train.to_numpy(dtype=np.float32))
        y_tr_arr = np.ascontiguousarray(y_train.to_numpy(dtype=np.float32))
        w_tr_arr = np.ascontiguousarray(w_train, dtype=np.float32)

        x_val_arr = np.ascontiguousarray(x_val.to_numpy(dtype=np.float32))
        y_val_arr = np.ascontiguousarray(y_val.to_numpy(dtype=np.float32))
        w_val_arr = np.ascontiguousarray(w_val, dtype=np.float32)

        train_dmat = xgb.DMatrix(x_tr_arr, label=y_tr_arr, weight=w_tr_arr)
        val_dmat = xgb.DMatrix(x_val_arr, label=y_val_arr, weight=w_val_arr)

        for q in self.quantiles:
            params = {
                "objective": "reg:quantileerror",
                "quantile_alpha": q,
                "max_leaves": num_leaves,
                "grow_policy": "lossguide",
                "learning_rate": learning_rate,
                "seed": seed,
                "tree_method": "hist",
                "verbosity": 0,
            }
            callbacks = []
            if early_stopping_rounds > 0 and len(x_val_arr) > 0:
                callbacks.append(xgb.callback.EarlyStopping(rounds=early_stopping_rounds, save_best=True))

            booster = xgb.train(
                params,
                train_dmat,
                num_boost_round=n_estimators,
                evals=[(val_dmat, "val")],
                callbacks=callbacks,
                verbose_eval=False,
            )
            self.models[q] = booster

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        self._load_data()
        start_target = (origin + pd.Timedelta(days=1)).floor("D")
        target_hours = pd.date_range(start=start_target, periods=168, freq="h", tz=constants.TZ)

        horizon_h_list = [int((t - origin).total_seconds() // 3600) for t in target_hours]
        horizon_day_list = [int(i // 24 + 1) for i in range(168)]

        if not self.models or self.load_df is None or self.features_df is None:
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

        known_load = self.load_df[self.load_df["ts"] < origin].copy()
        if len(known_load) == 0:
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

        feats = build_features_for_origin(known_load, self.features_df, origin, self.cfg)
        feats_arr = np.ascontiguousarray(feats.to_numpy(dtype=np.float32))
        dtest = xgb.DMatrix(feats_arr)

        pred_dict = {
            "target_ts": target_hours,
            "horizon_h": horizon_h_list,
            "horizon_day": horizon_day_list,
        }

        q_name_map = {
            0.05: "p05",
            0.10: "p10",
            0.50: "p50",
            0.90: "p90",
            0.95: "p95",
        }

        for q in self.quantiles:
            col_name = q_name_map.get(q, f"p{int(q*100):02d}")
            if q in self.models:
                preds = self.models[q].predict(dtest)
                pred_dict[col_name] = [round(float(v), 1) for v in preds]
            else:
                pred_dict[col_name] = [round(self.fallback_load, 1)] * 168

        df = pd.DataFrame(pred_dict)
        return sort_quantiles(df)
