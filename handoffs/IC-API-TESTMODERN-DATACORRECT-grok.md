# IC-API-TEST-MODERNIZATION Phase1 資料正確性簽核 — Grok 獨立版
Task-id: icatm-dc-grok | Reviewer: Grok | Date: 2026-07-12 | 禁改碼

## 標的
`tests/fixtures/ic_api_real_kline.py` → IC 輸入 features/labels 是否 PIT 無洩漏、真 kline 衍生、可證偽。

## (1) Label — 自跑數值
- 公式：`close.shift(-5)/close - 1.0`（simple 前瞻），`RETURN_TYPE="simple"` 與 `config_override.labels.return_type` 同源。
- 尾 5：`labels.iloc[-5:]=NaN`；`notna` 前 507 列全有限。
- 抽樣 t∈{0,50,100,250,400,506}：`got == close[t+5]/close[t]-1`（atol=0）。
- 與 backward `close/close.shift(5)-1` 最大差 ≫1e-6；與 log 前瞻差 ≫1e-8。
- **LABEL: PASS**（真前瞻 simple，非 backward/log，尾5 NaN）。

## (2) Features 逐欄 ≤t
| 欄 | 公式 | 時序 |
|----|------|------|
| log_return_1 | logc[t]-logc[t-1] | ≤t |
| log_return_3 | logc[t]-logc[t-3] | ≤t |
| rvol_20 | std(lr1 rolling20, 右端 t) | ≤t |
| zscore_20 | (c-mean)/std rolling20 | ≤t |
| hl_range | (h-l)/c 同 bar | ≤t |
| oc_return | c/o-1 同 bar | ≤t |
| close_sma_ratio_20 | c/sma20-1 rolling | ≤t |

- 無 `shift(-*)`；manual 重算 7 欄 allclose；全 finite；vs `shift(-1)` 各欄 maxdiff>0。
- warmup：`MAX_FEATURE_LOOKBACK=21`，mid[200:712] 512 列有限。
- **FEATURE: PASS**。

## (3) Mutation 可證偽（自跑）
```
venv/bin/pytest tests/momentum/Analysis/test_ic_api_real_kline_pit.py -v --tb=short
→ 2 passed in 0.06s
```
- feature_shift=-1 → `AssertionError: feature PIT oracle mismatch`
- backward_label=True → `AlignmentViolationError: label mismatch at ...`（validate_alignment + close + return_kind=simple, sample_size=16）
- 獨立 script 再證兩 mutation 真 raise（非空轉）。

## (4) 合成殘留 / R2-7 / 生產 / 去重 / API
- IC 輸入面 5 檔 `rg rng.normal|np.arange|np.random` → 0 hits；真 ETHUSDT/12h 1696 根衍生。
- R2-7 stub：**僅** API 輸出面（deep_analysis_result 序列化邊界 / export seam）；`copy.deepcopy` + finally/teardown restore；filtered HDF5 取真 feature 值。
- `git diff -- momentum/ api/` → empty（生產零 diff）。
- 去重 3：`test_feature_list` / `test_full_analysis` / `test_deep_analysis_result` 已不存在；由 list_success / full_analysis_endpoint / start_and_get_result 覆蓋。
- API：`pytest tests/api/test_ic_{analysis_api,deep_analysis}.py tests/api/test_export_api.py` → **29 passed** in 8.03s。

## 實作 review（附）
- Builder oracle 雙層：特徵 recompute 對照 + Tier-2 `validate_alignment(close=..., return_kind=simple)`。
- mutation 參數僅 PIT self-test；session fixture 走 clean path。
- 無越界改 production。

## 簽核
DATA-CORRECT: PASS

無疑點；三方鐵律本席獨立 PASS。
