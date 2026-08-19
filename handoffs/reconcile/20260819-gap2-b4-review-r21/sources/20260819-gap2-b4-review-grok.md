# GAP-2 B4 實作 code review（R21）— GROK

**task-id**: `20260819-GAP2-B4-REVIEW-R21`｜**family**: grok｜**輪次**: R21  
**brief**: `handoffs/20260819-gap2-b4-review-BRIEF.md`  
**審查標的**: commits `f6b8d881` → `d7d00e0b` → `ab53c24e`（Task 4.0／A1-10／Task 4.1–4.3）  
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit／push／禁就地改檔實驗**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → **71 passed** rc=0（~692s，含 bench）
- `venv/bin/python scripts/gap2_freeze_golden.py --check` → **CHECK PASS** rc=0（`canonical_sha=163c4cec…`；兩 sidefx 目錄相等；`config_hash` pre=`9faf5345…` live=`0a42a198…` 只記錄）
- `bash scripts/mutation_probe_check.sh <三新測試檔>` → **PASS**（4 mutation 真跑）rc=0
- `bash scripts/ic_wiring_check.sh` → **R1a(24)/R1b(16)/R2(11)/R3(7 sections)** 全綠 rc=0
- 探針 B4：讀 receipt `handoffs/run_receipts/20260819T002456Z-gap2-B4-probe.log` → 七條 RED＋RESTORED GREEN；對照首版 `20260819T000902Z` V-14 未轉紅
- 段 D 本機重算（真實 fixture `_run()`）：見段 D 表；③ `test_forced_full_sample_fallback` 本輪 **PASSED（ok 分支，未 skip）**

---

## Verdict：可進 B5

Task 4.0–4.3 主路徑（兩插入點／fallback 旗標／root OOS 注入／persist 五鍵／golden／B4 探針）**符合**契約；段 B 十二項實作期決定經獨立攻擊後**均可接受**（B-1 A1-10 **非**重新凍結換綠；B-11 bench 嵌 golden 為觀測成本，非正確性缺陷）；段 E 四條殘留觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `GROK-R21-P3-00`）。

---

## 段 A — 契約符合度（Task 4.0／4.1／4.2／4.3）

| 要點 | 結論 | 碼證 |
|------|------|------|
| **兩插入點** analyze／refilter stage6→stage7 | **符合** | `ic_filter_orchestrator.py` ~L1068–1077／~L1798–1806 |
| **`_in_fallback_rerun` try/finally** | **符合** | L1138–1154 設 True；finally 還原 False；`_resolve_stage6b_fit_scope` 唯讀此旗標 |
| **`fit_scope` 不由 masks 推** | **符合** | `_resolve_stage6b_fit_scope`：fallback⇒`full_sample`；無 split⇒None；否則 `train` |
| **oos 欄 None 佔位＋`_inject_root_oos` 唯一注入** | **符合** | `_stage6b` 回傳後 A1-3；`_stage7_report` L3496＋fallback wrapper L1171 重注入 |
| **xsec 禁呼叫計算** | **符合** | `analyze_cross_sectional` 寫 N/A 節、spy `calls==[]`（測試⑯） |
| **契約增鍵同 commit／reason 經 loader** | **符合** | `ic_report_contract` 只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；`_survivor_reason`／`_marginal_status_object` 成員檢查 |
| **persist 顯式 kwargs；`_ic_cache` 只在 persist 後** | **符合** | `_persist_outputs` kwargs；`_ic_cache` 於 L3532+ 組裝；cold-call ⑧／mutation |
| **倖存者檔同 output_dir；A1-6／A1-1** | **符合** | `_write_survivor_output` 沿 `report_json_path.parent`；`write_failed` exact；`persist_suppressed` 五鍵 |
| **Task 4.0／4.3 golden＋探針** | **符合** | `--check` PASS；B4 七條 receipt；bench receipt `n_regressions=600==spy` |

---

