# ROADMAP — 量化交易系統戰術路線圖

> **這份只回答一個問題：現在在哪、接下來做什麼。** 敘事與歷史在 `docs/ROADMAP_DETAIL.md`。
> 即時任務狀態看 `HANDOFF.md`；決策理由看 memory。
> 維護：**每次 commit 一併更新本檔**（2026-06-26 使用者定）。日期看 git log，手寫日期欄已廢。

當前階段：**V1.0 工具階段** — crypto 單市場研究管線（探索 → 發現 Pattern → ML 優化 → 回測）。
願景 V1→V2→V3 見 `PRODUCT_VISION.md`。

---

## 🔥 現在在哪（狀態表）

> 🔴 **本表只放狀態與下一步。** 想寫背景、理由、歷史 ⇒ 寫進 `ROADMAP_DETAIL.md`，本表放 pointer。
> 病根（使用者 2026-08-14 第四次指出）：本檔曾 227 行、其中「進行中／下一步」一節佔 213 行
> ⇒ 要回答「我在哪」得讀 213 行敘事。**主委四次說要改、四次講完就放掉。**

| 工作線 | 狀態 | 下一步 | 細節 |
|---|---|---|---|
| **量化主線（IC 分析）** | 🏁 **GAP-1 四批全部 CLOSED（2026-08-18）**：B1–B4 各三家 code review＋三家戳記；280 測試／20 mutation／wiring 閘 rc=0；延伸檔 A1-1..A1-24；殘留 G1-R1..R7／R9／R10／R11 | GAP-2a 亦 CLOSED（2026-08-19）；**GAP-3 之 UAT 缺口修補：SPEC 與 TODO 皆已 FROZEN（2026-08-24）**；**B1 已收斂（2026-08-24，五輪 review 3→2→10→7→0）**，唯一入口 `docs/GAP3UX_IMPL_HANDOFF.md`（42 Task 中 3 個 ✅／1 個 🔧；看板 `白話說明/GAP-3施工看板.md`）。**B2 已落地（2026-08-25）：Task 1.2／1.3／1.4／1.8，mutation 9 條 `closure: CLOSED`，待三家 code review**。下一步＝B3（Task 1.11／1.12／1.9） | TODO `docs/GAP1_STRATEGY_OVERFIT_TODO.md`；延伸檔 `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`；收斂 `handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md` |
| **`/search` 修復（out-of-epic）** | 🏁 **CLOSED（2026-08-22）**：使用者 UAT 現場抓到三個既有 bug（毫秒游標→無窮迴圈＋資料重複、同步下載佔事件迴圈、worker 日誌不落檔）；7 輪三家對抗審＋2 輪蓋章，findings 8→7→2→2→3→3→0；`reconcile_stamps_check.sh` rc=0 三家 APPROVED | —（九項具名殘留各帶三值理由，觸發時再開） | 收斂＋戳記 `handoffs/reconcile/20260822-searchfix-x-review-r7/synth.md`；白話 `白話說明/search搜尋修復.md`；commit `bf0fd48a` |
| 治理 epic | **留現狀、不再擴建**（使用者 2026-08-14） | 無。已掛機制繼續運作。**唯一例外（使用者 2026-08-25 明示授權）**：mutation 併發隔離 `scripts/mutation_worktree.py`＋`verify_mutation.sh` 改薄殼委派 ⇒ 三家可平行跑 mutation，主 repo 零觸碰 | `ROADMAP_DETAIL.md` |
| P1-6 委員債狀態機 | B5 未完工（線 C 未做） | 不排程（治理不再擴建） | `ROADMAP_DETAIL.md` |
| GAP-1 DSR/PBO/MinBTL 策略層防偽 | 🏁 **全票 CLOSED（2026-08-18）**；殘留 registry G1-R1..R7＋R9＋R10 | —（殘留 registry 觸發時再開） | TODO＋延伸檔（見上行）；待補完：registry「GAP-1 待補完」節 |
| PA-CUMSUM 單利權益改正（小票；G1-R8 收回） | 🏁 **CLOSED（2026-08-18）**：`EquityCurveData` 改為單利（cumsum）／複利（cumprod−1）**兩條都算、都標清楚**（後端＋API model＋前端切換，預設複利）；三家 code review 7 條全修（多標的等權組合／proba 缺值 4xx／契約封閉）| — | 出處＝`CODEX-R8-P1-12`／`GROK-R8-P1-03`；使用者 2026-08-18 裁定「兩條都算＋前端切換一起做」；收斂＋三家戳記 `handoffs/reconcile/20260818-pacumsum-x-review-r23/synth.md` |
| **GAP-2a 邊際 IC／多因子組合（純 IC 層）** | 🏁 **CLOSED（2026-08-19）**：SPEC R7 FROZEN＋TODO FROZEN（五輪 20→15→7→1→0）；B1–B5 各三家 code review＋三家戳記；A1-1..A1-11；§V 24 條 mutation 全 RED；§G-1 golden 改前==改後 PASS；殘留 G2-R1／R2／R3／R5／R6／R7／R8 見 registry「GAP-2 待補完」 | — | SPEC `docs/GAP2_MARGINAL_IC_SPEC.md`；registry #2a |
| GAP-2b IC→ML 橋 | 契約 **已落地**（`ic_survivor_contract.json` v1＋`validate_survivor_output`／`build_survivor_output`；B1／B3／B4 三家戳記；倖存者檔 `ic_survivors_{case_id}.json` 每次 analyze 落檔）；橋本體＝殘留 G2-R1（user-ruling blocked-by ML 層） | 本體等 ML 層穩定 | registry #2b／「GAP-2 待補完」G2-R1 |
| GAP-3 事件型分析（使用者重定義：外部標好正反例匯入→PIT 對齊→條件 IC／ML；非 event study） | **SPEC＋TODO 皆 FROZEN（2026-08-20 白話閘核准）**：SPEC 六輪對抗審 15→0＋三家戳記；TODO 兩輪 14→0（R7 12 群集寫回、R8 原提出方全 CLOSED）＋三家 RECONCILE-STAMP 蓋 r8 synth rc=0；殘留 G3-R1..R8 入 registry | **B1–B4 CLOSED（2026-08-21）**：B1 七 Task（review 四輪 8→3→1→0）、B2 五 Task（三輪 11→4→0）、B3 三 Task（條件引擎／產生器 adapter／五個 state-counter 算子；兩輪 9→0）、B4 兩 Task（pattern 橋 train-only＋candidate ledger→GAP-1 DSR/PBO/MinBTL，N 只從 ledger、AUC 型別閘；四輪 8→2→1→0）皆三家 RECONCILE-STAMP rc=0；event_samples 全套 224＋state_counters 17 tests；GAP-1 strategy_validation 272 不退步；§G-1 golden sha 不變；B5 follow-up：`requests.py` allowed_filtering_params 改讀契約出口。**B5 審查完工蓋章（2026-08-22）**：B5.1 API 接線＋`create_event_sample_pipeline()` 唯一出口＋規模 receipt（direct 76.978s／API 路徑 0.382s）、B5.2 前端三頁（匯出契約 JSON＋companion 來源檔／新契約匯入／事件模式選批＋三表）、B5.3 UAT checklist；review 五輪 11→5→4→1→0＋三家 RECONCILE-STAMP rc=0；UAT A 段 9 項 rc=0（receipt `20260822T040000Z-gap3-b5-uat-sectionA.log`）。**UAT 缺口修補 SPEC 進行中（2026-08-22，未 FROZEN）**：使用者 UAT 提出之 10 條問題寫成 `docs/GAP3_EVENT_UX_SPEC.md`（1168 行／7 Phase／41 Task／§V 18 條）；對抗審 R1 24 → R2 7 → R3 18 → **R4 19（全數 ACCEPT、0 條降殘留，§C0 條文 2）**。R4 為**去錨定輪**（brief 零「請攻」＋fact 全改可重跑 receipt＋標的 sha256 鎖版），較前三輪多出 5 條無人觸及之 findings（最重＝D-7 L3 與 `event_forward_return_table` 必填 `event_split_plan` 之真矛盾）。R4 九群集全數修訂完成（新增 Task 7.0／7.6／7.7、§G S-1..S-8 canonical serialization、V-14／V-15；§N #8／#10 殘留撤回改為 Task 7.7）。🔴 **上列 R4 之後續已完成，敘述以此為準（2026-08-24 更新，取代原「下一步＝派 R5」）**：SPEC 續審至 **R34** 後由**使用者直接裁定 FROZEN**（3,547 行／**42 Task**／§V 20 條；P0=0、新缺口連二十輪 0；委員四條件之①未滿足由使用者覆蓋，四條具名殘留 F-1..F-4 皆非量化正確性）。**TODO 亦 FROZEN v1.0**（`docs/GAP3_EVENT_UX_TODO.md`，1,618 行／42 Task；三輪對抗審 12→19→3 ＋ 戳記輪，三份 reconcile 皆三家 APPROVED；延伸檔 `docs/GAP3_EVENT_UX_TODO.D-001.md` 更正 §B 之 B1 列，**已於 2026-08-24 三家 APPROVED**）。**B1 實作已落地（2026-08-24，待 code review）**：Task 1.1 契約先行（`event_import_contract.json` 之 typed namespace-aware `receipt_schema`＋`flatten_receipt_schema`／`receipt_type_ok`／`validate_receipt_namespace`；凍結 baseline fixture sha256 `7111b2d7…`）、Task 1.10 lookahead registry（`future_column_lookahead.json` 登記 `CaseData` 之 37 個 future 欄，分 bar／hour／unknown 三類；`lookahead_registry.py` 含 provenance 信任邊界）、Task 2.1b 唯一深度函式 `lookahead_depth.py::depth_by_timeframe()`＋前端下界鎖定、Task 4.2 之 §G S-9 參考實作 `canonical_serialize.py`＋重複 horizon 守衛。驗收：`gap3_contract_reason_registry` 16／`lookahead_registry_complete` 12／`lookahead_rename_attack` 4／`gap3_lookahead_depth` 9／`canonical_serialize` 9／vitest 7 皆綠；13 條 mutation 逐條轉紅並還原轉綠（receipt `handoffs/run_receipts/gap3ux-b1-task{11,110,21b,42-s9}-mutation.receipt.json`）；G-1 `gap3_freeze_golden.py --check` rc=0；`npm run build` rc=0。延伸檔 `docs/GAP3_EVENT_UX_TODO.D-002.md`（A-002 S-9 應為 7 條、A-003 小時換算取 ceil、A-004 前端下界值來源殘留），**尚未過戳記**。**四輪 code review 已跑完（2026-08-24，commit `fa172e44`）**：findings 3→2→10→7，P0 全程 0、P1 連兩輪 0；第一輪之後皆屬測試強度而非產品邏輯。R1 之 `CODEX-R1-P1-01` 為**資料正確性真缺口**（SPEC Task 1.10 對 `future{1,2,4,6}_close_return` 之單位敘述與 producer 不符——producer 用裸 `shift(-N)`＝根，SPEC 寫小時；12h 線上 purge 低估六倍）；R3 之三條合併導致**設計改變**（把匯出包進 `withHorizonLowerBoundGuard` 之 `proceed`，使「阻擋早於網路動作」由需檢查之性質變成結構保證）。驗收：`gap3_contract_reason_registry` 等 54／`event_samples` 270／vitest 23／build rc=0／G-1 rc=0；**mutation 32 條、receipt `closure: CLOSED`**。延伸檔 `docs/GAP3_EVENT_UX_TODO.D-002.md` 累計 14 條修訂（A-002..A-015），**尚未過戳記**。🔴 **上列三個待裁定已由使用者於 2026-08-24／25 全數裁定並執行完畢（本段取代原「現停在使用者裁定」）**：①**R5 已跑**（`dec88c10`）——三家零 finding，R4 七條由**原提出方**各自重跑自己的反例確認閉合（章程 §B8）；mutation 累計 **32 條 `closure: CLOSED`**。②**D-002 已補戳記輪**（`51f1a65e`）——codex／composer／grok 全數 APPROVED，14 條修訂（A-002..A-015）生效。③殘留 `R-B1-1` **未釘死**，維持 `needs-research`。另有兩件由該批衍生：**repo 內 11 條既有紅測試已清**（`1f9dceac`；10 條修測試、1 條先標 `xfail(strict)`，**產品碼零改動**，依使用者「以現行程式碼為準、測試可能過時」之裁定）；**`survivor_contract` 事件模式對帳誤擋已修**（`0f09e30f`／`6981b79f`）——事件過濾後列數與全軸切分列數屬**不同母體**卻被直接相比，導致事件 IC 分析整段中止，修法三落點＋兩道守衛，7 條 mutation `closure: CLOSED`，review R2 三家零 finding。**B2 已落地（2026-08-25，待三家 code review）**：Task 1.2 CSV 欄名對映端點（對映層轉呼與 `/import-events` 同一 `import_records`，V-3 兩重 oracle）、Task 1.3 `source_file_digest` 綁完整 `CaseData` 列且一律由後端算（承載點＝既有 `/search/task/{id}/result` 增兩鍵，不新增 route；前端 `sha256Hex` 移出 `eventExport.ts` 至 `ruleDigest.ts` 使「無模組同時碰雜湊入口且寫 digest」成結構保證）、Task 1.4 `detect_t0_unit_ms()` 單一門檻導出兩帶且判不出即拒、Task 1.8 異質列拒收（比對正規化後之列，只在使用者匯入路徑啟用）。驗收：`gap3_csv_import` 13／`gap3_t0_unit_detect` 7／`gap3_heterogeneous_rows` 6／`gap3_source_digest` 12／vitest `canonicalSourceCoverage` 14／vitest 全套 198／`npm run build` rc=0；**mutation 9 條 `closure: CLOSED`**（receipt `handoffs/run_receipts/gap3ux-b2-all-mutations.receipt.json`）。🔴 一處與 TODO 字面不同已具名回報：Task 1.3 承載點採 SPEC 之「既有匯出流程服務端入口」＝`api/routes/case_search.py`，因 `api/routes/case.py` 之 `@router` 無一持有 `cases`。**下一步＝B3＝Task 1.11／1.12／1.9。**其後才是使用者 **UAT B 段 13 項簽字** ⇒ epic 收案（未簽字不收案） | registry #3＋SPEC／TODO（FROZEN）＋`docs/GAP3_EVENT_TODO.D-001.md`＋`handoffs/reconcile/20260821-gap3-b{1-review-r4,2-review-r3,3-review-r2,4-review-r4}/synth.md` |
| GAP-4 Pooled/Panel IC | 未開票 | — | 同上 #4 |
| GAP-5 容量 ADV 接線 | 未開票 | **條件觸發**：volume 資料源 | 同上 #5 |
| GAP-6 430K 規模防護 | 未開票 | 併 IC-PERF epic | 同上 #6 |
| 票 A（timing-overlap 診斷） | **未開票** | Phase 4；前置見下節 | 本檔下節 |
| 票 B（多標的橫截面 attribution） | **未開票，條件觸發** | 只有宇宙變多標的才成立 | 本檔下節 |
| FU-1 exposure `fillna` fail-closed | 未做 | 碰到再處理 | 本檔下節 |
| FU-2 cache close carrier index 對齊 | 未做 | **票 A／B 的硬前置** | 本檔下節 |

