from dataclasses import dataclass
import pandas as pd
from src.common import constants


@dataclass
class Fold:
    fold_id: int
    train_end: pd.Timestamp
    origins: list[pd.Timestamp]


def make_folds(index: pd.DatetimeIndex, cfg: dict) -> list[Fold]:
    if len(index) == 0:
        return []

    backtest_cfg = cfg.get("backtest", {})
    min_train_days = int(backtest_cfg.get("min_train_days", 730))
    retrain_every_days = int(backtest_cfg.get("retrain_every_days", 30))
    test_months = int(backtest_cfg.get("test_months", 12))
    origin_hour = int(cfg.get("origin_hour_local", 10))
    tz = cfg.get("timezone", constants.TZ)

    start_ts = index.min().tz_convert(tz)
    end_ts = index.max().tz_convert(tz)

    earliest_by_train = (start_ts.floor("D") + pd.Timedelta(days=min_train_days)).floor("D") + pd.Timedelta(hours=origin_hour)
    earliest_by_months = (end_ts.floor("D") - pd.DateOffset(months=test_months)).floor("D") + pd.Timedelta(days=1, hours=origin_hour)

    if earliest_by_months >= earliest_by_train:
        start_origin = earliest_by_months
    else:
        start_origin = earliest_by_train

    latest_target = end_ts
    latest_origin_raw = latest_target - pd.Timedelta(hours=181)
    latest_origin = latest_origin_raw.floor("D") + pd.Timedelta(hours=origin_hour)
    if latest_origin + pd.Timedelta(hours=181) > latest_target:
        latest_origin = latest_origin - pd.Timedelta(days=1)

    if start_origin > latest_origin:
        return []

    test_origins = pd.date_range(start=start_origin, end=latest_origin, freq="D", tz=tz)
    if len(test_origins) == 0:
        return []

    folds = []
    fold_id = 0
    for i in range(0, len(test_origins), retrain_every_days):
        fold_origins = [pd.Timestamp(o) for o in test_origins[i : i + retrain_every_days]]
        if not fold_origins:
            continue
        train_end = fold_origins[0]
        folds.append(Fold(fold_id=fold_id, train_end=train_end, origins=fold_origins))
        fold_id += 1

    return folds
