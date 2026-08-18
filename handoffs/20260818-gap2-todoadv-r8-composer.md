brief-kind: review

# GAP-2a／2b TODO adversarial 審查 R8 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R8`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-todoadv-r8-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R2）｜義務來源：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..3）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check todo` PASS | fact-verified | **成立** — `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` |
| `todo_spec_crosscheck` SMOKE PASS | fact-verified | **成立** — `bash scripts/todo_spec_crosscheck.sh` → `CROSSCHECK SMOKE PASS` |
| Task 4.0／4.2 `persist_suppressed` 不構成 SPEC 義務漂移 | assumed | **成立** — 延伸檔 A1-1 已記錄；Task 4.2 L220 鍵集不變僅值增 |
| Task 1.2 步驟 6 與 Task 4.1 ⑫ AST 可同時成立 | assumed | **成立** — Task 4.1 L206 已釘「runtime 一律 `load_survivor_contract()`；AST 可選、無常數 vacuous」 |
| Task 3.1 參數＋ hash 路徑可取得 | assumed | **成立** — L151 簽名含 `summary_by_feature`／`root_analysis_status`；Task 4.1 L202 明列 `self._features_path`＋persist 顯式 `label_series` |
| 五批可獨立綠 | assumed | **成立** — B1 Gate 已分兩條 pytest（§B L32）；B5 依 B4 `STAGE_OVERRIDE_PATHS` |
| Task 4.1 掛載敘述足以定位 orchestrator | assumed | **成立** — 兩插入點＋`_in_fallback_rerun`（L202）；行號 `:1039-1047`／`:1746-1754` 與 repo 一致 |
| Task 5.1 與 `ic_wiring_check` 相容 | assumed | **成立** — Task 5.1 已列 FeatureTierPanel／具名 preset／`_apply_tier_config`／驗證⑤三路徑 |

---

## COMPOSER-R8-P1-01