🔴 **優先序（2026-08-14 使用者明示「現在開始就是要回去做量化主線」）**：
量化主線 **優先於** 治理。此句覆蓋兩條舊裁決——P0 之「完成後才回 IC」（2026-07-05）、
「治理優先於產品線」（2026-08-04）。

---

## 量化主線（IC 分析）

**已完成**：`ic-la0` → `ic-la1` → `ic-la2`（前瞻整治三站）→ `ic-1c`（Net IC 量綱）→
`ic-1cfr`（canonical 因子報酬序列 F0–F5.2）→ `ic-1d`（factor attribution 六批 B0–B5）→
`ic-1e+1b`（HAC 顯著性＋FDR 接線＋xsec p 值；**本行 2026-08-17 補記，原漏列**）。
🔴 `ic-1d` **B4／B5 亦已完工**（2026-08-14 逐項查證：7 支 mutation 探針＋cache/force 兩測、
`FactorExposureRadar.test.tsx`、Radar 契約地雷殘留 0、ExportButtons 舊判斷殘留 0、前端 triage 檔皆在）。

**✔ IC 全棧健檢 epic 已收工（2026-08-17）**——四步全走完（偵察四方 reconcile→SPEC/TODO 凍結
→六批實作 3×P0 修復＋契約 SoT＋wiring 閘門→三家 code review 全 CLOSED 三家戳記）。
原定四步（存檔備查）：

