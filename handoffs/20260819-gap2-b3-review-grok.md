# GAP-2 B3 實作 code review（R18）— GROK

**task-id**: `20260819-GAP2-B3-REVIEW-R18`｜**family**: grok｜**輪次**: R18  
**brief**: `handoffs/20260819-gap2-b3-review-BRIEF.md`  
**審查標的**: commit `038fd10b`（Task 3.1／3.2：`survivor_contract.py` resolver／validator／build＋測試＋B3 探針）  
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit／push／禁就地改檔實驗**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_ichc_contract_sync.py -q` → **40 passed** rc=0（35＋5；~10.5s）
- `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → **PASS**（2 mutation 真跑）rc=0
- `bash scripts/gap2_mutation_probe.sh --batch B3` → **rc=0**；V-10／11／12／17b／19a／19b／19c／20 各 `RED ✓`＋`RESTORED GREEN ✓`；receipt `handoffs/run_receipts/20260818T231235Z-gap2-B3-probe.log`
- `grep -E "from api\.|import api" momentum/Analysis/survivor_contract.py` → **0 命中**
- `git show 038fd10b --stat`：僅 `survivor_contract.py`／`test_survivor_contract.py`／`gap2_mutation_probe.sh`／receipt／白話看板；契約 JSON 未動
- orchestrator／reporter 欄位實核見段 B（B-3／B-7／B-9）

---

## Verdict：可進 B4

Task 3.1／3.2 主路徑與契約 oracle／mutation **符合**；段 B 十項實作期決定經獨立攻擊後**均可接受**（B-4／B-9 附 B4 接線注意，不構成 B3 阻擋）；段 E 四條殘留觸發**均未成立**。本輪無 BLOCKING／MAJOR／MINOR finding（sentinel `GROK-R18-P3-00`）。

---

## 段 A — 契約符合度（Task 3.1 步驟 1–4／①–⑱）

| 要點 | 結論 | 碼證 |
|------|------|------|
| **步驟 1** `resolve_ref` | **符合** | `survivor_contract.py` L140–159：檔缺／鍵路徑缺／非 list ⇒ `ContractValidationError`；測試 ⑧ |
| **步驟 2** validator | **符合** | L231–336：物件層 `_check_object`（additional_properties:false／required／type／nullable）；枚舉；`kind=event ⇒ event 非 null`；OOS 四欄互斥；`feature_set_hash`；survivors 序列==names；身分三欄（`report_meta` 缺鍵 raise，禁 `None==None`；`report_ref_path` 檔名段）；不讀 report 檔內容 |
| **步驟 3** `build_survivor_output` | **符合** | L343–536：純組裝；OOS 四欄由 `root_analysis_status` 單一來源；sample_scope／split／provenance／survivors／composite／removed／頂層 status |
| **步驟 4／不可做** | **符合** | 不接 ML；不動 `ic_report_contract.json`（本輪 `test_ichc_contract_sync` 5 passed）；不複列鍵表（讀 `load_survivor_contract()`） |
| **①–⑫⑭–⑱** | **符合** | 測試覆蓋；⑬ 註明 B4 整合（合成 plan 已斷言 `test_index_hash == canonical_idx_hash`） |
| **邊界** | **符合** | 空 survivors→`not_applicable:no_survivors`；degraded root；event／fallback；ref 失敗；query 模式 `timestamps_hash is None` |

---

## 段 B — 實作期決定複核（十項；優先攻）

