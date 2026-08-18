# GAP-2 B3 實作 code review（R18）— COMPOSER

**task-id**: `20260819-GAP2-B3-REVIEW-R18` | **family**: composer | **brief**: `handoffs/20260819-gap2-b3-review-BRIEF.md`
**審查標的**: commit `038fd10b`（Task 3.1：`survivor_contract.py` resolver／validator／`build_survivor_output`＋測試＋B3 探針）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → **35 passed** rc=0
- `venv/bin/python -m pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` → **5 passed** rc=0
- `bash scripts/gap2_mutation_probe.sh --batch B3` → **rc=0**；V-10／11／12／17b／19a／19b／19c／20 各 `RED ✓`＋`RESTORED GREEN ✓`（receipt `handoffs/run_receipts/20260818T231005Z-gap2-B3-probe.log`）
- `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → **PASS** rc=0

---

## Verdict：可進 B4

段 A Task 3.1 步驟 1–4／不可做／邊界／驗證 ①–⑱（⑬ 留 B4）**逐條符合**；段 B 十項實作期決定經獨立攻擊後**均可接受**（B4 接線須映射 `fit_mode`／傳 `full_index`，已於 TODO 4.1 明示）；段 C 探針八條本輪重跑全綠、seam 真；段 D 數值／hash 與契約一致；段 E registry 四條觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `COMPOSER-R18-P3-00`）。

---

## 段 A — 契約符合度（Task 3.1）

| 要點 | 結論 | 碼證 |
|------|------|------|
| **步驟 1** `resolve_ref` | **符合** | `survivor_contract.py` L140–159：檔缺／鍵路徑缺／非 list ⇒ `ContractValidationError`；測試 ⑧ |
| **步驟 2** `validate_survivor_output` | **符合** | L231–336：遞迴觸及各物件層 `_check_object`；枚舉／OOS 四欄互斥／`kind=event⇒event非null`／`feature_set_hash`／survivors 序列；測試 ②–⑥⑪⑫⑯⑰ |
| **步驟 3** `build_survivor_output` | **符合** | L343–536：純組裝；`sample_scope`／`split`／`provenance`／`survivors[]`／頂層 status；測試 ① |
| **步驟 4** `feature_set_hash` | **符合** | L203–204：`sha256(json.dumps(names, separators=(",",":")))`；測試 ⑫ |
| **不可做** | **符合** | 未改 `ic_report_contract.json`；未接 ML；`validate` 不讀 `report_ref` 檔內容（僅檔名段） |
| **邊界** | **符合** | 空 survivors（①）、degraded root（⑥）、事件 fallback（⑱）、ref 失敗（⑧） |
| **驗證 ①–⑱** | **符合**（⑬ B4） | 35 passed；⑬ 合成 `SimpleNamespace` plan 於 round-trip 斷言 `canonical_idx_hash(test_plan.row_index)` |

---

## 段 B — 實作期決定複核（十項）

| # | 議題 | 結論 |
|---|------|------|
| **B1** `_TYPE_CHECKS` int/float/bool | **接受**。`int` 拒 bool；`float` 接受 int 且 `isfinite`；JSON 往返後整數仍為 `int`、不會 bool 誤判；NaN／inf 於 validator 與 `_f()` 雙層擋（測試 L449–451）。 |
| **B2** `compute_event_identity` 優先序 | **接受**。timestamps 非空 ⇒ `mode=timestamps` 且 `definition_hash==timestamps_hash`（sorted-unique-ms JSON sha256）；query 僅在無 timestamps 時生效；與 TODO 步驟 3／邊界 ⑤ 一致。兩者同時給時忽略 query 為合理單一路徑（orchestrator stage3 先算 cache，B4 只讀 identity）。 |
| **B3** `n_samples_total` 優先序 | **接受**。`report_meta.n_samples` → `marginal n_train+n_test` → split 列數和 → raise（L402–410）；`_build_report_metadata` L3717 寫入 `n_samples=len(features_df)`，B4 主路徑必有第一來源。 |
| **B4** 無 split 之 `arange` 退路 | **接受（B4 義務）**。L438–452：`full_index` 優先，否則 `canonical_idx_hash(arange(n_total))`；positional hash 在無 index 時為誠實退化；B4 應傳 `split_context["full_index"]=features_df.index.values`（TODO 4.1 split_context 已含 train/test plan）。缺 `full_index` 不應改為 raise——與 TODO「無 split ⇒ full 表述」一致。 |
| **B5** fallback 仍帶 `event` 物件 | **接受**。契約只要求 `kind=event⇒event非null`；`kind=full` 時帶追溯用 event 物件＋`degraded=True` 不違契約（測試 ⑱ `p_fb`）。 |
| **B6** composite `"method" in comp` 判別 | **接受**。完整 composite 必有 `method`；status object 僅 `{status,reason}`（測試 `test_view_status_object_composite_and_type_checks`）；B2 `CompositeResult` 與契約 `composite_keys`／`view_status_keys` 已對齊。 |
| **B7** `summary_by_feature` 欄名 | **已實核 OK**。`ic_reporter.py` L447–460／L1409–1449：`summary_table` 列含 `ic_mean`／`icir`／`p_value_adj`；`pass_class` 由 `_annotate_root_status_and_pass_class` L1188–1195 注入每列——非 `ic_ir`／`p_adj`。`build_survivor_output` L488–491 讀同名欄，缺欄 ⇒ null。 |
| **B8** 頂層 `status`／`reason` | **接受**。空 survivors ⇒ `not_applicable:no_survivors`；有 marginal ⇒ 沿用節 status；marginal None ⇒ `not_computed:disabled_by_config`（L500–508）；與 B4 語意相容。 |
| **B9** `provenance.fit_mode` 值域 | **接受（B4 須映射）**。契約 `fit_scope_values`＝`{train,full_sample}`（契約 JSON L45–48）；orchestrator `_resolve_stage1_fit` 內部值為 `train_mask`／`pit_expanding`／`full_sample`（L2609–2617）。`build_survivor_output` 收 **caller 顯式** `fit_mode` 參數；B4 TODO 4.1 已規定 holdout 傳 `fit_scope="train"`、fallback 傳 `"full_sample"`——**禁**直傳 `metadata["fit_mode"]` 原字。 |
| **B10** `removed_candidates` 不驗 `per_feature` | **接受**。契約 `removed_candidate_keys` 無 `per_feature`；survivors[] 已攤平 IC／marginal 欄；validator L322–323 只驗 removed 鍵集。 |

---

## 段 C — 測試品質

- **mutation 探針**：本輪 `bash scripts/gap2_mutation_probe.sh --batch B3` rc=0；八條 RED+RESTORED GREEN；post-restore 35 passed。
- **V-19a/b/c**：探針寫死 symbol/timeframe/case_id，但 `test_identity_three_fields` L381–385 **換值重建**（BTCUSDT／1h／alt_case）先斷言 payload 反映參數——足以擋「與 fixture 同值寫死仍綠」；三探針各 RED ✓。
- **`test_mutation_validator_skips_feature_set_hash`**：monkeypatch `feature_set_hash` 恆等篡改值 ⇒ validator 不 raise ⇒ 測試 `assert mutant_raised` 失敗——**真 seam**（⑫ oracle）。
- **⑭ checklist**：`test_checklist_subset_of_contract_keys` L361–374 驗 checklist **⊆** 契約鍵集（單向，與 TODO ⑭ 字面一致）；`sample_scope_keys` checklist 未列 `n_samples_total`／`n_samples_test`，但 round-trip＋`_check_object(sample_scope)` 仍覆蓋實欄——**非廉價綠**，屬機檢方向設計而非實作缺漏。
- **⑦ V-12**：對映 `test_load_sample_scope_kind_values_subset_of_row_mask_plan_source`（B1 AST）；V-12 RED ✓。
- **skip／smoke**：24 條 B3 測試無 skip；核心含 round-trip、身分、OOS 互斥、event hash、型別 gate。

---

## 段 D — 正確性

| Oracle | 結論 | 碼證 |
|--------|------|------|
| `feature_set_hash` | **正確** | L203–204＋測試 ⑫ 逐字 sha256 |
| `_to_epoch_ms_utc` | **正確** | L162–177：tz-aware 字串、ms 數值（≥1e12）、s 數值（<1e12）三種輸入於測試 ⑱ 同 `timestamps_hash` |
| `canonical_idx_hash` | **可接受** | L423–424／440–451 只傳 `row_index`（與既有 IC split 用法一致）；可選 `split_label`／`symbol`／`base_universe_hash` 未傳——SPEC 只要求用既有原語，B4 有 `base_universe_hash` on SplitPlan 可擴充但非 B3 阻擋 |
| `_TYPE_CHECKS` | **正確** | bool 欄拒 int（L446–448）；float 拒 NaN（L449–451） |

---

## 段 E — registry「GAP-2 待補完」

本批僅契約 resolver／validator／`build_survivor_output`（`version=1` 輸入契約）；**未觸發** G2-R1（ML 橋本體）、G2-R2（forward-stepwise）、G2-R3（xsec 邊際 IC）、G2-R5（nested holdout）。預期與 brief 一致：橋本體仍 blocked-by ML 層。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| pytest 35 passed | fact-verified | **覆核 rc=0** |
| mutation B3 rc=0 | fact-verified | **覆核 rc=0**（receipt 20260818T231005Z） |
| ichc_contract_sync 5 passed | fact-verified | **覆核 rc=0** |
| 段 B 十項為合理選擇 | assumed→**verified** | 段 B 表逐項攻擊（含 B7 欄名、B9 fit_mode 映射） |
| ⑭ checklist 涵蓋全部義務項 | assumed→**部分成立** | 機檢為 checklist⊆契約（單向）；未列 `n_samples_*` 於常數但實作與 validator 已覆蓋——**不構成實作缺陷** |
| 合成 `SimpleNamespace` plan 代表 `SplitPlan` | assumed→**verified** | 測試用欄位 `row_index`／`time_bounds`／`embargo`／`purge_gap`／`base_universe_hash` 與 `contracts.py::SplitPlan` L362–374 對齊；B4 用真 `SplitPlan` 時介面相容 |

---

## Findings（canonical）

## COMPOSER-R18-P3-00

**斷言**: 本輪對 commit `038fd10b` 段 A–E 與段 B 十項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → 35 passed rc=0；`venv/bin/python -m pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` → 5 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B3` → rc=0（V-10/11/12/17b/19a/b/c/20 各 RED+GREEN）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → PASS；`ic_reporter.py` L447–460 summary_table 欄名含 `ic_mean`/`icir`/`p_value_adj` + L1188–1195 `pass_class` 注入；`_resolve_stage1_fit` L2609–2617 內部 `train_mask`/`pit_expanding` vs 契約 `fit_scope_values` `{train,full_sample}`——B4 映射已於 TODO 4.1 明示；`compute_event_identity` 測試 ⑱ 三種 timestamp 輸入同 hash。

