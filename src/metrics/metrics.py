import numpy as np


def mape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-5) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.where(np.abs(y_true) < eps, eps, np.abs(y_true))
    return float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(y_pred - y_true))


def pinball(y_true: np.ndarray, y_pred: np.ndarray, q: float) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    diff = y_true - y_pred
    loss = np.maximum(q * diff, (q - 1.0) * diff)
    return float(np.mean(loss))


def mean_pinball(
    y_true: np.ndarray,
    q_preds: dict[float, np.ndarray] | list[tuple[float, np.ndarray]],
) -> float:
    if isinstance(q_preds, dict):
        pairs = list(q_preds.items())
    else:
        pairs = q_preds
    losses = [pinball(y_true, pred, q) for q, pred in pairs]
    return float(np.mean(losses))


def picp(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    inside = (y_true >= lower) & (y_true <= upper)
    return float(np.mean(inside))


def picp_80(y_true: np.ndarray, p10: np.ndarray, p90: np.ndarray) -> float:
    return picp(y_true, p10, p90)


def picp_90(y_true: np.ndarray, p05: np.ndarray, p95: np.ndarray) -> float:
    return picp(y_true, p05, p95)


def mpiw(lower: np.ndarray, upper: np.ndarray) -> float:
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    return float(np.mean(upper - lower))


def mpiw_80(p10: np.ndarray, p90: np.ndarray) -> float:
    return mpiw(p10, p90)


def improvement_pct(baseline_val: float | None, model_val: float | None) -> float | None:
    if baseline_val is None or model_val is None or baseline_val == 0.0:
        return None
    return float((baseline_val - model_val) / baseline_val * 100.0)
