import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.models import (
    BacktestMetricsResponse,
    BacktestPredictionsResponse,
    DayAheadForecastResponse,
    ErrorHeatmapResponse,
    FeatureImportanceResponse,
    HealthResponse,
    MetaResponse,
    MissedPeaksResponse,
    ModelsResponse,
    PeakDayResponse,
    PeakEventsResponse,
    PeakMetricsResponse,
    ProcurementDefaultsResponse,
    ProcurementResponse,
    WeekAheadForecastResponse,
)
from api.store import store


@pytest.fixture
def client_for_dir(monkeypatch):
    def _make_client(art_dir):
        monkeypatch.setenv("ARTIFACTS_DIR", str(art_dir))
        monkeypatch.setenv("MOCK", "1" if "mock" in art_dir.name else "0")
        store.dir_path = art_dir
        store.load()
        return TestClient(app)

    return _make_client


def test_health_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        model = HealthResponse(**data)
        assert model.status == "ok"
        if "mock" in art_dir.name:
            assert model.mock is True


def test_meta_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/meta")
        assert resp.status_code == 200
        data = resp.json()
        model = MetaResponse(**data)
        assert model.version == "1.0.0"
        assert model.timezone == "Asia/Kolkata"


def test_models_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        model = ModelsResponse(**data)
        ids = [m.id for m in model.models]
        assert "ensemble" in ids
        assert "seasonal_naive" in ids


def test_forecast_day_ahead_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/forecast/day-ahead?date=2024-06-12&model=ensemble")
        assert resp.status_code == 200
        data = resp.json()
        model = DayAheadForecastResponse(**data)
        assert len(model.points) == 24
        assert model.date == "2024-06-12"

        bad_date_resp = client.get("/api/v1/forecast/day-ahead?date=not-a-date&model=ensemble")
        assert bad_date_resp.status_code == 400
        assert bad_date_resp.json()["error"]["code"] == "BAD_DATE_RANGE"

        oor_resp = client.get("/api/v1/forecast/day-ahead?date=2099-01-01&model=ensemble")
        assert oor_resp.status_code == 404
        assert oor_resp.json()["error"]["code"] == "DATE_OUT_OF_RANGE"

        bad_model_resp = client.get("/api/v1/forecast/day-ahead?date=2024-06-12&model=invalid_model")
        assert bad_model_resp.status_code == 400
        assert bad_model_resp.json()["error"]["code"] == "UNKNOWN_MODEL"


def test_forecast_week_ahead_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/forecast/week-ahead?start_date=2024-06-12&model=ensemble")
        assert resp.status_code == 200
        data = resp.json()
        model = WeekAheadForecastResponse(**data)
        assert len(model.points) == 168
        assert len(model.daily_peaks) == 7

        bad_date_resp = client.get("/api/v1/forecast/week-ahead?start_date=not-a-date")
        assert bad_date_resp.status_code == 400
        assert bad_date_resp.json()["error"]["code"] == "BAD_DATE_RANGE"


def test_peak_day_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/peak/day?date=2024-06-12&model=ensemble")
        assert resp.status_code == 200
        data = resp.json()
        model = PeakDayResponse(**data)
        assert model.date == "2024-06-12"

        oor_resp = client.get("/api/v1/peak/day?date=2099-01-01&model=ensemble")
        assert oor_resp.status_code == 404
        assert oor_resp.json()["error"]["code"] == "DATE_OUT_OF_RANGE"


def test_peak_events_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/peak/events?from=2024-01-01&to=2024-03-31&model=ensemble")
        assert resp.status_code == 200
        data = resp.json()
        model = PeakEventsResponse(**data)
        assert model.total >= 0

        bad_range_resp = client.get("/api/v1/peak/events?from=2024-03-31&to=2024-01-01")
        assert bad_range_resp.status_code == 400
        assert bad_range_resp.json()["error"]["code"] == "BAD_DATE_RANGE"


def test_backtest_predictions_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/backtest/predictions?from=2024-01-01&to=2024-01-10&model=ensemble&horizon_day=1")
        assert resp.status_code == 200
        data = resp.json()
        model = BacktestPredictionsResponse(**data)
        assert len(model.points) > 0

        bad_range = client.get("/api/v1/backtest/predictions?from=2024-01-10&to=2024-01-01")
        assert bad_range.status_code == 400
        assert bad_range.json()["error"]["code"] == "BAD_DATE_RANGE"

        span_too_long = client.get("/api/v1/backtest/predictions?from=2024-01-01&to=2024-05-01")
        assert span_too_long.status_code == 400
        assert span_too_long.json()["error"]["code"] == "BAD_DATE_RANGE"


