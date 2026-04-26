# Optimization Report — hyper_98ef85777d45420997425e3d45991df9

## Summary
- task_type: hyperparameter
- status: completed
- completed_at: 2026-01-01T00:00:02+00:00

## Best Parameters
- best_trial_number: 1
- best_value: 0.9
- params: {"num_leaves": 10, "max_depth": 15, "learning_rate": 0.10779361932748845, "n_estimators": 251, "subsample": 0.5909124836035503, "colsample_bytree": 0.5917022549267169, "min_child_samples": 64, "reg_alpha": 5.247564316322379, "reg_lambda": 4.319450186421157, "min_gain_to_split": 0.2912291401980419}

## Performance
- metrics: {"val_auc": 0.9, "train_val_gap": 0.03}
- constraint_satisfaction: {"max_train_val_gap": {"limit": 0.1, "actual": null, "satisfied": null}}

## Decision
- RECOMMENDED_ACTION: INSUFFICIENT_DATA

## Warnings
- No trades data available.

## Next Steps
- 若 RECOMMENDED_ACTION=PROCEED，建議進入下一階段驗證。
- 若 RECOMMENDED_ACTION=REOPTIMIZE，建議調整搜索空間與限制後重跑。