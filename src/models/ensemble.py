import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.backtest.registry import REGISTRY, get_forecaster, register
from src.common import constants, paths
from src.metrics.accuracy_table import build_accuracy_table, print_compact_table
from src.models.calibration import calibrate
from src.models.daily_summary import export_daily_peak_summary
from src.models.quantile_utils import sort_quantiles


def get_validation_origins(
    train_end: pd.Timestamp,
    val_days: int = 30,
) -> list[pd.Timestamp]:
    val_end = (train_end - pd.Timedelta(days=8)).floor("D") + pd.Timedelta(hours=train_end.hour)
    val_start = val_end - pd.Timedelta(days=val_days - 1)
    if val_start > val_end:
        return []
    origins = pd.date_range(start=val_start, end=val_end, freq="D", tz=train_end.tz)
    return [pd.Timestamp(o) for o in origins]


def optimize_weights_for_horizon(
    preds_by_model: list[np.ndarray],
    y_true: np.ndarray,
    quantiles: list[float],
) -> np.ndarray:
    n_models = len(preds_by_model)
    if n_models == 0:
        return np.array([])
    if n_models == 1:
        return np.array([1.0])

    n_samples = len(y_true)
    if n_samples == 0:
        return np.full(n_models, 1.0 / n_models)

    q_arr = np.array(quantiles, dtype=float)

    def pinball_loss_objective(w: np.ndarray) -> float:
        ens_preds = np.zeros((n_samples, len(q_arr)), dtype=float)
        for m_idx in range(n_models):
            ens_preds += w[m_idx] * preds_by_model[m_idx]
        diff = y_true[:, None] - ens_preds
        loss = np.maximum(q_arr * diff, (q_arr - 1.0) * diff)
        return float(np.mean(loss))

    w0 = np.full(n_models, 1.0 / n_models)
    bounds = [(0.0, 1.0) for _ in range(n_models)]
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    res = minimize(
        pinball_loss_objective,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 200, "ftol": 1e-6},
    )

    if res.success:
        w_res = np.maximum(0.0, res.x)
        sum_w = np.sum(w_res)
        if sum_w > 0:
            return w_res / sum_w

    return w0


def combine_quantile_predictions(
    base_preds: dict[str, pd.DataFrame],
    weights_by_horizon: dict[int, dict[str, float]],
    quantiles: list[float],
) -> pd.DataFrame:
    models = list(base_preds.keys())
    first_df = base_preds[models[0]]

    res_df = pd.DataFrame(
        {
            "target_ts": first_df["target_ts"],
            "horizon_h": first_df["horizon_h"],
            "horizon_day": first_df["horizon_day"],
        }
    )

    q_cols = ["p05", "p10", "p50", "p90", "p95"]

    for col in q_cols:
        res_df[col] = 0.0

    for h_day, group in res_df.groupby("horizon_day"):
        indices = group.index
        h_weights = weights_by_horizon.get(int(h_day), {m: 1.0 / len(models) for m in models})

        for col in q_cols:
            accum = np.zeros(len(indices), dtype=float)
            for m in models:
                w = h_weights.get(m, 0.0)
                if w > 0:
                    accum += w * base_preds[m].loc[indices, col].to_numpy(dtype=float)
            res_df.loc[indices, col] = np.round(accum, 1)

    return sort_quantiles(res_df)


