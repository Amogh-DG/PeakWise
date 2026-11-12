from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

os.environ.setdefault("MOCK", "1")

from src.procurement.advisor import _hour_cost, _interpolate_quantile, recommend


def _make_tiny_parquet(tmp_path: Path, rows: list[dict]) -> Path:
    df = pd.DataFrame(rows)
    path = tmp_path / "predictions_backtest.parquet"
    pq.write_table(pa.Table.from_pandas(df), path)
    return path


def _make_meta(tmp_path: Path, threshold_mw: float) -> Path:
    import json
    meta = {
        "version": "mock",
        "timezone": "Asia/Kolkata",
        "origin_hour_local": 10,
        "data_range": {"start": "2024-01-01", "end": "2024-12-31"},
        "backtest_range": {"start": "2024-01-02", "end": "2024-12-31"},
        "quantiles": [0.05, 0.1, 0.5, 0.9, 0.95],
        "peak_threshold_mw_latest": threshold_mw,
        "peak_definition": "",
        "season_definition": "",
        "peak_hours": [],
        "models": [],
        "weather_proxy_note": "",
    }
    path = tmp_path / "meta.json"
    path.write_text(json.dumps(meta))
    return path


def _procurement_defaults(tmp_path: Path) -> Path:
    import json
    data = {
        "tariff": {
            "da_price_inr_per_mwh": 5000,
            "under_price_inr_per_mwh": 12000,
            "resale_price_inr_per_mwh": 2500,
        },
        "disclaimer": "Illustrative placeholder values.",
        "default_risk_quantile": 0.9,
    }
    path = tmp_path / "procurement_defaults.json"
    path.write_text(json.dumps(data))
    return path


def _build_rows_for_days(
    target_dates: list[date],
    model: str,
    p05: float,
    p10: float,
    p50: float,
    p90: float,
    p95: float,
    y_true: float,
) -> list[dict]:
    rows = []
    for d in target_dates:
        origin_day = d - __import__("datetime").timedelta(days=1)
        origin_ts = pd.Timestamp(f"{origin_day.isoformat()} 10:00:00", tz="Asia/Kolkata")
        for h in range(24):
            target_ts = pd.Timestamp(f"{d.isoformat()} {h:02d}:00:00", tz="Asia/Kolkata")
            rows.append({
                "model": model,
                "fold_id": 0,
                "origin_ts": origin_ts,
                "target_ts": target_ts,
                "horizon_h": 14 + h,
                "horizon_day": 1,
                "y_true": y_true,
                "p05": p05,
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p05_raw": p05,
                "p10_raw": p10,
                "p50_raw": p50,
                "p90_raw": p90,
                "p95_raw": p95,
                "is_outage_suspect": False,
            })
    return rows


class TestHourCost:
    def test_exact_match_no_shortfall_no_surplus(self):
        cost = _hour_cost(s=1000.0, d=1000.0, da=5000, under=12000, resale=2500)
        assert cost == pytest.approx(5_000_000.0)

    def test_shortfall_adds_under_price(self):
        cost = _hour_cost(s=800.0, d=1000.0, da=5000, under=12000, resale=2500)
        expected = 5000 * 800 + 12000 * 200
        assert cost == pytest.approx(expected)

    def test_surplus_subtracts_resale(self):
        cost = _hour_cost(s=1200.0, d=1000.0, da=5000, under=12000, resale=2500)
        expected = 5000 * 1200 - 2500 * 200
        assert cost == pytest.approx(expected)

    def test_null_demand_returns_none(self):
        assert _hour_cost(s=1000.0, d=None, da=5000, under=12000, resale=2500) is None


class TestThreeHourToyExample:
    def test_cost_matches_hand_computation(self):
        da, under, resale = 5000.0, 12000.0, 2500.0
        cases = [
            (1000.0, 900.0),
            (1000.0, 1100.0),
            (1000.0, 1000.0),
        ]
        expected = (
            (5000 * 1000 + 12000 * 0 - 2500 * 100) +
            (5000 * 1000 + 12000 * 100 - 2500 * 0) +
            (5000 * 1000 + 12000 * 0 - 2500 * 0)
        )
        total = sum(_hour_cost(s, d, da, under, resale) for s, d in cases)
        assert total == pytest.approx(expected, rel=1e-9)


class TestNewsvendorQuantile:
    def test_default_tariff_gives_expected_quantile(self):
        da, under, resale = 5000.0, 12000.0, 2500.0
        q = (under - da) / (under - resale)
        assert q == pytest.approx(0.736842105263, rel=1e-6)

    def test_newsvendor_quantile_rounded(self):
        da, under, resale = 5000.0, 12000.0, 2500.0
        q = (under - da) / (under - resale)
        assert round(q, 4) == pytest.approx(0.7368, rel=1e-4)


class TestInterpolateQuantile:
    def test_exact_p50_col(self):
        row = pd.Series({"p05": 100.0, "p10": 110.0, "p50": 150.0, "p90": 190.0, "p95": 200.0})
        assert _interpolate_quantile(0.5, row) == pytest.approx(150.0)

    def test_exact_p90_col(self):
        row = pd.Series({"p05": 100.0, "p10": 110.0, "p50": 150.0, "p90": 190.0, "p95": 200.0})
        assert _interpolate_quantile(0.9, row) == pytest.approx(190.0)

    def test_interpolated_between_p50_and_p90(self):
        row = pd.Series({"p05": 100.0, "p10": 110.0, "p50": 150.0, "p90": 190.0, "p95": 200.0})
        result = _interpolate_quantile(0.7, row)
        assert 150.0 < result < 190.0


