# IC Phase 1 — 1a cut1 SPEC Adversarial Review（Composer 2.5，獨立）

> 審查對象：`handoffs/20260626-ic-PHASE1-1a-cut1-SPEC-DRAFT.md` + MANIFEST/BRIEF + 契約層實作（實讀核對）
> 嚴格度：MAXIMUM | 焦點：完整審查 | 日期：2026-06-26

## Verdict：需修補後派工

SPEC 骨架（§RISK/§A/§C/§G/§P/§V/§R/§N 錨點齊、winsor/standardize 洩漏診斷正確、flag-off byte 守恆意圖清楚）可作為修補基礎，但存在 **pipeline 順序與 mask 語義矛盾**、**label-horizon purge 未規格化**、**OOS 範圍只覆蓋 stage4 點 IC 卻漏 stage5 衍生統計**、**Task 2.1 切分來源與參數未凍結** 等會讓實作者猜測或產出「看似綠燈仍洩漏」的 BLOCKING 缺口。修補後再派工；不建議整份重作。

---

## Findings（挑戰前提置頂）

### [BLOCKING | High] §A「主流程完全無 split」屬實，但 SPEC 未處理 split 與 event filter 的順序矛盾，B-3 mask 貫穿在現行 pipeline 下不可行

- **證據**：§A L20「主流程 IC 目前完全無 train/test split」— 實讀 `ic_filter_orchestrator.py:94-166` 確認無 split 呼叫。Task 2.1 L66「ingestion 後、preprocessing 前」產生 split；Task 2.3 L81-84 mask 貫穿各 stage。但 `analyze()` 實際順序為 stage0→**stage1 preprocessing**→stage2 label→**stage3 event_filter**（`:122-125`）→feature_filter→stage4；stage3 以 `features_df.loc[idx]` 子集化（`:1096-1097`），列數與 positional index 重映射。
- **會怎麼失敗**：split 在 ingestion 後以 positional `row_index` 建立；event filter 刪列後 mask 指向錯誤列或靜默錯位；`test_split_mask_consistent_across_stages` 可能在未開 event filter 時假綠，真實路徑（event_filter enabled）OOS IC 算在錯誤列上。
- **修法**：在 SPEC 寫死 canonical 順序（建議：ingestion → event filter / row subset → **再** split → preprocessing train-fit → IC/OOS），或改 `SplitPlan.index_kind="timestamp"` + 每個會改列集合的 stage 後重算/校驗 mask；Task 2.1/2.3/B-3 與 §V 邊界測試同步改。

### [BLOCKING | High] §A 確認 winsor/standardize 全段 fit 屬實，但 SPEC 漏列同 stage 其他全段 fit 路徑（handle_missing / remove_constant），train-only 宣稱不成立

- **證據**：§A L19 引用 `data_preprocessor.py:154-155`、`:136-137` — 實讀確認 `series.quantile` / `df.mean/std` 對全段。同檔 `handle_missing` L114-117 `coverage = filled.notna().mean()` 全段決定刪欄；`remove_constant_features` L121-122 `nunique` 全段。Phase 3 僅覆蓋 C-1/C-2 winsor/standardize（§P Task 3.1-3.2），未列 Task。
- **會怎麼失敗**：test 段 NaN 模式改變 coverage → 訓練段本可保留的特徵被刪（或反之）→ 等於用 test 資訊做特徵選擇；F-1 只測 winsor/standardize 仍會 PASS。
- **修法**：新增 Task（或擴 C-3）：`handle_missing`/`remove_constant_features` 的統計量僅用 train mask；補可證偽測試（test 段注入全 NaN 列不改刪欄集合）。

### [BLOCKING | High] 單幣縱向切分未規格化 `purge_gap` ↔ `default_horizon`，違反契約 pair-level purge 紅線且引入 label look-ahead

