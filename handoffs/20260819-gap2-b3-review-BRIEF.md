# GAP-2 B3 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap2-b3-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–E 之敘述是「請你查證的問句與我的待攻決定」，不是主委的 operational 結論；實際結論在委員產出與收斂檔 `handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md`。
> 🔴 **禁就地改任何 repo 檔做實驗**（實驗一律 in-memory monkeypatch）；探針有互斥鎖（rc=3 ⇒ 稍後重試或讀 receipt）。

brief-kind: review

## 審查標的（commit `038fd10b`；`git show 038fd10b --stat`）
- `momentum/Analysis/survivor_contract.py`（Task 3.1 新增：`resolve_ref`／`compute_event_identity`／`feature_set_hash`／`_check_object`／`validate_survivor_output`／`build_survivor_output`；loader 段未動）
- `tests/momentum/Analysis/test_survivor_contract.py`（+24 條：Task 3.1 驗證 ①–⑱ 除 ⑬（B4 整合）＋`test_mutation_validator_skips_feature_set_hash`；`-k load` 11 條不變）
- `scripts/gap2_mutation_probe.sh`（B3 case 表：V-10／11／12／17b／19a／19b／19c／20；receipt `handoffs/run_receipts/20260818T230546Z-gap2-B3-probe.log`）
- **未動**：`ic_survivor_contract.json`（B1 A1-7 版）、`ic_report_contract.json`（`test_ichc_contract_sync` 5 passed）
- 契約來源：TODO（FROZEN）Task 3.1／3.2；SPEC Task 3.1／§G 契約 oracle／D6；AMENDMENTS A1-1..A1-8

## 本輪任務（五段皆必答）
**段 A — 契約符合度**：Task 3.1 步驟 1–4／不可做／邊界／驗證 ①–⑱ 逐條；`resolve_ref` fail-closed（檔缺／鍵路徑缺／非 list）；validator 遞迴驗每物件層 `additional_properties:false`／required／type／nullable；枚舉；`kind=event ⇒ event 非 null`；OOS 四欄互斥；`feature_set_hash`；survivors 序列 == feature_names；身分三欄（`report_meta` 缺 ⇒ raise，禁 `None==None`；`report_ref_path` 檔名段）；不讀 `report_ref` 檔；不接 ML；不動 report 契約。

**段 B — 🔴 實作期決定（請攻）**：
1. **型別檢查表** `_TYPE_CHECKS`：`float` 接受 int（非 bool）且須有限（NaN／inf 拒）；`int` 拒 bool；`bool` 只准 bool。JSON 往返後 int/float 語意是否會誤判？
2. **`compute_event_identity`**：timestamps 非空 ⇒ `mode="timestamps"` 且 `definition_hash == timestamps_hash`（皆＝sorted-unique-ms JSON 之 sha256）；query 只在無 timestamps 時生效；數值 timestamps 依 `max|·|>=1e12` 判 ms／s（沿 ic_engine 原語）。這與契約 `_doc`／SPEC「`definition_hash=sha256(canonical(query|sorted timestamps))`」是否一致？兩者同時給時的優先序是否該反過來或合併 hash？
3. **`n_samples_total` 來源優先序**：`report_meta["n_samples"]`（orchestrator 於報告組裝寫入）→ `marginal.n_train+n_test` → split 列數和 → 皆缺 raise。合理？B4 orchestrator 一定有 `n_samples`（`_stage7_report` `meta.update({"n_samples": len(features_df)})`）——請實核。
4. **無 split（fallback）時之 `split` 物件**：`split_method` 取 `report_meta.split_method` 或 `full_sample_fallback`；`train_rows==test_rows==n_total`；`row_identity` 兩 hash 相同＝`canonical_idx_hash(split_context["full_index"])` 或 `arange(n_total)`（B4 須傳 `full_index`）。這個 `arange` 退路是否會讓 row identity 失真（positional vs timestamp index）？是否應改為必傳 `full_index`（缺 ⇒ raise）？
5. **`sample_scope.event` 於 fallback 時仍帶身分物件**（`kind=full`、`degraded=True`）——供追溯；契約只要求 `kind=event ⇒ event 非 null`。可接受？
6. **`composite` 為 status object 時**（disabled／None）用 `view_status_keys` 驗；完整 composite 用 `composite_keys`——以 `"method" in comp` 判別。是否該改為明確 discriminator？
7. **`survivors[]` IC 快照**（`ic_mean`／`icir`／`p_value_adj`／`pass_class`）自 `summary_by_feature[name]`，缺欄 ⇒ null；`redundancy_kept=True` 常數（倖存者定義即已通過 redundancy filter）。B4 caller 之 `summary_by_feature` 由 `report["summary_table"]` 轉 `{feature_name: row}`——請對照 `ic_reporter` summary_table 之欄名（`ic_mean`／`icir`／`p_value_adj`／`pass_class` 是否真存在，還是叫 `ic_ir`／`p_adj`？）**這是我最不確定處**。
8. **頂層 `status`／`reason`**：空 survivors ⇒ `not_applicable:no_survivors`；有 marginal ⇒ 沿用節 status／reason；marginal 為 None ⇒ `not_computed:disabled_by_config`。與 B4 語意相容？
9. **`provenance.fit_mode` 驗 ∈ `fit_scope_values`**（`train`／`full_sample`）——orchestrator `metadata["fit_mode"]` 的值域是否恰為這兩者？請實核（`_resolve_stage1_fit`）。
10. **validator 對 `removed_candidates` 只驗 `removed_candidate_keys`、不驗 `per_feature`（檔內無 per_feature，survivors[] 已攤平）**——契約 `survivor_file_keys` 無 `per_feature`；可接受？

