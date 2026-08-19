# Reconcile — 20260819-gap2-b4-review-r21

**來源** 20260819-gap2-b4-review-codex.md, 20260819-gap2-b4-review-composer.md, 20260819-gap2-b4-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-19）

三家共 **4 條**（codex 2 P1；composer sentinel；grok sentinel），下列三個群集**引用全部 4 條，0 掉項**。Verdict：codex「需修補後進 B5」、composer／grok「可進 B5」⇒ 依較嚴：**需修補後進 B5**；2 條全接受（修補走 B4 修補 commit；A1-11 記錄）；三家對 A1-10（scope_id 正規化）皆判成立（grok 另核 git 三版 pre 不變項；composer 段 B-1 亦認可）。戳記輪 r22 兼修補驗收。

Verdict：需修補後進 B5——修補 commit 落地後派 stamp r22（含 codex 反例重跑）；APPROVED ⇒ B4 CLOSED → B5。

### N1 — 落盤 `ic_report_*.json` 缺 `metadata.survivor_output`（五鍵注入發生於 `save_report` 之後）
**引用**: CODEX-R21-P1-01
**處置＝接受**：`_persist_outputs` 於 survivor 五鍵注入後**重存報告**（`save_report` 二次；同 redirect 路徑）⇒ 落盤 JSON 含 `metadata.survivor_output`（互指鏡像）；測試 `test_persisted_report_json_mirrors_survivor_output`（磁碟 report 之五鍵 == 回傳 report）。golden 不受影響（`survivor_output` 在 scrub ②）。

### N2 — provenance `ic_method`／`label_return_type` 取建構時 `self._config` 而非本次 effective config
**引用**: CODEX-R21-P1-02
**處置＝接受**：`analyze()`／`refilter()` 存 `self._current_config`（effective）；`_write_survivor_output` 之 `config_hash`／`ic_method`／`label_return_type` 取 `self._current_config`；測試 `test_provenance_uses_effective_config`（override `methods=["kendall"]`／`return_type="log"` ⇒ provenance 反映）。

### N3 — 收斂 sentinel（composer／grok）：可進 B5；A1-10 成立
**引用**: COMPOSER-R21-P3-00, GROK-R21-P3-00
**處置＝接受（記錄）**：段 B 十二問兩家獨立重判可接受（含 A1-10 非重新凍結換綠、`_require_marginal_section` fail-loud、③／⑭／⑯ 前提偏差之處置誠實）；與 N1／N2 不衝突。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R21-P1-01
**斷言**: `metadata.survivor_output` 只存在於回傳中的 report，未寫入同次落盤的 `ic_report_*.json`，違反報告鏡像與互指契約。
**碼證**: `ic_filter_orchestrator.py:4049` 先呼叫 `save_report`，`:4062-4074` 才注入 survivor object；`ic_reporter.py:833-837` 立即 JSON dump。VERIFY `venv/bin/python -c ...` → `IN_MEMORY_SURVIVOR True`, `DISK_SURVIVOR False`。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5;momentum/Analysis/ic_reporter.py#73006e6bb658
[P1] 信心度=10/10；下游只讀 persisted report 時拿不到 survivor path/sha/status。應在 survivor metadata 注入後再保存 report，或等價保證落盤 JSON 含五鍵。
## CODEX-R21-P1-02
**斷言**: `config_override` 改變 IC method 時，倖存者 provenance 的 `ic_method` 仍取建構時基礎 config，非本次 effective config。
**碼證**: `analyze()` 的 effective `config` 來自 `:4303-4310` override merge；`_write_survivor_output:4156` 卻讀 `self._config.ic_calculation.methods[0]`。VERIFY override `{"ic_calculation":{"methods":["kendall"]}}` → `OVERRIDE_METHOD spearman`，而 `OVERRIDE_CONFIG_HASH True`。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5;momentum/Analysis/ic_config_schema.py#d7b736fce3a5
[P1] 信心度=10/10；結果的 provenance 會誤導重現／消費端，且同型 `label_return_type` 也使用基礎 config。將 effective config 顯式傳到 persist 或保存當次 config，再取規定欄位。
## COMPOSER-R21-P3-00

