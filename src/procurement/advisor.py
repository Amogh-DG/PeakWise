from datetime import datetime, timedelta

IS_STUB = True


def recommend(
    start_date: str,
    days: int,
    model: str = "ensemble",
    risk_quantile: float | str = 0.9,
    tariff: dict | None = None,
) -> dict:
    if not (1 <= days <= 7):
        raise ValueError("days must be between 1 and 7")

    default_tariff = {
        "da_price_inr_per_mwh": 5000.0,
        "under_price_inr_per_mwh": 12000.0,
        "resale_price_inr_per_mwh": 2500.0,
    }
    used_tariff = tariff if tariff is not None else default_tariff
    for key in ("da_price_inr_per_mwh", "under_price_inr_per_mwh", "resale_price_inr_per_mwh"):
        if key not in used_tariff:
            raise ValueError(f"tariff missing required field: {key}")

    da = float(used_tariff["da_price_inr_per_mwh"])
    under = float(used_tariff["under_price_inr_per_mwh"])
    resale = float(used_tariff["resale_price_inr_per_mwh"])

    if under <= resale:
        raise ValueError("under_price must be greater than resale_price")
    newsvendor_q = (under - da) / (under - resale)

    if isinstance(risk_quantile, str) and risk_quantile.lower() == "newsvendor":
        effective_q = newsvendor_q
        source = "newsvendor"
    else:
        try:
            effective_q = float(risk_quantile)
            if not (0.5 <= effective_q <= 0.99):
                raise ValueError("risk_quantile must be between 0.5 and 0.99")
            source = "user"
        except (ValueError, TypeError) as exc:
            raise ValueError("risk_quantile must be between 0.5 and 0.99 or 'newsvendor'") from exc

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=days - 1)
    end_date = end_dt.strftime("%Y-%m-%d")

    schedule = []
    by_day = []
    total_hours = days * 24

    for day_idx in range(days):
        current_day_dt = start_dt + timedelta(days=day_idx)
        current_day_str = current_day_dt.strftime("%Y-%m-%d")
        day_mwh = 0.0

        for hour in range(24):
            hour_ts = f"{current_day_str}T{hour:02d}:00:00+05:30"
            base_load = 5000.0 + (hour * 50.0)
            p50 = base_load
            p90 = base_load + 450.0
            scheduled = p90 if effective_q >= 0.8 else p50 + 200.0
            actual = base_load + 20.0
            day_mwh += scheduled

            schedule.append({
                "ts": hour_ts,
                "scheduled_mw": round(scheduled, 1),
                "p50_mw": round(p50, 1),
                "p90_mw": round(p90, 1),
                "flat_mw": 5420.0,
                "actual_mw": round(actual, 1),
            })

        day_cost = day_mwh * da
        by_day.append({
            "date": current_day_str,
            "scheduled_mwh": round(day_mwh, 1),
            "cost_inr": round(day_cost, 1),
            "flat_cost_inr": round(day_cost * 1.05, 1),
            "peak_scheduled_mw": 6200.0,
        })

    total_mwh = sum(item["scheduled_mwh"] for item in by_day)
    cost = total_mwh * da
    flat_cost = cost * 1.05
    flat_peak_cost = cost * 1.12
    savings = flat_cost - cost
    savings_pct = (savings / flat_cost) * 100.0 if flat_cost > 0 else 0.0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "model": model,
        "risk_quantile": round(effective_q, 4),
        "risk_quantile_source": source,
        "newsvendor_quantile": round(newsvendor_q, 4),
        "tariff_used": {
            "da_price_inr_per_mwh": da,
            "under_price_inr_per_mwh": under,
            "resale_price_inr_per_mwh": resale,
        },
        "baseline": {
            "type": "flat_prev_week_mean",
            "flat_mw": 5420.0,
            "alt_flat_prev_week_peak_mw": 7600.0,
        },
        "schedule": schedule,
        "summary": {
            "total_scheduled_mwh": round(total_mwh, 1),
            "cost_inr": round(cost, 1),
            "flat_cost_inr": round(flat_cost, 1),
            "flat_peak_cost_inr": round(flat_peak_cost, 1),
            "savings_inr": round(savings, 1),
            "savings_pct": round(savings_pct, 2),
            "p90_risk_exposure_inr": round(cost * 0.05, 1),
            "under_procured_hours": min(5, total_hours),
            "over_procured_hours": max(0, total_hours - 5),
            "at_risk_hours": [f"{start_date}T21:00:00+05:30"],
        },
        "by_day": by_day,
    }
