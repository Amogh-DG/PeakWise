from typing import Protocol
import pandas as pd


class Forecaster(Protocol):
    name: str

    def fit(self, train_end: pd.Timestamp) -> None:
        ...

    def predict(self, origin: pd.Timestamp) -> pd.DataFrame:
        ...
