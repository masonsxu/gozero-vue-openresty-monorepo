# 单变量 CNN+Transformer 预测管线：与参考 main.py 逐语句等价的移植。
# 差异仅在于：图表改为返回前端可渲染的数据序列（ECharts），指标口径不变。
from __future__ import annotations

import math
import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler

from .dataset import T_UNIVARIATE, WINDOW_SIZE, create_dataset, generate_series
from .model import CNNTransformer, TimeSeriesDataset

TRAIN_RATIO = 0.8
BATCH_SIZE = 64
LR = 1e-3
SEED = 42

DEVICE = torch.device("cpu")


def _train(
    model: CNNTransformer,
    train_loader,
    test_loader,
    epochs: int,
) -> tuple[list[float], list[float], float]:
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    train_losses: list[float] = []
    test_losses: list[float] = []
    start = time.perf_counter()
    for _ in range(epochs):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            pred = model(xb)
            loss = criterion(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        train_losses.append(total_loss / len(train_loader))

        model.eval()
        test_loss = 0.0
        with torch.no_grad():
            for xb, yb in test_loader:
                loss = criterion(model(xb), yb)
                test_loss += loss.item()
        test_losses.append(test_loss / len(test_loader))
    return train_losses, test_losses, time.perf_counter() - start


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(math.sqrt(float(np.mean((y_true - y_pred) ** 2))))
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(1 - ss_res / ss_tot, 4),
    }


def _collect_predictions(model, test_loader) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    preds, targets = [], []
    with torch.no_grad():
        for xb, yb in test_loader:
            preds.extend(model(xb).flatten().tolist())
            targets.extend(yb.flatten().tolist())
    return np.array(preds), np.array(targets)


def _r5(values: np.ndarray) -> list[float]:
    return [round(float(v), 5) for v in values]


def run_univariate(epochs: int, progress=None) -> dict:
    """执行完整单变量实验，返回指标 + 图表数据。默认参数下与参考
    metrics.json 数值一致（同 torch 版本、seed=42）。"""
    if progress:
        progress("generating synthetic series (T=2000, seed=42)")
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    series, _ = generate_series()

    scaler = StandardScaler()
    series_scaled = scaler.fit_transform(series.reshape(-1, 1)).flatten()
    X, y = create_dataset(series_scaled, WINDOW_SIZE)
    X = X[:, :, None]
    y = y[:, None]

    split = int(len(X) * TRAIN_RATIO)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    from torch.utils.data import DataLoader

    if progress:
        progress(f"training CNNTransformer ({epochs} epochs)")
    train_loader = DataLoader(
        TimeSeriesDataset(X_train, y_train), batch_size=BATCH_SIZE, shuffle=True
    )
    test_loader = DataLoader(
        TimeSeriesDataset(X_test, y_test), batch_size=BATCH_SIZE, shuffle=False
    )

    model = CNNTransformer().to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    train_losses, test_losses, seconds = _train(model, train_loader, test_loader, epochs)

    if progress:
        progress("collecting predictions and metrics")
    preds, targets = _collect_predictions(model, test_loader)
    preds_inv = scaler.inverse_transform(preds.reshape(-1, 1)).flatten()
    targets_inv = scaler.inverse_transform(targets.reshape(-1, 1)).flatten()

    persist = scaler.inverse_transform(X_test[:, -1, 0].reshape(-1, 1)).flatten()
    m_model = regression_metrics(targets_inv, preds_inv)
    m_persist = regression_metrics(targets_inv, persist)

    residuals = targets_inv - preds_inv
    residual_stats = {
        "mean": round(float(np.mean(residuals)), 4),
        "std": round(float(np.std(residuals)), 4),
    }
    counts, bin_edges = np.histogram(residuals, bins=40)

    metrics = {
        "device": str(DEVICE),
        "seed": SEED,
        "params": n_params,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_mse_scaled": round(train_losses[-1], 6),
        "test_mse_scaled": round(test_losses[-1], 6),
        "train_seconds": round(seconds, 2),
        "model_inverse": m_model,
        "persistence_inverse": m_persist,
        "residual": residual_stats,
    }

    return {
        "kind": "univariate",
        "seed": SEED,
        "epochs": epochs,
        "device": str(DEVICE),
        "torch_version": torch.__version__,
        "metrics": metrics,
        "series": {
            "raw": {"t": list(range(T_UNIVARIATE)), "value": _r5(series)},
            "loss": {
                "epoch": list(range(1, len(train_losses) + 1)),
                "train": [round(v, 6) for v in train_losses],
                "test": [round(v, 6) for v in test_losses],
            },
            "prediction": {
                "sample": list(range(200)),
                "true": _r5(targets_inv[:200]),
                "pred": _r5(preds_inv[:200]),
            },
            "residual_histogram": {
                "bin_left": _r5(bin_edges[:-1]),
                "bin_right": _r5(bin_edges[1:]),
                "counts": [int(c) for c in counts],
            },
            "scatter": {
                "actual": _r5(targets_inv),
                "predicted": _r5(preds_inv),
            },
        },
    }
