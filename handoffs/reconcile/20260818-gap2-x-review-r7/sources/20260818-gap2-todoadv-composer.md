brief-kind: review

# GAP-2a／2b TODO adversarial 審查 R7 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R7`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-todoadv-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R1）｜義務來源：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check todo` PASS | fact-verified | **成立** — `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` |
| `todo_spec_crosscheck` SMOKE PASS | fact-verified | **成立** — `bash scripts/todo_spec_crosscheck.sh` → `CROSSCHECK SMOKE PASS` |
| Task 4.0／4.2 `persist_suppressed` 不構成 SPEC 義務漂移 | assumed | **成立（無需延伸檔 A1）** — TODO Task 4.2 L220 已具名「B4 commit 內對契約檔之允許修改；測試 1.0-① 鍵集不變，僅值增」；與 SPEC Task 1.0「reason 字面唯一列舉處」相容，屬實作期契約值擴充而非新義務 |
| Task 1.2 步驟 6「契約讀字面」與 Task 4.1 ⑫「AST 掃 orchestrator 常數」可同時成立 | assumed | **部分成立、有歧義** — 見 `COMPOSER-R7-P2-01`；不阻 B1 但 B4 前須補一句規則 |
| Task 3.1 `build_survivor_output` 參數足以組契約＋hash 可取得 | assumed | **不成立** — `summary_by_feature` 簽名缺漏（P1-02）；`features_path` 未入 cache（P1-03） |
| 五批可獨立綠 | assumed | **B1–B4 拓撲成立**；B5 依 B4 `STAGE_OVERRIDE_PATHS` 成立；但 B1 Gate 命令本身假綠（P1-01） |
| Task 4.1 四處掛載敘述足以定位 orchestrator | assumed | **analyze／refilter 足夠**；第四處 `_run_full_sample_fallback` 語意含糊（P2-02） |
| Task 5.1 與 `ic_wiring_check` R1a／R1b 相容 | assumed | **R1a／R1b 機檢可過、功能不過** — 具名 preset 分支未覆蓋 toggle 關閉（P1-04） |

---

## COMPOSER-R7-P1-01

**斷言**: §B B1→B2 Gate 與 Phase B1 Gate 之 `pytest … test_survivor_contract.py -k load test_marginal_ic.py` 會因 `-k load` 把 `test_marginal_ic.py` 全檔 deselect，Gate 可假綠。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:32,110` 命令字面；對照探針 `pytest tests/momentum/Analysis/test_ichc_contract_sync.py -k sync tests/momentum/Analysis/test_ic_persist_redirect_unit.py --collect-only` → `41 items / 36 deselected / 5 selected`（第二檔僅 sync 子集）；新檔不存在時同命令 `collected 0 items`。RECHECK: 實作 B1 後改為 `pytest tests/momentum/Analysis/test_survivor_contract.py -k load tests/momentum/Analysis/test_marginal_ic.py -q`（應 0 或極少 marginal 用例）vs `pytest tests/momentum/Analysis/test_survivor_contract.py -k load tests/momentum/Analysis/test_marginal_ic.py -q` 拆成兩條或去掉 `-k load` 於第二路徑。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。B1 交付若只跑 Gate 字面命令，邊際 IC 核心測試可全跳過仍 rc=0。修法：Gate 改為 `pytest tests/momentum/Analysis/test_survivor_contract.py -k load tests/momentum/Analysis/test_marginal_ic.py -q` → `pytest tests/momentum/Analysis/test_survivor_contract.py -k load && pytest tests/momentum/Analysis/test_marginal_ic.py -q`（或單一 pytest 兩路徑不加共享 `-k`）。

---

## COMPOSER-R7-P1-02

**斷言**: Task 3.1 `build_survivor_output` 簽名（L151）缺 `summary_by_feature`，與 L155 實作要點③「**加此參數**」及 Task 4.2 L220 呼叫 `summary_by_feature=...` 矛盾，執行端無法依簽名寫碼。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:151` 簽名列至 `report_ref: str) -> dict` 無 `summary_by_feature`；L155「IC 快照…傳入 `summary_by_feature`——**加此參數**」；L220 `build_survivor_output(..., summary_by_feature=..., ...)`。SPEC Task 3.1 亦要求 survivors IC 快照來自 report summary，但 TODO 簽名未收斂。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。B3 實作者會在「從 report_meta 抽」vs「獨立參數」間自行判斷，易與 Task 4.2 呼叫不一致。修法：L151 簽名補 `summary_by_feature: dict[str, dict]`（或明確型別）並在 L155 註明鍵集（`ic_mean`／`icir`／`p_value_adj`／`pass_class`／`train_ic` 等）。

---

## COMPOSER-R7-P1-03

**斷言**: Task 4.2 要求 `features_source_hash`／`features_path` provenance，但 orchestrator `_ic_cache` 未存 `features_path`，`_persist_outputs` 亦無該參數，TODO 未指定何處 cache，執行端會卡住。