| # | 議題 | 結論 |
|---|------|------|
| **B1** `_TYPE_CHECKS` | **接受**。`float` 接受非 bool 之 int／float 且 `isfinite`；`int` 拒 bool；`bool` 只准 bool。JSON 往返後整數仍為 int、`1.0` 仍為 float；IC 欄偶發整數 JSON 可過 float 檢查屬合理寬容。測試拒 `oos_guarantees=1`、`ic_mean=nan`、`train_rows="3000"`。 |
| **B2** `compute_event_identity` 優先序 | **接受**。timestamps 非空 ⇒ `mode=timestamps` 且 `definition_hash==timestamps_hash`（sorted-unique-ms JSON sha256）；query 僅無 timestamps 時生效。契約 `_doc` 分兩模式敘述；SPEC「`query\|sorted timestamps`」讀作交替（非合併 hash）。同時給定時 timestamps 優先＝更具體身分；本輪實核 both→timestamps 且 def≠query-only hash。合併 hash 屬延伸檔提案，非 B3 阻擋。 |
| **B3** `n_samples_total` 優先序 | **接受**。實核 `_stage7_report`：`meta.update({"n_samples": int(len(features_df))})`（`ic_filter_orchestrator.py` ~L3717）。優先序 `report_meta.n_samples`→marginal n_train+n_test→split 列數和→raise 合理；B4 常有 `n_samples`。 |
| **B4** fallback `arange(n_total)` | **可接受（B4 注意）**。無 plan 時用 `full_index` 或 `np.arange(n_total)`。本輪實核：positional arange hash ≠ 以 epoch-ms 當 index 之 hash ⇒ **若 B4 漏傳 `full_index` 且真實列身分非 0..n-1 positional，row identity 會失真**。契約／TODO 已寫「對全 index」；建議 B4 **必傳** `full_index`（缺⇒raise）——屬接線強化，非 B3 須改碼。 |
| **B5** fallback 仍帶 `event` 物件 | **接受**。`kind=full`＋`degraded=True` 仍可帶身分；契約只強制 `kind=event ⇒ event 非 null`（單向）。測試 ⑱ fallback 案例綠。 |
| **B6** composite 以 `"method" in comp` 判別 | **可接受**。完整 composite 必有 `method`；status object 用 `view_status_keys`。顯式 discriminator 更清晰但非阻擋；現判別＋鍵集檢查足夠 fail-closed。 |
| **B7** survivors IC 快照欄名 | **接受（主委最不確定處已實核）**。`_build_summary_table` 寫入 `ic_mean`／`icir`／`p_value_adj`（~L3581–3587）；`pass_class` 由 `_annotate_root_status_and_pass_class` 於報告組裝後寫入 summary 列。`ic_reporter` CSV／JSON 路徑同用 `ic_mean`／`icir`／`p_value_adj`（**非** `ic_ir`／`p_adj`）。缺欄⇒null；`redundancy_kept=True` 常數符合倖存者定義。 |
| **B8** 頂層 status／reason | **接受**。空 survivors⇒`not_applicable:no_survivors`；有 marginal⇒沿用節；None⇒`not_computed:disabled_by_config`。與 B4 disabled／空集合語意相容。 |
| **B9** `provenance.fit_mode` ∈ `fit_scope_values` | **接受（B4 接線注意）**。契約 `fit_scope_values={train,full_sample}`；validator L293–294 對齊。**實核 `_resolve_stage1_fit` 回傳 `{full_sample, train_mask, pit_expanding}`**——與契約 **不是同一值域**。`metadata["fit_mode"]` 屬預處理詞彙；B4 應傳 stage6b 之 **`fit_scope`**（`train`／`full_sample`），**禁**把 `train_mask`／`pit_expanding` 原樣寫入 provenance。此為接線陷阱標註，B3 綁契約值域正確。 |
| **B10** `removed_candidates` 不驗 `per_feature` | **接受**。契約 `survivor_file_keys` 無 `per_feature`；survivors[] 已攤平；只驗 `removed_candidate_keys` 正確。 |

---

## 段 C — 測試品質

- **mutation 探針（本輪重跑）**：`bash scripts/gap2_mutation_probe.sh --batch B3` → **rc=0**；receipt `20260818T231235Z`：八條皆 RED＋RESTORED GREEN；baseline／post-restore 35 passed。
- **V-19a/b/c**：`test_identity_three_fields` 以 `symbol=BTCUSDT`／`timeframe=1h`／`case_id=alt_case` **換值重建**後斷言 payload 反映新值並過 validator——足以擋「與 fixture 同值寫死」；探針字面替換寫死 ETHUSDT／12h／ic_gatekeeper ⇒ 該測試紅。
- **`test_mutation_validator_skips_feature_set_hash`**：monkeypatch `feature_set_hash` 恆回傳篡改值 ⇒ validator 不再 raise ⇒ 外層 `assert mutant_raised` 期望失敗——**真 seam**（對應 V-20 字面 `if False` 略過重算）。
- **⑭ checklist vs SPEC L179 改法**：checklist 涵蓋改法段具名義務（身分／sample_scope／event 五欄／provenance／split／row_identity／feature_names／feature_set_hash／survivors IC+marginal 欄／composite／OOS 四欄＋selection_sample／oos_semantics／statistic）。`feature_name` 由⑫序列斷言覆蓋；`n_samples_*`／`projection_space` 等非 L179 改法具名清單之鍵不在⑭子集（⑭語意＝checklist ⊆ 契約，非契約 ⊆ checklist）。
- **⑦／V-12**：`sample_scope_kind_values ⊆ RowMaskPlan.source` AST（B1 `test_load_…`）；V-12 對契約插入 `"panel"` ⇒ 該測試紅。
- **廉價綠**：無 skip；核心含 raise／枚舉／OOS 互斥／hash／身分／mutation；非僅 smoke。

