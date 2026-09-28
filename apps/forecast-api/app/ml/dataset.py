# 合成数据生成：与参考实现逐语句一致（含 RNG 消耗顺序），
# 保证 seed=42 下生成序列与参考完全相同。
from __future__ import annotations

import numpy as np

T_UNIVARIATE = 2000
T_MULTIVARIATE = 4000
WINDOW_SIZE = 30
VAL_START = 2400
BENIGN_START = 3400
FAULT_ONSET = 3700
RAMP = 100
LAG_MAX = 6


def generate_series() -> tuple[np.ndarray, np.ndarray]:
    """单变量：趋势 + 双周期 + 两段突变 + 高斯噪声，返回 (series, spike)。"""
    t = np.arange(T_UNIVARIATE)
    trend = 0.005 * t
    seasonal = 1.5 * np.sin(2 * np.pi * t / 50) + 0.8 * np.sin(2 * np.pi * t / 120)
    noise = np.random.normal(0, 0.4, T_UNIVARIATE)
    spike = np.zeros(T_UNIVARIATE)
    spike[600:620] += np.linspace(0, 4, 20)
    spike[620:640] += np.linspace(4, 0, 20)
    spike[1400:1420] -= np.linspace(0, 3, 20)
    spike[1420:1440] -= np.linspace(3, 0, 20)
    return trend + seasonal + spike + noise, spike


def create_dataset(data: np.ndarray, window_size: int) -> tuple[np.ndarray, np.ndarray]:
    """滑动窗口：前 window_size 个点预测下一个点。"""
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i : i + window_size])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)


def generate_multivariate(mode: str) -> tuple[np.ndarray, np.ndarray]:
    """两通道平稳合成数据：A 温度（慢周期+噪声），B 键合压力（耦合 A）。

    返回 (series[T,2], ramp)。RNG 消耗顺序与参考 multivariate.py 一致：
    先 4 组基础噪声，再按 mode 分支消耗分支内噪声。
    """
    t = np.arange(T_MULTIVARIATE)
    a_slow = 1.2 * np.sin(2 * np.pi * t / 60)
    fast = 0.5 * np.sin(2 * np.pi * t / 17)
    n1a, n2a = np.random.normal(0, 0.3, (2, T_MULTIVARIATE))
    n1b, n2b = np.random.normal(0, 0.25, (2, T_MULTIVARIATE))
    n_a = np.where(t < BENIGN_START, n1a, n2a)
    n_b = np.where(t < BENIGN_START, n1b, n2b)
    a = a_slow + n_a
    b_normal = 0.8 * a + fast + n_b
    ramp = np.clip((t - FAULT_ONSET) / RAMP, 0, 1)
    if mode == "phase_swap":
        a2 = 1.2 * np.cos(2 * np.pi * t / 60) + np.random.normal(0, 0.3, T_MULTIVARIATE)
        b_anom = 0.8 * a2 + fast + n_b
    elif mode == "actuator_lag":
        tau = np.round(LAG_MAX * ramp).astype(int)
        a_lag = a[np.clip(t - tau, 0, None)]
        b_anom = 0.8 * a_lag + fast + n_b
    else:
        raise ValueError(f"unknown mode: {mode}")
    b = (1 - ramp) * b_normal + ramp * b_anom
    return np.stack([a, b], axis=1), ramp


def make_windows(scaled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """多变量滑窗：前 WINDOW 步预测下一步全通道。"""
    X, y = [], []
    for i in range(len(scaled) - WINDOW_SIZE):
        X.append(scaled[i : i + WINDOW_SIZE])
        y.append(scaled[i + WINDOW_SIZE])
    return np.array(X), np.array(y)