- **證據**：`validate_split_pair_integrity` 依 `purge_gap`/`embargo` 禁 train 踩 test 禁區（`contracts.py:584-595`）。`ICGlobalConfig.default_horizon=5`（`ic_config_schema.py:19`）。Task 2.1 只要求產出 `SplitPlan` 含 `expected_freq`，**未指定 purge_gap/embargo 來源與數值**；全文無 `purge_gap`/`horizon` 交叉引用。
- **會怎麼失敗**：實作者設 `purge_gap=0` 或猜常數 → train 末段標籤使用 test 段價格（forward return horizon=5）→ OOS IC 仍含前瞻偏誤；`validate_split_pair_integrity` 不擋此類洩漏。
- **修法**：Task 2.1 寫死 `purge_gap >= config.global_settings.default_horizon`（及實際選用 horizon），embargo 來源寫死；驗證用已知切點 + 人工構造邊界列 assert train 末 purge 區不含可計算 label 的列。

### [BLOCKING | High] Task 2.1「holdout vs CPCV/WF adapter」未決 + 切分比例/參數未凍結，Agent 必須自行判斷

- **證據**：§A L27「待雙家族 adversarial 收斂」；Task 2.1 L67-68「待決點…TODO 凍結前二選一寫死」；IC config 無 `train_size`/`test_size`/`n_groups`（`grep` `ic_config_schema.py` 僅 `min_splits`）。CPCV/WF adapter 產出**多 fold**（`ic_split_adapter.py:65-100`, `:135-161`），SPEC 未規定 IC 報告用哪一 fold。
- **會怎麼失敗**：實作者隨機選 WF fold 或硬編 70/30 → 與 golden/三方簽核基準不一致；選 CPCV 需額外 config 且多 fold 語義與 cut1「單次 OOS 報告」不符。
- **修法**：見下方「holdout vs adapter 獨立裁決」；在 Task 2.1 寫死 holdout 比例來源、單切點算法、purge/embargo、樣本不足時 `SkippedResult` 條件。

### [BLOCKING | High] Task 4.1 宣稱 OOS IC/統計，但 stage5 仍依賴全段 `rolling_ic` 算 icir/p-value，與 D-1/D-2 矛盾

- **證據**：Task 4.1 L111-112「stage4 IC、stage5 統計在 test 計算」。實讀 `_stage4_ic_calculation` L1216-1220 對全 `features_df` 算 `rolling_ic`/`icir`；`_stage5_statistical_validation` L1276 `compute_ic_statistics(rolling_ic)`、L1284-1296 monotonicity/coverage/turnover 用全段 `features_df`。
- **會怎麼失敗**：點 IC 在 test、但 p-value/icir/monotonicity 仍含 train 資訊 → passed_features 混用 scope（違反 D-2 意圖）→ 假 OOS。
- **修法**：Task 4.1/4.2 明列 stage5 每個指標的 scope（ic_stats/icir/p/monotonicity/coverage/turnover）；或 stage4 僅在 test mask 上算 rolling_ic；補 `test_summary_and_threshold_same_scope` 斷言 p-value 變動可證偽（改 train 不動 test → p 不變）。

### [MAJOR | High] §G G-OLD baseline 的 `config_hash` 與凍結命令未寫死，G-OLD 不可執行

- **證據**：§G L35「config_hash=取 feature_library 最新 BTC/1h run hash，TODO 凍結前寫死」；路徑 `tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h.json` 尚不存在（repo 僅 `docs/IC_PHASE1_CONTRACT_*`）。HANDOFF L13 記 G1 baseline 52MB 不進 git、clean checkout 缺檔。
- **會怎麼失敗**：實作者自選 run → G-OLD 不可重現；CI 缺檔 skip 或假綠。
- **修法**：動工前跑 `freeze_baseline.py`（或等價）寫死 hash + 生成命令 + skip-if-absent 策略；§G 填入實測 hash。

### [MAJOR | High] BRIEF 與使用者 2026-06-26 決策矛盾（預設策略）

- **證據**：BRIEF L40「新算法一律藏在預設關閉的開關後」；BRIEF L24 / MANIFEST L5 / Task 5.1 L127「簽核 PASS 後預設 ON」。
- **會怎麼失敗**：執行端依 BRIEF 實作永久 default OFF → 違反使用者決策與 Task 5.1「不可做」。
- **修法**：統一以 2026-06-26 決策為準，修 BRIEF L40；SPEC §C L32「新行為一律藏 flag 後」加註「簽核後 default ON，flag=逃生口」。

### [MAJOR | Medium] Task 4.1 未涵蓋 ic_decay / grouped_ic / stage6 redundancy，下游仍全段計算

