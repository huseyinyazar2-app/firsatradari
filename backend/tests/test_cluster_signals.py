import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from firsat_radari.metrics.cluster_signals import TimePoint, analyze_points


def _points(values: list[str]) -> list[TimePoint]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        TimePoint(
            at=start + timedelta(days=index),
            value=Decimal(value),
            observation_id=uuid.uuid4(),
        )
        for index, value in enumerate(values)
    ]


def test_trend_requires_history_and_uses_robust_slope() -> None:
    insufficient = analyze_points(_points(["0.1", "0.2", "0.3"]))
    assert insufficient.status == "insufficient_history"
    assert insufficient.slope_per_day is None

    rising = analyze_points(_points(["0.10", "0.12", "0.14", "0.16"]))
    assert rising.status == "measured"
    assert rising.trend_direction == "rising"
    assert rising.slope_per_day == Decimal("0.020000000")
    assert rising.calculation["future_data_used"] is False


def test_anomaly_and_seasonality_are_data_gated() -> None:
    anomaly = analyze_points(
        _points(["0.10", "0.10", "0.10", "0.10", "0.10", "0.90"])
    )
    assert anomaly.anomaly_status == "anomaly"
    assert anomaly.anomaly_score == Decimal("9.999999")
    assert anomaly.seasonality_period_days is None

    weekly_pattern = [
        str(value)
        for _ in range(4)
        for value in (1, 2, 3, 4, 3, 2, 1)
    ]
    seasonal = analyze_points(_points(weekly_pattern))
    assert seasonal.seasonality_period_days == 7
    assert seasonal.seasonality_strength == Decimal("1.000000")