**碼證**: Task 4.2 L221–222：`features_source_hash`＝features h5 bytes hash、`features_path` 入 `build_survivor_output`；`momentum/Analysis/ic_filter_orchestrator.py:3449-3464` `_ic_cache` 鍵集無 `features_path`；`analyze()` L862 收 `features_path` 僅傳 `_stage0_ingestion` L886；`_persist_outputs` L3789 簽名無 path。`label_series` 在 cache（L3451）⇒ `labels_content_hash` 可行；path 不行。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。B4 倖存者檔 provenance 缺欄或執行端臆測路徑。修法：Task 4.1 增「`analyze()` 將 `features_path`／`labels_path` 寫入 `_ic_cache`（或 metadata）」；Task 4.2 `_persist_outputs` 明確讀取來源。

---

## COMPOSER-R7-P1-04

**斷言**: Task 5.1 只要求 `getEffectiveConfig` 的 `stageOverrides` 加 `marginal_ic`，但未要求具名 preset 分支（foundation／intermediate／advanced）像 `fdr_correction` 一樣送出並由 `_apply_tier_config` 消費，導致驗證⑤「toggle 關 ⇒ marginal_ic.enabled=false」在預設 preset 下不成立。

**碼證**: Task 5.1 L257：`getEffectiveConfig` stageOverrides 加 `marginal_ic`；`frontend/src/store/icAnalysisStore.ts:366-374` 非 custom 僅回 `{ stage_overrides: { fdr_correction: … } }`；`momentum/Analysis/ic_filter_orchestrator.py:4047-4056` 具名 preset 只映射 `fdr_correction`→`significance.fdr.enabled`；`scripts/ic_wiring_check.py:91-96` R1a 只查 toggle⊆消費集，不驗證具名 preset 功能路徑。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。使用者於 intermediate preset 關閉邊際 IC，後端仍 `MarginalICConfig.enabled=True`（Task 4.1 預設），違反使用者裁決「toggle 可關」。修法：Task 5.1 補① `getEffectiveConfig` 具名 preset 分支送 `marginal_ic`（比照 L371 fdr）；② Task 4.1 `_apply_tier_config` else 分支映射 `STAGE_OVERRIDE_PATHS["marginal_ic"]`；③ 驗證⑤ 明寫須覆蓋 intermediate preset。

---

## COMPOSER-R7-P2-01

**斷言**: Task 1.2 L85「字面值一律由 `load_survivor_contract()` 讀出、不寫死於程式」與 Task 4.1 L206「orchestrator 內 reason 以契約取值或以常數對照測試⑫ AST 掃描」並存但未定優先順序，B1／B4 可能一邊全讀檔、一邊字串常數，測試⑫與「不寫死」語意衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:85,206`；`compute_marginal_ic` 在 `marginal_ic.py`（B1）、`_stage6b_marginal_ic` 在 orchestrator（B4）為不同檔。RECHECK: 實作後 `grep -n 'disabled_by_config\|no_holdout_split' momentum/Analysis/marginal_ic.py momentum/Analysis/ic_filter_orchestrator.py`。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=Medium。不阻 B1；B4 前須統一規則：建議「runtime 值一律 `load_survivor_contract()`；orchestrator 若留字面常數僅供 AST⊆契約測試，且與 runtime 讀檔結果一致」。

---

## COMPOSER-R7-P2-02

**斷言**: Task 4.1 L202 列四處掛載含 `_run_full_sample_fallback()`，但該函式 L1109 僅呼叫 `analyze()`，stage6b 實際只需插入 `analyze()` L1038–1047 與 `refilter()` L1746–1754；第四處未說明是「獨立呼叫點」還是「確保 fallback 語意」，執行端可能重複掛載或漏 `fit_scope=full_sample`。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:202`；`ic_filter_orchestrator.py:1038-1047` stage6→stage7 無 6b；`1065-1151` fallback 經 `analyze()` 間接覆蓋；L201 `_stage6b` 已述 fallback⇒`fit_scope="full_sample"`。brief 假設行號 1039–1063／1736–1765 與 repo 一致（已複驗）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=Medium。修法：Task 4.1 改為「兩個插入點：`analyze()` stage6 後 stage7 前；`refilter()` stage6 後 `_stage7_report` 前；`analyze_full`／`_run_full_sample_fallback` 經 `analyze` 覆蓋，fallback 語意由 `_stage6b` 讀 `split_context`／metadata 決定 `fit_scope`」。

---

## 必答 1 — Agent 可執行性

| Task | 判定 | 卡住／需自行判斷處 |
|---|---|---|
| 1.0–1.3 | 可執行 | 無（B1 Gate 命令見 P1-01） |
| 2.1–2.2 | 可執行 | 無 |
| 3.1 | **需補簽名** | `summary_by_feature`（P1-02） |
| 3.2 | 可執行 | 無 |
| 4.0 | 可執行 | `gap2_canonical_sha` import 路徑已寫清 |
| 4.1 | **需補 cache／掛載語意** | `features_path` cache（P1-03）；四處掛載（P2-02）；reason 規則（P2-01） |
| 4.2 | **需補 path 來源** | provenance path／hash（P1-03） |
| 4.3 | 可執行 | bench 無時間閾值已寫清 |
| 5.1 | **需補 preset 分支** | 具名 preset toggle（P1-04） |

