# 事件模式 rolling warmup／holdout consult R1 — COMPOSER

task-id: 20260908-EVTWARMUP-X-CONSULT-R1  
family: composer  
findings-round: R1  
brief-kind: consult  
標的 commit: `8f10d2e1`（HEAD）

---

## 被當成事實的未驗證假設（§0）

| 前提 | 標記 | 本輪覆核 |
|---|---|---|
| 門檻＝max(adjusted rolling windows)+effective_horizon，以列數計 | fact-verified | **成立** — `_rolling_warmup_min_rows` `:3184-3187`；UAT log `min_test_rows=131`＝126+5 |
| stage3 後 stage4 只剩事件列；測試段事件＝34 | fact-verified | **成立** — `_stage3_event_filter` 以 timestamp 交集 `.loc` 稀疏化 `:3327-3331`；`_stage4_ic_calculation` `len(features_for_ic)` `:3502-3513` |
| `ICEngine(config.ic_calculation.model_dump())` 無 `timeframe` ⇒ 視窗從不換算 | fact-verified | **成立** — 建構 `:988`；`_adjust_rolling_windows` `if not self._timeframe: return windows` `ic_engine.py:1333-1335` |
| 使用者實機 log 逐字 | fact-verified | **成立** — brief 引用 `train_rows=15149 test_rows=34 min_test_rows=131` |
| 事件模式 rolling ICIR 是主要篩選依據 | unverified | **未查** — brief「我沒查的」第一列；讀碼見 `_apply_thresholds` 仍消費 `icir_min` `:4248-4249`，但 fallback 後 `icir` 常 None（G3-R12） |
| 歷史裁決已把 rolling 視窗定義為「列數」 | fact-verified | **部分** — `test_ic_1a_cut1_oos.py:test_oos_ic_rolling_warmup` 以 K 線 test 列數斷言 rolling 長度 `:144-146`；**無**事件稀疏列專用裁決 |

---

## COMPOSER-R1-P3-00

**斷言**: 本輪為 consult（非 adversarial review），逐項核對 brief 必答 1–6 與四條碼證後**無獨立實質 finding**；規則錯置與 `_timeframe` 未注入已由讀碼確認，裁定收斂於「事件模式 bypass K 線 rolling warmup 門檻 + timeframe 修正另票」。

**碼證**: ① `sed -n '3184-3221p;3496-3515p' momentum/Analysis/ic_filter_orchestrator.py` — warmup 與 stage4 skip 同一規則、事件預檢以 test 段事件列計數；② `sed -n '988p;3327-3350p' momentum/Analysis/ic_filter_orchestrator.py` — engine 無 timeframe、stage3 稀疏化；③ `sed -n '1333-1345p' momentum/Analysis/ic_engine.py` — `_timeframe` None 時 early return；④ `grep -n "icir_min" momentum/Analysis/ic_filter_orchestrator.py` → `:4248` stage5 門檻仍讀 rolling 衍生 summary。

**來源摘要**: handoffs/20260908-EVTWARMUP-X-CONSULT-R1-BRIEF.md#consult-r1; momentum/Analysis/ic_filter_orchestrator.py#644bd066457d; momentum/Analysis/ic_engine.py#da4521cf2b82; config/ic_config.yaml#b2c5917df9ee

---

## 必答（逐條）

### 1. 規則錯置是否成立

**1a — 成立（量化上無意義且有害）。**

- Warmup 規則為 K 線連續列設計：`rolling_windows: [21,63,126]`（`config/ic_config.yaml:44-45`）在 global 模式每列＝相鄰 bar（`test_oos_ic_rolling_warmup` 以 test K 線列數斷言 rolling 序列長 `:144-146`）。
- 事件模式 stage3 後 `features_df` 僅剩事件決策列（`:3327-3331`）；holdout 仍切最後 20% **K 線**（metadata `test_rows`≈4070），但 stage4 安全網量的是 `len(features_for_ic)`＝測試段內**事件列**（34）對 `min_test_rows=131`（`:3502-3514`）。使用者「3000 根 vs 131 根」混淆即此：看的是 K 線 test 列數，門檻看的是稀疏事件列數。
- 若硬算 rolling IC，126 視窗＝「最近 126 個**事件**」，時間跨度隨事件密度漂移，與 12h 設計語意脫鉤。
- **有害**：34＜131 ⇒ `_precheck_rolling_warmup` `:1147-1161` 或 stage4 `:3504-3515` 觸發 `_run_full_sample_fallback` ⇒ `fit_mode=full_sample`、`oos_guarantees=False`（`:1367-1371`），條件 IC 失去 OOS，非資料不足。

