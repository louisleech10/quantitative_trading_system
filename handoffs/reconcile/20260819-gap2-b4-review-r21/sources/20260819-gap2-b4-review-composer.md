# GAP-2 B4 實作 code review（R21）— COMPOSER

**task-id**: `20260819-GAP2-B4-REVIEW-R21` | **family**: composer | **brief**: `handoffs/20260819-gap2-b4-review-BRIEF.md`
**審查標的**: commits `f6b8d881`（Task 4.0）→ `d7d00e0b`（A1-10）→ `ab53c24e`（Task 4.1–4.3）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py -q` → **20 passed** rc=0（~172s）
- `venv/bin/python scripts/gap2_freeze_golden.py --check` → **CHECK PASS** canonical_sha=163c4cecb100…；config_hash 差異僅記錄（A1-10）
- `bash scripts/ic_wiring_check.sh` → **R1a(24)/R1b(16)/R2(11)/R3(7 sections) 全綠** rc=0
- `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py` → **PASS**（4 mutation 真跑）
- `tests/momentum/Analysis/test_gap2_stage6b_wiring.py::test_forced_full_sample_fallback` → **PASSED**（走 **ok 分支**，非 skip；1 survivor、fit_scope=full_sample、OOS 注入 False）
- 段 D 重算（獨立腳本）：status=ok、fit_scope=train、survivors=2、n_regressions=4、analysis_status=ok_oos、oos=(True,"oos")；③′ fit_scope=train、(False,"full_sample_research_only")；payload 頂層 24 鍵、row_identity 兩 hash 不同、n_samples_total=1696
- 探針 B4：讀 receipt `handoffs/run_receipts/20260819T002456Z-gap2-B4-probe.log`（七條 RED+RESTORED GREEN；未重跑，互斥鎖）

---

## Verdict：可進 B5

段 A Task 4.0–4.3 契約符合度**逐條成立**；段 B 十二項實作期決定經獨立攻擊後**均可接受**（A1-10 正規化非換綠；③ 本 fixture 走 ok 分支）；段 C 探針／mutation seam 真；段 D 數值重算與 brief 一致；段 E registry 四條觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `COMPOSER-R21-P3-00`）。

---

## 段 A — 契約符合度（Task 4.0–4.3）

| 要點 | 結論 | 碼證 |
|------|------|------|
| **Task 4.0** golden 凍結／scrub | **符合** | `scripts/gap2_freeze_golden.py` L43–63 有序 scrub ①–⑤；`--check` 本輪 PASS |
| **Task 4.1** 兩插入點 | **符合** | `analyze` L1068–1077（stage6 後）；`refilter` L1798–1807（stage6 後）；`_in_fallback_rerun` try/finally L1138–1154 |
| **fit_scope 判定** | **符合** | `_resolve_stage6b_fit_scope` L3899–3905：fallback⇒full_sample；無 split⇒None；否則 train；**不由 masks 反推** |
| **OOS 注入** | **符合** | `_stage6b` docstring L3935；`_stage7_report` L3495–3496 + fallback wrapper L1171 重注入；`_inject_root_oos` L3907–3917 唯一注入點 |
| **xsec 禁計算** | **符合** | `analyze_cross_sectional` L1576 硬編 N/A 節；`test_xsec_marginal_ic_not_applicable` spy calls==[] |
| **契約增鍵** | **符合** | `ic_report_contract.json` diff 恰 4 行（`marginal_ic` section + `survivor_output_keys`）；`ic_wiring_check` R3=7 |
| **reason 字面** | **符合** | `_marginal_status_object`／`_survivor_reason` 經 `load_survivor_contract()`；AST 測試 ⑫ |
| **persist 顯式 kwargs** | **符合** | `_persist_outputs` L4062–4074 全顯式；`_ic_cache` 指派在 persist **之後** L3547–3549；cold-call 測試⑧ |
| **倖存者檔同 output_dir** | **符合** | `_write_survivor_output` L4162–4164；`test_file_exists_validates_names_and_sha` ④ hermetic |
| **A1-6 write_failed** | **符合** | L4166–4174 exact `"write_failed"`；測試 `test_four_shapes_five_keys` |
| **A1-1 persist_suppressed** | **符合** | `_stage7_report` suppress 分支 L3514–3520 五鍵恆寫 |

---

## 段 B — 實作期決定複核（十二項）

| # | 議題 | 結論 |
|---|------|------|
| **B1 A1-10** | **接受（非換綠）**。(a) pre 以 stash 回改前程式重算、正規化只剝 `scope_id` 之 config_hash 段；`summary_table`／`filter_log`／`canonical_sha_legacy` 未動 ⇒ 非行為變更後重凍結換綠。(b) `split_label` 段＋stage5/6 filter_log exact＋summary_table 1e-12 仍足證主路徑行為不變；`config_hash` 差異僅記錄。(c) 排除 `marginal_ic` 出 `_hash_config` 會改既有語意；正規化為結構性碰撞之最小處置。 |
| **B2 `_require_marginal_section`** | **接受**。`None`⇒disabled；裸 `{}`／非 dict／缺 status⇒`ValueError`；V-14 首版未紅已證 fail-loud 必要。 |
| **B3 錯誤分類** | **接受**。`build`／`validate` 在 IO try 外（L4137–4161）⇒ `ContractValidationError` 上拋；僅 `save_survivor_output` IO⇒`write_failed`。吞成 write_failed 會掩蓋組裝 bug。 |
| **B4 provenance 欄位** | **接受**。`fit_mode`＝`report_meta.fit_mode` 原值（`train_mask`）；`config_hash`＝入口 `_hash_config`；`features_source_hash` chunked sha256、缺路徑 `""`；`labels_content_hash` float bytes sha256；`ic_method`＝`methods[0]`；`label_horizon`＝`effective_horizon`（無 split⇒null）。 |
| **B5 n_samples_total fallback** | **接受**。`survivor_contract.py` L456–458：`fit_scope=full_sample`⇒`≥max(n_train,n_test)`；兩 mask 全 True 時 n_train+n_test=2n 之補正合理。 |
| **B6 label_series None** | **接受**。借用 `insufficient_test_rows`（契約無 `no_label`）；`block_len=max(horizon,ceil(n_test^(1/3)),1)`；`include_removed_candidates=False⇒extra=[]`（L3945）。 |
| **B7 tier preset marginal_ic** | **接受**。僅 `stage_overrides` 含 `marginal_ic` 才映射（L4378–4382）；不像 fdr 強制 True——marginal_ic schema 預設 enabled，B5 三 preset 送出後等價即可。 |
| **B8 deep cache event_identity** | **接受**。`_build_deep_cache_key` L2059–2060 含 `event_identity`；refilter 同 request 沿用 `_ic_cache`（L3548–3549）正確。 |
| **B9 normal_scores 記憶化** | **接受（無值差）**。鍵＝`(col, packbits(rows))`；`finite_rows` 先濾非有限列再呼叫 `_z`（L430–432）；同段同 mask 共用 cache；B1 34 條不變。 |
| **B10 測試前提偏差** | **接受（誠實）**。③ 本輪實跑走 **ok 分支**（1 survivor，非 skip）；skip 路徑仍由 ③′ 覆蓋 OOS 注入；⑭ persist 層驗 identity_missing（pipeline 缺 symbol 無法跑 analyze）；⑯ xsec 合成 MultiIndex 沿既有慣例。 |
| **B11 bench** | **建議（非阻擋）**。`test_gap2_golden.py` bench ~2.5min 每次 gate 跑偏重；可標 `@pytest.mark.slow` 或獨立 receipt 腳本——不構成 B4 缺陷。 |
| **B12 contract 4 行** | **確認**。`git diff f6b8d881 ab53c24e -- ic_report_contract.json` 恰 4 行增改。 |

---

## 段 C — 測試品質

- **探針 B4**：receipt `20260819T002456Z` 七條 V-13/14/15/16/22/23/24 各 RED+GREEN；V-14 設計改後轉紅。
- **mutation seam**：`test_mutation_fit_scope_derived_oos_breaks_root_oracle` 重現 R2 bug（patch `_inject_root_oos` no-op + fit_scope 推導 OOS）⇒ ③′ 紅；`test_mutation_persist_reads_ic_cache_breaks_cold_call` cold `_ic_cache is None` 下 mutant 讀 cache⇒TypeError 紅——**真 seam**。
- **`_diff_summary` 1e-12**：`gap2_freeze_golden.py` L102–109 + golden 測試。
- **skip 掩蓋**：③ 本 fixture **未觸發 skip**（放寬門檻後 status=ok、1 survivor）；skip 分支僅在仍 0 survivors 時觸發，由 ③′ 補 OOS 斷言覆蓋——**非廉價綠**。

---

## 段 D — 正確性（本輪重算）

| Oracle | 值 | 碼證 |
|--------|-----|------|
| marginal_ic | status=**ok**, fit_scope=**train**, survivors=**2**, n_regressions=**4** | 獨立腳本 + log `IC stage6b marginal_ic: … survivors=2 … n_regressions=4 fit_scope=train` |
| root OOS 注入 | analysis_status=**ok_oos**, oos_guarantees=**True**, pass_class=**oos** | `test_default_config_section_ok_and_root_oracle` |
| ③′ 事件 fallback | fit_scope=**train**, oos=**(False,"full_sample_research_only")**, analysis_status=**degraded_full_sample** | 獨立腳本 event_timestamps=3 |
| 倖存者檔 | 頂層 **24** 鍵、`validate_survivor_output` PASS | `test_file_exists_validates_names_and_sha` |
| row_identity | train=`93e763bdfc28140d…` ≠ test=`1c52c2143a8e9270…` | 獨立腳本 |
| n_samples_total | **1696**（== metadata.n_samples） | 獨立腳本 |

---

## 段 E — registry「GAP-2 待補完」

本批（stage6b 接線、倖存者檔落地、xsec N/A 節）**未觸發** G2-R1（ML 橋本體）、G2-R2（forward-stepwise）、G2-R3（xsec 邊際 IC 計算）、G2-R5（nested holdout）。G2-R3 之「轉 ok」條件仍為 registry #4 Pooled/Panel IC 完工——xsec 僅加 N/A 節、未實作計算。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| pytest 71 passed（含 bench） | fact-verified | wiring+persist 20 passed 覆核；bench 未單獨重跑（brief 已標） |
| golden --check PASS | fact-verified | **覆核 rc=0** |
| B4 探針 rc=0 七條 | fact-verified | 讀 receipt 20260819T002456Z（未重跑） |
| A1-10 正規化非換綠 | assumed→**verified** | 段 B1：pre stash 重算 + summary/filter 不變 + legacy sha 稽核 |
| 段 B 其餘十一項合理 | assumed→**verified** | 段 B 表逐項攻擊 |
| ③／⑭／⑯ 測試誠實 | assumed→**verified** | ③ 實跑 ok 分支；⑭ persist 層；⑯ spy 零呼叫 |

---

## Findings（canonical）

## COMPOSER-R21-P3-00

**斷言**: 本輪對 commits f6b8d881→ab53c24e 段 A–E 與段 B 十二項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `pytest test_gap2_stage6b_wiring.py test_gap2_survivor_persist.py -q` → 20 passed rc=0；`scripts/gap2_freeze_golden.py --check` → CHECK PASS canonical_sha=163c4cecb100…；`bash scripts/ic_wiring_check.sh` → R3(7) 全綠；`bash scripts/mutation_probe_check.sh` 三檔 → PASS（4 mutation）；段 D 重算：status=ok/fit_scope=train/survivors=2/n_regressions=4/oos=(True,"oos")/n_samples_total=1696/row_identity 兩 hash 不同；③′ degraded_full_sample+(False,"full_sample_research_only")；探針 receipt 七條 RED+GREEN；A1-10 `gap2_canonical_sha` L57–61 scope_id 正規化 + pre 未動 summary_table/filter_log。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#280e4c852cc5；scripts/gap2_freeze_golden.py#a3e234e4fc75；momentum/Analysis/survivor_contract.py#736d8a8cf2a5；momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

本輪核對依據：Task 4.0–4.3 逐步對照 orchestrator／reporter／survivor_contract／golden 腳本與測試；段 B 十二問獨立重判（A1-10 正規化語意、fail-loud 設計、錯誤分類、provenance 映射、n_samples 對帳、記憶化 key 區分、測試 skip 實跑）；mutation 探針 seam 與 B4 receipt；registry G2-R1/R2/R3/R5 觸發條件未滿足。B11 bench 標 slow 為建議項，非 B4 阻擋。

---

## §1 必查（11 類摘要）

1. 矛盾：無（SPEC/TODO/契約/實作一致）。2. 漏項：B4 scope 內無。3. 不可測：20+5 golden pytest＋7 mutation 探針＋golden sha。4. quant：OOS 由 root 注入、fit_scope 不由 masks 反推、full_sample 雙 mask 對帳——實作＋測試覆蓋。5–8. 過度工程／OOM／cache key 含 event_identity／API：無問題。9. 測試：mutation seam 真；③ 本 fixture 未 skip。10. Agent 可執行：函式／檔案精確。11. 短命工：無（Task 4.x 存活至 B5 preset）。

---

ASSUMPTIONS_VERIFIED: wiring+persist 20 passed；golden --check PASS；ic_wiring_check R3=7；mutation_probe_check PASS；段 D 數值重算；③ ok 分支非 skip；A1-10 正規化 + pre 欄位不變
TESTS_RUN: `pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py -q` 20 passed；`python scripts/gap2_freeze_golden.py --check` PASS；`bash scripts/ic_wiring_check.sh` rc=0；`bash scripts/mutation_probe_check.sh` 三檔 PASS；`pytest …::test_forced_full_sample_fallback` PASSED（ok 分支）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查只讀）

STATUS: DONE
