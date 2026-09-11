# SPLITUNIFY D-001 延伸 — COMPOSER R5

task-id: 20260911-SPLITUNIFY-X-REVIEW-R5  
family: composer  
brief: `handoffs/20260912-SPLITUNIFY-D001-REVIEW-R1-BRIEF.md`  
findings-round: R5  
review-target: `docs/SPLITUNIFY_SPEC.D-001.md`（sha256[:12]=`82b4e2b544b0`）  
BASE: `docs/SPLITUNIFY_SPEC.md` @ `b095cc754cb9de26bbf2dd35564db329aca3c98f`

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| Task 3.2「存活至」足以支撐 D 延伸類別 | brief fact-verified | **成立** — BASE `Task 3.2` 末段逐字寫「改寫為支援分支（見 §N R-1）」與「不得只刪 raise」 |
| 觸及面四欄錨點逐字存在於原檔 | brief assumed | **成立** — 八個 anchor 已 `rg -F` 對讀 BASE @ b095cc7，全命中 |
| `SU-RESID-3` 為 §N 既有殘留 | D-001 檔頭 | **不成立** — BASE `§N` 無 `SU-RESID-3`；殘留僅在 `SPLITUNIFY_TODO.md:472` 與 consult 收斂；不擋 D 但觸面敘述不精確 |
| 指紋 payload 足以兩端重算一致 | brief assumed | **部分成立** — 投影端 `_index_as_ms`＋`assert_positional_rows` 路徑封閉；**producer 端取哪條 ts 陣列未寫**（見 P2-02） |
| `debt_ledger.sh --has-open` rc=0 | brief 前提 | **不成立（本輪 OPEN）** — 實跑 `rc=1`（與 brief 預期一致） |

---

## 必答 1–9（立場＋正反各一句）

**1. 類別判定（D vs R）**  
**立場：D 延伸成立，不必升 R。** ①理由成立：BASE `Task 3.2` 已預告 per-symbol 支援後改寫 raise 分支，D-001 即該落地。②**反面**：C-2 字面寫「多 symbol 批在 per-symbol 投影完成前一律 fail-closed」——若無 Task 3.2 存活至語句，改為支援會與 C-2 字面互斥而需 R；但 Task 3.2 存活至＋覆蓋風險已把此改寫授權寫死，故不互斥。

**2. 觸及面宣告**  
**立場：八個 anchor 逐字存在，但有一處實際會動到卻未宣告。** 對讀：`rg -F` 八條 anchor @ b095cc7 全 1 hit（C-2／Task 3.2／§N／C-4／§V／§G／C-0／C-1）。**反面**：Task 8.1 改 `derive_event_split_from_plans` 簽名為 per-symbol `Mapping`，但 **C-4 未列覆寫**（只列依賴）——實作會動到 C-4 簽名卻未宣告（見 `COMPOSER-R5-P1-02`）。

**3. hash 不變式**  
**立場：碼證支持；逐 symbol 同源對證足夠。** ①`ICSplitAdapter._base_universe_hash(frame,…)` 整框 hash（`ic_split_adapter.py:189-199`）＋ orchestrator 一次寫入各 symbol plan（`ic_filter_orchestrator.py:907-932`）與 D-001-C1 一致。②**反面**：若只靠 hash 字面互異防冒充，會拒收現行 IC 多標的計畫；D-001 改由逐 symbol 指紋＋首尾對證承擔身分——在 **producer 確實寫入指紋** 前提下足夠；producer 缺口見 P1-01。

**4. 指紋定義可重算性**  
**立場：投影端封閉；producer 端有一處未定義。** ①未定義處：`row_time_fingerprint` 物件結構（provenance 是嵌套 dict 還是 SplitPlan 平鋪欄位）未寫；空 `row_index` plan 的指紋是否為 `sha256("[]")` 未寫（train 可空）。②**反面**：重複 `row_pos` 會被 `assert_positional_rows` 擋（`split_preview.py:123-126`）；NaT 會被 `_index_as_ms` 擋（`split_projection.py:204-205`）；秒／毫秒歧異在投影端由 `assert_epoch_ms_array` 擋秒值（`split_projection.py:213-214`），**不會**走 `_coerce_timestamp_array` 的 `unit="s"` 路徑——但 producer 若在 `split_per_symbol` 用 `_coerce_timestamp_array` 建指紋而投影用 `_index_as_ms`，仍可能分歧（見 P2-02）。

**5. golden 重凍**  
**立場：改前／改後逐值對照重凍足以防「錯誤一起凍」。** ①`freeze_splitunify_golden.py:170-175` 已凍 positions＋首尾 ms 明文，測試可獨立重算 sha256。②**反面**：更便宜作法是只比 `g5_row_fingerprint_positions` 與首尾 ms 不重算全列——但對「中間一列 ts 錯」較弱；D-001 選完整指紋＋逐值對照是正確取捨。

