# 全量轮数的一致性（parity）测试：与参考 metrics 逐项比对。
# 本机 CPU 约 3 min（单变量 ~7s + 多变量 ~2min），标记 slow。
import pytest

from app.comparison import compare_multivariate, compare_univariate, load_reference
from app.ml.multivariate import run_multivariate
from app.ml.univariate import run_univariate


@pytest.mark.slow
def test_univariate_parity():
    result = run_univariate(20)
    comp = compare_univariate(result, load_reference("univariate"))
    failed = {k: v for k, v in comp["checks"].items() if not v["within_tolerance"]}
    assert comp["passed"], f"failed checks: {failed}"
    # 同机同版本下应为逐位一致；仅计时字段允许不同
    assert result["metrics"]["params"] == 74401
    assert result["metrics"]["train_mse_scaled"] == 0.026656
    assert result["metrics"]["model_inverse"]["R2"] == 0.2864


@pytest.mark.slow
def test_multivariate_parity():
    result = run_multivariate(30)
    comp = compare_multivariate(result, load_reference("multivariate"))
    for mode, m in comp["modes"].items():
        failed = {k: v for k, v in m["checks"].items() if not v["within_tolerance"]}
        assert m["passed"], f"{mode} failed checks: {failed}"