**斷言**: Task 4.2 L220 偽碼仍寫 `event_identity=self._ic_cache["event_identity"]`，與 Task 4.1 L202「`_persist_outputs` 在 `_ic_cache` 建立前被呼叫、須顯式 kwargs、不讀 `_ic_cache`」直接矛盾；照 L220 實作會在 persist 時讀到**上一輪 stale cache** 或 `KeyError`。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:202`「新增 kwargs `stage6b_results`／`event_identity`／`features_path`／`label_series` **顯式傳入**（不讀 `_ic_cache`）」；L220「`event_identity=self._ic_cache["event_identity"]`」；`momentum/Analysis/ic_filter_orchestrator.py:3432` `_persist_outputs` 早於 `:3449` `self._ic_cache = {`。RECHECK: 對照 L202 與 L220 是否同寫 `event_identity` 來源（應為 persist kwarg 或 `self._event_identity`）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[MAJOR] 信心度=High。B4 `_persist_outputs`／倖存者檔 provenance 會用錯事件身分或執行期炸。修法：Task 4.2 L220 改為 `event_identity=event_identity`（`_persist_outputs` 新 kwarg，由 `_stage7_report` 傳 `self._event_identity`）或明寫 `self._event_identity`；刪除 `_ic_cache` 讀取。

---

## COMPOSER-R8-P2-01

**斷言**: §0 L12 與 Task 4.1 標題 L197 仍寫「`_stage6b` 掛四處／四處掛載」，正文 L202 已收斂為「**兩個插入點**」，執行端若只讀 §0 會重複掛載或找第四呼叫點。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:12`「掛四處」；L197「stage 6b 四處掛載」；L202「掛載**兩個插入點**…`analyze()`…`refilter()`」。R7 T3 已接受兩插入點處置。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[MINOR] 信心度=High。不阻 B1；建議 §0／Task 4.1 標題改「兩處插入」與 L202 對齊。

---

## R8 必核（T1–T6；逐條 verdict）

| 群集 | verdict | 依據（TODO 行號） |
|---|---|---|
| **T1** Gate 分跑＋B1 十條唯一對映 | **PASS** | §B L32–33 兩條分開 pytest；Task 1.3 L98–99 十條 V_ID 唯一；V-22／V-24 僅 B4（L99） |
| **T2** `build_survivor_output` 簽名＋OOS 佔位＋root 注入＋golden case_id | **PASS** | L151 `summary_by_feature`／`root_analysis_status`；L79 `None` 佔位＋`_stage7_report` 注入；A1-2／A1-3；Task 4.0 A1-2 |
| **T3** 兩插入點＋`_in_fallback_rerun`＋persist kwargs＋paths | **PASS（L220 除外）** | L202 兩插入點／旗標／顯式 kwargs／`self._features_path`；**L220 `event_identity` 來源未同步** → P1-01 |
| **T4** B5 toggle 端到端 | **PASS** | Task 5.1 L253–262 FeatureTierPanel／具名 preset／`_apply_tier_config`／驗證⑤三路徑 |
| **T5** 警語子字串＋bench 觀測 | **PASS** | L256 警語不含「獨立 OOS 驗證」（`python3` substring 檢 `False`）；L236 bench 觀測、無資源閾值 |
| **T6** reason `load_survivor_contract()`＋`persist_suppressed` | **PASS** | L206 runtime load；A1-1；Task 4.2 L220 `persist_suppressed` |

---

## 必答 1 — Agent 可執行性

| Task | 判定 | 卡住／需自行判斷處 |
|---|---|---|
| 1.0–1.3 | 可執行 | 無 |
| 2.1–2.2 | 可執行 | 無 |
| 3.1 | 可執行 | 簽名已含 `summary_by_feature`（L151） |
| 3.2 | 可執行 | 無 |
| 4.0 | 可執行 | 無 |
| 4.1 | 可執行 | `_stage7_report` 須增 `stage6b_results` 參數可從 L202 插入點推得 |
| 4.2 | **需對照 4.1** | L220 `event_identity` 來源（P1-01） |
| 4.3 | 可執行 | bench 無時間閾值已明示 |
| 5.1 | 可執行 | 無 |

整體：13 Task 僅 Task 4.2 偽碼一處與 4.1 衝突；其餘檔案／函式／驗證命令足夠。

---

## 必答 2 — 義務覆蓋（SPEC→TODO）

| SPEC 區塊 | 覆蓋 | 漂移 |
|---|---|---|
| §A D1–D7／D3′／D3″ | §0＋Task 1.2／2.1／4.1 | 無 |
| §G 1–4 | Task 4.0／4.3＋1.2／2.1／3.1 | Task 4.0 獨立化語意一致 |
| §V 24 條 | 各 Task mutation＋`gap2_mutation_probe.sh` | 無 |
| §C 白名單 | §0 | 無 |
| §N R1／R2／R3／R5 | registry「GAP-2 待補完」 | 無 |

義務覆蓋完整；殘留為 TODO 內部文字未同步（P1-01／P2-01）。

---

## 必答 3 — 批次獨立性／forward dependency

| 批 | 判定 | 備註 |
|---|---|---|
| B1 | 獨立綠 | Gate 分跑（§B L32） |
| B2 | 獨立綠 | 依 B1 |
| B3 | 獨立綠 | 不改 report 契約 |
| B4 | 獨立綠 | 4.0→4.1→4.2→4.3；契約增鍵同 commit |
| B5 | 依 B4 | `STAGE_OVERRIDE_PATHS["marginal_ic"]` 已聲明 |

Task 4.0 為 B4 首件；Task 4.2 `persist_suppressed` 走 A1-1，無義務漂移。

---

## 必答 4 — 取巧面

| 區域 | 可假綠風險 |
|---|---|
| B1 Gate | **低** — 已分兩條 pytest |
| §G oracle | 低 — 容差／seed 在 SPEC §G 表 |
| `n_regressions`／bench | 低 — L236 明示觀測、僅計數上界 |
| mutation 探针 | 低 — 十條唯一對映（L98–99） |
| B5 toggle | **低** — 具名 preset 三路徑已寫（L262） |
| wiring R1a | 低 — R1b 待 B4 加 `marginal_ic` 鍵 |

---

## 必答 5 — 測試設計

- `test_mutation_*`／`gap2_mutation_probe.sh`：V-n 與 `--batch` 唯一對映（L98–99）；V-19 三欄參數化為刻意例外。
- falsification：O1a raw 探針、O7 參考實作、V-13..16 golden／OOS — 指向真實失敗模式。
- 缺口：無新增（R7 四 BLOCKING 已收斂）。

---

## 必答 6 — 可 Frozen 進 B1？

**可 Frozen**（TODO → FROZEN → B1），**建議開 B4 前**修 Task 4.2 L220（P1-01）與 §0／標題「四處」殘留（P2-01）。

**BLOCKING 清單（阻 Frozen）**：無。

**開 B4 前建議修補（非阻 B1）**：
1. P1-01：Task 4.2 L220 `event_identity` 改顯式 kwarg／`self._event_identity`
2. P2-01：§0 L12、Task 4.1 標題「四處」→「兩處插入」

---

## Verdict：可 Frozen

R7 三家 20 findings（T1–T6）已寫回 DRAFT R2＋延伸檔 A1-1..3；本輪僅餘 Task 4.2 偽碼與 Task 4.1 persist 順序之一處 MAJOR 文字衝突（P1-01），不阻 B1 契約／純函式批次。修一行即可消除 B4 執行歧義。

---

ASSUMPTIONS_VERIFIED: `template_check todo` PASS；`todo_spec_crosscheck` SMOKE PASS；orchestrator persist/cache 行號 3432 vs 3449；B5 警語 substring；§B Gate 字面；`build_survivor_output` 簽名 L151  
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → SMOKE PASS；`python3` substring 警語檢查  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-todoadv-r8-composer.md`  
TMP_CLEANUP: `/private/tmp` 無本輪專用 workdir；`/private/tmp/claude-501` 保留  
STATUS: DONE
