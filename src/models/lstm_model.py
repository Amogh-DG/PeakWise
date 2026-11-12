import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from src.backtest.registry import register
from src.common import config as cfg_module
from src.common import constants, paths
from src.models.quantile_utils import sort_quantiles

LSTM_FEATURES = [
    "load_mw",
    "wx_temp_c",
    "wx_cdh",
    "cal_hour_sin",
    "cal_hour_cos",
    "cal_dow_sin",
    "cal_dow_cos",
    "cal_is_holiday",
]
N_FEATURES = len(LSTM_FEATURES)
SEQ_LEN = 168
N_HORIZONS = 168
N_QUANTILES = 5
QUANTILES = [0.05, 0.1, 0.5, 0.9, 0.95]


class LSTMNet(nn.Module):
    def __init__(self, hidden: int, seed: int):
        super().__init__()
        torch.manual_seed(seed)
        self.lstm = nn.LSTM(
            input_size=N_FEATURES,
            hidden_size=hidden,
            num_layers=2,
            batch_first=True,
            dropout=0.1,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden * 2),
            nn.ReLU(),
            nn.Linear(hidden * 2, N_HORIZONS * N_QUANTILES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, (h, _) = self.lstm(x)
        last_hidden = h[-1]
        out = self.head(last_hidden)
        return out.view(-1, N_HORIZONS, N_QUANTILES)


def _pinball_loss(pred: torch.Tensor, target: torch.Tensor, quantiles: list[float]) -> torch.Tensor:
    q = torch.tensor(quantiles, dtype=torch.float32).view(1, 1, N_QUANTILES)
    target_exp = target.unsqueeze(-1).expand_as(pred)
    err = target_exp - pred
    loss = torch.max(q * err, (q - 1.0) * err)
    return loss.mean()


def _load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    pdir = paths.processed_dir()
    load_path = pdir / "load_hourly.parquet"
    feat_path = pdir / "features_known.parquet"
    if not load_path.exists():
        pdir = paths.repo_root() / "data" / "processed_mock"
        load_path = pdir / "load_hourly.parquet"
        feat_path = pdir / "features_known.parquet"
    load_df = pd.read_parquet(load_path)
    feat_df = pd.read_parquet(feat_path)
    return load_df, feat_df


def _build_merged(load_df: pd.DataFrame, feat_df: pd.DataFrame) -> pd.DataFrame:
    if not pd.api.types.is_datetime64_any_dtype(load_df["ts"]):
        load_df = load_df.copy()
        load_df["ts"] = pd.to_datetime(load_df["ts"], utc=True).dt.tz_convert(constants.TZ)
    if not pd.api.types.is_datetime64_any_dtype(feat_df.index):
        feat_df = feat_df.copy()
        feat_df.index = pd.to_datetime(feat_df.index, utc=True).dt.tz_convert(constants.TZ)
    else:
        feat_df = feat_df.copy()
        if feat_df.index.tz is None:
            feat_df.index = feat_df.index.tz_localize(constants.TZ)
        else:
            feat_df.index = feat_df.index.tz_convert(constants.TZ)

    load_df = load_df.set_index("ts").sort_index()
    feat_df = feat_df.sort_index()

    merged = load_df[["load_mw"]].join(feat_df[LSTM_FEATURES[1:]], how="left")
    merged = merged[LSTM_FEATURES]
    return merged


@register("lstm")
class LSTMForecaster:
    calibrate = True
    name = "lstm"

    def __init__(self, cfg: dict):
        self._cfg = cfg
        lstm_cfg = cfg.get("models", {}).get("lstm", {})
        self._epochs = int(lstm_cfg.get("epochs", 30))
        self._hidden = int(lstm_cfg.get("hidden", 64))
        self._max_minutes = float(lstm_cfg.get("max_minutes", 10))
        self._retrain_every = int(lstm_cfg.get("retrain_every_n_folds", 3))
        self._seed = int(cfg.get("seed", 42))
        self._model: LSTMNet | None = None
        self._feat_mean: np.ndarray | None = None
        self._feat_std: np.ndarray | None = None
        self._tgt_mean: float = 0.0
        self._tgt_std: float = 1.0
        self._fold_count = 0
        self._merged: pd.DataFrame | None = None
        self._start_wall: float = time.time()

    def _get_merged(self) -> pd.DataFrame:
        if self._merged is None:
            load_df, feat_df = _load_data()
            self._merged = _build_merged(load_df, feat_df)
        return self._merged

    def _build_windows(self, train_end: pd.Timestamp) -> tuple[np.ndarray, np.ndarray]:
        merged = self._get_merged()
        sub = merged[merged.index <= train_end].ffill().bfill()
        vals = sub.to_numpy(dtype=np.float32)
        X, y = [], []
        step = 24
        i = SEQ_LEN
        while i + N_HORIZONS <= len(vals):
            X.append(vals[i - SEQ_LEN : i])
            y.append(vals[i : i + N_HORIZONS, 0])
            i += step
        return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    def _normalize_X(self, X: np.ndarray) -> np.ndarray:
        return (X - self._feat_mean) / (self._feat_std + 1e-8)

    def _normalize_y(self, y: np.ndarray) -> np.ndarray:
        return (y - self._tgt_mean) / (self._tgt_std + 1e-8)

    def _denormalize_y(self, y: np.ndarray) -> np.ndarray:
        return y * self._tgt_std + self._tgt_mean

    def fit(self, train_end: pd.Timestamp) -> None:
        self._fold_count += 1
        budget_elapsed = (time.time() - self._start_wall) / 60.0
        if self._model is not None and (self._fold_count - 1) % self._retrain_every != 0:
            return
        if budget_elapsed >= self._max_minutes:
            return

        X, y = self._build_windows(train_end)
        if len(X) < 10:
            return

        self._feat_mean = X.mean(axis=(0, 1), keepdims=True)
        self._feat_std = X.std(axis=(0, 1), keepdims=True)
        self._tgt_mean = float(y.mean())
        self._tgt_std = float(y.std()) + 1e-8

        X_n = self._normalize_X(X)
        y_n = self._normalize_y(y)

        val_cut = max(1, int(len(X_n) * 0.15))
        X_tr, X_val = X_n[:-val_cut], X_n[-val_cut:]
        y_tr, y_val = y_n[:-val_cut], y_n[-val_cut:]

        X_tr_t = torch.tensor(X_tr)
        y_tr_t = torch.tensor(y_tr)
        X_val_t = torch.tensor(X_val)
        y_val_t = torch.tensor(y_val)

        torch.manual_seed(self._seed)
        model = LSTMNet(self._hidden, self._seed)
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)

        best_val = float("inf")
        patience = 5
        no_improve = 0
        batch_size = 32

        for epoch in range(self._epochs):
            elapsed_min = (time.time() - self._start_wall) / 60.0
            if elapsed_min >= self._max_minutes:
                break

            model.train()
            idx = torch.randperm(len(X_tr_t))
            for start in range(0, len(X_tr_t), batch_size):
                b = idx[start : start + batch_size]
                opt.zero_grad()
                pred = model(X_tr_t[b])
                loss = _pinball_loss(pred, y_tr_t[b], QUANTILES)
                loss.backward()
                opt.step()

            model.eval()
            with torch.no_grad():
                val_pred = model(X_val_t)
                val_loss = _pinball_loss(val_pred, y_val_t, QUANTILES).item()

            if val_loss < best_val - 1e-6:
                best_val = val_loss
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        model.eval()
        self._model = model

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        merged = self._get_merged()
        sub = merged[merged.index < origin].ffill().bfill()
        if len(sub) < SEQ_LEN or self._model is None:
            horizons = range(1, N_HORIZONS + 1)
            rows = []
            for h in horizons:
                ts = origin + pd.Timedelta(hours=h)
                rows.append({
                    "target_ts": ts,
                    "horizon_h": h,
                    "horizon_day": int(np.ceil(h / 24)),
                    "p05": 0.0, "p10": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0,
                })
            return pd.DataFrame(rows)

        window = sub.iloc[-SEQ_LEN:].to_numpy(dtype=np.float32)
        X = window[np.newaxis, :, :]
        X_n = self._normalize_X(X)
        X_t = torch.tensor(X_n)

        with torch.no_grad():
            out = self._model(X_t).numpy()[0]

        out_denorm = self._denormalize_y(out)

        rows = []
        for h in range(N_HORIZONS):
            ts = origin + pd.Timedelta(hours=h + 1)
            q = np.sort(out_denorm[h])
            rows.append({
                "target_ts": ts,
                "horizon_h": h + 1,
                "horizon_day": int(np.ceil((h + 1) / 24)),
                "p05": float(q[0]),
                "p10": float(q[1]),
                "p50": float(q[2]),
                "p90": float(q[3]),
                "p95": float(q[4]),
            })

        df = pd.DataFrame(rows)
        return sort_quantiles(df)