**6. ASSERT 可證偽性**  
**立場：Task 8.3 兩條與 fingerprint 中間列／缺欄兩條可證偽；Task 8.1 有一條可能綠在錯誤 reason。** ①Task 8.1 第二條要求訊息含 `multi_symbol_projection_unsupported`，但 per-symbol `Mapping` API 下「只給 A 之 plan、事件含 B」更可能是缺 key／symbol mismatch，實作可用不同 `ValueError` 字面仍滿足「rc!=0」——**斷言過弱**。②Task 8.2「首尾相同中間不同」與「缺 row_time_fingerprint」在跳過比對時會紅；`row_time_fingerprint` 重算兩次相同**若未單測 helper 且只在 happy path 呼叫**，impl 可硬編碼常數 hash 仍過「逐列相同」——需確保 `-k fingerprint` 含獨立 helper 測試（斷言已寫，可執行）。

**7. mutation 對照**  
**立場：M-SU-D1-01～06 各對應一條可紅測試；缺 cross-symbol row_index。** 01～06 與 Task 8.1／8.2／8.3 的 `-k per_symbol|fingerprint|insufficient` 一一對應。**反面**：D-001-C1 第 4 點「跨 symbol 禁共用 row_index 數字空間」無 `M-SU-D1-07`——用 symbol A 的 `feature_index` 解 symbol B 的 `row_index` 可靜默錯分（見 P2-03）。

**8. 範圍切割**  
**立場：切割自洽，留下可接受中間態。** ①b8 後投影層支援多 symbol＋完整指紋，但 `pipeline.py:745-748` 仍傳單一 plan／單一 index；事件掃描端仍 event-study-only（D1／R-5 留後）；多 TF 仍 fail-closed（SU-RESID-2）——**中間態明示且保守**。②**反面**：無「本批非做不可」項；SU-RESID-2 可下一批做而不使 b8 自相矛盾。

**9. 可否進入實作**  
**立場：修 P1 後可 `proceed`。** producer 指紋寫入點與 C-4 覆寫宣告補齊前，b8 實作會讓現行單標的 pipeline 全面 fail-closed 或 agent 與 C-4 簽名衝突。

---

## COMPOSER-R5-P1-01

**斷言**: Task 8.2 要求 plan 缺 `row_time_fingerprint` 即 fail-closed，但未指定 IC producer（`split_per_symbol`／orchestrator）何處寫入指紋；僅改投影比對會使 `pipeline.py` 現行單標的路徑在 b8 收案時全面紅。

**碼證**: D-001 Task 8.2 檔案列 `contracts.py`（攜帶）＋`split_projection.py`（比對），**未列** `ic_filter_orchestrator.py`；`pipeline.py:745-748` 仍傳 orchestrator 產出的 `SplitPlan`；現行 `SplitPlan` 無指紋欄（`contracts.py:377-390`）；`split_per_symbol` 建 plan 未寫指紋（`:662-685`）；ASSERT「缺欄 rc!=0」（D-001:66）。RECHECK: `rg row_time_fingerprint momentum/` → 0 生產碼；讀 `pipeline.py:745-748` 與 `contracts.py:625-694`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0;momentum/Analysis/event_samples/pipeline.py#98ee62905643;momentum/core/contracts.py#642aecf26b32

[P1] 信心度=High。b8 實作後 `derive_event_split_from_plans` 對所有 caller 要求指紋，但唯一生產 caller 未更新 ⇒ **單標的 IC 投影全批失敗**（非測試隔離）。修法：Task 8.2 增實作要點——在 `split_per_symbol`（或具名 helper）以與 `_index_as_ms` 同規則從 producer universe 算指紋並寫入 `SplitPlan`；檔案列明 `split_per_symbol` 與 orchestrator 傳遞；或明示「b8 僅測試 synthetic plan、producer 延後」並把 pipeline 排除在收案 gate 外（目前未寫）。

---

## COMPOSER-R5-P1-02

**斷言**: Task 8.1 將投影簽名改為 per-symbol `Mapping`，但觸及面「覆寫」未含 C-4，依賴欄仍指向單一 `train_plan`／`test_plan`／`feature_index` 簽名——agent 會收到互斥權威。

**碼證**: D-001 觸及面「覆寫」僅 C-2／Task 3.2／§N（`:16-17`）；「依賴」含 C-4（`:17`）；Task 8.1 要點①「投影簽名接受 per-symbol 結構」（`:49`）；BASE C-4 簽名仍為單一 `SplitPlan`＋單一 `feature_index`（`SPLITUNIFY_SPEC.md` @ b095cc7 `:161-169`）。RECHECK: `git show b095cc7:docs/SPLITUNIFY_SPEC.md | sed -n '157,170p'`；對讀 D-001 觸及面表。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0;docs/SPLITUNIFY_SPEC.md#b095cc754cb9

[P1] 信心度=High。實作端若只改 `split_projection.py` 會與 C-4（依賴＝不可改）衝突；若改 C-4 則觸及面未宣告 ⇒ 收案機械檢查與 adversarial 追溯失敗。修法：將 `### C-4 …` 列入「覆寫」並給出 overload 簽名（單 symbol 舊簽名可為 wrapper 或 Union 輸入，須逐字寫清）。

---

## COMPOSER-R5-P2-01