## 段 B — 實作期決定複核（十二項；優先攻 B-1）

| # | 議題 | 結論 |
|---|------|------|
| **B1 A1-10** | **接受（非重新凍結換綠）**。(a) `summary_table`／`filter_log`／`config_hash`／`canonical_sha_legacy` 跨 `f6→d7→ab53` **一字未動**；僅 scrub 定義擴至兩處 `scope_id`（`selection_scope`＋`significance`，皆嵌 `config_hash`）導致 `canonical_sha` 重算——結構性碰撞處置，非行為漂移後改 baseline 換綠。legacy=`55101dbf…` 可稽核。(b) 正規化後失去對 scope_id 內 hash 段之偵測屬誠實邊界；**行為不變主證**＝`split_label` 段＋stage5／stage6 `filter_log` exact＋`summary_table` 1e-12 逐鍵仍在；本輪 `--check` live canonical==pre 且 live `config_hash` 已變（`9faf→0a42`）卻仍 PASS，反證主證足夠。(c) 排除 `marginal_ic` 出 `_hash_config` 會靜默改既有 hash 語意——否決合理；正規化已知嵌入點較誠實。 |
| **B2 `_require_marginal_section`** | **接受**。`None`⇒disabled；裸 `{}`／非 dict／缺 status⇒`ValueError`。首版靜默升級使 V-14 未紅（receipt `20260819T000902Z`）；改後 `20260819T002456Z` V-14 RED——fail-loud 正確。 |
| **B3 錯誤分類** | **接受**。`ContractValidationError` 於 try 外上拋（程式錯）；僅 IO⇒`write_failed` exact（A1-6）。吞成 write_failed 會掩蓋組裝 bug。 |
| **B4 provenance** | **接受（對齊 A1-9）**。`fit_mode`＝`report_meta.fit_mode` 原值（`train_mask` 等）；`config_hash`＝入口 `_hash_config`；features 檔 chunked sha256（py3.9）；labels `to_numpy(float).tobytes()`；`ic_method`＝`methods[0]`；`label_horizon`＝`effective_horizon`／null。 |
| **B5 `n_samples_total` fallback** | **接受**。`fit_scope=full_sample`⇒`≥max(n_train,n_test)`（A1-9）；holdout 仍 `≥n_train+n_test`。 |
| **B6 label None／block_len／removed** | **接受**。`label is None`⇒`insufficient_test_rows`（契約無 `no_label`，借用既有字面）；`block_len=max(horizon,ceil(n_test^(1/3)),1)`；`include_removed_candidates=False⇒extra=[]`。 |
| **B7 具名 preset** | **接受（不強制如 fdr）**。缺 `stage_overrides` 沿 schema 預設 `enabled=True`；fdr 強制 ON 是統計預設義務，邊際 IC 為可關成本級 stage。B5 三 preset 送出後等價；關斷由 override 路徑負責。 |
| **B8 deep cache＋refilter** | **接受**。deep key 含 `event_identity`；refilter 沿 `_ic_cache`（同 request）正確；跨 request 換 identity 已測。 |
| **B9 `normal_scores` 記憶化** | **接受（無值差異）**。鍵=`(col_idx, packbits(rows_mask))`；不同候選因 `finite_rows` 依 `[f]+S` 而異 ⇒ 不同 key；同 key＝同輸入同輸出。NaN 列集差異不會串味。 |
| **B10 測試前提偏差** | **接受**。③ 放寬門檻後本輪走 **ok 分支（1 survivor，未 skip）**；OOS 注入另由 ③′ 覆蓋；⑭ persist 層驗同一入口；⑯ 沿既有 xsec MultiIndex 慣例。換 BTCUSDT fixture 非必要。 |
| **B11 bench** | **可接受（觀測成本）**。`n_regressions=600==spy`、`max_design_cols=199`、超預算 0／400；receipt wall≈94s／RSS≈613MB（觀測）。嵌 `test_gap2_golden` 使 gate ~+2.5 分——DX 成本，非正確性缺陷；標 slow／獨立腳本屬後續優化，不擋 B5。 |
| **B12 契約只動 4 行** | **接受**。避免 json.dumps 重排；orchestrator 多處 `"marginal_ic"` 字面滿足 `test_r6_wider_contract_nodes_consistent`。 |