@register("ensemble")
class EnsembleForecaster:
    name: str = "ensemble"
    calibrate: bool = True

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.quantiles = [float(q) for q in self.cfg.get("quantiles", constants.QUANTILES)]
        self.train_end: pd.Timestamp | None = None
        self.weights_by_horizon: dict[int, dict[str, float]] = {}
        self.base_models: list[str] = []
        self._cached_preds_df: pd.DataFrame | None = None
        self._fallback_forecasters: dict[str, object] = {}

    def _get_candidate_models(self) -> list[str]:
        cfg_models = self.cfg.get("models", {}).get("ensemble", {}).get("models", None)
        if cfg_models:
            return [m for m in cfg_models if m in REGISTRY and m != "ensemble"]

        all_candidates = ["lgbm", "xgboost", "prophet", "lstm", "linear"]
        return [m for m in all_candidates if m in REGISTRY]

    def _get_preds_df(self) -> pd.DataFrame:
        if self._cached_preds_df is not None:
            return self._cached_preds_df

        pred_file = paths.artifacts_dir() / "predictions_backtest.parquet"
        if not pred_file.exists():
            mock_file = paths.repo_root() / "artifacts_mock" / "predictions_backtest.parquet"
            if mock_file.exists():
                pred_file = mock_file

        if pred_file.exists():
            self._cached_preds_df = pd.read_parquet(pred_file)
        else:
            self._cached_preds_df = pd.DataFrame()

        return self._cached_preds_df

    def fit(self, train_end: pd.Timestamp) -> None:
        self.train_end = train_end
        candidates = self._get_candidate_models()

        val_days = int(self.cfg.get("models", {}).get("ensemble", {}).get("val_days", 30))
        val_origins = get_validation_origins(train_end, val_days)

        df_preds = self._get_preds_df()
        available_in_file = set(df_preds["model"].unique()) if not df_preds.empty and "model" in df_preds.columns else set()
        active_models = [m for m in candidates if m in available_in_file]
        if not active_models:
            active_models = [m for m in candidates if m in ("lgbm", "linear")]
        if not active_models:
            active_models = ["seasonal_naive"]

        self.base_models = active_models

        q_cols = ["p05", "p10", "p50", "p90", "p95"]

        for h in range(1, 8):
            preds_m_list = []
            y_arr = None

            if not df_preds.empty and val_origins:
                sub_val = df_preds[
                    (df_preds["origin_ts"].isin(val_origins))
                    & (df_preds["horizon_day"] == h)
                    & (df_preds["y_true"].notna())
                ]

                has_all_models = all(m in sub_val["model"].values for m in self.base_models)
                if has_all_models:
                    model_dfs = {
                        m: sub_val[sub_val["model"] == m].sort_values(["origin_ts", "target_ts"])
                        for m in self.base_models
                    }
                    first_m = self.base_models[0]
                    first_len = len(model_dfs[first_m])

                    if first_len > 0 and all(len(model_dfs[m]) == first_len for m in self.base_models):
                        y_arr = model_dfs[first_m]["y_true"].to_numpy(dtype=float)
                        for m in self.base_models:
                            preds_m_list.append(model_dfs[m][q_cols].to_numpy(dtype=float))

            if y_arr is not None and len(y_arr) > 0 and len(preds_m_list) == len(self.base_models):
                w_vec = optimize_weights_for_horizon(preds_m_list, y_arr, self.quantiles)
            else:
                w_vec = np.full(len(self.base_models), 1.0 / len(self.base_models))

            self.weights_by_horizon[h] = {
                m: float(w_vec[idx]) for idx, m in enumerate(self.base_models)
            }

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        df_preds = self._get_preds_df()

        base_preds_dict = {}
        for m in self.base_models:
            sub = pd.DataFrame()
            if not df_preds.empty:
                sub = df_preds[(df_preds["model"] == m) & (df_preds["origin_ts"] == origin)].sort_values("target_ts")

            if len(sub) == 168:
                base_preds_dict[m] = sub.reset_index(drop=True)
            else:
                if m not in self._fallback_forecasters:
                    fc = get_forecaster(m, self.cfg)
                    fc.fit(origin)
                    self._fallback_forecasters[m] = fc
                pred_df = self._fallback_forecasters[m].predict(origin)
                base_preds_dict[m] = pred_df.reset_index(drop=True)

        return combine_quantile_predictions(
            base_preds_dict,
            self.weights_by_horizon,
            self.quantiles,
        )