**斷言**: D-001-C2 指紋 payload 僅 `[[row_pos, ts_ms],…]` 之 sha256，與依賴之 §G G-5① 四元組 `(position, feature_ts_ms, symbol, base_universe_hash)` 序列化不一致，未說明兩者關係或 G-5 更新步驟。

**碼證**: D-001-C2:39（payload 僅 row_pos＋ts_ms；symbol／provenance「另帶」）；BASE §G G-5①（`SPLITUNIFY_SPEC.md:312-314` @ b095cc7）四元組 canonical；`freeze_splitunify_golden.py:152-155` 用四元組凍結。RECHECK: 對讀 D-001-C2:39 與 BASE §G；`sed -n '152,156p' scripts/freeze_splitunify_golden.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0;docs/SPLITUNIFY_SPEC.md#b095cc754cb9;scripts/freeze_splitunify_golden.py#6fb0c7361dad

[P2] 信心度=High。Agent 可能實作 `row_time_fingerprint` 與 G-5 golden 各用一套 hash ⇒ b8 重凍後 G-5 與 plan 指紋仍不一致、假綠或雙重維護。修法：要麼 D-001-C2 payload 對齊 G-5 四元組，要麼 Task 8.2 明寫「G-5① 改讀 `SplitPlan.row_time_fingerprint` 欄、舊四元組凍結作廢」並列 freeze 腳本改動。

---

## COMPOSER-R5-P2-02

**斷言**: D-001-C2 未指定 producer 指紋計算所取的 timestamp 陣列（全框 `audit_frame` vs per-symbol slice）與投影端 `feature_index` 的對齊規則，兩端可各自合法卻 hash 不同。

**碼證**: D-001-C2:39「producer 當時 universe 上的時刻序列」未指名陣列；`split_per_symbol` 用全框 `ts`＋symbol-local `row_index`（`contracts.py:647,666`）；投影用傳入之 per-symbol `feature_index`（Task 8.1）；IC 路徑 `feature_index` 可能為裁切後 index（`test_plan_symbols_differ` 同題，`test_splitunify_derive.py:310-315`）。RECHECK: 讀 `contracts.py:647-672` 與 D-001-C2:39-41。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0;momentum/core/contracts.py#642aecf26b32

[P2] 信心度=Medium。實作若 producer 用全框 ts、投影用裁切 index，同 row_pos 可對不同 ts_ms ⇒ 指紋永遠紅或 impl 為過測試硬對齊。修法：C2 增一條——指紋必從「該 symbol 的 post-trim `feature_index`」取 ts，且 row_index 為該 index 內 positional ordinals。

---

## COMPOSER-R5-P2-03

**斷言**: D-001-C1 第 4 點禁止跨 symbol 共用 row_index 數字空間，但 mutation 表 M-SU-D1-01～06 無對應項，回歸可漏。

**碼證**: D-001-C1:33-34；mutation 表 `:78-85` 止於 `M-SU-D1-06`（門檻）；§V 無 `M-SU-D1-07`。RECHECK: `rg M-SU-D1 docs/SPLITUNIFY_SPEC.D-001.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#82b4e2b544b0

[P2] 信心度=High。mutant 用 symbol A 的 index 解 symbol B 的 plan.row_index 可靜默錯分而 `-k per_symbol` 仍綠。修法：增 `M-SU-D1-07`｜跨 symbol 混用 feature_index｜`-k per_symbol` 或專用 `-k row_index_scope`。

---

## §1 必查摘要（11 類）

| # | 結果 |
|---|---|
| 1 矛盾/互斥 | C-4 簽名 vs Task 8.1 → P1-02 |
| 2 漏項/端到端 | producer 指紋寫入 → P1-01 |
| 3 不可測驗收 | 無 blocking（ASSERT 多數可執行；Task 8.1 第二條 reason 過弱見必答 6） |
| 4 quant 假設 | 指紋對齊 → P2-01／P2-02 |
| 5–11 | 無額外 blocking |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R5-P1-01,COMPOSER-R5-P1-02
CLOSED:

---

ASSUMPTIONS_VERIFIED: BASE @ b095cc7 八 anchor `rg -F` 全命中；`ic_split_adapter.py:189-199`＋`ic_filter_orchestrator.py:907-932` joint hash；`split_projection.py:569` 整批 `n_test`；`split_projection.py:474-484` 首尾對證；`rg row_time_fingerprint momentum/`→0；`bash scripts/debt_ledger.sh --has-open`→rc=1
TESTS_RUN: `sha256sum docs/SPLITUNIFY_SPEC.D-001.md`→82b4e2b544b0；`git show b095cc7:docs/SPLITUNIFY_SPEC.md | rg -F` 八 anchor；`rg row_time_fingerprint momentum/`；`bash scripts/debt_ledger.sh --has-open`→rc=1；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r5-composer.md --family composer`→見下
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼；指出 D-001 將動 SplitPlan schema／C-4 簽名）
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-x-review-r5-composer.md
TMP_CLEANUP: 已清 `/tmp` workdir（保留 `claude-501`）

STATUS: DONE