**1b — 反面情境（少數成立）。**

- 測試段事件數 ≥131（高頻批、長窗 holdout、或事件密度接近每 bar 一事件）時，以事件數計 rolling **可以**解讀為「最近 N 次決策的 IC 軌跡」——與條件 IC 的 estimand 一致。
- 170 筆／20k bar 之 ETH 1h 批**不在**此類；brief 實機 34 test 事件屬典型稀疏批，1b 不救本 case。

### 2. 事件模式 OOS 與 rolling 視窗

**2a — 可行；洩漏風險可管。**

- Holdout 繼續在 **K 線時間軸**切 train/test（現行 `:951-958`），purge/embargo 仍依 `effective_horizon`；stage3 稀疏化後，**點估 IC ＋ HAC 顯著性**已在 test 段事件上算：`compute_hac_ic_statistics(features_for_stats, label_for_stats, …)` `:3676-3681`，`_slice_by_mask` 用 `test_mask` `:3664-3668`。
- 條件 IC 的 OOS 保證應定義為：**預處理 fit 僅 train**（現行 `_resolve_stage1_fit` + split）、**label/特徵在決策點 PIT**（EVTALIGN B+D 路線）、**Spearman/t_stat 只在 test 段事件列**——**不要求** rolling warmup 才能算 pooled IC。
- 洩漏：若 bypass warmup 但仍用 train∪test 做 rolling IC（`:3528-3533` `allowed_mask = train_mask | test_mask`），rolling 序列本身可能含 train 事件——這是 rolling **診斷**問題，不是點 IC OOS 問題；stage5 註解已寫 rolling 不餵 p-value 鏈 `:3659-3660`。OOS 點 IC 與 FDR 不受 rolling warmup 門檻阻擋即可。

**2b — 若保留 rolling（次要／診斷）。**

- 視窗應**顯式分轨**：global 模式＝K 線 bar 數（並修 timeframe 換算）；事件模式＝**事件序號**或**日曆時間**（例如 reference 63×12h 映射成 ms window），契約欄 `ic_source=event_rolling|bar_rolling`。
- 最小事件數：pooled 條件 IC 已有 `event_filter.min_events=30`（`ic_config_schema.py:68`，`event_filter.py:183-189`）；統計上 Spearman 穩定估計常用 n≥30。Rolling ICIR 另需 `window_events + buffer`（例如 max(30, window)+1）；不足則 NaN＋揭露（G3-R12 已描述），**不得**因此降級整條 holdout。

### 3. `_adjust_rolling_windows` 從未生效

**3a — 須修，但為獨立票；修後 global 1h 影響大、需另裁定。**

- 現況：`ICEngine` 只收 `ic_calculation.model_dump()`（`:988`），無 `timeframe` ⇒ 1h run 直接用 [21,63,126] bar（≈0.9–5.25 天），非 config 宣稱的 12h reference（63 bar ≈ 2.6 天而非 31.5 天）。
- 修正：建 engine 時注入 `metadata["timeframe"]` 或 config 欄 ⇒ 1h 因子 12 ⇒ 視窗 [252,756,1512]、warmup 1512+horizon（例 1517）。**全域連續 IC 語意變更**，影響 golden／survivor 門檻／歷史報告對比 ⇒ **不可與事件 warmup bypass 混在同一批**，需獨立 consult＋§G golden。

**3b — 不修而只揭露：構成語意假 ICIR（非捏造數字）。**