- **證據**：`_stage4_ic_calculation` L1233-1251 decay/grouped 用全段 `features_df`；`_stage6_redundancy` L1335-1340 對 `passed_features` 全段相關矩陣。
- **會怎麼失敗**：報告/decay 圖仍洩漏 train；cut1 若宣稱「OOS 報告」語義不完整。
- **修法**：§N 明確登記 decay/grouped/redundancy 為 cut1 外或 flag-on 時僅 test；或加 Task 限制 scope。

### [MAJOR | Medium] §P 多數驗證為尚未存在的 pytest 路徑，部分為「確認正確」式描述，TODO 前需具體化

- **證據**：Task 1.1-6.2 均引用 `pytest tests/momentum/...::test_*` 檔案尚未存在；Task 6.3 L163-164 驗證=「三方齊簽 PASS」非 pytest。
- **會怎麼失敗**：gate 過後實作者自行發明測試或略過 Task 6.3。
- **修法**：TODO 生成時每 Task 對應真實檔名；Task 6.3 改為 handoff 簽核 checklist + 禁止放寬既有 pytest 斷言的 grep 命令。

### [MINOR | High] §A 稱 `pd.Timedelta("1h")` 可解析「待 TODO 實跑」— 實測已可解析，但 SPEC 仍標未驗證

- **證據**：§A L21「待 TODO 凍結前實跑確認」；本審查實跑：`pd.Timedelta('1h'/'4h'/'12h')` 皆成功。
- **會怎麼失敗**：無（事實已成立）；但違反驗證保真度鐵律「§A 結構型別須附實跑輸出」。
- **修法**：§A 改為已驗證並貼實跑輸出；Task 1.2 補非法 timeframe（如 `"1H"`/`"60m"`）fail-closed 表。

### [MINOR | Medium] Task 5.1 flag 落點模糊（`ic_config.py` 可能不存在）

- **證據**：Task 5.1 L126「`momentum/Analysis/ic_config.py`（或對應 config）」；實際 schema 在 `ic_config_schema.py`，API 在 `api/core/config.py`。
- **會怎麼失敗**：實作者新建重複 config 或只改一端導致 API/引擎 flag 不同步。
- **修法**：寫死單一 SSOT（建議 `ICConfig` + `config_override` 路徑）及 API 是否需鏡像。

### [MINOR | Low] stage6 / deep analysis cache 未要求 split-aware key

- **證據**：`_ic_cache` 快取全段結果（`ic_filter_orchestrator.py:1414+`），SPEC 未提 resume 語義。
- **會怎麼失敗**：cut1 單幣風險低；未來 partial rerun 可能混用 pre/post split 快取。
- **修法**：§N 登記 cut1 N/A 或註明 flag 變更須清 cache。

---

## §1 必查 10 類

| # | 類別 | 結果 |
|---|------|------|
| 1 | 矛盾/互斥 | **有** — split 時點 vs event filter（見上 BLOCKING）；D-1 vs stage5 rolling_ic；BRIEF default OFF vs 使用者 ON |
| 2 | 漏項/端到端 | **有** — mask 與列子集；handle_missing/constant；purge_gap；decay/grouped/redundancy scope |
| 3 | 不可測驗收 | **有** — config_hash 未凍；Task 6.3 非機械可證偽 |
| 4 | 可疑 quant 假設 | **有** — label horizon purge 缺失；OOS 範圍不完整；train-only 僅 winsor/std |
| 5 | 過度工程 | **有（若選 adapter）** — cut1 用 CPCV/WF 多 fold 過重；holdout 足夠（見裁決） |
| 6 | OOM/並行 | **無** — 單幣 cut1，無新巢狀並行 |
| 7 | Cache 正確性 | **有（輕）** — golden key 待寫死 config_hash；_ic_cache 未 split-aware |
| 8 | API/型別/相容 | **有（輕）** — flag SSOT 模糊；flag-off byte 守恆有規格但 baseline 未備 |
| 9 | 測試品質 | **部分** — F-1/F-2 要求真實 kline 佳，但未覆蓋 missing/constant/rolling 洩漏 |
| 10 | Agent 可執行性 | **有** — Task 2.1 未決 + 切分參數缺失；多 pytest 路徑為占位 |