---

## 段 C — 測試品質

- **探針 B4（讀 receipt，未並行重跑）**：`20260819T002456Z` 七條 V-13／14／15／16／22／23／24 皆 RED＋RESTORED GREEN；首版 `20260819T000902Z` **V-14 未轉紅**與 B-2 設計改對齊。
- **`test_mutation_fit_scope_derived_oos_breaks_root_oracle`**：**真 seam**——patch stage6b 依 `fit_scope` 填 OOS＋`_inject_root_oos` no-op ⇒ ③′ 期望 `oos_guarantees is False` 紅。
- **`test_mutation_persist_reads_ic_cache_breaks_cold_call`**：**真 seam**——mutant 讀 `_ic_cache["event_identity"]` 於 cold（`_ic_cache is None`）⇒ TypeError 轉 AssertionError。
- **`_diff_summary` 1e-12**：`gap2_freeze_golden.py` 數值鍵 abs≤1e-12；非數值 exact。
- **③ skip 掩蓋**：本輪實跑 `test_forced_full_sample_fallback` → **PASSED**，status=`ok`／`fit_scope=full_sample`／`oos_guarantees=False`（**ok 分支，未觸發 skip**）。skip 僅為「放寬後仍 0 survivors」之逃生；③′ 仍鎖 root≠fit_scope 之 OOS 注入。
- **mutation_probe_check**：三檔 PASS（4 探針真跑）。

---

## 段 D — 正確性（本輪重算）

| 項目 | 本輪實測 | 判定 |
|------|----------|------|
| 預設 `marginal_ic` | `status=ok`，`fit_scope=train`，survivors=2，`n_regressions=4`，removed=0 | ✓ |
| root 注入 | `analysis_status=ok_oos` ⇒ `(oos_guarantees=True, pass_class="oos")`；composite 同 | ✓ |
| ③′ 事件 fallback | `fit_scope=train` 但 root=`degraded_full_sample` ⇒ `(False, "full_sample_research_only")`；`event_filter.fallback=True` | ✓ |
| 倖存者檔 | 頂層 **24 鍵**（＝契約 `survivor_file_keys.keys`）；過 `validate_survivor_output` | ✓ |
| `row_identity` | train=`93e763bdfc28140d…` ≠ test=`1c52c2143a8e9270…` | ✓ |
| `n_samples_total` | **1696**（＝`metadata.n_samples`；fixture 1696 bars） | ✓ |

---

## 段 E — registry「GAP-2 待補完」

| # | 觸發成立？ | 理由 |
|---|------------|------|
| G2-R1 | **否** | 倖存者檔落地＝橋之**輸入契約**；未接 ML `selected_features`；user-ruling 仍有效 |
| G2-R2 | **否** | 邊際 IC 只報不選；未改倖存者集合／無二次選擇政策 |
| G2-R3 | **否** | xsec 仍 `not_applicable:cross_sectional_mode`；觸發＝registry #4 完工（未） |
| G2-R5 | **否** | 仍 `independent_oos_validation=false`＋`selection_sample=test`；主線切分未升級 |

預期：無。本批未使任一觸發成立。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 本輪 |
|------------|------|
| pytest 71 passed（含 bench） | **覆核** 71 passed rc=0 |
| `gap2_freeze_golden.py --check` PASS | **覆核** CHECK PASS；config_hash 只記錄 |
| wiring／mpc／B4 探針 | **覆核** wiring 全綠；mpc PASS；探針讀最終 receipt＋首版 V-14 對照 |
| A1-10＝結構性碰撞非換綠 | **逐項攻擊後接受**；見 B-1（含 ab53 第二次 scrub 擴至 `significance.scope_id`） |
| 段 B 其餘十一項合理 | **逐項攻擊後接受** |
| ③／⑭／⑯ 處置誠實 | **覆核** ③ 本輪 ok 未 skip；⑭／⑯ 註解與碼一致 |