- `ic_mean`/`icir` 來自 rolling 序列（`_build_summary_table` `:4192-4194`），數值真實但**標籤假**：宣稱 12h 參考卻跑 1h 列數。`_apply_thresholds` 的 `icir_min` 門檻（`:4248`）在錯尺度上篩選 ⇒ 比「不算」更糟。須麵包屑或 `ic_window_scale=unadjusted` 直至 3a 修完。

### 4. 最小修法

**4a — 本票首選（不動 IC 數值語意、只動 holdout 閘）：事件模式 bypass K 線 rolling warmup。**

| 項目 | 內容 |
|---|---|
| 觸發 | `config.event_filter.enabled` 且 holdout 已套用（`split_context is not None`） |
| 改動 | `_precheck_rolling_warmup` / `_stage4_ic_calculation` skip 區塊：改為 `min_required = max(effective_horizon+1, event_filter.min_events)` **或** 事件模式下直接跳過 warmup skip（仍保留 `min_events` / `conditional_ic_abandoned`） |
| 檔案 | `momentum/Analysis/ic_filter_orchestrator.py`（`_precheck_rolling_warmup`、`_stage4_ic_calculation`、可選 `_rolling_warmup_min_rows` 加 `mode` 參數） |
| 測試 | 擴 `tests/api/test_stage_progress.py:test_precheck_rolling_warmup_*`（34 test 事件 + timestamps ⇒ precheck None）；`tests/api/test_gap3_oos_downgrade.py` 增「事件批 holdout 不 fallback」；`tests/momentum/Analysis/test_ic_1a_cut1_oos.py` 保留 global warmup 回歸 |
| golden | metadata `ic_train_test_split.applied=True`、`oos_guarantees=True` 對 170 事件批；`oos_downgrade` 不出現 `rolling_warmup_insufficient` |

**4b — 新誤擋／新漏。**

| 風險 | 評估 |
|---|---|
| 測試段 <30 事件 | 仍由 `min_events` / `conditional_ic_abandoned` 擋或標 unavailable（`:1199-1208`），非新洞 |
| rolling ICIR 全 NaN | 34 事件仍 <126 window ⇒ summary `icir` NaN（G3-R12）；`icir_min` 可能全剔——屬**既有**小樣本問題，應另走 pooled `ic_mean` 或門檻豁免事件模式，**不可**再 fallback 全樣本 |
| scan cube 110 格 | 註 `:1240-1246` 曾把 `_suppress_persist` 誤當 fallback guard 打穿掃描；修法須沿用 `_in_fallback_rerun` 判別，**不**改 suppress 語意 |
| fallback 路徑 | one-shot guard 保留（`:1248-1252`）；bypass 後正常 holdout 不應再進 fallback |

### 5. ≥10× 不必要複雑？

**無。** 首選方案＝兩處條件分支 + 3–5 條測試，不新增 framework／queue／110 格特判。把 timeframe 換算 + 事件 rolling 雙轨 + summary 契約重寫捆在一起才會 ≥10×——應拒。

### 6. Verdict

**Verdict: 採「事件模式 bypass K 線 rolling warmup 門檻（4a）」，因為碼證顯示 131 門檻量的是稀疏事件列而非 K 線 test 段，導致幾乎必然 full-sample fallback 剝奪 OOS；`_adjust_rolling_windows` 未生效（3a）須另開票修 timeframe 注入，不可與本票混批。**

---

ASSUMPTIONS_VERIFIED: `sed -n '3184-3221p;3496-3515p;988p;3327-3331p' momentum/Analysis/ic_filter_orchestrator.py`；`sed -n '1333-1345p' momentum/Analysis/ic_engine.py`；`sed -n '44-49p' config/ic_config.yaml`；brief UAT log 逐字。

TESTS_RUN: 讀碼驗收；**未跑** `pytest tests/governance`（brief 禁）。

FAILURES_SEEN: none

SCOPE_CHANGES: none（consult 唯讀）

NUMERIC_OR_SCHEMA_IMPACT: none（路線裁決；4a 實作將恢復事件 holdout OOS，不改 pooled IC 公式）

HANDOFF_OUTPUT: `handoffs/20260908-evtwarmup-x-consult-r1-composer.md`

STATUS: DONE
