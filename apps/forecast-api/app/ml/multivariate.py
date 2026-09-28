# 多变量耦合失效检测管线：与参考 multivariate.py 逐语句等价的移植。
# 关键约束：两种 mode 必须按 (phase_swap, actuator_lag) 顺序在一次
# seed=42 的运行中执行 —— 参考实现共享 RNG 状态，单独运行某个 mode
# 无法复现参考指标。
from __future__ import annotations

import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader

from .dataset import (
    BENIGN_START,
    FAULT_ONSET,
    LAG_MAX,
    RAMP,
    T_MULTIVARIATE,
    VAL_START,
    WINDOW_SIZE,
    generate_multivariate,
    make_windows,
)
from .model import CNNTransformer, MultiCNNTransformer, TimeSeriesDataset

EPOCHS_DEFAULT = 30
BATCH_SIZE = 64
LR = 1e-3
SMOOTH = 30
QUANTILE = 0.995
EWMA_LAMBDA = 0.2
MODES = ("phase_swap", "actuator_lag")
SEED = 42


def _fit(model: nn.Module, loader: DataLoader, epochs: int) -> float:
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    start = time.perf_counter()
    model.train()
    for _ in range(epochs):
        for xb, yb in loader:
            loss = criterion(model(xb), yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
    return time.perf_counter() - start


def _channel_errors(model: nn.Module, X: np.ndarray, y: np.ndarray, ch: int) -> np.ndarray:
    model.eval()
    errs = []
    with torch.no_grad():
        for i in range(0, len(X), 256):
            pred = model(torch.tensor(X[i : i + 256], dtype=torch.float32))
            errs.extend(
                ((pred[:, ch] - torch.tensor(y[i : i + 256, ch])) ** 2).tolist()
            )
    return np.array(errs)


def _smooth_score(errs: np.ndarray, window: int) -> np.ndarray:
    out = np.full(len(errs), np.nan)
    for j in range(window - 1, len(errs)):
        out[j] = errs[j - window + 1 : j + 1].mean()
    return out


def _ewma_absz(values: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    z, s = np.empty(len(values)), mu
    for i, v in enumerate(values):
        s = EWMA_LAMBDA * v + (1 - EWMA_LAMBDA) * s
        z[i] = (s - mu) / sigma
    return np.abs(z)


def _alarm_stats(alarm: np.ndarray, lo: int, hi: int) -> tuple[float, int]:
    seg = alarm[lo:hi]
    idx = np.flatnonzero(seg)
    first = int(idx[0]) + lo if len(idx) else -1
    return float(seg.mean()), first


def _run_pipeline(series: np.ndarray, epochs: int, progress, mode_label: str):
    scaler = StandardScaler().fit(series[:VAL_START])
    scaled = scaler.transform(series)
    X, y = make_windows(scaled)

    X_tr, y_tr = X[: VAL_START - WINDOW_SIZE], y[: VAL_START - WINDOW_SIZE]
    loaders = {
        "mv": DataLoader(
            TimeSeriesDataset(X_tr, y_tr), batch_size=BATCH_SIZE, shuffle=True
        ),
        "uv_b": DataLoader(
            TimeSeriesDataset(X_tr[:, :, 1:2], y_tr[:, 1:2]),
            batch_size=BATCH_SIZE,
            shuffle=True,
        ),
        "uv_a": DataLoader(
            TimeSeriesDataset(X_tr[:, :, 0:1], y_tr[:, 0:1]),
            batch_size=BATCH_SIZE,
            shuffle=True,
        ),
    }
    models = {
        "mv": MultiCNNTransformer(input_dim=2, output_dim=2),
        "uv_b": CNNTransformer(input_dim=1),
        "uv_a": CNNTransformer(input_dim=1),
    }
    for name, model in models.items():
        if progress:
            progress(f"[{mode_label}] training model {name}")
        _fit(model, loaders[name], epochs)

    model_inputs = {"mv": X, "uv_b": X[:, :, 1:2], "uv_a": X[:, :, 0:1]}
    scores: dict[str, np.ndarray] = {}
    for name, model, ch in (
        ("mv", models["mv"], 1),
        ("uv_b", models["uv_b"], 0),
        ("uv_a", models["uv_a"], 0),
    ):
        e = _channel_errors(model, model_inputs[name], y, ch)
        scores[name] = np.concatenate(
            [np.full(WINDOW_SIZE, np.nan), _smooth_score(e, SMOOTH)]
        )

    mu_a, sd_a = scaled[:VAL_START, 0].mean(), scaled[:VAL_START, 0].std()
    mu_b, sd_b = scaled[:VAL_START, 1].mean(), scaled[:VAL_START, 1].std()
    scores["ewma_a"] = _ewma_absz(scaled[:, 0], mu_a, sd_a)
    scores["ewma_b"] = _ewma_absz(scaled[:, 1], mu_b, sd_b)

    results, thresholds, alarms = {}, {}, {}
    for name, sc in scores.items():
        th = float(np.nanquantile(sc[VAL_START:BENIGN_START], QUANTILE))
        thresholds[name] = round(th, 6)
        alarm = sc > th
        alarms[name] = alarm
        val_rate, _ = _alarm_stats(alarm, VAL_START, BENIGN_START)
        benign_rate, _ = _alarm_stats(alarm, BENIGN_START, FAULT_ONSET)
        fault_rate, first = _alarm_stats(alarm, FAULT_ONSET, T_MULTIVARIATE)
        results[name] = {
            "val_alarm_rate": round(val_rate, 4),
            "benign_alarm_rate": round(benign_rate, 4),
            "fault_alarm_rate": round(fault_rate, 4),
            "detection_delay": (first - FAULT_ONSET) if first >= 0 else None,
        }
    return results, scores, thresholds


def _summarize(series: np.ndarray, results: dict) -> dict:
    pre = slice(1000, BENIGN_START)
    post = slice(FAULT_ONSET + RAMP, T_MULTIVARIATE)
    return {
        "b_marginal": {
            "pre_mean": round(float(series[pre, 1].mean()), 4),
            "post_mean": round(float(series[post, 1].mean()), 4),
            "pre_std": round(float(series[pre, 1].std()), 4),
            "post_std": round(float(series[post, 1].std()), 4),
        },
        "corr_a_b": {
            "train": round(
                float(np.corrcoef(series[:VAL_START, 0], series[:VAL_START, 1])[0, 1]),
                4,
            ),
            "benign": round(
                float(
                    np.corrcoef(
                        series[BENIGN_START:FAULT_ONSET, 0],
                        series[BENIGN_START:FAULT_ONSET, 1],
                    )[0, 1]
                ),
                4,
            ),
            "post_onset": round(
                float(np.corrcoef(series[post, 0], series[post, 1])[0, 1]), 4
            ),
        },
        "methods": results,
    }


def _opt(values: np.ndarray) -> list[float | None]:
    """NaN -> None（JSON 无 NaN），保留 5 位小数。"""
    return [None if np.isnan(v) else round(float(v), 5) for v in values]


def _r5(values: np.ndarray) -> list[float]:
    return [round(float(v), 5) for v in values]


def run_multivariate(epochs: int, progress=None) -> dict:
    """顺序执行两种 mode 的完整实验，返回指标 + 图表数据。"""
    if progress:
        progress("seeding RNG (seed=42)")
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    modes_out: dict[str, dict] = {}
    for mode in MODES:
        if progress:
            progress(f"[{mode}] generating two-channel stream")
        series, _ = generate_multivariate(mode)
        results, scores, thresholds = _run_pipeline(series, epochs, progress, mode)
        summary = _summarize(series, results)

        sel_tr = slice(0, VAL_START, 5)
        post = slice(FAULT_ONSET + RAMP, T_MULTIVARIATE)
        modes_out[mode] = {
            "metrics": summary,
            "thresholds": thresholds,
            "series": {
                "channels": {
                    "t": list(range(T_MULTIVARIATE)),
                    "a": _r5(series[:, 0]),
                    "b": _r5(series[:, 1]),
                },
                "scores": {
                    "t": list(range(T_MULTIVARIATE)),
                    "mv": _opt(scores["mv"]),
                    "uv_b": _opt(scores["uv_b"]),
                    "uv_a": _opt(scores["uv_a"]),
                    "ewma_a": _opt(scores["ewma_a"]),
                    "ewma_b": _opt(scores["ewma_b"]),
                },
                "coupling": {
                    "train": {"a": _r5(series[sel_tr, 0]), "b": _r5(series[sel_tr, 1])},
                    "post": {"a": _r5(series[post, 0]), "b": _r5(series[post, 1])},
                },
            },
        }

    return {
        "kind": "multivariate",
        "seed": SEED,
        "epochs": epochs,
        "device": "cpu",
        "torch_version": torch.__version__,
        "constants": {
            "benign_start": BENIGN_START,
            "fault_onset": FAULT_ONSET,
            "ramp": RAMP,
            "lag_max": LAG_MAX,
            "val_start": VAL_START,
            "smooth": SMOOTH,
            "quantile": QUANTILE,
            "ewma_lambda": EWMA_LAMBDA,
        },
        "modes": modes_out,
    }
