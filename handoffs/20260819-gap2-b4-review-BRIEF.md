# GAP-2 B4 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap2-b4-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–E 之敘述是「請你查證的問句與我的待攻決定」，不是主委的 operational 結論；實際結論在委員產出與收斂檔 `handoffs/reconcile/20260819-gap2-b4-review-r21/synth.md`。
> 🔴 **禁就地改任何 repo 檔做實驗**（in-memory monkeypatch only）；探針 `--batch B4` 約 20 分鐘且互斥（rc=3 ⇒ 讀 receipt）；`test_gap2_golden.py` 含 bench（~2.5 分鐘）。

brief-kind: review

## 審查標的（commits `f6b8d881`（Task 4.0）→ `d7d00e0b`（A1-10 補正）→ `ab53c24e`（Task 4.1–4.3）；`git diff 038fd10b ab53c24e --stat`）
- 既有檔改動（**白名單 §C＋A1-4..A1-5 內**）：`momentum/Analysis/ic_filter_orchestrator.py`（imports／`STAGE_OVERRIDE_PATHS["marginal_ic"]`／`__init__` 五欄／`analyze` 入口存路徑＋config hash／`_stage3_event_filter` 事件身分／`_run_full_sample_fallback` 旗標＋重注入＋persist kwargs／兩插入點／`analyze_cross_sectional` N/A 節／`_stage7_report` 新節＋root 注入＋persist kwargs＋suppress 五鍵＋cache snapshot／deep cache key 含 event_identity／`_apply_tier_config` 具名 preset 消費／新 helper `_marginal_status_object`／`_require_marginal_section`／`_survivor_reason`／`_resolve_stage6b_fit_scope`／`_inject_root_oos`／`_stage6b_marginal_ic`／`_persist_outputs` kwargs／`_write_survivor_output`）；`ic_config_schema.py`（`MarginalICConfig`＋`ICConfig.marginal_ic`）；`contracts/ic_report_contract.json`（**只**加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；4 行）；`ic_reporter.py`（`generate_json_report` 條件透傳＋`save_survivor_output`）；`scripts/ic_wiring_check.py`（`REPORT_SECTIONS` 改讀契約 ⇒ R3 7 節）；`marginal_ic.py`（**只**加 `normal_scores` 記憶化 `_z()`——純效能，值不變）；`contracts/ic_survivor_contract.json`（A1-1：`reasons.survivor_output` 增值 `persist_suppressed`）；`survivor_contract.py`（`n_samples_total` 對帳於 `fit_scope=full_sample` 改 `≥max`）
- 新檔：`scripts/gap2_freeze_golden.py`＋pre 檔 `handoffs/run_receipts/gap2_golden_pre.json`；`tests/momentum/Analysis/test_gap2_stage6b_wiring.py`（13）／`test_gap2_survivor_persist.py`（7）／`test_gap2_golden.py`（5，含 bench）；探針 B4 case V-13／14／15／16／22／23／24
- 契約來源：TODO（FROZEN）Task 4.0–4.3；SPEC §G／§V；AMENDMENTS A1-1..**A1-10**

## 本輪任務（五段皆必答）
**段 A — 契約符合度**：Task 4.0／4.1／4.2／4.3 實作要點／不可做／驗證逐條；特別查：兩插入點（`analyze` :stage6 後／`refilter`）＋`_in_fallback_rerun` try/finally；`_stage6b` 不由 masks 推 `fit_scope`、`oos` 欄 None 佔位、`_inject_root_oos` 唯一注入（含 fallback wrapper 重注入）；xsec 禁呼叫計算；契約增鍵與 orchestrator 字面同 commit；reason 字面經 `load_survivor_contract()`；persist 顯式 kwargs 不讀 `_ic_cache`（cold-call 測試⑧）；`_ic_cache` 只在 persist 後承接；倖存者檔沿 report json 同 output_dir（hermetic ④）；A1-6 `write_failed` exact；A1-1 `persist_suppressed` 五鍵。