整體：13 Task 中 4 處有 BLOCKING 級缺口；其餘檔案／函式／驗證命令足夠。

---

## 必答 2 — 義務覆蓋（SPEC→TODO）

| SPEC 區塊 | 覆蓋 | 漂移 |
|---|---|---|
| §A D1–D7／D3′／D3″ | §0＋Task 1.2／2.1／4.1 | 無方向漂移 |
| §G 1–4 | Task 4.0／4.3＋1.2／2.1／3.1 | Task 4.0 自 §G 凍結獨立化（追溯表 L283）— 語意一致 |
| §V 24 條 | 各 Task mutation＋`gap2_mutation_probe.sh` | 無 |
| §C 白名單 | §0 | 無 |
| §N R1／R2／R3／R5 | registry 登記＋無 Task | 與 SPEC 一致 |

**義務覆蓋完整**；缺口在執行細節非 SPEC 漏項。

---

## 必答 3 — 批次獨立性／forward dependency

| 批 | 判定 | 備註 |
|---|---|---|
| B1 | 獨立綠（修 Gate 後） | 不依 report 契約；P1-01 不影響批間依賴 |
| B2 | 獨立綠 | 依 B1 dataclass／契約鍵 |
| B3 | 獨立綠 | 不改 `ic_report_contract.json`；Gate 含 `test_ichc_contract_sync` |
| B4 | 獨立綠 | 4.0→4.1→4.2→4.3 批內順序明確；契約增鍵與 orchestrator 同 commit |
| B5 | 依 B4 | `STAGE_OVERRIDE_PATHS["marginal_ic"]` forward dep 已聲明；P1-04 為批內實作缺口 |

Task 4.0 位置：B4 首件，與 SPEC「4.1 動工前 freeze」等價，無義務漂移。Task 4.2 `persist_suppressed`：B4 契約值增，已自洽（§0）。

---

## 必答 4 — 取巧面

| 區域 | 可假綠風險 |
|---|---|
| B1 Gate | **高** — `-k load` 跳過 `test_marginal_ic.py`（P1-01） |
| §G oracle | 低 — 容差／seed 寫死於 SPEC §G 表 |
| `n_regressions` | 中 — Task 4.3 只斷言 600、receipt 無時間／RSS 閾值（SPEC 刻意）；計數錯可過若未跑 bench |
| mutation 探针 | 低 — sed+pytest rc 雙斷言 |
| B5 toggle | **高** — 具名 preset 下前端關、後端開（P1-04） |
| wiring R1a | 中 — 機檢可綠但 preset 功能不綠（P1-04） |

---

## 必答 5 — 測試設計

- `test_mutation_*`：各 Task 已映射 §V-n 或 `gap2_mutation_probe.sh` case 表；探針 case 與 §V 編號一一對應（V-19 三欄參數化為刻意例外）。
- falsification：O1a raw 探針、O7 獨立參考、V-13..16 golden／OOS 語意 — 指向真實失敗模式。
- 缺口：B1 Gate 未實跑 marginal 測試（P1-01）；Task 5.1 驗證⑤若只測 custom preset 會假綠（P1-04）。

---

## 必答 6 — 可 Frozen 進 B1？

**不可 Frozen**（TODO 需修補後再 Frozen）。

**BLOCKING 清單**（修完可重審 B1）：
1. P1-01：修正 B1 Gate／Phase B1 pytest 命令（拆分或移除共享 `-k`）
2. P1-02：Task 3.1 簽名補 `summary_by_feature`
3. P1-03：Task 4.1／4.2 明確 `features_path`（與 labels path）cache 與 provenance 接線
4. P1-04：Task 5.1＋4.1 補具名 preset 之 `marginal_ic` toggle 端到端

**建議一併修（非阻 B1）**：P2-01 reason 規則；P2-02 掛載點敘述。

---

## Verdict：需修補後派工

TODO 與 SPEC R7 義務方向一致、追溯表完整，但四處 BLOCKING 執行缺口（Gate 假綠、簽名缺參、provenance path、preset toggle）會讓 Agent 在 B1 Gate／B3 組裝／B5 驗收卡住或假綠。修補上述四項後可 Frozen 進 B1。

---

ASSUMPTIONS_VERIFIED: `template_check todo` PASS；`todo_spec_crosscheck` SMOKE PASS；`pytest … -k sync` 雙檔 collect 探針；`_ic_cache` 鍵集 grep；`getEffectiveConfig`／`_apply_tier_config` 具名 preset 分支讀碼；orchestrator stage6/7 行號 1038–1047、1746–1765  
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md`；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md`；`pytest tests/momentum/Analysis/test_ichc_contract_sync.py -k sync tests/momentum/Analysis/test_ic_persist_redirect_unit.py --collect-only`；`shasum -a 256` 來源摘要  
FAILURES_SEEN: none（審查階段未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（審查產出）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-todoadv-composer.md`  
TMP_CLEANUP: 本輪未建立 `/tmp` workdir；`/private/tmp/claude-501` 保留  
STATUS: DONE