**來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0；momentum/Analysis/ic_reporter.py#8f3e2a1b0c9d

本輪核對依據：Task 3.1 步驟 1–4／不可做／邊界／驗證 ①–⑱ 逐條對照 `survivor_contract.py` 與測試檔；段 B 十問獨立重判（型別表、event hash 優先序、n_samples 來源、arange 退路、fallback event 追溯、composite 判別、summary_table 欄名實 grep、status 語意、fit_mode B4 映射、removed_candidates 鍵集）；mutation 探針與 ichc sync 本機重跑；registry G2-R1/R2/R3/R5 觸發條件未滿足。B4 接線注意項（`fit_mode` 映射、`full_index` 傳入）屬已文件化接線義務，非 B3 實作缺陷。

---

## §1 必查（11 類摘要）

1. 矛盾：無（SPEC/TODO/契約/實作一致）。2. 漏項：B3 scope 內無。3. 不可測：35 pytest＋8 mutation＋round-trip validator。4. quant：OOS 四欄互斥、身分三欄禁 `None==None`、event hash 決定性——實作＋測試覆蓋。5–8. 過度工程／OOM／cache／API：N/A 或無問題。9. 測試：無 skip、探針 seam 真。10. Agent 可執行：函式／檔案精確。11. 短命工：無（Task 3.1 存活至 ML 橋輸入契約）。

---

ASSUMPTIONS_VERIFIED: pytest 35+5 passed；B3 mutation rc=0；summary_table 欄名 ic_mean/icir/p_value_adj/pass_class；fit_mode 內部值 vs 契約值域（B4 映射）；n_samples 於 _build_report_metadata L3717
TESTS_RUN: `pytest tests/momentum/Analysis/test_survivor_contract.py -q` 35 passed；`pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` 5 passed；`bash scripts/gap2_mutation_probe.sh --batch B3` rc=0；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` PASS
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查只讀）

STATUS: DONE