**段 B — 🔴 實作期決定（請攻；本批多且重）**：
1. **A1-10（最重要）**：`config_hash=md5(config.model_dump())` ⇒ 加 `ICConfig.marginal_ic` 後 `metadata.selection_scope.scope_id`／`metadata.significance.scope_id`（`hash:label`）必變 ⇒ §G-1 canonical_sha 在行為不變下必不等。我把 `gap2_canonical_sha` 對兩處 `scope_id` 正規化為 label 段，pre 檔以 **git stash 回到改前程式碼**重算（`git diff f6b8d881 d7d00e0b -- handoffs/run_receipts/gap2_golden_pre.json`＋本批 diff：`summary_table`／`filter_log`／`config_hash`／`canonical_sha_legacy` 一字未動）。**請答**：(a) 這算不算「重新凍結換綠」？(b) 正規化後 §G-1 失去對 config_hash 段的偵測，`split_label` 段＋stage5／stage6 filter_log＋summary_table exact 是否仍足證「行為不變」？(c) 有無更好的方案（例：`_hash_config` 排除 `marginal_ic`——我否決：動既有 hash 語意）？
2. **`_require_marginal_section`**：`None` ⇒ disabled 物件；裸 `{}`／非 dict／缺 status ⇒ `ValueError`（fail-loud）。首版曾把 `{}` 靜默升級成 disabled 物件 ⇒ 探針 V-14 抓不到（receipt `20260819T000902Z` V-14 未轉紅）⇒ 改此設計。可接受？
3. **`_write_survivor_output` 之錯誤分類**：`build_survivor_output`／`validate_survivor_output` 之 `ContractValidationError` **上拋**（程式錯，fail-closed）；只有寫檔 IO 例外 ⇒ `computation_failed:write_failed`（例外只進 log）。TODO 4.2 只寫「寫檔失敗 ⇒ write_failed 不上拋」——契約組裝錯誤上拋是否正確？（另一選項：也吞成 write_failed——我判那會掩蓋 bug。）
4. **`provenance.fit_mode`**＝`report_meta.fit_mode` 原值（`train_mask`）；`config_hash`＝`self._current_config_hash`（analyze／refilter 入口 `_hash_config(config)`）；`features_source_hash`＝檔案 sha256（chunked；py3.9 無 `file_digest`）、路徑缺 ⇒ `""`；`labels_content_hash`＝`sha256(label.to_numpy(float).tobytes())`；`ic_method`＝`config.ic_calculation.methods[0]`；`label_horizon`＝`split_context.effective_horizon`（無 split ⇒ null）。合理？
5. **`n_samples_total` 對帳於 fallback**：兩 mask 全 True ⇒ `n_train+n_test=2n` ⇒ 規則改為 `fit_scope=full_sample ⇒ ≥max(n_train,n_test)`（B3 M4 之補正；A1-9 更新）。
6. **`_stage6b`：`label_series is None ⇒ not_computed:insufficient_test_rows`**（借用 reason；契約無 `no_label`）；`block_len=max(effective_horizon, ceil(n_test^(1/3)), 1)`；`include_removed_candidates=False ⇒ extra=[]`。
7. **`_apply_tier_config` 具名 preset**：`marginal_ic` 出現在 `stage_overrides` 才映射，缺則沿 config 預設（**不像 fdr 強制 True**）——B5 三 preset 送出後等價；是否應同 fdr 強制？
8. **deep cache key 加 `event_identity`**（TODO 4.1 步驟 3「deep／refilter cache key 含 event_identity 之 hash」）；refilter 無獨立 cache key（沿 `_ic_cache`）——我判 refilter 同 request 沿用即正確。是否足夠？
9. **`normal_scores` 記憶化**（`_z()`；鍵＝(欄, packbits(列遮罩))）：bench 6 分鐘 → ~1.5 分鐘；B1 34 條測試不變、V-2 目標行不變。是否引入任何值差異？（同輸入同輸出；請攻 NaN 列不同候選之 key 區分）。
10. **測試前提偏差（TODO 之前提被 fixture 推翻）**：③ 預設門檻下 fixture 於 full-sample fallback **0 survivors** ⇒ 測試放寬門檻、仍無則 `skip`（OOS 注入斷言由 ③′ 事件 fallback 覆蓋）；⑭ 缺 symbol 時 pipeline 無法取 label ⇒ 於 persist 層驗（同一 `_persist_outputs` 入口）；⑯ xsec 用既有合成 MultiIndex 慣例。是否有更誠實的做法（例：③ 換 BTCUSDT fixture）？
11. **bench**：`n_regressions=600 == fit_projection spy`、`max_design_cols=199`、超預算 spy 0／400；wall 82.6s、RSS 686MB（觀測）；bench 在 `test_gap2_golden.py` 內每次 gate 跑 ~2.5 分鐘——是否應標記為 slow／獨立 receipt 腳本？
12. **`ic_report_contract.json` 只動 4 行**（避免 json.dumps 重排）；`test_r6_wider_contract_nodes_consistent` 對 `"marginal_ic"` 字面之要求由 orchestrator 多處滿足。