---

## Findings（canonical）

## GROK-R21-P3-00

**斷言**: 本輪對 commits `f6b8d881`→`d7d00e0b`→`ab53c24e`（GAP-2 B4 Task 4.0–4.3）段 A–E（含段 B 十二項實作期決定，優先 A1-10）逐項核對後無 finding。

**碼證**: `venv/bin/python -m pytest …test_gap2_stage6b_wiring.py …test_gap2_survivor_persist.py …test_gap2_golden.py …test_ichc_contract_sync.py …test_ichc_wiring_check.py …test_ic_persist_redirect_unit.py -q` → 71 passed rc=0；`venv/bin/python scripts/gap2_freeze_golden.py --check` → CHECK PASS（canonical_sha=163c4cec…；config_hash pre≠live 只記錄）；`bash scripts/mutation_probe_check.sh <三檔>` → PASS；`bash scripts/ic_wiring_check.sh` → R3 7 sections 全綠；B4 probe receipt `20260819T002456Z` 七條 RED＋RESTORED（首版 `20260819T000902Z` V-14 未紅→`_require_marginal_section` fail-loud）；段 D 重算 status=ok／fit_scope=train／survivors=2／n_regressions=4／root ok_oos→(True,oos)；③′ fit_scope=train 但 (False,full_sample_research_only)；倖存者 24 鍵／n_samples_total=1696／row_identity 兩 hash 不同；③ 實跑 PASSED 走 ok 未 skip；A1-10：summary_table／filter_log／config_hash／canonical_sha_legacy 跨 freeze 提交未變；G2-R1..R5 觸發未成立。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5；scripts/gap2_freeze_golden.py#a3e234e4fc75；handoffs/run_receipts/gap2_golden_pre.json#cab3bc9959a2；handoffs/run_receipts/20260819T002456Z-gap2-B4-probe.log#94e981820f50；tests/momentum/Analysis/test_gap2_stage6b_wiring.py#247a78007dc5；tests/momentum/Analysis/test_gap2_survivor_persist.py#0e1b655adf91；tests/momentum/Analysis/test_gap2_golden.py#daae274a557b；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#76ab7cb4d0f7；docs/IC_QUANT_GAP_REGISTRY.md#a119d3b21771；handoffs/20260819-gap2-b4-review-BRIEF.md#65c1e409f93e

核對依據：Task 4.0–4.3／A1-1..A1-10 對照源碼與測試；段 B 十二問獨立重判（B-1 含 git 三版 pre 不變項＋live config_hash 漂移仍 CHECK PASS）；段 D 真實 fixture 重算；探針以 receipt 為準（互斥未並行重跑）；registry 四殘留觸發未成立。未發現需修補後才能進 B5 之 B4 缺陷。

---

## §1 必查（11 類摘要）

1. 矛盾：無（A1-3／A1-6／A1-9／A1-10 與實作對齊）。  
2. 漏項：B4 scope 內無（B5 前端／toggle 屬計劃）。  
3. 不可測：pytest 71＋七 mutation＋golden＋wiring R3。  
4. quant：OOS 由 root 注入、fit_scope 不推 OOS、xsec N/A——測試＋探針鎖住。  
5–8. 過度工程／OOM（計數 gate≤600）／cache（event_identity）／API（py3.9 chunked hash）：無阻擋問題。  
9. 測試：真 seam mutation；③ 本輪未 skip；無假綠弱化斷言。  
10. Agent 可執行：檔案／函式／驗證明確。  
11. 短命工：無（B5 消費本批報告節／toggle 路徑，不刪本批交付物）。

STATUS: DONE
