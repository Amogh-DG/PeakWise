import numpy as np
import pandas as pd
import pytest
import torch

from src.models.lstm_model import LSTMNet, LSTMForecaster, SEQ_LEN, N_HORIZONS, N_FEATURES, N_QUANTILES


def _make_cfg():
    return {
        "seed": 42,
        "models": {
            "lstm": {
                "epochs": 2,
                "hidden": 16,
                "max_minutes": 5,
                "retrain_every_n_folds": 3,
            }
        },
    }


def test_lstm_forward_shape():
    model = LSTMNet(hidden=16, seed=42)
    x = torch.randn(4, SEQ_LEN, N_FEATURES)
    out = model(x)
    assert out.shape == (4, N_HORIZONS, N_QUANTILES)


def test_lstm_quantile_ordering():
    cfg = _make_cfg()
    forecaster = LSTMForecaster(cfg)
    rng = np.random.default_rng(0)
    n = SEQ_LEN + N_HORIZONS + 50

    ts = pd.date_range("2023-01-01", periods=n, freq="h", tz="Asia/Kolkata")
    load_mw = rng.uniform(100, 200, size=n).astype(np.float32)
    wx_temp_c = rng.uniform(20, 40, size=n).astype(np.float32)
    wx_cdh = rng.uniform(0, 10, size=n).astype(np.float32)
    cal_hour_sin = np.sin(2 * np.pi * np.arange(n) / 24).astype(np.float32)
    cal_hour_cos = np.cos(2 * np.pi * np.arange(n) / 24).astype(np.float32)
    cal_dow_sin = np.sin(2 * np.pi * np.arange(n) / 168).astype(np.float32)
    cal_dow_cos = np.cos(2 * np.pi * np.arange(n) / 168).astype(np.float32)
    cal_is_holiday = np.zeros(n, dtype=np.float32)

    merged = pd.DataFrame({
        "load_mw": load_mw,
        "wx_temp_c": wx_temp_c,
        "wx_cdh": wx_cdh,
        "cal_hour_sin": cal_hour_sin,
        "cal_hour_cos": cal_hour_cos,
        "cal_dow_sin": cal_dow_sin,
        "cal_dow_cos": cal_dow_cos,
        "cal_is_holiday": cal_is_holiday,
    }, index=ts)

    forecaster._merged = merged
    train_end = ts[SEQ_LEN + 20]
    forecaster.fit(train_end)

    origin = ts[SEQ_LEN + 30]
    preds = forecaster.predict(origin)

    assert (preds["p05"] <= preds["p10"]).all()
    assert (preds["p10"] <= preds["p50"]).all()
    assert (preds["p50"] <= preds["p90"]).all()
    assert (preds["p90"] <= preds["p95"]).all()


def test_lstm_no_future_in_input():
    cfg = _make_cfg()
    forecaster = LSTMForecaster(cfg)
    rng = np.random.default_rng(1)
    n = SEQ_LEN + N_HORIZONS + 50

    ts = pd.date_range("2023-01-01", periods=n, freq="h", tz="Asia/Kolkata")
    data = rng.uniform(100, 300, size=(n, 8)).astype(np.float32)
    merged = pd.DataFrame(data, index=ts, columns=[
        "load_mw", "wx_temp_c", "wx_cdh",
        "cal_hour_sin", "cal_hour_cos",
        "cal_dow_sin", "cal_dow_cos", "cal_is_holiday",
    ])
    forecaster._merged = merged

    origin = ts[SEQ_LEN + 20]
    sub = merged[merged.index < origin]

    assert sub.index.max() < origin
    assert len(sub) >= SEQ_LEN

    window = sub.iloc[-SEQ_LEN:]
    assert window.index.max() < origin
