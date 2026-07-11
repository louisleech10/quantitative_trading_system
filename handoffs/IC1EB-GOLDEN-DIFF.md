# IC1EB-GOLDEN-DIFF（G-2 變更腿）

- generated_at_utc: `2026-07-11T03:41:14.002896+00:00`
- head_sha: `cfcf08e2a4954e816cb6fefad820694c6aac4f73`
- generator: `scripts/ic1eb_g2_golden_diff.py`
- baseline: `handoffs/ic1eb_baseline/` (v4, 唯讀)
- newpath_freeze_manifest_sha256: `d3d2c5b74b0103a0eac3117599a36d97ec2869439fbeb5682da5fddbd8614108`

## 變化方向摘要（三方簽核）

預期：高自相關假顯著 feature 在 HAC+FDR 下轉紅（pass_old→!pass_new）。

| metric | value |
|--------|------:|
| n_feature_rows | 6488 |
| pass_both | 506 |
| pass_old_only | 273 |
| pass_new_only | 0 |
| pass_neither | 5709 |
| false_significant_to_red | 273 |
| p_hac_gt_p_iid_among_comparable | 5160 |
| n_comparable_p | 5482 |
| fraction_p_inflated | 0.941262 |

## fraction_nan_p（12h 短窗 fail-closed 比例）

| run | n_summary | fraction_nan_p (new p_value) | n_passed_old | n_passed_new |
|-----|----------:|-----------------------------:|-------------:|-------------:|
| `event_BTCUSDT_12h_e53e2290` | 499 | 0.000000 | 45 | 0 |
| `event_lowconf_BTCUSDT_12h_e53e2290` | 499 | 0.002004 | 0 | 0 |
| `full_BTCUSDT_12h_e53e2290` | 499 | 0.000000 | 21 | 0 |
| `long_BCHUSDT_12h_e53e2290` | 498 | 0.002008 | 22 | 2 |
| `long_BCHUSDT_12h_f754aad4` | 498 | 0.002008 | 27 | 3 |
| `long_BTCUSDT_12h_e53e2290` | 499 | 0.002004 | 39 | 0 |
| `long_BTCUSDT_12h_f754aad4` | 499 | 0.002004 | 40 | 0 |
| `long_ETHUSDT_12h_e53e2290` | 500 | 0.002000 | 37 | 0 |
| `long_ETHUSDT_12h_f754aad4` | 499 | 0.002004 | 37 | 0 |
| `xsec_3sym_12h_e53e2290` | 500 | 0.000000 | 500 | 500 |

## Per-run 通過集合

| run | n_rows | pass_old | pass_new | old_only | new_only |
|-----|-------:|---------:|---------:|---------:|---------:|
| `event_BTCUSDT_12h_e53e2290` | 499 | 45 | 0 | 45 | 0 |
| `event_lowconf_BTCUSDT_12h_e53e2290` | 499 | 0 | 0 | 0 | 0 |
| `full_BTCUSDT_12h_e53e2290` | 499 | 21 | 0 | 21 | 0 |
| `long_BCHUSDT_12h_e53e2290` | 498 | 22 | 2 | 20 | 0 |
| `long_BCHUSDT_12h_f754aad4` | 498 | 27 | 3 | 24 | 0 |
| `long_BCHUSDT_1h_4a8a0b37` | 499 | 4 | 1 | 3 | 0 |
| `long_BTCUSDT_12h_e53e2290` | 499 | 39 | 0 | 39 | 0 |
| `long_BTCUSDT_12h_f754aad4` | 499 | 40 | 0 | 40 | 0 |
| `long_BTCUSDT_1h_4a8a0b37` | 499 | 2 | 0 | 2 | 0 |
| `long_ETHUSDT_12h_e53e2290` | 500 | 37 | 0 | 37 | 0 |
| `long_ETHUSDT_12h_f754aad4` | 499 | 37 | 0 | 37 | 0 |
| `long_ETHUSDT_1h_4a8a0b37` | 500 | 5 | 0 | 5 | 0 |
| `xsec_3sym_12h_e53e2290` | 500 | 500 | 500 | 0 | 0 |

## Per-feature 對照表（13 顆全量）

| run | feature_name | p_iid_old | p_hac | q | pass_old | pass_new | reason |
|-----|--------------|----------:|------:|--:|:--------:|:--------:|--------|
| `event_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 1.08894e-06 | 0.168298 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 0.773295 | 0.379853 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 0.0102535 | 0.0134196 | 0.822983 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 0.0283848 | 0.452054 | 0.904459 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 0.94763 | 0.64652 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` | 1.85723e-32 | 0.24723 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` | 1.1147e-07 | 0.680242 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` | 5.28513e-21 | 0.69797 | 0.974922 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` | 6.22923e-08 | 0.898153 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 1.54119e-07 | 0.621501 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 1.01778e-15 | 0.895592 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 0.000919877 | 0.400966 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 0.0501638 | 0.894337 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 0.0748346 | 0.0420743 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 0.000218652 | 0.379469 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 0.0759222 | 0.877307 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 1.27708e-07 | 0.978183 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 7.45225e-13 | 0.0830542 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 0.00738266 | 0.709075 | 0.985595 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 0.893202 | 0.266642 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 0.673996 | 0.731502 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 0.655174 | 0.940185 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 2.2435e-06 | 0.276045 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 0.0002493 | 0.372803 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 0.203474 | 0.171207 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 0.00110268 | 0.281726 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 5.20619e-14 | 0.22227 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 6.60976e-21 | 0.540393 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 0.18454 | 0.811008 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 3.78452e-07 | 0.328107 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 6.60976e-21 | 0.462161 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.00208785 | 0.493485 | 0.922281 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 0.0559584 | 0.836229 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 3.94457e-11 | 0.823309 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 0.0155253 | 0.656641 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` | 0.292877 | 0.47174 | 0.907839 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_21` | 0.00029519 | 0.841649 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.198824 | 0.635841 | 0.965707 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 0.996392 | 0.162922 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 0.00035059 | 0.947933 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` | 0.00346742 | 0.276981 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` | 0.476261 | 0.456587 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` | 0.00473691 | 0.660652 | 0.970408 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` | 4.45196e-06 | 0.763591 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 2.79019e-05 | 0.632817 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 2.28891e-22 | 0.141957 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` | 7.08581e-05 | 0.566389 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 4.61002e-23 | 0.827535 | 0.989973 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.37506e-23 | 0.895438 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` | 5.65335e-07 | 0.226561 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` | 8.64906e-06 | 0.548384 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` | 7.81452e-40 | 0.975742 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` | 0.000220172 | 0.452023 | 0.904459 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` | 0.0971236 | 0.9295 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` | 0.553563 | 0.171523 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` | 2.01286e-05 | 0.69268 | 0.974922 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 7.77916e-05 | 0.966658 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` | 1.11733e-15 | 0.671694 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 6.60709e-21 | 0.941266 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.57895e-09 | 0.45289 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 0.015589 | 0.524927 | 0.945627 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 9.85773e-08 | 0.430797 | 0.895698 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 8.31039e-10 | 0.373319 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.146063 | 0.587207 | 0.951352 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 0.0740857 | 0.931894 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 9.59271e-10 | 0.680647 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 7.61324e-14 | 0.938049 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 0.0084054 | 0.616306 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 3.80109e-14 | 0.208682 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` | 1.2514e-08 | 0.953687 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 6.2747e-07 | 0.924168 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` | 1.07253e-22 | 0.382189 | 0.878859 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` | 3.51395e-17 | 0.0331672 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` | 0.00308394 | 0.0291841 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` | 0.0631735 | 0.455862 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` | 0.184473 | 0.919151 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 0.613576 | 0.782731 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` | 0.332329 | 0.313022 | 0.878618 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` | 0.3235 | 0.0954998 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` | 0.0139093 | 0.860617 | 0.992075 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 0.00014933 | 0.131707 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` | 9.75782e-05 | 0.365613 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` | 1.71218e-05 | 0.221552 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` | 0.446686 | 0.436235 | 0.901666 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` | 1.07682e-09 | 0.049106 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` | 0.0793442 | 0.210069 | 0.869245 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` | 0.00029527 | 0.54775 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` | 0.744502 | 0.409255 | 0.882961 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` | 0.0805001 | 0.500296 | 0.926387 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` | 3.89488e-06 | 0.986854 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` | 4.00553e-05 | 0.254774 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` | 4.19938e-08 | 0.109158 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` | 5.14867e-05 | 0.31913 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` | 0.260313 | 0.303513 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` | 7.86617e-06 | 0.0338716 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` | 0.001592 | 0.403979 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` | 0.0041455 | 0.164913 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` | 4.43653e-19 | 0.330685 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` | 0.0257663 | 0.506641 | 0.929097 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` | 0.325664 | 0.661401 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` | 4.67563e-09 | 0.824327 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 0.000548168 | 0.300499 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 0.00024171 | 0.916172 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` | 0.911414 | 0.26872 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` | 2.66922e-06 | 0.456745 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` | 0.00251563 | 0.282837 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` | 0.0118451 | 0.261274 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` | 0.00389867 | 0.943138 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` | 0.0142601 | 0.627604 | 0.965707 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` | 0.00413537 | 0.988099 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` | 0.00360837 | 0.822004 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` | 0.000134525 | 0.802871 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` | 8.48488e-10 | 0.853174 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` | 1.1517e-11 | 0.773164 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` | 1.55228e-05 | 0.979557 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` | 0.713293 | 0.77047 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` | 6.49535e-14 | 0.932267 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` | 0.387046 | 0.82329 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` | 0.0486413 | 0.948241 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` | 6.34082e-05 | 0.218801 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_apen_55_Max_W8` | 0.0288678 | 0.267399 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` | 4.6305e-05 | 0.598115 | 0.956601 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` | 0.061463 | 0.329266 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_perm_55_Min_W233` | 0.000462048 | 0.904934 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` | 1.92825e-10 | 0.379662 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 0.0564277 | 0.140201 | 0.822983 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 0.117395 | 0.690986 | 0.974922 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 5.72651e-20 | 0.0135598 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` | 9.06728e-16 | 0.582792 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` | 1.64753e-12 | 0.824619 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 0.0442407 | 0.415823 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 0.000848119 | 0.712278 | 0.987296 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 0.00119543 | 0.338433 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 0.00079189 | 0.117936 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 3.537e-11 | 0.334364 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 2.01074e-06 | 0.126736 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 0.0023972 | 0.73603 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 0.139453 | 0.928678 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.000326369 | 0.869969 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 1.71094e-06 | 0.8837 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 7.96635e-22 | 0.374808 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 0.680922 | 0.670316 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 0.0963238 | 0.30751 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 1.09865e-07 | 0.568629 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 4.09618e-12 | 0.645733 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 0.045874 | 0.672012 | 0.970408 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.204018 | 0.321784 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` | 2.90488e-13 | 0.168028 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` | 5.49384e-21 | 0.438524 | 0.901666 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` | 3.50117e-37 | 0.564081 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` | 4.36991e-25 | 0.0508998 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` | 1.88133e-11 | 0.194418 | 0.869245 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 0.0921724 | 0.202743 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` | 4.34066e-11 | 0.340265 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` | 1.6318e-05 | 0.314602 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 0.0251508 | 0.556143 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` | 3.4175e-05 | 0.229255 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` | 2.89131e-05 | 0.113873 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 2.70002e-11 | 0.32745 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` | 0.0295388 | 0.861551 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 0.0421756 | 0.419558 | 0.887117 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 7.51709e-07 | 0.96874 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` | 0.308845 | 0.0305035 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` | 0.00874224 | 0.361235 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.016837 | 0.42585 | 0.892854 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` | 0.000118046 | 0.799375 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 1.12771e-08 | 0.878843 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` | 4.78715e-11 | 0.155231 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` | 0.730593 | 0.54183 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` | 4.8107e-23 | 0.876802 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` | 3.35538e-05 | 0.962274 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` | 1.80782e-05 | 0.134146 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` | 4.08572e-05 | 0.565839 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` | 0.0266145 | 0.984443 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 1.70726e-06 | 0.132509 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` | 4.28549e-05 | 0.794503 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 1.83935e-05 | 0.475195 | 0.907839 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` | 0.00142692 | 0.306168 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` | 3.38046e-06 | 0.948021 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` | 4.08321e-06 | 0.388094 | 0.88279 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` | 0.916403 | 0.789672 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` | 2.36193e-10 | 0.270519 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` | 1.0081e-07 | 0.371877 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 0.000930532 | 0.963075 | 0.992075 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 1.32458e-13 | 0.687025 | 0.974922 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 0.000808647 | 0.142402 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 0.000525861 | 0.96499 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 0.127019 | 0.130327 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 1.11809e-10 | 0.583184 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.63069e-15 | 0.408134 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 0.039439 | 0.229846 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 1.74459e-08 | 0.12487 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 1.24101e-08 | 0.632198 | 0.965707 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 0.00273856 | 0.998353 | 0.998353 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 1.41616e-19 | 0.722501 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 3.24045e-16 | 0.138806 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 8.55881e-23 | 0.352504 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 0.000137692 | 0.342424 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 4.29505e-07 | 0.727946 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 0.453664 | 0.0692584 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 0.193311 | 0.80208 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 0.262849 | 0.573745 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 0.175492 | 0.720228 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 7.05335e-21 | 0.801154 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 0.000979145 | 0.823728 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` | 0.0777003 | 0.548403 | 0.947911 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` | 0.0380083 | 0.0225774 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` | 6.88421e-07 | 0.72872 | 0.989146 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` | 5.71355e-06 | 0.406116 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` | 0.00383792 | 0.57534 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` | 0.120206 | 0.855083 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 0.281836 | 0.751392 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` | 0.350874 | 0.945919 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` | 0.974051 | 0.819497 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 1.04151e-08 | 0.817626 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` | 3.57808e-08 | 0.810617 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 4.33322e-10 | 0.0794763 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` | 1.89378e-11 | 0.872419 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` | 0.000166085 | 0.166544 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` | 0.000163418 | 0.57763 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` | 0.0274055 | 0.648748 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` | 0.803702 | 0.48924 | 0.921249 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` | 1.0831e-10 | 0.326861 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` | 2.06641e-12 | 0.0359047 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` | 1.94929e-08 | 0.468564 | 0.907839 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` | 3.6228e-12 | 0.508303 | 0.929097 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` | 0.00163505 | 0.915177 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 0.133141 | 0.963725 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 0.000181125 | 0.741215 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 0.617997 | 0.0933997 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 4.28896e-10 | 0.604336 | 0.963304 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 0.000357522 | 0.283478 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 0.0391613 | 0.389206 | 0.88279 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 0.00168471 | 0.562148 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 2.49379e-43 | 0.20708 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 2.64806e-05 | 0.061106 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 0.00207807 | 0.901409 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 0.151612 | 0.153403 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 5.30506e-14 | 0.111892 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 2.17976e-14 | 0.028669 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 0.407524 | 0.699443 | 0.974922 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 0.000871992 | 0.575441 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 1.52441e-08 | 0.465018 | 0.906422 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 0.338331 | 0.151792 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 0.0189664 | 0.961409 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 1.05133e-07 | 0.205574 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 0.00259606 | 0.0324722 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 1.17452e-19 | 0.0231193 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 0.275836 | 0.0614708 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 0.00441346 | 0.0520587 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 1.0618e-15 | 0.294731 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 5.28097e-05 | 0.803603 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 2.26729e-05 | 0.512927 | 0.934126 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 1.57294e-18 | 0.407854 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 1.24231e-16 | 0.696995 | 0.974922 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 1.14231e-12 | 0.199744 | 0.869245 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 2.24764e-20 | 0.0721569 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 0.00652191 | 0.867423 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 0.129621 | 0.409326 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 8.93529e-08 | 0.476661 | 0.907839 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 9.74941e-19 | 0.228471 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 1.18722e-20 | 0.26521 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 8.27163e-15 | 0.428072 | 0.893757 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 4.92633e-06 | 0.887657 | 0.992075 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 1.23877e-06 | 0.322656 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 0.0680437 | 0.0695302 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 0.11271 | 0.300546 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 2.40091e-19 | 0.354802 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 2.37094e-06 | 0.0759838 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 0.00591538 | 0.409377 | 0.882961 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 0.685365 | 0.169289 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 0.928898 | 0.968979 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 0.0028775 | 0.632069 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 0.159429 | 0.863397 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 2.54508e-21 | 0.111715 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 0.43215 | 0.886798 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 0.606824 | 0.667475 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 0.0928059 | 0.0448179 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 1.26855e-05 | 0.453756 | 0.904459 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 0.00128323 | 0.598043 | 0.956601 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 2.03647e-05 | 0.462198 | 0.904459 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 0.0685168 | 0.98306 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 0.979838 | 0.141479 | 0.822983 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 0.00124647 | 0.894195 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 0.000588626 | 0.255131 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 1.48932e-06 | 0.561217 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 6.33503e-13 | 0.439088 | 0.901666 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 0.0129985 | 0.373962 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 0.61301 | 0.829276 | 0.989973 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 1.16348e-24 | 0.245286 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 0.0404092 | 0.534608 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 0.1325 | 0.766797 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 7.70102e-10 | 0.689561 | 0.974922 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 3.27374e-05 | 0.975609 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 9.46809e-07 | 0.240834 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 1.90111e-11 | 0.346661 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 0.116057 | 0.315172 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 4.94077e-32 | 0.0754529 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 0.0674876 | 0.127036 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 2.74861e-08 | 0.0125048 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 0.033703 | 0.677053 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 0.792972 | 0.53232 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 9.56366e-10 | 0.975083 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 1.00269e-12 | 0.950021 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 1.83252e-23 | 0.777243 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 2.21768e-15 | 0.0981629 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 2.00958e-07 | 0.366266 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 9.39913e-15 | 0.91721 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 0.336212 | 0.779292 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 5.64666e-13 | 0.0598107 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 0.00032811 | 0.1403 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 8.72171e-17 | 0.0188208 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 3.16762e-20 | 0.736581 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 6.89228e-06 | 0.516575 | 0.937349 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 2.00313e-08 | 0.563759 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 8.27589e-16 | 0.310426 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 2.15398e-08 | 0.35325 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.00457327 | 0.320664 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 3.18941e-12 | 0.306669 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` | 1.73809e-08 | 0.737154 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 0.140322 | 0.608157 | 0.963398 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` | 8.64656e-18 | 0.977274 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 0.02909 | 0.369673 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` | 1.70036e-19 | 0.321928 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` | 0.000167264 | 0.450313 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 5.6419e-16 | 0.784605 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 1.06242e-05 | 0.916578 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 1.64219e-11 | 0.380324 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 6.7454e-21 | 0.264698 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` | 6.905e-13 | 0.985198 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 8.30816e-10 | 0.424282 | 0.892854 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 3.79468e-06 | 0.0119721 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` | 9.39569e-12 | 0.392328 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` | 9.66511e-13 | 0.855585 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` | 2.50997e-05 | 0.89946 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 1.04897e-09 | 0.363945 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 9.59863e-35 | 0.252606 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` | 0.00454095 | 0.675988 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` | 0.00747119 | 0.918875 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 0.649713 | 0.805548 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 0.819882 | 0.506407 | 0.929097 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 4.39671e-10 | 0.350076 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` | 0.0325991 | 0.343813 | 0.878618 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` | 0.198368 | 0.198785 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` | 0.653275 | 0.201252 | 0.869245 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 0.00947471 | 0.619281 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 0.013998 | 0.792873 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` | 1.00243e-11 | 0.413876 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 3.27541e-09 | 0.279853 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 0.500123 | 0.867579 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 4.22305e-12 | 0.204398 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` | 1.54657e-09 | 0.1959 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 1.93857e-08 | 0.0392835 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 0.000123451 | 0.157407 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` | 0.000420891 | 0.606167 | 0.963304 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` | 3.22517e-06 | 0.698017 | 0.974922 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` | 0.30029 | 0.367652 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` | 0.157328 | 0.131116 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 1.6575e-08 | 0.736643 | 0.989146 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 4.6535e-05 | 0.655124 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 0.00526254 | 0.966996 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 2.63653e-10 | 0.0991495 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 1.34452e-15 | 0.798133 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 0.000341401 | 0.092586 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` | 1.08991e-08 | 0.37813 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` | 3.20156e-07 | 0.790023 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_34_Momentum_L5` | 0.0764433 | 0.795968 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` | 1.68864e-06 | 0.570817 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 1.22775e-09 | 0.975431 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 0.943943 | 0.156843 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 4.4041e-24 | 0.622823 | 0.965707 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 1.74998e-14 | 0.0790629 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 8.63628e-15 | 0.161941 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 5.86735e-22 | 0.915798 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 3.10455e-06 | 0.300528 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 2.58153e-14 | 0.0262251 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 3.47267e-10 | 0.529818 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 1.18467e-05 | 0.593736 | 0.955724 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 0.175343 | 0.201365 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 5.85653e-19 | 0.023643 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 0.640518 | 0.795599 | 0.989146 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 0.0244078 | 0.0406881 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 2.88632e-09 | 0.797978 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 0.551177 | 0.6776 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 9.69738e-14 | 0.63796 | 0.965707 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 0.160321 | 0.115059 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 7.34681e-08 | 0.334757 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 5.21811e-20 | 0.106978 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 0.0267013 | 0.65705 | 0.970408 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 7.34385e-06 | 0.578793 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 0.759961 | 0.210779 | 0.869245 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 3.95263e-05 | 0.491387 | 0.921813 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 6.29415e-05 | 0.249138 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 0.0433703 | 0.81309 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 3.11284e-08 | 0.484645 | 0.916052 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 3.11505e-22 | 0.756443 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 0.0554402 | 0.271726 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 0.138645 | 0.116307 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 0.0346088 | 0.146738 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.51693 | 0.370362 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 0.997814 | 0.168137 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 1.88981e-07 | 0.0886783 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 4.29559e-10 | 0.227269 | 0.875521 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` | 9.64786e-13 | 0.0748566 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 0.0173117 | 0.533338 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 5.79489e-26 | 0.0841329 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 2.09212e-05 | 0.227151 | 0.875521 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 0.107258 | 0.408525 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` | 0.127577 | 0.499141 | 0.926387 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` | 2.58441e-06 | 0.748832 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` | 0.0565555 | 0.34245 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 0.00789228 | 0.622717 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 3.37018e-05 | 0.4698 | 0.907839 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` | 0.0334536 | 0.461168 | 0.904459 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 2.93671e-07 | 0.207047 | 0.869245 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` | 2.47956e-14 | 0.193712 | 0.869245 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` | 0.999293 | 0.460434 | 0.904459 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` | 1.19338e-09 | 0.348925 | 0.878618 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 1.61888e-16 | 0.772511 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` | 0.00249987 | 0.387174 | 0.88279 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` | 0.822576 | 0.295859 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` | 0.312195 | 0.0815343 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` | 0.777177 | 0.142818 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 5.20139e-17 | 0.80668 | 0.989146 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 0.390237 | 0.760284 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 2.3376e-06 | 0.921435 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 0.250473 | 0.96972 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 8.6665e-05 | 0.117524 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` | 0.0137593 | 0.0996229 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.205811 | 0.717291 | 0.988752 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` | 0.800687 | 0.818097 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 5.9104e-14 | 0.367126 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 0.0132427 | 0.567369 | 0.947911 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.022712 | 0.483764 | 0.916052 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 0.482165 | 0.354837 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 0.00310465 | 0.854113 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 0.00755607 | 0.0697915 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 0.249044 | 0.200723 | 0.869245 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 1.23491e-28 | 0.400032 | 0.882961 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 0.00190387 | 0.146616 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 0.743276 | 0.76816 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 2.7413e-06 | 0.546325 | 0.947911 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 0.148339 | 0.803654 | 0.989146 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` | 0.703773 | 0.158874 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 1.15773e-15 | 0.66725 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 2.46427e-05 | 0.501251 | 0.926387 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` | 0.000499246 | 0.882316 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` | 0.664316 | 0.565069 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` | 1.72049e-30 | 0.625941 | 0.965707 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` | 0.00439112 | 0.324988 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` | 1.87255e-20 | 0.323654 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` | 0.000115897 | 0.18218 | 0.865791 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.102873 | 0.244219 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` | 0.720023 | 0.716495 | 0.988752 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` | 0.0851192 | 0.904692 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` | 0.000216323 | 0.0893033 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` | 4.60004e-07 | 0.593211 | 0.955724 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` | 3.70674e-15 | 0.105418 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 0.0049028 | 0.0847619 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` | 0.00466099 | 0.617965 | 0.965707 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` | 0.424269 | 0.569796 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` | 0.306312 | 0.130621 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` | 0.000373055 | 0.28672 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` | 0.0900764 | 0.240497 | 0.878618 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` | 3.61732e-06 | 0.415545 | 0.882961 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` | 1.54076e-05 | 0.918887 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` | 0.00329691 | 0.22691 | 0.875521 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` | 0.0599257 | 0.0615556 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` | 0.000163861 | 0.234503 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` | 6.5707e-19 | 0.760493 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` | 2.61313e-11 | 0.818939 | 0.989146 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` | 0.0718371 | 0.580222 | 0.947911 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` | 7.35196e-19 | 0.0015411 | 0.384505 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` | 1.1359e-11 | 0.473434 | 0.907839 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` | 0.979754 | 0.156141 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` | 0.769568 | 0.156175 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` | 6.43084e-06 | 0.675686 | 0.970408 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` | 2.77409e-11 | 0.146157 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` | 1.3149e-13 | 0.0583251 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` | 4.32419e-12 | 0.08391 | 0.822983 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` | 7.44861e-23 | 0.124928 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` | 0.000979637 | 0.160773 | 0.822983 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` | 0.00208602 | 0.854397 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` | 0.00077885 | 0.963102 | 0.992075 | True | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` | 7.01577e-08 | 0.153245 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` | 0.0247333 | 0.41345 | 0.882961 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` | 0.149428 | 0.253704 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` | 0.00167536 | 0.679751 | 0.970408 | False | False | removed:icir |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` | 0.192335 | 0.524535 | 0.945627 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` | 0.00287009 | 0.909733 | 0.992075 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` | 0.741461 | 0.316796 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` | 1.39226e-06 | 0.000415243 | 0.207206 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` | 0.0499017 | 0.95037 | 0.992075 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` | 1.3019e-07 | 0.023184 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` | 5.36528e-14 | 0.638644 | 0.965707 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` | 0.00243336 | 0.635748 | 0.965707 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` | 0.0810119 | 0.302484 | 0.878618 | False | False | removed:ic_mean |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` | 0.284852 | 0.115029 | 0.822983 | False | False | removed:p_value |
| `event_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` | 1.61168e-06 | 0.996256 | 0.998256 | False | False | removed:p_value |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` |  | 0.731814 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` |  | 0.764247 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` |  | 0.0263641 | 0.423527 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` |  | 0.0387048 | 0.470122 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` |  | 0.0166344 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` |  | 0.254681 | 0.712535 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` |  | 0.023703 | 0.403903 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` |  | 0.107638 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` |  | 0.307683 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` |  | 0.0185845 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` |  | 0.788181 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` |  | 0.928009 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` |  | 0.0937558 | 0.576425 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` |  | 0.168431 | 0.673684 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` |  | 0.793217 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` |  | 0.0455119 | 0.519879 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` |  | 0.214181 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` |  | 0.83644 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` |  | 0.197999 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` |  | 0.706228 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` |  | 0.215492 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` |  | 0.594636 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` |  | 0.16 | 0.662178 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` |  | 0.619873 | 0.899429 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` |  | 0.793064 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` |  | 0.121346 | 0.598318 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` |  | 0.413665 | 0.811044 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` |  | 0.355912 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` |  | 0.00150688 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` |  | 0.352407 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` |  | 0.331792 | 0.754443 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` |  | 0.270895 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` |  | 0.0545827 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` |  | 0.944274 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` |  | 0.914629 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` |  | 0.456794 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_21` |  | 0.0550058 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` |  | 0.460513 | 0.827816 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` |  | 0.721582 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` |  | 0.11239 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` |  | 0.0964356 | 0.578613 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` |  | 0.947873 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` |  | 0.490054 | 0.835777 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` |  | 0.132816 | 0.616332 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` |  | 0.0664979 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` |  | 0.00309058 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` |  | 0.0320558 | 0.431454 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` |  | 0.354507 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` |  | 0.268653 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` |  | 0.00186132 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` |  | 0.367912 | 0.782387 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` |  | 0.62876 | 0.903427 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` |  | 0.237334 | 0.70143 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` |  | 0.670709 | 0.924845 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` |  | 0.752163 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` |  | 0.208866 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` |  | 0.803725 | 0.950725 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` |  | 0.109943 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` |  | 0.821091 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` |  | 0.193379 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` |  | 0.0011587 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` |  | 0.296182 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` |  | 0.759794 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` |  | 0.737002 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` |  | 0.868543 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` |  | 0.0688261 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` |  | 0.397849 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` |  | 0.0158258 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` |  | 0.390949 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` |  | 0.814538 | 0.956698 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` |  | 0.258871 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` |  | 0.571078 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` |  | 0.0811608 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` |  | 0.133662 | 0.616332 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` |  | 0.0152991 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` |  | 0.600325 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` |  | 0.391214 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` |  | 0.939349 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` |  | 0.695599 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` |  | 0.94049 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` |  | 0.0901047 | 0.569059 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` |  | 0.25237 | 0.712535 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` |  | 0.839427 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` |  | 0.567828 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` |  | 0.322615 | 0.743806 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` |  | 0.229034 | 0.697395 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` |  | 0.214544 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` |  | 0.152729 | 0.660298 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` |  | 0.474733 | 0.830782 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` |  | 0.196906 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` |  | 0.397612 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` |  | 0.383488 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` |  | 0.238035 | 0.70143 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` |  | 0.214046 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` |  | 0.219042 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` |  | 0.262848 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` |  | 0.558403 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` |  | 0.567696 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` |  | 0.569414 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` |  | 0.345272 | 0.771057 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` |  | 0.655542 | 0.917022 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` |  | 0.558939 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` |  | 0.0684435 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` |  | 0.611092 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` |  | 0.743317 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` |  | 0.587159 | 0.894205 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` |  | 0.790981 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` |  | 0.551656 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` |  | 0.0834394 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` |  | 0.980327 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` |  | 0.123671 | 0.603604 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` |  | 0.92803 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` |  | 0.878903 | 0.972653 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` |  | 0.114796 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` |  | 0.0641854 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` |  | 0.84368 | 0.961447 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` |  | 0.682123 | 0.930677 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` |  | 0.150678 | 0.658224 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` |  | 0.0189659 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` |  | 0.539253 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_apen_55_Max_W8` |  | 0.477587 | 0.830782 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` |  | 0.241688 | 0.708004 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` |  | 0.576223 | 0.888418 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_perm_55_Min_W233` |  | 0.0284028 | 0.428624 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` |  | 0.610779 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` |  | 0.0294875 | 0.429918 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` |  | 0.457527 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` |  | 0.379599 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` |  | 0.652242 | 0.917022 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` |  | 0.203082 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` |  | 0.218639 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` |  | 0.181232 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` |  | 0.650899 | 0.917022 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` |  | 0.988739 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` |  | 0.314063 | 0.737751 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` |  | 0.112272 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` |  | 0.318794 | 0.743806 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` |  | 0.278351 | 0.714129 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` |  | 0.26933 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` |  | 0.306483 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` |  | 0.550306 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` |  | 0.110679 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` |  | 0.110148 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` |  | 0.0822969 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` |  | 0.0243315 | 0.403903 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` |  | 0.0140989 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` |  | 0.560311 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` |  | 0.0184509 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` |  | 0.3998 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` |  | 0.258192 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` |  | 0.932661 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` |  | 0.228305 | 0.697395 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` |  | 0.286135 | 0.727017 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` |  | 0.321955 | 0.743806 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` |  | 0.00207352 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` |  | 0.000303704 | 0.0756223 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` |  | 0.868018 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` |  | 0.458312 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` |  | 0.00225762 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` |  | 0.382651 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` |  | 0.298757 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` |  | 0.119334 | 0.598318 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` |  | 0.00992018 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` |  | 0.76649 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` |  | 0.670792 | 0.924845 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` |  | 0.837578 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` |  | 0.523854 | 0.878382 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` |  | 0.308078 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` |  | 0.0505851 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` |  | 0.858273 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` |  | 0.43314 | 0.81343 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` |  | 0.0142717 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` |  | 0.217006 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` |  | 0.583773 | 0.891776 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` |  | 0.0703978 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` |  | 0.828716 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` |  | 0.988341 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` |  | 0.197455 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` |  | 0.868246 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` |  | 0.0700427 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` |  | 0.73844 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` |  | 0.605881 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` |  | 0.00231628 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` |  | 0.0518029 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` |  | 0.229664 | 0.697395 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` |  | 0.638279 | 0.912339 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` |  | 0.331748 | 0.754443 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` |  | 0.0429049 | 0.50873 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` |  | 0.31246 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` |  | 0.0776931 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` |  | 0.0174577 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` |  | 0.818411 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` |  | 0.0639745 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` |  | 0.0697299 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` |  | 0.0302151 | 0.429918 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` |  | 0.378575 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` |  | 0.304299 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` |  | 0.0189511 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` |  | 0.0549013 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` |  | 0.0190614 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` |  | 0.249061 | 0.708757 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` |  | 0.115227 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` |  | 0.234555 | 0.70143 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` |  | 0.219026 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` |  | 0.182936 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` |  | 0.60728 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` |  | 0.231154 | 0.697664 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` |  | 0.932442 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` |  | 0.742696 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` |  | 0.968092 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` |  | 0.574184 | 0.888024 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` |  | 0.000153737 | 0.0756223 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` |  | 0.12606 | 0.603604 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` |  | 0.279629 | 0.714129 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` |  | 0.0815508 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` |  | 0.213063 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` |  | 0.107263 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` |  | 0.0902725 | 0.569059 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` |  | 0.013821 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` |  | 0.333732 | 0.754443 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` |  | 0.794596 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` |  | 0.766848 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` |  | 0.958451 | 0.996469 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` |  | 0.186638 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` |  | 0.862745 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` |  | 0.385463 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` |  | 0.920225 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` |  | 0.946571 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` |  | 0.692693 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` |  | 0.243571 | 0.708757 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` |  | 0.128478 | 0.603604 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` |  | 0.772211 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` |  | 0.652968 | 0.917022 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` |  | 0.398382 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` |  | 0.452819 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` |  | 0.70924 | 0.939366 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` |  | 0.78448 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` |  | 0.045933 | 0.519879 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` |  | 0.746275 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` |  | 0.16776 | 0.673684 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` |  | 0.206986 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` |  | 0.706829 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` |  | 0.235359 | 0.70143 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` |  | 0.801799 | 0.950705 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` |  | 0.14281 | 0.640717 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` |  | 0.464463 | 0.827816 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` |  | 0.00983182 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` |  | 0.541226 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` |  | 0.0949532 | 0.576667 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` |  | 0.308941 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` |  | 0.578881 | 0.889762 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` |  | 0.496052 | 0.843118 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` |  | 0.997155 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` |  | 0.220683 | 0.682608 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` |  | 0.0834063 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` |  | 0.0624741 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` |  | 0.128382 | 0.603604 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` |  | 0.931637 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` |  | 0.17045 | 0.673684 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` |  | 0.275036 | 0.714129 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` |  | 0.48957 | 0.835777 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` |  | 0.791818 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` |  | 0.782623 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` |  | 0.771102 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` |  | 0.886724 | 0.975429 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` |  | 0.397886 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` |  | 0.213428 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` |  | 0.719174 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` |  | 0.914792 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` |  | 0.713051 | 0.941908 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` |  | 0.159422 | 0.662178 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` |  | 0.698452 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` |  | 0.194661 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` |  | 0.600643 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` |  | 0.771271 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` |  | 0.212353 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` |  | 0.0031059 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` |  | 0.309397 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` |  | 0.623099 | 0.899429 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` |  | 0.391627 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` |  | 0.433269 | 0.81343 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` |  | 0.750387 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` |  | 0.0604631 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` |  | 0.420072 | 0.8114 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` |  | 0.294695 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` |  | 0.640277 | 0.912339 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` |  | 0.392145 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` |  | 0.192185 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` |  | 0.417416 | 0.8114 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` |  | 0.659922 | 0.920564 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` |  | 0.629496 | 0.903427 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` |  | 0.971945 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` |  | 0.0346478 | 0.4418 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` |  | 0.946007 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` |  | 0.253497 | 0.712535 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` |  | 0.991731 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` |  | 0.763893 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` |  | 0.998199 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` |  | 0.128214 | 0.603604 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` |  | 0.06319 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` |  | 0.772312 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` |  | 0.181609 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` |  | 0.750889 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` |  | 0.849975 | 0.964209 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` |  | 0.138435 | 0.629027 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` |  | 0.556069 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` |  | 0.932858 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` |  | 0.599505 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` |  | 0.55892 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` |  | 0.42666 | 0.81343 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` |  | 0.928247 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` |  | 0.138942 | 0.629027 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` |  | 0.609392 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` |  | 0.734495 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` |  | 0.915631 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` |  | 0.196155 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` |  | 0.980215 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` |  | 0.386235 | 0.796401 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` |  | 0.405268 | 0.797721 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` |  | 0.562257 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` |  | 0.160771 | 0.662178 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` |  | 0.995759 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` |  | 0.162172 | 0.662178 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` |  | 0.217288 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` |  | 0.334803 | 0.754443 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` |  | 0.47581 | 0.830782 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` |  | 0.278822 | 0.714129 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` |  | 0.175706 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` |  | 0.525766 | 0.878629 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` |  | 0.356874 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` |  | 0.617013 | 0.899429 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` |  | 0.120204 | 0.598318 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` |  | 0.677148 | 0.926428 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` |  | 0.421422 | 0.8114 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` |  | 0.271959 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` |  | 0.641202 | 0.912339 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` |  | 0.27012 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` |  | 0.247918 | 0.708757 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` |  | 0.444747 | 0.823361 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` |  | 0.484977 | 0.832976 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` |  | 0.891429 | 0.975674 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` |  | 0.861622 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` |  | 0.0278023 | 0.428624 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` |  | 0.738637 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` |  | 0.267788 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` |  | 0.424207 | 0.812519 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` |  | 0.664974 | 0.922444 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` |  | 0.309521 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` |  | 0.685477 | 0.932699 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` |  | 0.835259 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` |  | 0.870176 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` |  | 0.465628 | 0.827816 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` |  | 0.70289 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` |  | 0.874207 | 0.969611 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` |  | 0.86181 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` |  | 0.421811 | 0.8114 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` |  | 0.887288 | 0.975429 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` |  | 0.703641 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` |  | 0.246159 | 0.708757 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` |  |  |  | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` |  | 0.790322 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` |  | 0.673258 | 0.924845 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` |  | 0.114073 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` |  | 0.545947 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` |  | 0.185157 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` |  | 0.909816 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_34_Momentum_L5` |  | 0.108719 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` |  | 0.976493 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` |  | 0.302135 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` |  | 0.474913 | 0.830782 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` |  | 0.535197 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` |  | 0.421993 | 0.8114 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` |  | 0.465344 | 0.827816 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` |  | 0.753568 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` |  | 0.440314 | 0.818195 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` |  | 0.988994 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` |  | 0.184663 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` |  | 0.320073 | 0.743806 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` |  | 0.478784 | 0.830782 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` |  | 0.481531 | 0.832647 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` |  | 0.467101 | 0.827816 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` |  | 0.169375 | 0.673684 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` |  | 0.582961 | 0.891776 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` |  | 0.333123 | 0.754443 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` |  | 0.0594863 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` |  | 0.890152 | 0.975674 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` |  | 0.664318 | 0.922444 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` |  | 0.357648 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` |  | 0.528271 | 0.879862 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` |  | 0.0319853 | 0.431454 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` |  | 0.0869306 | 0.569059 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` |  | 0.0543714 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` |  | 0.247356 | 0.708757 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` |  | 0.652269 | 0.917022 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` |  | 0.153804 | 0.660298 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` |  | 0.981461 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` |  | 0.072993 | 0.546958 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` |  | 0.369131 | 0.782387 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` |  | 0.369199 | 0.782387 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` |  | 0.47335 | 0.830782 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` |  | 0.112665 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` |  | 0.951385 | 0.991192 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` |  | 0.743334 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` |  | 0.198338 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` |  | 0.277547 | 0.714129 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` |  | 0.960563 | 0.996584 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` |  | 0.808876 | 0.95455 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` |  | 0.993544 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` |  | 0.36866 | 0.782387 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` |  | 0.828818 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` |  | 0.622678 | 0.899429 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` |  | 0.908323 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` |  | 0.265972 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` |  | 0.728459 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` |  | 0.14925 | 0.658224 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` |  | 0.113374 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` |  | 0.311405 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` |  | 0.823893 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` |  | 0.450698 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` |  | 0.882184 | 0.974118 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` |  | 0.930091 | 0.988433 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` |  | 0.703774 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` |  | 0.0935813 | 0.576425 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` |  | 0.610753 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` |  | 0.846737 | 0.962729 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` |  | 0.971457 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` |  | 0.600206 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` |  | 0.61104 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` |  | 0.348544 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` |  | 0.831333 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` |  | 0.200463 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` |  | 0.434483 | 0.81343 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` |  | 0.729205 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` |  | 0.457085 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` |  | 0.403846 | 0.797721 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` |  | 0.150618 | 0.658224 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` |  | 0.00294391 | 0.140612 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` |  | 0.16222 | 0.662178 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` |  | 0.485066 | 0.832976 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` |  | 0.00370953 | 0.153946 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` |  | 0.0882076 | 0.569059 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` |  | 0.554438 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` |  | 0.994648 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` |  | 0.565714 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` |  | 0.0585638 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` |  | 0.302825 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` |  | 0.364881 | 0.782387 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` |  | 0.293464 | 0.737465 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` |  | 0.119071 | 0.598318 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` |  | 0.543132 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` |  | 0.0752711 | 0.55125 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` |  | 0.404428 | 0.797721 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` |  | 0.0501764 | 0.537116 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` |  | 0.854834 | 0.967293 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` |  | 0.431543 | 0.81343 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` |  | 0.791751 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` |  | 0.184091 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` |  | 0.83541 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` |  | 0.502616 | 0.848484 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` |  | 0.19824 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` |  | 0.449246 | 0.826955 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` |  | 0.0789495 | 0.554038 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` |  | 0.739219 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` |  | 0.352432 | 0.774385 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` |  | 0.433935 | 0.81343 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` |  | 0.0686763 | 0.539355 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` |  | 0.559797 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` |  | 0.035486 | 0.4418 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` |  | 0.214528 | 0.681767 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` |  | 0.791724 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` |  | 0.440171 | 0.818195 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` |  | 0.973352 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` |  | 0.265367 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` |  | 0.591687 | 0.89507 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` |  | 0.695055 | 0.938668 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` |  | 0.813401 | 0.956698 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` |  | 0.160037 | 0.662178 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` |  | 0.728424 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` |  | 0.828884 | 0.958795 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` |  | 0.0151827 | 0.351577 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` |  | 0.547129 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` |  | 0.34298 | 0.769387 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` |  | 0.759097 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` |  | 0.785441 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` |  | 0.674134 | 0.924845 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` |  | 0.982336 | 0.998199 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` |  | 0.498273 | 0.844014 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` |  | 0.900192 | 0.983104 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` |  | 0.264622 | 0.71282 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` |  | 0.57125 | 0.886239 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` |  | 0.0735867 | 0.546958 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` |  | 0.0202663 | 0.36045 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` |  | 0.519156 | 0.873445 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` |  | 0.947251 | 0.989603 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` |  | 0.654118 | 0.917022 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` |  | 0.778584 | 0.944412 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` |  | 0.101091 | 0.591575 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` |  | 0.0343945 | 0.4418 | False | False | removed:ic_mean |
| `event_lowconf_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` |  | 0.620216 | 0.899429 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 4.48607e-08 | 0.130242 | 0.764598 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 0.00863242 | 0.0380544 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 4.19296e-08 | 0.105583 | 0.712491 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 1.09811e-136 | 0.443658 | 0.916229 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 5.40091e-05 | 0.322778 | 0.873317 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` | 1.12151e-40 | 0.808823 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` | 0.152565 | 0.270241 | 0.861093 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` | 2.89483e-28 | 0.842296 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` | 6.94842e-15 | 0.542817 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 0.0222101 | 0.874409 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 9.34489e-07 | 0.444344 | 0.916229 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 4.87993e-28 | 0.631889 | 0.9762 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 8.81928e-154 | 0.924741 | 0.985996 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 2.62382e-29 | 0.577152 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 3.90555e-110 | 0.54832 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 4.07767e-20 | 0.669838 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 2.01918e-61 | 0.578613 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.997227 | 0.317422 | 0.873317 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 3.47359e-35 | 0.887007 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 3.6207e-50 | 0.815071 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 1.4125e-61 | 0.664686 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 0.268427 | 0.864241 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 0.0302438 | 0.528768 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 3.60955e-21 | 0.36938 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 1.01682e-73 | 0.702285 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 1.30186e-109 | 0.431599 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 6.64411e-14 | 0.0289692 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 7.65439e-30 | 0.734419 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.49998e-51 | 0.901336 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 1.54544e-60 | 0.23375 | 0.821123 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 7.65439e-30 | 0.678855 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.118939 | 0.0832717 | 0.704281 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 6.79383e-186 | 0.967929 | 0.995869 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 3.47095e-08 | 0.72454 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 1.66323e-05 | 0.829658 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` | 9.97214e-15 | 0.894883 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_21` | 9.04025e-230 | 0.78179 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.0158284 | 0.568284 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 0.438542 | 0.0893205 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 2.12462e-43 | 0.857701 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` | 0.436383 | 0.138563 | 0.789391 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` | 2.97936e-14 | 0.139211 | 0.789391 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` | 2.00601e-10 | 0.643311 | 0.979264 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` | 5.40553e-76 | 0.397831 | 0.909044 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 6.7829e-91 | 0.453273 | 0.923569 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 6.68478e-230 | 0.549417 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` | 6.495e-89 | 0.763731 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 0.00368934 | 0.76176 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.33137e-15 | 0.959798 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` | 4.44416e-63 | 0.432803 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` | 3.42042e-08 | 0.278448 | 0.861093 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` | 5.75089e-09 | 0.344799 | 0.877831 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` | 1.36487e-10 | 0.993199 | 0.999432 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` | 2.59369e-06 | 0.488496 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` | 5.8475e-07 | 0.0867606 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` | 2.59105e-89 | 0.983252 | 0.999273 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 8.05075e-114 | 0.329662 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` | 5.35158e-78 | 0.578484 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 1.05366e-53 | 0.691052 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 2.16993e-16 | 0.201648 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 6.5835e-08 | 0.862269 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 9.32359e-17 | 0.0483849 | 0.583141 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 4.97272e-13 | 0.886236 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` | 4.32966e-34 | 0.998071 | 0.999432 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 0.0717182 | 0.906437 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 0.0353168 | 0.804146 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 3.54899e-20 | 0.702843 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 2.9737e-40 | 0.0954485 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 4.79039e-98 | 0.321913 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` | 0.404414 | 0.181736 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 8.50798e-07 | 0.780933 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` | 1.56639e-101 | 0.00187566 | 0.233989 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` | 5.13968e-149 | 0.000766534 | 0.233989 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` | 2.51816e-26 | 0.330053 | 0.873317 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` | 0.0294408 | 0.402339 | 0.909044 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` | 7.86479e-09 | 0.751458 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 0.887287 | 0.830694 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` | 8.96754e-53 | 0.878246 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` | 6.36644e-05 | 0.84024 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` | 3.7029e-13 | 0.352087 | 0.886961 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 9.66636e-64 | 0.390902 | 0.903055 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` | 9.77288e-27 | 0.742607 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` | 3.28796e-21 | 0.0073454 | 0.449709 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` | 0.250072 | 0.145825 | 0.790108 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` | 2.73358e-08 | 0.0439698 | 0.562588 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` | 9.93755e-07 | 0.854263 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` | 3.96816e-18 | 0.229584 | 0.818303 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` | 5.53201e-85 | 0.737192 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` | 9.17299e-08 | 0.105527 | 0.712491 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` | 5.98003e-15 | 0.996622 | 0.999432 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` | 9.87378e-25 | 0.0514193 | 0.583141 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` | 2.20608e-22 | 0.0121516 | 0.449709 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` | 5.4648e-81 | 0.512165 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` | 2.95359e-59 | 0.976221 | 0.997391 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` | 6.75441e-28 | 0.00953689 | 0.449709 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` | 5.79201e-24 | 0.979402 | 0.997391 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` | 1.59666e-107 | 0.0218902 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` | 0.0493987 | 0.24278 | 0.828549 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` | 1.35265e-17 | 0.406246 | 0.909044 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` | 2.04431e-169 | 0.807818 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` | 3.12191e-73 | 0.50993 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 3.59881e-44 | 0.0438819 | 0.562588 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 4.22229e-97 | 0.503409 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` | 0.00869727 | 0.075965 | 0.704281 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` | 1.77402e-28 | 0.0233843 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` | 1.07615e-30 | 0.0453446 | 0.565673 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` | 5.71344e-18 | 0.0364058 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` | 3.97151e-09 | 0.148838 | 0.790108 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` | 3.19177e-128 | 0.486019 | 0.948212 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` | 4.89327e-07 | 0.204678 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` | 3.99398e-37 | 0.810747 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` | 2.28856e-36 | 0.0248704 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` | 4.76259e-38 | 0.960723 | 0.99371 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` | 4.38954e-45 | 0.775781 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` | 1.56162e-185 | 0.91048 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` | 1.63396e-23 | 0.0788105 | 0.704281 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` | 0.0253455 | 0.977907 | 0.997391 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` | 7.3711e-99 | 0.565991 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` | 0.00706556 | 0.63395 | 0.976362 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` | 1.6194e-29 | 0.0370118 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_apen_55_Max_W8` | 1.35134e-24 | 0.190427 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` | 5.18849e-28 | 0.594883 | 0.952194 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` | 0.573963 | 0.586978 | 0.950981 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_perm_55_Min_W233` | 0.000176951 | 0.788693 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` | 0.577665 | 0.98764 | 0.999432 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 6.72981e-07 | 0.621222 | 0.966088 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 6.45562e-16 | 0.0388956 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 1.33452e-15 | 0.00321625 | 0.320982 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` | 1.00703e-16 | 0.411664 | 0.91071 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` | 8.75569e-15 | 0.913499 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 4.20826e-127 | 0.338341 | 0.874778 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 1.27641e-63 | 0.920917 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 6.14048e-17 | 0.414291 | 0.91071 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 1.49855e-56 | 0.574382 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 1.56476e-32 | 0.841473 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 0.00395244 | 0.272326 | 0.861093 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 7.80186e-133 | 0.695875 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 0.0115589 | 0.910209 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 7.86015e-74 | 0.0581027 | 0.616877 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 2.193e-130 | 0.847389 | 0.98402 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 5.45316e-28 | 0.0966983 | 0.706295 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 7.59241e-283 | 0.0936551 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 6.25752e-42 | 0.354334 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 2.44945e-11 | 0.670467 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 5.06563e-24 | 0.38216 | 0.899518 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 4.11453e-134 | 0.283005 | 0.861093 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.140945 | 0.576647 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` | 7.88552e-14 | 0.0827086 | 0.704281 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` | 2.64169e-12 | 0.998066 | 0.999432 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` | 1.14771e-42 | 0.615686 | 0.963095 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` | 0.245387 | 0.164804 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` | 1.88873e-14 | 0.0826117 | 0.704281 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 1.30096e-30 | 0.729782 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` | 5.51236e-17 | 0.976484 | 0.997391 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` | 6.36451e-35 | 0.878807 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 1.9971e-08 | 0.544125 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` | 4.30782e-10 | 0.0314209 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` | 2.6129e-191 | 0.0122707 | 0.449709 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 6.6363e-33 | 0.219606 | 0.817865 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` | 0.00526884 | 0.245742 | 0.828549 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 5.42258e-14 | 0.50627 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 2.02246e-08 | 0.11256 | 0.712491 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` | 0.00230288 | 0.0596508 | 0.62012 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` | 2.03844e-39 | 0.219627 | 0.817865 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.000696592 | 0.585739 | 0.950981 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` | 1.17432e-07 | 0.767635 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 0.209487 | 0.245199 | 0.828549 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` | 9.12649e-100 | 0.0695332 | 0.704281 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` | 2.66992e-79 | 0.975743 | 0.997391 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` | 5.85739e-67 | 0.725279 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` | 2.51466e-123 | 0.374091 | 0.893164 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` | 5.49595e-119 | 0.326002 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` | 0.0119205 | 0.646507 | 0.980568 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` | 1.10422e-34 | 0.880796 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 6.19783e-11 | 0.775588 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` | 9.45244e-17 | 0.306395 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 1.06683e-24 | 0.2417 | 0.828549 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` | 1.3455e-33 | 0.225331 | 0.818303 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` | 0.126029 | 0.929885 | 0.987261 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` | 1.71828e-09 | 0.998986 | 0.999432 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` | 2.02652e-42 | 0.870475 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` | 1.14731e-30 | 0.764185 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` | 4.53773e-258 | 0.297917 | 0.862612 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 4.76203e-116 | 0.818813 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 5.75147e-07 | 0.684854 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 7.80019e-147 | 0.565929 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 0.396845 | 0.57741 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 0.8207 | 0.464895 | 0.927931 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 6.8801e-45 | 0.127515 | 0.758168 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 1.87917e-58 | 0.287386 | 0.86207 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 0.397949 | 0.41692 | 0.91247 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 8.98432e-08 | 0.036503 | 0.555492 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 4.12829e-06 | 0.626776 | 0.971307 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 3.37901e-137 | 0.74653 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 1.73175e-44 | 0.844595 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 0.463092 | 0.910307 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 1.04799e-23 | 0.905424 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 6.56696e-139 | 0.334276 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 7.44033e-87 | 0.652258 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 5.01347e-16 | 0.680619 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 1.77825e-32 | 0.289815 | 0.86207 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 1.35606e-108 | 0.726725 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 0.233728 | 0.540015 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 2.34376e-80 | 0.723738 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 1.84628e-102 | 0.733876 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` | 2.44645e-29 | 0.749523 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` | 0.0667341 | 0.0415392 | 0.562588 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` | 2.89052e-35 | 0.420394 | 0.912868 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` | 1.55959e-22 | 0.542059 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` | 2.54221e-09 | 0.492552 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` | 2.74976e-06 | 0.757272 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 3.04499e-54 | 0.959158 | 0.99371 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` | 2.18703e-33 | 0.754499 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` | 1.92091e-38 | 0.731962 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 4.03638e-78 | 0.681269 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` | 1.12332e-48 | 0.455307 | 0.923569 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 8.34952e-49 | 0.0335234 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` | 1.6542e-05 | 0.694196 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` | 9.60777e-28 | 0.0567655 | 0.615783 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` | 0.000405167 | 0.469749 | 0.930177 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` | 2.49228e-21 | 0.303393 | 0.870077 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` | 9.72391e-97 | 0.784655 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` | 0.00183681 | 0.0830791 | 0.704281 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` | 3.02505e-07 | 0.0808959 | 0.704281 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` | 2.37309e-94 | 0.459117 | 0.923788 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` | 2.48512e-05 | 0.42802 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` | 0.0211013 | 0.379133 | 0.897923 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 6.22124e-10 | 0.918575 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 3.27771e-38 | 0.885586 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 3.73014e-12 | 0.0126171 | 0.449709 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 0.0731931 | 0.157156 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 1.15756e-09 | 0.265798 | 0.855697 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 0.00505077 | 0.175552 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 2.44931e-104 | 0.133157 | 0.772622 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.75902e-19 | 0.551264 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 7.44024e-06 | 0.386101 | 0.900301 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 2.67795e-47 | 0.161002 | 0.798079 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 1.42234e-33 | 0.522249 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 1.67771e-09 | 0.184566 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 0.00119158 | 0.108816 | 0.712491 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 1.48383e-63 | 0.148029 | 0.790108 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 6.4223e-24 | 0.274569 | 0.861093 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 0.0331011 | 0.18684 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 3.70133e-12 | 0.203961 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 2.15716e-13 | 0.673844 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 3.23592e-07 | 0.0189328 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 6.99658e-39 | 0.405833 | 0.909044 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 1.27319e-84 | 0.175533 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 3.81652e-11 | 0.0143965 | 0.478925 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 4.00734e-15 | 0.0724146 | 0.704281 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 5.72961e-13 | 0.249206 | 0.834591 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 1.82978e-12 | 0.367194 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 7.87343e-14 | 0.510398 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 1.37692e-35 | 0.22879 | 0.818303 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 8.24625e-25 | 0.431663 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 1.91878e-06 | 0.295419 | 0.86207 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 1.42162e-08 | 0.330248 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 2.01897e-31 | 0.237717 | 0.823754 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 3.41676e-55 | 0.157643 | 0.798079 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 1.33684e-05 | 0.413089 | 0.91071 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 1.58792e-22 | 0.680112 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 2.77436e-28 | 0.510738 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 2.54016e-11 | 0.790718 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 2.56792e-09 | 0.612377 | 0.963095 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 2.28783e-15 | 0.385052 | 0.900301 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 4.47799e-16 | 0.317726 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 0.380989 | 0.0969907 | 0.706295 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 7.59104e-07 | 0.886942 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 0.00184316 | 0.235312 | 0.821123 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 2.41114e-24 | 0.6642 | 0.981297 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 3.63837e-06 | 0.907849 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 2.80057e-15 | 0.520689 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 0.000710971 | 0.112207 | 0.712491 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 0.120927 | 0.887601 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 3.13164e-15 | 0.258499 | 0.838392 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 5.33443e-05 | 0.364649 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 1.17356e-07 | 0.6377 | 0.979115 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 1.12822e-26 | 0.299062 | 0.862612 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 4.91892e-10 | 0.0219804 | 0.555492 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 4.90943e-09 | 0.818264 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 1.16214e-47 | 0.181302 | 0.798079 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 0.0222985 | 0.802877 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 2.15829e-36 | 0.728178 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 7.54621e-12 | 0.197804 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 8.56747e-08 | 0.463593 | 0.927931 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 4.62553e-07 | 0.950421 | 0.99371 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 1.02137e-79 | 0.654763 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 1.34841e-14 | 0.579568 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 0.00219435 | 0.643685 | 0.979264 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 0.0189341 | 0.096645 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.93656e-57 | 0.615319 | 0.963095 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 5.20357e-62 | 0.196847 | 0.798079 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 3.22723e-07 | 0.874598 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 0.0690275 | 0.559774 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 8.16358e-120 | 0.802674 | 0.98402 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 2.92429e-21 | 0.450039 | 0.923569 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 2.47047e-20 | 0.887834 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 1.84075e-51 | 0.0716037 | 0.704281 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 0.146189 | 0.550892 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 7.13998e-76 | 0.00164506 | 0.233989 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 5.58769e-28 | 0.660641 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 4.825e-09 | 0.611935 | 0.963095 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 5.20936e-16 | 0.750969 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 0.749577 | 0.424682 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 1.43687e-06 | 0.142672 | 0.790108 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 0.0726226 | 0.127627 | 0.758168 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 7.8248e-43 | 0.379683 | 0.897923 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 4.55345e-44 | 0.602175 | 0.959219 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 0.621331 | 0.199094 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.0665745 | 0.481516 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 0.000105052 | 0.0566242 | 0.615783 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 1.20259e-16 | 0.946257 | 0.99371 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 8.66645e-08 | 0.119295 | 0.734914 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 2.6101e-34 | 0.221989 | 0.818303 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 3.33182e-06 | 0.143453 | 0.790108 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 1.44141e-16 | 0.676643 | 0.982018 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 1.28706e-66 | 0.213726 | 0.807951 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 9.30745e-09 | 0.803327 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 0.0355142 | 0.161105 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` | 1.70739e-16 | 0.621471 | 0.966088 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 1.97299e-06 | 0.898069 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` | 0.0151914 | 0.74161 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 0.00105488 | 0.89483 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` | 1.8994e-96 | 0.012566 | 0.449709 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` | 7.47194e-57 | 0.0990795 | 0.706295 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 0.0123747 | 0.112799 | 0.712491 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 8.1528e-41 | 0.0808234 | 0.704281 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 0.497683 | 0.825456 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 0.00666483 | 0.191429 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` | 3.36716e-111 | 0.74788 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 1.95822e-79 | 0.23314 | 0.821123 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 0.00612494 | 0.0119839 | 0.449709 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` | 7.49023e-29 | 0.0350606 | 0.555492 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` | 2.06395e-84 | 0.550507 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` | 1.87521e-07 | 0.847736 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 5.27799e-07 | 0.835435 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 0.799562 | 0.549062 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` | 1.02382e-10 | 0.436484 | 0.912868 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` | 0.339871 | 0.642879 | 0.979264 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 0.350004 | 0.944088 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 0.000115588 | 0.825482 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 5.88256e-10 | 0.288428 | 0.86207 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` | 2.17168e-16 | 0.575482 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` | 0.00160998 | 0.966293 | 0.995869 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` | 4.90808e-30 | 0.0348049 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 0.163235 | 0.181052 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 0.000587523 | 0.148811 | 0.790108 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` | 0.0941804 | 0.663492 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 1.30793e-09 | 0.402739 | 0.909044 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 0.509724 | 0.5591 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 5.59697e-05 | 0.433632 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` | 7.20212e-36 | 0.0293228 | 0.555492 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 3.16057e-15 | 0.165143 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 0.00210229 | 0.312121 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` | 1.09868e-70 | 0.0317201 | 0.555492 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` | 1.81322e-59 | 0.341437 | 0.877018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` | 3.93061e-18 | 0.210998 | 0.807951 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` | 5.65448e-62 | 0.291764 | 0.86207 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 0.290314 | 0.656763 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 8.89184e-27 | 0.84627 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 1.60502e-18 | 0.696416 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 4.77384e-29 | 0.362471 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 2.40119e-43 | 0.843423 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 5.24275e-08 | 0.0501719 | 0.583141 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` | 1.58687e-23 | 0.469222 | 0.930177 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` | 1.02402e-151 | 0.439055 | 0.912868 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_34_Momentum_L5` | 7.55376e-16 | 0.56502 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` | 3.38794e-19 | 0.77117 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 0.511118 | 0.493473 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 3.56734e-47 | 0.870456 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 5.82776e-54 | 0.503342 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 0.0244085 | 0.851582 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 2.03196e-59 | 0.171693 | 0.798079 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 5.99125e-144 | 0.196511 | 0.798079 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 0.836762 | 0.108295 | 0.712491 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 2.21529e-58 | 0.0211955 | 0.555492 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 1.49038e-25 | 0.944817 | 0.99371 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 1.68864e-18 | 0.227608 | 0.818303 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 3.84234e-12 | 0.40266 | 0.909044 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 2.0138e-06 | 0.517333 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 2.13321e-15 | 0.661024 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 9.47398e-83 | 0.959487 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 9.82098e-11 | 0.861311 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 8.8014e-07 | 0.12708 | 0.758168 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 1.91457e-05 | 0.762593 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 5.85678e-15 | 0.0426208 | 0.562588 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 1.83916e-43 | 0.40565 | 0.909044 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 0.167866 | 0.0976046 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 2.20584e-53 | 0.543306 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 0.00403425 | 0.414025 | 0.91071 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 1.22735e-06 | 0.165905 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 6.46557e-70 | 0.255029 | 0.838392 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 1.70335e-21 | 0.366201 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 0.000586277 | 0.181771 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 3.08188e-18 | 0.322864 | 0.873317 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 2.78399e-110 | 0.603597 | 0.959219 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 8.36878e-25 | 0.91051 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 2.5586e-63 | 0.737065 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 7.15139e-62 | 0.00155255 | 0.233989 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.000290367 | 0.584263 | 0.950981 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 2.5302e-83 | 0.928068 | 0.987261 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 1.50481e-19 | 0.181766 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 1.15558e-19 | 0.364507 | 0.886961 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` | 0.000451702 | 0.791289 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 2.59948e-13 | 0.294336 | 0.86207 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 3.46842e-05 | 0.282663 | 0.861093 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 1.31368e-22 | 0.890908 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 0.754395 | 0.838512 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` | 1.27787e-24 | 0.918394 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` | 3.08941e-110 | 0.20094 | 0.798079 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` | 0.301865 | 0.332667 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 1.12846e-08 | 0.31763 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 1.80283e-36 | 0.117377 | 0.732136 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` | 2.06263e-18 | 0.941998 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 7.63706e-37 | 0.430313 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` | 0.00306169 | 0.258742 | 0.838392 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` | 5.63508e-69 | 0.336067 | 0.873425 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` | 5.23902e-05 | 0.856743 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 2.37625e-38 | 0.85868 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` | 9.38435e-106 | 0.213091 | 0.807951 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` | 0.0109524 | 0.80769 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` | 3.89809e-34 | 0.992133 | 0.999432 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` | 4.95577e-70 | 0.332771 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 9.74894e-61 | 0.523959 | 0.948212 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 2.24146e-118 | 0.0989697 | 0.706295 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 2.12681e-126 | 0.176478 | 0.798079 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 7.1099e-98 | 0.19782 | 0.798079 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 4.46063e-87 | 0.664618 | 0.981297 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` | 2.31796e-60 | 0.457457 | 0.923788 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` | 1.9222e-70 | 0.958656 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` | 0.00576296 | 0.552735 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 9.26484e-44 | 0.845788 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 1.09409e-09 | 0.206317 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 5.10518e-08 | 0.794087 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 9.35133e-19 | 0.544112 | 0.948212 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 0.000156182 | 0.683383 | 0.982018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 6.74996e-05 | 0.817505 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 0.421911 | 0.50644 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 3.76543e-112 | 0.00942545 | 0.449709 | False | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 2.18978e-120 | 0.028604 | 0.555492 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 4.76211e-09 | 0.354941 | 0.886961 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 7.59616e-13 | 0.613361 | 0.963095 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 5.33706e-05 | 0.919282 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` | 0.594893 | 0.342723 | 0.877018 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 9.58787e-38 | 0.793561 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 0.000163797 | 0.436972 | 0.912868 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` | 5.93254e-26 | 0.369715 | 0.886961 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` | 0.993171 | 0.902051 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` | 2.5107e-06 | 0.8317 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` | 1.08683e-116 | 0.437455 | 0.912868 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` | 1.54132e-44 | 0.189133 | 0.798079 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` | 0.536461 | 0.104965 | 0.712491 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.0271643 | 0.797676 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` | 1.13713e-31 | 0.17262 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` | 0.0051864 | 0.563217 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` | 3.01908e-12 | 0.577382 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` | 1.45855e-28 | 0.574327 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` | 6.86964e-10 | 0.555549 | 0.948212 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 1.81943e-05 | 0.518863 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` | 0.447846 | 0.959165 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` | 0.0125748 | 0.293121 | 0.86207 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` | 1.25004e-20 | 0.722348 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` | 2.66225e-14 | 0.368264 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` | 0.00345779 | 0.205892 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` | 8.92192e-29 | 0.154854 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` | 0.300101 | 0.718337 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` | 5.10991e-20 | 0.0966637 | 0.706295 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` | 1.73559e-14 | 0.817053 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` | 3.44728e-100 | 0.726141 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` | 1.02657e-157 | 0.279791 | 0.861093 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` | 4.84028e-11 | 0.765077 | 0.98402 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` | 0.0248095 | 0.59536 | 0.952194 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` | 6.56516e-11 | 0.226637 | 0.818303 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` | 9.65893e-40 | 0.273902 | 0.861093 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` | 3.0084e-20 | 0.315344 | 0.873317 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` | 3.54926e-134 | 0.454522 | 0.923569 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` | 2.77023e-25 | 0.281084 | 0.861093 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` | 1.03536e-06 | 0.251504 | 0.836669 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` | 1.86777e-27 | 0.107113 | 0.712491 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` | 2.00003e-22 | 0.162219 | 0.798079 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` | 5.63429e-55 | 0.0115179 | 0.449709 | True | False | removed:p_value |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` | 6.23651e-81 | 0.999432 | 0.999432 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` | 0.198864 | 0.817141 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` | 1.21742e-24 | 0.918094 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` | 3.78611e-12 | 0.0509043 | 0.583141 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` | 3.20567e-09 | 0.57349 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` | 5.45425e-49 | 0.558298 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` | 2.44749e-26 | 0.576823 | 0.948212 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` | 5.589e-21 | 0.8275 | 0.98402 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` | 3.51301e-08 | 0.315747 | 0.873317 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` | 5.42121e-46 | 0.360867 | 0.886961 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` | 6.8406e-19 | 0.0389624 | 0.555492 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` | 0.00465092 | 0.5929 | 0.952194 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` | 0.00336406 | 0.388923 | 0.902664 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` | 1.35906e-24 | 0.961848 | 0.99371 | False | False | removed:icir |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` | 1.80091e-21 | 0.25628 | 0.838392 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` | 0.00107852 | 0.948197 | 0.99371 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` | 0.249479 | 0.591464 | 0.952194 | False | False | removed:ic_mean |
| `full_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` | 1.01314e-11 | 0.695852 | 0.98402 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 1.57717e-51 | 0.785716 | 0.929764 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 0.180501 | 0.815087 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 3.46951e-07 | 0.897025 | 0.953589 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 0.192681 | 0.593992 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 1.41903e-06 | 0.862208 | 0.943871 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` | 4.51837e-05 | 0.306317 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` | 1.51242e-11 | 0.198118 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` | 1.08959e-77 | 2.86658e-06 | 0.000356172 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` | 1.63129e-120 | 0.00164111 | 0.0479785 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 3.98868e-36 | 0.00310214 | 0.0811454 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 0.576934 | 0.00392505 | 0.0928928 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 0.00229082 | 0.724025 | 0.916135 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 1.76941e-34 | 0.79802 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 0.283337 | 0.263315 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 7.32999e-40 | 0.923971 | 0.958693 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 1.48522e-09 | 0.346383 | 0.740468 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 9.86451e-35 | 0.545072 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 1.5875e-39 | 0.599369 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 2.02002e-11 | 0.600422 | 0.863687 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 0.00975491 | 0.807908 | 0.938623 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 3.84937e-35 | 0.44549 | 0.77517 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 1.42068e-09 | 0.73331 | 0.916135 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 1.098e-74 | 0.0682541 | 0.477778 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 1.28064e-24 | 0.134483 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 1.07594e-09 | 0.546818 | 0.840279 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 0.387198 | 0.223335 | 0.675447 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 2.63851e-10 | 0.0415411 | 0.396506 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 1.52043e-12 | 0.0529591 | 0.434631 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.0389e-17 | 0.167648 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 0.00148326 | 0.814951 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 1.52043e-12 | 0.0529591 | 0.434631 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.747007 | 0.601614 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 1.02416e-43 | 0.452078 | 0.775611 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 7.17958e-21 | 0.318842 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 2.10126e-40 | 0.0232356 | 0.270845 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` | 6.3875e-11 | 0.22715 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_MOM_21` | 3.7927e-103 | 0.166958 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.0612538 | 0.249942 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 0.194165 | 0.596309 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 2.01372e-15 | 0.895887 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` | 5.86545e-05 | 0.645036 | 0.87115 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` | 9.47625e-18 | 0.218422 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` | 9.80707e-77 | 0.103375 | 0.604442 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` | 7.19556e-12 | 0.013161 | 0.197077 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 3.89415e-15 | 0.0570187 | 0.443986 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 1.5867e-59 | 0.543353 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` | 6.98804e-12 | 0.397894 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 1.20591e-53 | 1.32488e-05 | 0.00131693 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` | 3.9081e-58 | 2.46181e-06 | 0.000356172 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` | 2.04565e-11 | 0.556118 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` | 3.06264e-74 | 0.0392525 | 0.396506 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` | 2.63684e-18 | 0.841728 | 0.942205 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` | 1.38528e-12 | 0.446919 | 0.77517 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` | 0.619026 | 0.738482 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` | 8.55689e-19 | 0.409442 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` | 1.04396e-73 | 0.00100966 | 0.0334533 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 1.18015e-131 | 0.0864212 | 0.557134 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` | 3.80159e-96 | 0.000462602 | 0.0205246 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 4.21306e-23 | 9.07966e-05 | 0.00451259 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 3.18155e-35 | 4.52992e-05 | 0.00250152 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 0.00190869 | 0.45409 | 0.775611 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 8.30155e-70 | 0.053345 | 0.434631 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 1.64353e-11 | 0.282115 | 0.711731 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.00318028 | 0.892714 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 4.84658e-05 | 0.617536 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 6.51626e-13 | 0.94681 | 0.96824 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 0.0039016 | 0.347141 | 0.740468 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 2.58162e-19 | 0.872035 | 0.948362 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 0.717165 | 0.529688 | 0.83573 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` | 2.89816e-79 | 0.0370356 | 0.383472 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 8.25846e-132 | 0.0422833 | 0.396506 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` | 1.21804e-07 | 0.800859 | 0.938623 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` | 4.27517e-41 | 0.704055 | 0.904174 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` | 2.00445e-104 | 0.334687 | 0.736015 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` | 2.51624e-06 | 0.63494 | 0.867629 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` | 0.614705 | 0.187461 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 3.39262e-07 | 0.650365 | 0.873873 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` | 0.0329646 | 0.621606 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` | 3.97226e-53 | 0.419002 | 0.767264 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` | 1.91268e-64 | 0.5477 | 0.840279 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 1.6096e-72 | 0.627483 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` | 8.95629e-74 | 0.494909 | 0.803823 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` | 0.159372 | 0.551666 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` | 0.00331293 | 0.276835 | 0.707966 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` | 2.0913e-09 | 0.139024 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` | 1.08996e-54 | 0.0712606 | 0.491896 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` | 5.11769e-07 | 0.22643 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` | 5.18536e-45 | 0.220643 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` | 1.85255e-10 | 0.255184 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` | 0.934003 | 0.0159404 | 0.210563 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` | 1.22157e-33 | 0.524373 | 0.83263 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` | 1.03334e-08 | 0.228514 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` | 1.4132e-158 | 0.0176494 | 0.224917 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` | 3.36202e-42 | 0.165615 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` | 2.9508e-19 | 0.19085 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` | 1.73777e-09 | 0.254038 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` | 2.63078e-38 | 0.24395 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` | 0.000746289 | 0.433254 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` | 6.16326e-107 | 0.0112294 | 0.186034 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` | 3.77647e-32 | 0.753654 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` | 0.0566847 | 0.739088 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 1.79316e-05 | 0.252114 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 4.96312e-49 | 0.0515286 | 0.434631 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` | 1.26739e-12 | 0.201921 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` | 0.928949 | 0.296994 | 0.718121 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` | 0.407857 | 0.302724 | 0.72683 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` | 0.015616 | 0.26144 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` | 0.00918785 | 0.239416 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` | 0.00075434 | 0.0118702 | 0.190306 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` | 1.82356e-25 | 0.227049 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` | 4.17076e-09 | 0.457128 | 0.777667 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` | 0.110246 | 0.801953 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` | 4.67624e-14 | 0.805377 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` | 4.20891e-106 | 2.93387e-07 | 0.000145813 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` | 2.70193e-108 | 0.0571732 | 0.443986 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` | 0.000182821 | 0.656027 | 0.874779 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` | 3.5982e-120 | 0.989811 | 0.993811 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` | 1.24789e-64 | 0.412675 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` | 0.384995 | 0.297652 | 0.718121 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` | 8.71133e-16 | 0.205075 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_apen_55_Max_W8` | 4.0872e-35 | 0.590487 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` | 2.31137e-35 | 0.680535 | 0.885408 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` | 0.0362992 | 0.888813 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_perm_55_Min_W233` | 0.00835493 | 0.544769 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` | 5.9175e-11 | 0.492374 | 0.802328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 0.0858546 | 0.811398 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 2.71235e-37 | 0.0273476 | 0.308904 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 0.534984 | 0.465608 | 0.784431 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` | 0.384362 | 0.623774 | 0.863923 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` | 0.000735895 | 0.899462 | 0.953589 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 1.41139e-25 | 0.230558 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 6.14584e-11 | 0.225838 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 3.16445e-67 | 0.929422 | 0.960936 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 3.51452e-24 | 0.089516 | 0.557134 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 5.01271e-11 | 0.699051 | 0.902411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 0.0676965 | 0.656817 | 0.874779 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 4.67935e-10 | 0.0931786 | 0.564753 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 7.69714e-24 | 0.307674 | 0.727014 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 6.01851e-42 | 0.982571 | 0.993811 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 0.437192 | 0.432161 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 8.54873e-11 | 0.851366 | 0.942602 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 1.12525e-70 | 0.41354 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 1.97746e-15 | 0.724486 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 4.05257e-79 | 0.00451593 | 0.0935174 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 0.43937 | 0.290734 | 0.718121 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 7.87325e-105 | 0.0682135 | 0.477778 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.00969471 | 0.618155 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` | 0.48528 | 0.676668 | 0.882687 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` | 6.38302e-18 | 0.876523 | 0.951162 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` | 0.237819 | 0.735585 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` | 2.67936e-52 | 0.718203 | 0.914354 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` | 3.22793e-08 | 0.499207 | 0.805538 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 7.75129e-13 | 0.76422 | 0.919655 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` | 0.0125903 | 0.49042 | 0.801772 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` | 5.23076e-28 | 0.121295 | 0.641315 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 9.41404e-43 | 0.0207841 | 0.258242 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` | 0.287693 | 0.425769 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` | 3.87602e-46 | 0.267274 | 0.695473 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 0.574266 | 0.772283 | 0.922655 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` | 1.32351e-22 | 0.206076 | 0.675447 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 8.80628e-70 | 0.332155 | 0.733693 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 2.05947e-25 | 0.841198 | 0.942205 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` | 0.779727 | 0.779695 | 0.927054 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` | 0.224466 | 0.292746 | 0.718121 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.0154515 | 0.885039 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` | 1.33978e-11 | 0.197485 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 7.61211e-17 | 0.619109 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` | 0.0942126 | 0.453284 | 0.775611 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` | 2.13079e-34 | 0.119198 | 0.637002 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` | 4.26015e-32 | 0.666879 | 0.879148 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` | 0.68432 | 0.867147 | 0.945114 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` | 1.28201e-91 | 0.0234333 | 0.270845 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` | 7.39115e-58 | 0.458463 | 0.777667 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` | 7.15184e-18 | 0.509804 | 0.81733 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 4.0433e-37 | 0.176408 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` | 1.17416e-05 | 0.830395 | 0.942205 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 0.363885 | 0.526057 | 0.832644 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` | 1.32348e-33 | 0.231038 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` | 1.0033e-16 | 0.823015 | 0.941436 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` | 1.93823e-32 | 0.413646 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` | 2.06749e-58 | 0.171439 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` | 3.92343e-52 | 0.837269 | 0.942205 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` | 9.33967e-102 | 0.163367 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 1.066e-88 | 0.187524 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 1.67938e-82 | 2.35294e-05 | 0.00167059 | True | True | passed |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 1.01434e-27 | 0.390252 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 3.36428e-64 | 0.00053686 | 0.0205246 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 2.17981e-36 | 0.534597 | 0.840279 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 8.10891e-34 | 1.91122e-05 | 0.00158313 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.63614e-09 | 0.166037 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 0.27541 | 0.853462 | 0.942602 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 5.51535e-42 | 0.891065 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 2.02767e-29 | 0.257609 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 8.86334e-100 | 0.0496813 | 0.434631 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 1.41004e-60 | 3.43117e-05 | 0.00213162 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 1.37095e-15 | 0.33824 | 0.738238 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 9.80806e-12 | 0.00497379 | 0.098879 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 1.6644e-09 | 0.250418 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 3.79631e-75 | 0.00445116 | 0.0935174 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 9.16161e-146 | 0.108128 | 0.605918 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 0.448939 | 0.285329 | 0.716204 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 9.71971e-61 | 0.0490289 | 0.434631 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 2.49759e-12 | 0.728777 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 1.64394e-97 | 1.24344e-06 | 0.000308994 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 9.53404e-110 | 0.16393 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` | 1.0971e-22 | 0.644775 | 0.87115 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` | 9.26866e-41 | 0.432186 | 0.767719 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` | 0.000226969 | 0.204523 | 0.675447 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` | 1.22329e-27 | 0.85575 | 0.943033 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` | 6.72535e-119 | 0.0779923 | 0.518466 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` | 0.0738724 | 0.642629 | 0.87115 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 8.15542e-118 | 0.0434421 | 0.399828 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` | 1.58248e-13 | 0.620166 | 0.863923 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` | 3.10368e-48 | 0.291977 | 0.718121 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 1.81362e-115 | 0.0960307 | 0.575027 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` | 3.23727e-13 | 0.903764 | 0.953589 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 2.95822e-22 | 0.315677 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` | 0.322321 | 0.310863 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` | 2.86531e-06 | 0.344102 | 0.740468 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` | 2.15509e-50 | 0.260882 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` | 0.00164162 | 0.752828 | 0.916135 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` | 0.00543869 | 0.878811 | 0.951566 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` | 0.00139681 | 0.338669 | 0.738238 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` | 0.000666607 | 0.429281 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` | 0.00781151 | 0.917969 | 0.956458 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` | 3.52053e-68 | 0.223026 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` | 0.00282488 | 0.653167 | 0.874779 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 1.4571e-07 | 0.177879 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 9.16078e-84 | 0.288878 | 0.718121 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 9.5346e-10 | 0.261568 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 2.87563e-06 | 0.503083 | 0.809165 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 9.68143e-25 | 0.572413 | 0.851764 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 0.0135078 | 0.313281 | 0.727014 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 1.26436e-10 | 0.391583 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.86899e-47 | 0.606223 | 0.863923 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 1.27056e-08 | 0.815287 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 0.00130947 | 0.599554 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 0.0151848 | 0.390523 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 1.602e-09 | 0.22182 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 4.50742e-06 | 0.309379 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 0.00556742 | 0.439508 | 0.774593 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 1.01249e-07 | 0.544839 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 1.9129e-23 | 0.559622 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 0.00742539 | 0.635446 | 0.867629 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 0.0440441 | 0.783228 | 0.929032 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 1.58038e-25 | 0.243644 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 1.78224e-09 | 0.215299 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 0.0359487 | 0.683891 | 0.887451 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 0.69008 | 0.258966 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 0.369325 | 0.901692 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 1.67866e-16 | 0.325909 | 0.728403 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 1.64778e-28 | 0.708891 | 0.908038 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 3.92612e-21 | 0.141471 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 0.00159807 | 0.910871 | 0.95507 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 0.00796653 | 0.95557 | 0.975192 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 5.18665e-13 | 0.0134821 | 0.197077 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 1.44164e-05 | 0.999993 | 0.999993 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 1.58538e-10 | 0.627088 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 0.0104093 | 0.410583 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 3.20121e-32 | 0.936192 | 0.962331 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 1.20516e-07 | 0.719341 | 0.914354 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 7.01243e-20 | 0.414855 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 9.58348e-06 | 0.83239 | 0.942205 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 0.00289353 | 0.858895 | 0.943706 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 5.74859e-05 | 0.110943 | 0.605918 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 6.42711e-52 | 0.185888 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 0.00206122 | 0.137254 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 0.030403 | 0.387613 | 0.764352 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 2.71599e-84 | 0.3931 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 1.96498e-05 | 0.779648 | 0.927054 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 1.88921e-26 | 0.296059 | 0.718121 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 8.08735e-15 | 0.813524 | 0.938623 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 2.74709e-08 | 0.403089 | 0.764352 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 3.08729e-15 | 0.962016 | 0.977754 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 2.03891e-28 | 0.348672 | 0.740501 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 4.3126e-46 | 0.838095 | 0.942205 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 8.04048e-09 | 0.603017 | 0.863687 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 0.126234 | 0.629256 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 0.0609006 | 0.142832 | 0.675447 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 9.29706e-27 | 0.0151134 | 0.208648 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 0.0653979 | 0.412544 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 0.550851 | 0.836507 | 0.942205 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 0.614269 | 0.173444 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 0.0323149 | 0.310567 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 0.000109955 | 0.419911 | 0.767264 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 2.17871e-12 | 0.0669829 | 0.477778 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 0.000132931 | 0.847541 | 0.942602 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 6.19238e-25 | 0.570616 | 0.85164 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 1.97127e-23 | 0.0357221 | 0.379668 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 2.41546e-06 | 0.75244 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.11073e-06 | 0.895181 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 3.42424e-05 | 0.474703 | 0.787723 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 4.8258e-09 | 0.145974 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 2.32715e-30 | 0.00831193 | 0.148318 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 6.0981e-20 | 0.825887 | 0.941436 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 2.31188e-49 | 0.181582 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 0.357417 | 0.214054 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 0.000443873 | 0.40094 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 1.73716e-37 | 0.46838 | 0.785541 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 3.12925e-07 | 0.377096 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 2.98151e-05 | 0.470561 | 0.785541 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 4.93867e-18 | 0.0773913 | 0.518466 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 0.761439 | 0.860158 | 0.943706 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 8.13509e-10 | 0.539435 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 1.87723e-07 | 0.384665 | 0.764352 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 2.4793e-21 | 0.391913 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 1.4906e-23 | 0.13893 | 0.675447 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 0.000170611 | 0.378609 | 0.764352 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 3.33248e-06 | 0.760279 | 0.919364 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.658589 | 0.0416557 | 0.396506 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 7.53529e-16 | 0.483526 | 0.79311 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 4.8735e-05 | 0.408864 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 0.00290885 | 0.558624 | 0.840279 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 6.01545e-09 | 0.0896795 | 0.557134 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 8.13739e-13 | 0.824746 | 0.941436 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 8.47034e-15 | 0.193545 | 0.675447 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 2.5663e-12 | 0.620466 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.00159557 |  |  | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 0.129444 | 0.380526 | 0.764352 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` | 1.5235e-28 | 0.584081 | 0.858841 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 3.70253e-12 | 0.85286 | 0.942602 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` | 0.698981 | 0.454131 | 0.775611 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 6.78864e-38 | 0.240762 | 0.688835 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` | 9.41636e-18 | 0.185654 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` | 3.79797e-15 | 0.376877 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 2.2834e-12 | 0.628988 | 0.863923 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 1.47914e-06 | 0.356763 | 0.741888 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 0.292774 | 0.672348 | 0.879797 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 3.91931e-09 | 0.206058 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` | 2.41143e-25 | 0.191909 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 4.21072e-22 | 0.757847 | 0.918658 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 0.290397 | 0.442468 | 0.77517 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` | 8.29915e-06 | 0.800887 | 0.938623 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` | 6.22963e-21 | 0.22157 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` | 4.48729e-26 | 0.0160994 | 0.210563 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 2.21217e-35 | 0.000523061 | 0.0205246 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 0.0315118 | 0.355998 | 0.741888 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` | 1.526e-27 | 0.12403 | 0.648874 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` | 0.607536 | 0.422984 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 0.000199101 | 0.517095 | 0.826355 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 0.000325956 | 0.9346 | 0.962331 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 0.125738 | 0.164041 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` | 5.3657e-05 | 0.345851 | 0.740468 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` | 1.10925e-06 | 0.988106 | 0.993811 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` | 0.00834321 | 0.224148 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 7.4132e-10 | 0.223247 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 0.316034 | 0.845 | 0.942602 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` | 0.00120684 | 0.749711 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 3.34673e-14 | 0.110757 | 0.605918 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 0.251624 | 0.262217 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 9.41373e-27 | 0.206608 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` | 3.36066e-11 | 0.145157 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 0.00100635 | 0.662553 | 0.875768 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 5.16473e-18 | 0.056752 | 0.443986 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` | 2.40561e-66 | 0.00120837 | 0.037535 | True | True | passed |
| `long_BCHUSDT_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` | 9.94118e-31 | 0.577557 | 0.853593 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` | 8.25409e-86 | 0.136735 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` | 8.50937e-41 | 0.215916 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 7.90524e-61 | 0.613227 | 0.863923 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 3.14269e-40 | 0.40025 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 8.04252e-26 | 0.172686 | 0.675447 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.00137183 | 0.081304 | 0.531685 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 2.14462e-14 | 0.434062 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 6.86727e-06 | 0.319907 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` | 0.000425775 | 0.659989 | 0.874779 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` | 5.31831e-39 | 0.350136 | 0.740501 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` | 3.1191e-144 | 0.0677868 | 0.477778 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 0.000636269 | 0.551666 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 2.93769e-14 | 0.742603 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 1.79217e-76 | 0.0141285 | 0.200624 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 0.274635 | 0.731222 | 0.916135 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 9.67616e-63 | 0.145343 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 1.24276e-15 | 0.389958 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 0.71751 | 0.480015 | 0.792582 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 9.56577e-102 | 0.147467 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 0.000430445 | 0.905368 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 2.76185e-31 | 0.345834 | 0.740468 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 1.07785e-28 | 0.174788 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 0.000179091 | 0.0581743 | 0.44481 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 0.0468517 | 0.355978 | 0.741888 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 1.73849e-34 | 0.240745 | 0.688835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 1.15054e-93 | 0.279198 | 0.707966 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 7.69993e-14 | 0.175616 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 8.13198e-39 | 0.551948 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 4.36157e-22 | 0.143506 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 0.000922293 | 0.650569 | 0.873873 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 1.07084e-31 | 0.728796 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 0.000391444 | 0.56997 | 0.85164 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 0.251464 | 0.278717 | 0.707966 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 7.99024e-23 | 0.944749 | 0.968124 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 2.84375e-91 | 0.00835596 | 0.148318 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 5.40005e-93 | 0.0131903 | 0.197077 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 0.0149646 | 0.768065 | 0.922049 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 1.10347e-92 | 0.0093557 | 0.160337 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 0.0746597 | 0.255862 | 0.688835 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 4.60403e-139 | 0.0516114 | 0.434631 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 1.74723e-08 | 0.481904 | 0.793067 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 0.776743 | 0.985488 | 0.993811 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.0223158 | 0.578794 | 0.853593 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 4.40989e-171 | 0.162324 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 6.76533e-47 | 0.0598605 | 0.450768 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 7.1106e-08 | 0.594972 | 0.863687 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` | 1.70955e-150 | 0.160452 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 9.85762e-11 | 0.671996 | 0.879797 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 5.32224e-09 | 0.106946 | 0.605918 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 1.84925e-79 | 0.104961 | 0.605918 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 7.65345e-13 | 0.327141 | 0.728403 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` | 0.00103378 | 0.446755 | 0.77517 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` | 7.94051e-10 | 0.865174 | 0.945036 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` | 3.66057e-34 | 0.119169 | 0.637002 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 9.69469e-43 | 0.277951 | 0.707966 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 3.6391e-87 | 0.00648195 | 0.123905 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` | 3.32069e-118 | 0.100372 | 0.593869 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 4.24771e-24 | 0.375147 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` | 1.67791e-29 | 0.222542 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` | 1.07187e-24 | 0.975083 | 0.989013 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` | 3.04207e-11 | 0.917193 | 0.956458 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 0.00496034 | 0.216513 | 0.675447 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` | 1.33001e-43 | 0.144442 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` | 0.144779 | 0.75103 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` | 1.25716e-20 | 0.177884 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` | 9.04255e-49 | 0.637746 | 0.868384 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 0.00735149 | 0.425552 | 0.767719 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 1.05211e-29 | 0.0218566 | 0.264945 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 8.19452e-24 | 0.0359042 | 0.379668 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 4.95054e-18 | 0.0282221 | 0.311697 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 1.91516e-33 | 0.328294 | 0.728403 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` | 1.59782e-41 | 0.753922 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.000150653 | 0.93 | 0.960936 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` | 5.43022e-10 | 0.689344 | 0.892198 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 2.83016e-58 | 0.0782394 | 0.518466 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 2.31541e-15 | 0.959774 | 0.977474 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.0515489 | 0.294243 | 0.718121 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 0.89096 | 0.554129 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 1.15117e-103 | 0.00379925 | 0.0928928 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 1.44576e-20 | 0.322776 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 1.11688e-17 | 0.93716 | 0.962331 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 0.0412755 | 0.415241 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 7.1361e-16 | 0.186767 | 0.675447 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 0.00133183 | 0.461268 | 0.779762 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 0.135339 | 0.559508 | 0.840279 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 0.000221399 | 0.751349 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` | 0.00104044 | 0.411238 | 0.764352 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 0.00455979 | 0.11081 | 0.605918 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 0.245142 | 0.922341 | 0.958693 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` | 5.43545e-26 | 0.322994 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` | 9.48859e-27 | 0.191975 | 0.675447 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` | 1.04641e-22 | 0.753064 | 0.916135 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` | 9.96701e-21 | 0.471008 | 0.785541 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` | 2.82108e-52 | 0.900493 | 0.953589 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` | 0.00644708 | 0.912885 | 0.955166 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` | 1.1413e-36 | 0.218909 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` | 0.0228439 | 0.317664 | 0.727014 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` | 5.13076e-15 | 0.380259 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` | 9.00063e-35 | 0.0912521 | 0.559905 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` | 1.13984e-07 | 0.770365 | 0.922582 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` | 6.18013e-33 | 0.256127 | 0.688835 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 3.65147e-17 | 0.660044 | 0.874779 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` | 1.85308e-13 | 0.263337 | 0.688835 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` | 0.000142746 | 0.672682 | 0.879797 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` | 2.5354e-35 | 0.275708 | 0.707966 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` | 1.69609e-06 | 0.994587 | 0.996592 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` | 0.111453 | 0.321743 | 0.727014 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` | 0.535051 | 0.820727 | 0.941436 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` | 0.000188047 | 0.618127 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` | 0.540218 | 0.840595 | 0.942205 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` | 4.9921e-55 | 0.405788 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` | 3.24399e-65 | 0.152776 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` | 1.92776e-94 | 0.193746 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` | 1.1437e-08 | 0.907516 | 0.953589 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` | 0.545797 | 0.76242 | 0.919655 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` | 7.61072e-11 | 0.199072 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` | 1.80677e-64 | 0.404111 | 0.764352 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` | 3.73089e-38 | 0.204043 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` | 5.84991e-68 | 0.00258556 | 0.0713902 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` | 4.80867e-12 | 0.987523 | 0.993811 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` | 0.217591 | 0.578313 | 0.853593 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` | 1.64167e-105 | 0.0885779 | 0.557134 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` | 2.26151e-62 | 0.149747 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` | 3.01375e-67 | 0.0654724 | 0.477778 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` | 7.85554e-29 | 0.0409513 | 0.396506 | True | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` | 2.3901e-10 | 0.427307 | 0.767719 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` | 1.73037e-126 | 0.00420269 | 0.0935174 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` | 0.00256693 | 0.625752 | 0.863923 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` | 0.00130726 | 0.352139 | 0.741582 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` | 3.01771e-06 | 0.475487 | 0.787723 | False | False | removed:icir |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` | 2.24327e-121 | 0.000793658 | 0.0281749 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` | 4.99082e-18 | 0.714032 | 0.912273 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` | 0.136789 | 0.90754 | 0.953589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` | 6.44076e-09 | 0.358697 | 0.742802 | False | False | removed:p_value |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` | 1.86648e-16 | 0.520382 | 0.828942 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` | 0.00163894 | 0.815865 | 0.938623 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` | 1.56869e-43 | 0.447633 | 0.77517 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` | 7.44477e-43 | 0.210717 | 0.675447 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` | 0.0103312 | 0.851935 | 0.942602 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` | 1.23211e-05 | 0.701202 | 0.902844 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` | 1.2793e-33 | 0.32328 | 0.727014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` | 0.0297038 | 0.496891 | 0.804412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 1.57717e-51 | 0.785716 | 0.952442 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 0.180501 | 0.815087 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 3.46951e-07 | 0.897025 | 0.967673 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 0.192681 | 0.593992 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 1.41903e-06 | 0.862208 | 0.962961 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_APO_55-144-0_Range_W8` | 4.51837e-05 | 0.306317 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_APO_55-144-0_Std_W144` | 1.51242e-11 | 0.198118 | 0.674415 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_144_Kurt_W5` | 2.2185e-26 | 0.446648 | 0.818772 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_89_Momentum_L21` | 6.04479e-08 | 0.741952 | 0.934412 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_89_Slope_W5` | 1.08959e-77 | 2.86658e-06 | 0.000474896 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_8_Rank_W3` | 1.63129e-120 | 0.00164111 | 0.0407817 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 3.98868e-36 | 0.00310214 | 0.0670331 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 0.576934 | 0.00392505 | 0.0750288 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_55-233-34_Momentum_L55` | 0.841808 | 0.993987 | 0.995991 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_8-34-9_Lag_8` | 4.4324e-05 | 0.0409364 | 0.362324 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 0.00229082 | 0.724025 | 0.934235 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 1.76941e-34 | 0.79802 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_13-55-13_Mean_W89` | 5.02701e-12 | 0.350342 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 0.283337 | 0.263315 | 0.739364 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 7.32999e-40 | 0.923971 | 0.97291 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_5-21-5_Range_W8` | 3.67569e-65 | 0.226123 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 1.48522e-09 | 0.346383 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_13-55-13_DecayLinear_W13` | 1.2233e-52 | 0.164709 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_34-89-13_Std_W3` | 6.32466e-08 | 0.125612 | 0.612049 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 9.86451e-35 | 0.545072 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 1.5875e-39 | 0.599369 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 2.02002e-11 | 0.600422 | 0.885759 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_21-55-9_ZScore_W3` | 1.12114e-51 | 0.00833826 | 0.125846 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 0.00975491 | 0.807908 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 3.84937e-35 | 0.44549 | 0.818772 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_12-26-9_Mean_W34` | 1.33188e-54 | 0.179393 | 0.660431 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 1.42068e-09 | 0.73331 | 0.934412 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_21-55-9_Std_W144` | 2.11036e-21 | 0.123487 | 0.607655 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_21-89-13_Momentum_L233` | 7.57932e-23 | 0.947842 | 0.979371 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 1.098e-74 | 0.0682541 | 0.451343 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_55-233-34_ZScore_W21` | 1.62861e-08 | 0.70452 | 0.930413 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 1.28064e-24 | 0.134483 | 0.636397 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_21-89-13_Max_W34` | 1.38501e-05 | 0.564296 | 0.870979 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_8-21-5_TsArgmin_W5` | 1.23715e-57 | 0.244027 | 0.721914 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 1.07594e-09 | 0.546818 | 0.866456 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 0.387198 | 0.223335 | 0.701203 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_8_Mean_W55` | 2.07059e-63 | 0.176823 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_9_ZScore_W144` | 1.84169e-08 | 0.196941 | 0.674415 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 2.63851e-10 | 0.0415411 | 0.362324 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 1.52043e-12 | 0.0529591 | 0.401704 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.0389e-17 | 0.167648 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Rank_W3` | 5.87034e-68 | 0.000198591 | 0.008225 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 0.00148326 | 0.814951 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 1.52043e-12 | 0.0529591 | 0.401704 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.747007 | 0.601614 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 1.02416e-43 | 0.452078 | 0.820665 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 7.17958e-21 | 0.318842 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_TsRank_W5` | 2.16589e-52 | 0.000474176 | 0.015711 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 2.10126e-40 | 0.0232356 | 0.261525 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_8_Rank_W5` | 6.81113e-05 | 0.299078 | 0.770164 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_9_Std_W34` | 3.21109e-16 | 0.766102 | 0.942457 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MOM_13_Min_W144` | 6.3875e-11 | 0.22715 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MOM_21` | 3.7927e-103 | 0.166958 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_MOM_89_Rank_W89` | 8.86913e-34 | 0.81655 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_13-55-0_Lag_3` | 1.86295e-55 | 0.290014 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.0612538 | 0.249942 | 0.732103 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 0.194165 | 0.596309 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 2.01372e-15 | 0.895887 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_55-233-0_Kurt_W34` | 1.50605e-08 | 0.936841 | 0.974411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_12_Skew_W233` | 5.86545e-05 | 0.645036 | 0.89072 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_13_Range_W5` | 9.47625e-18 | 0.218422 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_89_Kurt_W13` | 9.80707e-77 | 0.103375 | 0.564588 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_8_Lag_1` | 7.19556e-12 | 0.013161 | 0.175546 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 3.89415e-15 | 0.0570187 | 0.414133 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_9_TsRank_W13` | 6.32853e-25 | 0.00039967 | 0.0152797 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 1.5867e-59 | 0.543353 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_34_Mean_W89` | 6.98804e-12 | 0.397894 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 1.20591e-53 | 1.32488e-05 | 0.00136229 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_8_34_Ratio` | 1.13275e-12 | 0.810834 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_9_Rank_W8` | 3.9081e-58 | 2.46181e-06 | 0.000474896 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_13_Rank_W144` | 2.04565e-11 | 0.556118 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_55_Rank_W3` | 3.06264e-74 | 0.0392525 | 0.362324 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_5_Skew_W13` | 2.63684e-18 | 0.841728 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_55_Range_W89` | 1.38528e-12 | 0.446919 | 0.818772 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_55_Std_W144` | 0.619026 | 0.738482 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_89_Range_W3` | 0.843356 | 0.352165 | 0.777894 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_89_Slope_W233` | 8.55689e-19 | 0.409442 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_14_Momentum_L55` | 1.04396e-73 | 0.00100966 | 0.0278777 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_34_Max_W21` | 6.5042e-84 | 0.278918 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 1.18015e-131 | 0.0864212 | 0.530263 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_8_Rank_W55` | 3.80159e-96 | 0.000462602 | 0.015711 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 4.21306e-23 | 9.07966e-05 | 0.00410235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 3.18155e-35 | 4.52992e-05 | 0.00250152 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 0.00190869 | 0.45409 | 0.820665 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 8.30155e-70 | 0.053345 | 0.401704 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastk_21-8-5-0_Range_W8` | 2.03773e-05 | 0.483187 | 0.825816 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 1.64353e-11 | 0.282115 | 0.766451 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_13_Lag_5` | 1.44034e-32 | 0.42537 | 0.807248 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.00318028 | 0.892714 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_55_Rank_W233` | 0.000167763 | 0.552503 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 4.84658e-05 | 0.617536 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 6.51626e-13 | 0.94681 | 0.979371 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 0.0039016 | 0.347141 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 2.58162e-19 | 0.872035 | 0.967414 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_34_Slope_W21` | 0.0437659 | 0.34461 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 0.717165 | 0.529688 | 0.86597 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_21_89_Ratio` | 2.89854e-38 | 0.318452 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_5_Lag_2` | 1.4138e-51 | 0.134751 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_5_Std_W8` | 2.89816e-79 | 0.0370356 | 0.353974 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_89_Slope_W13` | 1.33758e-70 | 0.714054 | 0.934235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 8.25846e-132 | 0.0422833 | 0.362324 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_STDDEV_89_Skew_W5` | 1.21804e-07 | 0.800859 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_TSF_55_Kurt_W13` | 4.27517e-41 | 0.704055 | 0.930413 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_TSF_89_Momentum_L8` | 2.00445e-104 | 0.334687 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_TSF_89_Range_W233` | 2.51624e-06 | 0.63494 | 0.889625 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Kurt_W13` | 1.51249e-35 | 0.72224 | 0.934235 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Log1p` | 0.614705 | 0.187461 | 0.665709 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Slope_W8` | 0.628427 | 0.801382 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 3.39262e-07 | 0.650365 | 0.893185 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_55_TsRank_W5` | 0.0329646 | 0.621606 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_89_TsRank_W13` | 3.97226e-53 | 0.419002 | 0.80523 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_apen_55_Max_W8` | 4.0872e-35 | 0.590487 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_fractal_dim_55_Kurt_W55` | 2.31137e-35 | 0.680535 | 0.91166 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_fractal_dim_55_Lag_21` | 1.91523e-16 | 0.0236793 | 0.261525 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_perm_21_Mean_W34` | 0.0362992 | 0.888813 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_perm_55_Min_W233` | 0.00835493 | 0.544769 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_shannon_close_return_55_Slope_W13` | 5.9175e-11 | 0.492374 | 0.835188 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 0.0858546 | 0.811398 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 2.71235e-37 | 0.0273476 | 0.295473 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 0.534984 | 0.465608 | 0.825816 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_shannon_volume_21_Max_W89` | 0.384362 | 0.623774 | 0.885759 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ent_12h_shannon_volume_55_Max_W233` | 0.000735895 | 0.899462 | 0.967673 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_144_Lag_8` | 0.000327619 | 0.475653 | 0.825816 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 1.41139e-25 | 0.230558 | 0.704454 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 6.14584e-11 | 0.225838 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 3.16445e-67 | 0.929422 | 0.974411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 3.51452e-24 | 0.089516 | 0.533175 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 5.01271e-11 | 0.699051 | 0.928953 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 0.0676965 | 0.656817 | 0.896808 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 4.67935e-10 | 0.0931786 | 0.538486 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 7.69714e-24 | 0.307674 | 0.77328 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_55_Std_W5` | 0.190596 | 0.418935 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 6.01851e-42 | 0.982571 | 0.991473 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_13_Slope_W8` | 8.87938e-10 | 0.112414 | 0.570099 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 0.437192 | 0.432161 | 0.810552 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_34_DecayLinear_W21` | 0.000225275 | 0.61627 | 0.885759 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 8.54873e-11 | 0.851366 | 0.961657 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 1.12525e-70 | 0.41354 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 1.97746e-15 | 0.724486 | 0.934235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_21_Range_W21` | 0.00257566 | 0.829906 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 4.05257e-79 | 0.00451593 | 0.0801577 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 0.43937 | 0.290734 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 7.87325e-105 | 0.0682135 | 0.451343 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_13_Lag_2` | 7.47921e-08 | 0.554909 | 0.866456 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.00969471 | 0.618155 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_233_Max_W144` | 0.48528 | 0.676668 | 0.90893 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_34_ZScore_W8` | 6.38302e-18 | 0.876523 | 0.967673 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_21_Slope_W89` | 0.237819 | 0.735585 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_233_Rank_W233` | 2.67936e-52 | 0.718203 | 0.934235 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_55_Slope_W233` | 3.22793e-08 | 0.499207 | 0.843511 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 7.75129e-13 | 0.76422 | 0.942457 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_8_Skew_W3` | 0.0125903 | 0.49042 | 0.834721 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 8.80628e-70 | 0.332155 | 0.777321 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 2.05947e-25 | 0.841198 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_14_Range_W233` | 0.779727 | 0.779695 | 0.949776 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_233_Rank_W144` | 0.00735417 | 0.95344 | 0.981076 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_13_Skew_W21` | 0.224466 | 0.292746 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.0154515 | 0.885039 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_144_Mean_W13` | 1.9674e-26 | 0.475537 | 0.825816 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_14_Lag_3` | 4.72889e-49 | 0.296094 | 0.766451 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_34_Mean_W34` | 1.33978e-11 | 0.197485 | 0.674415 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 7.61211e-17 | 0.619109 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_144_Skew_W34` | 0.0942126 | 0.453284 | 0.820665 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_14_Log1p` | 6.88294e-97 | 1.37052e-05 | 0.00136229 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_233_Min_W34` | 2.13079e-34 | 0.119198 | 0.592412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_34_Range_W3` | 4.26015e-32 | 0.666879 | 0.900649 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_34_Skew_W34` | 0.68432 | 0.867147 | 0.964143 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_5_Mean_W13` | 1.28201e-91 | 0.0234333 | 0.261525 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Kurt_W8` | 7.39115e-58 | 0.458463 | 0.825566 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Momentum_L233` | 4.80294e-07 | 0.800135 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Std_W89` | 7.15184e-18 | 0.509804 | 0.850243 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 4.0433e-37 | 0.176408 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_144_Mean_W34` | 1.17416e-05 | 0.830395 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 0.363885 | 0.526057 | 0.865729 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_21_Rank_W21` | 1.32348e-33 | 0.231038 | 0.704454 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_233_Skew_W13` | 1.0033e-16 | 0.823015 | 0.955299 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_34_Momentum_L21` | 1.93823e-32 | 0.413646 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_55_Lag_8` | 2.06749e-58 | 0.171439 | 0.659763 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_89_Range_W34` | 3.92343e-52 | 0.837269 | 0.955299 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_144` | 9.33967e-102 | 0.163367 | 0.659763 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_233_Mean_W5` | 1.65012e-42 | 0.295853 | 0.766451 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 1.066e-88 | 0.187524 | 0.665709 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 1.67938e-82 | 2.35294e-05 | 0.00167059 | True | True | passed |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 1.01434e-27 | 0.390252 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 3.36428e-64 | 0.00053686 | 0.0166762 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS_DI_8_89_Cross` | 1.84557e-71 | 0.145879 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 2.17981e-36 | 0.534597 | 0.866456 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 8.10891e-34 | 1.91122e-05 | 0.00158313 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.63614e-09 | 0.166037 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 0.27541 | 0.853462 | 0.961838 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 5.51535e-42 | 0.891065 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 2.02767e-29 | 0.257609 | 0.739364 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 8.86334e-100 | 0.0496813 | 0.398252 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 1.41004e-60 | 3.43117e-05 | 0.00213162 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 1.37095e-15 | 0.33824 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 9.80806e-12 | 0.00497379 | 0.0852405 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 1.6644e-09 | 0.250418 | 0.732103 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 3.79631e-75 | 0.00445116 | 0.0801577 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_8-3-0_Std_W21` | 0.237972 | 0.91833 | 0.971085 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_34-55-144_Kurt_W5` | 4.4171e-42 | 0.527833 | 0.865785 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 9.16161e-146 | 0.108128 | 0.565681 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 0.448939 | 0.285329 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-10-20_ZScore_W3` | 3.2548e-32 | 0.0561054 | 0.414133 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-13-26_Mean_W233` | 1.44826e-12 | 0.63036 | 0.887504 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 9.71971e-61 | 0.0490289 | 0.398252 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 2.49759e-12 | 0.728777 | 0.934235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 1.64394e-97 | 1.24344e-06 | 0.000474896 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_5_Momentum_L233` | 3.44332e-19 | 6.72562e-05 | 0.00334263 | True | True | passed |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 9.53404e-110 | 0.16393 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_144_Std_W144` | 1.55451e-08 | 0.263182 | 0.739364 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_14_Rank_W5` | 1.0971e-22 | 0.644775 | 0.89072 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Lag_13` | 9.26866e-41 | 0.432186 | 0.810552 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Range_W8` | 0.000226969 | 0.204523 | 0.691483 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Rank_W34` | 1.22329e-27 | 0.85575 | 0.962235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_233_Kurt_W13` | 9.15317e-33 | 0.964961 | 0.984775 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_233_Mean_W13` | 0.10474 | 0.985378 | 0.991473 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_5_20_Cross` | 6.72535e-119 | 0.0779923 | 0.492215 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_13_Lag_1` | 0.0738724 | 0.642629 | 0.89072 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 8.15542e-118 | 0.0434421 | 0.365945 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_55_Range_W21` | 1.58248e-13 | 0.620166 | 0.885759 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_89_Slope_W34` | 3.10368e-48 | 0.291977 | 0.766451 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 1.81362e-115 | 0.0960307 | 0.548589 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_21_DecayLinear_W21` | 1.10277e-69 | 0.817633 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_55_Min_W233` | 3.23727e-13 | 0.903764 | 0.967673 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 2.95822e-22 | 0.315677 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `hlcv_12h_volume_EOM_14_Slope_W3` | 0.322321 | 0.310863 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_21_Std_W233` | 0.0811331 | 0.794325 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_55_Max_W5` | 2.86531e-06 | 0.344102 | 0.777321 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_55_Rank_W8` | 2.53023e-121 | 0.0334635 | 0.339416 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_cs_spread_21_Rank_W8` | 2.15509e-50 | 0.260882 | 0.739364 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_kyle_lambda_21_Momentum_L13` | 0.00164162 | 0.752828 | 0.934412 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_13_Skew_W13` | 0.00543869 | 0.878811 | 0.967673 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_21_Std_W144` | 0.00139681 | 0.338669 | 0.777321 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_55_Kurt_W5` | 0.000666607 | 0.429281 | 0.810552 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_55_Skew_W21` | 0.00781151 | 0.917969 | 0.971085 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_roll_spread_55_Min_W34` | 3.52053e-68 | 0.223026 | 0.701203 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_vpin_30_Slope_W89` | 0.000743786 | 0.978537 | 0.991473 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `ms_12h_vpin_50_Kurt_W13` | 0.00282488 | 0.653167 | 0.894281 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 1.4571e-07 | 0.177879 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_cycle_HT-SINE-Sine_Min_W89` | 2.79919e-13 | 0.841894 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 9.16078e-84 | 0.288878 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 9.5346e-10 | 0.261568 | 0.739364 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 2.87563e-06 | 0.503083 | 0.844703 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 9.68143e-25 | 0.572413 | 0.872666 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 0.0135078 | 0.313281 | 0.77328 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 1.26436e-10 | 0.391583 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.86899e-47 | 0.606223 | 0.885759 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 1.27056e-08 | 0.815287 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 0.00130947 | 0.599554 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 0.0151848 | 0.390523 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 1.602e-09 | 0.22182 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_5_Slope_W233` | 9.93953e-25 | 0.0095268 | 0.135281 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_89_Slope_W5` | 0.0310164 | 0.345885 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 4.50742e-06 | 0.309379 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 0.00556742 | 0.439508 | 0.81811 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 1.01249e-07 | 0.544839 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_21-55-9_Sign` | 4.96739e-09 | 0.535468 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 1.9129e-23 | 0.559622 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_55-144-21_Skew_W233` | 4.34455e-11 | 0.327101 | 0.77328 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 0.00742539 | 0.635446 | 0.889625 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 0.0440441 | 0.783228 | 0.951747 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_55-233-34_Momentum_L13` | 0.0882067 | 0.483074 | 0.825816 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 1.58038e-25 | 0.243644 | 0.721914 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_12-26-9_Range_W21` | 1.66147e-25 | 0.88802 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 1.78224e-09 | 0.215299 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 0.0359487 | 0.683891 | 0.913693 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 0.69008 | 0.258966 | 0.739364 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 0.369325 | 0.901692 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_34-89-13_Mean_W3` | 3.49929e-51 | 0.00070904 | 0.020729 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 1.67866e-16 | 0.325909 | 0.77328 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-55-9_Kurt_W13` | 9.20659e-104 | 0.234552 | 0.710806 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-55-9_Lag_8` | 1.13647e-22 | 0.0138624 | 0.175546 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-89-13_DecayLinear_W13` | 2.35931e-20 | 0.0304994 | 0.315796 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 1.64778e-28 | 0.708891 | 0.932061 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_34-89-13_Slope_W89` | 0.00562665 | 0.715494 | 0.934235 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 3.92612e-21 | 0.141471 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 0.00159807 | 0.910871 | 0.971085 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 0.00796653 | 0.95557 | 0.981236 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 5.18665e-13 | 0.0134821 | 0.175546 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 1.44164e-05 | 0.999993 | 0.999993 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 1.58538e-10 | 0.627088 | 0.887504 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 0.0104093 | 0.410583 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Line_21_DecayLinear_W5` | 5.34818e-24 | 0.0449055 | 0.371967 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 3.20121e-32 | 0.936192 | 0.974411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 1.20516e-07 | 0.719341 | 0.934235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 7.01243e-20 | 0.414855 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 9.58348e-06 | 0.83239 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 0.00289353 | 0.858895 | 0.962835 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_21_Range_W34` | 1.54474e-17 | 0.304418 | 0.77328 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 5.74859e-05 | 0.110943 | 0.568439 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 6.42711e-52 | 0.185888 | 0.665709 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 0.00206122 | 0.137254 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 0.030403 | 0.387613 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 2.71599e-84 | 0.3931 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_34_Mean_W13` | 3.09656e-27 | 0.0026532 | 0.0603763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 1.96498e-05 | 0.779648 | 0.949776 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 1.88921e-26 | 0.296059 | 0.766451 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 8.08735e-15 | 0.813524 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_13_Rank_W55` | 0.00115964 | 0.62317 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 2.74709e-08 | 0.403089 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 3.08729e-15 | 0.962016 | 0.98379 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 2.03891e-28 | 0.348672 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 4.3126e-46 | 0.838095 | 0.955299 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 8.04048e-09 | 0.603017 | 0.885759 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_55_Kurt_W21` | 3.4066e-10 | 0.980962 | 0.991473 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_89_Max_W3` | 4.75478e-33 | 0.209242 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_34_Momentum_L233` | 1.04035e-13 | 0.514536 | 0.855266 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 0.126234 | 0.629256 | 0.887504 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 0.0609006 | 0.142832 | 0.636397 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_89_Mean_W13` | 0.000678769 | 0.101746 | 0.561865 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_14_Kurt_W34` | 6.0929e-12 | 0.0690182 | 0.451343 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 9.29706e-27 | 0.0151134 | 0.183203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_5_Momentum_L5` | 3.08033e-08 | 0.82739 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_7_Std_W13` | 1.13523e-08 | 0.4481 | 0.818772 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 0.0653979 | 0.412544 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-5-3-0_Range_W233` | 1.14117e-06 | 0.936581 | 0.974411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 0.550851 | 0.836507 | 0.955299 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 0.614269 | 0.173444 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 0.0323149 | 0.310567 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Kurt_W5` | 2.9363e-22 | 0.524978 | 0.865729 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 0.000109955 | 0.419911 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_55-8-5-0_Skew_W233` | 2.97486e-09 | 0.973691 | 0.991035 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 2.17871e-12 | 0.0669829 | 0.451343 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 0.000132931 | 0.847541 | 0.959517 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 6.19238e-25 | 0.570616 | 0.872604 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 1.97127e-23 | 0.0357221 | 0.34989 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_5_Kurt_W34` | 0.0722993 | 0.666463 | 0.900649 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 2.41546e-06 | 0.75244 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.11073e-06 | 0.895181 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 3.42424e-05 | 0.474703 | 0.825816 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 4.8258e-09 | 0.145974 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 2.32715e-30 | 0.00831193 | 0.125846 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 6.0981e-20 | 0.825887 | 0.955299 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 2.31188e-49 | 0.181582 | 0.663574 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 0.357417 | 0.214054 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 0.000443873 | 0.40094 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 1.73716e-37 | 0.46838 | 0.825816 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Kurt_W21` | 5.88678e-36 | 0.993171 | 0.995991 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 3.12925e-07 | 0.377096 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 2.98151e-05 | 0.470561 | 0.825816 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 4.93867e-18 | 0.0773913 | 0.492215 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 0.761439 | 0.860158 | 0.962835 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 8.13509e-10 | 0.539435 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 1.87723e-07 | 0.384665 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 2.4793e-21 | 0.391913 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_13_Slope_W8` | 6.7599e-22 | 0.500675 | 0.843511 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 1.4906e-23 | 0.13893 | 0.636397 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_5_Rank_W34` | 2.52092e-08 | 0.157788 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 0.000170611 | 0.378609 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 3.33248e-06 | 0.760279 | 0.939947 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.658589 | 0.0416557 | 0.362324 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 7.53529e-16 | 0.483526 | 0.825816 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 4.8735e-05 | 0.408864 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 0.00290885 | 0.558624 | 0.866456 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 6.01545e-09 | 0.0896795 | 0.533175 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 8.13739e-13 | 0.824746 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 8.47034e-15 | 0.193545 | 0.674415 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_14_Momentum_L21` | 3.30158e-07 | 0.64519 | 0.89072 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 2.5663e-12 | 0.620466 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.00159557 |  |  | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 0.129444 | 0.380526 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 0.00100635 | 0.662553 | 0.899696 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_cvar_5pct_100_Range_W34` | 0.0025875 | 0.753293 | 0.934412 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_jb_100_Slope_W13` | 2.40561e-66 | 0.00120837 | 0.0316085 | True | True | passed |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_mdd_55_Min_W8` | 0.178572 | 0.949946 | 0.979509 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_rsj_13_Range_W21` | 0.00122435 | 0.46219 | 0.825816 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_rsj_21_Max_W21` | 9.94118e-31 | 0.577557 | 0.877014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_rv_up_21_Mean_W89` | 1.52351e-08 | 0.506414 | 0.847433 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_ud_vol_ratio_21_Max_W13` | 8.25409e-86 | 0.136735 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `tr_12h_ud_vol_ratio_21_Std_W34` | 8.50937e-41 | 0.215916 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 7.90524e-61 | 0.613227 | 0.885759 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 3.14269e-40 | 0.40025 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 8.04252e-26 | 0.172686 | 0.659763 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_13-34-0_Mean_W55` | 0.0280996 | 0.580987 | 0.877661 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.00137183 | 0.081304 | 0.505101 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 2.14462e-14 | 0.434062 | 0.811011 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 6.86727e-06 | 0.319907 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_14_Max_W144` | 0.000425775 | 0.659989 | 0.89867 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_14_Rank_W13` | 5.31831e-39 | 0.350136 | 0.777321 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_233_Max_W55` | 4.19042e-06 | 0.900094 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_34_Momentum_L5` | 5.05613e-05 | 0.397364 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_8_Momentum_L3` | 3.1191e-144 | 0.0677868 | 0.451343 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 0.000636269 | 0.551666 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 2.93769e-14 | 0.742603 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 1.79217e-76 | 0.0141285 | 0.175546 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_21-89-13_Slope_W13` | 1.37661e-109 | 0.00360343 | 0.0746211 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 0.274635 | 0.731222 | 0.934235 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 9.67616e-63 | 0.145343 | 0.636397 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_5-21-5_Min_W144` | 0.000256595 | 0.372893 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 1.24276e-15 | 0.389958 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 0.71751 | 0.480015 | 0.825816 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 9.56577e-102 | 0.147467 | 0.637312 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 0.000430445 | 0.905368 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 2.76185e-31 | 0.345834 | 0.777321 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 1.07785e-28 | 0.174788 | 0.659763 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 0.000179091 | 0.0581743 | 0.414133 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 0.0468517 | 0.355978 | 0.782837 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 1.73849e-34 | 0.240745 | 0.720786 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_21-55-9_TsArgmax_W21` | 3.85418e-13 | 0.89157 | 0.967673 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 1.15054e-93 | 0.279198 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 7.69993e-14 | 0.175616 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_34-89-13_ZScore_W3` | 1.03543e-46 | 0.239088 | 0.720162 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 8.13198e-39 | 0.551948 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_13-55-13_Skew_W13` | 1.30883e-70 | 0.090114 | 0.533175 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 4.36157e-22 | 0.143506 | 0.636397 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 0.000922293 | 0.650569 | 0.893185 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 1.07084e-31 | 0.728796 | 0.934235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_5-21-5_Range_W21` | 9.28417e-20 | 0.56665 | 0.871905 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 0.000391444 | 0.56997 | 0.872604 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 0.251464 | 0.278717 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 7.99024e-23 | 0.944749 | 0.979371 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_34-89-13_Kurt_W5` | 1.10628e-12 | 0.81628 | 0.955299 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 2.84375e-91 | 0.00835596 | 0.125846 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 5.40005e-93 | 0.0131903 | 0.175546 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 0.0149646 | 0.768065 | 0.942539 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 1.10347e-92 | 0.0093557 | 0.135281 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 0.0746597 | 0.255862 | 0.739364 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 4.60403e-139 | 0.0516114 | 0.401704 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 1.74723e-08 | 0.481904 | 0.825816 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 0.776743 | 0.985488 | 0.991473 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_Log1p` | 3.05128e-133 | 0.421247 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.0223158 | 0.578794 | 0.877014 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 4.40989e-171 | 0.162324 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 6.76533e-47 | 0.0598605 | 0.419024 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 7.1106e-08 | 0.594972 | 0.885759 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_MOM_21_Slope_W21` | 1.70955e-150 | 0.160452 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 9.85762e-11 | 0.671996 | 0.9051 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 5.32224e-09 | 0.106946 | 0.565681 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 1.84925e-79 | 0.104961 | 0.565681 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 7.65345e-13 | 0.327141 | 0.77328 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_144_Lag_34` | 0.00103378 | 0.446755 | 0.818772 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_233_Mean_W8` | 5.16924e-67 | 0.404625 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_89_Min_W13` | 7.94051e-10 | 0.865174 | 0.964107 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR100_55_Range_W13` | 3.66057e-34 | 0.119169 | 0.592412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 9.69469e-43 | 0.277951 | 0.766451 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 3.6391e-87 | 0.00648195 | 0.107384 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_21_Range_W3` | 3.32069e-118 | 0.100372 | 0.560505 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 4.24771e-24 | 0.375147 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_89_Std_W5` | 1.25234e-42 | 0.0997843 | 0.560505 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_8_Min_W55` | 1.67791e-29 | 0.222542 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_21_ZScore_W8` | 1.07187e-24 | 0.975083 | 0.991035 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_34_Momentum_L13` | 1.24222e-10 | 0.0583286 | 0.414133 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_5_Slope_W55` | 3.04207e-11 | 0.917193 | 0.971085 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_89_Skew_W55` | 0.00239486 | 0.519426 | 0.860516 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 0.00496034 | 0.216513 | 0.701203 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_9_Momentum_L21` | 1.33001e-43 | 0.144442 | 0.636397 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_13_Kurt_W21` | 0.144779 | 0.75103 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_55_Max_W13` | 1.25716e-20 | 0.177884 | 0.659763 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_6_Min_W13` | 9.04255e-49 | 0.637746 | 0.890337 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 0.00735149 | 0.425552 | 0.807248 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Lag_21` | 3.27599e-24 | 0.0417303 | 0.362324 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 1.05211e-29 | 0.0218566 | 0.258636 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_55-8-5-0_Lag_34` | 1.04304e-111 | 0.150733 | 0.645811 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 8.19452e-24 | 0.0359042 | 0.34989 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 4.95054e-18 | 0.0282221 | 0.298433 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_34_Lag_8` | 2.87304e-20 | 0.705766 | 0.930413 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 1.91516e-33 | 0.328294 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Max_W233` | 1.59782e-41 | 0.753922 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.000150653 | 0.93 | 0.974411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Range_W144` | 0.345218 | 0.48332 | 0.825816 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_89_Min_W5` | 5.43022e-10 | 0.689344 | 0.918509 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 2.83016e-58 | 0.0782394 | 0.492215 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 2.31541e-15 | 0.959774 | 0.983521 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_55_Max_W144` | 0.121875 | 0.606515 | 0.885759 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.0515489 | 0.294243 | 0.766451 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 0.89096 | 0.554129 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_21_Slope_W5` | 1.6698e-35 | 0.00267259 | 0.0603763 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W8` | 2.64883e-83 | 0.410314 | 0.80523 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 1.15117e-103 | 0.00379925 | 0.0750288 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 1.44576e-20 | 0.322776 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 1.11688e-17 | 0.93716 | 0.974411 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 0.0412755 | 0.415241 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 7.1361e-16 | 0.186767 | 0.665709 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 0.00133183 | 0.461268 | 0.825816 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 0.135339 | 0.559508 | 0.866456 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 0.000221399 | 0.751349 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_5_Rank_W34` | 1.83928e-70 | 0.107124 | 0.565681 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_144_Std_W34` | 0.00104044 | 0.411238 | 0.80523 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 0.00455979 | 0.11081 | 0.568439 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_34_Range_W21` | 5.53201e-10 | 0.729532 | 0.934235 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 0.245142 | 0.922341 | 0.97291 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_13_Range_W89` | 5.43545e-26 | 0.322994 | 0.77328 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_144_Kurt_W89` | 9.48859e-27 | 0.191975 | 0.674415 | True | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_34_Kurt_W5` | 1.04641e-22 | 0.753064 | 0.934412 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_34_Lag_5` | 9.96701e-21 | 0.471008 | 0.825816 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_89_Momentum_L13` | 5.71783e-61 | 0.195184 | 0.674415 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_13_Kurt_W8` | 2.82108e-52 | 0.900493 | 0.967673 | False | False | removed:p_value |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_20_Mean_W21` | 0.00644708 | 0.912885 | 0.971085 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_21_Kurt_W144` | 1.1413e-36 | 0.218909 | 0.701203 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_34_Kurt_W8` | 0.0228439 | 0.317664 | 0.77328 | False | False | removed:icir |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_55_Min_W144` | 5.13076e-15 | 0.380259 | 0.80523 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_55_Slope_W3` | 9.00063e-35 | 0.0912521 | 0.533557 | False | False | removed:ic_mean |
| `long_BCHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_89_Mean_W34` | 1.13984e-07 | 0.770365 | 0.943033 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close-volume_1h_volume_OBV_Momentum_L233` | 0 | 0.734751 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 0.0333141 | 0.928355 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 4.08197e-48 | 0.916421 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_CMO_89_Slope_W5` | 3.07693e-204 | 0.0113349 | 0.154977 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_CMO_8_Rank_W3` | 7.4567e-59 | 0.264945 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 3.69692e-269 | 0.00205975 | 0.0513908 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 1.03396e-38 | 0.0206331 | 0.223824 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 2.13227e-20 | 0.964274 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 1.30232e-178 | 0.961256 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 0.484687 | 0.381675 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 0.000180808 | 0.842257 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 4.2559e-21 | 0.627067 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 0.0282986 | 0.825828 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 0.290805 | 0.872427 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 4.11448e-39 | 0.178078 | 0.821514 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 0.0117041 | 0.112762 | 0.676476 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 1.0528e-36 | 0.544087 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 6.03799e-68 | 0.67307 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 0.000424497 | 0.914072 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 9.6447e-310 | 0.010796 | 0.15392 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 7.61388e-09 | 0.832211 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MOM_13_Min_W144` | 3.5e-22 | 0.254699 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_MOM_21` | 0 | 0.137822 | 0.743734 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 0.000164032 | 0.50314 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCP_89_Kurt_W13` | 1.26177e-24 | 0.0446895 | 0.391229 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 1.14211e-197 | 0.25701 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.40176e-77 | 0.00759561 | 0.12634 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR_5_Skew_W13` | 1.63741e-10 | 0.779656 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_55_Range_W89` | 2.3175e-12 | 0.879548 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_55_Std_W144` | 0.0581229 | 0.903508 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_89_Slope_W233` | 0.997143 | 0.33476 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_RSI_8_Rank_W55` | 0 | 0.0100737 | 0.153668 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 1.14596e-94 | 0.00171866 | 0.0451375 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.61124e-262 | 0.000192411 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 2.42568e-08 | 0.295452 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.00174787 | 0.657415 | 0.980108 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 0.0138498 | 0.859166 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 1.7934e-223 | 0.0160099 | 0.199724 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 1.89961e-85 | 0.118037 | 0.677016 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG_5_Std_W8` | 6.89378e-12 | 0.27641 | 0.966158 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 1.5231e-10 | 0.131045 | 0.718589 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_55_Kurt_W13` | 4.22718e-27 | 0.486371 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_89_Momentum_L8` | 4.24439e-153 | 0.43959 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_89_Range_W233` | 1.28927e-24 | 0.687452 | 0.980163 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_144_Log1p` | 4.58645e-34 | 0.438943 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 5.5842e-18 | 0.0232119 | 0.236383 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_55_TsRank_W5` | 0.190705 | 0.731802 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 9.16964e-13 | 0.355377 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_DEMA_13_Slope_W55` | 6.70297e-08 | 0.68485 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_EMA_21_Mean_W34` | 0.109376 | 0.383944 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_EMA_55_ZScore_W8` | 0 | 0.0387038 | 0.355074 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_KAMA_8_Lag_5` | 9.4304e-16 | 0.477378 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_MA_21_Rank_W13` | 1.42349e-118 | 0.701671 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 8.7842e-06 | 0.426724 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 6.48908e-15 | 0.196015 | 0.843203 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_20_Kurt_W233` | 0.000134874 | 0.919415 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_55_Mean_W34` | 0.373667 | 0.476616 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_55_Mean_W55` | 0.00548372 | 0.414807 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_89_Min_W55` | 0.593313 | 0.390465 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_TEMA_13_Slope_W144` | 2.71983e-11 | 0.520575 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_TEMA_8_Rank_W3` | 1.96911e-86 | 0.0196226 | 0.217593 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_12h_trend_TRIMA_34_Std_W8` | 1.15606e-27 | 0.996604 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_13_Std_W8` | 2.42365e-35 | 0.00264512 | 0.0628531 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_8_Lag_13` | 2.38175e-155 | 0.0175274 | 0.208242 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_8_ZScore_W13` | 2.48137e-83 | 0.742267 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Hist_8-34-9_Rank_W144` | 2.03211e-47 | 0.465306 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_21-89-13_Min_W144` | 2.8562e-138 | 0.536929 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_34-144-21_Log1p` | 0 | 0.00336292 | 0.0729609 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_55-144-21_Max_W34` | 3.62676e-229 | 0.106946 | 0.658842 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_8-21-5_Mean_W34` | 0 | 0.00129363 | 0.0358623 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Signal_13-55-13_DecayLinear_W21` | 0 | 0.000423718 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Signal_34-89-13_Kurt_W34` | 1.72163e-19 | 0.638858 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_12-26-9_TsRank_W21` | 0.000897624 | 0.320804 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_55-144-21_Max_W34` | 7.62519e-67 | 0.00114953 | 0.0358511 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_8-34-9_Range_W5` | 0.000169541 | 0.760328 | 0.98803 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Line_34-89-13_Mean_W21` | 3.60904e-167 | 0.000795072 | 0.0264494 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Signal_12-26-9_Rank_W34` | 4.7833e-40 | 0.772194 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Signal_8-21-5_Slope_W144` | 1.28303e-160 | 0.000672277 | 0.0258051 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Line_13_Range_W3` | 6.55048e-25 | 0.219317 | 0.897043 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_13_DecayLinear_W5` | 0 | 0.000507166 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_3_Slope_W8` | 4.06993e-22 | 0.839526 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_9_Max_W144` | 1.64985e-155 | 0.746585 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MOM_144_Min_W144` | 1.51248e-107 | 0.569372 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_MOM_21_Momentum_L8` | 1.23482e-115 | 0.646653 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_21-55-0_Min_W34` | 0 | 0.000732266 | 0.0261 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_34-89-0_Std_W21` | 9.62489e-50 | 0.936808 | 0.991927 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_55-144-0_Range_W5` | 0.000127847 | 0.977015 | 0.998188 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_233_Sign` | 1.13259e-289 | 0.387666 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_55_ZScore_W5` | 0.0410301 | 0.241612 | 0.920339 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_9_Range_W55` | 3.31405e-10 | 0.96147 | 0.998188 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_13_144_Cross` | 2.51863e-275 | 0.014482 | 0.185295 | True | False | removed:p_value |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_13_Slope_W13` | 0.152998 | 0.284691 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_144_Slope_W34` | 8.80212e-295 | 0.00126746 | 0.0358623 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_233_Range_W5` | 0.00207093 | 0.478578 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR_12_Std_W233` | 0.121616 | 0.929698 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_14_55_Cross` | 2.39924e-308 | 0.326359 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_233_Slope_W89` | 0 | 0.00039439 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_9_Momentum_L55` | 2.64198e-112 | 0.834185 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_STOCHRSI-fastd_21-5-3-0_Kurt_W21` | 1.50169e-06 | 0.510773 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_momentum_TRIX_89_ZScore_W233` | 4.39733e-157 | 0.15692 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-INTERCEPT_55_TsRank_W21` | 1.57057e-06 | 0.046688 | 0.39487 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_10_Momentum_L21` | 1.54037e-11 | 0.435911 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_144_Mean_W13` | 1.89694e-191 | 0.00585399 | 0.116261 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_144_Std_W55` | 2.50994e-12 | 0.753183 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_89_Lag_2` | 0 | 0.00065173 | 0.0258051 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_8_Momentum_L5` | 0.00083979 | 0.462366 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_10_Max_W144` | 5.09735e-118 | 0.227692 | 0.916277 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_10_Range_W13` | 0.328081 | 0.647535 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_8_Mean_W55` | 0 | 0.12769 | 0.715923 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_STDDEV_5_Skew_W144` | 1.21511e-11 | 0.148454 | 0.779773 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_TSF_13_Range_W144` | 1.05567e-17 | 0.429123 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_VAR_34_Momentum_L233` | 1.30536e-24 | 0.586033 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_statistics_VAR_89_Std_W3` | 8.51051e-19 | 0.738114 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_BBANDS-Lower_13_Kurt_W144` | 0.000138741 | 0.584399 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_BBANDS-Upper_13_Max_W89` | 6.80909e-197 | 0.159591 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_DEMA_21_Momentum_L8` | 6.49159e-282 | 0.141753 | 0.752495 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_EMA_100_Rank_W144` | 0 | 0.00295547 | 0.0670354 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_KAMA_5_TsArgmax_W21` | 0 | 0.0669188 | 0.488946 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_KAMA_8_ZScore_W34` | 3.80297e-306 | 0.0368397 | 0.34685 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_55_ZScore_W34` | 0 | 0.0412179 | 0.367281 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_5_Std_W21` | 0.0118289 | 0.304761 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_89_Skew_W13` | 2.68259e-114 | 0.608674 | 0.979769 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_MA_55_DecayLinear_W13` | 6.05965e-33 | 0.788134 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_MIDPOINT_21_Std_W89` | 2.40224e-12 | 0.577768 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_MIDPOINT_55_Rank_W144` | 0 | 0.000117792 | 0.0222626 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_SMA_200_Max_W5` | 4.6281e-10 | 0.276875 | 0.966158 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_T3_8_Log1p` | 4.72367e-15 | 0.488141 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_TEMA_55_Skew_W5` | 1.93411e-46 | 0.481511 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_21_ZScore_W233` | 0 | 0.0072894 | 0.125428 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_233_Range_W13` | 1.97648e-05 | 0.995149 | 0.998188 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_34_TsRank_W5` | 6.95522e-149 | 0.0223315 | 0.232155 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_12h_perm_21_Mean_W34` | 2.15584e-07 | 0.678783 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 1.53205e-12 | 0.827523 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 5.19471e-35 | 0.103995 | 0.654754 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_12h_shannon_volume_21_Max_W89` | 4.15453e-05 | 0.841052 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_1h_apen_55_Momentum_L21` | 6.17756e-35 | 0.303372 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_1h_hurst_55_Min_W144` | 1.1028e-06 | 0.716933 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ent_1h_shannon_close_return_21_ZScore_W3` | 3.41066e-06 | 0.459712 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 3.21743e-05 | 0.876557 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 8.29175e-57 | 0.167931 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.00340378 | 0.982293 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 1.07579e-85 | 0.52528 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 1.92102e-19 | 0.102752 | 0.654754 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 4.96355e-140 | 0.279769 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.168437 | 0.657403 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_statistics_BETA_34_ZScore_W8` | 1.05175e-57 | 0.324388 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_21_Slope_W89` | 1.20263e-07 | 0.980964 | 0.998188 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 0.000455171 | 0.460869 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_8_Skew_W3` | 0.00179168 | 0.85231 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 8.7141e-135 | 0.0335837 | 0.322274 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 1.55819e-118 | 0.104971 | 0.654754 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroondown_233_Slope_W233` | 0.000183569 | 0.575254 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroondown_34_ZScore_W8` | 0.000205747 | 0.639217 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroonup_89_DecayLinear_W13` | 1.03334e-158 | 0.00820364 | 0.132052 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROONOSC_144_Std_W13` | 0.644542 | 0.54547 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_momentum_MINUS-DM_21_Max_W13` | 0 | 0.0863837 | 0.582506 | True | False | removed:p_value |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_momentum_PLUS-DM_8_Max_W144` | 5.27844e-145 | 0.589028 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_13_ZScore_W13` | 8.28673e-07 | 0.459073 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_21_Range_W21` | 6.51529e-182 | 0.00435996 | 0.0906509 | False | False | removed:p_value |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_5_21_Cross` | 1.67236e-07 | 0.948813 | 0.992728 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_statistics_CORREL_89_Lag_8` | 9.86916e-08 | 0.856869 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_statistics_CORREL_8_Mean_W55` | 4.88098e-112 | 0.172348 | 0.810296 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_trend_MIDPRICE_144_Min_W5` | 4.11731e-178 | 0.290045 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hl_1h_trend_SAR_0.02-0.2_Kurt_W144` | 4.95779e-42 | 0.364778 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 3.87861e-12 | 0.458339 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 0.0961973 | 0.940434 | 0.991927 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_14_Range_W233` | 2.92584e-28 | 0.93296 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADX_34_Mean_W34` | 0.433601 | 0.50731 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 7.5889e-30 | 0.757604 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_34_Range_W3` | 4.0282e-69 | 0.179449 | 0.821514 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_34_Skew_W34` | 8.19143e-56 | 0.830246 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_5_Mean_W13` | 2.02896e-210 | 0.0275765 | 0.275213 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_13_Std_W89` | 7.73986e-35 | 0.674642 | 0.980163 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 0.0348528 | 0.195788 | 0.843203 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_144_Mean_W34` | 0.162737 | 0.984654 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_34_Momentum_L21` | 0.755464 | 0.863613 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_55_Lag_8` | 0.255822 | 0.321031 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_MINUS-DI_144` | 0 | 0.216987 | 0.895632 | True | False | removed:p_value |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 1.18532e-12 | 0.519993 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 2.50814e-131 | 0.0212453 | 0.225562 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 5.75337e-142 | 0.172779 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 0 | 0.000286871 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 1.43283e-237 | 0.0644101 | 0.486641 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 0 | 0.0104703 | 0.153668 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 1.32945e-07 | 0.420159 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 4.55446e-10 | 0.826118 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 1.22499e-237 | 0.00605771 | 0.116261 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_14_Rank_W5` | 0.0904771 | 0.835689 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_21_Lag_13` | 0.0405539 | 0.32883 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_5_20_Cross` | 0.786601 | 0.225028 | 0.91292 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_NATR_13_Lag_1` | 7.82414e-19 | 0.746919 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ADX_144_Rank_W21` | 1.99525e-09 | 0.299896 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ADX_89_Max_W3` | 3.44758e-05 | 0.548042 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_13_Range_W5` | 3.70999e-68 | 0.247152 | 0.927286 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_34_ZScore_W34` | 7.49788e-66 | 0.89201 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_55_Rank_W8` | 9.63862e-20 | 0.584961 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_DX_144_Std_W144` | 0.00158401 | 0.692762 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_DX_55_Rank_W8` | 3.19106e-11 | 0.054504 | 0.438669 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_MINUS-DI_21_Momentum_L144` | 0 | 0.00042397 | 0.0230069 | True | True | passed |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_PLUS-DI_144_Max_W5` | 0 | 0.0391365 | 0.355074 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_PLUS-DI_21_Min_W8` | 0 | 0.0181358 | 0.20952 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowd_13-3-0-3-0_Range_W55` | 0.000328471 | 0.727102 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowd_34-5-0-5-0_Mean_W34` | 2.49284e-281 | 0.000464276 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_21-3-0-3-0_TsRank_W21` | 6.2685e-30 | 0.525168 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_21-5-0-5-0_Lag_21` | 5.03909e-77 | 0.0652474 | 0.486641 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_34-5-0-3-0_Lag_3` | 0 | 0.0184747 | 0.20952 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_55-5-0-5-0_Skew_W233` | 1.04235e-103 | 0.0118018 | 0.154977 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_21-5-0_Lag_21` | 6.01564e-77 | 0.0653406 | 0.486641 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_5-3-0_Slope_W89` | 3.48199e-235 | 0.607573 | 0.979769 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_5-3-0_ZScore_W21` | 1.06355e-77 | 0.922097 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastk_21-5-0_Mean_W55` | 0 | 0.000133844 | 0.0222626 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ULTOSC_5-10-20_Slope_W3` | 1.76528e-06 | 0.509705 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_WILLR_21_Skew_W34` | 1.48266e-65 | 0.0510133 | 0.417306 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlc_1h_volatility_ATR_233_Skew_W55` | 1.13164e-27 | 0.633126 | 0.980108 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `hlcv_12h_momentum_MFI_55_Min_W233` | 1.96531e-13 | 0.920347 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlcv_1h_momentum_MFI_89_Rank_W3` | 1.48252e-129 | 0.530948 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `hlcv_1h_volume_ForceIndex_Rank_W3` | 0.511928 | 0.512434 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_12h_amihud_illiq_55_Max_W5` | 1.62279e-25 | 0.379321 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_12h_cs_spread_21_Rank_W8` | 6.25593e-43 | 0.275299 | 0.966158 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_12h_kyle_lambda_21_Momentum_L13` | 0.0120934 | 0.920012 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_12h_ofi_zscore_13_Skew_W13` | 0.14338 | 0.752605 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_12h_roll_spread_55_Min_W34` | 0.377428 | 0.405192 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_12h_vpin_50_Kurt_W13` | 1.8385e-11 | 0.17263 | 0.810296 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `ms_1h_kyle_lambda_21_ZScore_W144` | 0.706265 | 0.173751 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 2.80365e-15 | 0.788845 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 2.43058e-31 | 0.441971 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 0.0282682 | 0.307026 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 0.450022 | 0.808711 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.41465e-07 | 0.784569 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 2.90144e-07 | 0.621581 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 1.8996e-08 | 0.931051 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 5.90286e-23 | 0.438482 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 2.52605e-07 | 0.745158 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 2.09649e-29 | 0.718607 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 3.86859e-36 | 0.757589 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 0.54132 | 0.393633 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 0.00320495 | 0.404785 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 4.55607e-19 | 0.614142 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 3.25421e-38 | 0.997843 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 0.000261745 | 0.87256 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 2.18153e-16 | 0.450662 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 2.61549e-09 | 0.68261 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 1.03779e-12 | 0.908997 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 3.41969e-06 | 0.700007 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 1.96931e-17 | 0.533984 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 8.7416e-16 | 0.472006 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 0.155275 | 0.360301 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 0.647749 | 0.516666 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 1.35101e-47 | 0.467383 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 8.32046e-11 | 0.790942 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 4.31759e-11 | 0.673718 | 0.980163 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 0.00015626 | 0.646264 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 2.04026e-15 | 0.246649 | 0.927286 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 3.21648e-11 | 0.622725 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 1.14344e-08 | 0.76385 | 0.98826 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 1.99773e-66 | 0.124079 | 0.703584 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 0.267372 | 0.715851 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 1.00438e-10 | 0.26353 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 0.483409 | 0.973087 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 1.82932e-05 | 0.399361 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 1.48346e-49 | 0.358119 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 9.03564e-25 | 0.296243 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 0.389157 | 0.818267 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 8.00506e-12 | 0.526378 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 0.0104828 | 0.675774 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 6.35289e-06 | 0.469506 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 5.19765e-08 | 0.4728 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 2.14492e-31 | 0.265059 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 0.522183 | 0.988252 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 0.000383049 | 0.664229 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.41594 | 0.688963 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 2.25766e-06 | 0.814698 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 3.01374e-17 | 0.186886 | 0.832417 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 3.06625e-11 | 0.524981 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 1.06182e-25 | 0.560476 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 0.0167415 | 0.578939 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 0.00348753 | 0.645249 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 0.0137489 | 0.860691 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 1.38164e-14 | 0.407718 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 1.74027e-37 | 0.457441 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 3.16268e-12 | 0.303137 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 1.46338e-05 | 0.291917 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 6.74454e-31 | 0.783237 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 4.58151e-13 | 0.560787 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 0.58556 | 0.118029 | 0.677016 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 3.10223e-20 | 0.563778 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 3.8314e-06 | 0.711243 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 0.257683 | 0.74505 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 0.231704 | 0.375863 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 2.9326e-119 | 0.213825 | 0.895632 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 0.00235318 | 0.857901 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 3.82459e-187 | 0.00714778 | 0.125428 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 2.46194e-39 | 0.88009 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 7.22897e-92 | 0.184813 | 0.830827 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_cycle_HT-PHASOR-InPhase_Kurt_W34` | 2.50657e-21 | 0.400329 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_APO_5-13-0_Mean_W34` | 7.68627e-40 | 0.720238 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_APO_55-233-0_Range_W233` | 2.62211e-54 | 0.741355 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_CMO_55_Slope_W5` | 1.7269e-19 | 0.159758 | 0.810296 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_13-34-9_Min_W5` | 1.43394e-134 | 0.541144 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_13-34-9_Momentum_L8` | 0.000107529 | 0.385234 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_21-55-9_Momentum_L144` | 3.43558e-07 | 0.750263 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_21-55-9_TsArgmax_W13` | 4.9523e-247 | 0.188503 | 0.832417 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_5-21-5_Skew_W8` | 0.473095 | 0.931271 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_55-233-34_Min_W5` | 3.77197e-122 | 0.416356 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Signal_12-26-9_Std_W144` | 8.54006e-10 | 0.995266 | 0.998188 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Hist_13-34-9_TsRank_W13` | 0.00587063 | 0.418636 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Hist_21-89-13_Range_W5` | 3.72444e-21 | 0.0694926 | 0.488946 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Line_13-34-9_Std_W13` | 0.413519 | 0.881537 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Line_55-144-21_Slope_W8` | 1.83932e-88 | 0.811576 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Signal_21-89-13_Rank_W144` | 0.0400257 | 0.662379 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Signal_34-89-13_Range_W233` | 0.155577 | 0.665845 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Hist_3_Std_W3` | 6.83467e-22 | 0.764466 | 0.98826 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Line_13_Mean_W8` | 7.32484e-137 | 0.308932 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Line_5_Momentum_L3` | 2.01378e-60 | 0.16368 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MOM_13_Mean_W233` | 7.73027e-48 | 0.565103 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MOM_34_Momentum_L55` | 2.14935e-12 | 0.0837368 | 0.572393 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_21-55-0_Clip` | 6.9057e-23 | 0.619755 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_8-34-0_Mean_W3` | 9.67623e-161 | 0.311629 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_8-34-0_Rank_W34` | 1.7918e-139 | 0.481592 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_13_Kurt_W144` | 8.38503e-08 | 0.840362 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_21_Mean_W13` | 1.98358e-47 | 0.969887 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_8_Lag_21` | 3.39248e-33 | 0.561993 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCR100_233_Skew_W3` | 4.11098e-27 | 0.6356 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROC_55_Min_W144` | 1.05837e-29 | 0.257508 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_233_Mean_W89` | 1.86705e-37 | 0.536689 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_34_Rank_W5` | 8.83463e-12 | 0.925219 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_7_Std_W3` | 1.02886e-15 | 0.619194 | 0.980108 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_7_TsArgmax_W13` | 3.95431e-15 | 0.129655 | 0.718589 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_8_ZScore_W5` | 0.0021998 | 0.588015 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_STOCHRSI-fastk_14-5-3-0_TsArgmax_W5` | 7.04538e-11 | 0.95095 | 0.992728 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_TRIX_55_Min_W5` | 6.07069e-34 | 0.497343 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_TRIX_8_Skew_W5` | 7.6977e-05 | 0.791258 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_233_Kurt_W89` | 2.72943e-143 | 0.0613291 | 0.478176 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_89_Kurt_W5` | 1.0357e-22 | 0.0103372 | 0.153668 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_89_Rank_W5` | 6.24543e-48 | 0.0603942 | 0.478176 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-SLOPE_21_Kurt_W34` | 0.813601 | 0.405483 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_55_Min_W3` | 1.36066e-36 | 0.645791 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_55_Slope_W8` | 1.89798e-35 | 0.559271 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_8_Lag_13` | 3.74355e-30 | 0.820329 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_STDDEV_89_Clip` | 2.72138e-06 | 0.355757 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_STDDEV_8_Lag_34` | 0.000652098 | 0.828883 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_VAR_13_Mean_W89` | 0.0126411 | 0.907663 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_VAR_89_Mean_W5` | 1.54527e-05 | 0.998188 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_BBANDS-Lower_20_Std_W89` | 1.20392e-06 | 0.802708 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_BBANDS-Middle_21_Max_W233` | 0.0135139 | 0.338673 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_EMA_144_Std_W55` | 0.00117298 | 0.931438 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_EMA_55_ZScore_W89` | 1.89424e-131 | 0.996395 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_KAMA_21_Lag_3` | 4.98375e-84 | 0.444402 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_KAMA_34_Skew_W55` | 0.0311325 | 0.660144 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MA_5_Rank_W13` | 2.27734e-08 | 0.164126 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MIDPOINT_13_Mean_W233` | 5.32389e-32 | 0.432926 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MIDPOINT_89_Mean_W233` | 3.07927e-17 | 0.419166 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_10_Max_W21` | 1.01535e-09 | 0.821501 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_13_Range_W13` | 0.0187456 | 0.904326 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_144_ZScore_W8` | 0.632691 | 0.207945 | 0.886879 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_50_ZScore_W8` | 9.84555e-14 | 0.183026 | 0.830271 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_5_Lag_34` | 8.47255e-57 | 0.217177 | 0.895632 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_5_Skew_W144` | 0.224021 | 0.283127 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TEMA_13_Kurt_W55` | 5.45951e-11 | 0.909708 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TEMA_55_Distance` | 6.97012e-07 | 0.114017 | 0.676476 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TRIMA_55_Momentum_L3` | 3.16336e-26 | 0.479743 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TRIMA_5_Momentum_L21` | 9.63698e-74 | 0.43403 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_WMA_89_Min_W233` | 7.97057e-73 | 0.83546 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 1.65697e-09 | 0.717003 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 6.66488e-103 | 0.0458335 | 0.394326 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `taker_1h_ratio_trend_SMA_8_50_Ratio` | 2.63771e-114 | 0.872436 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `tr_12h_rsj_21_Max_W21` | 0.00234587 | 0.867293 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `tr_12h_ud_vol_ratio_21_Max_W13` | 7.0785e-91 | 0.625224 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `tr_1h_cvar_5pct_55_TsArgmin_W21` | 1.8659e-143 | 8.52461e-05 | 0.0222626 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `tr_1h_gpr_100_Lag_2` | 0 | 0.000336879 | 0.0230069 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `tr_1h_gpr_55_Kurt_W5` | 1.2528e-28 | 0.0115571 | 0.154977 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `tr_1h_rsj_21_Rank_W13` | 1.49671e-12 | 0.474337 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 1.9523e-120 | 0.0305187 | 0.298604 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 9.96433e-07 | 0.942231 | 0.991927 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 0.73665 | 0.478546 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 3.0522e-43 | 0.696206 | 0.980163 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 0.0269232 | 0.434369 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_CMO_14_Max_W144` | 2.28475e-73 | 0.55964 | 0.968954 | False | False | removed:p_value |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_CMO_14_Rank_W13` | 3.00946e-10 | 0.802687 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 3.37405e-09 | 0.545397 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 3.87482e-08 | 0.814037 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 3.66541e-18 | 0.87411 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 1.67074e-08 | 0.875588 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 3.51161e-20 | 0.882128 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 0.0595066 | 0.70136 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 3.77876e-09 | 0.473286 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 5.10964e-12 | 0.696787 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 0.401017 | 0.542885 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 4.424e-06 | 0.138612 | 0.743734 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 0.205336 | 0.240617 | 0.920339 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 0.322713 | 0.687648 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 2.30641e-06 | 0.821621 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 3.13998e-31 | 0.260415 | 0.944745 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCP_89_Min_W13` | 6.3523e-59 | 0.740013 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR100_55_Range_W13` | 2.50364e-15 | 0.234376 | 0.920339 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 3.95556e-40 | 0.653003 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 2.47836e-13 | 0.650084 | 0.980108 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 0.0673383 | 0.563557 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROC_5_Slope_W55` | 0.0443137 | 0.596992 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_RSI_13_Kurt_W21` | 1.66249e-96 | 0.4788 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_RSI_6_Min_W13` | 1.52309e-11 | 0.341078 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 2.98516e-26 | 0.194674 | 0.843203 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 1.40548e-57 | 0.0761668 | 0.527878 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_5_Max_W233` | 1.6219e-52 | 0.914516 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.741723 | 0.703203 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_89_Min_W5` | 0.127115 | 0.753954 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.0506254 | 0.389884 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 1.91061e-16 | 0.550936 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_13_Range_W89` | 9.3206e-28 | 0.354753 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_144_Kurt_W89` | 1.10283e-05 | 0.868201 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_34_Kurt_W5` | 3.88429e-14 | 0.0994203 | 0.651558 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_34_Lag_5` | 0.528431 | 0.580584 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_13_Kurt_W8` | 8.88156e-23 | 0.736352 | 0.987061 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.023261 | 0.570929 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_34_Kurt_W8` | 4.01545e-26 | 0.616606 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 9.54144e-14 | 0.401481 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_233_Lag_2` | 0.571651 | 0.967717 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_233_Min_W144` | 0.00158334 | 0.41759 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_89_Std_W233` | 1.49293e-25 | 0.521324 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_8_Mean_W34` | 7.00958e-07 | 0.948143 | 0.992728 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_13_Rank_W144` | 0.00104065 | 0.543018 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_200_Slope_W144` | 0.264078 | 0.816198 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_21_Range_W13` | 1.44014e-53 | 0.92811 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_KAMA_8_Lag_21` | 1.82025e-12 | 0.754629 | 0.987061 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_MAVP_55_Range_W5` | 0.000104406 | 0.591346 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_MA_233_Mean_W89` | 0.589316 | 0.398772 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_MIDPOINT_8_Abs` | 0.014556 | 0.914046 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_SMA_50_ZScore_W233` | 2.67625e-16 | 0.922846 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_T3_21_Min_W55` | 0.161345 | 0.989513 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_T3_8_Std_W5` | 2.74924e-73 | 0.858015 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_TRIMA_55_Skew_W34` | 0.128837 | 0.794926 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_12h_trend_WMA_89_Max_W233` | 0.00494641 | 0.651818 | 0.980108 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_CMO_34_Max_W8` | 5.90718e-86 | 0.0492471 | 0.409571 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Hist_55-233-34_Kurt_W8` | 2.20498e-21 | 0.859694 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Hist_55-233-34_Min_W89` | 0.00246748 | 0.827934 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Line_21-89-13_Rank_W13` | 0.0062224 | 0.240959 | 0.920339 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Line_55-233-34_Range_W233` | 1.89387e-82 | 0.545065 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_21-55-9_Lag_2` | 3.69701e-36 | 0.318471 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_21-89-13_TsArgmin_W5` | 4.09311e-37 | 0.0695694 | 0.488946 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_55-233-34_Skew_W13` | 6.71337e-07 | 0.241082 | 0.920339 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_34-144-21_TsArgmin_W13` | 2.69452e-05 | 0.9823 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_8-21-5_Min_W21` | 2.00361e-06 | 0.909582 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_8-34-9_Kurt_W8` | 0.445144 | 0.596383 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Line_34-144-21_Slope_W3` | 1.12622e-15 | 0.456086 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Line_55-144-21_Min_W13` | 5.18606e-06 | 0.974577 | 0.998188 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Signal_34-144-21_ZScore_W144` | 1.10963e-25 | 0.231056 | 0.920339 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_13_Lag_5` | 0.000967322 | 0.351924 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_21_Mean_W89` | 1.16674e-41 | 0.0166769 | 0.20297 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_8_Std_W5` | 7.01007e-59 | 0.214304 | 0.895632 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_8_Std_W55` | 0.246799 | 0.686117 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_9_Max_W21` | 1.26412e-27 | 0.93011 | 0.990526 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_9_Max_W233` | 5.20635e-23 | 0.56063 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_144_Std_W13` | 0.292653 | 0.36428 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_21_Clip` | 0.0227783 | 0.0691681 | 0.488946 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_21_Min_W55` | 8.2018e-91 | 0.100541 | 0.651558 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_34_ZScore_W55` | 0.00480636 | 0.361175 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_PPO_34-89-0_Kurt_W5` | 0.0304764 | 0.32554 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCP_21_TsArgmax_W5` | 3.38775e-25 | 0.59397 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCR100_8_Lag_2` | 4.93215e-119 | 0.297744 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCR100_8_Slope_W233` | 2.51528e-09 | 0.530812 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROC_34_ZScore_W55` | 0.000458795 | 0.844511 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_14_Skew_W5` | 2.89442e-06 | 0.950573 | 0.992728 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_233_Rank_W21` | 5.24146e-15 | 0.598072 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_34_Kurt_W34` | 0.0560163 | 0.361554 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_34_Rank_W34` | 2.26904e-11 | 0.693106 | 0.980163 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_8_Lag_1` | 1.32343e-13 | 0.238521 | 0.920339 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_9_TsArgmax_W13` | 3.2916e-54 | 0.448357 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_STOCHRSI-fastd_9-5-3-0_Mean_W89` | 1.26616e-05 | 0.414402 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_momentum_STOCHRSI-fastk_21-8-5-0_Std_W21` | 0.358058 | 0.641339 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_statistics_LINEARREG-SLOPE_89_Mean_W21` | 6.91896e-14 | 0.406659 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_statistics_LINEARREG-SLOPE_8_Slope_W34` | 0.634899 | 0.317122 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_statistics_STDDEV_55_Std_W8` | 0.0382133 | 0.355914 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_statistics_TSF_5_Skew_W144` | 0.468111 | 0.787607 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_statistics_VAR_55_ZScore_W55` | 4.47936e-79 | 0.0063335 | 0.117052 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_statistics_VAR_8_Std_W3` | 9.98192e-06 | 0.549163 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_144_Max_W55` | 0.0911898 | 0.57471 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_21_Mean_W3` | 1.58376e-24 | 0.940565 | 0.991927 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_55_Range_W55` | 9.34572e-11 | 0.65858 | 0.980108 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_89_Max_W13` | 0.92112 | 0.542798 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_89_Mean_W55` | 0.392988 | 0.479688 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Upper_55_Momentum_L3` | 2.64487e-49 | 0.171088 | 0.810296 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Upper_55_ZScore_W5` | 3.31396e-56 | 0.110618 | 0.673153 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_13_Max_W34` | 5.02921e-36 | 0.562434 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_34_Momentum_L34` | 2.95703e-50 | 0.510629 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_5_Std_W89` | 0.000185589 | 0.59765 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_EMA_13_Max_W144` | 0.0247479 | 0.926172 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_HT-TRENDLINE_Lag_13` | 0.513399 | 0.34595 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_KAMA_233_Range_W144` | 2.96137e-10 | 0.623612 | 0.980108 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_KAMA_5_55_Ratio` | 1.88499e-56 | 0.348066 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_MAVP_233_Momentum_L144` | 2.0001e-10 | 0.542537 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_MA_13_Max_W144` | 0.573985 | 0.835063 | 0.990526 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_MA_89_Range_W3` | 2.08036e-11 | 0.982486 | 0.998188 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_50_Rank_W13` | 5.01791e-09 | 0.115231 | 0.676476 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_55_Max_W144` | 0.0245066 | 0.591863 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_5_TsArgmin_W13` | 4.26718e-66 | 0.0983389 | 0.651558 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_T3_5_21_Cross` | 5.94086e-21 | 0.290377 | 0.968954 | False | False | removed:icir |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_TEMA_5_Momentum_L144` | 3.58925e-06 | 0.164545 | 0.810296 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_TRIMA_144_Mean_W13` | 0.954806 | 0.512611 | 0.968954 | False | False | removed:ic_mean |
| `long_BCHUSDT_1h_4a8a0b37` | `volume_1h_trend_WMA_55_Max_W3` | 1.17485e-05 | 0.911464 | 0.990526 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 1.04516e-24 | 0.039238 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 8.84817e-35 | 0.490417 | 0.758984 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 0.129139 | 0.255909 | 0.558225 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 2.56002e-54 | 0.544174 | 0.792273 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 2.97231e-31 | 0.204084 | 0.50817 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` | 3.95308e-28 | 0.884757 | 0.943488 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` | 1.12174e-07 | 0.912271 | 0.960662 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` | 5.5119e-18 | 0.50438 | 0.768138 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` | 5.41088e-09 | 0.692651 | 0.879487 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 0.485764 | 0.455189 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 4.03073e-09 | 0.0363251 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 1.35431e-56 | 0.0757143 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 2.55459e-29 | 0.130177 | 0.438029 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 5.06203e-31 | 0.276565 | 0.569339 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 3.91112e-64 | 0.425383 | 0.729715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 8.02389e-28 | 0.00840158 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 3.66124e-93 | 0.0944855 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.000260418 | 0.11542 | 0.42264 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 3.56054e-34 | 0.835182 | 0.934711 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 1.07165e-63 | 0.15573 | 0.463578 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 4.31677e-18 | 0.102392 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 1.73706e-09 | 0.00992355 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 0.0337953 | 0.17069 | 0.477487 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 0.445815 | 0.160727 | 0.467031 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 1.70185e-78 | 0.306199 | 0.607519 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 6.87731e-35 | 0.545568 | 0.792273 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 5.0488e-13 | 0.104225 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 3.48613e-14 | 0.869065 | 0.934761 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.28852e-20 | 0.0564249 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 3.43619e-40 | 0.609014 | 0.842469 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 3.48613e-14 | 0.869065 | 0.934761 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.408349 | 0.608745 | 0.842469 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 2.32896e-59 | 0.249259 | 0.552235 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 5.48472e-13 | 0.0237629 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 0.00392406 | 0.266578 | 0.567008 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` | 4.35294e-23 | 0.185881 | 0.492976 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_MOM_21` | 9.3022e-101 | 0.548635 | 0.792273 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.000846601 | 0.530112 | 0.788047 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 3.44201e-34 | 0.201604 | 0.50817 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 0.00656996 | 0.0472729 | 0.336313 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` | 5.48622e-08 | 0.143198 | 0.453715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` | 7.51669e-19 | 0.490384 | 0.758984 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` | 0.943244 | 0.742802 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` | 5.51053e-49 | 0.398915 | 0.706973 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 2.9054e-52 | 0.753536 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 6.74893e-138 | 0.93319 | 0.96622 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` | 7.74245e-38 | 0.48053 | 0.756231 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 1.01497e-07 | 0.0631138 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.02034e-11 | 0.0936113 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` | 9.01179e-25 | 0.620327 | 0.853368 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` | 2.06436e-33 | 0.428796 | 0.730244 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` | 7.35118e-61 | 0.1007 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` | 1.78301e-29 | 0.164769 | 0.474306 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` | 0.168102 | 0.0947741 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` | 2.67047e-20 | 0.809246 | 0.925158 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` | 6.80319e-19 | 0.976182 | 0.986083 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 9.04706e-87 | 0.857757 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` | 1.97792e-25 | 0.823587 | 0.929602 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 9.3147e-86 | 0.0722701 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.07769e-09 | 0.112112 | 0.42264 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 8.45535e-10 | 0.692 | 0.879487 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 4.60623e-30 | 0.00358518 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 0.941305 | 0.882272 | 0.942857 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.645929 | 0.971823 | 0.984515 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 1.50779e-08 | 0.957756 | 0.979389 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 0.793231 | 0.508751 | 0.769606 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 5.01074e-11 | 0.881709 | 0.942857 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 4.70973e-05 | 0.237698 | 0.545501 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 2.48498e-93 | 0.0543511 | 0.365768 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` | 1.93976e-16 | 0.0339779 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 0.00706562 | 0.681458 | 0.877215 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` | 3.00048e-34 | 0.286922 | 0.585603 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` | 6.77948e-69 | 0.114387 | 0.42264 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` | 6.7666e-31 | 0.429642 | 0.730244 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` | 7.00806e-10 | 0.656741 | 0.866693 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` | 0.0977923 | 0.186104 | 0.492976 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 8.2969e-22 | 0.380755 | 0.687014 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` | 1.87552e-70 | 0.296294 | 0.602262 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` | 4.17739e-10 | 0.0688802 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` | 3.69153e-21 | 0.447579 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 3.43505e-25 | 0.243637 | 0.54901 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` | 2.4001e-06 | 0.0531875 | 0.362841 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` | 0.146093 | 0.121076 | 0.430932 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` | 0.200794 | 0.0777887 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` | 0.995473 | 0.0778016 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` | 3.78931e-08 | 0.694088 | 0.879487 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` | 2.37311e-05 | 0.256788 | 0.558225 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` | 6.24403e-28 | 0.925697 | 0.962416 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` | 0.27327 | 0.0777827 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` | 3.84778e-07 | 0.105651 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` | 3.24291e-46 | 0.00271155 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` | 5.63531e-19 | 0.0112352 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` | 1.34387e-66 | 0.728592 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` | 1.14042e-20 | 0.416206 | 0.727265 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` | 1.16419e-09 | 0.0222165 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` | 1.23569e-39 | 0.339451 | 0.645216 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` | 6.33613e-31 | 0.0438246 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` | 2.99498e-07 | 0.0962736 | 0.413159 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` | 0.000530037 | 0.499258 | 0.76267 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` | 2.3144e-105 | 0.358461 | 0.665929 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` | 5.97628e-35 | 0.13579 | 0.44776 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 6.25955e-16 | 0.0300316 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 1.45591e-10 | 0.57285 | 0.812762 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` | 0.914806 | 0.0767433 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` | 0.298956 | 0.18283 | 0.489514 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` | 3.12e-07 | 0.0391509 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` | 0.00642149 | 0.0508893 | 0.353818 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` | 3.93107e-05 | 0.0398683 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` | 8.16794e-40 | 0.735603 | 0.887797 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` | 0.0240417 | 0.0265096 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` | 9.41127e-47 | 0.182537 | 0.489514 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` | 0.0859949 | 0.128554 | 0.435946 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` | 0.556949 | 0.114554 | 0.42264 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` | 6.74128e-19 | 0.622033 | 0.853368 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` | 5.77496e-66 | 0.813233 | 0.92675 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` | 3.95619e-38 | 0.0269766 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` | 2.26376e-09 | 0.345012 | 0.653293 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` | 1.80233e-32 | 0.123778 | 0.431493 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` | 7.86108e-08 | 0.444257 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` | 0.00769964 | 0.0634128 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_apen_55_Max_W8` | 2.98081e-09 | 0.725424 | 0.887797 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` | 0.220936 | 0.181699 | 0.489514 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` | 3.26305e-05 | 0.148189 | 0.453715 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_perm_55_Min_W233` | 0.0203251 | 0.373892 | 0.682044 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` | 5.66106e-05 | 0.239836 | 0.546728 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 2.46989e-08 | 0.236002 | 0.544117 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 0.00261785 | 0.533838 | 0.788876 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 6.32959e-29 | 0.0042501 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` | 4.57e-05 | 0.0419369 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` | 0.239844 | 0.182174 | 0.489514 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 1.08864e-37 | 0.93749 | 0.966604 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 3.36347e-27 | 0.917209 | 0.960662 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 0.099692 | 0.21388 | 0.519573 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 8.76908e-20 | 0.371772 | 0.680671 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 7.73778e-23 | 0.182396 | 0.489514 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 1.21594e-28 | 0.422625 | 0.729715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 8.36764e-101 | 0.0239484 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 0.00427599 | 0.359709 | 0.665929 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.143328 | 0.835956 | 0.934711 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 3.76931e-57 | 0.624464 | 0.854349 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 0.162991 | 0.189386 | 0.499017 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 8.16307e-69 | 0.771951 | 0.896111 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 1.65646e-41 | 0.661357 | 0.868824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 6.77632e-07 | 0.663373 | 0.868824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 0.00167217 | 0.476387 | 0.755544 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 1.32345e-30 | 0.70916 | 0.885117 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` | 8.98944e-31 | 0.792051 | 0.913059 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` | 2.07577e-21 | 0.099244 | 0.413159 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` | 1.49527e-14 | 0.191912 | 0.503011 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` | 3.05541e-24 | 0.0379982 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` | 1.89467e-06 | 0.136666 | 0.44776 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` | 3.55691e-11 | 0.0755737 | 0.370418 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 3.91903e-36 | 0.0953457 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` | 0.111956 | 0.867615 | 0.934761 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` | 0.000189145 | 0.532529 | 0.788876 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 5.70419e-05 | 0.635352 | 0.859798 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` | 2.62072e-14 | 0.0511543 | 0.353818 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` | 8.21186e-69 | 0.0324889 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 2.43151e-15 | 0.489993 | 0.758984 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` | 0.0103266 | 0.809977 | 0.925158 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 7.75535e-05 | 0.711778 | 0.886059 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 2.2174e-24 | 0.591724 | 0.82543 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` | 1.03059e-41 | 0.0152115 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` | 1.97754e-47 | 0.327667 | 0.632473 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.000452699 | 0.64761 | 0.86542 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` | 0.0313142 | 0.652065 | 0.866316 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 8.90588e-22 | 0.753062 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` | 2.36771e-08 | 0.672348 | 0.871951 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` | 3.58659e-20 | 0.702843 | 0.881652 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` | 3.90652e-32 | 0.967747 | 0.983547 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` | 1.07446e-48 | 0.31538 | 0.618343 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` | 2.17654e-46 | 0.469568 | 0.749503 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` | 5.67799e-06 | 0.951184 | 0.975136 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` | 0.123105 | 0.595866 | 0.828887 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 9.42666e-54 | 0.702608 | 0.881652 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` | 1.06838e-06 | 0.103557 | 0.413159 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 3.00502e-32 | 0.648196 | 0.86542 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` | 5.22836e-05 | 0.50998 | 0.769606 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` | 0.47768 | 0.620706 | 0.853368 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` | 3.34728e-12 | 0.628885 | 0.857533 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` | 0.366642 | 0.724548 | 0.887797 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` | 1.90299e-14 | 0.201256 | 0.50817 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` | 6.26819e-50 | 0.647796 | 0.86542 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 3.75655e-06 | 0.104609 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 0.427986 | 0.845794 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 5.27288e-143 | 0.0565986 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 0.498144 | 0.147839 | 0.453715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 1.95417e-33 | 0.169342 | 0.476455 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 8.1296e-46 | 0.0247555 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.03654e-13 | 0.850963 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 3.79256e-17 | 0.14108 | 0.453277 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 2.83883e-27 | 0.268703 | 0.567008 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 0.000267674 |  |  | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 2.22076e-38 | 0.491541 | 0.758984 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 4.35438e-35 | 0.0709129 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 3.19277e-30 | 0.993949 | 0.995949 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 1.28495e-33 | 0.0133422 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 2.51583e-72 | 0.85123 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 5.3989e-51 | 0.951638 | 0.975136 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 1.12208e-14 | 0.109025 | 0.41765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 3.87037e-38 | 0.214961 | 0.519663 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 1.05235e-49 | 0.732577 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 2.7055e-39 | 0.681691 | 0.877215 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 2.86352e-55 | 0.0943704 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 4.47425e-74 | 0.665419 | 0.868824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` | 0.702571 | 0.498102 | 0.76267 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` | 1.70663e-16 | 0.856159 | 0.934711 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` | 0.00019773 | 0.657851 | 0.866693 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` | 4.96994e-07 | 0.0675931 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` | 6.96212e-15 | 0.0256628 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` | 9.41746e-06 | 0.770095 | 0.896045 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 3.91971e-30 | 0.387175 | 0.693573 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` | 0.000621082 | 0.962042 | 0.981756 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` | 1.75787e-23 | 0.146285 | 0.453715 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 2.18516e-46 | 0.454623 | 0.735987 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` | 2.18215e-16 | 0.118738 | 0.428488 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 3.61501e-06 | 0.559573 | 0.800768 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` | 3.82567e-33 | 0.753271 | 0.887797 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` | 2.18312e-19 | 0.0399271 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` | 1.41315e-06 | 0.0777633 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` | 0.29645 | 0.465825 | 0.749503 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` | 5.89236e-57 | 0.442788 | 0.735987 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` | 1.78912e-20 | 0.153723 | 0.462909 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` | 0.0657122 | 0.123903 | 0.431493 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` | 1.7794e-25 | 0.915302 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` | 9.14714e-40 | 0.89761 | 0.953112 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` | 5.5322e-45 | 0.106193 | 0.413159 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 2.84452e-55 | 0.497735 | 0.76267 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 2.09875e-75 | 0.0831608 | 0.387048 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 0.00916357 | 0.451829 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 1.08675e-07 | 0.436849 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 3.18988e-106 | 0.117717 | 0.427906 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 6.53188e-12 | 0.235516 | 0.544117 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 4.52774e-74 | 0.4264 | 0.729715 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 4.46514e-09 | 0.41343 | 0.724958 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 5.89289e-53 | 0.564552 | 0.805578 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 1.87973e-10 | 0.255898 | 0.558225 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 9.44489e-10 | 0.0707493 | 0.370418 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 3.52286e-13 | 0.203526 | 0.50817 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 1.25113e-16 | 0.915475 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 2.38114e-15 | 0.133649 | 0.446692 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 0.235088 | 0.838552 | 0.934711 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 2.23938e-06 | 0.0673249 | 0.370418 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 2.03981e-05 | 0.37773 | 0.684034 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 3.51015e-27 | 0.722354 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 1.95652e-05 | 0.00558821 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 7.99415e-28 | 0.384599 | 0.691445 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 8.55159e-68 | 0.764978 | 0.892176 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 5.92336e-19 | 0.966307 | 0.983547 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 1.48168e-106 | 0.271464 | 0.568728 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 4.64671e-10 | 0.324092 | 0.628008 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 2.01726e-13 | 0.652347 | 0.866316 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 8.6912e-15 | 0.984342 | 0.992312 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 5.48183e-36 | 0.329485 | 0.633526 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 3.40897e-31 | 0.467213 | 0.749503 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 8.80563e-11 | 0.121146 | 0.430932 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 2.60432e-08 | 0.304076 | 0.606877 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 4.18715e-05 | 0.590825 | 0.82543 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 7.22444e-06 | 0.123229 | 0.431493 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 0.000437354 | 0.70503 | 0.882173 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 0.00190206 | 0.754519 | 0.887797 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 0.00171769 | 0.356265 | 0.665571 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 4.26447e-06 | 0.804682 | 0.923345 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 0.0295547 | 0.827349 | 0.930068 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 0.758576 | 0.336251 | 0.641583 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 8.85316e-27 | 0.423692 | 0.729715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 1.31295e-18 | 0.0470407 | 0.336313 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 8.4033e-17 | 0.043922 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 0.0597805 | 0.362817 | 0.669196 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 0.0231128 | 0.685579 | 0.879487 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 0.0136585 | 0.740068 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 0.869558 | 0.797227 | 0.916904 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 6.79049e-20 | 0.018626 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 0.000583948 | 0.921917 | 0.961237 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 5.49962e-05 | 0.841929 | 0.934711 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 2.63919e-67 | 0.241526 | 0.546728 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 5.10792e-27 | 0.268647 | 0.567008 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 8.01546e-55 | 0.84347 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 1.07412e-73 | 0.0440844 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 3.31338e-19 | 0.0158774 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 1.78137e-06 | 0.449885 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 4.07152e-18 | 0.426169 | 0.729715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 1.1868e-08 | 0.201437 | 0.50817 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 0.273764 | 0.304171 | 0.606877 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 1.12943e-05 | 0.128683 | 0.435946 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 0.0232109 | 0.115331 | 0.42264 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 3.42747e-85 | 0.900386 | 0.954025 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 0.63372 | 0.580556 | 0.816714 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 8.21408e-17 | 0.043111 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 1.74747e-07 | 0.492273 | 0.758984 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.43834e-25 | 0.199201 | 0.50817 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 3.89156e-97 | 0.222733 | 0.530296 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 6.0492e-88 | 0.008682 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 0.196048 | 0.0853417 | 0.39352 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 1.7304e-16 | 0.145423 | 0.453715 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 0.00287791 | 0.240959 | 0.546728 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 3.08975e-06 | 0.442668 | 0.735987 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 1.2773e-32 | 0.210208 | 0.513154 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 0.935336 | 0.257815 | 0.558225 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 1.87655e-138 | 0.00039588 | 0.197148 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 2.85406e-48 | 0.161304 | 0.467031 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 7.42054e-79 | 0.0282983 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 3.10611e-13 | 0.724499 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 5.63992e-06 | 0.911244 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 0.0187852 | 0.8191 | 0.929184 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 8.557e-10 | 0.249504 | 0.552235 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 8.82235e-78 | 0.894714 | 0.952068 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 5.84878e-49 | 0.788686 | 0.911289 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 1.23967e-05 | 0.151086 | 0.458785 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.762922 | 0.992356 | 0.995949 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 8.08766e-10 | 0.397506 | 0.706973 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 3.51598e-05 | 0.475669 | 0.755544 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 8.60382e-44 | 0.157247 | 0.463578 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 1.05584e-16 | 0.321893 | 0.628008 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 1.2605e-19 | 0.070476 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 9.79754e-11 | 0.635128 | 0.859798 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 1.23933e-88 | 0.0234621 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.00010438 | 0.548864 | 0.792273 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 4.03794e-24 | 0.692867 | 0.879487 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` | 9.07168e-14 | 0.207861 | 0.509926 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 1.69728e-09 | 0.404762 | 0.714793 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` | 0.478312 | 0.997801 | 0.997801 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 0.150614 | 0.303275 | 0.606877 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` | 6.04684e-58 | 0.0336903 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` | 2.06514e-24 | 0.13902 | 0.449558 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 2.1981e-11 | 0.0239059 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 7.18455e-12 | 0.147878 | 0.453715 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 0.0157393 | 0.437761 | 0.735987 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 9.44937e-07 | 0.202873 | 0.50817 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` | 7.16002e-22 | 0.271802 | 0.568728 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 1.02353e-18 | 0.256829 | 0.558225 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 8.48396e-05 | 0.853396 | 0.934711 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` | 0.000128629 | 0.506874 | 0.769582 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` | 7.31803e-44 | 0.148505 | 0.453715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` | 2.35605e-08 | 0.0714404 | 0.370418 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 0.288822 | 0.138234 | 0.449558 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 1.12586e-28 | 0.698835 | 0.881063 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` | 0.000751996 | 0.227981 | 0.533025 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` | 1.77772e-29 | 0.276667 | 0.569339 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 1.03418e-06 | 0.244974 | 0.549536 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 5.13427e-38 | 0.206544 | 0.509203 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 1.16339e-19 | 0.857036 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` | 2.06704e-05 | 0.333084 | 0.637983 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` | 1.71378e-05 | 0.0995849 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` | 8.19006e-11 | 0.411346 | 0.723852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 1.04759e-14 | 0.0149484 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 8.18842e-08 | 0.451155 | 0.735987 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` | 3.40564e-05 | 0.108417 | 0.41765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 4.64457e-20 | 0.125389 | 0.433638 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 1.37835e-34 | 0.755295 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 1.31394e-44 | 0.221848 | 0.530296 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` | 7.06818e-38 | 0.0327556 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 2.81717e-06 | 0.918223 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 4.11308e-27 | 0.0735724 | 0.370418 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` | 5.7969e-54 | 0.447469 | 0.735987 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` | 1.43624e-43 | 0.572343 | 0.812762 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` | 1.9928e-11 | 0.193752 | 0.505176 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` | 1.5565e-22 | 0.267388 | 0.567008 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 6.62943e-14 | 0.0634164 | 0.370418 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 6.39671e-19 | 0.868552 | 0.934761 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 0.0041711 | 0.375624 | 0.682703 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.00399423 | 0.157319 | 0.463578 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 0.000459625 | 0.736077 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 2.50395e-07 | 0.024204 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` | 4.62954e-55 | 0.666448 | 0.868824 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` | 4.33408e-73 | 0.972653 | 0.984515 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_34_Momentum_L5` | 1.18381e-52 | 0.110077 | 0.41846 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` | 1.0418e-44 | 0.74377 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 3.52154e-26 | 0.713868 | 0.886059 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 0.0002775 | 0.935177 | 0.96622 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 1.96847e-09 | 0.524415 | 0.781912 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 7.62581e-12 | 0.0627224 | 0.370418 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 4.904e-83 | 0.267548 | 0.567008 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 7.08663e-33 | 0.639089 | 0.86251 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 3.86163e-21 | 0.0388659 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 2.82593e-52 | 0.521358 | 0.781912 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 1.22678e-15 | 0.480063 | 0.756231 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 6.90468e-14 | 0.922633 | 0.961237 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 0.000423741 | 0.454055 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 1.41327e-12 | 0.823269 | 0.929602 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 2.27537e-41 | 0.0123473 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 2.83132e-49 | 0.0327276 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 0.007064 | 0.16118 | 0.467031 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 1.97822e-06 | 0.0371581 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 0.0428676 | 0.217216 | 0.522578 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 0.740022 | 0.171627 | 0.477487 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 9.86057e-35 | 0.0781002 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 0.00556839 | 0.349561 | 0.656911 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 9.32139e-14 | 0.759441 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 1.16052e-06 | 0.93465 | 0.96622 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 0.826818 | 0.715253 | 0.886059 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 1.59535e-76 | 0.00956513 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 6.18619e-42 | 0.224684 | 0.530296 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 3.32233e-27 | 0.0287605 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 1.94334e-08 | 0.17999 | 0.489514 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 7.73781e-37 | 0.302666 | 0.606877 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 3.40651e-21 | 0.0437414 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 0.0202634 | 0.538672 | 0.791324 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 2.51192e-28 | 0.154303 | 0.462909 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.0123121 | 0.735395 | 0.887797 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 1.58398e-24 | 0.101509 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 1.87851e-07 | 0.0424822 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 9.92451e-15 | 0.851749 | 0.934711 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` | 0.585266 | 0.55151 | 0.793791 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 1.62491e-16 | 0.547704 | 0.792273 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 0.399822 | 0.0985592 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 1.81652e-40 | 0.0770465 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 2.64772e-11 | 0.348952 | 0.656911 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` | 2.40152e-50 | 0.371352 | 0.680671 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` | 1.51897e-18 | 0.674709 | 0.87274 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` | 2.70363e-19 | 0.272992 | 0.568829 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 4.40134e-08 | 0.0401847 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 0.0777036 | 0.168476 | 0.476455 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` | 0.940291 | 0.0695599 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 6.31174e-11 | 0.546136 | 0.792273 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` | 3.84956e-30 | 0.00388881 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` | 4.45588e-40 | 0.783766 | 0.90771 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` | 5.94447e-05 | 0.0256012 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 2.64632e-111 | 0.00348741 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` | 5.72424e-25 | 0.758651 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` | 7.49534e-16 | 0.690721 | 0.879487 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` | 0.521168 | 0.178341 | 0.489514 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` | 0.00563327 | 0.737832 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 2.11134e-14 | 0.825069 | 0.929602 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 1.38265e-73 | 0.0339937 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 5.6521e-132 | 0.0669228 | 0.370418 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 3.47013e-87 | 0.0441346 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 9.68779e-30 | 0.0555046 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` | 7.08395e-42 | 0.0436178 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.0163665 | 0.148067 | 0.453715 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` | 2.53909e-39 | 0.576665 | 0.814396 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 5.97007e-26 | 0.523541 | 0.781912 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 1.14601e-10 | 0.425275 | 0.729715 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 2.2413e-17 | 0.523006 | 0.781912 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 4.20696e-08 | 0.0418692 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 8.89461e-35 | 0.00716992 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 4.03379e-11 | 0.0686585 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 4.80815e-18 | 0.165905 | 0.474831 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 2.94631e-77 | 0.0412557 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 5.9575e-77 | 0.0681947 | 0.370418 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 8.7023e-11 | 0.09692 | 0.413159 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 6.05759e-05 | 0.0809183 | 0.380163 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 2.23288e-12 | 0.206296 | 0.509203 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` | 0.388664 | 0.224551 | 0.530296 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 7.08564e-25 | 0.669468 | 0.870483 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 3.4088e-32 | 0.481376 | 0.756231 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` | 3.46041e-31 | 0.279568 | 0.572942 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` | 1.5639e-17 | 0.748133 | 0.887797 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` | 0.0159413 | 0.433703 | 0.73464 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` | 1.16628e-22 | 0.558655 | 0.800768 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` | 2.17296e-09 | 0.867778 | 0.934761 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` | 3.53431e-10 | 0.202999 | 0.50817 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.0607635 | 0.815713 | 0.927455 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` | 6.34936e-30 | 0.695819 | 0.879487 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` | 1.74308e-08 | 0.203458 | 0.50817 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` | 2.34199e-18 | 0.841528 | 0.934711 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` | 2.27998e-44 | 0.392133 | 0.699935 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` | 7.71293e-17 | 0.312846 | 0.615799 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 3.96853e-09 | 0.87786 | 0.942186 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` | 1.32518e-41 | 0.356842 | 0.665571 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` | 1.47441e-17 | 0.309323 | 0.611282 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` | 0.24438 | 0.490658 | 0.758984 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` | 0.0297072 | 0.304657 | 0.606877 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` | 9.45941e-05 | 0.127731 | 0.435946 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` | 4.64567e-73 | 0.0263347 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` | 0.362368 | 0.0910448 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` | 0.167486 | 0.645566 | 0.86542 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` | 0.555969 | 0.73285 | 0.887797 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` | 8.97783e-30 | 0.0237998 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` | 1.09435e-41 | 0.757361 | 0.887797 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` | 3.76978e-47 | 0.0426673 | 0.333016 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` | 7.40947e-16 | 0.264121 | 0.567008 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` | 0.78782 | 0.0166849 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` | 1.24849e-49 | 0.0621497 | 0.370418 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` | 2.28523e-43 | 0.946255 | 0.973626 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` | 2.48281e-43 | 0.585648 | 0.821557 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` | 8.36205e-05 | 0.453643 | 0.735987 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` | 1.37796e-44 | 0.0461125 | 0.336313 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` | 6.0581e-31 | 0.232607 | 0.541301 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` | 6.79756e-05 | 0.577272 | 0.814396 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` | 7.24802e-30 | 0.536842 | 0.790968 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` | 3.12623e-07 | 0.276292 | 0.569339 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` | 0.00773282 | 0.168606 | 0.476455 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` | 2.85282e-10 | 0.0351252 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` | 1.12395e-09 | 0.656379 | 0.866693 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` | 0.00462335 | 0.136581 | 0.44776 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` | 2.21231e-12 | 0.0606624 | 0.370418 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` | 9.27668e-43 | 0.0463246 | 0.336313 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` | 0.0188094 | 0.750686 | 0.887797 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` | 5.66394e-24 | 0.469406 | 0.749503 | True | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` | 0.00614299 | 0.226504 | 0.532071 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` | 7.99256e-41 | 0.986854 | 0.992835 | False | False | removed:p_value |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` | 1.78482e-06 | 0.247452 | 0.552235 | False | False | removed:icir |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` | 0.00154643 | 0.323302 | 0.628008 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` | 0.00838669 | 0.100424 | 0.413159 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` | 0.00169402 | 0.86167 | 0.934761 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` | 5.01428e-05 | 0.0382223 | 0.333016 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` | 0.00890841 | 0.630235 | 0.857533 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` | 1.9318e-38 | 0.0163276 | 0.333016 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 1.04516e-24 | 0.039238 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 8.84817e-35 | 0.490417 | 0.797663 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 0.129139 | 0.255909 | 0.584599 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 2.56002e-54 | 0.544174 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 2.97231e-31 | 0.204084 | 0.528021 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_APO_55-144-0_Range_W8` | 3.95308e-28 | 0.884757 | 0.947546 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_APO_55-144-0_Std_W144` | 1.12174e-07 | 0.912271 | 0.960662 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_CMO_144_Kurt_W5` | 0.880989 | 0.269132 | 0.590431 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_CMO_89_Momentum_L21` | 4.64192e-19 | 0.399653 | 0.74542 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_CMO_89_Slope_W5` | 5.5119e-18 | 0.50438 | 0.805068 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_CMO_8_Rank_W3` | 5.41088e-09 | 0.692651 | 0.891597 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 0.485764 | 0.455189 | 0.778128 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 4.03073e-09 | 0.0363251 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_55-233-34_Momentum_L55` | 1.57068e-26 | 0.374086 | 0.727714 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_8-34-9_Lag_8` | 9.13779e-12 | 0.285498 | 0.612836 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 1.35431e-56 | 0.0757143 | 0.392868 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 2.55459e-29 | 0.130177 | 0.463059 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_13-55-13_Mean_W89` | 1.73565e-51 | 0.139763 | 0.486727 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 5.06203e-31 | 0.276565 | 0.598823 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 3.91112e-64 | 0.425383 | 0.764239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_5-21-5_Range_W8` | 3.7478e-18 | 0.0299952 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 8.02389e-28 | 0.00840158 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_13-55-13_DecayLinear_W13` | 2.21104e-43 | 0.983198 | 0.988311 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_34-89-13_Std_W3` | 1.40266e-55 | 0.1705 | 0.502765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 3.66124e-93 | 0.0944855 | 0.433665 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.000260418 | 0.11542 | 0.445574 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 3.56054e-34 | 0.835182 | 0.944509 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_21-55-9_ZScore_W3` | 3.75875e-51 | 0.0155573 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 1.07165e-63 | 0.15573 | 0.495852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 4.31677e-18 | 0.102392 | 0.437775 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_12-26-9_Mean_W34` | 8.21782e-37 | 0.970339 | 0.982518 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 1.73706e-09 | 0.00992355 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_21-55-9_Std_W144` | 0.448217 | 0.167995 | 0.502765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_21-89-13_Momentum_L233` | 1.59366e-14 | 0.0825594 | 0.40602 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 0.0337953 | 0.17069 | 0.502765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_55-233-34_ZScore_W21` | 1.41518e-27 | 0.414622 | 0.761926 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 0.445815 | 0.160727 | 0.49894 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_21-89-13_Max_W34` | 7.0479e-24 | 0.242261 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_8-21-5_TsArgmin_W5` | 0.270548 | 0.873621 | 0.94579 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W13` | 2.53588e-10 | 0.0314843 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 1.70185e-78 | 0.306199 | 0.640703 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 6.87731e-35 | 0.545568 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_8_Mean_W55` | 9.17588e-42 | 0.654244 | 0.882963 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_9_ZScore_W144` | 7.04226e-13 | 0.78993 | 0.92344 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 5.0488e-13 | 0.104225 | 0.437775 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 3.48613e-14 | 0.869065 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.28852e-20 | 0.0564249 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Rank_W3` | 0.00156764 | 0.559114 | 0.82446 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 3.43619e-40 | 0.609014 | 0.86654 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 3.48613e-14 | 0.869065 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.408349 | 0.608745 | 0.86654 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 2.32896e-59 | 0.249259 | 0.57792 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 5.48472e-13 | 0.0237629 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_TsRank_W5` | 0.0653935 | 0.575829 | 0.839706 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 0.00392406 | 0.266578 | 0.590431 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_8_Rank_W5` | 0.103433 | 0.456252 | 0.778128 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_9_Std_W34` | 4.46254e-10 | 0.252353 | 0.581813 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MOM_13_Min_W144` | 4.35294e-23 | 0.185881 | 0.514887 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MOM_21` | 9.3022e-101 | 0.548635 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_MOM_89_Rank_W89` | 8.96263e-19 | 0.261549 | 0.589373 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_PPO_13-55-0_Lag_3` | 1.7552e-43 | 0.491143 | 0.797663 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.000846601 | 0.530112 | 0.819862 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 3.44201e-34 | 0.201604 | 0.528021 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 0.00656996 | 0.0472729 | 0.336313 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_PPO_55-233-0_Kurt_W34` | 1.74293e-11 | 0.543953 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_12_Skew_W233` | 5.48622e-08 | 0.143198 | 0.491812 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_13_Range_W5` | 7.51669e-19 | 0.490384 | 0.797663 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_89_Kurt_W13` | 0.943244 | 0.742802 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_8_Lag_1` | 5.51053e-49 | 0.398915 | 0.74542 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 2.9054e-52 | 0.753536 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_9_TsRank_W13` | 1.08131e-05 | 0.126173 | 0.458642 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 6.74893e-138 | 0.93319 | 0.96622 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_34_Mean_W89` | 7.74245e-38 | 0.48053 | 0.793792 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 1.01497e-07 | 0.0631138 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_8_34_Ratio` | 2.1713e-05 | 0.157123 | 0.495852 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.02034e-11 | 0.0936113 | 0.433665 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_13_Rank_W144` | 9.01179e-25 | 0.620327 | 0.870737 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_55_Rank_W3` | 2.06436e-33 | 0.428796 | 0.764239 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_5_Skew_W13` | 7.35118e-61 | 0.1007 | 0.437775 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROC_55_Range_W89` | 1.78301e-29 | 0.164769 | 0.502765 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROC_55_Std_W144` | 0.168102 | 0.0947741 | 0.433665 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROC_89_Range_W3` | 3.96106e-25 | 0.847012 | 0.944509 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_ROC_89_Slope_W233` | 2.67047e-20 | 0.809246 | 0.937219 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_RSI_14_Momentum_L55` | 6.80319e-19 | 0.976182 | 0.984087 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_RSI_34_Max_W21` | 7.81678e-61 | 0.904575 | 0.960508 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 9.04706e-87 | 0.857757 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_RSI_8_Rank_W55` | 1.97792e-25 | 0.823587 | 0.940239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 9.3147e-86 | 0.0722701 | 0.391201 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.07769e-09 | 0.112112 | 0.445574 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 8.45535e-10 | 0.692 | 0.891597 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 4.60623e-30 | 0.00358518 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastk_21-8-5-0_Range_W8` | 1.30479e-20 | 0.866555 | 0.944509 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 0.941305 | 0.882272 | 0.946921 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_13_Lag_5` | 3.37645e-30 | 0.241086 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.645929 | 0.971823 | 0.982518 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_55_Rank_W233` | 2.48701e-60 | 0.878527 | 0.946921 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 1.50779e-08 | 0.957756 | 0.979389 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 0.793231 | 0.508751 | 0.808821 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 5.01074e-11 | 0.881709 | 0.946921 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 4.70973e-05 | 0.237698 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_34_Slope_W21` | 1.63929e-06 | 0.0256968 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 2.48498e-93 | 0.0543511 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_21_89_Ratio` | 1.26313e-36 | 0.334808 | 0.680548 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_5_Lag_2` | 4.73719e-114 | 0.0062254 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_5_Std_W8` | 1.93976e-16 | 0.0339779 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_89_Slope_W13` | 2.2501e-18 | 0.3188 | 0.661511 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 0.00706562 | 0.681458 | 0.888697 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_STDDEV_89_Skew_W5` | 3.00048e-34 | 0.286922 | 0.613249 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_TSF_55_Kurt_W13` | 6.77948e-69 | 0.114387 | 0.445574 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_TSF_89_Momentum_L8` | 6.7666e-31 | 0.429642 | 0.764239 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_TSF_89_Range_W233` | 7.00806e-10 | 0.656741 | 0.883046 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Kurt_W13` | 1.4165e-08 | 0.230808 | 0.56622 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Log1p` | 0.0977923 | 0.186104 | 0.514887 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Slope_W8` | 8.07048e-11 | 0.480371 | 0.793792 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 8.2969e-22 | 0.380755 | 0.732107 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_VAR_55_TsRank_W5` | 1.87552e-70 | 0.296294 | 0.630573 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `close_12h_statistics_VAR_89_TsRank_W13` | 4.17739e-10 | 0.0688802 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_apen_55_Max_W8` | 2.98081e-09 | 0.725424 | 0.898659 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_fractal_dim_55_Kurt_W55` | 0.220936 | 0.181699 | 0.514753 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_fractal_dim_55_Lag_21` | 1.53753e-24 | 0.635206 | 0.881149 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_perm_21_Mean_W34` | 3.26305e-05 | 0.148189 | 0.491986 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_perm_55_Min_W233` | 0.0203251 | 0.373892 | 0.727714 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_shannon_close_return_55_Slope_W13` | 5.66106e-05 | 0.239836 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 2.46989e-08 | 0.236002 | 0.569084 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 0.00261785 | 0.533838 | 0.820528 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 6.32959e-29 | 0.0042501 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_shannon_volume_21_Max_W89` | 4.57e-05 | 0.0419369 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ent_12h_shannon_volume_55_Max_W233` | 0.239844 | 0.182174 | 0.514753 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_144_Lag_8` | 1.15361e-32 | 0.881568 | 0.946921 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 1.08864e-37 | 0.93749 | 0.966604 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 3.36347e-27 | 0.917209 | 0.960662 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 0.099692 | 0.21388 | 0.543404 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 8.76908e-20 | 0.371772 | 0.727714 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 7.73778e-23 | 0.182396 | 0.514753 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 1.21594e-28 | 0.422625 | 0.764239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 8.36764e-101 | 0.0239484 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 0.00427599 | 0.359709 | 0.71654 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_55_Std_W5` | 0.000163632 | 0.00100003 | 0.166005 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.143328 | 0.835956 | 0.944509 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_13_Slope_W8` | 7.56872e-07 | 0.917676 | 0.960662 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 3.76931e-57 | 0.624464 | 0.873548 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_34_DecayLinear_W21` | 1.04958e-10 | 0.597585 | 0.855165 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 0.162991 | 0.189386 | 0.51821 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 8.16307e-69 | 0.771951 | 0.912207 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 1.65646e-41 | 0.661357 | 0.885042 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_21_Range_W21` | 9.60541e-07 | 0.707416 | 0.89635 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 6.77632e-07 | 0.663373 | 0.885042 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 0.00167217 | 0.476387 | 0.793792 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 1.32345e-30 | 0.70916 | 0.89635 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_13_Lag_2` | 2.42762e-39 | 0.532169 | 0.820495 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_144_Slope_W233` | 8.98944e-31 | 0.792051 | 0.92375 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_233_Max_W144` | 2.07577e-21 | 0.099244 | 0.437376 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_34_ZScore_W8` | 1.49527e-14 | 0.191912 | 0.522252 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_21_Slope_W89` | 3.05541e-24 | 0.0379982 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_233_Rank_W233` | 1.89467e-06 | 0.136666 | 0.479293 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_55_Slope_W233` | 3.55691e-11 | 0.0755737 | 0.392868 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 3.91903e-36 | 0.0953457 | 0.433665 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_8_Skew_W3` | 0.111956 | 0.867615 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 7.75535e-05 | 0.711778 | 0.897219 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 2.2174e-24 | 0.591724 | 0.851672 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_14_Range_W233` | 1.03059e-41 | 0.0152115 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_233_Rank_W144` | 0.000844187 | 0.0519276 | 0.361544 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_13_Skew_W21` | 1.97754e-47 | 0.327667 | 0.671515 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.000452699 | 0.64761 | 0.881971 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_144_Mean_W13` | 9.42408e-22 | 0.00978342 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_14_Lag_3` | 2.36791e-13 | 0.127599 | 0.460466 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_34_Mean_W34` | 0.0313142 | 0.652065 | 0.882795 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 8.90588e-22 | 0.753062 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_144_Skew_W34` | 2.36771e-08 | 0.672348 | 0.88697 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_14_Log1p` | 1.9738e-62 | 0.473352 | 0.793792 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_233_Min_W34` | 3.58659e-20 | 0.702843 | 0.895181 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_34_Range_W3` | 3.90652e-32 | 0.967747 | 0.982518 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_34_Skew_W34` | 1.07446e-48 | 0.31538 | 0.657151 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_5_Mean_W13` | 2.17654e-46 | 0.469568 | 0.792695 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Kurt_W8` | 5.67799e-06 | 0.951184 | 0.975136 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Momentum_L233` | 6.94024e-14 | 0.553579 | 0.822933 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Std_W89` | 0.123105 | 0.595866 | 0.855163 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 9.42666e-54 | 0.702608 | 0.895181 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_144_Mean_W34` | 1.06838e-06 | 0.103557 | 0.437775 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 3.00502e-32 | 0.648196 | 0.881971 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_21_Rank_W21` | 5.22836e-05 | 0.50998 | 0.808821 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_233_Skew_W13` | 0.47768 | 0.620706 | 0.870737 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_34_Momentum_L21` | 3.34728e-12 | 0.628885 | 0.877268 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_55_Lag_8` | 0.366642 | 0.724548 | 0.898659 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_89_Range_W34` | 1.90299e-14 | 0.201256 | 0.528021 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_144` | 6.26819e-50 | 0.647796 | 0.881971 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_233_Mean_W5` | 5.09856e-24 | 0.429693 | 0.764239 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 3.75655e-06 | 0.104609 | 0.437775 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 0.427986 | 0.845794 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 5.27288e-143 | 0.0565986 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 0.498144 | 0.147839 | 0.491986 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS_DI_8_89_Cross` | 2.69877e-22 | 0.619757 | 0.870737 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 1.95417e-33 | 0.169342 | 0.502765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 8.1296e-46 | 0.0247555 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.03654e-13 | 0.850963 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 3.79256e-17 | 0.14108 | 0.487902 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 2.83883e-27 | 0.268703 | 0.590431 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 0.000267674 |  |  | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 2.22076e-38 | 0.491541 | 0.797663 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 4.35438e-35 | 0.0709129 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 3.19277e-30 | 0.993949 | 0.993949 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 1.28495e-33 | 0.0133422 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 2.51583e-72 | 0.85123 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 5.3989e-51 | 0.951638 | 0.975136 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_8-3-0_Std_W21` | 4.56105e-50 | 0.731731 | 0.902801 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_34-55-144_Kurt_W5` | 3.67142e-18 | 0.171089 | 0.502765 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 1.12208e-14 | 0.109025 | 0.445574 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 3.87037e-38 | 0.214961 | 0.543404 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-10-20_ZScore_W3` | 9.92119e-30 | 0.174425 | 0.507975 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-13-26_Mean_W233` | 8.56594e-10 | 0.240931 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 1.05235e-49 | 0.732577 | 0.902801 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 2.7055e-39 | 0.681691 | 0.888697 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 2.86352e-55 | 0.0943704 | 0.433665 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_5_Momentum_L233` | 6.33077e-58 | 0.124522 | 0.455971 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 4.47425e-74 | 0.665419 | 0.885042 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_144_Std_W144` | 1.16622e-15 | 0.0306479 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_14_Rank_W5` | 0.702571 | 0.498102 | 0.797663 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Lag_13` | 1.70663e-16 | 0.856159 | 0.944509 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Range_W8` | 0.00019773 | 0.657851 | 0.883046 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Rank_W34` | 4.96994e-07 | 0.0675931 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_233_Kurt_W13` | 0.701484 | 0.825024 | 0.940239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_233_Mean_W13` | 3.51786e-14 | 0.723126 | 0.898659 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_5_20_Cross` | 6.96212e-15 | 0.0256628 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_13_Lag_1` | 9.41746e-06 | 0.770095 | 0.912207 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 3.91971e-30 | 0.387175 | 0.735929 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_55_Range_W21` | 0.000621082 | 0.962042 | 0.981756 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_89_Slope_W34` | 1.75787e-23 | 0.146285 | 0.491986 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 2.18516e-46 | 0.454623 | 0.778128 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_21_DecayLinear_W21` | 5.22047e-66 | 0.385938 | 0.735929 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_55_Min_W233` | 2.18215e-16 | 0.118738 | 0.447965 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 3.61501e-06 | 0.559573 | 0.82446 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `hlcv_12h_volume_EOM_14_Slope_W3` | 3.82567e-33 | 0.753271 | 0.903247 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_21_Std_W233` | 5.05401e-17 | 0.055597 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_55_Max_W5` | 2.18312e-19 | 0.0399271 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_55_Rank_W8` | 9.23519e-89 | 0.524138 | 0.816634 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_cs_spread_21_Rank_W8` | 1.41315e-06 | 0.0777633 | 0.392868 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_kyle_lambda_21_Momentum_L13` | 0.29645 | 0.465825 | 0.791401 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_13_Skew_W13` | 5.89236e-57 | 0.442788 | 0.773714 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_21_Std_W144` | 1.78912e-20 | 0.153723 | 0.495852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_55_Kurt_W5` | 0.0657122 | 0.123903 | 0.455971 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_55_Skew_W21` | 1.7794e-25 | 0.915302 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_roll_spread_55_Min_W34` | 9.14714e-40 | 0.89761 | 0.957194 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_vpin_30_Slope_W89` | 4.80328e-24 | 0.204634 | 0.528021 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `ms_12h_vpin_50_Kurt_W13` | 5.5322e-45 | 0.106193 | 0.440703 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 2.84452e-55 | 0.497735 | 0.797663 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_cycle_HT-SINE-Sine_Min_W89` | 1.08922e-116 | 0.000565499 | 0.140809 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 2.09875e-75 | 0.0831608 | 0.40602 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 0.00916357 | 0.451829 | 0.778128 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 1.08675e-07 | 0.436849 | 0.76873 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 3.18988e-106 | 0.117717 | 0.447965 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 6.53188e-12 | 0.235516 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 4.52774e-74 | 0.4264 | 0.764239 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 4.46514e-09 | 0.41343 | 0.761926 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 5.89289e-53 | 0.564552 | 0.829341 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 1.87973e-10 | 0.255898 | 0.584599 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 9.44489e-10 | 0.0707493 | 0.388073 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 3.52286e-13 | 0.203526 | 0.528021 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_5_Slope_W233` | 8.34274e-40 | 0.774826 | 0.912207 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_89_Slope_W5` | 1.03027e-07 | 0.0957895 | 0.433665 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 1.25113e-16 | 0.915475 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 2.38114e-15 | 0.133649 | 0.472036 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 0.235088 | 0.838552 | 0.944509 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_21-55-9_Sign` | 2.42896e-41 | 0.0358644 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 2.23938e-06 | 0.0673249 | 0.388073 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_55-144-21_Skew_W233` | 4.72356e-11 | 0.183988 | 0.514753 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 2.03981e-05 | 0.37773 | 0.729106 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 3.51015e-27 | 0.722354 | 0.898659 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_55-233-34_Momentum_L13` | 0.147073 | 0.860513 | 0.944509 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 1.95652e-05 | 0.00558821 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_12-26-9_Range_W21` | 4.30233e-06 | 0.0257655 | 0.328045 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 7.99415e-28 | 0.384599 | 0.735929 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 8.55159e-68 | 0.764978 | 0.90921 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 5.92336e-19 | 0.966307 | 0.982518 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 1.48168e-106 | 0.271464 | 0.592934 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_34-89-13_Mean_W3` | 1.73929e-92 | 0.00775884 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 4.64671e-10 | 0.324092 | 0.666934 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-55-9_Kurt_W13` | 7.66766e-34 | 0.8175 | 0.940239 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-55-9_Lag_8` | 4.8407e-06 | 0.0759446 | 0.392868 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-89-13_DecayLinear_W13` | 2.05994e-05 | 0.15319 | 0.495852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 2.01726e-13 | 0.652347 | 0.882795 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_34-89-13_Slope_W89` | 3.60827e-93 | 0.0909689 | 0.433665 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 8.6912e-15 | 0.984342 | 0.988311 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 5.48183e-36 | 0.329485 | 0.672473 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 3.40897e-31 | 0.467213 | 0.791401 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 8.80563e-11 | 0.121146 | 0.453613 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 2.60432e-08 | 0.304076 | 0.639143 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 4.18715e-05 | 0.590825 | 0.851672 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 7.22444e-06 | 0.123229 | 0.455971 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Line_21_DecayLinear_W5` | 8.25681e-14 | 0.0522715 | 0.361544 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 0.000437354 | 0.70503 | 0.895675 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 0.00190206 | 0.754519 | 0.903247 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 0.00171769 | 0.356265 | 0.71253 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 4.26447e-06 | 0.804682 | 0.934106 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 0.0295547 | 0.827349 | 0.940685 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_21_Range_W34` | 2.75932e-14 | 0.642978 | 0.881971 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 0.758576 | 0.336251 | 0.680704 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 8.85316e-27 | 0.423692 | 0.764239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 1.31295e-18 | 0.0470407 | 0.336313 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 8.4033e-17 | 0.043922 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 0.0597805 | 0.362817 | 0.719852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_34_Mean_W13` | 3.30549e-21 | 0.0402539 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 0.0231128 | 0.685579 | 0.891431 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 0.0136585 | 0.740068 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 0.869558 | 0.797227 | 0.927615 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_13_Rank_W55` | 1.08811e-80 | 0.26026 | 0.589135 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 6.79049e-20 | 0.018626 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 0.000583948 | 0.921917 | 0.961237 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 5.49962e-05 | 0.841929 | 0.944509 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 2.63919e-67 | 0.241526 | 0.569084 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 5.10792e-27 | 0.268647 | 0.590431 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_55_Kurt_W21` | 0.0032814 | 0.748136 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_89_Max_W3` | 0.861551 | 0.678341 | 0.888697 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_34_Momentum_L233` | 0.000215924 | 0.644609 | 0.881971 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 8.01546e-55 | 0.84347 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 1.07412e-73 | 0.0440844 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_89_Mean_W13` | 4.86923e-42 | 0.698781 | 0.894583 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_14_Kurt_W34` | 7.01542e-08 | 0.373493 | 0.727714 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 3.31338e-19 | 0.0158774 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_5_Momentum_L5` | 0.138045 | 0.187403 | 0.515616 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_7_Std_W13` | 3.48347e-25 | 0.933751 | 0.96622 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 1.78137e-06 | 0.449885 | 0.778128 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-5-3-0_Range_W233` | 2.36158e-15 | 0.405747 | 0.753582 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 4.07152e-18 | 0.426169 | 0.764239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 1.1868e-08 | 0.201437 | 0.528021 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 0.273764 | 0.304171 | 0.639143 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Kurt_W5` | 5.11382e-19 | 0.495565 | 0.797663 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 1.12943e-05 | 0.128683 | 0.461037 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_55-8-5-0_Skew_W233` | 0.00399376 | 0.0167513 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 0.0232109 | 0.115331 | 0.445574 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 3.42747e-85 | 0.900386 | 0.958103 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 0.63372 | 0.580556 | 0.842906 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 8.21408e-17 | 0.043111 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_5_Kurt_W34` | 1.09556e-19 | 0.0110411 | 0.30547 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 1.74747e-07 | 0.492273 | 0.797663 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.43834e-25 | 0.199201 | 0.528021 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 3.89156e-97 | 0.222733 | 0.553923 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 6.0492e-88 | 0.008682 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 0.196048 | 0.0853417 | 0.412623 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 1.7304e-16 | 0.145423 | 0.491986 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 0.00287791 | 0.240959 | 0.569084 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 3.08975e-06 | 0.442668 | 0.773714 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 1.2773e-32 | 0.210208 | 0.536838 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 0.935336 | 0.257815 | 0.586264 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Kurt_W21` | 7.51143e-108 | 0.00834524 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 1.87655e-138 | 0.00039588 | 0.140809 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 2.85406e-48 | 0.161304 | 0.49894 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 7.42054e-79 | 0.0282983 | 0.328045 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 3.10611e-13 | 0.724499 | 0.898659 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 5.63992e-06 | 0.911244 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 0.0187852 | 0.8191 | 0.940239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 8.557e-10 | 0.249504 | 0.57792 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_13_Slope_W8` | 0.616899 | 0.587125 | 0.849965 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 8.82235e-78 | 0.894714 | 0.956154 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_5_Rank_W34` | 1.54493e-09 | 0.0638668 | 0.388073 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 5.84878e-49 | 0.788686 | 0.92344 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 1.23967e-05 | 0.151086 | 0.495852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.762922 | 0.992356 | 0.993949 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 8.08766e-10 | 0.397506 | 0.74542 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 3.51598e-05 | 0.475669 | 0.793792 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 8.60382e-44 | 0.157247 | 0.495852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 1.05584e-16 | 0.321893 | 0.665157 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 1.2605e-19 | 0.070476 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 9.79754e-11 | 0.635128 | 0.881149 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_14_Momentum_L21` | 4.9747e-05 | 0.498139 | 0.797663 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 1.23933e-88 | 0.0234621 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.00010438 | 0.548864 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 4.03794e-24 | 0.692867 | 0.891597 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 2.81717e-06 | 0.918223 | 0.960662 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_cvar_5pct_100_Range_W34` | 4.79969e-06 | 0.675023 | 0.88697 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_jb_100_Slope_W13` | 5.7969e-54 | 0.447469 | 0.778128 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_mdd_55_Min_W8` | 1.18446e-36 | 0.542241 | 0.820824 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_rsj_13_Range_W21` | 0.000123501 | 0.0247773 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_rsj_21_Max_W21` | 1.43624e-43 | 0.572343 | 0.838314 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_rv_up_21_Mean_W89` | 0.480133 | 0.016511 | 0.328045 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_ud_vol_ratio_21_Max_W13` | 1.9928e-11 | 0.193752 | 0.524395 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `tr_12h_ud_vol_ratio_21_Std_W34` | 1.5565e-22 | 0.267388 | 0.590431 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 6.62943e-14 | 0.0634164 | 0.388073 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 6.39671e-19 | 0.868552 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 0.0041711 | 0.375624 | 0.727862 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_APO_13-34-0_Mean_W55` | 0.000838462 | 0.0343847 | 0.328045 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.00399423 | 0.157319 | 0.495852 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 0.000459625 | 0.736077 | 0.902801 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 2.50395e-07 | 0.024204 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_14_Max_W144` | 4.62954e-55 | 0.666448 | 0.885042 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_14_Rank_W13` | 4.33408e-73 | 0.972653 | 0.982518 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_233_Max_W55` | 2.21773e-09 | 0.61993 | 0.870737 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_34_Momentum_L5` | 1.18381e-52 | 0.110077 | 0.445574 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_8_Momentum_L3` | 1.0418e-44 | 0.74377 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 3.52154e-26 | 0.713868 | 0.897219 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 0.0002775 | 0.935177 | 0.96622 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 1.96847e-09 | 0.524415 | 0.816634 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_21-89-13_Slope_W13` | 4.27971e-20 | 0.113467 | 0.445574 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 7.62581e-12 | 0.0627224 | 0.388073 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 4.904e-83 | 0.267548 | 0.590431 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_5-21-5_Min_W144` | 2.74646e-19 | 0.0249009 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 7.08663e-33 | 0.639089 | 0.881971 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 3.86163e-21 | 0.0388659 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 2.82593e-52 | 0.521358 | 0.816634 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 1.22678e-15 | 0.480063 | 0.793792 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 6.90468e-14 | 0.922633 | 0.961237 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 0.000423741 | 0.454055 | 0.778128 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 1.41327e-12 | 0.823269 | 0.940239 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 2.27537e-41 | 0.0123473 | 0.32363 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 2.83132e-49 | 0.0327276 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_21-55-9_TsArgmax_W21` | 1.49144e-21 | 0.949688 | 0.975136 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 0.007064 | 0.16118 | 0.49894 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 1.97822e-06 | 0.0371581 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_34-89-13_ZScore_W3` | 1.41117e-07 | 0.243799 | 0.570009 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 0.0428676 | 0.217216 | 0.546332 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_13-55-13_Skew_W13` | 2.376e-05 | 0.524745 | 0.816634 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 0.740022 | 0.171627 | 0.502765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 9.86057e-35 | 0.0781002 | 0.392868 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 0.00556839 | 0.349561 | 0.701941 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_5-21-5_Range_W21` | 0.0375991 | 0.219226 | 0.548616 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 9.32139e-14 | 0.759441 | 0.904788 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 1.16052e-06 | 0.93465 | 0.96622 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 0.826818 | 0.715253 | 0.897219 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_34-89-13_Kurt_W5` | 1.45998e-124 | 0.183608 | 0.514753 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 1.59535e-76 | 0.00956513 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 6.18619e-42 | 0.224684 | 0.553923 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 3.32233e-27 | 0.0287605 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 1.94334e-08 | 0.17999 | 0.514753 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 7.73781e-37 | 0.302666 | 0.639143 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 3.40651e-21 | 0.0437414 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 0.0202634 | 0.538672 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 2.51192e-28 | 0.154303 | 0.495852 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_Log1p` | 5.26382e-27 | 0.110314 | 0.445574 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.0123121 | 0.735395 | 0.902801 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 1.58398e-24 | 0.101509 | 0.437775 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 1.87851e-07 | 0.0424822 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 9.92451e-15 | 0.851749 | 0.944509 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_MOM_21_Slope_W21` | 0.585266 | 0.55151 | 0.822311 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 1.62491e-16 | 0.547704 | 0.820824 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 0.399822 | 0.0985592 | 0.437376 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 1.81652e-40 | 0.0770465 | 0.392868 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 2.64772e-11 | 0.348952 | 0.701941 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_144_Lag_34` | 2.40152e-50 | 0.371352 | 0.727714 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_233_Mean_W8` | 1.59443e-11 | 0.114554 | 0.445574 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_89_Min_W13` | 1.51897e-18 | 0.674709 | 0.88697 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR100_55_Range_W13` | 2.70363e-19 | 0.272992 | 0.593669 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 4.40134e-08 | 0.0401847 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 0.0777036 | 0.168476 | 0.502765 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_21_Range_W3` | 0.940291 | 0.0695599 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 6.31174e-11 | 0.546136 | 0.820824 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_89_Std_W5` | 5.14086e-10 | 0.117956 | 0.447965 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_8_Min_W55` | 3.84956e-30 | 0.00388881 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_21_ZScore_W8` | 4.45588e-40 | 0.783766 | 0.920555 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_34_Momentum_L13` | 0.00106466 | 0.526386 | 0.816637 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_5_Slope_W55` | 5.94447e-05 | 0.0256012 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_89_Skew_W55` | 0.0142434 | 0.407055 | 0.753582 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 2.64632e-111 | 0.00348741 | 0.290702 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_9_Momentum_L21` | 5.72424e-25 | 0.758651 | 0.904788 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_13_Kurt_W21` | 7.49534e-16 | 0.690721 | 0.891597 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_55_Max_W13` | 0.521168 | 0.178341 | 0.514753 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_6_Min_W13` | 0.00563327 | 0.737832 | 0.902801 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 2.11134e-14 | 0.825069 | 0.940239 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Lag_21` | 1.04691e-38 | 0.433622 | 0.765901 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 1.38265e-73 | 0.0339937 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_55-8-5-0_Lag_34` | 9.97229e-40 | 0.61168 | 0.867854 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 5.6521e-132 | 0.0669228 | 0.388073 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 3.47013e-87 | 0.0441346 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_34_Lag_8` | 2.38691e-08 | 0.0776024 | 0.392868 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 9.68779e-30 | 0.0555046 | 0.366053 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Max_W233` | 7.08395e-42 | 0.0436178 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.0163665 | 0.148067 | 0.491986 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Range_W144` | 1.01439e-23 | 0.645767 | 0.881971 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_89_Min_W5` | 2.53909e-39 | 0.576665 | 0.839706 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 5.97007e-26 | 0.523541 | 0.816634 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 1.14601e-10 | 0.425275 | 0.764239 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_55_Max_W144` | 5.16161e-41 | 0.0457402 | 0.33498 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 2.2413e-17 | 0.523006 | 0.816634 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 4.20696e-08 | 0.0418692 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_21_Slope_W5` | 0.00228712 | 0.870541 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W8` | 1.11225e-85 | 0.0218648 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 8.89461e-35 | 0.00716992 | 0.290702 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 4.03379e-11 | 0.0686585 | 0.388073 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 4.80815e-18 | 0.165905 | 0.502765 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 2.94631e-77 | 0.0412557 | 0.328045 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 5.9575e-77 | 0.0681947 | 0.388073 | True | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 8.7023e-11 | 0.09692 | 0.43483 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 6.05759e-05 | 0.0809183 | 0.402973 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 2.23288e-12 | 0.206296 | 0.529564 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_5_Rank_W34` | 3.41624e-13 | 0.393647 | 0.742562 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_144_Std_W34` | 0.388664 | 0.224551 | 0.553923 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 7.08564e-25 | 0.669468 | 0.886689 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_34_Range_W21` | 0.000387882 | 0.774179 | 0.912207 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 3.4088e-32 | 0.481376 | 0.793792 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_13_Range_W89` | 3.46041e-31 | 0.279568 | 0.602705 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_144_Kurt_W89` | 1.5639e-17 | 0.748133 | 0.903247 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_34_Kurt_W5` | 0.0159413 | 0.433703 | 0.765901 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_34_Lag_5` | 1.16628e-22 | 0.558655 | 0.82446 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_89_Momentum_L13` | 5.14037e-14 | 0.0282179 | 0.328045 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_13_Kurt_W8` | 2.17296e-09 | 0.867778 | 0.944509 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_20_Mean_W21` | 3.53431e-10 | 0.202999 | 0.528021 | False | False | removed:p_value |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.0607635 | 0.815713 | 0.940239 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_34_Kurt_W8` | 6.34936e-30 | 0.695819 | 0.893088 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_55_Min_W144` | 1.74308e-08 | 0.203458 | 0.528021 | False | False | removed:icir |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_55_Slope_W3` | 2.34199e-18 | 0.841528 | 0.944509 | False | False | removed:ic_mean |
| `long_BTCUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_89_Mean_W34` | 2.27998e-44 | 0.392133 | 0.742517 | True | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `close-volume_1h_volume_OBV_Momentum_L233` | 0 | 0.131983 | 0.740845 | True | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 0.182458 | 0.240234 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 2.62765e-109 | 0.939057 | 0.976788 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_CMO_89_Slope_W5` | 5.7668e-118 | 0.386299 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_CMO_8_Rank_W3` | 0.0644391 | 0.846274 | 0.928695 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 4.72292e-157 | 0.424071 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 1.36606e-243 | 0.0289702 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 1.71648e-15 | 0.477795 | 0.80809 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 4.01064e-92 | 0.769294 | 0.913995 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 7.50736e-07 | 0.0717109 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 5.27256e-23 | 0.0527516 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.0116249 | 0.193363 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 0.0911686 | 0.285233 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 1.98916e-07 | 0.530822 | 0.81839 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 0.934344 | 0.444228 | 0.78886 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 0.0603704 | 0.229332 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 8.4029e-55 | 0.253098 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 1.86933e-83 | 0.815274 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 3.61963e-10 | 0.650542 | 0.870296 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 3.91059e-243 | 0.398726 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 1.9977e-06 | 0.0147797 | 0.555489 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MOM_13_Min_W144` | 2.02909e-08 | 0.676468 | 0.875069 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_MOM_21` | 8.44388e-193 | 0.625428 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 1.01823e-10 | 0.157218 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCP_89_Kurt_W13` | 6.94672e-54 | 0.308048 | 0.768177 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 2.96266e-263 | 0.260597 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.26005e-70 | 0.0861823 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR_5_Skew_W13` | 0.00136481 | 0.0332115 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_55_Range_W89` | 1.89026e-08 | 0.372098 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_55_Std_W144` | 8.50806e-07 | 0.624806 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_89_Slope_W233` | 6.21329e-06 | 0.381501 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_RSI_8_Rank_W55` | 1.86347e-188 | 0.455077 | 0.802415 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 9.80533e-51 | 0.234398 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 7.37019e-238 | 0.0293353 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 2.73534e-07 | 0.0695741 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_momentum_TRIX_21_Kurt_W5` | 0.699756 | 0.552621 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 1.81026e-10 | 0.470288 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 1.03842e-269 | 0.183942 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 8.17786e-22 | 0.0764914 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG_5_Std_W8` | 0.03825 | 0.0832762 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 0.00965667 | 0.251645 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_55_Kurt_W13` | 5.20729e-06 | 0.351294 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_89_Momentum_L8` | 0.000174521 | 0.634518 | 0.853436 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_89_Range_W233` | 0.245538 | 0.707904 | 0.886808 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_144_Log1p` | 0.496724 | 0.31915 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 3.92838e-06 | 0.244775 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_55_TsRank_W5` | 0.889247 | 0.496891 | 0.812947 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 1.57565e-07 | 0.39542 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_DEMA_13_Slope_W55` | 8.05384e-11 | 0.876263 | 0.942909 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_EMA_21_Mean_W34` | 0.45959 | 0.175649 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_EMA_55_ZScore_W8` | 1.74192e-150 | 0.291991 | 0.751048 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_KAMA_8_Lag_5` | 2.6574e-24 | 0.33906 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_MA_21_Rank_W13` | 8.8353e-20 | 0.911618 | 0.959522 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 0.367247 | 0.22611 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 3.04101e-24 | 0.998734 | 0.998734 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_20_Kurt_W233` | 0.724371 | 0.285181 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_55_Mean_W34` | 0.37725 | 0.284689 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_55_Mean_W55` | 0.0859795 | 0.410164 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_89_Min_W55` | 0.583105 | 0.364565 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_TEMA_13_Slope_W144` | 0.292077 | 0.25835 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_TEMA_8_Rank_W3` | 4.77495e-29 | 0.729078 | 0.896083 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_12h_trend_TRIMA_34_Std_W8` | 1.05577e-07 | 0.683896 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_13_Std_W8` | 1.57532e-24 | 0.0293884 | 0.613797 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_8_Lag_13` | 0.043511 | 0.716975 | 0.892196 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_8_ZScore_W13` | 7.45419e-207 | 0.230064 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Hist_8-34-9_Rank_W144` | 2.89904e-239 | 0.307128 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_21-89-13_Min_W144` | 1.86452e-260 | 0.531379 | 0.81839 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_34-144-21_Log1p` | 0 | 0.156159 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_55-144-21_Max_W34` | 0 | 0.243612 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_8-21-5_Mean_W34` | 3.35866e-164 | 0.473121 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Signal_13-55-13_DecayLinear_W21` | 3.90263e-195 | 0.164913 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Signal_34-89-13_Kurt_W34` | 6.48513e-25 | 0.803869 | 0.927269 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_12-26-9_TsRank_W21` | 9.02454e-116 | 0.1693 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_55-144-21_Max_W34` | 5.94487e-104 | 0.00502152 | 0.555194 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_8-34-9_Range_W5` | 5.45801e-05 | 0.591613 | 0.835908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Line_34-89-13_Mean_W21` | 1.33038e-268 | 0.0751622 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Signal_12-26-9_Rank_W34` | 2.59263e-05 | 0.958588 | 0.982208 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Signal_8-21-5_Slope_W144` | 1.54146e-22 | 0.0826098 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Line_13_Range_W3` | 1.62377e-87 | 0.0460058 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_13_DecayLinear_W5` | 1.12264e-164 | 0.442521 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_3_Slope_W8` | 3.57061e-193 | 0.150789 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_9_Max_W144` | 8.02923e-115 | 0.371463 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MOM_144_Min_W144` | 3.60586e-104 | 0.462915 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_MOM_21_Momentum_L8` | 2.9848e-34 | 0.105419 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_21-55-0_Min_W34` | 1.09126e-222 | 0.219316 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_34-89-0_Std_W21` | 1.37308e-57 | 0.754947 | 0.905391 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_55-144-0_Range_W5` | 0.954073 | 0.907572 | 0.959488 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_233_Sign` | 0 | 0.158145 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_55_ZScore_W5` | 1.6891e-55 | 0.491694 | 0.810294 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_9_Range_W55` | 0.378933 | 0.522542 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_13_144_Cross` | 6.87541e-308 | 0.272374 | 0.741309 | False | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_13_Slope_W13` | 5.40946e-134 | 0.258369 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_144_Slope_W34` | 4.56041e-114 | 0.0328751 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_233_Range_W5` | 1.08017e-30 | 0.827243 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR_12_Std_W233` | 0.000887976 | 0.704756 | 0.886808 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_14_55_Cross` | 1.44725e-271 | 0.382659 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_233_Slope_W89` | 0 | 0.0166981 | 0.555489 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_9_Momentum_L55` | 4.357e-128 | 0.554661 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_STOCHRSI-fastd_21-5-3-0_Kurt_W21` | 0.00217777 | 0.588751 | 0.835908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_momentum_TRIX_89_ZScore_W233` | 7.84454e-139 | 0.554762 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-INTERCEPT_55_TsRank_W21` | 5.75926e-17 | 0.290571 | 0.751048 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_10_Momentum_L21` | 9.64135e-09 | 0.277762 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_144_Mean_W13` | 1.01531e-286 | 0.273701 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_144_Std_W55` | 0.00098107 | 0.354887 | 0.773313 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_89_Lag_2` | 0 | 0.0604362 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_8_Momentum_L5` | 0.177078 | 0.830144 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_10_Max_W144` | 1.81873e-101 | 0.106686 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_10_Range_W13` | 0.0242807 | 0.85451 | 0.933028 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_8_Mean_W55` | 0 | 0.0300192 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_STDDEV_5_Skew_W144` | 1.70797e-90 | 0.560255 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_TSF_13_Range_W144` | 0.264649 | 0.0321307 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_VAR_34_Momentum_L233` | 0.0866827 | 0.751533 | 0.905391 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_statistics_VAR_89_Std_W3` | 0.908401 | 0.189074 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_BBANDS-Lower_13_Kurt_W144` | 5.0267e-50 | 0.169124 | 0.740845 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_BBANDS-Upper_13_Max_W89` | 4.69982e-63 | 0.103626 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_DEMA_21_Momentum_L8` | 0 | 0.0792358 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_EMA_100_Rank_W144` | 0 | 0.312351 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_KAMA_5_TsArgmax_W21` | 7.64248e-144 | 0.573129 | 0.830067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_KAMA_8_ZScore_W34` | 8.76902e-252 | 0.250366 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_55_ZScore_W34` | 1.71191e-135 | 0.732835 | 0.89766 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_5_Std_W21` | 0.0142571 | 0.618915 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_89_Skew_W13` | 1.02847e-116 | 0.100481 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_MA_55_DecayLinear_W13` | 2.74097e-281 | 0.0351545 | 0.626504 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_MIDPOINT_21_Std_W89` | 0.000218797 | 0.0855075 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_MIDPOINT_55_Rank_W144` | 0 | 0.0442284 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_SMA_200_Max_W5` | 0.000146538 | 0.172669 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_T3_8_Log1p` | 6.44886e-28 | 0.205035 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_TEMA_55_Skew_W5` | 6.50814e-47 | 0.628699 | 0.850191 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_21_ZScore_W233` | 0 | 0.366467 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_233_Range_W13` | 0.213496 | 0.280118 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_34_TsRank_W5` | 1.40854e-30 | 0.581928 | 0.835835 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_12h_perm_21_Mean_W34` | 1.55973e-08 | 0.259607 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 0.00357066 | 0.349242 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 1.81124e-22 | 0.683921 | 0.875069 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_12h_shannon_volume_21_Max_W89` | 3.69597e-07 | 0.525538 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_1h_apen_55_Momentum_L21` | 2.22093e-11 | 0.992869 | 0.998734 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_1h_hurst_55_Min_W144` | 0.487442 | 0.13238 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ent_1h_shannon_close_return_21_ZScore_W3` | 4.74435e-49 | 0.437541 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 0.0225646 | 0.981478 | 0.993423 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 1.80941e-06 | 0.722441 | 0.895338 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.000144602 | 0.535499 | 0.822197 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 1.29253e-69 | 0.478586 | 0.80809 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 1.22811e-38 | 0.612703 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 1.07619e-98 | 0.2659 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_statistics_BETA_144_Slope_W233` | 2.18301e-05 | 0.683107 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_statistics_BETA_34_ZScore_W8` | 2.58208e-29 | 0.252358 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_21_Slope_W89` | 0.162439 | 0.0644197 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 2.81672e-47 | 0.0962005 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_8_Skew_W3` | 1.16917e-05 | 0.175764 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 1.3554e-06 | 0.631551 | 0.85174 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 1.77114e-164 | 0.284813 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroondown_233_Slope_W233` | 1.85382e-94 | 0.551339 | 0.824553 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroondown_34_ZScore_W8` | 4.60526e-52 | 0.0396305 | 0.646969 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroonup_89_DecayLinear_W13` | 1.97585e-164 | 0.0111574 | 0.555489 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROONOSC_144_Std_W13` | 9.06674e-07 | 0.586223 | 0.835908 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_momentum_MINUS-DM_21_Max_W13` | 7.26619e-213 | 0.939596 | 0.976788 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_momentum_PLUS-DM_8_Max_W144` | 1.57441e-119 | 0.461677 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_13_ZScore_W13` | 0.194545 | 0.750487 | 0.905391 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_21_Range_W21` | 1.90947e-25 | 0.493646 | 0.810294 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_5_21_Cross` | 9.43258e-11 | 0.988 | 0.995984 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_statistics_CORREL_89_Lag_8` | 7.10292e-11 | 0.519914 | 0.816314 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_statistics_CORREL_8_Mean_W55` | 6.85832e-20 | 0.23994 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_trend_MIDPRICE_144_Min_W5` | 1.42135e-119 | 0.155199 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hl_1h_trend_SAR_0.02-0.2_Kurt_W144` | 1.28027e-52 | 0.0868683 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 0.682991 | 0.778817 | 0.91658 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 3.46879e-09 | 0.858695 | 0.933028 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_14_Range_W233` | 2.13534e-29 | 0.127025 | 0.72908 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADX_34_Mean_W34` | 0.999742 | 0.524727 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 8.25456e-79 | 0.884313 | 0.946937 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_34_Range_W3` | 0.00701046 | 0.315063 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_34_Skew_W34` | 1.2361e-09 | 0.262429 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_5_Mean_W13` | 1.37919e-193 | 0.987543 | 0.995984 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_13_Std_W89` | 8.95546e-33 | 0.816209 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 1.94746e-05 | 0.876773 | 0.942909 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_144_Mean_W34` | 0.00288262 | 0.284889 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_34_Momentum_L21` | 5.41712e-07 | 0.336958 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_55_Lag_8` | 2.61954e-96 | 0.41084 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_MINUS-DI_144` | 3.41983e-57 | 0.913128 | 0.959522 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 2.78572e-38 | 0.108233 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 4.45657e-111 | 0.318992 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 1.00746e-98 | 0.678726 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 6.23526e-101 | 0.0701779 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 6.55644e-291 | 0.275873 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 8.71722e-234 | 0.43458 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 0.00833024 | 0.163398 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 4.74383e-31 | 0.710868 | 0.886808 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 2.45233e-82 | 0.0921236 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_14_Rank_W5` | 2.88167e-45 | 0.783283 | 0.917507 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_21_Lag_13` | 2.6056e-06 | 0.613367 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_5_20_Cross` | 3.38486e-08 | 0.0637822 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_12h_volatility_NATR_13_Lag_1` | 6.80938e-06 | 0.797515 | 0.926186 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ADX_144_Rank_W21` | 0.114156 | 0.582907 | 0.835835 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ADX_89_Max_W3` | 0.244589 | 0.231905 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_13_Range_W5` | 3.00635e-23 | 0.198957 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_34_ZScore_W34` | 1.46572e-188 | 0.0904409 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_55_Rank_W8` | 4.90137e-147 | 0.436001 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_DX_144_Std_W144` | 6.87804e-36 | 0.0102175 | 0.555489 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_DX_55_Rank_W8` | 3.00431e-54 | 0.997744 | 0.998734 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_MINUS-DI_21_Momentum_L144` | 9.65654e-280 | 0.0676446 | 0.65864 | True | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_PLUS-DI_144_Max_W5` | 0 | 0.945937 | 0.9793 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_PLUS-DI_21_Min_W8` | 2.6295e-211 | 0.952043 | 0.981549 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowd_13-3-0-3-0_Range_W55` | 0.231021 | 0.441582 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowd_34-5-0-5-0_Mean_W34` | 2.68955e-139 | 0.0756723 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_21-3-0-3-0_TsRank_W21` | 4.38851e-277 | 0.173227 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_21-5-0-5-0_Lag_21` | 0.00256823 | 0.346748 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_34-5-0-3-0_Lag_3` | 1.24536e-142 | 0.186783 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_55-5-0-5-0_Skew_W233` | 3.10981e-192 | 0.467003 | 0.807802 | False | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_21-5-0_Lag_21` | 0.00256823 | 0.346748 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_5-3-0_Slope_W89` | 4.36896e-276 | 0.393652 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_5-3-0_ZScore_W21` | 1.1818e-237 | 0.168484 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastk_21-5-0_Mean_W55` | 0 | 0.00703358 | 0.555194 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ULTOSC_5-10-20_Slope_W3` | 2.08431e-25 | 0.588859 | 0.835908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_momentum_WILLR_21_Skew_W34` | 1.23185e-78 | 0.0861559 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `hlc_1h_volatility_ATR_233_Skew_W55` | 0.151849 | 0.351127 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlcv_12h_momentum_MFI_55_Min_W233` | 6.52896e-06 | 0.17901 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlcv_1h_momentum_MFI_89_Rank_W3` | 1.59791e-45 | 0.231424 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `hlcv_1h_volume_ForceIndex_Rank_W3` | 0.00178156 | 0.165198 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_12h_amihud_illiq_55_Max_W5` | 2.56137e-06 | 0.316461 | 0.768177 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_12h_cs_spread_21_Rank_W8` | 9.40349e-10 | 0.823482 | 0.928203 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_12h_kyle_lambda_21_Momentum_L13` | 8.92185e-38 | 0.881938 | 0.946424 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_12h_ofi_zscore_13_Skew_W13` | 3.51743e-12 | 0.558392 | 0.824553 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_12h_roll_spread_55_Min_W34` | 4.00102e-38 | 0.65784 | 0.874892 | False | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_12h_vpin_50_Kurt_W13` | 2.84352e-28 | 0.446349 | 0.789817 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `ms_1h_kyle_lambda_21_ZScore_W144` | 0.368446 | 0.362514 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 3.96558e-42 | 0.372024 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 1.98357e-121 | 0.698482 | 0.882386 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 0.000180366 | 0.844738 | 0.928695 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 5.68744e-24 | 0.178022 | 0.740845 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.11895e-10 | 0.741052 | 0.899721 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 1.9502e-68 | 0.622625 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 1.07647e-05 | 0.774691 | 0.914439 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 1.51778e-34 | 0.745175 | 0.90253 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 4.41843e-93 | 0.669845 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 1.25418e-20 | 0.431373 | 0.788635 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 0.00902151 | 0.439484 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 0.000252122 | 0.0675929 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 0.000253161 | 0.35781 | 0.776292 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 4.92837e-63 | 0.821145 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 0.888067 | 0.797406 | 0.926186 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 8.97885e-12 | 0.504234 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 1.34728e-12 | 0.687873 | 0.877874 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 0.0261126 | 0.798117 | 0.926186 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 9.84169e-15 | 0.925804 | 0.970538 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 3.37643e-09 | 0.125758 | 0.72908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 4.3238e-16 | 0.552392 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 1.49376e-10 | 0.0971158 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 1.81218e-52 | 0.337207 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 6.12599e-08 | 0.266357 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 2.40756e-71 | 0.55266 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 5.49364e-06 | 0.160937 | 0.740845 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 3.17551e-09 | 0.26953 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 2.77909e-27 | 0.0393836 | 0.646969 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 0.0291244 | 0.284611 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 2.21701e-31 | 0.431627 | 0.788635 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 0.0119405 | 0.524555 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 5.57412e-28 | 0.413324 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 3.88202e-21 | 0.0462335 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 3.52247e-16 | 0.298614 | 0.760247 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 0.816523 | 0.440646 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 2.15049e-17 | 0.198994 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 7.91809e-09 | 0.500274 | 0.815807 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 5.12947e-24 | 0.564123 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 5.05183e-29 | 0.223211 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 1.26725e-08 | 0.735757 | 0.89766 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 2.27738e-06 | 0.84454 | 0.928695 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 1.17658e-46 | 0.490831 | 0.810294 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 5.24673e-31 | 0.33891 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 1.57217e-59 | 0.390431 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 0.0478439 | 0.617962 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 3.75544e-10 | 0.410869 | 0.788635 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.000320858 | 0.424891 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 0.00228904 | 0.335357 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 1.9149e-60 | 0.554807 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 6.9263e-06 | 0.389941 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 5.38009e-05 | 0.163691 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 4.28518e-49 | 0.438928 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 0.910664 | 0.853091 | 0.933028 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 2.97454e-08 | 0.898925 | 0.95439 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 2.24189e-28 | 0.221292 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 3.33595e-09 | 0.350421 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 0.1954 | 0.401343 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 0.232235 | 0.123971 | 0.72908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 1.41955e-37 | 0.765828 | 0.912048 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 0.000213052 | 0.659237 | 0.874892 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 0.00259842 | 0.0881042 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 0.000265544 | 0.179773 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 0.00734266 | 0.834156 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 0.140537 | 0.760769 | 0.908191 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 0.00030815 | 0.621987 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 8.60222e-55 | 0.178264 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 6.62855e-57 | 0.430018 | 0.788635 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 6.05502e-06 | 0.0990434 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 4.29873e-71 | 0.200955 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 3.02205e-47 | 0.474321 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_cycle_HT-PHASOR-InPhase_Kurt_W34` | 5.96265e-14 | 0.821546 | 0.928203 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_APO_5-13-0_Mean_W34` | 0.0822191 | 0.825118 | 0.928203 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_APO_55-233-0_Range_W233` | 7.43446e-48 | 0.734521 | 0.89766 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_CMO_55_Slope_W5` | 0.00940701 | 0.157409 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_13-34-9_Min_W5` | 0.00113845 | 0.863845 | 0.933028 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_13-34-9_Momentum_L8` | 1.23685e-09 | 0.857385 | 0.933028 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_21-55-9_Momentum_L144` | 0.523169 | 0.176119 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_21-55-9_TsArgmax_W13` | 2.63854e-38 | 0.184814 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_5-21-5_Skew_W8` | 5.57721e-55 | 0.596359 | 0.835908 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_55-233-34_Min_W5` | 2.99764e-31 | 0.313513 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Signal_12-26-9_Std_W144` | 0.000468715 | 0.400645 | 0.786326 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Hist_13-34-9_TsRank_W13` | 0.0256824 | 0.697271 | 0.882386 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Hist_21-89-13_Range_W5` | 2.01766e-06 | 0.724915 | 0.895338 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Line_13-34-9_Std_W13` | 2.66936e-11 | 0.827296 | 0.928203 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Line_55-144-21_Slope_W8` | 2.8434e-27 | 0.0962688 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Signal_21-89-13_Rank_W144` | 0.461105 | 0.696017 | 0.882386 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Signal_34-89-13_Range_W233` | 2.77978e-26 | 0.147124 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Hist_3_Std_W3` | 4.22084e-28 | 0.997917 | 0.998734 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Line_13_Mean_W8` | 2.47406e-14 | 0.958235 | 0.982208 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Line_5_Momentum_L3` | 1.76664e-47 | 0.47202 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MOM_13_Mean_W233` | 5.33139e-05 | 0.00561589 | 0.555194 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MOM_34_Momentum_L55` | 6.79917e-07 | 0.811779 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_21-55-0_Clip` | 4.43016e-09 | 0.507414 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_8-34-0_Mean_W3` | 1.72797e-27 | 0.656881 | 0.874892 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_8-34-0_Rank_W34` | 1.44637e-35 | 0.1924 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_13_Kurt_W144` | 3.85179e-56 | 0.120672 | 0.725485 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_21_Mean_W13` | 2.37336e-31 | 0.492675 | 0.810294 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_8_Lag_21` | 1.98183e-44 | 0.361221 | 0.77689 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCR100_233_Skew_W3` | 3.52645e-11 | 0.775166 | 0.914439 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROC_55_Min_W144` | 0.00404323 | 0.482587 | 0.80809 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_233_Mean_W89` | 3.9743e-57 | 0.673223 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_34_Rank_W5` | 0.720458 | 0.0848984 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_7_Std_W3` | 6.45605e-05 | 0.493123 | 0.810294 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_7_TsArgmax_W13` | 0.979424 | 0.421914 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_8_ZScore_W5` | 0.00453128 | 0.192623 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_STOCHRSI-fastk_14-5-3-0_TsArgmax_W5` | 2.30359e-05 | 0.323826 | 0.769472 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_TRIX_55_Min_W5` | 6.22637e-26 | 0.590923 | 0.835908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_TRIX_8_Skew_W5` | 0.00069497 | 0.127114 | 0.72908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_233_Kurt_W89` | 0.0208018 | 0.892606 | 0.951732 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_89_Kurt_W5` | 5.78129e-14 | 0.515675 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_89_Rank_W5` | 6.15345e-126 | 0.204431 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-SLOPE_21_Kurt_W34` | 1.44485e-15 | 0.605447 | 0.846269 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_55_Min_W3` | 2.30082e-33 | 0.262447 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_55_Slope_W8` | 7.81296e-68 | 0.303029 | 0.763694 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_8_Lag_13` | 1.89141e-05 | 0.565125 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_STDDEV_89_Clip` | 6.8515e-21 | 0.663346 | 0.875069 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_STDDEV_8_Lag_34` | 6.10083e-60 | 0.231173 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_VAR_13_Mean_W89` | 1.36614e-06 | 0.710086 | 0.886808 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_VAR_89_Mean_W5` | 0.726428 | 0.772219 | 0.914439 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_BBANDS-Lower_20_Std_W89` | 6.40726e-16 | 0.517918 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_BBANDS-Middle_21_Max_W233` | 1.7643e-48 | 0.835237 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_EMA_144_Std_W55` | 0.287763 | 0.249635 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_EMA_55_ZScore_W89` | 8.00253e-24 | 0.482009 | 0.80809 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_KAMA_21_Lag_3` | 8.24741e-28 | 0.668791 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_KAMA_34_Skew_W55` | 0.000306555 | 0.551553 | 0.824553 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MA_5_Rank_W13` | 4.32864e-34 | 0.50767 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MIDPOINT_13_Mean_W233` | 1.80493e-09 | 0.594949 | 0.835908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MIDPOINT_89_Mean_W233` | 2.57486e-08 | 0.726629 | 0.895338 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_10_Max_W21` | 0.937446 | 0.565076 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_13_Range_W13` | 3.04038e-25 | 0.314704 | 0.768177 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_144_ZScore_W8` | 0.0175284 | 0.395751 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_50_ZScore_W8` | 4.41535e-32 | 0.837243 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_5_Lag_34` | 6.77221e-11 | 0.19449 | 0.740845 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_5_Skew_W144` | 2.3451e-79 | 0.577075 | 0.832255 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TEMA_13_Kurt_W55` | 1.58361e-33 | 0.836716 | 0.928203 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TEMA_55_Distance` | 2.35175e-11 | 0.0843163 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TRIMA_55_Momentum_L3` | 7.73613e-07 | 0.508533 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TRIMA_5_Momentum_L21` | 1.28744e-119 | 0.296287 | 0.758191 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_WMA_89_Min_W233` | 7.77655e-24 | 0.594397 | 0.835908 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 8.55808e-39 | 0.860933 | 0.933028 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 5.07932e-39 | 0.234107 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `taker_1h_ratio_trend_SMA_8_50_Ratio` | 1.73053e-15 | 0.823786 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `tr_12h_rsj_21_Max_W21` | 0.00808898 | 0.838917 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `tr_12h_ud_vol_ratio_21_Max_W13` | 7.9359e-07 | 0.573894 | 0.830067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `tr_1h_cvar_5pct_55_TsArgmin_W21` | 9.49419e-65 | 0.0553521 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `tr_1h_gpr_100_Lag_2` | 0 | 0.0136804 | 0.555489 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `tr_1h_gpr_55_Kurt_W5` | 0.885786 | 0.846806 | 0.928695 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `tr_1h_rsj_21_Rank_W13` | 2.18478e-230 | 0.155662 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 1.46537e-06 | 0.620983 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 1.89746e-30 | 0.741024 | 0.899721 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 0.0115379 | 0.526593 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.305745 | 0.338758 | 0.772229 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 0.292277 | 0.888838 | 0.949744 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_CMO_14_Max_W144` | 6.40482e-70 | 0.518902 | 0.816314 | False | False | removed:p_value |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_CMO_14_Rank_W13` | 0.336247 | 0.903607 | 0.957325 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 0.000317171 | 0.10591 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 0.000240713 | 0.975069 | 0.988942 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 2.6282e-46 | 0.0976892 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 6.07399e-07 | 0.781644 | 0.917507 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 0.000645605 | 0.93636 | 0.976788 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 0.748787 | 0.52676 | 0.816314 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 3.30693e-09 | 0.690546 | 0.879037 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 0.00818846 | 0.894922 | 0.952167 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 2.62038e-08 | 0.353143 | 0.772888 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 3.65823e-06 | 0.0510907 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 2.00414e-16 | 0.945921 | 0.9793 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 0.368202 | 0.150064 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 5.31079e-07 | 0.56868 | 0.827321 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 0.467979 | 0.160754 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCP_89_Min_W13` | 0.229994 | 0.435404 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR100_55_Range_W13` | 2.75303e-67 | 0.710182 | 0.886808 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 0.0429578 | 0.207859 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 4.16059e-11 | 0.187073 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 0.738638 | 0.32064 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROC_5_Slope_W55` | 0.375573 | 0.219557 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_RSI_13_Kurt_W21` | 2.85978e-43 | 0.794339 | 0.926186 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_RSI_6_Min_W13` | 5.18954e-70 | 0.391357 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 8.34494e-19 | 0.968376 | 0.986162 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 5.95021e-13 | 0.972103 | 0.987942 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_5_Max_W233` | 1.39017e-33 | 0.470542 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.0162011 | 0.229618 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_89_Min_W5` | 0.181502 | 0.756609 | 0.905391 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.390446 | 0.726677 | 0.895338 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 0.436204 | 0.548563 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_13_Range_W89` | 1.59909e-14 | 0.19962 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_144_Kurt_W89` | 0.669953 | 0.96667 | 0.986162 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_34_Kurt_W5` | 1.77554e-67 | 0.955613 | 0.982208 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_34_Lag_5` | 1.58509e-14 | 0.441133 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_13_Kurt_W8` | 0.146615 | 0.440064 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.930729 | 0.671577 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_34_Kurt_W8` | 0.00444894 | 0.967874 | 0.986162 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 3.97451e-45 | 0.913372 | 0.959522 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_233_Lag_2` | 7.55842e-06 | 0.55871 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_233_Min_W144` | 0.56435 | 0.385562 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_89_Std_W233` | 0.00068707 | 0.484579 | 0.808712 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_8_Mean_W34` | 0.00171583 | 0.618924 | 0.848067 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_13_Rank_W144` | 0.00139872 | 0.0516665 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_200_Slope_W144` | 0.00590209 | 0.433876 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_21_Range_W13` | 0.00992227 | 0.181719 | 0.740845 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_KAMA_8_Lag_21` | 1.54134e-13 | 0.515655 | 0.816314 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_MAVP_55_Range_W5` | 7.1435e-22 | 0.369631 | 0.77689 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_MA_233_Mean_W89` | 4.22548e-13 | 0.683245 | 0.875069 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_MIDPOINT_8_Abs` | 0.745135 | 0.0694416 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_SMA_50_ZScore_W233` | 0.823088 | 0.802209 | 0.927269 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_T3_21_Min_W55` | 0.00031056 | 0.804624 | 0.927269 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_T3_8_Std_W5` | 5.13867e-16 | 0.677148 | 0.875069 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_TRIMA_55_Skew_W34` | 0.0175488 | 0.754951 | 0.905391 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_12h_trend_WMA_89_Max_W233` | 0.00445402 | 0.265557 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_CMO_34_Max_W8` | 1.00902e-35 | 0.0301035 | 0.613797 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Hist_55-233-34_Kurt_W8` | 1.96643e-44 | 0.4019 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Hist_55-233-34_Min_W89` | 0.0509593 | 0.862307 | 0.933028 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Line_21-89-13_Rank_W13` | 4.08929e-58 | 0.0064439 | 0.555194 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Line_55-233-34_Range_W233` | 1.39858e-50 | 0.268819 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_21-55-9_Lag_2` | 9.65158e-15 | 0.511023 | 0.816314 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_21-89-13_TsArgmin_W5` | 1.22255e-56 | 0.024705 | 0.613797 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_55-233-34_Skew_W13` | 9.04181e-134 | 0.0157234 | 0.555489 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_34-144-21_TsArgmin_W13` | 0.79596 | 0.932189 | 0.975183 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_8-21-5_Min_W21` | 6.11403e-07 | 0.0146629 | 0.555489 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_8-34-9_Kurt_W8` | 0.0681545 | 0.363477 | 0.77689 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Line_34-144-21_Slope_W3` | 6.27662e-10 | 0.403406 | 0.786326 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Line_55-144-21_Min_W13` | 0.0435018 | 0.814845 | 0.928203 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Signal_34-144-21_ZScore_W144` | 0.012611 | 0.433036 | 0.788635 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_13_Lag_5` | 2.25907e-21 | 0.27739 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_21_Mean_W89` | 5.40017e-78 | 0.0230698 | 0.613797 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_8_Std_W5` | 1.35689e-58 | 0.219767 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_8_Std_W55` | 2.01795e-33 | 0.480066 | 0.80809 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_9_Max_W21` | 0.00243985 | 0.343454 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_9_Max_W233` | 1.94412e-102 | 0.401283 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_144_Std_W13` | 3.26571e-36 | 0.644367 | 0.864352 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_21_Clip` | 4.88631e-44 | 0.012202 | 0.555489 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_21_Min_W55` | 1.88937e-06 | 0.246206 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_34_ZScore_W55` | 7.64904e-18 | 0.54353 | 0.824553 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_PPO_34-89-0_Kurt_W5` | 4.88952e-47 | 0.828341 | 0.928203 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCP_21_TsArgmax_W5` | 1.30766e-16 | 0.15433 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCR100_8_Lag_2` | 3.94634e-54 | 0.0401924 | 0.646969 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCR100_8_Slope_W233` | 0.00217412 | 0.0656642 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROC_34_ZScore_W55` | 1.15689e-13 | 0.662291 | 0.875069 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_14_Skew_W5` | 6.93644e-85 | 0.236613 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_233_Rank_W21` | 8.15073e-34 | 0.00778829 | 0.555194 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_34_Kurt_W34` | 0.128194 | 0.321741 | 0.768177 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_34_Rank_W34` | 2.1947e-36 | 0.0179652 | 0.560289 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_8_Lag_1` | 6.16792e-63 | 0.00407322 | 0.555194 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_9_TsArgmax_W13` | 1.87203e-06 | 0.950034 | 0.981505 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_STOCHRSI-fastd_9-5-3-0_Mean_W89` | 1.26561e-106 | 0.228448 | 0.741309 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_momentum_STOCHRSI-fastk_21-8-5-0_Std_W21` | 0.210715 | 0.0939924 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_statistics_LINEARREG-SLOPE_89_Mean_W21` | 2.21915e-12 | 0.342274 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_statistics_LINEARREG-SLOPE_8_Slope_W34` | 3.66303e-82 | 0.00129179 | 0.555194 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_statistics_STDDEV_55_Std_W8` | 2.10958e-38 | 0.620935 | 0.848067 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_statistics_TSF_5_Skew_W144` | 8.15251e-24 | 0.471488 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_statistics_VAR_55_ZScore_W55` | 0.148744 | 0.232412 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_statistics_VAR_8_Std_W3` | 4.84529e-16 | 0.424864 | 0.788635 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_144_Max_W55` | 0.00395316 | 0.301191 | 0.762916 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_21_Mean_W3` | 9.78148e-09 | 0.329916 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_55_Range_W55` | 0.721225 | 0.265433 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_89_Max_W13` | 0.0809528 | 0.0502105 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_89_Mean_W55` | 0.235295 | 0.0852434 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Upper_55_Momentum_L3` | 1.77695e-05 | 0.468298 | 0.807802 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Upper_55_ZScore_W5` | 0.171971 | 0.259605 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_13_Max_W34` | 0.827159 | 0.230549 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_34_Momentum_L34` | 0.024047 | 0.681464 | 0.875069 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_5_Std_W89` | 8.68037e-11 | 0.080513 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_EMA_13_Max_W144` | 3.51306e-05 | 0.222907 | 0.741309 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_HT-TRENDLINE_Lag_13` | 1.89586e-13 | 0.0659124 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_KAMA_233_Range_W144` | 0.627774 | 0.186928 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_KAMA_5_55_Ratio` | 5.79337e-48 | 0.10783 | 0.65864 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_MAVP_233_Momentum_L144` | 0.0157212 | 0.0642485 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_MA_13_Max_W144` | 5.39353e-08 | 0.151685 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_MA_89_Range_W3` | 4.26661e-17 | 0.557051 | 0.824553 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_50_Rank_W13` | 1.00147e-14 | 0.342218 | 0.772229 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_55_Max_W144` | 0.13755 | 0.18124 | 0.740845 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_5_TsArgmin_W13` | 7.2759e-16 | 0.387162 | 0.786326 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_T3_5_21_Cross` | 3.66124e-37 | 0.0326409 | 0.613797 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_TEMA_5_Momentum_L144` | 1.63823e-113 | 0.138751 | 0.740845 | False | False | removed:icir |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_TRIMA_144_Mean_W13` | 2.34781e-05 | 0.0995003 | 0.65864 | False | False | removed:ic_mean |
| `long_BTCUSDT_1h_4a8a0b37` | `volume_1h_trend_WMA_55_Max_W3` | 4.26507e-09 | 0.341493 | 0.772229 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 2.63526e-51 | 0.0298881 | 0.379436 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 1.87932e-05 | 0.157708 | 0.505229 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 0.00237857 | 0.339866 | 0.700798 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 2.25812e-72 | 0.882525 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 1.13616e-47 | 0.685457 | 0.900537 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` | 1.47677e-09 | 0.950507 | 0.98385 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` | 8.74056e-40 | 0.322336 | 0.678144 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` | 1.92196e-30 | 0.2652 | 0.633004 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` | 0.763399 | 0.285888 | 0.65098 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 7.56074e-08 | 0.309474 | 0.663613 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 4.16493e-58 | 0.0626854 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 3.74183e-38 | 0.299364 | 0.656343 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 1.15035e-47 | 0.479177 | 0.795119 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 0.963393 | 0.0611378 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 6.46315e-52 | 0.899795 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 1.46092e-09 | 0.141847 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 2.64658e-19 | 0.80783 | 0.949557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.761576 | 0.130831 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 2.26019e-24 | 0.770014 | 0.92349 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 2.63776e-30 | 0.267663 | 0.633004 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 2.14875e-19 | 0.360579 | 0.718268 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 0.0690068 | 0.0853458 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 1.74742e-43 | 0.447139 | 0.782818 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 3.91767e-27 | 0.916887 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 4.3968e-29 | 0.427172 | 0.777952 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 1.72336e-40 | 0.957558 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 5.36643e-38 | 0.0213625 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 1.00622e-55 | 0.319075 | 0.674655 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.1409e-22 | 0.126704 | 0.47898 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 3.59992e-16 | 0.990619 | 0.992608 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 1.00622e-55 | 0.319075 | 0.674655 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.119808 | 0.210284 | 0.592834 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 9.01853e-84 | 0.754275 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 1.42715e-35 | 0.00685375 | 0.263078 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 6.69513e-16 | 0.129836 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` | 2.87735e-19 | 0.135377 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_MOM_21` | 8.62164e-77 | 0.94211 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.496023 | 0.363614 | 0.718268 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 1.67661e-16 | 0.491227 | 0.808985 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 0.437189 | 0.138372 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` | 0.000114963 | 0.428736 | 0.777961 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` | 1.61344e-17 | 0.167631 | 0.522799 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` | 6.57591e-05 | 0.938682 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` | 3.63901e-149 | 0.120895 | 0.475932 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 7.42121e-136 | 0.226085 | 0.609819 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 7.16022e-109 | 0.894844 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` | 1.13927e-35 | 0.305922 | 0.660844 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 3.63528e-09 | 0.128383 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.73197e-37 | 0.0646226 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` | 2.92993e-45 | 0.993005 | 0.993005 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` | 9.14893e-12 | 0.958218 | 0.98385 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` | 2.57494e-107 | 0.180117 | 0.544719 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` | 0.159668 | 0.496536 | 0.809711 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` | 5.92606e-19 | 0.257979 | 0.628294 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` | 1.25736e-16 | 0.267545 | 0.633004 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` | 1.28632e-45 | 0.94801 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 2.50143e-10 | 0.760513 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` | 3.83865e-54 | 0.285681 | 0.65098 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 6.16964e-29 | 0.176949 | 0.538399 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.83947e-62 | 0.0449194 | 0.392357 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 1.38022e-38 | 0.324888 | 0.678144 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 0.0161104 | 0.407081 | 0.75796 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 3.05219e-15 | 0.138179 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` | 2.24847e-53 | 0.392158 | 0.744056 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 2.93069e-10 | 0.326162 | 0.678144 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 8.46985e-16 | 0.123212 | 0.475932 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 1.81837e-67 | 0.300999 | 0.656343 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 0.0606434 | 0.453561 | 0.782818 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 1.16216e-103 | 0.0367401 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` | 1.6353e-16 | 0.0365925 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 0.020259 | 0.439382 | 0.780254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` | 0.0254382 | 0.803489 | 0.949557 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` | 0.0629953 | 0.280977 | 0.65098 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` | 9.95103e-33 | 0.718135 | 0.907214 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` | 9.43879e-38 | 0.416895 | 0.766259 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` | 4.39601e-05 | 0.208551 | 0.59129 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 0.0178376 | 0.81788 | 0.94966 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` | 2.4599e-27 | 0.0517548 | 0.397318 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` | 0.216661 | 0.0314662 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` | 6.88422e-06 | 0.636266 | 0.885792 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 3.22708e-28 | 0.282374 | 0.65098 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` | 0.0532753 | 0.0390149 | 0.389369 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` | 0.721405 | 0.098746 | 0.434388 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` | 0.605143 | 0.244174 | 0.614753 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` | 0.242414 | 0.253959 | 0.628294 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` | 0.00247758 | 0.908594 | 0.983235 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` | 1.95595e-12 | 0.0783073 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` | 3.65609e-36 | 0.912263 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` | 0.586628 | 0.243167 | 0.614753 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` | 0.498494 | 0.242057 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` | 8.75932e-49 | 0.00367817 | 0.229426 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` | 2.03737e-22 | 0.0435749 | 0.392357 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` | 4.11962e-94 | 0.399824 | 0.749638 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` | 1.08158e-26 | 0.76283 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` | 1.16703e-27 | 0.0651261 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` | 1.26162e-35 | 0.295686 | 0.656343 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` | 2.52086e-30 | 0.0778992 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` | 3.01606e-17 | 0.0434457 | 0.392357 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` | 1.84688e-06 | 0.544108 | 0.835414 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` | 2.9121e-43 | 0.635616 | 0.885792 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` | 6.82393e-16 | 0.0445156 | 0.392357 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 4.78641e-27 | 0.0629695 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 2.66046e-13 | 0.806283 | 0.949557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` | 0.732457 | 0.242892 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` | 0.142183 | 0.142583 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` | 2.4162e-28 | 0.0542491 | 0.404034 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` | 6.68137e-15 | 0.0918174 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` | 2.74383e-07 | 0.133032 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` | 1.10589e-124 | 0.246247 | 0.614753 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` | 4.38215e-08 | 0.0699355 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` | 9.28719e-13 | 0.19962 | 0.572473 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` | 0.997116 | 0.0863773 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` | 2.88918e-26 | 0.0112148 | 0.294536 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` | 0.13142 | 0.257946 | 0.628294 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` | 9.38766e-106 | 0.85626 | 0.973289 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` | 8.80668e-08 | 0.108682 | 0.450045 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` | 1.36728e-32 | 0.0153351 | 0.318843 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` | 6.24408e-32 | 0.401109 | 0.749638 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` | 0.00018576 | 0.191305 | 0.558253 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` | 1.18864e-11 | 0.124944 | 0.475932 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_apen_55_Max_W8` | 1.52579e-08 | 0.705612 | 0.902822 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` | 0.894617 | 0.301207 | 0.656343 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` | 1.54929e-42 | 0.208345 | 0.59129 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_perm_55_Min_W233` | 3.45019e-115 | 0.0611246 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` | 4.17081e-37 | 0.0237716 | 0.336376 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 3.50275e-70 | 0.240951 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 1.16249e-11 | 0.274687 | 0.643517 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 3.11127e-10 | 0.600744 | 0.860797 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` | 0.444756 | 0.36787 | 0.721097 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` | 0.0670867 | 0.197737 | 0.572473 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 8.25089e-71 | 0.936058 | 0.98385 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 2.42634e-16 | 0.157947 | 0.505229 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 9.19271e-19 | 0.0512932 | 0.397318 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 0.0152891 | 0.237239 | 0.614753 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 0.845293 | 0.290166 | 0.652219 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 7.49715e-34 | 0.182487 | 0.545274 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 1.27436e-47 | 0.172916 | 0.530305 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 1.70327e-64 | 0.381799 | 0.736219 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.0183476 | 0.584705 | 0.850635 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 1.25218e-22 | 0.647724 | 0.887952 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 0.000493279 | 0.0889357 | 0.418557 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 3.64844e-116 | 0.269231 | 0.633709 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 4.34972e-42 | 0.363722 | 0.718268 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 9.368e-53 | 0.14191 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 1.4162e-26 | 0.817912 | 0.94966 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 1.37594e-129 | 0.18484 | 0.549018 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.00232719 | 0.220603 | 0.604839 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` | 7.67147e-29 | 0.0912013 | 0.418557 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` | 0.00105367 | 0.0427847 | 0.392357 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` | 6.408e-05 | 0.0916241 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` | 8.07624e-45 | 0.0234377 | 0.336376 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` | 0.000200586 | 0.621588 | 0.878353 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 1.85535e-21 | 0.0341913 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` | 1.65968e-13 | 0.951674 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` | 5.56968e-05 | 0.716392 | 0.907214 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 8.83675e-05 | 0.905928 | 0.983235 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` | 1.10918e-15 | 0.136282 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` | 1.88684e-90 | 0.0737352 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 5.77847e-79 | 0.243961 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` | 0.0128663 | 0.456513 | 0.782818 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 4.6118e-06 | 0.950316 | 0.98385 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 0.329947 | 0.810707 | 0.949631 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` | 7.52767e-09 | 0.453922 | 0.782818 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` | 0.112722 | 0.756062 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.15542 | 0.523334 | 0.826404 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` | 2.55648e-20 | 0.446302 | 0.782818 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 1.23352e-10 | 0.472343 | 0.791128 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` | 5.39542e-21 | 0.673004 | 0.897938 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` | 6.82972e-25 | 0.87253 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` | 2.24174e-07 | 0.924792 | 0.983235 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` | 9.51253e-69 | 0.391583 | 0.744056 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` | 8.98127e-36 | 0.665353 | 0.894656 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` | 4.46506e-16 | 0.0868451 | 0.418557 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` | 1.17645e-13 | 0.14305 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 7.9379e-37 | 0.356311 | 0.718268 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` | 4.03633e-19 | 0.0482094 | 0.394368 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 6.11745e-43 | 0.798472 | 0.949557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` | 5.11214e-31 | 0.517241 | 0.820509 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` | 0.055229 | 0.771734 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` | 0.00172945 | 0.336422 | 0.696575 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` | 0.956775 | 0.840259 | 0.965475 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` | 1.99236e-18 | 0.107468 | 0.450045 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` | 1.12948e-99 | 0.234625 | 0.614753 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 1.80858e-19 | 0.456335 | 0.782818 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 3.72428e-29 | 0.246394 | 0.614753 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 5.68607e-102 | 0.513532 | 0.818698 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 1.16403e-46 | 0.0916918 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 1.06331e-05 | 0.637273 | 0.885792 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 4.27702e-126 | 0.0100901 | 0.292209 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.32028e-115 | 0.342039 | 0.702261 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 5.15914e-52 | 0.920609 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 1.02738e-39 | 0.153859 | 0.501801 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 7.54473e-47 | 0.112949 | 0.458223 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 3.61101e-97 | 0.952351 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 4.46279e-101 | 0.0181759 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 9.57223e-13 | 0.562483 | 0.839834 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 5.87022e-62 | 0.0140949 | 0.318843 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 1.15629e-152 | 0.300826 | 0.656343 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 4.09548e-78 | 0.554837 | 0.839563 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 4.88365e-35 | 0.258117 | 0.628294 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 1.80158e-132 | 0.121705 | 0.475932 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 3.89859e-85 | 0.617534 | 0.875424 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 7.11139e-63 | 0.40102 | 0.749638 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 1.46864e-58 | 0.0606676 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 3.06425e-93 | 0.860667 | 0.976074 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` | 2.93087e-23 | 0.0795384 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` | 0.324167 | 0.410847 | 0.759361 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` | 2.84965e-17 | 0.947496 | 0.98385 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` | 2.37061e-42 | 0.000579672 | 0.144628 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` | 2.9805e-35 | 0.00169747 | 0.169407 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` | 0.0403669 | 0.383601 | 0.736219 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 9.49538e-36 | 0.70279 | 0.902822 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` | 3.36807e-36 | 0.478662 | 0.795119 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` | 1.11863e-07 | 0.352205 | 0.717349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 9.78042e-42 | 0.913086 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` | 6.64464e-33 | 0.0712249 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 0.0390357 | 0.438387 | 0.780254 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` | 4.98053e-36 | 0.468625 | 0.790013 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` | 1.67515e-08 | 0.0367963 | 0.379436 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` | 8.93555e-20 | 0.078046 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` | 2.91821e-17 | 0.833707 | 0.963009 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` | 2.85455e-09 | 0.503928 | 0.816429 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` | 0.000853846 | 0.837473 | 0.965125 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` | 0.0007342 | 0.685779 | 0.900537 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` | 1.32487e-33 | 0.25622 | 0.628294 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` | 2.98012e-155 | 0.0762859 | 0.418557 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` | 2.64889e-19 | 0.220594 | 0.604839 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 0.00121513 | 0.300735 | 0.656343 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 1.89689e-16 | 0.148614 | 0.493733 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 3.61978e-05 | 0.917512 | 0.983235 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 0.0406664 | 0.818344 | 0.94966 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 2.51022e-26 | 0.479621 | 0.795119 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 3.33796e-14 | 0.975864 | 0.989748 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 4.19071e-23 | 0.537473 | 0.832819 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.69638e-11 | 0.510452 | 0.818698 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 7.65463e-27 | 0.841646 | 0.965475 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 2.49897e-08 | 0.759066 | 0.92349 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 8.02323e-32 | 0.690174 | 0.90252 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 0.0150534 | 0.88967 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 5.32676e-19 | 0.745484 | 0.923069 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 5.08094e-19 | 0.71078 | 0.905315 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 1.10304e-42 | 0.690907 | 0.90252 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 4.00943e-35 | 0.893732 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 8.94751e-18 | 0.536756 | 0.832819 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 6.58427e-25 | 0.726144 | 0.910417 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 5.72536e-48 | 0.091248 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 2.75823e-20 | 0.683178 | 0.900537 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 7.28119e-16 | 0.549455 | 0.839563 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 1.98803e-34 | 0.567182 | 0.839834 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 1.57903e-41 | 0.260617 | 0.629235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 8.70632e-30 | 0.465535 | 0.787464 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 4.84402e-19 | 0.43415 | 0.779049 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 1.82306e-88 | 0.0571495 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 0.000407213 | 0.636378 | 0.885792 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 3.12773e-10 | 0.79912 | 0.949557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 8.40651e-21 | 0.456506 | 0.782818 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 0.15829 | 0.603981 | 0.861104 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 1.01061e-22 | 0.741885 | 0.920897 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 5.98135e-28 | 0.880353 | 0.983235 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 1.56729e-19 | 0.592293 | 0.856679 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 1.98967e-19 | 0.555222 | 0.839563 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 2.1903e-16 | 0.41768 | 0.766259 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 0.00789229 | 0.973857 | 0.989724 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 3.6959e-21 | 0.612102 | 0.870196 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 0.0920626 | 0.364172 | 0.718268 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 1.18851e-26 | 0.419822 | 0.767367 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 9.75686e-20 | 0.800553 | 0.949557 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 0.0218147 | 0.770154 | 0.92349 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 6.56353e-22 | 0.129498 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 2.89997e-08 | 0.666958 | 0.894656 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 1.41317e-166 | 0.0419164 | 0.392357 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 0.000770799 | 0.170449 | 0.528287 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 0.0200796 | 0.73944 | 0.920151 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 7.73971e-43 | 0.100109 | 0.434388 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 5.73349e-07 | 0.954277 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 0.196112 | 0.925118 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 7.29101e-11 | 0.118866 | 0.474512 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 1.40899e-15 | 0.926093 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 0.761213 | 0.918697 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 0.161116 | 0.947686 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 0.1558 | 0.36937 | 0.721097 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 3.91176e-12 | 0.852004 | 0.970662 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 5.45338e-13 | 0.62312 | 0.878353 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 5.51088e-05 | 0.540748 | 0.832819 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 0.165445 | 0.960523 | 0.984191 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 6.34099e-47 | 0.461319 | 0.785534 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 7.90914e-18 | 0.595953 | 0.857005 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 6.48587e-53 | 0.397714 | 0.749638 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 1.1051e-05 | 0.694321 | 0.902822 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 0.995321 | 0.887374 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.48405e-48 | 0.888635 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 1.38242e-29 | 0.57137 | 0.840892 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 7.45408e-14 | 0.283392 | 0.65098 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 7.4206e-40 | 0.287947 | 0.65098 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 6.2564e-07 | 0.980691 | 0.990617 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 0.0178128 | 0.704249 | 0.902822 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 2.05398e-10 | 0.46282 | 0.785534 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 7.49546e-11 | 0.163716 | 0.513802 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 0.0834391 | 0.512871 | 0.818698 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 6.32766e-19 | 0.74741 | 0.923162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 0.0123651 | 0.235805 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 0.00140054 | 0.717578 | 0.907214 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 1.73834e-05 | 0.886694 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 2.59566e-16 | 0.0503291 | 0.397318 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 3.16225e-14 | 0.572953 | 0.840892 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 0.053066 | 0.831158 | 0.962292 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 5.86691e-26 | 0.923711 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 0.731498 | 0.803037 | 0.949557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 1.12652e-18 | 0.0593009 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.00993854 | 0.685373 | 0.900537 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 0.0988491 | 0.980423 | 0.990617 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 5.99597e-05 | 0.533452 | 0.832819 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 3.73563e-11 | 0.358673 | 0.718268 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 3.63767e-16 | 0.70207 | 0.902822 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 1.79453e-30 | 0.0467634 | 0.394368 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 4.82116e-06 | 0.704517 | 0.902822 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 0.0468473 | 0.139639 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.0205042 | 0.812791 | 0.94966 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 0.000641816 | 0.55774 | 0.839834 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` | 2.02917e-12 | 0.0804315 | 0.418557 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 3.33484e-13 | 0.0880023 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` | 2.65379e-15 | 0.639745 | 0.886273 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 3.35875e-28 | 0.434501 | 0.779049 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` | 0.00250116 | 0.535879 | 0.832819 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` | 0.0112965 | 0.489979 | 0.808985 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 4.99726e-48 | 0.382581 | 0.736219 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 4.04968e-13 | 0.844354 | 0.966359 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 8.19443e-09 | 0.443734 | 0.782818 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 0.000147305 | 0.55328 | 0.839563 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` | 2.17595e-13 | 0.924694 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 1.83823e-10 | 0.90777 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 0.626747 | 0.754269 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` | 1.31432e-07 | 0.987405 | 0.991378 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` | 0.735131 | 0.770308 | 0.92349 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` | 9.24126e-08 | 0.235628 | 0.614753 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 0.000121473 | 0.565677 | 0.839834 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 1.13227e-23 | 0.0639742 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` | 7.16153e-26 | 0.472457 | 0.791128 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` | 0.000953906 | 0.711189 | 0.905315 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 0.676126 | 0.678778 | 0.900537 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 1.2189e-15 | 0.641263 | 0.886273 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 0.115689 | 0.878871 | 0.983235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` | 4.02299e-30 | 0.911107 | 0.983235 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` | 0.000678996 | 0.666153 | 0.894656 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` | 3.1219e-33 | 0.493551 | 0.809711 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 0.486357 | 0.229139 | 0.614733 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 0.032051 | 0.764255 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` | 2.23452e-23 | 0.906811 | 0.983235 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 0.00139015 | 0.724066 | 0.910417 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 3.10485e-15 | 0.570963 | 0.840892 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 8.44974e-09 | 0.685613 | 0.900537 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` | 0.124341 | 0.435581 | 0.779049 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 4.57321e-28 | 0.0508254 | 0.397318 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 0.682231 | 0.940919 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` | 0.140539 | 0.630097 | 0.885686 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` | 3.42377e-19 | 0.808741 | 0.949557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` | 0.588876 | 0.500327 | 0.813235 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` | 1.37383e-44 | 0.133183 | 0.479072 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 0.000284663 | 0.32366 | 0.678144 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 1.52514e-20 | 0.0530171 | 0.400841 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 1.9535e-15 | 0.173226 | 0.530305 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.102493 | 0.454789 | 0.782818 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 4.76589e-11 | 0.38672 | 0.73936 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 3.57466e-22 | 0.0213412 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` | 1.56216e-47 | 0.354129 | 0.718268 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` | 1.49015e-08 | 0.540143 | 0.832819 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_34_Momentum_L5` | 1.30516e-74 | 0.0242676 | 0.336376 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` | 2.31345e-54 | 0.0131501 | 0.318843 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 1.66166e-13 | 0.591967 | 0.856679 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 1.9815e-14 | 0.0931058 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 2.34799e-07 | 0.527774 | 0.830786 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 1.09638e-06 | 0.0778212 | 0.418557 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 1.88116e-05 | 0.968179 | 0.985961 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 0.0193644 | 0.431713 | 0.779049 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 3.28136e-19 | 0.162113 | 0.512117 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 1.41311e-121 | 0.584133 | 0.850635 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 3.00987e-18 | 0.261025 | 0.629235 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 2.01454e-17 | 0.517957 | 0.820509 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 0.00345032 | 0.105966 | 0.450045 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 0.86795 | 0.0747562 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 1.64427e-17 | 0.01615 | 0.322355 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 2.01677e-84 | 0.00459327 | 0.254671 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 4.02125e-31 | 0.0911214 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 0.538741 | 0.21597 | 0.598716 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 1.8624e-07 | 0.538152 | 0.832819 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 0.180718 | 0.579975 | 0.848702 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 5.26056e-108 | 0.00144015 | 0.169407 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 2.37164e-08 | 0.222595 | 0.606967 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 2.91761e-25 | 0.34339 | 0.702261 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 3.24564e-05 | 0.595382 | 0.857005 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 4.32008e-19 | 0.0843136 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 5.54699e-10 | 0.0799765 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 6.91317e-33 | 0.967566 | 0.985961 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 1.02009e-13 | 0.0100441 | 0.292209 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 1.92781e-46 | 0.918581 | 0.983235 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 1.17909e-18 | 0.107006 | 0.450045 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 1.68452e-15 | 0.00678375 | 0.263078 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 6.17024e-11 | 0.0309442 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 6.26456e-25 | 0.149599 | 0.493733 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.0202191 | 0.566086 | 0.839834 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 2.60284e-10 | 0.0197105 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 0.0256575 | 0.0370045 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 1.32644e-05 | 0.642948 | 0.886273 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` | 2.87546e-06 | 0.728377 | 0.910928 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 0.362385 | 0.317411 | 0.674655 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 0.207655 | 0.162153 | 0.512117 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 2.33578e-45 | 0.00308244 | 0.219734 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 2.47282e-41 | 0.110728 | 0.452896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` | 7.09739e-56 | 0.109129 | 0.450045 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` | 6.31287e-11 | 0.51346 | 0.818698 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` | 5.16692e-12 | 0.124256 | 0.475932 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 1.09846e-63 | 0.0147845 | 0.318843 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 2.37579e-34 | 0.150396 | 0.493733 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` | 1.54862e-46 | 0.0105406 | 0.292209 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 0.00044554 | 0.309863 | 0.663613 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` | 3.97386e-55 | 0.141095 | 0.479072 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` | 2.03285e-32 | 0.669275 | 0.895358 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` | 1.00896e-103 | 0.000232293 | 0.115914 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 3.88288e-44 | 0.047957 | 0.394368 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` | 0.579561 | 0.700645 | 0.902822 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` | 0.593015 | 0.725336 | 0.910417 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` | 0.0212427 | 0.0143285 | 0.318843 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` | 1.59183e-19 | 0.0819812 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 8.55601e-09 | 0.660644 | 0.893391 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Min_W8` |  |  |  | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 0.00611165 | 0.058519 | 0.406224 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 1.8158e-17 | 0.078608 | 0.418557 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 6.34059e-18 | 0.0450719 | 0.392357 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 7.79842e-33 | 0.00569655 | 0.263078 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` | 3.48266e-14 | 0.0800243 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.0040164 | 0.238602 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` | 1.5251e-17 | 0.215693 | 0.598716 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 6.2075e-06 | 0.410877 | 0.759361 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 0.195632 | 0.140136 | 0.479072 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.318211 | 0.0928514 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 6.30816e-11 | 0.0196159 | 0.32832 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 2.55347e-21 | 0.0217126 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 2.23795e-49 | 0.0210038 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 0.0372829 | 0.380657 | 0.736219 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 4.20253e-55 | 0.182299 | 0.545274 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 4.9948e-34 | 0.265599 | 0.633004 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 0.0124759 | 0.448165 | 0.782818 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 3.26875e-05 | 0.19859 | 0.572473 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 8.0661e-13 | 0.359009 | 0.718268 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` | 6.35105e-15 | 0.0723497 | 0.418557 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 1.43415e-32 | 0.987098 | 0.991378 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 1.22003e-26 | 0.651138 | 0.890186 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` | 0.000216876 | 0.657395 | 0.893391 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` | 6.07647e-28 | 0.5618 | 0.839834 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` | 1.14691e-120 | 0.00685069 | 0.263078 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` | 1.30601e-33 | 0.0372593 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` | 6.61084e-82 | 0.157744 | 0.505229 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` | 9.09696e-13 | 0.0869745 | 0.418557 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.0275411 | 0.984205 | 0.991378 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` | 3.68128e-14 | 0.875135 | 0.983235 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` | 0.0016178 | 0.212056 | 0.594471 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` | 4.46213e-10 | 0.190444 | 0.558253 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` | 7.52994e-29 | 0.369942 | 0.721097 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` | 8.38049e-08 | 0.0638791 | 0.406224 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 0.68091 | 0.934244 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` | 7.54924e-08 | 0.735219 | 0.917186 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` | 2.94547e-14 | 0.903449 | 0.983235 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` | 0.354139 | 0.122563 | 0.475932 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` | 1.84474e-06 | 0.703481 | 0.902822 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` | 5.67479e-08 | 0.768288 | 0.92349 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` | 2.78918e-108 | 0.189851 | 0.558253 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` | 0.0214098 | 0.510357 | 0.818698 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` | 0.444449 | 0.304468 | 0.660563 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` | 1.45749e-08 | 0.462818 | 0.785534 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` | 5.92132e-21 | 0.00748899 | 0.266929 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` | 0.793627 | 0.647271 | 0.887952 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` | 3.27303e-17 | 0.22412 | 0.607804 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` | 1.50889e-09 | 0.0996061 | 0.434388 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` | 4.36177e-08 | 0.0336219 | 0.379436 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` | 2.39375e-105 | 0.0639018 | 0.406224 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` | 0.712606 | 0.753488 | 0.92349 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` | 8.85633e-09 | 0.848305 | 0.96866 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` | 1.84714e-46 | 0.28831 | 0.65098 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` | 1.06017e-18 | 0.104451 | 0.449321 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` | 2.32365e-43 | 0.114395 | 0.460346 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` | 0.430477 | 0.60204 | 0.860797 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` | 0.170826 | 0.956968 | 0.98385 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` | 9.19191e-42 | 0.0171999 | 0.32832 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` | 7.51136e-15 | 0.967249 | 0.985961 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` | 3.13891e-26 | 0.000885992 | 0.14737 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` | 5.87133e-05 | 0.566617 | 0.839834 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` | 1.99558e-16 | 0.0251429 | 0.33909 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` | 0.00047145 | 0.00818383 | 0.272249 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` | 2.62772e-08 | 0.0456047 | 0.392357 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` | 0.104636 | 0.654977 | 0.892988 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` | 1.85452e-11 | 0.495079 | 0.809711 | False | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` | 0.00146636 | 0.233871 | 0.614753 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` | 1.37257e-39 | 0.659622 | 0.893391 | True | False | removed:p_value |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` | 4.44587e-06 | 0.555108 | 0.839563 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` | 6.2888e-12 | 0.299402 | 0.656343 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` | 3.69859e-35 | 0.0332809 | 0.379436 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` | 3.15019e-85 | 0.0280792 | 0.368724 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` | 4.7443e-24 | 0.00288781 | 0.219734 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` | 0.00242205 | 0.279543 | 0.65098 | False | False | removed:icir |
| `long_ETHUSDT_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` | 4.71859e-13 | 0.0956171 | 0.426008 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 2.63526e-51 | 0.0298881 | 0.381648 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` | 1.87932e-05 | 0.157708 | 0.527904 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_APO_34-89-0_Skew_W21` | 0.00237857 | 0.339866 | 0.724612 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 2.25812e-72 | 0.882525 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_APO_5-13-0_Skew_W233` | 1.13616e-47 | 0.685457 | 0.894026 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_APO_55-144-0_Range_W8` | 1.47677e-09 | 0.950507 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_APO_55-144-0_Std_W144` | 8.74056e-40 | 0.322336 | 0.706211 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_144_Kurt_W5` | 5.4089e-23 | 0.0804652 | 0.450162 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_89_Momentum_L21` | 0.000282451 | 0.825609 | 0.960639 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_89_Slope_W5` | 1.92196e-30 | 0.2652 | 0.673213 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_CMO_8_Rank_W3` | 0.763399 | 0.285888 | 0.687788 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 7.56074e-08 | 0.309474 | 0.698244 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 4.16493e-58 | 0.0626854 | 0.421856 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_55-233-34_Momentum_L55` | 5.85897e-49 | 0.19187 | 0.579099 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Hist_8-34-9_Lag_8` | 0.0591998 | 0.475957 | 0.78056 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` | 3.74183e-38 | 0.299364 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 1.15035e-47 | 0.479177 | 0.78056 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_13-55-13_Mean_W89` | 5.41113e-20 | 0.132129 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` | 0.963393 | 0.0611378 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 6.46315e-52 | 0.899795 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_5-21-5_Range_W8` | 1.45325e-71 | 0.00088759 | 0.14089 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 1.46092e-09 | 0.141847 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_13-55-13_DecayLinear_W13` | 8.07313e-35 | 0.961319 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_34-89-13_Std_W3` | 0.348063 | 0.0479012 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 2.64658e-19 | 0.80783 | 0.954391 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.761576 | 0.130831 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` | 2.26019e-24 | 0.770014 | 0.930882 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_21-55-9_ZScore_W3` | 1.34165e-57 | 0.0108831 | 0.285252 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 2.63776e-30 | 0.267663 | 0.673213 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 2.14875e-19 | 0.360579 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_12-26-9_Mean_W34` | 1.19612e-40 | 0.877615 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` | 0.0690068 | 0.0853458 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_21-55-9_Std_W144` | 0.00642411 | 0.365653 | 0.736924 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_21-89-13_Momentum_L233` | 9.73294e-05 | 0.962288 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 1.74742e-43 | 0.447139 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Line_55-233-34_ZScore_W21` | 3.12815e-52 | 0.972058 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 3.91767e-27 | 0.916887 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_21-89-13_Max_W34` | 1.36031e-15 | 0.505505 | 0.797807 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDEXT-Signal_8-21-5_TsArgmin_W5` | 1.43015e-61 | 0.472921 | 0.77985 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W13` | 9.02625e-21 | 0.068298 | 0.447531 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 4.3968e-29 | 0.427172 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 1.72336e-40 | 0.957558 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_8_Mean_W55` | 2.1286e-36 | 0.412626 | 0.763896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Hist_9_ZScore_W144` | 4.10199e-77 | 0.233679 | 0.641698 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` | 5.36643e-38 | 0.0213625 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` | 1.00622e-55 | 0.319075 | 0.703096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` | 2.1409e-22 | 0.126704 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Rank_W3` | 0.334725 | 0.395001 | 0.75596 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 3.59992e-16 | 0.990619 | 0.992612 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 1.00622e-55 | 0.319075 | 0.703096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` | 0.119808 | 0.210284 | 0.605326 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` | 9.01853e-84 | 0.754275 | 0.925108 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 1.42715e-35 | 0.00685375 | 0.243798 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Line_9_TsRank_W5` | 5.85764e-06 | 0.41602 | 0.764724 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` | 6.69513e-16 | 0.129836 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_8_Rank_W5` | 5.99032e-38 | 0.914571 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MACDFIX-Signal_9_Std_W34` | 1.81805e-15 | 0.113431 | 0.491205 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MOM_13_Min_W144` | 2.87735e-19 | 0.135377 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MOM_21` | 8.62164e-77 | 0.94211 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_MOM_89_Rank_W89` | 1.20838e-12 | 0.309666 | 0.698244 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_13-55-0_Lag_3` | 4.87632e-38 | 0.780837 | 0.939267 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_13-55-0_Slope_W89` | 0.496023 | 0.363614 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 1.67661e-16 | 0.491227 | 0.796844 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` | 0.437189 | 0.138372 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_PPO_55-233-0_Kurt_W34` | 1.49299e-13 | 0.334366 | 0.720842 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_12_Skew_W233` | 0.000114963 | 0.428736 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_13_Range_W5` | 1.61344e-17 | 0.167631 | 0.545623 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_89_Kurt_W13` | 6.57591e-05 | 0.938682 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_8_Lag_1` | 3.63901e-149 | 0.120895 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_9_DecayLinear_W5` | 7.42121e-136 | 0.226085 | 0.625503 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCP_9_TsRank_W13` | 4.20088e-48 | 0.0573942 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 7.16022e-109 | 0.894844 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_34_Mean_W89` | 1.13927e-35 | 0.305922 | 0.698244 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_5_TsRank_W21` | 3.63528e-09 | 0.128383 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_8_34_Ratio` | 0.599443 | 0.2101 | 0.605326 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR100_9_Rank_W8` | 1.73197e-37 | 0.0646226 | 0.429094 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_13_Rank_W144` | 2.92993e-45 | 0.993005 | 0.993005 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_55_Rank_W3` | 9.14893e-12 | 0.958218 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROCR_5_Skew_W13` | 2.57494e-107 | 0.180117 | 0.560977 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_55_Range_W89` | 0.159668 | 0.496536 | 0.796896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_55_Std_W144` | 5.92606e-19 | 0.257979 | 0.669491 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_89_Range_W3` | 0.201829 | 0.206268 | 0.605326 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_ROC_89_Slope_W233` | 1.25736e-16 | 0.267545 | 0.673213 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_14_Momentum_L55` | 1.28632e-45 | 0.94801 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_34_Max_W21` | 2.70231e-57 | 0.469423 | 0.779242 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_55_TsArgmax_W21` | 2.50143e-10 | 0.760513 | 0.926004 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_RSI_8_Rank_W55` | 3.83865e-54 | 0.285681 | 0.687788 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 6.16964e-29 | 0.176949 | 0.557725 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.83947e-62 | 0.0449194 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` | 1.38022e-38 | 0.324888 | 0.706211 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 0.0161104 | 0.407081 | 0.763896 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastk_21-8-5-0_Range_W8` | 5.32958e-15 | 0.668219 | 0.884082 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` | 3.05219e-15 | 0.138179 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_13_Lag_5` | 3.73759e-19 | 0.452388 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_21_Kurt_W5` | 2.24847e-53 | 0.392158 | 0.754033 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_momentum_TRIX_55_Rank_W233` | 5.95741e-29 | 0.694293 | 0.894135 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` | 2.93069e-10 | 0.326162 | 0.706211 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 8.46985e-16 | 0.123212 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 1.81837e-67 | 0.300999 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` | 0.0606434 | 0.453561 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_34_Slope_W21` | 1.63077e-05 | 0.0530172 | 0.41254 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 1.16216e-103 | 0.0367401 | 0.386565 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_21_89_Ratio` | 2.37568e-56 | 0.56402 | 0.821096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_5_Lag_2` | 4.24462e-160 | 0.0195639 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_5_Std_W8` | 1.6353e-16 | 0.0365925 | 0.386565 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_LINEARREG_89_Slope_W13` | 0.000969688 | 0.616675 | 0.859028 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 0.020259 | 0.439382 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_STDDEV_89_Skew_W5` | 0.0254382 | 0.803489 | 0.954391 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_TSF_55_Kurt_W13` | 0.0629953 | 0.280977 | 0.685914 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_TSF_89_Momentum_L8` | 9.95103e-33 | 0.718135 | 0.9015 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_TSF_89_Range_W233` | 9.43879e-38 | 0.416895 | 0.764724 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Kurt_W13` | 3.31874e-34 | 0.0979903 | 0.46037 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Log1p` | 4.39601e-05 | 0.208551 | 0.605326 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_144_Slope_W8` | 1.53098e-06 | 0.256397 | 0.669491 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 0.0178376 | 0.81788 | 0.954415 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_55_TsRank_W5` | 2.4599e-27 | 0.0517548 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `close_12h_statistics_VAR_89_TsRank_W13` | 0.216661 | 0.0314662 | 0.382199 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_apen_55_Max_W8` | 1.52579e-08 | 0.705612 | 0.894135 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_fractal_dim_55_Kurt_W55` | 0.894617 | 0.301207 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_fractal_dim_55_Lag_21` | 5.04107e-22 | 0.879117 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_perm_21_Mean_W34` | 1.54929e-42 | 0.208345 | 0.605326 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_perm_55_Min_W233` | 3.45019e-115 | 0.0611246 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_shannon_close_return_55_Slope_W13` | 4.17081e-37 | 0.0237716 | 0.326629 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 3.50275e-70 | 0.240951 | 0.645126 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 1.16249e-11 | 0.274687 | 0.678723 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_shannon_taker_ratio_100_Skew_W144` | 3.11127e-10 | 0.600744 | 0.845114 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_shannon_volume_21_Max_W89` | 0.444756 | 0.36787 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ent_12h_shannon_volume_55_Max_W233` | 0.0670867 | 0.197737 | 0.592203 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_144_Lag_8` | 1.99287e-25 | 0.661675 | 0.883416 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 8.25089e-71 | 0.936058 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` | 2.42634e-16 | 0.157947 | 0.527904 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 9.19271e-19 | 0.0512932 | 0.41254 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` | 0.0152891 | 0.237239 | 0.642093 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` | 0.845293 | 0.290166 | 0.691399 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` | 7.49715e-34 | 0.182487 | 0.560977 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_25_Skew_W144` | 1.27436e-47 | 0.172916 | 0.552019 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` | 1.70327e-64 | 0.381799 | 0.752811 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_55_Std_W5` | 6.05428e-11 | 0.201858 | 0.598364 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.0183476 | 0.584705 | 0.834336 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_13_Slope_W8` | 7.42739e-16 | 0.543625 | 0.810554 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 1.25218e-22 | 0.647724 | 0.87654 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_34_DecayLinear_W21` | 5.88938e-21 | 0.807677 | 0.954391 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_MINUS-DM_34_Range_W5` | 0.000493279 | 0.0889357 | 0.450162 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_14_Min_W3` | 3.64844e-116 | 0.269231 | 0.673754 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_21_Min_W89` | 4.34972e-42 | 0.363722 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_21_Range_W21` | 3.82012e-32 | 0.307532 | 0.698244 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 9.368e-53 | 0.14191 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` | 1.4162e-26 | 0.817912 | 0.954415 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 1.37594e-129 | 0.18484 | 0.564725 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_13_Lag_2` | 4.22142e-18 | 0.44661 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_144_Slope_W233` | 0.00232719 | 0.220603 | 0.617192 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_233_Max_W144` | 7.67147e-29 | 0.0912013 | 0.450162 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_BETA_34_ZScore_W8` | 0.00105367 | 0.0427847 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_21_Slope_W89` | 6.408e-05 | 0.0916241 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_233_Rank_W233` | 8.07624e-45 | 0.0234377 | 0.326629 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_55_Slope_W233` | 0.000200586 | 0.621588 | 0.861983 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 1.85535e-21 | 0.0341913 | 0.386565 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hl_12h_statistics_CORREL_8_Skew_W3` | 1.65968e-13 | 0.951674 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 4.6118e-06 | 0.950316 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 0.329947 | 0.810707 | 0.954415 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_14_Range_W233` | 7.52767e-09 | 0.453922 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADXR_233_Rank_W144` | 2.46764e-25 | 0.00926834 | 0.285252 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_13_Skew_W21` | 0.112722 | 0.756062 | 0.925108 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_13_Std_W89` | 0.15542 | 0.523334 | 0.804384 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_144_Mean_W13` | 8.49208e-28 | 0.0206674 | 0.318025 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_14_Lag_3` | 1.70176e-06 | 0.0157829 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ADX_34_Mean_W34` | 2.55648e-20 | 0.446302 | 0.775325 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 1.23352e-10 | 0.472343 | 0.77985 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_144_Skew_W34` | 5.39542e-21 | 0.673004 | 0.886656 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_14_Log1p` | 5.43505e-112 | 0.142228 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_233_Min_W34` | 6.82972e-25 | 0.87253 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_34_Range_W3` | 2.24174e-07 | 0.924792 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_34_Skew_W34` | 9.51253e-69 | 0.391583 | 0.754033 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_CCI_5_Mean_W13` | 8.98127e-36 | 0.665353 | 0.884082 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Kurt_W8` | 4.46506e-16 | 0.0868451 | 0.450162 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Momentum_L233` | 3.1315e-30 | 0.887619 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_Std_W89` | 1.17645e-13 | 0.14305 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 7.9379e-37 | 0.356311 | 0.736924 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_144_Mean_W34` | 4.03633e-19 | 0.0482094 | 0.41254 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_144_TsArgmin_W13` | 6.11745e-43 | 0.798472 | 0.954391 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_21_Rank_W21` | 5.11214e-31 | 0.517241 | 0.800817 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_233_Skew_W13` | 0.055229 | 0.771734 | 0.930882 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_34_Momentum_L21` | 0.00172945 | 0.336422 | 0.722147 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_55_Lag_8` | 0.956775 | 0.840259 | 0.96799 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_DX_89_Range_W34` | 1.99236e-18 | 0.107468 | 0.482152 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_144` | 1.12948e-99 | 0.234625 | 0.641698 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_233_Mean_W5` | 7.84082e-76 | 0.150823 | 0.518 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` | 1.80858e-19 | 0.456335 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` | 3.72428e-29 | 0.246394 | 0.653796 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 5.68607e-102 | 0.513532 | 0.799184 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 1.16403e-46 | 0.0916918 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_PLUS_DI_8_89_Cross` | 2.60548e-54 | 0.94382 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` | 1.06331e-05 | 0.637273 | 0.874275 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` | 4.27702e-126 | 0.0100901 | 0.285252 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` | 3.32028e-115 | 0.342039 | 0.724612 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 5.15914e-52 | 0.920609 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` | 1.02738e-39 | 0.153859 | 0.524806 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` | 7.54473e-47 | 0.112949 | 0.491205 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` | 3.61101e-97 | 0.952351 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 4.46279e-101 | 0.0181759 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` | 9.57223e-13 | 0.562483 | 0.821096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` | 5.87022e-62 | 0.0140949 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 1.15629e-152 | 0.300826 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 4.09548e-78 | 0.554837 | 0.818049 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_STOCHF-fastk_8-3-0_Std_W21` | 2.56015e-86 | 0.386087 | 0.752811 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_34-55-144_Kurt_W5` | 2.67599e-12 | 0.506239 | 0.797807 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 4.88365e-35 | 0.258117 | 0.669491 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` | 1.80158e-132 | 0.121705 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-10-20_ZScore_W3` | 7.48477e-05 | 0.127051 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_ULTOSC_5-13-26_Mean_W233` | 7.17508e-08 | 0.299784 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_14_Mean_W34` | 3.89859e-85 | 0.617534 | 0.859028 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 7.11139e-63 | 0.40102 | 0.759345 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 1.46864e-58 | 0.0606676 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_5_Momentum_L233` | 2.11325e-15 | 0.141532 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_momentum_WILLR_89_Rank_W233` | 3.06425e-93 | 0.860667 | 0.985315 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_144_Std_W144` | 1.67027e-30 | 0.0599356 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_14_Rank_W5` | 2.93087e-23 | 0.0795384 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Lag_13` | 0.324167 | 0.410847 | 0.763896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Range_W8` | 2.84965e-17 | 0.947496 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_21_Rank_W34` | 2.37061e-42 | 0.000579672 | 0.14089 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_233_Kurt_W13` | 5.15604e-30 | 0.496492 | 0.796896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_233_Mean_W13` | 0.000334076 | 0.386987 | 0.752811 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_ATR_5_20_Cross` | 2.9805e-35 | 0.00169747 | 0.14089 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_13_Lag_1` | 0.0403669 | 0.383601 | 0.752811 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_144_Momentum_L34` | 9.49538e-36 | 0.70279 | 0.894135 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_55_Range_W21` | 3.36807e-36 | 0.478662 | 0.78056 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `hlc_12h_volatility_NATR_89_Slope_W34` | 1.11863e-07 | 0.352205 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_13_Rank_W233` | 9.78042e-42 | 0.913086 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_21_DecayLinear_W21` | 1.27346e-40 | 0.44495 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_55_Min_W233` | 6.64464e-33 | 0.0712249 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `hlcv_12h_momentum_MFI_8_Skew_W8` | 0.0390357 | 0.438387 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `hlcv_12h_volume_EOM_14_Slope_W3` | 4.98053e-36 | 0.468625 | 0.779242 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_21_Std_W233` | 6.26048e-34 | 0.0280539 | 0.367654 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_55_Max_W5` | 1.67515e-08 | 0.0367963 | 0.386565 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_amihud_illiq_55_Rank_W8` | 3.11089e-59 | 0.459279 | 0.775325 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_cs_spread_21_Rank_W8` | 8.93555e-20 | 0.078046 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_kyle_lambda_21_Momentum_L13` | 2.91821e-17 | 0.833707 | 0.965549 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_13_Skew_W13` | 2.85455e-09 | 0.503928 | 0.797807 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_21_Std_W144` | 0.000853846 | 0.837473 | 0.96766 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_55_Kurt_W5` | 0.0007342 | 0.685779 | 0.894026 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_ofi_zscore_55_Skew_W21` | 1.32487e-33 | 0.25622 | 0.669491 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_roll_spread_55_Min_W34` | 2.98012e-155 | 0.0762859 | 0.450162 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_vpin_30_Slope_W89` | 4.39042e-09 | 0.246814 | 0.653796 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `ms_12h_vpin_50_Kurt_W13` | 2.64889e-19 | 0.220594 | 0.617192 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` | 0.00121513 | 0.300735 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_cycle_HT-SINE-Sine_Min_W89` | 8.04296e-10 | 0.492886 | 0.796896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 1.89689e-16 | 0.148614 | 0.518 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 3.61978e-05 | 0.917512 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 0.0406664 | 0.818344 | 0.954415 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 2.51022e-26 | 0.479621 | 0.78056 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` | 3.33796e-14 | 0.975864 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` | 4.19071e-23 | 0.537473 | 0.808687 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 1.69638e-11 | 0.510452 | 0.799184 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 7.65463e-27 | 0.841646 | 0.96799 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 2.49897e-08 | 0.759066 | 0.926004 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` | 8.02323e-32 | 0.690174 | 0.894135 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` | 0.0150534 | 0.88967 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_5_Slope_W233` | 4.31427e-20 | 0.407503 | 0.763896 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_CMO_89_Slope_W5` | 2.69402e-27 | 0.646769 | 0.87654 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 5.32676e-19 | 0.745484 | 0.921219 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` | 5.08094e-19 | 0.71078 | 0.898397 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 1.10304e-42 | 0.690907 | 0.894135 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_21-55-9_Sign` | 8.23766e-05 | 0.390257 | 0.754033 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 4.00943e-35 | 0.893732 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_55-144-21_Skew_W233` | 0.644934 | 0.431247 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` | 8.94751e-18 | 0.536756 | 0.808687 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 6.58427e-25 | 0.726144 | 0.906316 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_55-233-34_Momentum_L13` | 1.20571e-13 | 0.643676 | 0.875821 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 5.72536e-48 | 0.091248 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_12-26-9_Range_W21` | 1.00348e-35 | 0.532823 | 0.808687 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 2.75823e-20 | 0.683178 | 0.894026 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` | 7.28119e-16 | 0.549455 | 0.816801 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 1.98803e-34 | 0.567182 | 0.821096 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` | 1.57903e-41 | 0.260617 | 0.670055 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_34-89-13_Mean_W3` | 0.000356993 | 0.538926 | 0.808687 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 8.70632e-30 | 0.465535 | 0.777975 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-55-9_Kurt_W13` | 1.45984e-25 | 0.397399 | 0.75596 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-55-9_Lag_8` | 9.97143e-11 | 0.181887 | 0.560977 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Line_21-89-13_DecayLinear_W13` | 7.10563e-09 | 0.519405 | 0.800817 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 4.84402e-19 | 0.43415 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_34-89-13_Slope_W89` | 2.91519e-28 | 0.275305 | 0.678723 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 1.82306e-88 | 0.0571495 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` | 0.000407213 | 0.636378 | 0.874275 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` | 3.12773e-10 | 0.79912 | 0.954391 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` | 8.40651e-21 | 0.456506 | 0.775325 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` | 0.15829 | 0.603981 | 0.847274 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` | 1.01061e-22 | 0.741885 | 0.919051 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` | 5.98135e-28 | 0.880353 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Line_21_DecayLinear_W5` | 0.138234 | 0.870722 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 1.56729e-19 | 0.592293 | 0.840348 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` | 1.98967e-19 | 0.555222 | 0.818049 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` | 2.1903e-16 | 0.41768 | 0.764724 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` | 0.00789229 | 0.973857 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 3.6959e-21 | 0.612102 | 0.856255 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_21_Range_W34` | 3.19419e-07 | 0.503044 | 0.797807 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 0.0920626 | 0.364172 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 1.18851e-26 | 0.419822 | 0.765829 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` | 9.75686e-20 | 0.800553 | 0.954391 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 0.0218147 | 0.770154 | 0.930882 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 6.56353e-22 | 0.129498 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_34_Mean_W13` | 0.000488948 | 0.458652 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 2.89997e-08 | 0.666958 | 0.884082 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` | 1.41317e-166 | 0.0419164 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 0.000770799 | 0.170449 | 0.551193 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_13_Rank_W55` | 1.05966e-13 | 0.135338 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 0.0200796 | 0.73944 | 0.918307 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` | 7.73971e-43 | 0.100109 | 0.461615 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` | 5.73349e-07 | 0.954277 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 0.196112 | 0.925118 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 7.29101e-11 | 0.118866 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_55_Kurt_W21` | 1.92577e-14 | 0.973011 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROCR_89_Max_W3` | 0.272172 | 0.412509 | 0.763896 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_34_Momentum_L233` | 1.39619e-07 | 0.979035 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` | 1.40899e-15 | 0.926093 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 0.761213 | 0.918697 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_ROC_89_Mean_W13` | 0.759111 | 0.771996 | 0.930882 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_14_Kurt_W34` | 0.636546 | 0.643404 | 0.875821 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` | 0.161116 | 0.947686 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_5_Momentum_L5` | 2.66034e-13 | 0.718666 | 0.9015 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_RSI_7_Std_W13` | 1.83878e-11 | 0.17403 | 0.552019 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 0.1558 | 0.36937 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-5-3-0_Range_W233` | 2.04963e-70 | 0.55414 | 0.818049 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 3.91176e-12 | 0.852004 | 0.977645 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` | 5.45338e-13 | 0.62312 | 0.861983 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 5.51088e-05 | 0.540748 | 0.808687 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Kurt_W5` | 0.000308235 | 0.953638 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 0.165445 | 0.960523 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_STOCHRSI-fastk_55-8-5-0_Skew_W233` | 4.81669e-22 | 0.353955 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 6.34099e-47 | 0.461319 | 0.776041 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` | 7.90914e-18 | 0.595953 | 0.84075 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 6.48587e-53 | 0.397714 | 0.75596 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` | 1.1051e-05 | 0.694321 | 0.894135 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_5_Kurt_W34` | 0.503258 | 0.97242 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_momentum_TRIX_5_Sign` | 0.995321 | 0.887374 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` | 2.48405e-48 | 0.888635 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` | 1.38242e-29 | 0.57137 | 0.824654 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` | 7.45408e-14 | 0.283392 | 0.687788 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` | 7.4206e-40 | 0.287947 | 0.689411 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 6.2564e-07 | 0.980691 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 0.0178128 | 0.704249 | 0.894135 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 2.05398e-10 | 0.46282 | 0.776041 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 7.49546e-11 | 0.163716 | 0.536387 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` | 0.0834391 | 0.512871 | 0.799184 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Kurt_W21` | 5.6572e-20 | 0.34318 | 0.724612 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` | 6.32766e-19 | 0.74741 | 0.921312 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 0.0123651 | 0.235805 | 0.641698 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` | 0.00140054 | 0.717578 | 0.9015 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 1.73834e-05 | 0.886694 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 2.59566e-16 | 0.0503291 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 3.16225e-14 | 0.572953 | 0.824654 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 0.053066 | 0.831158 | 0.964841 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_13_Slope_W8` | 1.08742e-05 | 0.944781 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` | 5.86691e-26 | 0.923711 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_5_Rank_W34` | 7.67036e-08 | 0.699406 | 0.894135 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 0.731498 | 0.803037 | 0.954391 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 1.12652e-18 | 0.0593009 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 0.00993854 | 0.685373 | 0.894026 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 0.0988491 | 0.980423 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` | 5.99597e-05 | 0.533452 | 0.808687 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` | 3.73563e-11 | 0.358673 | 0.736924 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 3.63767e-16 | 0.70207 | 0.894135 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_13_Std_W8` | 1.79453e-30 | 0.0467634 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 4.82116e-06 | 0.704517 | 0.894135 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_14_Momentum_L21` | 0.928748 | 0.908331 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 0.0468473 | 0.139639 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` | 0.0205042 | 0.812791 | 0.954415 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 0.000641816 | 0.55774 | 0.819335 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 4.57321e-28 | 0.0508254 | 0.41254 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_cvar_5pct_100_Range_W34` | 0.001681 | 0.656193 | 0.882433 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_jb_100_Slope_W13` | 0.140539 | 0.630097 | 0.86922 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_mdd_55_Min_W8` | 0.868802 | 0.752092 | 0.924795 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_rsj_13_Range_W21` | 8.79975e-22 | 0.00493578 | 0.243798 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_rsj_21_Max_W21` | 3.42377e-19 | 0.808741 | 0.954391 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_rv_up_21_Mean_W89` | 0.011007 | 0.0905916 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_ud_vol_ratio_21_Max_W13` | 0.588876 | 0.500327 | 0.797807 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `tr_12h_ud_vol_ratio_21_Std_W34` | 1.37383e-44 | 0.133183 | 0.505239 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 0.000284663 | 0.32366 | 0.706211 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 1.52514e-20 | 0.0530171 | 0.41254 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 1.9535e-15 | 0.173226 | 0.552019 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_13-34-0_Mean_W55` | 0.0767631 | 0.07934 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.102493 | 0.454789 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 4.76589e-11 | 0.38672 | 0.752811 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_APO_5-21-0_Max_W34` | 3.57466e-22 | 0.0213412 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_14_Max_W144` | 1.56216e-47 | 0.354129 | 0.736924 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_14_Rank_W13` | 1.49015e-08 | 0.540143 | 0.808687 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_233_Max_W55` | 2.81802e-06 | 0.317082 | 0.703096 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_34_Momentum_L5` | 1.30516e-74 | 0.0242676 | 0.326629 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_CMO_8_Momentum_L3` | 2.31345e-54 | 0.0131501 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` | 1.66166e-13 | 0.591967 | 0.840348 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` | 1.9815e-14 | 0.0931058 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` | 2.34799e-07 | 0.527774 | 0.808687 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_21-89-13_Slope_W13` | 1.06305e-09 | 0.49766 | 0.796896 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 1.09638e-06 | 0.0778212 | 0.450162 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` | 1.88116e-05 | 0.968179 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Hist_5-21-5_Min_W144` | 7.60222e-25 | 0.0545639 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 0.0193644 | 0.431713 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` | 3.28136e-19 | 0.162113 | 0.534784 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` | 1.41311e-121 | 0.584133 | 0.834336 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` | 3.00987e-18 | 0.261025 | 0.670055 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 2.01454e-17 | 0.517957 | 0.800817 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 0.00345032 | 0.105966 | 0.482152 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 0.86795 | 0.0747562 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 1.64427e-17 | 0.01615 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` | 2.01677e-84 | 0.00459327 | 0.243798 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_21-55-9_TsArgmax_W21` | 3.82952e-13 | 0.279665 | 0.685914 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` | 4.02125e-31 | 0.0911214 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` | 0.538741 | 0.21597 | 0.611096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_34-89-13_ZScore_W3` | 1.87571e-80 | 0.0964751 | 0.457568 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` | 1.8624e-07 | 0.538152 | 0.808687 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_13-55-13_Skew_W13` | 3.88446e-77 | 0.91643 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` | 0.180718 | 0.579975 | 0.832356 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` | 5.26056e-108 | 0.00144015 | 0.14089 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 2.37164e-08 | 0.222595 | 0.619287 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Line_5-21-5_Range_W21` | 0.0106539 | 0.0994134 | 0.461615 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 2.91761e-25 | 0.34339 | 0.724612 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` | 3.24564e-05 | 0.595382 | 0.84075 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 4.32008e-19 | 0.0843136 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_34-89-13_Kurt_W5` | 8.04506e-54 | 0.27504 | 0.678723 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 5.54699e-10 | 0.0799765 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` | 6.91317e-33 | 0.967566 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` | 1.02009e-13 | 0.0100441 | 0.285252 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 1.92781e-46 | 0.918581 | 0.988632 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 1.17909e-18 | 0.107006 | 0.482152 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` | 1.68452e-15 | 0.00678375 | 0.243798 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` | 6.17024e-11 | 0.0309442 | 0.382199 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 6.26456e-25 | 0.149599 | 0.518 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_Log1p` | 8.63126e-16 | 0.00156568 | 0.14089 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` | 0.0202191 | 0.566086 | 0.821096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` | 2.60284e-10 | 0.0197105 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 0.0256575 | 0.0370045 | 0.386565 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` | 1.32644e-05 | 0.642948 | 0.875821 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_MOM_21_Slope_W21` | 2.87546e-06 | 0.728377 | 0.90683 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_34-144-0_Min_W144` | 0.362385 | 0.317411 | 0.703096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` | 0.207655 | 0.162153 | 0.534784 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` | 2.33578e-45 | 0.00308244 | 0.219294 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_PPO_8-34-0_Min_W89` | 2.47282e-41 | 0.110728 | 0.487987 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_144_Lag_34` | 7.09739e-56 | 0.109129 | 0.485235 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_233_Mean_W8` | 0.0931853 | 0.133061 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCP_89_Min_W13` | 6.31287e-11 | 0.51346 | 0.799184 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR100_55_Range_W13` | 5.16692e-12 | 0.124256 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 1.09846e-63 | 0.0147845 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 2.37579e-34 | 0.150396 | 0.518 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_21_Range_W3` | 1.54862e-46 | 0.0105406 | 0.285252 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 0.00044554 | 0.309863 | 0.698244 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_89_Std_W5` | 3.6401e-05 | 0.0946471 | 0.453214 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROCR_8_Min_W55` | 3.97386e-55 | 0.141095 | 0.505239 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_21_ZScore_W8` | 2.03285e-32 | 0.669275 | 0.884082 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_34_Momentum_L13` | 4.7751e-40 | 0.87001 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_5_Slope_W55` | 1.00896e-103 | 0.000232293 | 0.115682 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_89_Skew_W55` | 1.22255e-11 | 0.299853 | 0.69445 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_8_TsArgmin_W21` | 3.88288e-44 | 0.047957 | 0.41254 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_ROC_9_Momentum_L21` | 0.579561 | 0.700645 | 0.894135 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_13_Kurt_W21` | 0.593015 | 0.725336 | 0.906316 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_55_Max_W13` | 0.0212427 | 0.0143285 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_RSI_6_Min_W13` | 1.59183e-19 | 0.0819812 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` | 8.55601e-09 | 0.660644 | 0.883416 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Lag_21` | 9.66004e-05 | 0.905973 | 0.988632 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Min_W8` |  |  |  | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 0.00611165 | 0.058519 | 0.417077 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_55-8-5-0_Lag_34` | 7.77029e-44 | 0.445096 | 0.775325 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 1.8158e-17 | 0.078608 | 0.450162 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` | 6.34059e-18 | 0.0450719 | 0.41254 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_34_Lag_8` | 1.07279e-08 | 0.0706786 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_55_TsRank_W13` | 7.79842e-33 | 0.00569655 | 0.243798 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Max_W233` | 3.48266e-14 | 0.0800243 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Max_W89` | 0.0040164 | 0.238602 | 0.642291 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_5_Range_W144` | 8.24505e-107 | 0.0391298 | 0.397687 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_momentum_TRIX_89_Min_W5` | 1.5251e-17 | 0.215693 | 0.611096 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` | 6.2075e-06 | 0.410877 | 0.763896 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` | 0.195632 | 0.140136 | 0.505239 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.318211 | 0.0928514 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` | 6.30816e-11 | 0.0196159 | 0.318025 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_21_Slope_W5` | 4.86972e-88 | 0.313008 | 0.702152 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W8` | 2.94961e-85 | 0.0510856 | 0.41254 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` | 2.55347e-21 | 0.0217126 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` | 2.23795e-49 | 0.0210038 | 0.318025 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` | 0.0372829 | 0.380657 | 0.752811 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` | 4.20253e-55 | 0.182299 | 0.560977 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 4.9948e-34 | 0.265599 | 0.673213 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_233_Skew_W233` | 0.0124759 | 0.448165 | 0.775325 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_34_Min_W144` | 3.26875e-05 | 0.19859 | 0.592203 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_55_Min_W89` | 8.0661e-13 | 0.359009 | 0.736924 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_LINEARREG_5_Rank_W34` | 3.94148e-12 | 0.0367687 | 0.386565 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_144_Std_W34` | 6.35105e-15 | 0.0723497 | 0.450162 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_14_ZScore_W5` | 1.43415e-32 | 0.987098 | 0.991079 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_34_Range_W21` | 0.000139357 | 0.442915 | 0.775325 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_STDDEV_55_Mean_W5` | 1.22003e-26 | 0.651138 | 0.878772 | False | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_13_Range_W89` | 0.000216876 | 0.657395 | 0.882433 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_144_Kurt_W89` | 6.07647e-28 | 0.5618 | 0.821096 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_34_Kurt_W5` | 1.14691e-120 | 0.00685069 | 0.243798 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_34_Lag_5` | 1.30601e-33 | 0.0372593 | 0.386565 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_TSF_89_Momentum_L13` | 0.0683879 | 0.00476861 | 0.243798 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_13_Kurt_W8` | 6.61084e-82 | 0.157744 | 0.527904 | True | False | removed:p_value |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_20_Mean_W21` | 9.09696e-13 | 0.0869745 | 0.450162 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.0275411 | 0.984205 | 0.99017 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_34_Kurt_W8` | 3.68128e-14 | 0.875135 | 0.988632 | False | False | removed:icir |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_55_Min_W144` | 0.0016178 | 0.212056 | 0.606918 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_55_Slope_W3` | 4.46213e-10 | 0.190444 | 0.5783 | False | False | removed:ic_mean |
| `long_ETHUSDT_12h_f754aad4` | `volume_12h_statistics_VAR_89_Mean_W34` | 7.52994e-29 | 0.369942 | 0.736924 | True | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `close-volume_1h_volume_OBV_Momentum_L233` | 0 | 0.790219 | 0.934406 | True | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` | 0.0163935 | 0.164903 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` | 9.95021e-143 | 0.783687 | 0.932737 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_CMO_89_Slope_W5` | 2.56863e-107 | 0.346383 | 0.744782 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_CMO_8_Rank_W3` | 2.52273e-34 | 0.693158 | 0.89432 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` | 1.01767e-194 | 0.25073 | 0.683684 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` | 1.15492e-85 | 0.0539158 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` | 1.07542e-50 | 0.849661 | 0.948244 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` | 1.46704e-109 | 0.881638 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` | 1.93254e-07 | 0.119448 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` | 7.47123e-12 | 0.667593 | 0.888633 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` | 0.000135032 | 0.0601913 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` | 2.54147e-06 | 0.127981 | 0.578424 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` | 0.0129379 | 0.773476 | 0.930035 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` | 2.61301e-19 | 0.363138 | 0.748784 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` | 2.74781e-10 | 0.688887 | 0.892896 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` | 5.33816e-48 | 0.447318 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` | 1.06412e-56 | 0.842193 | 0.948244 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` | 0.00409949 | 0.869541 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` | 4.61179e-239 | 0.243684 | 0.681537 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` | 0.00198896 | 0.0105817 | 0.352019 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MOM_13_Min_W144` | 3.25684e-18 | 0.253895 | 0.685007 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_MOM_21` | 4.25504e-310 | 0.51094 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_PPO_21-55-0_Slope_W233` | 0.603128 | 0.210547 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCP_89_Kurt_W13` | 1.13032e-69 | 0.42344 | 0.797844 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR100_21_Momentum_L144` | 1.07126e-305 | 0.166473 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR100_9_Rank_W8` | 5.95713e-15 | 0.561514 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROCR_5_Skew_W13` | 3.94987e-10 | 0.172221 | 0.588438 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_55_Range_W89` | 1.41145e-21 | 0.535387 | 0.837486 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_55_Std_W144` | 5.78438e-09 | 0.87513 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_ROC_89_Slope_W233` | 0.00796016 | 0.0951112 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_RSI_8_Rank_W55` | 0 | 0.321255 | 0.727248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` | 9.48788e-57 | 0.350749 | 0.744782 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` | 1.40965e-242 | 0.0387209 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` | 1.11645e-05 | 0.383233 | 0.765804 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_momentum_TRIX_21_Kurt_W5` | 8.74039e-07 | 0.340095 | 0.74108 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` | 0.372909 | 0.0792936 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` | 0 | 0.1004 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` | 0.0592396 | 0.145584 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_LINEARREG_5_Std_W8` | 3.98469e-06 | 0.147048 | 0.580909 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_STDDEV_13_ZScore_W21` | 6.46458e-20 | 0.151021 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_55_Kurt_W13` | 6.0238e-25 | 0.560552 | 0.839948 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_89_Momentum_L8` | 3.02314e-115 | 0.956729 | 0.988796 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_TSF_89_Range_W233` | 4.20667e-05 | 0.325003 | 0.727248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_144_Log1p` | 3.05196e-06 | 0.310283 | 0.72351 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_20_TsArgmin_W5` | 5.3859e-67 | 0.461605 | 0.810673 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_statistics_VAR_55_TsRank_W5` | 1.27649e-05 | 0.433817 | 0.804738 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` | 1.74002e-12 | 0.389835 | 0.766113 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_DEMA_13_Slope_W55` | 0.00125569 | 0.781054 | 0.932406 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_EMA_21_Mean_W34` | 0.85943 | 0.299214 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_EMA_55_ZScore_W8` | 3.86519e-150 | 0.328459 | 0.72845 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_KAMA_8_Lag_5` | 5.54255e-29 | 0.507256 | 0.817176 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_MA_21_Rank_W13` | 5.30266e-150 | 0.823078 | 0.945338 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_MIDPOINT_34_Mean_W55` | 0.998078 | 0.30761 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_MIDPOINT_34_Rank_W144` | 5.68499e-20 | 0.779688 | 0.932406 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_20_Kurt_W233` | 0.479324 | 0.437472 | 0.80553 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_55_Mean_W34` | 1.23299e-07 | 0.313397 | 0.727248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_55_Mean_W55` | 0.0242562 | 0.543053 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_SMA_89_Min_W55` | 1.93736e-05 | 0.807286 | 0.942896 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_TEMA_13_Slope_W144` | 0.763279 | 0.110016 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_TEMA_8_Rank_W3` | 5.47719e-113 | 0.272729 | 0.694347 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_12h_trend_TRIMA_34_Std_W8` | 9.0046e-24 | 0.0980765 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_13_Std_W8` | 1.15901e-62 | 0.19948 | 0.629119 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_8_Lag_13` | 6.40082e-35 | 0.660533 | 0.888426 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_CMO_8_ZScore_W13` | 2.25181e-144 | 0.941922 | 0.978293 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Hist_8-34-9_Rank_W144` | 2.39473e-199 | 0.482685 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_21-89-13_Min_W144` | 4.60046e-138 | 0.276132 | 0.699442 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_34-144-21_Log1p` | 0 | 0.148177 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_55-144-21_Max_W34` | 0 | 0.142377 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Line_8-21-5_Mean_W34` | 5.29495e-200 | 0.426882 | 0.797844 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Signal_13-55-13_DecayLinear_W21` | 1.44393e-238 | 0.230588 | 0.665105 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACD-Signal_34-89-13_Kurt_W34` | 2.39045e-38 | 0.46301 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_12-26-9_TsRank_W21` | 0.0649157 | 0.736455 | 0.911457 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_55-144-21_Max_W34` | 9.66712e-88 | 0.0554526 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Hist_8-34-9_Range_W5` | 2.5909e-08 | 0.0463392 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Line_34-89-13_Mean_W21` | 9.15441e-170 | 0.076623 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Signal_12-26-9_Rank_W34` | 6.76708e-57 | 0.688908 | 0.892896 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDEXT-Signal_8-21-5_Slope_W144` | 0.0023968 | 0.65303 | 0.883913 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Line_13_Range_W3` | 4.71305e-57 | 0.798339 | 0.941776 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_13_DecayLinear_W5` | 4.40798e-301 | 0.270989 | 0.694347 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_3_Slope_W8` | 4.63303e-185 | 0.103335 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MACDFIX-Signal_9_Max_W144` | 8.62758e-198 | 0.0603511 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MOM_144_Min_W144` | 2.15171e-156 | 0.460334 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_MOM_21_Momentum_L8` | 1.84309e-40 | 0.67093 | 0.888633 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_21-55-0_Min_W34` | 5.94736e-248 | 0.10865 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_34-89-0_Std_W21` | 0.00859847 | 0.426629 | 0.797844 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_PPO_55-144-0_Range_W5` | 3.86e-26 | 0.224461 | 0.658858 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_233_Sign` | 1.28013e-244 | 0.576417 | 0.849235 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_55_ZScore_W5` | 2.27543e-45 | 0.121247 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCP_9_Range_W55` | 7.20561e-06 | 0.268648 | 0.694347 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_13_144_Cross` | 2.29268e-241 | 0.108229 | 0.565959 | True | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_13_Slope_W13` | 5.51224e-63 | 0.471784 | 0.813605 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_144_Slope_W34` | 1.22659e-179 | 0.0927559 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR100_233_Range_W5` | 0.00643443 | 0.884619 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_ROCR_12_Std_W233` | 0.00292236 | 0.374186 | 0.76524 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_14_55_Cross` | 0 | 0.496331 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_233_Slope_W89` | 1.39356e-299 | 0.0171408 | 0.407297 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_RSI_9_Momentum_L55` | 1.36621e-73 | 0.302823 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_STOCHRSI-fastd_21-5-3-0_Kurt_W21` | 0.00413113 | 0.541967 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_momentum_TRIX_89_ZScore_W233` | 1.64497e-147 | 0.248921 | 0.68248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-INTERCEPT_55_TsRank_W21` | 0.00756794 | 0.16167 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_10_Momentum_L21` | 8.72144e-05 | 0.815536 | 0.942896 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_144_Mean_W13` | 7.16971e-305 | 0.190927 | 0.614663 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_144_Std_W55` | 6.06548e-12 | 0.0395065 | 0.558922 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_89_Lag_2` | 4.34694e-292 | 0.0673328 | 0.560267 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG-SLOPE_8_Momentum_L5` | 0.682676 | 0.648424 | 0.883913 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_10_Max_W144` | 1.16357e-210 | 0.2388 | 0.677052 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_10_Range_W13` | 0.221931 | 0.346323 | 0.744782 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_LINEARREG_8_Mean_W55` | 0 | 0.0976311 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_STDDEV_5_Skew_W144` | 1.37279e-17 | 0.992529 | 0.996523 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_TSF_13_Range_W144` | 2.22228e-14 | 0.0120795 | 0.37673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_VAR_34_Momentum_L233` | 5.26776e-07 | 0.82763 | 0.946114 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_statistics_VAR_89_Std_W3` | 1.17111e-05 | 0.433235 | 0.804738 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_BBANDS-Lower_13_Kurt_W144` | 1.97099e-57 | 0.716106 | 0.904631 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_BBANDS-Upper_13_Max_W89` | 2.02915e-121 | 0.20417 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_DEMA_21_Momentum_L8` | 2.75746e-295 | 0.104856 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_EMA_100_Rank_W144` | 0 | 0.253961 | 0.685007 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_KAMA_5_TsArgmax_W21` | 0 | 0.204846 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_KAMA_8_ZScore_W34` | 0 | 0.114084 | 0.569282 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_55_ZScore_W34` | 1.80698e-262 | 0.468212 | 0.813605 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_5_Std_W21` | 6.47838e-37 | 0.0596635 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_MAVP_89_Skew_W13` | 1.03825e-128 | 0.0347329 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_MA_55_DecayLinear_W13` | 0 | 0.0908966 | 0.565959 | False | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_MIDPOINT_21_Std_W89` | 0.000575689 | 0.188353 | 0.613666 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_MIDPOINT_55_Rank_W144` | 0 | 0.0402672 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_SMA_200_Max_W5` | 1.08261e-37 | 0.362555 | 0.748784 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_T3_8_Log1p` | 6.53858e-08 | 0.671816 | 0.888633 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_TEMA_55_Skew_W5` | 6.53161e-60 | 0.640311 | 0.882639 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_21_ZScore_W233` | 0 | 0.210511 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_233_Range_W13` | 0.000384311 | 0.303515 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `close_1h_trend_TRIMA_34_TsRank_W5` | 4.10246e-299 | 0.151434 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_12h_perm_21_Mean_W34` | 4.26827e-06 | 0.161283 | 0.580909 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_12h_shannon_taker_ratio_100_Min_W21` | 0.814168 | 0.847274 | 0.948244 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_12h_shannon_taker_ratio_100_Rank_W34` | 0.0157295 | 0.272191 | 0.694347 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_12h_shannon_volume_21_Max_W89` | 4.52626e-08 | 0.614506 | 0.868665 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_1h_apen_55_Momentum_L21` | 1.15384e-52 | 0.214087 | 0.635888 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_1h_hurst_55_Min_W144` | 1.09291e-13 | 0.961796 | 0.988796 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `ent_1h_shannon_close_return_21_ZScore_W3` | 1.47169e-114 | 0.611536 | 0.866922 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` | 0.000490005 | 0.927148 | 0.975711 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` | 1.95069e-05 | 0.932813 | 0.975836 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` | 0.000742349 | 0.877286 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_momentum_MINUS-DM_144_Max_W8` | 0.000634578 | 0.552837 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` | 3.68927e-57 | 0.165016 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` | 1.54833e-263 | 0.141597 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_statistics_BETA_144_Slope_W233` | 4.8443e-12 | 0.958967 | 0.988796 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_statistics_BETA_34_ZScore_W8` | 0.832145 | 0.150471 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_21_Slope_W89` | 0.00188272 | 0.105499 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_55_ZScore_W3` | 0.00316369 | 0.0623395 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_statistics_CORREL_8_Skew_W3` | 1.01026e-29 | 0.243993 | 0.681537 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` | 7.72755e-27 | 0.471854 | 0.813605 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` | 1.42811e-104 | 0.124533 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroondown_233_Slope_W233` | 4.28102e-63 | 0.787965 | 0.933954 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroondown_34_ZScore_W8` | 4.78067e-60 | 0.128667 | 0.578424 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROON-aroonup_89_DecayLinear_W13` | 1.24734e-308 | 0.00340797 | 0.198888 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_momentum_AROONOSC_144_Std_W13` | 0.00187743 | 0.601911 | 0.860192 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_momentum_MINUS-DM_21_Max_W13` | 8.31022e-168 | 0.380755 | 0.765804 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_momentum_PLUS-DM_8_Max_W144` | 2.0168e-65 | 0.158276 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_13_ZScore_W13` | 2.24146e-10 | 0.39014 | 0.766113 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_21_Range_W21` | 1.14e-11 | 0.416466 | 0.796232 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_statistics_BETA_5_21_Cross` | 1.07198e-15 | 0.52086 | 0.822498 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_statistics_CORREL_89_Lag_8` | 1.87768e-27 | 0.442656 | 0.810673 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_statistics_CORREL_8_Mean_W55` | 2.7616e-84 | 0.385204 | 0.765804 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_trend_MIDPRICE_144_Min_W5` | 5.54861e-135 | 0.373222 | 0.76524 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hl_1h_trend_SAR_0.02-0.2_Kurt_W144` | 8.83272e-30 | 0.384037 | 0.765804 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` | 9.89252e-21 | 0.554458 | 0.839948 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_144_ZScore_W89` | 4.99078e-12 | 0.840958 | 0.948244 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADXR_14_Range_W233` | 0.0263522 | 0.435453 | 0.804782 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ADX_34_Mean_W34` | 1.08335e-10 | 0.349436 | 0.744782 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_13_Kurt_W5` | 1.03112e-06 | 0.565411 | 0.842209 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_34_Range_W3` | 4.66416e-40 | 0.271906 | 0.694347 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_34_Skew_W34` | 2.86565e-36 | 0.105785 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_CCI_5_Mean_W13` | 7.34923e-248 | 0.728414 | 0.9091 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_13_Std_W89` | 2.17865e-09 | 0.111302 | 0.566729 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_13_TsArgmax_W21` | 0.0287235 | 0.80447 | 0.942326 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_144_Mean_W34` | 0.00232884 | 0.092837 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_34_Momentum_L21` | 1.93786e-06 | 0.452126 | 0.810673 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_DX_55_Lag_8` | 6.0707e-08 | 0.902577 | 0.962283 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_MINUS-DI_144` | 2.31353e-285 | 0.269079 | 0.694347 | True | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` | 1.00845e-79 | 0.121543 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` | 3.44355e-75 | 0.638968 | 0.882639 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` | 1.72162e-154 | 0.263088 | 0.694347 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` | 4.21555e-163 | 0.134568 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` | 0 | 0.0935466 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` | 0 | 0.321411 | 0.727248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` | 0.00153407 | 0.138934 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_WILLR_20_Kurt_W55` | 6.70477e-56 | 0.391501 | 0.766113 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_momentum_WILLR_55_Rank_W13` | 4.07937e-238 | 0.0627247 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_14_Rank_W5` | 2.82647e-36 | 0.0583428 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_21_Lag_13` | 0.0202841 | 0.581502 | 0.850937 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_ATR_5_20_Cross` | 8.03136e-25 | 0.00292803 | 0.198888 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_12h_volatility_NATR_13_Lag_1` | 6.90926e-67 | 0.862402 | 0.949727 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ADX_144_Rank_W21` | 9.53894e-12 | 0.38505 | 0.765804 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ADX_89_Max_W3` | 0.695763 | 0.0887104 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_13_Range_W5` | 1.89576e-71 | 0.037598 | 0.558922 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_34_ZScore_W34` | 7.80739e-182 | 0.304462 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_CCI_55_Rank_W8` | 3.48875e-104 | 0.923968 | 0.975711 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_DX_144_Std_W144` | 8.04537e-39 | 0.00209818 | 0.198888 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_DX_55_Rank_W8` | 3.37888e-112 | 0.0643095 | 0.560267 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_MINUS-DI_21_Momentum_L144` | 2.71949e-192 | 0.848376 | 0.948244 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_PLUS-DI_144_Max_W5` | 0 | 0.708744 | 0.90451 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_PLUS-DI_21_Min_W8` | 5.76384e-308 | 0.482533 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowd_13-3-0-3-0_Range_W55` | 1.50004e-57 | 0.620775 | 0.870232 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowd_34-5-0-5-0_Mean_W34` | 3.79101e-135 | 0.0566294 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_21-3-0-3-0_TsRank_W21` | 3.53094e-130 | 0.260584 | 0.691656 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_21-5-0-5-0_Lag_21` | 2.94433e-08 | 0.745989 | 0.912835 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_34-5-0-3-0_Lag_3` | 7.56601e-248 | 0.147234 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCH-slowk_55-5-0-5-0_Skew_W233` | 5.3467e-309 | 0.0592281 | 0.558922 | True | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_21-5-0_Lag_21` | 2.94433e-08 | 0.745989 | 0.912835 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_5-3-0_Slope_W89` | 1.17179e-160 | 0.499417 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastd_5-3-0_ZScore_W21` | 1.40597e-35 | 0.906359 | 0.962283 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_STOCHF-fastk_21-5-0_Mean_W55` | 0 | 0.00358717 | 0.198888 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_ULTOSC_5-10-20_Slope_W3` | 1.27277e-46 | 0.80289 | 0.942326 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_momentum_WILLR_21_Skew_W34` | 3.3739e-182 | 0.0141715 | 0.392865 | True | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `hlc_1h_volatility_ATR_233_Skew_W55` | 0.00239433 | 0.963036 | 0.988796 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `hlcv_12h_momentum_MFI_55_Min_W233` | 0.623774 | 0.510505 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlcv_1h_momentum_MFI_89_Rank_W3` | 2.07498e-10 | 0.713461 | 0.904631 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `hlcv_1h_volume_ForceIndex_Rank_W3` | 3.41301e-05 | 0.418189 | 0.796474 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_12h_amihud_illiq_55_Max_W5` | 1.38934e-31 | 0.393885 | 0.767768 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_12h_cs_spread_21_Rank_W8` | 0.0447361 | 0.10079 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_12h_kyle_lambda_21_Momentum_L13` | 1.1328e-06 | 0.703353 | 0.899931 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_12h_ofi_zscore_13_Skew_W13` | 0.54161 | 0.379384 | 0.765804 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_12h_roll_spread_55_Min_W34` | 0.485496 | 0.162749 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_12h_vpin_50_Kurt_W13` | 7.47262e-19 | 0.878864 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `ms_1h_kyle_lambda_21_ZScore_W144` | 0.300262 | 0.0613853 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` | 3.7668e-28 | 0.0545481 | 0.558922 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` | 4.55524e-74 | 0.678496 | 0.888633 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` | 5.69302e-06 | 0.761611 | 0.922436 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` | 0.142563 | 0.865984 | 0.949727 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` | 5.69416e-25 | 0.549802 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` | 8.48329e-15 | 0.695825 | 0.894888 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` | 8.44002e-14 | 0.990466 | 0.996523 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` | 0.000517517 | 0.766764 | 0.925237 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` | 4.80663e-14 | 0.279607 | 0.702262 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` | 8.60857e-11 | 0.409324 | 0.791288 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` | 2.12843e-09 | 0.624802 | 0.870883 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` | 0.115727 | 0.162849 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` | 9.29047e-12 | 0.457226 | 0.810673 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` | 5.33741e-36 | 0.745845 | 0.912835 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` | 0.000505186 | 0.843177 | 0.948244 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` | 0.29692 | 0.509645 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` | 9.49123e-39 | 0.04793 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` | 4.56681e-104 | 0.123687 | 0.575388 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_144_Range_W8` | 0.370225 | 0.181683 | 0.608456 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` | 1.25673e-24 | 0.666597 | 0.888633 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_MOM_89_Std_W21` | 2.82344e-42 | 0.721156 | 0.906441 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` | 2.94784e-19 | 0.555204 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` | 0.0276158 | 0.453492 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` | 1.55544e-16 | 0.654944 | 0.883913 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` | 5.78415e-06 | 0.183345 | 0.609928 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` | 0.0186726 | 0.617768 | 0.870232 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` | 0.747133 | 0.976079 | 0.995983 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` | 2.06742e-103 | 0.00805528 | 0.334965 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_ROC_5_Lag_34` | 7.04989e-06 | 0.509517 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` | 0.881088 | 0.554341 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` | 1.14756e-22 | 0.402811 | 0.782111 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` | 9.48441e-12 | 0.319517 | 0.727248 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` | 6.32562e-07 | 0.978019 | 0.995983 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` | 8.7025e-06 | 0.515015 | 0.821062 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` | 0.00545673 | 0.878661 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` | 3.95267e-07 | 0.847164 | 0.948244 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` | 5.4621e-16 | 0.492163 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` | 0.000173584 | 0.587741 | 0.855051 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` | 0.00152909 | 0.2086 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` | 8.46531e-06 | 0.518626 | 0.821569 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` | 1.60247e-06 | 0.556075 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` | 5.86827e-29 | 0.0991988 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` | 3.45908e-25 | 0.930405 | 0.975711 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` | 0.000587862 | 0.906266 | 0.962283 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` | 2.54559e-35 | 0.283019 | 0.702619 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` | 0.694698 | 0.0603335 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` | 6.6687e-06 | 0.452798 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` | 0.00232611 | 0.390888 | 0.766113 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` | 1.1422e-57 | 0.95942 | 0.988796 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` | 0.070576 | 0.553174 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` | 0.000170625 | 0.485445 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` | 4.68423e-09 | 0.589681 | 0.85538 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` | 0.167252 | 0.169677 | 0.587815 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` | 0.000666509 | 0.189238 | 0.613666 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` | 4.28565e-17 | 0.802632 | 0.942326 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` | 2.82979e-17 | 0.912272 | 0.966504 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_EMA_100_Skew_W3` | 6.95787e-28 | 0.864911 | 0.949727 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` | 2.38463e-15 | 0.655406 | 0.883913 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MAVP_34_Max_W5` | 6.00593e-21 | 0.737126 | 0.911457 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` | 0.155864 | 0.446955 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` | 0.01044 | 0.332979 | 0.735207 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_MA_89_Skew_W5` | 2.94097e-23 | 0.930514 | 0.975711 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_SMA_144_Mean_W55` | 4.55242e-29 | 0.598085 | 0.86007 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_T3_5_Skew_W21` | 0.0752702 | 0.164276 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` | 0.137838 | 0.839778 | 0.948244 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TEMA_5_Min_W13` | 1.47042e-62 | 0.987941 | 0.996523 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` | 4.54078e-28 | 0.528707 | 0.832255 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` | 0.234511 | 0.998132 | 0.998132 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` | 0.579092 | 0.360845 | 0.748784 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` | 0.582748 | 0.851537 | 0.948244 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_cycle_HT-PHASOR-InPhase_Kurt_W34` | 1.27018e-52 | 0.700823 | 0.898999 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_APO_5-13-0_Mean_W34` | 6.15948e-15 | 0.581314 | 0.850937 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_APO_55-233-0_Range_W233` | 0.00051362 | 0.186476 | 0.613666 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_CMO_55_Slope_W5` | 5.28109e-14 | 0.412295 | 0.791288 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_13-34-9_Min_W5` | 7.52129e-30 | 0.316615 | 0.727248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_13-34-9_Momentum_L8` | 1.40101e-08 | 0.189388 | 0.613666 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_21-55-9_Momentum_L144` | 9.27269e-36 | 0.508065 | 0.817176 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_21-55-9_TsArgmax_W13` | 8.48255e-11 | 0.864722 | 0.949727 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_5-21-5_Skew_W8` | 2.13166e-119 | 0.622591 | 0.870232 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Line_55-233-34_Min_W5` | 2.8316e-11 | 0.683068 | 0.891264 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACD-Signal_12-26-9_Std_W144` | 1.4055e-12 | 0.983852 | 0.996523 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Hist_13-34-9_TsRank_W13` | 0.00917756 | 0.943004 | 0.978293 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Hist_21-89-13_Range_W5` | 7.87468e-65 | 0.0583701 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Line_13-34-9_Std_W13` | 3.86722e-47 | 0.159836 | 0.580909 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Line_55-144-21_Slope_W8` | 0.99534 | 0.0799517 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Signal_21-89-13_Rank_W144` | 0.233059 | 0.882902 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDEXT-Signal_34-89-13_Range_W233` | 0.485258 | 0.246871 | 0.682308 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Hist_3_Std_W3` | 9.93327e-11 | 0.337971 | 0.739682 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Line_13_Mean_W8` | 5.8111e-32 | 0.503081 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MACDFIX-Line_5_Momentum_L3` | 4.08619e-08 | 0.830457 | 0.946114 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MOM_13_Mean_W233` | 1.22642e-20 | 0.96733 | 0.991166 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_MOM_34_Momentum_L55` | 3.62255e-17 | 0.991151 | 0.996523 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_21-55-0_Clip` | 0.000962287 | 0.730718 | 0.909297 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_8-34-0_Mean_W3` | 4.13354e-25 | 0.574999 | 0.849235 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_PPO_8-34-0_Rank_W34` | 3.09273e-14 | 0.425228 | 0.797844 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_13_Kurt_W144` | 5.1158e-13 | 0.842581 | 0.948244 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_21_Mean_W13` | 4.78298e-18 | 0.500599 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCP_8_Lag_21` | 6.95044e-29 | 0.328069 | 0.72845 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROCR100_233_Skew_W3` | 1.51433e-52 | 0.28006 | 0.702262 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_ROC_55_Min_W144` | 2.24285e-16 | 0.411169 | 0.791288 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_233_Mean_W89` | 8.28602e-51 | 0.677361 | 0.888633 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_34_Rank_W5` | 1.11472e-16 | 0.510282 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_7_Std_W3` | 6.89117e-05 | 0.693591 | 0.89432 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_7_TsArgmax_W13` | 2.05157e-41 | 0.665282 | 0.888633 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_RSI_8_ZScore_W5` | 0.00270099 | 0.59608 | 0.859665 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_STOCHRSI-fastk_14-5-3-0_TsArgmax_W5` | 5.68011e-13 | 0.814685 | 0.942896 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_TRIX_55_Min_W5` | 4.92242e-10 | 0.818184 | 0.942896 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_momentum_TRIX_8_Skew_W5` | 7.32961e-71 | 0.334508 | 0.735329 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_233_Kurt_W89` | 1.68791e-32 | 0.0679212 | 0.560267 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_89_Kurt_W5` | 1.98151e-06 | 0.569641 | 0.845984 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-INTERCEPT_89_Rank_W5` | 5.0759e-34 | 0.233052 | 0.66835 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG-SLOPE_21_Kurt_W34` | 0.165966 | 0.107811 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_55_Min_W3` | 1.40434e-34 | 0.859637 | 0.949727 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_55_Slope_W8` | 3.3493e-27 | 0.873565 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_LINEARREG_8_Lag_13` | 7.6197e-06 | 0.557234 | 0.839948 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_STDDEV_89_Clip` | 8.58852e-28 | 0.994674 | 0.996671 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_STDDEV_8_Lag_34` | 1.67231e-93 | 0.170808 | 0.587815 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_VAR_13_Mean_W89` | 7.50096e-25 | 0.109442 | 0.565959 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_statistics_VAR_89_Mean_W5` | 3.26642e-24 | 0.162811 | 0.580909 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_BBANDS-Lower_20_Std_W89` | 1.82193e-05 | 0.976397 | 0.995983 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_BBANDS-Middle_21_Max_W233` | 0.619093 | 0.535285 | 0.837486 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_EMA_144_Std_W55` | 4.06018e-20 | 0.207032 | 0.629119 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_EMA_55_ZScore_W89` | 3.43235e-07 | 0.517227 | 0.821569 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_KAMA_21_Lag_3` | 8.20722e-10 | 0.82973 | 0.946114 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_KAMA_34_Skew_W55` | 4.60085e-07 | 0.747228 | 0.912835 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MA_5_Rank_W13` | 0.000189326 | 0.287022 | 0.705538 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MIDPOINT_13_Mean_W233` | 0.385284 | 0.817501 | 0.942896 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_MIDPOINT_89_Mean_W233` | 0.296784 | 0.985967 | 0.996523 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_10_Max_W21` | 9.33201e-27 | 0.540721 | 0.839948 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_13_Range_W13` | 1.24307e-21 | 0.359424 | 0.748784 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_144_ZScore_W8` | 0.951216 | 0.483555 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_50_ZScore_W8` | 1.00623e-46 | 0.942022 | 0.978293 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_5_Lag_34` | 5.37934e-42 | 0.215535 | 0.636402 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_SMA_5_Skew_W144` | 7.17753e-08 | 0.648261 | 0.883913 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TEMA_13_Kurt_W55` | 1.47398e-64 | 0.510338 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TEMA_55_Distance` | 0.772935 | 0.204209 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TRIMA_55_Momentum_L3` | 1.26065e-16 | 0.785069 | 0.932737 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_TRIMA_5_Momentum_L21` | 0.0308233 | 0.112958 | 0.569282 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker-ratio_1h_trend_WMA_89_Min_W233` | 9.079e-08 | 0.63626 | 0.882639 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` | 2.83273e-49 | 0.00194605 | 0.198888 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `taker_12h_ratio_trend_SMA_5_50_Cross` | 0.0589936 | 0.748904 | 0.912835 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `taker_1h_ratio_trend_SMA_8_50_Ratio` | 4.34939e-21 | 0.487297 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `tr_12h_rsj_21_Max_W21` | 3.92642e-34 | 0.553132 | 0.839948 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `tr_12h_ud_vol_ratio_21_Max_W13` | 2.18391e-15 | 0.98443 | 0.996523 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `tr_1h_cvar_5pct_55_TsArgmin_W21` | 1.16737e-08 | 0.315651 | 0.727248 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `tr_1h_gpr_100_Lag_2` | 0 | 0.0420091 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `tr_1h_gpr_55_Kurt_W5` | 1.6055e-120 | 0.124068 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `tr_1h_rsj_21_Rank_W13` | 2.0713e-156 | 0.376527 | 0.765804 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` | 7.56812e-13 | 0.101807 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` | 3.0858e-16 | 0.288919 | 0.706718 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_12-26-0_Mean_W89` | 0.000115266 | 0.445627 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_13-55-0_Range_W13` | 0.00010619 | 0.601374 | 0.860192 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_APO_5-13-0_Skew_W3` | 1.12989e-58 | 0.684076 | 0.891264 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_CMO_14_Max_W144` | 1.35012e-89 | 0.0696124 | 0.560267 | False | False | removed:p_value |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_CMO_14_Rank_W13` | 2.56312e-12 | 0.244479 | 0.681537 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` | 0.836763 | 0.237045 | 0.675916 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` | 2.3254e-19 | 0.17644 | 0.59489 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` | 5.98162e-20 | 0.458826 | 0.810673 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` | 2.67236e-50 | 0.271697 | 0.694347 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` | 0.37153 | 0.0755232 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` | 6.10603e-05 | 0.653623 | 0.883913 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` | 5.6867e-11 | 0.350567 | 0.744782 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` | 5.57998e-08 | 0.737933 | 0.911457 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` | 2.19924e-26 | 0.118665 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` | 1.37442e-27 | 0.0799076 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` | 5.28994e-18 | 0.479791 | 0.815978 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` | 0.00778446 | 0.0986231 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` | 7.00323e-50 | 0.101652 | 0.565959 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` | 7.34298e-06 | 0.257111 | 0.689777 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCP_89_Min_W13` | 1.22605e-21 | 0.576935 | 0.849235 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR100_55_Range_W13` | 6.26924e-10 | 0.197864 | 0.62888 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR100_9_Momentum_L34` | 0.000563332 | 0.306976 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR_13_ZScore_W13` | 1.63295e-32 | 0.0720307 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROCR_55_Kurt_W5` | 0.353782 | 0.750025 | 0.912835 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_ROC_5_Slope_W55` | 4.2231e-05 | 0.0233849 | 0.50735 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_RSI_13_Kurt_W21` | 5.78001e-10 | 0.472837 | 0.813605 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_RSI_6_Min_W13` | 9.82116e-31 | 0.050373 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Min_W8` |  |  |  | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` | 1.70373e-15 | 0.890908 | 0.953998 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` | 0.293491 | 0.824092 | 0.945338 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_5_Max_W233` | 1.18771e-18 | 0.604431 | 0.860192 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_5_Max_W89` | 4.76731e-09 | 0.728737 | 0.9091 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_momentum_TRIX_89_Min_W5` | 0.0323926 | 0.204255 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` | 0.308313 | 0.132631 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` | 0.00137998 | 0.886198 | 0.950995 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_13_Range_W89` | 0.0522321 | 0.426903 | 0.797844 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_144_Kurt_W89` | 4.04386e-05 | 0.818123 | 0.942896 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_34_Kurt_W5` | 6.07697e-48 | 0.013791 | 0.392865 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_TSF_34_Lag_5` | 0.0808542 | 0.207459 | 0.629119 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_13_Kurt_W8` | 1.57687e-17 | 0.584035 | 0.852145 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_21_Kurt_W144` | 0.0125387 | 0.486715 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_statistics_VAR_34_Kurt_W8` | 0.274836 | 0.645844 | 0.883913 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` | 2.50155e-07 | 0.669051 | 0.888633 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_233_Lag_2` | 5.75679e-05 | 0.355871 | 0.746726 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_233_Min_W144` | 0.279194 | 0.297286 | 0.720126 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_89_Std_W233` | 6.32199e-06 | 0.654764 | 0.883913 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_DEMA_8_Mean_W34` | 8.30567e-46 | 0.767631 | 0.925237 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_13_Rank_W144` | 1.21692e-28 | 0.0329906 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_200_Slope_W144` | 0.293848 | 0.138658 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_EMA_21_Range_W13` | 0.0687038 | 0.307478 | 0.720644 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_KAMA_8_Lag_21` | 1.32565e-114 | 0.0668012 | 0.560267 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_MAVP_55_Range_W5` | 3.04594e-06 | 0.166226 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_MA_233_Mean_W89` | 0.672939 | 0.32408 | 0.727248 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_MIDPOINT_8_Abs` | 1.56638e-08 | 0.0419969 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_SMA_50_ZScore_W233` | 1.21374e-24 | 0.714111 | 0.904631 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_T3_21_Min_W55` | 2.9589e-32 | 0.173348 | 0.588438 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_T3_8_Std_W5` | 4.70968e-10 | 0.605065 | 0.860192 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_TRIMA_55_Skew_W34` | 7.07693e-08 | 0.15413 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_12h_trend_WMA_89_Max_W233` | 4.44385e-13 | 0.292239 | 0.711352 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_CMO_34_Max_W8` | 1.66325e-17 | 0.196524 | 0.628625 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Hist_55-233-34_Kurt_W8` | 1.60073e-30 | 0.284456 | 0.702691 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Hist_55-233-34_Min_W89` | 7.69217e-12 | 0.755953 | 0.917811 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Line_21-89-13_Rank_W13` | 7.8171e-52 | 0.0021949 | 0.198888 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Line_55-233-34_Range_W233` | 0.912275 | 0.0949208 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_21-55-9_Lag_2` | 0.00105994 | 0.67805 | 0.888633 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_21-89-13_TsArgmin_W5` | 1.22115e-49 | 0.0160522 | 0.400501 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACD-Signal_55-233-34_Skew_W13` | 1.52085e-66 | 0.0204944 | 0.464849 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_34-144-21_TsArgmin_W13` | 5.3043e-06 | 0.356154 | 0.746726 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_8-21-5_Min_W21` | 1.95196e-30 | 0.0160046 | 0.400501 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Hist_8-34-9_Kurt_W8` | 1.1323e-73 | 0.165973 | 0.580909 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Line_34-144-21_Slope_W3` | 1.42236e-21 | 0.0377514 | 0.558922 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Line_55-144-21_Min_W13` | 0.598096 | 0.227958 | 0.661344 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDEXT-Signal_34-144-21_ZScore_W144` | 0.0134037 | 0.455306 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_13_Lag_5` | 8.93696e-39 | 0.0965353 | 0.565959 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_21_Mean_W89` | 1.36372e-11 | 0.454431 | 0.810673 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Hist_8_Std_W5` | 5.21712e-30 | 0.56221 | 0.839948 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_8_Std_W55` | 0.385353 | 0.259728 | 0.691656 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_9_Max_W21` | 0.750183 | 0.480838 | 0.815978 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MACDFIX-Signal_9_Max_W233` | 5.91696e-21 | 0.107034 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_144_Std_W13` | 0.000736757 | 0.777746 | 0.932406 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_21_Clip` | 1.33042e-51 | 0.00637324 | 0.289113 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_21_Min_W55` | 1.83456e-86 | 0.639363 | 0.882639 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_MOM_34_ZScore_W55` | 1.01062e-47 | 0.0342649 | 0.558922 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_PPO_34-89-0_Kurt_W5` | 5.22681e-13 | 0.899125 | 0.960735 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCP_21_TsArgmax_W5` | 0.0075594 | 0.282575 | 0.702619 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCR100_8_Lag_2` | 3.7166e-46 | 0.0100739 | 0.352019 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROCR100_8_Slope_W233` | 2.36454e-26 | 0.0808638 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_ROC_34_ZScore_W55` | 2.59899e-19 | 0.132454 | 0.580909 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_14_Skew_W5` | 1.05682e-07 | 0.595153 | 0.859665 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_233_Rank_W21` | 3.10777e-117 | 0.00227709 | 0.198888 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_34_Kurt_W34` | 0.00305485 | 0.163074 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_34_Rank_W34` | 2.98488e-116 | 0.00329608 | 0.198888 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_8_Lag_1` | 5.26455e-43 | 0.00432055 | 0.215595 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_RSI_9_TsArgmax_W13` | 0.0948289 | 0.468041 | 0.813605 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_STOCHRSI-fastd_9-5-3-0_Mean_W89` | 5.29225e-05 | 0.621824 | 0.870232 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_momentum_STOCHRSI-fastk_21-8-5-0_Std_W21` | 4.55206e-19 | 0.155491 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_statistics_LINEARREG-SLOPE_89_Mean_W21` | 3.04366e-07 | 0.716595 | 0.904631 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_statistics_LINEARREG-SLOPE_8_Slope_W34` | 1.51713e-84 | 0.00272124 | 0.198888 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_statistics_STDDEV_55_Std_W8` | 6.18727e-08 | 0.226457 | 0.660832 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_statistics_TSF_5_Skew_W144` | 0.00649745 | 0.814728 | 0.942896 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_statistics_VAR_55_ZScore_W55` | 3.36093e-09 | 0.510311 | 0.817176 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_statistics_VAR_8_Std_W3` | 6.45217e-19 | 0.941674 | 0.978293 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_144_Max_W55` | 5.55597e-05 | 0.127536 | 0.578424 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_21_Mean_W3` | 3.04918e-14 | 0.0360313 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_55_Range_W55` | 9.68125e-09 | 0.930739 | 0.975711 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_89_Max_W13` | 3.15302e-29 | 0.0414666 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Middle_89_Mean_W55` | 1.05633e-14 | 0.0850589 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Upper_55_Momentum_L3` | 2.15226e-09 | 0.355758 | 0.746726 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_BBANDS-Upper_55_ZScore_W5` | 1.21285e-07 | 0.345769 | 0.744782 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_13_Max_W34` | 2.67333e-27 | 0.0435795 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_34_Momentum_L34` | 0.582952 | 0.864772 | 0.949727 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_DEMA_5_Std_W89` | 0.00343189 | 0.123002 | 0.575388 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_EMA_13_Max_W144` | 3.52036e-09 | 0.159858 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_HT-TRENDLINE_Lag_13` | 4.52486e-09 | 0.0459603 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_KAMA_233_Range_W144` | 4.53058e-10 | 0.717903 | 0.904631 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_KAMA_5_55_Ratio` | 1.87743e-41 | 0.24749 | 0.682308 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_MAVP_233_Momentum_L144` | 0.457042 | 0.674885 | 0.888633 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_MA_13_Max_W144` | 2.24774e-23 | 0.0691145 | 0.560267 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_MA_89_Range_W3` | 0.0179175 | 0.724832 | 0.908772 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_50_Rank_W13` | 3.2009e-42 | 0.322333 | 0.727248 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_55_Max_W144` | 2.44498e-22 | 0.0586707 | 0.558922 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_SMA_5_TsArgmin_W13` | 1.35503e-37 | 0.164463 | 0.580909 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_T3_5_21_Cross` | 1.51507e-41 | 0.00984204 | 0.352019 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_TEMA_5_Momentum_L144` | 3.13497e-55 | 0.85323 | 0.948244 | False | False | removed:icir |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_TRIMA_144_Mean_W13` | 9.17177e-07 | 0.104346 | 0.565959 | False | False | removed:ic_mean |
| `long_ETHUSDT_1h_4a8a0b37` | `volume_1h_trend_WMA_55_Max_W3` | 0.145798 | 0.061936 | 0.558922 | False | False | removed:ic_mean |
| `xsec_3sym_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-InPhase_Slope_W89` |  | 0.900698 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_cycle_HT-PHASOR-Quadrature_Min_W89` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_APO_34-89-0_Skew_W21` |  | 0.445448 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_DecayLinear_W13` |  | 0.588565 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_APO_5-13-0_Skew_W233` |  | 1 | 1 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Range_W8` |  | 0.67074 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_APO_55-144-0_Std_W144` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_CMO_89_Slope_W5` |  | 0.082453 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_CMO_8_Rank_W3` |  | 0.851827 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Hist_34-89-13_TsRank_W5` |  | 0.861944 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Hist_5-13-3_Lag_2` |  | 0.186301 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Lag_34` |  | 0.821816 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Line_12-26-9_Min_W8` |  | 0.745374 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-144-21_Range_W13` |  | 0.562979 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Line_34-89-13_ZScore_W89` |  | 0.363757 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Line_55-144-21_Min_W34` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACD-Signal_5-13-3_Max_W55` |  | 0.659122 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W144` |  | 0.770503 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_12-26-9_Slope_W3` |  | 0.0291897 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Hist_55-233-34_Max_W34` |  | 0.530456 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_12-26-9_DecayLinear_W21` |  | 0.841463 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_13-55-13_Range_W5` |  | 0.592795 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Line_5-13-3_Skew_W13` |  | 0.411164 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDEXT-Signal_13-55-13_Momentum_L55` |  | 0.0942374 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_21_Skew_W34` |  | 0.937405 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Hist_5_Mean_W13` |  | 0.505049 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_Momentum_L144` |  | 0.29783 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_13_ZScore_W13` |  | 0.196563 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Min_W144` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_21_Skew_W89` |  | 0.297547 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_5_ZScore_W13` |  | 0.196563 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_8_Range_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_DecayLinear_W5` |  | 0.938712 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Line_9_Range_W3` |  | 0.56715 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MACDFIX-Signal_8_Range_W144` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MOM_13_Min_W144` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_MOM_21` |  | 0.418336 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_PPO_13-55-0_Slope_W89` |  | 0.970664 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_Slope_W233` |  | 0.513393 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_PPO_21-55-0_TsRank_W5` |  | 0.60153 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCP_12_Skew_W233` |  | 0.972419 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCP_13_Range_W5` |  | 0.0259228 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCP_89_Kurt_W13` |  | 0.394539 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCP_8_Lag_1` |  | 0.675169 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCP_9_DecayLinear_W5` |  | 0.641173 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR100_21_Momentum_L144` |  | 0.575518 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR100_34_Mean_W89` |  | 0.994224 | 1 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR100_5_TsRank_W21` |  | 0.280923 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR100_9_Rank_W8` |  | 0.984496 | 0.993751 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR_13_Rank_W144` |  | 0.651397 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR_55_Rank_W3` |  | 0.141238 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROCR_5_Skew_W13` |  | 0.324786 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROC_55_Range_W89` |  | 0.863692 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROC_55_Std_W144` |  | 0.144826 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_ROC_89_Slope_W233` |  | 0.449247 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_RSI_14_Momentum_L55` |  | 0.44458 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_RSI_55_TsArgmax_W21` |  | 0.210833 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_RSI_8_Rank_W55` |  | 0.492353 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_14-5-3-0_Momentum_L233` |  | 0.70864 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_21-8-5-0_ZScore_W144` |  | 0.320946 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_55-8-5-0_Std_W3` |  | 0.374516 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastd_9-5-3-0_Kurt_W21` |  | 0.249464 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_STOCHRSI-fastk_9-5-3-0_Std_W3` |  | 0.856268 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_momentum_TRIX_21_Kurt_W5` |  | 0.292629 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_LINEARREG-ANGLE_13_Momentum_L13` |  | 0.518422 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_LINEARREG-INTERCEPT_5_Std_W233` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_13_Rank_W34` |  | 0.0488158 | 0.860528 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_14_Max_W233` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_LINEARREG-SLOPE_8_Momentum_L233` |  | 0.391814 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_LINEARREG_5_Std_W8` |  | 0.617611 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_STDDEV_13_ZScore_W21` |  | 0.147113 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_STDDEV_89_Skew_W5` |  | 0.326339 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_TSF_55_Kurt_W13` |  | 0.570917 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_TSF_89_Momentum_L8` |  | 0.184673 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_TSF_89_Range_W233` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_VAR_144_Log1p` |  | 0.884556 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_VAR_20_TsArgmin_W5` |  | 0.769643 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_VAR_55_TsRank_W5` |  | 0.112864 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_statistics_VAR_89_TsRank_W13` |  | 0.261129 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_144_Std_W21` |  | 0.643705 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_Slope_W3` |  | 0.39729 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Lower_89_TsRank_W5` |  | 0.182056 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_13_Kurt_W233` |  | 0.964952 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_144_Max_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_233_Min_W5` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Middle_34_Skew_W3` |  | 0.767544 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_BBANDS-Upper_89_Slope_W89` |  | 0.878069 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_DEMA_13_Slope_W55` |  | 0.564957 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_EMA_100_Mean_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_EMA_144_Kurt_W89` |  | 0.490937 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_EMA_200_Kurt_W55` |  | 0.719814 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_EMA_21_Mean_W34` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_EMA_55_ZScore_W8` |  | 0.721905 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_HT-TRENDLINE_ZScore_W144` |  | 0.789798 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_KAMA_21_Mean_W21` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_KAMA_233_Slope_W55` |  | 0.790148 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_KAMA_8_Lag_5` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_MAVP_233_Range_W144` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_MA_13_Kurt_W8` |  | 0.0231814 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_MA_21_Rank_W13` |  | 0.2672 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_MIDPOINT_21_Std_W34` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Mean_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_MIDPOINT_34_Rank_W144` |  | 0.554988 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_SMA_144_Min_W13` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_SMA_20_Kurt_W233` |  | 0.564346 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W34` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_SMA_55_Mean_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_SMA_89_Min_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_SMA_8_TsArgmin_W5` |  | 0.131177 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_T3_21_Min_W21` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TEMA_13_Slope_W144` |  | 0.368438 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TEMA_55_Kurt_W233` |  | 0.761143 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TEMA_5_Range_W3` |  | 0.968285 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TEMA_8_Rank_W3` |  | 0.72912 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TEMA_8_ZScore_W55` |  | 0.565584 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TRIMA_13_Range_W3` |  | 0.715838 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_TRIMA_34_Std_W8` |  | 0.782711 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_WMA_21_Momentum_L21` |  | 0.467054 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_WMA_233_Slope_W144` |  | 0.48073 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `close_12h_trend_WMA_55_Min_W34` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_apen_55_Max_W8` |  | 0.468946 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_fractal_dim_55_Kurt_W55` |  | 0.108818 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_perm_21_Mean_W34` |  | 0.14338 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_perm_55_Min_W233` |  | 0.655917 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_shannon_close_return_55_Slope_W13` |  | 0.22417 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Min_W21` |  | 0.653304 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Rank_W34` |  | 0.620289 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_shannon_taker_ratio_100_Skew_W144` |  | 0.459209 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_shannon_volume_21_Max_W89` |  | 0.558295 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ent_12h_shannon_volume_55_Max_W233` |  | 0.642748 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_14_Mean_W34` |  | 0.864907 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROON-aroondown_21_Skew_W233` |  | 0.210887 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_21_Momentum_L21` |  | 0.80551 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROON-aroonup_233_ZScore_W233` |  | 0.833705 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROONOSC_144_ZScore_W89` |  | 0.0797996 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROONOSC_14_TsArgmin_W13` |  | 0.3265 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROONOSC_25_Skew_W144` |  | 0.736321 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROONOSC_55_Kurt_W5` |  | 0.388681 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_AROONOSC_89_Kurt_W34` |  | 0.18803 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_144_Max_W8` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_MINUS-DM_34_Range_W5` |  | 0.783203 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_14_Min_W3` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_21_Min_W89` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_233_Slope_W5` |  | 0.707097 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_PLUS-DM_89_Kurt_W21` |  | 0.510642 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_momentum_PLUS_DM_8_233_Ratio` |  | 0.299604 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_BETA_144_Slope_W233` |  | 0.90408 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_BETA_233_Max_W144` |  | 0.918162 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_BETA_34_ZScore_W8` |  | 0.393808 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_CORREL_21_Slope_W89` |  | 0.795458 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_CORREL_233_Rank_W233` |  | 0.84088 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_CORREL_55_Slope_W233` |  | 0.87216 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_CORREL_55_ZScore_W3` |  | 0.615165 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_statistics_CORREL_8_Skew_W3` |  | 0.0980826 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_trend_MIDPRICE_144_Rank_W233` |  | 0.722978 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_trend_MIDPRICE_233_TsRank_W5` |  | 0.667996 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_trend_MIDPRICE_55_Min_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_trend_MIDPRICE_5_Mean_W5` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_trend_SAREXT_0-0-0.02-0.02-0.2-0.02-0.02-0.2_DecayLinear_W5` |  | 0.89312 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hl_12h_trend_SAR_0.02-0.2_DecayLinear_W21` |  | 0.936163 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ADXR_13_TsArgmax_W13` |  | 0.967623 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ADXR_144_ZScore_W89` |  | 0.902373 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ADXR_14_Range_W233` |  | 0.90161 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Skew_W21` |  | 0.345523 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ADX_13_Std_W89` |  | 0.212292 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ADX_34_Mean_W34` |  | 0.743139 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_CCI_13_Kurt_W5` |  | 0.418443 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_CCI_144_Skew_W34` |  | 0.00167964 | 0.42631 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_CCI_233_Min_W34` |  | 0.572821 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Range_W3` |  | 0.0337002 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_CCI_34_Skew_W34` |  | 0.0553063 | 0.892038 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_CCI_5_Mean_W13` |  | 0.430784 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_13_Kurt_W8` |  | 0.395441 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_13_Std_W89` |  | 0.679681 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_13_TsArgmax_W21` |  | 0.330527 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_144_Mean_W34` |  | 0.879265 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_144_TsArgmin_W13` |  | 0.562448 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_21_Rank_W21` |  | 0.902817 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_233_Skew_W13` |  | 0.131906 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_34_Momentum_L21` |  | 0.315297 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_55_Lag_8` |  | 0.655806 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_DX_89_Range_W34` |  | 0.0321302 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_144` |  | 0.462348 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_233_Rank_W55` |  | 0.475965 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_MINUS-DI_34_Slope_W5` |  | 0.9016 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_14_Slope_W233` |  | 0.805739 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_PLUS-DI_8_Momentum_L8` |  | 0.966217 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_13-5-0-3-0_Range_W55` |  | 0.970429 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_5-3-0-3-0_ZScore_W144` |  | 0.366834 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_55-5-0-5-0_ZScore_W13` |  | 0.304201 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowd_89-8-0-5-0_TsArgmax_W5` |  | 0.0266612 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_21-5-0-3-0_Kurt_W13` |  | 0.495454 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_34-5-0-3-0_Min_W233` |  | 0.859173 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_55-5-0-5-0_Rank_W144` |  | 0.977511 | 0.99139 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCH-slowk_89-8-0-5-0_Rank_W3` |  | 0.0190028 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Kurt_W34` |  | 0.722939 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastd_21-3-0_Momentum_L5` |  | 0.425204 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_13-3-0_DecayLinear_W13` |  | 0.403276 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_STOCHF-fastk_21-5-0_ZScore_W89` |  | 0.892431 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_34-89-233_Range_W13` |  | 0.664547 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_ULTOSC_5-10-20_Lag_3` |  | 0.212861 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_WILLR_14_Mean_W34` |  | 0.519855 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_WILLR_20_Kurt_W55` |  | 0.939839 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_WILLR_55_Rank_W13` |  | 0.968364 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_momentum_WILLR_89_Rank_W233` |  | 0.901735 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_ATR_14_Rank_W5` |  | 0.916241 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Lag_13` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Range_W8` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_ATR_21_Rank_W34` |  | 0.0242502 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_ATR_5_20_Cross` |  | 0.778575 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_NATR_13_Lag_1` |  | 0.431283 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_NATR_144_Momentum_L34` |  | 0.268195 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_NATR_55_Range_W21` |  | 0.635389 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlc_12h_volatility_NATR_89_Slope_W34` |  | 0.460587 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlcv_12h_momentum_MFI_13_Rank_W233` |  | 0.969633 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlcv_12h_momentum_MFI_55_Min_W233` |  | 0.406618 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlcv_12h_momentum_MFI_8_Skew_W8` |  | 0.760126 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `hlcv_12h_volume_EOM_14_Slope_W3` |  | 0.0830573 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_amihud_illiq_55_Max_W5` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_cs_spread_21_Rank_W8` |  | 0.715496 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_kyle_lambda_21_Momentum_L13` |  | 0.479481 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_ofi_zscore_13_Skew_W13` |  | 0.367513 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_ofi_zscore_21_Std_W144` |  | 0.759093 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_ofi_zscore_55_Kurt_W5` |  | 0.797549 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_ofi_zscore_55_Skew_W21` |  | 0.740401 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_roll_spread_55_Min_W34` |  | 0.0223053 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `ms_12h_vpin_50_Kurt_W13` |  | 0.232237 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_cycle_HT-PHASOR-InPhase_Range_W5` |  | 0.115562 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_Momentum_L3` |  | 0.91612 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_12-26-0_ZScore_W233` |  | 0.752472 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-34-0_Momentum_L144` |  | 0.827312 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_13-55-0_TsArgmin_W5` |  | 0.985373 | 0.993751 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_21-55-0_Min_W55` |  | 0.267727 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Momentum_L55` |  | 0.942862 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_34-89-0_Std_W21` |  | 0.878747 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_APO_8-21-0_TsRank_W21` |  | 0.644374 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Rank_W8` |  | 0.391856 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_13_Slope_W5` |  | 0.663516 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_CMO_21_Mean_W5` |  | 0.466279 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_12-26-9_Slope_W13` |  | 0.708756 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-34-9_Slope_W3` |  | 0.118392 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_13-55-13_Lag_3` |  | 0.657406 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_5-13-3_Kurt_W233` |  | 0.566834 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Hist_55-233-34_Min_W144` |  | 0.791366 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_5-21-5_Kurt_W8` |  | 0.243668 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Line_8-34-9_Std_W21` |  | 0.433405 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_13-55-13_Momentum_L8` |  | 0.30223 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACD-Signal_21-55-9_Kurt_W34` |  | 0.931773 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_Mean_W13` |  | 0.374788 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_13-55-13_TsRank_W5` |  | 0.757811 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Hist_8-21-5_Lag_8` |  | 0.943333 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_13-34-9_ZScore_W3` |  | 0.20683 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_5-13-3_Max_W5` |  | 0.339129 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-144-21_ZScore_W89` |  | 0.733511 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_55-233-34_Rank_W55` |  | 0.942055 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDEXT-Signal_8-21-5_Slope_W55` |  | 0.355911 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_13_Skew_W144` |  | 0.599044 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_3_Momentum_L8` |  | 0.259849 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Hist_5_TsRank_W5` |  | 0.95979 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Line_21_Momentum_L233` |  | 0.271087 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_13_Slope_W5` |  | 0.929844 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_21_TsRank_W5` |  | 0.792794 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MACDFIX-Signal_3_Rank_W21` |  | 0.698873 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_144_Range_W8` |  | 0.149025 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_34_TsRank_W21` |  | 0.585244 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_MOM_89_Std_W21` |  | 0.591215 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_13-34-0_Rank_W89` |  | 0.697957 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_34-89-0_Skew_W144` |  | 0.971224 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_PPO_55-233-0_Momentum_L144` |  | 0.646665 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_5_Range_W3` |  | 0.152048 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_89_Lag_21` |  | 0.948876 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCP_9_Momentum_L55` |  | 0.721941 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_21_Skew_W34` |  | 0.680837 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_55_Max_W34` |  | 0.421026 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR100_5_Mean_W8` |  | 0.865674 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_12_TsArgmin_W21` |  | 0.248579 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROCR_233_Slope_W3` |  | 0.369275 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_55_Kurt_W13` |  | 0.936214 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_ROC_5_Lag_34` |  | 0.494326 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_RSI_25_DecayLinear_W13` |  | 0.409078 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_14-3-3-0_TsRank_W21` |  | 0.373146 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_55-8-5-0_Min_W233` |  | 0.455358 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastd_9-5-3-0_Momentum_L3` |  | 0.577945 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_14-3-3-0_Skew_W3` |  | 0.73461 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_STOCHRSI-fastk_21-5-3-0_Std_W5` |  | 0.675354 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_13_Slope_W34` |  | 0.26625 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_144_Slope_W21` |  | 0.911179 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_21_Kurt_W55` |  | 0.454132 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_34_Slope_W5` |  | 0.853292 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_momentum_TRIX_5_Sign` |  | 0.707337 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_13_Mean_W233` |  | 0.939869 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_144_Momentum_L13` |  | 0.834727 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_233_TsArgmax_W5` |  | 0.0830726 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Lag_5` |  | 0.313116 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_34_Range_W8` |  | 0.266146 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-ANGLE_89_ZScore_W5` |  | 0.574887 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_233_ZScore_W55` |  | 0.250094 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_34_ZScore_W21` |  | 0.761647 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-INTERCEPT_89_Kurt_W233` |  | 0.660826 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_21_Lag_21` |  | 0.569133 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_233_Min_W144` |  | 0.533981 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_55_TsRank_W13` |  | 0.510424 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_89_Mean_W13` |  | 0.653754 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Range_W8` |  | 0.615605 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG-SLOPE_8_Rank_W13` |  | 0.90444 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_10_ZScore_W34` |  | 0.5397 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_233_Mean_W34` |  | 0.693213 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_89_Lag_8` |  | 0.741381 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_LINEARREG_8_Range_W34` |  | 0.972717 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_14_Kurt_W13` |  | 0.145979 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_55_Momentum_L233` |  | 0.378652 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Momentum_L13` |  | 0.359096 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_STDDEV_5_Rank_W3` |  | 0.62476 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Slope_W34` |  | 0.661005 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_13_Std_W8` |  | 0.430117 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_TSF_5_Skew_W8` |  | 0.542976 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_21_Mean_W13` |  | 0.88348 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_233_Mean_W8` |  | 0.853836 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_statistics_VAR_5_Rank_W34` |  | 0.512881 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_13_Lag_2` |  | 0.38279 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Lower_21_Min_W89` |  | 0.955753 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Middle_89_TsArgmax_W5` |  | 0.128602 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_144_Max_W89` |  | 0.9105 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_BBANDS-Upper_55_Momentum_L5` |  | 0.243823 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_34_Distance` |  | 0.394563 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_Momentum_L144` |  | 0.181437 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_DEMA_8_ZScore_W5` |  | 0.25178 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_EMA_100_Skew_W3` |  | 0.715424 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_KAMA_34_TsArgmin_W5` |  | 0.173031 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MAMA-FAMA_0.5-0.05_Min_W5` |  | 0.291156 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_34_Max_W5` |  | 0.574712 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_Momentum_L5` |  | 0.388687 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MAVP_5_ZScore_W5` |  | 0.738817 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MA_21_Min_W3` |  | 0.581088 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_Slope_W21` |  | 0.620033 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MA_34_TsArgmax_W21` |  | 0.409388 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_MA_89_Skew_W5` |  | 0.800057 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Lag_34` |  | 0.624481 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_SMA_100_Range_W144` |  | 0.850657 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_SMA_144_Mean_W55` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_T3_5_Skew_W21` |  | 0.524346 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_T3_89_DecayLinear_W5` |  | 0.617091 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_13_Kurt_W21` |  | 0.969985 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_233_Min_W144` |  | 0.467705 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_34_Slope_W21` |  | 0.87976 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TEMA_5_Min_W13` |  | 0.119388 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_21_TsArgmin_W5` |  | 0.495024 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_233_Min_W233` |  | 0.592616 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_TRIMA_5_ZScore_W55` |  | 0.695888 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_Kurt_W8` |  | 0.522737 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_WMA_13_ZScore_W13` |  | 0.862342 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker-ratio_12h_trend_WMA_34_Rank_W3` |  | 0.927874 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker_12h_ratio_statistics_LINEARREG_ANGLE_13_55_Ratio` |  | 0.236366 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `taker_12h_ratio_trend_SMA_5_50_Cross` |  | 0.642279 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `tr_12h_jb_100_Slope_W13` |  | 0.0465825 | 0.860528 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `tr_12h_rsj_21_Max_W21` |  | 0.971416 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Max_W13` |  | 0.76858 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `tr_12h_ud_vol_ratio_21_Std_W34` |  | 0.815524 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_cycle_HT-PHASOR-InPhase_Momentum_L233` |  | 0.0202109 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_cycle_HT-TRENDMODE_Momentum_L21` |  | 0.0400662 | 0.834712 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_APO_12-26-0_Mean_W89` |  | 0.75898 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_APO_13-55-0_Range_W13` |  | 0.108248 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_APO_5-13-0_Skew_W3` |  | 0.41081 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_APO_5-21-0_Max_W34` |  | 0.243152 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_CMO_14_Max_W144` |  | 0.777255 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_CMO_14_Rank_W13` |  | 0.985801 | 0.993751 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_CMO_34_Momentum_L5` |  | 0.806948 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_CMO_8_Momentum_L3` |  | 0.217494 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-34-9_Std_W89` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_Mean_W21` |  | 0.0779181 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_13-55-13_TsArgmax_W13` |  | 0.304084 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-144-21_Max_W55` |  | 0.962301 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Hist_34-89-13_TsArgmin_W13` |  | 0.640397 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Line_12-26-9_ZScore_W5` |  | 0.192583 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Range_W233` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-34-9_Skew_W34` |  | 0.487867 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Line_13-55-13_Skew_W55` |  | 0.109896 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Line_5-13-3_Momentum_L89` |  | 0.641085 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Line_55-144-21_Momentum_L8` |  | 0.378928 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_13-55-13_Range_W3` |  | 0.0532953 | 0.888255 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_5-21-5_Skew_W13` |  | 0.0499106 | 0.860528 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACD-Signal_55-144-21_TsArgmax_W13` |  | 0.00321217 | 0.535361 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_21-89-13_Rank_W8` |  | 0.451317 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_34-144-21_Skew_W21` |  | 0.838886 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Hist_8-34-9_Momentum_L3` |  | 0.403196 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_21-89-13_Skew_W144` |  | 0.64037 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_34-144-21_Rank_W13` |  | 0.0276579 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Line_5-13-3_Range_W3` |  | 0.796074 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_12-26-9_Slope_W55` |  | 0.0751329 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_13-34-9_Skew_W89` |  | 0.0655084 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_34-144-21_Range_W8` |  | 0.932065 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-13-3_Min_W3` |  | 0.312535 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_5-21-5_Slope_W13` |  | 0.724036 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDEXT-Signal_55-144-21_Max_W89` |  | 0.315433 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Hist_5_Slope_W21` |  | 0.489228 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_Min_W21` |  | 0.806725 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_13_ZScore_W89` |  | 0.0466462 | 0.860528 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Line_21_Mean_W13` |  | 0.0400298 | 0.834712 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_21_Momentum_L34` |  | 0.0442339 | 0.860528 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_Mean_W144` |  | 0.0915031 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_5_ZScore_W89` |  | 0.0212408 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Max_W34` |  | 0.626252 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MACDFIX-Signal_8_Range_W3` |  | 0.270186 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_MOM_21_Slope_W21` |  | 0.46503 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_PPO_34-144-0_Min_W144` |  | 0.971458 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_PPO_5-21-0_Skew_W21` |  | 0.00170524 | 0.42631 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_PPO_55-233-0_Rank_W8` |  | 0.108555 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_PPO_8-34-0_Min_W89` |  | 0.786399 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCP_144_Lag_34` |  | 0.0337346 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCP_89_Min_W13` |  | 1 | 1 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCR100_55_Range_W13` |  | 0.00950233 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCR100_9_Momentum_L34` |  | 0.804381 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCR_13_ZScore_W13` |  | 0.0848894 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCR_21_Range_W3` |  | 0.407167 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCR_55_Kurt_W5` |  | 0.750248 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROCR_8_Min_W55` |  | 0.171182 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROC_21_ZScore_W8` |  | 0.912387 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROC_5_Slope_W55` |  | 0.393822 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROC_8_TsArgmin_W21` |  | 0.438934 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_ROC_9_Momentum_L21` |  | 0.408963 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_RSI_13_Kurt_W21` |  | 0.789766 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_RSI_55_Max_W13` |  | 0.729385 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_RSI_6_Min_W13` |  | 0.531506 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastd_21-8-5-0_TsArgmax_W5` |  | 0.951635 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_14-3-3-0_Min_W8` |  | 0.545089 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_34-8-5-0_ZScore_W5` |  | 0.941947 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_Rank_W13` |  | 0.840161 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_STOCHRSI-fastk_9-5-3-0_ZScore_W8` |  | 0.367069 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_TRIX_55_TsRank_W13` |  | 0.0251237 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W233` |  | 0.872976 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_TRIX_5_Max_W89` |  | 0.320258 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_momentum_TRIX_89_Min_W5` |  | 0.378589 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_144_Kurt_W21` |  | 0.883674 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-ANGLE_233_Lag_2` |  | 0.201128 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_Mean_W89` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-INTERCEPT_144_ZScore_W34` |  | 0.824885 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_13_ZScore_W233` |  | 0.465789 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_233_ZScore_W34` |  | 0.0888802 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W233` |  | 0.536478 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_34_Skew_W8` |  | 0.552319 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG-SLOPE_5_Rank_W5` |  | 0.50607 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG_233_Skew_W233` |  | 0.613875 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG_34_Min_W144` |  | 0.489921 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_LINEARREG_55_Min_W89` |  | 1 | 1 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_STDDEV_144_Std_W34` |  | 0.059057 | 0.922765 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_STDDEV_14_ZScore_W5` |  | 0.0247234 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_STDDEV_55_Mean_W5` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_TSF_13_Range_W89` |  | 0.483077 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_TSF_144_Kurt_W89` |  | 0.176322 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_TSF_34_Kurt_W5` |  | 0.786442 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_TSF_34_Lag_5` |  | 0.285781 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_13_Kurt_W8` |  | 0.647284 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_20_Mean_W21` |  | 0.698117 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_21_Kurt_W144` |  | 0.693428 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_34_Kurt_W8` |  | 0.77058 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_55_Min_W144` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_55_Slope_W3` |  | 0.167861 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_statistics_VAR_89_Mean_W34` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_20_Lag_2` |  | 0.031653 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_BBANDS-Lower_55_Range_W21` |  | 0.469815 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_34_Std_W34` |  | 0.924634 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_BBANDS-Middle_89_Momentum_L233` |  | 0.231057 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_DEMA_21_Skew_W89` |  | 0.122399 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_DEMA_233_Lag_2` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_DEMA_233_Min_W144` |  | 0.581195 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_DEMA_34_Range_W144` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_DEMA_89_Std_W233` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_DEMA_8_Mean_W34` |  | 0.501215 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_13_Momentum_L144` |  | 0.276175 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_13_Rank_W144` |  | 0.173052 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_13_ZScore_W3` |  | 0.762137 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_144_Max_W55` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_200_Slope_W144` |  | 0.102701 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_21_Range_W13` |  | 0.92319 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_5_Lag_34` |  | 0.71646 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_EMA_5_Min_W233` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_KAMA_89_Kurt_W13` |  | 0.22634 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_KAMA_8_Lag_21` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MAMA_0.5-0.05_Kurt_W233` |  | 0.358057 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MAVP_55_Range_W5` |  | 0.453034 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MAVP_89_Range_W8` |  | 0.543759 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MAVP_8_Kurt_W34` |  | 0.531688 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MA_21_233_Ratio` |  | 0.970932 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MA_233_Mean_W89` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MA_5_Rank_W34` |  | 0.0871184 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_Mean_W13` |  | 0.580693 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MIDPOINT_34_ZScore_W34` |  | 0.289901 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_MIDPOINT_8_Abs` |  | 0.966086 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_SMA_10_TsArgmax_W5` |  | 0.905128 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_SMA_50_ZScore_W233` |  | 0.441989 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_SMA_55_Min_W13` |  | 0.548786 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_SMA_89_Rank_W89` |  | 0.231681 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_T3_13_Range_W21` |  | 0.440431 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_T3_21_Min_W55` |  | 0.926445 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_T3_8_Std_W5` |  | 0.669024 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_TEMA_5_Momentum_L8` |  | 0.189695 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_TRIMA_55_Skew_W34` |  | 0.0278018 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_WMA_144_Momentum_L3` |  | 0.0213083 | 0.766695 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_WMA_21_Skew_W89` |  | 0.109892 | 0.988534 | True | True | passed |
| `xsec_3sym_12h_e53e2290` | `volume_12h_trend_WMA_89_Max_W233` |  | 0.580693 | 0.988534 | True | True | passed |

## 機讀附件

- `handoffs/ic1eb_newpath_freeze/baseline_manifest.json`
- 每 run 的 `*.report.json` + `feature_sig` 已寫入 freeze 目錄