---

## 段 D — 正確性

| 項目 | 本輪 | 判定 |
|------|------|------|
| `feature_set_hash` | `sha256(json.dumps(names, separators=(",",":")).encode())` | 與 validator／測試⑫一致 ✓ |
| `_to_epoch_ms_utc` | 字串／ms／s 三路（⑱）同 `timestamps_hash`；naive 經 `utc=True` | 一致 ✓ |
| `canonical_idx_hash` | build 只傳 `row_index`（`split_label`／`symbol`／`base_universe_hash` 預設 `""`） | **符合 SPEC「用既有原語」**；加命名空間防跨宇宙撞 hash 屬可選強化，非本批義務 |
| OOS 四欄 | `ok_oos`⇒(True,oos)；否則 degraded＋False＋full_sample_research_only | 單一來源 ✓ |

---

## 段 E — registry「GAP-2 待補完」

本批落地契約交付物（resolver／validator／build＋測試＋B3 探針）；`version=1` 為未來橋之**輸入契約**，**未**接 ML 橋、**未**做 forward-stepwise 選擇、**未**接 xsec 邊際 IC、**未**改 holdout／`independent_oos_validation_allowed`。G2-R1／R2／R3／R5 觸發**均未成立**；「為何現在不做」理由仍成立（預期：無）。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 本輪 |
|------------|------|
| pytest 35／ichc 5 | **覆核** 40 passed rc=0 |
| mutation B3 rc=0／mpc PASS／R1=0 | **覆核** probe rc=0；mpc PASS；R1 0 命中 |
| 段 B 十項合理（尤 B-7／B-4／B-2） | **逐項攻擊後接受**；B-7 欄名實核為真；B-4／B-9 標 B4 接線注意 |
| SimpleNamespace ≈ SplitPlan | **覆核** SplitPlan 含 `row_index`／`time_bounds`／`embargo`／`purge_gap`／`base_universe_hash`；測試 fixture 覆蓋 build 所讀欄（缺 `split_label`／`symbol` 等本函式未讀） |
| ⑭ 涵蓋 SPEC 改法義務 | **覆核** 具名義務 ⊆ checklist；見段 C |

---

## Findings（canonical）

## GROK-R18-P3-00

**斷言**: 本輪對 commit `038fd10b` 段 A–E（含段 B 十項實作期決定）逐項核對後無 finding。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_ichc_contract_sync.py -q` → 40 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B3` → rc=0（V-10／11／12／17b／19a-c／20 RED+RESTORED GREEN；receipt `handoffs/run_receipts/20260818T231235Z-gap2-B3-probe.log`）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → PASS；`_build_summary_table` 欄＝`ic_mean`／`icir`／`p_value_adj`（非 `ic_ir`／`p_adj`）；`_stage7_report` 寫 `n_samples=len(features_df)`；`_resolve_stage1_fit`∈{full_sample,train_mask,pit_expanding}≠`fit_scope_values`（B4 須傳 fit_scope）；R1 grep 0；契約 JSON 未動；G2-R1..R5 觸發未成立。

**來源摘要**: momentum/Analysis/survivor_contract.py#96bc6de810e6；tests/momentum/Analysis/test_survivor_contract.py#01de7a2306c6；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0；scripts/gap2_mutation_probe.sh#23baf8fbaefb；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

核對依據：Task 3.1 步驟 1–4／不可做／邊界／①–⑱（⑬ 留 B4）對照源碼與測試；段 B 十問獨立重判並實核 orchestrator／reporter；mutation 八條本機重跑；registry 四殘留觸發未成立。未發現需修補後才能進 B4 之 B3 缺陷。

---

## §1 必查（11 類摘要）

1. 矛盾：無（契約／TODO／實作對齊；fit_mode 詞彙差已標 B4）。  
2. 漏項：B3 scope 內無（B4 persist／stage6b 屬計劃）。  
3. 不可測：pytest＋八 mutation＋hash／身分／OOS 互斥。  
4. quant：OOS 四欄／獨立驗證 false／event 身分序列化——實作＋測試鎖住。  
5–8. 過度工程／OOM／cache／API：本批 N/A 或無問題；Python 3.9 相容。  
9. 測試：+24 條＋八探針；無 skip；V-19 換值重建非廉價綠。  
10. Agent 可執行：檔案／函式／驗證明確。  
11. 短命工：無（契約讀取器長期保留；B4 只呼叫不覆蓋本檔邏輯）。

STATUS: DONE