1. **discovery sweep**：Claude＋三委員平行，產「後端產出／前端消費／wiring／空態」四欄表
2. **quant gap analysis**：現況 vs 業界；複審 4 個 deferred（funnel／capacity／regime IC／walk-forward+CPCV）
3. **建 typed 契約 SoT ＋ wiring 閘門**（順手修 #1 幽靈＝原 `1f`）
4. 跑閘門確認閉合，之後自動守

設計原則（使用者洞察）：①audit 先天不完整 ⇒ time-box ②**手動快照會腐爛 ⇒ 把發現做成機器閘門**
③分層防禦。底稿＝`handoffs/20260624-ic-map-WHOLEMAP.md`（**6/24 版，已隔月過時，須逐條複核**）。

✅ **底稿複核已完成**（2026-08-17，四方獨立＋reconcile）：28 條逐條標定＝已修/部分修/變形 ≥15、
未修 7、未查具名 6；三個 P0 仍活（分位圖巢狀 schema 空圖／xsec 硬編空殼／事件 silent fallback）。
白話版＝`白話說明/IC健檢偵察結果.md`；技術收斂＝`handoffs/reconcile/20260817-ichc-x-consult-r1/`（本地）。

🔴 **本節曾整段消失十天**：`aae04295`（2026-08-05）把 ROADMAP 由 393 → 111 行、「敘事移出 Archived」，
連同量化主線的下一步一起砍掉，直到 2026-08-14 使用者追問才發現。完整敘事仍在
`docs/Archived/ROADMAP_P16_NARRATIVE_20260805.md:139-157`。

