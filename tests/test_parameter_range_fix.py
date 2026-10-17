#!/usr/bin/env python3
"""
參數範圍修復驗證（行程內版，不需 run_api.py）

用戶配置: Short 3-12, Mid 14-18, Long 20-33
預期: OptunaOptimizer 實際抽樣的每個 trial，short/mid/long_period 都落在這些範圍內
      （修復前 Optuna 忽略前端配置，改用 strategies.yaml 預設範圍）。

做法：以真實 OptunaOptimizer（in-memory study，TPE，固定 seed）與真實 `_objective_function`
抽樣路徑跑數個 trial；僅把「信號密度分析」這一步替身為固定回應（不涉案例／K 線資料），
抽樣、範圍覆寫、策略參數驗證皆走生產碼。
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import optuna
import pytest

from momentum.Optimization.optuna_optimizer import OptunaOptimizer, ParameterRanges

SHORT = (3, 12)
MID = (14, 18)
LONG = (20, 33)
N_TRIALS = 25


def _build_optimizer() -> OptunaOptimizer:
    ranges = ParameterRanges(
        ema_short_range=SHORT,
        ema_mid_range=MID,
        ema_long_range=LONG,
        data_sources=["close"],
        strategy_logics=["three_line"],
    )
    with patch("momentum.Optimization.optuna_optimizer.SignalAnalysisService"), patch(
        "momentum.Optimization.optuna_optimizer.CaseStorage"
    ):
        opt = OptunaOptimizer(
            study_name="range_test",
            storage=None,
            sampler_type="TPE",
            n_trials=N_TRIALS,
            random_seed=7,
            parameter_ranges=ranges,
        )
    # 信號密度分析替身：只回 separation；case 清單與訓練窗不被抽樣路徑使用
    opt.signal_service = SimpleNamespace(
        analyze_signal_density=AsyncMock(return_value=SimpleNamespace(separation=0.25))
    )
    opt.positive_cases = ["p1"]
    opt.negative_cases = ["n1"]
    opt.training_window = SimpleNamespace(far_lookback_bars=None)
    return opt


@pytest.mark.slow
def test_parameter_range_fix():
    """所有完成之 trial 的 short/mid/long_period 皆在用戶配置範圍內，且確有 trial 完成。"""
    opt = _build_optimizer()
    study = optuna.create_study(
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=7)
    )

    for _ in range(N_TRIALS):
        trial = study.ask()
        try:
            value = asyncio.run(opt._objective_function(trial))
        except optuna.TrialPruned:
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
            continue
        study.tell(trial, value)

    complete = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    assert len(complete) >= N_TRIALS // 2, "足夠多的 trial 應完成，否則範圍斷言不具意義"

    violations = []
    for t in complete:
        p = t.params
        for key, (lo, hi) in (("short_period", SHORT), ("mid_period", MID), ("long_period", LONG)):
            assert key in p, f"trial #{t.number} 缺 {key}"
            if not (lo <= p[key] <= hi):
                violations.append(f"trial #{t.number}: {key}={p[key]} 超出 {lo}-{hi}")
    assert violations == []

    # 抽樣確實探索了範圍（非全落同一點）：short 至少出現 3 種不同值
    assert len({t.params["short_period"] for t in complete}) >= 3
