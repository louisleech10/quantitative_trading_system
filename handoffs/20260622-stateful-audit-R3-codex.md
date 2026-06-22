# R3 Stateful Param Audit — Codex final convergence review

## Scope
- Read-only audit; no code changes.
- Sources: `docs/FEATURE_STATEFUL_PARAM_AUDIT_MERGED.md`, `momentum/FeatureEngineering`, `momentum/Analysis`, `momentum/Optimization`, `momentum/Strategy`.

## R2 Verdict Check
- SAR=B3: agree. `warmup_table.yaml:286-294` marks SAR `stateful_pivot`.
- Hurst-prior=A1 subcase: agree. `_hurst_prior.py:36-77` estimates Hurst from sample R/S slope.
- ADF default OFF: agree. `feature_config.py:174-180`, `config/scan_config.yaml:471-477`; `professional_full` turns it on at `config_manager.py:1093-1095`.
- A5 labels winsor opt-in: agree. `label_generator.py:71-80` only via `return_type="winsorized"` dispatch at `:90-96`.
- B2 ADOSC => D-prime: agree with correction. `warmup_table.yaml:377-381` says ADOSC converges after EMAs settle, despite AD level offset.
- safe_denom causal: agree with R2 recommendation. Current `numeric_guards.py:46-58` uses full-column median scale.
- schema=A-schema: agree. Selected/pinned feature sets must be retained.

## Analysis/IC/ML Online Artifacts To Retain
- DataPreprocessor winsor params/statistics: percentile q lo/hi `data_preprocessor.py:151-156`, MAD median/mad `:158-164`, zscore mean/std `:166-172`.
- DataPreprocessor drop gates: low coverage removed columns `data_preprocessor.py:113-118`; constant columns `:120-125`.
- DataPreprocessor scaler stats: time-series zscore column mean/std `data_preprocessor.py:135-138`; cross-sectional zscore is row-local `:131-134`.
- Probability calibration: bound model + expected feature count `probability_calibrator.py:58-61`; selected method/comparison/fitted transformer `:121-134`; Platt/isotonic/beta/venn fitted mappings `:224-257`, rebuilt transformer `:267-285`.
- XGBoost/LightGBM final model weights: `xgboost_analyzer.py:432-441`; `lightgbm_analyzer.py:224-238`.
- Model CV/walk-forward fitted fold artifacts are validation-only unless promoted: XGB `xgboost_analyzer.py:857-858,1116-1118`; LGBM `lightgbm_analyzer.py:333-334,546-551`; WF `walk_forward_validator.py:224-235`; CPCV `combinatorial_purged_cv.py:103-123`.
- Selected feature set/schema: IC JSON path and threshold reuse `ic_engine.py:144-164,774-823`; HDF5 `feature_names` persisted `ic_reporter.py:365-378`; redundancy-filter selected/removed features `redundancy_filter.py:101-127,185-208`.
- Factor centrality scaler/PCA if used online: `factor_centrality_analyzer.py:55-58`.

## R3 New Findings
- NEW C1: `SAREXT` should be listed with SAR as B3/stateful pivot. It is registered/generated in `talib_wrapper.py:61-62,188,237-247` and `scan_config.yaml:77`, but absent from `warmup_table.yaml` except SAR.
- NEW C2: Optimization search artifacts must be retained for deployed strategies/models: Optuna study storage/sampler/pruner `optuna_optimizer.py:681-750`, best params/trial `:2133-2164` and `:2599-2639`, checkpoint `checkpoint_manager.py:140-151`.
- Strategy layer itself found no fitted state; backtest/performance cumulative values are evaluation outputs, not online inference params.
- Sample weights are training-only artifacts. Risk: `compute_time_decay` uses `parsed.max()` over provided sample `sample_weight_calculator.py:50-68`; must be computed within train/calibration split only.
- CPCV/walk-forward split logic appears purged/forward by construction: WF `walk_forward_validator.py:117-128,176-189`; CPCV purge/embargo `combinatorial_purged_cv.py:50-82`.

## Convergence
- Not CONVERGED: R3 found two missing formal catalog items (`SAREXT`, Optimization best params/study).
- No code/schema/numeric changes made.