def generate_ensemble_predictions(df_all: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    candidates = ["lgbm", "xgboost", "prophet", "lstm", "linear"]
    available = [m for m in candidates if m in df_all["model"].unique() and m != "ensemble"]
    if not available:
        available = [m for m in ["lgbm", "linear"] if m in df_all["model"].unique()]
    if not available:
        available = ["seasonal_naive"]

    q_cols = ["p05", "p10", "p50", "p90", "p95"]
    quantiles = [float(q) for q in cfg.get("quantiles", constants.QUANTILES)]

    calib_cfg = cfg.get("calibration", {})
    window_days = int(calib_cfg.get("window_days", 90))

    folds = sorted(df_all["fold_id"].unique())
    ensemble_fold_dfs = []

    for fold_id in folds:
        fold_sub = df_all[(df_all["fold_id"] == fold_id) & (df_all["model"].isin(available))]
        test_origins = sorted(fold_sub["origin_ts"].unique())
        if not test_origins:
            continue

        first_test_origin = test_origins[0]

        val_origins = [o for o in df_all["origin_ts"].unique() if o < first_test_origin - pd.Timedelta(days=7)]
        val_origins = sorted(val_origins)[-30:]

        weights_by_h = {}
        for h in range(1, 8):
            preds_m_list = []
            y_arr = None

            if val_origins:
                sub_val = df_all[
                    (df_all["origin_ts"].isin(val_origins))
                    & (df_all["horizon_day"] == h)
                    & (df_all["y_true"].notna())
                ]
                has_all = all(m in sub_val["model"].values for m in available)
                if has_all:
                    m_dfs = {m: sub_val[sub_val["model"] == m].sort_values(["origin_ts", "target_ts"]) for m in available}
                    first_len = len(m_dfs[available[0]])
                    if first_len > 0 and all(len(m_dfs[m]) == first_len for m in available):
                        y_arr = m_dfs[available[0]]["y_true"].to_numpy(dtype=float)
                        for m in available:
                            preds_m_list.append(m_dfs[m][q_cols].to_numpy(dtype=float))

            if y_arr is not None and len(y_arr) > 0 and len(preds_m_list) == len(available):
                w_vec = optimize_weights_for_horizon(preds_m_list, y_arr, quantiles)
            else:
                w_vec = np.full(len(available), 1.0 / len(available))

            weights_by_h[h] = {m: float(w_vec[idx]) for idx, m in enumerate(available)}

        fold_preds = []
        for origin in test_origins:
            orig_base = {}
            for m in available:
                sub_m = fold_sub[(fold_sub["model"] == m) & (fold_sub["origin_ts"] == origin)].sort_values("target_ts")
                if len(sub_m) == 168:
                    orig_base[m] = sub_m.reset_index(drop=True)

            if len(orig_base) != len(available):
                continue

            ref_df = orig_base[available[0]]
            combined = combine_quantile_predictions(orig_base, weights_by_h, quantiles)

            combined["model"] = "ensemble"
            combined["fold_id"] = np.int32(fold_id)
            combined["origin_ts"] = origin
            combined["horizon_h"] = ref_df["horizon_h"].astype(np.int32)
            combined["horizon_day"] = ref_df["horizon_day"].astype(np.int32)
            combined["y_true"] = ref_df["y_true"]
            combined["p05_raw"] = combined["p05"].astype(float)
            combined["p10_raw"] = combined["p10"].astype(float)
            combined["p50_raw"] = combined["p50"].astype(float)
            combined["p90_raw"] = combined["p90"].astype(float)
            combined["p95_raw"] = combined["p95"].astype(float)
            combined["is_outage_suspect"] = ref_df["is_outage_suspect"].astype(bool)

            fold_preds.append(combined)

        if not fold_preds:
            continue

        raw_fold_df = pd.concat(fold_preds, ignore_index=True)

        if ensemble_fold_dfs:
            history_df = pd.concat(ensemble_fold_dfs, ignore_index=True)
            calib_sub = history_df[
                (history_df["origin_ts"] < first_test_origin)
                & (history_df["origin_ts"] >= first_test_origin - pd.Timedelta(days=window_days))
                & (history_df["y_true"].notna())
            ]
            if len(calib_sub) >= 20:
                calibrated_fold = calibrate(raw_fold_df, calib_sub, cfg)
            else:
                calibrated_fold = raw_fold_df
        else:
            calibrated_fold = raw_fold_df

        ensemble_fold_dfs.append(calibrated_fold)

    if ensemble_fold_dfs:
        return pd.concat(ensemble_fold_dfs, ignore_index=True)
    return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-weights", action="store_true", default=True)
    args = parser.parse_args()

    pred_file = paths.artifacts_dir() / "predictions_backtest.parquet"
    if not pred_file.exists():
        mock_file = paths.repo_root() / "artifacts_mock" / "predictions_backtest.parquet"
        if mock_file.exists():
            pred_file = mock_file

    if not pred_file.exists():
        raise FileNotFoundError(f"Missing backtest predictions at {pred_file}")

    df_all = pd.read_parquet(pred_file)
    from src.common.config import load_config
    cfg = load_config()

    ens_df = generate_ensemble_predictions(df_all, cfg)
    if not ens_df.empty:
        df_no_ens = df_all[df_all["model"] != "ensemble"].copy()
        df_updated = pd.concat([df_no_ens, ens_df], ignore_index=True)
        paths.artifacts_dir().mkdir(parents=True, exist_ok=True)
        df_updated.to_parquet(paths.artifacts_dir() / "predictions_backtest.parquet", index=False, compression="snappy")
        df_all = df_updated

    accuracy_data = build_accuracy_table(df_all)
    out_json = paths.artifacts_dir() / "metrics_accuracy.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(accuracy_data, f, indent=2)

    export_daily_peak_summary()

    print("Complete Accuracy Table (segment=all and segment=peak_hours):")
    print_compact_table(accuracy_data)

    print("\nLearned Weights:")
    fc = EnsembleForecaster(cfg)
    fc.fit(pd.Timestamp("2026-06-01 10:00:00", tz=constants.TZ))
    for h in sorted(fc.weights_by_horizon.keys()):
        w_strs = [f"{m}: {w:.3f}" for m, w in fc.weights_by_horizon[h].items()]
        print(f"Horizon Day {h}: " + ", ".join(w_strs))


if __name__ == "__main__":
    main()