### 後續兩票（皆 Phase 4，不插隊）

- **票 A — 策略 timing-overlap／clone score 診斷**：回答「ML 是否只在做簡單因子規則」。
  **開票前置＝先修 equity curve 契約**（**已於 2026-08-18 PA-CUMSUM 完成**：`EquityCurveData` 改單利／複利四序列＋四鍵終值、多標的逐 timestamp 等權組合、缺值 fail-closed）；
  殘餘：`prediction_analyzer.calculate_strategy_equity_curve` 只有 long/flat 無做空、
  `api/routes/pattern_analysis.py` 之 `actual_return.fillna(0)` 仍在（缺報酬視為 0，`predicted_proba` 缺值已改 4xx）。
- **票 B — 真·多標的橫截面 attribution**：**條件觸發，只有宇宙變多標的才成立**。
  前置＝CS factor-return 管線（`factor_return_analyzer.py:272-287` 現僅收單一 `future_returns: pd.Series`）
  ＋持倉權重 canonical 定義＋`analyze_cross_sectional` 與 deep 棧整合。
- **根因備忘（防未來重撞）**：單標的下 `ls_returnᵢ=positionᵢ⊙r`、組合報酬＝`position_p⊙r`，
  共用同一 `r` ⇒ OLS 只識別 **position 重疊度**非風險曝險。β 可誠實命名 timing-overlap，
  **禁冒充 Barra attribution**。