---

## §2 範本錨點 + 獵空殼

- **錨點**：§RISK/§A/§C/§G/§P/§V/§R/§N 均存在，非空殼。
- **§G 可證偽性**：G-NEW 容差（abs≤1e-9 / rel≤1e-7）+ NaN mask hash **具體**；G-OLD 要求 deep equality **具體**，但 reference run/hash **未凍** → 半空殼。
- **G-NEW「簽核後才凍 / flag 預設 OFF→簽核後 ON」**：Task 5.1/5.3/§R L173 **自洽**。
- **空殼 Task**：Task 2.1（待決點）、Task 6.3（簽核非 pytest）為 BLOCKING 级空殼；其餘 Task 有檔名+函式但測試檔尚不存在（預期草稿階段）。

---

## holdout vs adapter 獨立裁決

**選擇：(ii) 單純時間順序 train/test holdout（單切點 + 契約 purge/embargo）**

**理由（獨立於作者框架）：**

1. **cut1 產品語義**是「單次 OOS IC 報告 + train-only 清洗」，不是 walk-forward 多期評估；holdout 直接對應 D-1/D-2。
2. **CPCV/WF adapter 產出多 fold**（`ic_split_adapter.split_cpcv/split_wf`），SPEC 未規定選哪一 fold 作為 canonical OOS → 實作者必猜。
3. **IC 配置無 CPCV/WF 參數**（無 `train_size`/`n_groups`/`embargo_pct` 於 `ICConfig`），接 adapter 需額外引入 ML 孤島 config 或硬編碼，違反「最小改動、可驗收」。
4. **purge_gap 必須綁 label horizon**；holdout 單切點 + `validate_split_pair_integrity` 最易寫死可證偽測試。
5. **adapter 保留給 1e/rolling OOS 或多 fold 場景**，不應阻塞 cut1；可在 cut2/1e 再接入，不與「複用切分數學、不重寫」衝突（holdout 仍可用既有 `PurgedTimeSeriesSplit` 或等價最後一段 holdout 邏輯，不必發明新數學）。

**建議凍結參數（供 SPEC 寫死）**：test 比例或 `test_size` 來源（如 IC config 新欄位，預設 0.2）、`purge_gap = default_horizon`、`embargo` 明確公式、樣本不足門檻 → `SkippedResult`。

---

## 被當成事實的未驗證假設

| §A / 文件聲稱 | 核對結果 | 分級 |
|---------------|----------|------|
| winsor/standardize 對全段 fit | **屬實** — `data_preprocessor.py:154-155`, `:136-137` | fact ✓ |
| 主流程無 split | **屬實** — `analyze():94-166` 無 split | fact ✓ |
| `metadata symbol/timeframe` 可取 | **屬實** — `:1039-1040`, service L74-75 | fact ✓ |
| `create_ic_split_adapter` 未轉 `allowed_symbols` | **屬實** — `factories.py:574-581` | fact ✓ |
| `pd.Timedelta("1h"/"4h"/"12h")` 可解析 | **屬實**（SPEC 標待確認）— 本審查實跑 PASS | 應升格為已驗證 |
| gap 檢測接線後即生效 | **部分假設** — 需 `expected_freq` 非 None 且 split 在正確 pipeline 點；event filter 後未重算 mask 則不生效 | MAJOR |
| train-only fit 可防洩漏（整體） | **未證** — 僅 winsor/std；missing/constant/rolling/stage5 仍全段 | MAJOR |
| Task 2.1「複用 ML 孤島切分」已足 | **未決** — 無比例/purge/fold 選擇 | BLOCKING |
| G-OLD 可逐位元組守恆 | **未備** — baseline 路徑/config_hash 未凍 | MAJOR |

---

```
ASSUMPTIONS_VERIFIED: analyze()無split; data_preprocessor winsor/std全段fit; factories未轉allowed_symbols; pd.Timedelta(1h/4h/12h)可解析; event_filter在preprocessing之後子集化列
TESTS_RUN: python -c "pd.Timedelta('1h'/'4h'/'12h')" PASS; 源碼實讀 ic_filter_orchestrator/data_preprocessor/contracts/factories
FAILURES_SEEN: none
SCOPE_CHANGES: none（審查-only）
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