def test_backtest_metrics_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/backtest/metrics?model=ensemble&horizon_day=1")
        assert resp.status_code == 200
        data = resp.json()
        model = BacktestMetricsResponse(**data)
        assert len(model.rows) > 0


def test_backtest_peak_metrics_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/backtest/peak-metrics?model=ensemble")
        assert resp.status_code == 200
        data = resp.json()
        model = PeakMetricsResponse(**data)
        assert len(model.rows) > 0


def test_error_heatmap_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/backtest/error-heatmap?model=ensemble&metric=mape&horizon_day=1")
        assert resp.status_code == 200
        data = resp.json()
        model = ErrorHeatmapResponse(**data)
        assert len(model.hours) == 24
        assert len(model.seasons) == 4

        not_found_resp = client.get("/api/v1/backtest/error-heatmap?model=ensemble&metric=invalid_metric&horizon_day=1")
        assert not_found_resp.status_code == 404
        assert not_found_resp.json()["error"]["code"] == "NOT_FOUND"


def test_procurement_recommend_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        pred_path = art_dir / "predictions_backtest.parquet"
        target_model = "ensemble"
        if pred_path.exists():
            import pandas as pd
            models_in_art = pd.read_parquet(pred_path)["model"].unique().tolist()
            if "ensemble" not in models_in_art and models_in_art:
                target_model = models_in_art[0]
        valid_payload = {
            "start_date": "2024-06-08",
            "days": 7,
            "model": target_model,
            "risk_quantile": 0.9,
            "tariff": {
                "da_price_inr_per_mwh": 5000,
                "under_price_inr_per_mwh": 12000,
                "resale_price_inr_per_mwh": 2500,
            },
        }
        resp = client.post("/api/v1/procurement/recommend", json=valid_payload)
        assert resp.status_code == 200
        data = resp.json()
        model = ProcurementResponse(**data)
        assert len(model.schedule) == 168
        assert len(model.by_day) == 7

        nv_payload = {
            "start_date": "2024-06-08",
            "days": 2,
            "model": target_model,
            "risk_quantile": "newsvendor",
        }
        nv_resp = client.post("/api/v1/procurement/recommend", json=nv_payload)
        assert nv_resp.status_code == 200
        nv_model = ProcurementResponse(**nv_resp.json())
        assert nv_model.risk_quantile_source == "newsvendor"

        bad_days_payload = {
            "start_date": "2024-06-08",
            "days": 10,
            "model": target_model,
            "risk_quantile": 0.9,
        }
        bad_days_resp = client.post("/api/v1/procurement/recommend", json=bad_days_payload)
        assert bad_days_resp.status_code == 400
        assert bad_days_resp.json()["error"]["code"] == "BAD_PARAMETER"

        bad_q_payload = {
            "start_date": "2024-06-08",
            "days": 2,
            "model": target_model,
            "risk_quantile": 0.2,
        }
        bad_q_resp = client.post("/api/v1/procurement/recommend", json=bad_q_payload)
        assert bad_q_resp.status_code == 400
        assert bad_q_resp.json()["error"]["code"] == "BAD_PARAMETER"


def test_procurement_defaults_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/procurement/defaults")
        assert resp.status_code == 200
        data = resp.json()
        model = ProcurementDefaultsResponse(**data)
        assert model.tariff.da_price_inr_per_mwh > 0


def test_missed_peaks_endpoint(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/backtest/missed-peaks?model=ensemble")
        assert resp.status_code == 200
        data = resp.json()
        model = MissedPeaksResponse(**data)
        assert model.total >= 0


def test_feature_importance_valid_and_invalid(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.get("/api/v1/models/lgbm/feature-importance")
        assert resp.status_code == 200
        data = resp.json()
        model = FeatureImportanceResponse(**data)
        assert len(model.features) > 0

        not_found_resp = client.get("/api/v1/models/unknown_model/feature-importance")
        assert not_found_resp.status_code == 404
        assert not_found_resp.json()["error"]["code"] == "NOT_FOUND"


def test_scenario_endpoint_501(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        payload = {"date": "2024-06-12", "temp_delta_c": 2.0}
        resp = client.post("/api/v1/forecast/scenario", json=payload)
        assert resp.status_code == 501
        assert resp.json()["error"]["code"] == "NOT_IMPLEMENTED"


def test_validation_error_format(artifact_dirs, client_for_dir):
    for art_dir in artifact_dirs:
        client = client_for_dir(art_dir)
        resp = client.post("/api/v1/procurement/recommend", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "errors" in data["error"]["details"]