class TestRecommendIntegration:
    def _build_artifacts(self, tmp_path: Path) -> Path:
        from datetime import timedelta

        prev_dates = [date(2024, 6, 1) + timedelta(days=i) for i in range(7)]
        target_dates = [date(2024, 6, 8) + timedelta(days=i) for i in range(3)]
        rows = (
            _build_rows_for_days(prev_dates, "ensemble", 100, 110, 150, 190, 200, 145)
            + _build_rows_for_days(target_dates, "ensemble", 100, 110, 150, 190, 200, 145)
        )
        _make_tiny_parquet(tmp_path, rows)
        _make_meta(tmp_path, threshold_mw=200.0)
        _procurement_defaults(tmp_path)
        return tmp_path

    def test_schedule_length_and_shape(self, tmp_path, monkeypatch):
        art_dir = self._build_artifacts(tmp_path)
        import src.procurement.advisor as advisor_mod
        monkeypatch.setattr(advisor_mod, "artifacts_dir", lambda: art_dir)

        result = recommend("2024-06-08", days=3, model="ensemble", risk_quantile=0.9)
        assert len(result["schedule"]) == 72
        assert len(result["by_day"]) == 3
        assert result["start_date"] == "2024-06-08"
        assert result["end_date"] == "2024-06-10"

    def test_newsvendor_source_and_quantile(self, tmp_path, monkeypatch):
        art_dir = self._build_artifacts(tmp_path)
        import src.procurement.advisor as advisor_mod
        monkeypatch.setattr(advisor_mod, "artifacts_dir", lambda: art_dir)

        result = recommend("2024-06-08", days=1, model="ensemble", risk_quantile="newsvendor")
        assert result["risk_quantile_source"] == "newsvendor"
        expected_nv = (12000 - 5000) / (12000 - 2500)
        assert result["newsvendor_quantile"] == pytest.approx(expected_nv, rel=1e-5)

    def test_p90_risk_exposure_sign(self, tmp_path, monkeypatch):
        art_dir = self._build_artifacts(tmp_path)
        import src.procurement.advisor as advisor_mod
        monkeypatch.setattr(advisor_mod, "artifacts_dir", lambda: art_dir)

        result = recommend("2024-06-08", days=1, model="ensemble", risk_quantile=0.9)
        assert result["summary"]["p90_risk_exposure_inr"] is not None

    def test_validation_errors(self, tmp_path, monkeypatch):
        art_dir = self._build_artifacts(tmp_path)
        import src.procurement.advisor as advisor_mod
        monkeypatch.setattr(advisor_mod, "artifacts_dir", lambda: art_dir)

        with pytest.raises(ValueError, match="days must be between 1 and 7"):
            recommend("2024-06-08", days=10)

        with pytest.raises(ValueError, match="risk_quantile must be between 0.5 and 0.99"):
            recommend("2024-06-08", days=1, risk_quantile=0.2)

        with pytest.raises(ValueError, match="tariff ordering"):
            recommend(
                "2024-06-08",
                days=1,
                tariff={"da_price_inr_per_mwh": 12000, "under_price_inr_per_mwh": 5000, "resale_price_inr_per_mwh": 2500},
            )

    def test_no_previous_week_raises(self, tmp_path, monkeypatch):
        target_dates = [date(2024, 1, 2)]
        rows = _build_rows_for_days(target_dates, "ensemble", 100, 110, 150, 190, 200, 145)
        _make_tiny_parquet(tmp_path, rows)
        _make_meta(tmp_path, threshold_mw=200.0)
        _procurement_defaults(tmp_path)
        import src.procurement.advisor as advisor_mod
        monkeypatch.setattr(advisor_mod, "artifacts_dir", lambda: tmp_path)

        with pytest.raises(ValueError, match="No forecast data for the previous week"):
            recommend("2024-01-02", days=1, model="ensemble")

    def test_at_risk_hours_populated(self, tmp_path, monkeypatch):
        from datetime import timedelta
        prev_dates = [date(2024, 6, 1) + timedelta(days=i) for i in range(7)]
        target_dates = [date(2024, 6, 8)]
        rows = (
            _build_rows_for_days(prev_dates, "ensemble", 100, 110, 150, 190, 200, 145)
            + _build_rows_for_days(target_dates, "ensemble", 100, 110, 150, 210, 220, 145)
        )
        _make_tiny_parquet(tmp_path, rows)
        _make_meta(tmp_path, threshold_mw=200.0)
        _procurement_defaults(tmp_path)
        import src.procurement.advisor as advisor_mod
        monkeypatch.setattr(advisor_mod, "artifacts_dir", lambda: tmp_path)

        result = recommend("2024-06-08", days=1, model="ensemble", risk_quantile=0.9)
        assert len(result["summary"]["at_risk_hours"]) == 24