**段 C — 測試品質**：**請重跑** `bash scripts/gap2_mutation_probe.sh --batch B3`（<1 分鐘）貼 rc；V-19 三 case 之 oracle 加了「換值重建」（symbol=BTCUSDT／timeframe=1h／case_id=alt_case）——是否足以擋「與 fixture 同值寫死」；`test_mutation_validator_skips_feature_set_hash` monkeypatch `feature_set_hash` 恆等於篡改值是否為真 seam；⑭ checklist 常數是否涵蓋 SPEC Task 3.1「改法」段全部義務項名稱（請逐項對照 SPEC L179）；⑦（kind ⊆ RowMaskPlan.source AST）於 B1 已有——V-12 對映該測試；有無廉價綠燈。

**段 D — 正確性**：`feature_set_hash = sha256(json.dumps(names, separators=(",",":")))`；`_to_epoch_ms_utc` 對 tz-aware／naive 字串、ms／s 數值之一致性（測試 ⑱ 三種輸入同 hash）；`canonical_idx_hash` 用法（只傳 row_index，未帶 split_label／symbol／base_universe_hash——是否該帶以防撞？SPEC 只說用既有原語）。

**段 E — registry「GAP-2 待補完」四條之觸發是否已成立**（每批必審）：
| # | 待補完項 | 為何現在不做 | 觸發條件 |
|---|---|---|---|
| G2-R1 | IC→ML 橋本體 | user-ruling: 2026-08-18 橋本體 blocked-by ML 層 | ML 層重寫或宣告穩定 |
| G2-R2 | 以邊際 IC 做 forward-stepwise 選擇 | needs-research: post-FDR 二次選擇多重比較政策無認可方法 | 委員會定出政策 |
| G2-R3 | xsec 路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC | #4 完工 |
| G2-R5 | nested／frozen final test | blocked-by: IC 主路徑切分 holdout-only | 主線切分升級 |
請答：本批（2b 契約交付物落地）有無使 G2-R1 觸發成立或使理由失效？（預期：無——契約 `version=1` 為未來橋之輸入，橋本體仍 blocked。）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1／§3 與 canonical 四欄。ID＝`## <FAMILY>-R18-P<0-3>-<NN>`（**本輪＝R18**）。零 findings 用 sentinel `## <FAMILY>-R18-P3-00`（body 須實質）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁 commit／push、禁就地改檔實驗**；只產你自己的 review 檔。可跑測試／探針（貼 rc）。venv **Python 3.9.6**。使用者裁決不受理重議。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → 35 passed；`tests/momentum/Analysis/test_ichc_contract_sync.py` → 5 passed（Claude 實跑 2026-08-19）
fact-verified: `bash scripts/gap2_mutation_probe.sh --batch B3` → rc=0（八條 RED＋還原綠）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → PASS
fact-verified: `git show 038fd10b --stat` 只含 `survivor_contract.py`／該測試檔／探針腳本／receipt／白話看板；契約 JSON 未動；R1 零命中
assumed: 段 B 十項實作期決定為契約內合理選擇（特別是 B-7 summary_table 欄名、B-4 `arange` 退路、B-2 hash 優先序）← 請攻並實核 orchestrator／reporter
assumed: 測試用合成 `SimpleNamespace` 之 train/test plan 足以代表 `SplitPlan`（`row_index`／`time_bounds`／`embargo`／`purge_gap`／`base_universe_hash`）← 請對照 `momentum/core/contracts.py::SplitPlan` 欄位
assumed: ⑭ checklist 已涵蓋 SPEC Task 3.1 全部義務項 ← 請逐項對照

## Time-box
優先序＝段 B ＞ 段 D ＞ 段 C ＞ 段 A ＞ 段 E。**不受理**：使用者裁決、TODO 已 Frozen 之契約本身（要改走延伸檔提案）、B4–B5 未實作部分、治理機制。

## 產出
Verdict（可進 B4／需修補後進 B4／有根本缺陷需重作）＋段 A–E 結論＋canonical findings。收尾清 /tmp workdir（保留 claude-501）。
