# 系统结果与参考分析（more-than-moore 参考运行产出的 metrics json）的
# 一致性比对。容差覆盖跨线程数/平台的浮点漂移；同机同版本下偏差远小于容差。
from __future__ import annotations

import json
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "reference"


def load_reference(kind: str) -> dict:
    name = "metrics-univariate.json" if kind == "univariate" else "metrics-multivariate.json"
    return json.loads((REFERENCE_DIR / name).read_text())


def _check(actual, reference, *, atol: float = 0.0, rtol: float = 0.0) -> dict:
    if actual is None and reference is None:
        return {"actual": None, "reference": None, "delta": None, "within_tolerance": True}
    if actual is None or reference is None:
        return {
            "actual": actual,
            "reference": reference,
            "delta": None,
            "within_tolerance": False,
        }
    delta = round(actual - reference, 6)
    ok = abs(delta) <= atol + rtol * abs(reference)
    return {
        "actual": actual,
        "reference": reference,
        "delta": delta,
        "within_tolerance": bool(ok),
    }


def compare_univariate(result: dict, reference: dict) -> dict:
    m, r = result["metrics"], reference
    checks: dict[str, dict] = {
        "params": _check(m["params"], r["params"]),
        "train_samples": _check(m["train_samples"], r["train_samples"]),
        "test_samples": _check(m["test_samples"], r["test_samples"]),
        "train_mse_scaled": _check(m["train_mse_scaled"], r["train_mse_scaled"], rtol=0.25),
        "test_mse_scaled": _check(m["test_mse_scaled"], r["test_mse_scaled"], rtol=0.25),
        "model_MAE": _check(m["model_inverse"]["MAE"], r["model_inverse"]["MAE"], atol=0.08),
        "model_RMSE": _check(m["model_inverse"]["RMSE"], r["model_inverse"]["RMSE"], atol=0.08),
        "model_R2": _check(m["model_inverse"]["R2"], r["model_inverse"]["R2"], atol=0.08),
        "persistence_MAE": _check(
            m["persistence_inverse"]["MAE"], r["persistence_inverse"]["MAE"], atol=0.05
        ),
        "persistence_RMSE": _check(
            m["persistence_inverse"]["RMSE"], r["persistence_inverse"]["RMSE"], atol=0.05
        ),
        "persistence_R2": _check(
            m["persistence_inverse"]["R2"], r["persistence_inverse"]["R2"], atol=0.05
        ),
        "residual_mean": _check(m["residual"]["mean"], r["residual"]["mean"], atol=0.08),
        "residual_std": _check(m["residual"]["std"], r["residual"]["std"], atol=0.08),
    }
    return {
        "reference_source": "metrics-univariate.json (more-than-moore reference run, seed=42, epochs=20)",
        "epochs_match": result.get("epochs") == 20,
        "checks": checks,
        "passed": result.get("epochs") == 20
        and all(c["within_tolerance"] for c in checks.values()),
    }


def compare_multivariate(result: dict, reference: dict) -> dict:
    modes: dict[str, dict] = {}
    for mode, ref_mode in reference["modes"].items():
        cur = result["modes"][mode]
        m, rm = cur["metrics"], ref_mode
        checks: dict[str, dict] = {
            "corr_train": _check(m["corr_a_b"]["train"], rm["corr_a_b"]["train"], atol=0.02),
            "corr_benign": _check(m["corr_a_b"]["benign"], rm["corr_a_b"]["benign"], atol=0.02),
            "corr_post_onset": _check(
                m["corr_a_b"]["post_onset"], rm["corr_a_b"]["post_onset"], atol=0.02
            ),
        }
        for key in ("pre_mean", "post_mean", "pre_std", "post_std"):
            checks[f"b_marginal_{key}"] = _check(
                m["b_marginal"][key], rm["b_marginal"][key], atol=0.02
            )
        method_tol = {
            "val_alarm_rate": 0.02,
            "benign_alarm_rate": 0.08,
            "fault_alarm_rate": 0.10,
        }
        for method, ref_m in rm["methods"].items():
            cur_m = m["methods"][method]
            for key, tol in method_tol.items():
                checks[f"{method}.{key}"] = _check(cur_m[key], ref_m[key], atol=tol)
            checks[f"{method}.detection_delay"] = _check(
                cur_m["detection_delay"], ref_m["detection_delay"], atol=30
            )
        modes[mode] = {
            "checks": checks,
            "passed": all(c["within_tolerance"] for c in checks.values()),
        }
    return {
        "reference_source": "metrics-multivariate.json (more-than-moore reference run, seed=42, epochs=30)",
        "epochs_match": result.get("epochs") == 30,
        "modes": modes,
        "passed": result.get("epochs") == 30
        and all(m["passed"] for m in modes.values()),
    }
