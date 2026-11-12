import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from api.errors import ApiException
from src.common.paths import artifacts_dir


class ArtifactStore:

    def __init__(self, dir_path: Path | None = None):
        self.dir_path = dir_path or artifacts_dir()
        self._loaded_path: Path | None = None
        self._meta: dict[str, Any] | None = None
        self._procurement_defaults: dict[str, Any] | None = None
        self._metrics_accuracy: dict[str, Any] | None = None
        self._metrics_peak: dict[str, Any] | None = None
        self._error_heatmap: dict[str, Any] | None = None
        self._missed_peaks: dict[str, Any] | None = None
        self._feature_importance: dict[str, Any] | None = None
        self._predictions_df: pd.DataFrame | None = None
        self._peak_df: pd.DataFrame | None = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded and self._loaded_path == self.dir_path:
            return

        if not self.dir_path.exists():
            return

        meta_path = self.dir_path / "meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                self._meta = json.load(f)

        defaults_path = self.dir_path / "procurement_defaults.json"
        if defaults_path.exists():
            with open(defaults_path, "r", encoding="utf-8") as f:
                self._procurement_defaults = json.load(f)

        acc_path = self.dir_path / "metrics_accuracy.json"
        if acc_path.exists():
            with open(acc_path, "r", encoding="utf-8") as f:
                self._metrics_accuracy = json.load(f)

        peak_metrics_path = self.dir_path / "metrics_peak.json"
        if peak_metrics_path.exists():
            with open(peak_metrics_path, "r", encoding="utf-8") as f:
                self._metrics_peak = json.load(f)

        heatmap_path = self.dir_path / "error_heatmap.json"
        if heatmap_path.exists():
            with open(heatmap_path, "r", encoding="utf-8") as f:
                self._error_heatmap = json.load(f)

        missed_path = self.dir_path / "missed_peaks.json"
        if missed_path.exists():
            with open(missed_path, "r", encoding="utf-8") as f:
                self._missed_peaks = json.load(f)

        feat_path = self.dir_path / "feature_importance.json"
        if feat_path.exists():
            with open(feat_path, "r", encoding="utf-8") as f:
                self._feature_importance = json.load(f)

        pred_path = self.dir_path / "predictions_backtest.parquet"
        if pred_path.exists():
            self._predictions_df = pd.read_parquet(pred_path)

        peak_path = self.dir_path / "peak_predictions.parquet"
        if peak_path.exists():
            self._peak_df = pd.read_parquet(peak_path)

        self._loaded_path = self.dir_path
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def meta(self) -> dict[str, Any]:
        if self._meta is None:
            self.load()
        if self._meta is None:
            raise ApiException(500, "INTERNAL_ERROR", "meta.json not loaded")
        return self._meta

    @property
    def procurement_defaults(self) -> dict[str, Any]:
        if self._procurement_defaults is None:
            self.load()
        if self._procurement_defaults is None:
            raise ApiException(500, "INTERNAL_ERROR", "procurement_defaults.json not loaded")
        return self._procurement_defaults

    @property
    def metrics_accuracy(self) -> dict[str, Any]:
        if self._metrics_accuracy is None:
            self.load()
        if self._metrics_accuracy is None:
            raise ApiException(500, "INTERNAL_ERROR", "metrics_accuracy.json not loaded")
        return self._metrics_accuracy

    @property
    def metrics_peak(self) -> dict[str, Any]:
        if self._metrics_peak is None:
            self.load()
        if self._metrics_peak is None:
            raise ApiException(500, "INTERNAL_ERROR", "metrics_peak.json not loaded")
        return self._metrics_peak

    @property
    def error_heatmap(self) -> dict[str, Any]:
        if self._error_heatmap is None:
            self.load()
        if self._error_heatmap is None:
            raise ApiException(500, "INTERNAL_ERROR", "error_heatmap.json not loaded")
        return self._error_heatmap

    @property
    def missed_peaks(self) -> dict[str, Any]:
        if self._missed_peaks is None:
            self.load()
        if self._missed_peaks is None:
            raise ApiException(500, "INTERNAL_ERROR", "missed_peaks.json not loaded")
        return self._missed_peaks

    @property
    def feature_importance(self) -> dict[str, Any]:
        if self._feature_importance is None:
            self.load()
        if self._feature_importance is None:
            raise ApiException(500, "INTERNAL_ERROR", "feature_importance.json not loaded")
        return self._feature_importance

    @property
    def predictions_df(self) -> pd.DataFrame:
        if self._predictions_df is None:
            self.load()
        if self._predictions_df is None:
            raise ApiException(500, "INTERNAL_ERROR", "predictions_backtest.parquet not loaded")
        return self._predictions_df

    @property
    def peak_df(self) -> pd.DataFrame:
        if self._peak_df is None:
            self.load()
        if self._peak_df is None:
            raise ApiException(500, "INTERNAL_ERROR", "peak_predictions.parquet not loaded")
        return self._peak_df

    def validate_model(self, model: str) -> None:
        valid_models = self.meta.get("models", [])
        if model not in valid_models:
            raise ApiException(400, "UNKNOWN_MODEL", f"Unknown model: {model}", {"model": model, "valid_models": valid_models})

    def validate_date(self, date_str: str) -> datetime:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ApiException(400, "BAD_DATE_RANGE", f"Invalid date format: {date_str}") from exc

        backtest_range = self.meta.get("backtest_range", {})
        start_str = backtest_range.get("start")
        end_str = backtest_range.get("end")

        if start_str and end_str:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            if not (start_date <= target_date <= end_date):
                raise ApiException(
                    404,
                    "DATE_OUT_OF_RANGE",
                    f"Date {date_str} outside backtest range [{start_str}, {end_str}]",
                    {"date": date_str, "backtest_range": backtest_range},
                )

        return datetime.strptime(date_str, "%Y-%m-%d")


store = ArtifactStore()