### 兩筆 follow-up（2026-07-22 三方 IN-SCOPE-PASS 後登記，防丟）

- **FU-1 exposure 家族 `fillna` fail-closed 化**：`factor_exposure_analyzer.py:111-307` 三函式壞值靜默
  `fillna(0.0)`。嚴重度中（預設 `enabled=False`、僅餵 Radar 診斷非交易決策）。修法＝比照 `1d` B2。
- **FU-2 cache close all-NaN carrier index 對齊**：kline `RangeIndex` vs features `DatetimeIndex` 對不齊。
  **是票 A／票 B 的硬前置**（全 NaN carrier 上無法接真歸因）。

---

## 測試策略（2026-08-14 使用者定：「邊走邊建立」）

**建測試時的優先序**（前三類的紅綠，使用者可在**不讀程式碼**的前提下採信；第四類不可）：

1. **性質檢驗**（`t` 不得依賴 `t+1`、跨 symbol 換料另一標的輸出不變、合併前後守恆）
   ——**不需要凍結期望值，所以不會過期**
2. **真實 kline**（`data_cache/feature_klines/kline_cache.h5`；禁合成 fixture，既有鐵律）
3. **與第三方實作對照**（`scipy`／`statsmodels` 等）——量尺不是本專案產的
4. ⚠️ **凍結 golden 比對**：能不用就不用；非用不可時**改行為的當下必須重凍**

**病根（使用者 2026-08-14 指出，邏輯上無反駁餘地）**：基準與測試**兩側都是 Claude 產的**，
拿一個量另一個是循環論證 ⇒ 使用者無法判斷紅綠真假。**只有非本專案產生的量尺逃得出這個圈。**

**既有 32 個失效基準／40 個疑似孤兒＝不大清**（`scripts/golden_staleness_check.sh` 的歸屬判定
**已實測有兩個 bug**——檔名碰撞與動態組路徑，其輸出**不得用於刪檔**，詳見該檔頭）。
處置＝**碰到才處理**：動到某模組而其 golden 炸了，當場決定重凍或作廢。

---

## ✅ 已完成

歷史條目移至 `docs/ROADMAP_DETAIL.md`（**搬走不等於作廢**；要作廢請明寫）。