**斷言**: 本輪對 commits f6b8d881→ab53c24e 段 A–E 與段 B 十二項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `pytest test_gap2_stage6b_wiring.py test_gap2_survivor_persist.py -q` → 20 passed rc=0；`scripts/gap2_freeze_golden.py --check` → CHECK PASS canonical_sha=163c4cecb100…；`bash scripts/ic_wiring_check.sh` → R3(7) 全綠；`bash scripts/mutation_probe_check.sh` 三檔 → PASS（4 mutation）；段 D 重算：status=ok/fit_scope=train/survivors=2/n_regressions=4/oos=(True,"oos")/n_samples_total=1696/row_identity 兩 hash 不同；③′ degraded_full_sample+(False,"full_sample_research_only")；探針 receipt 七條 RED+GREEN；A1-10 `gap2_canonical_sha` L57–61 scope_id 正規化 + pre 未動 summary_table/filter_log。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5；scripts/gap2_freeze_golden.py#a3e234e4fc75；momentum/Analysis/survivor_contract.py#736d8a8cf2a5；momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

本輪核對依據：Task 4.0–4.3 逐步對照 orchestrator／reporter／survivor_contract／golden 腳本與測試；段 B 十二問獨立重判（A1-10 正規化語意、fail-loud 設計、錯誤分類、provenance 映射、n_samples 對帳、記憶化 key 區分、測試 skip 實跑）；mutation 探針 seam 與 B4 receipt；registry G2-R1/R2/R3/R5 觸發條件未滿足。B11 bench 標 slow 為建議項，非 B4 阻擋。

---

## GROK-R21-P3-00

**斷言**: 本輪對 commits `f6b8d881`→`d7d00e0b`→`ab53c24e`（GAP-2 B4 Task 4.0–4.3）段 A–E（含段 B 十二項實作期決定，優先 A1-10）逐項核對後無 finding。

**碼證**: `venv/bin/python -m pytest …test_gap2_stage6b_wiring.py …test_gap2_survivor_persist.py …test_gap2_golden.py …test_ichc_contract_sync.py …test_ichc_wiring_check.py …test_ic_persist_redirect_unit.py -q` → 71 passed rc=0；`venv/bin/python scripts/gap2_freeze_golden.py --check` → CHECK PASS（canonical_sha=163c4cec…；config_hash pre≠live 只記錄）；`bash scripts/mutation_probe_check.sh <三檔>` → PASS；`bash scripts/ic_wiring_check.sh` → R3 7 sections 全綠；B4 probe receipt `20260819T002456Z` 七條 RED＋RESTORED（首版 `20260819T000902Z` V-14 未紅→`_require_marginal_section` fail-loud）；段 D 重算 status=ok／fit_scope=train／survivors=2／n_regressions=4／root ok_oos→(True,oos)；③′ fit_scope=train 但 (False,full_sample_research_only)；倖存者 24 鍵／n_samples_total=1696／row_identity 兩 hash 不同；③ 實跑 PASSED 走 ok 未 skip；A1-10：summary_table／filter_log／config_hash／canonical_sha_legacy 跨 freeze 提交未變；G2-R1..R5 觸發未成立。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5；scripts/gap2_freeze_golden.py#a3e234e4fc75；handoffs/run_receipts/gap2_golden_pre.json#cab3bc9959a2；handoffs/run_receipts/20260819T002456Z-gap2-B4-probe.log#94e981820f50；tests/momentum/Analysis/test_gap2_stage6b_wiring.py#247a78007dc5；tests/momentum/Analysis/test_gap2_survivor_persist.py#0e1b655adf91；tests/momentum/Analysis/test_gap2_golden.py#daae274a557b；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#76ab7cb4d0f7；docs/IC_QUANT_GAP_REGISTRY.md#a119d3b21771；handoffs/20260819-gap2-b4-review-BRIEF.md#65c1e409f93e

核對依據：Task 4.0–4.3／A1-1..A1-10 對照源碼與測試；段 B 十二問獨立重判（B-1 含 git 三版 pre 不變項＋live config_hash 漂移仍 CHECK PASS）；段 D 真實 fixture 重算；探針以 receipt 為準（互斥未並行重跑）；registry 四殘留觸發未成立。未發現需修補後才能進 B5 之 B4 缺陷。

---


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: composer APPROVED 2026-08-19 sha256:969664ed8f7e400a619974c58d0bf9d949251b76b204b556de9485913d8971a8 task:20260819-GAP2-B4-STAMP-R22
RECONCILE-STAMP: codex BLOCKED 2026-08-19 sha256:969664ed8f7e400a619974c58d0bf9d949251b76b204b556de9485913d8971a8 task:20260819-GAP2-B4-STAMP-R22
RECONCILE-STAMP: grok APPROVED 2026-08-19 sha256:969664ed8f7e400a619974c58d0bf9d949251b76b204b556de9485913d8971a8 task:20260819-GAP2-B4-STAMP-R22
RECONCILE-STAMP: codex APPROVED 2026-08-19 sha256:969664ed8f7e400a619974c58d0bf9d949251b76b204b556de9485913d8971a8 task:20260819-GAP2-B4-STAMP-R23