**段 C — 測試品質**：探針 B4 七條（receipt `handoffs/run_receipts/20260819T002456Z-gap2-B4-probe.log`；V-14 首版未紅 → 設計改後紅）——請讀 receipt 或（不並行時）重跑；`test_mutation_fit_scope_derived_oos_breaks_root_oracle`（重現 R2 bug：patch `_inject_root_oos` 為 no-op＋stage6b 依 fit_scope 填 OOS ⇒ ③′ 紅）與 `test_mutation_persist_reads_ic_cache_breaks_cold_call` 是否為真 seam；`_diff_summary` 1e-12 逐鍵；有無 skip 掩蓋（③ 之 skip 條件是否會在本 fixture 觸發——請實跑並回報是走 ok 分支還是 skip）。

**段 D — 正確性**：真實 fixture：`marginal_ic.status=ok`、`fit_scope=train`、2 survivors、`n_regressions=4`、root `ok_oos` 注入 `(True,"oos")`；③′ 事件 fallback：`fit_scope=train` 但 `(False,"full_sample_research_only")`；倖存者檔 24 鍵過 validator、`row_identity` 兩 hash 不同、`n_samples_total=1696`。請重算並貼值。

**段 E — registry「GAP-2 待補完」四條之觸發是否已成立**：
| # | 待補完項 | 為何現在不做 | 觸發條件 |
|---|---|---|---|
| G2-R1 | IC→ML 橋本體 | user-ruling: 2026-08-18 橋本體 blocked-by ML 層 | ML 層重寫或宣告穩定 |
| G2-R2 | 以邊際 IC 做 forward-stepwise 選擇 | needs-research: post-FDR 二次選擇多重比較政策無認可方法 | 委員會定出政策 |
| G2-R3 | xsec 路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC | #4 完工 |
| G2-R5 | nested／frozen final test | blocked-by: IC 主路徑切分 holdout-only | 主線切分升級 |
請答：本批（xsec N/A 節、倖存者檔落地）有無使觸發成立？（預期：無；G2-R3 之「轉 ok」條件為 #4 完工。）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1／§3 與 canonical 四欄。ID＝`## <FAMILY>-R21-P<0-3>-<NN>`（**本輪＝R21**）。零 findings 用 sentinel `## <FAMILY>-R21-P3-00`（body 須實質）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁 commit／push、禁就地改檔實驗**；只產你自己的 review 檔。venv **Python 3.9.6**。使用者裁決不受理重議。
- 可跑測試（`venv/bin/python -m pytest …`）；重跑 golden `--check` 約 25 秒；探針 B4 約 20 分鐘且互斥（建議讀 receipt）。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → 71 passed（含 bench ~2.5 分鐘）（Claude 實跑 2026-08-19）
fact-verified: `venv/bin/python scripts/gap2_freeze_golden.py --check` → CHECK PASS（改後 canonical_sha == pre；兩 sidefx 目錄相等；`config_hash` 只記錄）
fact-verified: `bash scripts/ic_wiring_check.sh` → R1a(24)/R1b(16)/R2(11)/R3(7 sections) 全綠；`bash scripts/mutation_probe_check.sh <三新測試檔>` → PASS
fact-verified: `bash scripts/gap2_mutation_probe.sh --batch B4` → rc=0 七條 RED（receipt `handoffs/run_receipts/20260819T002456Z-gap2-B4-probe.log`）；B1／B2／B3 探針重跑仍 rc=0
assumed: A1-10 之正規化為結構性碰撞之正確處置、非重新凍結換綠 ← 請攻（段 B-1）
assumed: 段 B 其餘十一項為契約內合理選擇 ← 請攻
assumed: 三個測試前提偏差（③／⑭／⑯）之處置誠實且不降低保護 ← 請攻

## Time-box
優先序＝段 B-1（A1-10）＞ 段 B 其餘 ＞ 段 D ＞ 段 C ＞ 段 A ＞ 段 E。**不受理**：使用者裁決、TODO 已 Frozen 之契約本身（要改走延伸檔提案）、B5 未實作部分、治理機制。

## 產出
Verdict（可進 B5／需修補後進 B5／有根本缺陷需重作）＋段 A–E 結論＋canonical findings。收尾清 /tmp workdir（保留 claude-501）。
