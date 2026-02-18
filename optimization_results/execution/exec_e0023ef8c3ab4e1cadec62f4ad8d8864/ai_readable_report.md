# Optimization Report — exec_e0023ef8c3ab4e1cadec62f4ad8d8864

## Summary
- task_type: execution
- status: completed
- completed_at: 2026-01-01T00:00:02+00:00

## Best Parameters
- best_trial_number: 0
- best_value: 0.0013083467493690767
- params: {"entry_threshold": 0.65, "exit_threshold": 0.6, "stop_loss_atr": 4.0, "take_profit_ratio": 3.5, "position_sizing_method": "fixed", "kelly_fraction": 0.7, "max_position_size": 0.4, "cooldown_bars": 15, "trailing_stop_activation": 0.01}

## Performance
- metrics: {"total_return": 0.08089430501784722, "cagr": 0.7746334191455246, "sharpe_ratio": 5.531082030162886, "sortino_ratio": 0.0, "calmar_ratio": 0.0, "max_drawdown": 0.0, "max_drawdown_duration": 0.0, "expectancy": 0.0013083467493690767, "sqn": 3.8321697795533542, "win_rate": 1.0, "profit_factor": 0.0, "avg_win": 0.0013083467493690767, "avg_loss": 0.0, "total_trades": 6.0}
- constraint_satisfaction: {"max_drawdown": {"limit": -0.3, "actual": 0.0, "satisfied": true}, "min_win_rate": {"limit": 0.4, "actual": 1.0, "satisfied": true}, "min_trades": {"limit": 5, "actual": 6.0, "satisfied": true}}

## Decision
- RECOMMENDED_ACTION: PROCEED

## Warnings
- Trade count is below 10; result stability may be limited.

## Next Steps
- 若 RECOMMENDED_ACTION=PROCEED，建議進入下一階段驗證。
- 若 RECOMMENDED_ACTION=REOPTIMIZE，建議調整搜索空間與限制後重跑。