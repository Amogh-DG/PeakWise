from pathlib import Path
import pandas as pd
from src.backtest.registry import register
from src.common import constants, paths


def get_load_path() -> Path:
    p = paths.processed_dir() / "load_hourly.parquet"
    if not p.exists():
        mock_p = paths.repo_root() / "data" / "processed_mock" / "load_hourly.parquet"
        if mock_p.exists():
            return mock_p
    return p


@register("persistence")
class PersistenceForecaster:
    name: str = "persistence"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.train_end: pd.Timestamp | None = None
        self.last_train_load: float = 4000.0

    def fit(self, train_end: pd.Timestamp) -> None:
        self.train_end = train_end
        load_path = get_load_path()
        if load_path.exists():
            load_df = pd.read_parquet(load_path)
            train_load = load_df[load_df["ts"] < train_end]
            if not train_load.empty:
                self.last_train_load = float(train_load["load_mw"].iloc[-1])

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        load_path = get_load_path()
        last_val = self.last_train_load
        if load_path.exists():
            load_df = pd.read_parquet(load_path)
            known_load = load_df[load_df["ts"] < origin]
            if not known_load.empty:
                last_val = float(known_load["load_mw"].iloc[-1])

        start_target = (origin + pd.Timedelta(days=1)).floor("D")
        target_hours = pd.date_range(start=start_target, periods=168, freq="h", tz=constants.TZ)

        p50 = round(last_val, 1)
        p10 = round(p50 - 150.0, 1)
        p05 = round(p50 - 250.0, 1)
        p90 = round(p50 + 150.0, 1)
        p95 = round(p50 + 250.0, 1)

        horizon_h_vals = [(int((t - origin).total_seconds() // 3600)) for t in target_hours]
        horizon_day_vals = [int(h // 24 + 1) for h in range(168)]

        return pd.DataFrame(
            {
                "target_ts": target_hours,
                "horizon_h": horizon_h_vals,
                "horizon_day": horizon_day_vals,
                "p05": [p05] * 168,
                "p10": [p10] * 168,
                "p50": [p50] * 168,
                "p90": [p90] * 168,
                "p95": [p95] * 168,
            }
        )
