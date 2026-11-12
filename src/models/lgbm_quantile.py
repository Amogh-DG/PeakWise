import ctypes
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from src.backtest.registry import register
from src.common import constants, paths
from src.models.quantile_utils import sort_quantiles
from src.models.training_table import build_features_for_origin, build_training_table

lgb.basic._LIB.LGBM_DatasetSetField.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
]
lgb.basic._LIB.LGBM_DatasetSetField.restype = ctypes.c_int

lgb.basic._LIB.LGBM_DatasetCreateFromMat.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int32,
    ctypes.c_int32,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
]
lgb.basic._LIB.LGBM_DatasetCreateFromMat.restype = ctypes.c_int

lgb.basic._LIB.LGBM_DatasetFree.argtypes = [ctypes.c_void_p]
lgb.basic._LIB.LGBM_DatasetFree.restype = ctypes.c_int

lgb.basic._LIB.LGBM_BoosterFree.argtypes = [ctypes.c_void_p]
lgb.basic._LIB.LGBM_BoosterFree.restype = ctypes.c_int


def _safe_dataset_set_field(self, field_name, data):
    if not self._handle or getattr(self._handle, "value", None) is None:
        raise ValueError(f"Cannot set {field_name} before construct dataset")
    if data is None:
        lgb.basic._safe_call(
            lgb.basic._LIB.LGBM_DatasetSetField(
                self._handle,
                lgb.basic._c_str(field_name),
                None,
                ctypes.c_int(0),
                ctypes.c_int(lgb.basic._FIELD_TYPE_MAPPER[field_name]),
            )
        )
        return self
    dtype = (
        np.float64
        if field_name == "init_score"
        else (np.int32 if field_name in {"group", "position"} else np.float32)
    )
    data = lgb.basic._list_to_1d_numpy(data=data, dtype=dtype, name=field_name)
    if data.dtype in (np.float32, np.float64):
        ptr_data, type_data, keep = lgb.basic._c_float_array(data)
    elif data.dtype == np.int32:
        ptr_data, type_data, keep = lgb.basic._c_int_array(data)
    else:
        raise TypeError("Expected np.float32/64 or np.int32")
    if not hasattr(self, "_keep_refs"):
        self._keep_refs = []
    self._keep_refs.append((ptr_data, keep))
    lgb.basic._safe_call(
        lgb.basic._LIB.LGBM_DatasetSetField(
            self._handle,
            lgb.basic._c_str(field_name),
            ptr_data,
            ctypes.c_int(len(data)),
            ctypes.c_int(type_data),
        )
    )
    return self


lgb.basic.Dataset.set_field = _safe_dataset_set_field


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


@register("lgbm")
class LGBMQuantileForecaster:
    name: str = "lgbm"
    calibrate: bool = True

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.models: dict[float, lgb.Booster] = {}
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

        lgbm_cfg = self.cfg.get("models", {}).get("lgbm", {})
        num_leaves = int(lgbm_cfg.get("num_leaves", 63))
        learning_rate = float(lgbm_cfg.get("learning_rate", 0.05))
        n_estimators = int(lgbm_cfg.get("n_estimators", 500))
        early_stopping_rounds = int(lgbm_cfg.get("early_stopping_rounds", 50))
        stride = int(lgbm_cfg.get("origin_stride", 2))
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

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            train_data = lgb.Dataset(x_tr_arr, label=y_tr_arr, weight=w_tr_arr, free_raw_data=False)
            val_data = lgb.Dataset(
                x_val_arr, label=y_val_arr, weight=w_val_arr, reference=train_data, free_raw_data=False
            )
            for q in self.quantiles:
                params = {
                    "objective": "quantile",
                    "alpha": q,
                    "num_leaves": num_leaves,
                    "learning_rate": learning_rate,
                    "seed": seed,
                    "n_jobs": 1,
                    "verbose": -1,
                }
                callbacks = []
                if early_stopping_rounds > 0 and len(x_val_arr) > 0:
                    callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=False))

                booster = lgb.train(
                    params,
                    train_data,
                    num_boost_round=n_estimators,
                    valid_sets=[val_data],
                    callbacks=callbacks,
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
        x_pred = build_features_for_origin(known_load, self.features_df, origin, self.cfg)
        x_pred_arr = np.ascontiguousarray(x_pred.to_numpy(dtype=np.float32))

        q_map = {
            0.05: "p05",
            0.10: "p10",
            0.50: "p50",
            0.90: "p90",
            0.95: "p95",
        }

        preds_dict = {
            "target_ts": target_hours,
            "horizon_h": horizon_h_list,
            "horizon_day": horizon_day_list,
        }

        for q in self.quantiles:
            col_name = q_map.get(round(q, 2), f"p{int(q*100):02d}")
            if q in self.models:
                preds_dict[col_name] = np.round(self.models[q].predict(x_pred_arr), 1)
            else:
                preds_dict[col_name] = np.full(168, self.fallback_load)

        df = pd.DataFrame(preds_dict)
        return sort_quantiles(df)
