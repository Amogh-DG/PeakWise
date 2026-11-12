import json
from pathlib import Path
import numpy as np
import pandas as pd
import shap

from src.backtest.folds import make_folds
from src.backtest.registry import get_forecaster
from src.common import config, constants, paths
from src.models.feature_groups import group_of
from src.models.training_table import FEATURE_COLS, build_features_for_origin


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


def compute_shap_importance_for_booster(
    booster,
    x_df: pd.DataFrame,
    peak_mask: np.ndarray,
) -> tuple[list[dict], list[dict], list[dict]]:
    explainer = shap.TreeExplainer(booster)
    x_arr = np.ascontiguousarray(x_df.to_numpy(dtype=np.float32))
    shap_vals = explainer.shap_values(x_arr)

    if isinstance(shap_vals, list):
        shap_matrix = np.array(shap_vals[0])
    else:
        shap_matrix = np.array(shap_vals)

    features = list(x_df.columns)

    mean_abs_all = np.mean(np.abs(shap_matrix), axis=0)
    sum_all = float(np.sum(mean_abs_all))
    if sum_all > 0:
        norm_all = mean_abs_all / sum_all
    else:
        norm_all = np.ones(len(features)) / len(features)

    all_list = []
    for f, imp in zip(features, norm_all):
        all_list.append({"feature": f, "importance": round(float(imp), 4), "group": group_of(f)})
    all_list.sort(key=lambda x: x["importance"], reverse=True)

    diff = 1.0 - sum(x["importance"] for x in all_list)
    if all_list:
        all_list[0]["importance"] = round(all_list[0]["importance"] + diff, 4)

    if np.any(peak_mask):
        peak_shap = np.mean(np.abs(shap_matrix[peak_mask]), axis=0)
        p_sum = float(np.sum(peak_shap))
        peak_norm = peak_shap / p_sum if p_sum > 0 else np.ones(len(features)) / len(features)
        peak_list = []
        for f, imp in zip(features, peak_norm):
            peak_list.append({"feature": f, "importance": round(float(imp), 4), "group": group_of(f)})
        peak_list.sort(key=lambda x: x["importance"], reverse=True)
        top_peak = peak_list[:10]
    else:
        top_peak = all_list[:10]

    off_mask = ~peak_mask
    if np.any(off_mask):
        off_shap = np.mean(np.abs(shap_matrix[off_mask]), axis=0)
        o_sum = float(np.sum(off_shap))
        off_norm = off_shap / o_sum if o_sum > 0 else np.ones(len(features)) / len(features)
        off_list = []
        for f, imp in zip(features, off_norm):
            off_list.append({"feature": f, "importance": round(float(imp), 4), "group": group_of(f)})
        off_list.sort(key=lambda x: x["importance"], reverse=True)
        top_off = off_list[:10]
    else:
        top_off = all_list[:10]

    return all_list, top_peak, top_off


def run_feature_importance() -> tuple[dict, dict]:
    cfg = config.load_config()

    load_path = get_load_path()
    features_path = get_features_path()

    if not load_path.exists() or not features_path.exists():
        raise FileNotFoundError("Missing load or features data for importance calculation.")

    load_df = pd.read_parquet(load_path)
    features_df = pd.read_parquet(features_path)
    load_index = pd.DatetimeIndex(load_df["ts"])

    folds = make_folds(load_index, cfg)
    if not folds:
        raise ValueError("No folds available.")

    latest_fold = folds[-1]

    lgbm_forecaster = get_forecaster("lgbm", cfg)
    lgbm_forecaster.fit(latest_fold.train_end)

    if not lgbm_forecaster.models or 0.5 not in lgbm_forecaster.models:
        raise ValueError("LGBM model p50 failed to fit.")

    p50_booster = lgbm_forecaster.models[0.5]

    sample_origins = latest_fold.origins
    if len(sample_origins) > 30:
        step = len(sample_origins) // 30
        sample_origins = sample_origins[::step][:30]

    known_load = load_df[load_df["ts"] < latest_fold.train_end].copy()

    feature_dfs = []
    target_hours_list = []
    for orig in sample_origins:
        f_orig = build_features_for_origin(known_load, features_df, orig, cfg)
        feature_dfs.append(f_orig)
        target_hours_list.extend(f_orig.index.tolist())

    if not feature_dfs:
        raise ValueError("Failed to build feature samples.")

    combined_x = pd.concat(feature_dfs, ignore_index=True)
    if len(combined_x) > 5000:
        combined_x = combined_x.iloc[:5000].copy()
        target_hours_list = target_hours_list[:5000]

    peak_hours_set = set(constants.PEAK_HOURS)
    peak_mask = np.array([pd.Timestamp(t).hour in peak_hours_set for t in target_hours_list])

    lgbm_all, lgbm_peak, lgbm_off = compute_shap_importance_for_booster(
        p50_booster, combined_x, peak_mask
    )

    models_output = {"lgbm": lgbm_all}
    by_segment_output = {"lgbm": {"peak_hours": lgbm_peak, "off_peak": lgbm_off}}

    try:
        xgb_forecaster = get_forecaster("xgboost", cfg)
        xgb_forecaster.fit(latest_fold.train_end)
        if xgb_forecaster.models and 0.5 in xgb_forecaster.models:
            xgb_booster = xgb_forecaster.models[0.5]
            xgb_all, xgb_peak, xgb_off = compute_shap_importance_for_booster(
                xgb_booster, combined_x, peak_mask
            )
            models_output["xgboost"] = xgb_all
            by_segment_output["xgboost"] = {"peak_hours": xgb_peak, "off_peak": xgb_off}
    except Exception:
        pass

    out_file = paths.artifacts_dir() / "feature_importance.json"
    out_file_seg = paths.artifacts_dir() / "feature_importance_by_segment.json"
    paths.artifacts_dir().mkdir(parents=True, exist_ok=True)

    final_importance = {"models": models_output}

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_importance, f, indent=2)

    with open(out_file_seg, "w", encoding="utf-8") as f:
        json.dump(by_segment_output, f, indent=2)

    return final_importance, by_segment_output


def main():
    final_imp, seg_imp = run_feature_importance()
    print("Feature importance calculation complete.")
    for model_name, feats in final_imp.get("models", {}).items():
        print(f"\nTop 10 features for {model_name}:")
        for f in feats[:10]:
            print(f"  {f['feature']:<30} {f['importance']:.4f}  ({f['group']})")


if __name__ == "__main__":
    main()
