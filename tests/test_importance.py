import json
import numpy as np
import pandas as pd
import pytest
import lightgbm as lgb

from src.common import paths
from src.models.feature_groups import FEATURE_GROUPS, group_of
from src.models.importance import compute_shap_importance_for_booster
from src.models.training_table import FEATURE_COLS

VALID_GROUPS = {
    "calendar",
    "festival",
    "event",
    "weather",
    "thermal_inertia",
    "trend",
    "autoregressive",
    "horizon",
}


def test_every_feature_has_a_valid_group():
    for f in FEATURE_GROUPS:
        grp = group_of(f)
        assert grp in VALID_GROUPS

    for f in FEATURE_COLS:
        grp = group_of(f)
        assert grp in VALID_GROUPS


def test_compute_shap_importance_for_booster_normalization():
    np.random.seed(42)
    n = 200
    p = 10
    feature_names = [f"feat_{i}" for i in range(p)]
    x_df = pd.DataFrame(np.random.randn(n, p), columns=feature_names)
    y = np.random.randn(n)

    ds = lgb.Dataset(x_df, label=y, free_raw_data=False)
    params = {"objective": "regression", "verbose": -1, "seed": 42}
    booster = lgb.train(params, ds, num_boost_round=10)

    peak_mask = np.array([i % 2 == 0 for i in range(n)])

    all_list, top_peak, top_off = compute_shap_importance_for_booster(booster, x_df, peak_mask)

    total_imp = sum(item["importance"] for item in all_list)
    assert pytest.approx(1.0, abs=1e-3) == total_imp

    for item in all_list:
        assert "feature" in item
        assert "importance" in item
        assert "group" in item
        assert item["group"] in VALID_GROUPS

    assert len(top_peak) <= 10
    assert len(top_off) <= 10


def test_feature_importance_mock_artifact():
    mock_file = paths.repo_root() / "artifacts_mock" / "feature_importance.json"
    if not mock_file.exists():
        pytest.skip("Mock artifact not present")

    with open(mock_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "models" in data
    for model_name, feats in data["models"].items():
        total_imp = sum(item["importance"] for item in feats)
        assert pytest.approx(1.0, abs=1e-2) == total_imp
        for item in feats:
            assert item["group"] in VALID_GROUPS
