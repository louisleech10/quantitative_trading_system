# Reconcile — 20260819-gap2-b3-review-r18

**來源** 20260819-gap2-b3-review-codex.md, 20260819-gap2-b3-review-composer.md, 20260819-gap2-b3-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-19）

三家共 **10 條**（codex 8：1 P0／6 P1／1 P2；composer sentinel；grok sentinel），下列七個群集**引用全部 10 條，0 掉項**。Verdict：codex「需修補後進 B4」、composer／grok「可進 B4」⇒ 依較嚴：**需修補後進 B4**；8 條**全接受**（M4 部分接受：`n_samples_total` 對帳採 `≥`＋test 列 exact，因 purge／embargo 使 `==` 不成立），修補走 B3 修補 commit（A1-9）；戳記輪 r19 兼修補驗收。

Verdict：需修補後進 B4——修補 commit 落地後派 stamp r19（含 codex 反例重跑）；APPROVED ⇒ B3 CLOSED → B4。

### M1 — `provenance.fit_mode` 被以 `fit_scope_values` 驗證，holdout 之 `train_mask` 會被拒（P0）
**引用**: CODEX-R18-P0-01
**處置＝接受**：`provenance.fit_mode`＝orchestrator 前處理 fit_mode 原值（`full_sample|train_mask|pit_expanding`），validator 只驗非空字串、不做映射（與 `composite.fit_scope` 語意分離；A1-9）；測試 `test_provenance_fit_mode_raw_orchestrator_values_accepted` 三值 build→validate；B4 整合測試須以真實 holdout 路徑跑 build→validate（列入 B4 驗收）。

### M2 — `resolve_ref` 未限制 repo 相對路徑
**引用**: CODEX-R18-P1-02
**處置＝接受**：拒絕絕對路徑／`..`／resolve 後逃出 repo root；測試 `test_resolve_ref_rejects_escape`。

### M3 — event 物件缺 mode 不變式；fallback 以 `arange` 冒充 row identity；未知 root status 靜默降級
**引用**: CODEX-R18-P1-03, CODEX-R18-P1-04, CODEX-R18-P1-05
**處置＝接受**：`_check_event_object` 依 mode 驗 hash 64-hex／相等／計數；無 split 時 `split_context["full_index"]` 必傳（缺 ⇒ raise；B4 呼叫方義務入 A1-9）；`root_analysis_status` 只准兩值否則 raise；三條各有測試（`test_event_object_mode_invariants`／`test_fallback_requires_full_index_and_uses_real_index`／`test_unknown_root_status_raises`）。

### M4 — `n_samples_total` 未與 marginal／split 列數對帳
**引用**: CODEX-R18-P1-06
**處置＝部分接受**：正整數；`≥ marginal n_train+n_test`；`≥ split train_rows+test_rows`；marginal `n_test` 與 split `test_rows` **exact**。**不採 `==`**：purge／embargo 使 train+test < total 為正常（codex 建議之 exact 一致對 total 不成立；對 test 列採 exact）。測試 `test_n_samples_total_reconciliation`（含 total 6000 > 5000 合法案例）。

### M5 — ⑭ checklist 只驗子集且漏巢狀鍵
**引用**: CODEX-R18-P1-07
**處置＝接受**：checklist 補 `sample_scope.n_samples_*`／`survivor_record.feature_name`／composite／removed／view 巢狀鍵；⑩ tamper 參數化加 `removed_candidates[z]` 與 composite 物件層加鍵。維持 `⊆` 語意（TODO ⑭ 原文）＋巢狀 tamper。

### M6 — ⑱ 缺 naive 字串 regression
**引用**: CODEX-R18-P2-08
**處置＝接受**：`test_event_identity_naive_string_matches_aware`。

### M7 — 收斂 sentinel（composer／grok）：可進 B4
**引用**: COMPOSER-R18-P3-00, GROK-R18-P3-00
**處置＝接受（記錄）**：段 B 十問兩家獨立重判可接受（含 summary_table 欄名實核 `ic_mean`／`icir`／`p_value_adj`／`pass_class` 存在）；與 M1–M6 修補不衝突。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R18-P0-01
**斷言**: B4 若沿用 orchestrator metadata 的 `fit_mode`，正常 holdout payload 會被 B3 validator 拒絕，契約無法落檔。 **碼證**: `ic_filter_orchestrator.py:958` 寫入 `_resolve_stage1_fit()` 的原值；`:2613-2618` 返回 `train_mask`/`pit_expanding`；`survivor_contract.py:293-294` 僅接受契約 `train`/`full_sample`；VERIFY `venv/bin/python ...` → `FIT_MODE_TRAIN_MASK=REJECTED ContractValidationError provenance.fit_mode not in fit_scope_values`。 **來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744;momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970e。 [P0] 信心度=10/10；修法：在 B4 邊界明確把 orchestrator fit mode 映射成契約 fit scope，或另傳 typed `fit_scope`，並補真實 holdout integration test。
## CODEX-R18-P1-02
**斷言**: `resolve_ref()` 未限制 repo-relative path，絕對路徑可讀取 repo 外 JSON，違反 TODO L153 的 fail-closed 相對路徑契約。 **碼證**: `survivor_contract.py:142-146` 直接 `REPO_ROOT / rel_path` 後 `is_file/open`；VERIFY absolute ref → `ABSOLUTE_REF 6`。 **來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744;docs/GAP2_MARGINAL_IC_TODO.md#100695426a6cb。 [P1] 信心度=9/10；修法：拒絕 absolute/`..`/symlink escape，resolve 後強制位於 `REPO_ROOT`。
## CODEX-R18-P1-03
**斷言**: validator 只驗 event object 的欄位型別與 mode 字面，會接受 `mode="timestamps"` 但兩 hash/計數全為 null 的殘缺 identity。 **碼證**: `survivor_contract.py:278-281` 沒有 mode-specific hash/count invariant；VERIFY in-memory → `INCOMPLETE_EVENT=ACCEPTED {'definition_hash': None, 'timestamps_hash': None, 'mode': 'timestamps', 'n_events': None, 'n_timestamps_requested': None}`。 **來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744;momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0。 [P1] 信心度=9/10；修法：依 mode 驗 hash/count 非 null、64-hex、timestamps hash 等於 definition hash，或用 canonical identity 重算驗證。
## CODEX-R18-P1-04
**斷言**: fallback 缺 `split_context.full_index` 時以 positional `arange(n_total)` 冒充全量 row identity，timestamp/row-id index 會被靜默改寫。 **碼證**: `survivor_contract.py:439-451` 明示 fallback；orchestrator `:396/402` 的 SplitPlan time bounds 來自 `features_df.index`；VERIFY → `FALLBACK_ARANGE True 5000 5000`。 **來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744;momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970。 [P1] 信心度=9/10；修法：fallback 必須傳真實 `full_index`，缺少即 `ContractValidationError`，並補 timestamp-index regression。
## CODEX-R18-P1-05
**斷言**: `build_survivor_output()` 將任何未知 `root_analysis_status` 靜默改成 `degraded_full_sample`，掩蓋 caller 狀態錯誤。 **碼證**: `survivor_contract.py:384-388` 只有 `ok_oos` 分支，其餘一律降級；VERIFY `root_analysis_status="unexpected_status"` → `UNKNOWN_ROOT degraded_full_sample False full_sample_research_only`，之後仍過 validator。 **來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744;momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0。 [P1] 信心度=9/10；修法：只接受契約允許的兩個 root status，未知值 fail-closed，不可用降級取代錯誤。
## CODEX-R18-P1-06
**斷言**: `n_samples_total` 優先採 metadata 但不和 marginal/split rows 對帳，錯誤樣本數可產出並通過 validator。 **碼證**: `survivor_contract.py:402-410` 直接採 `report_meta["n_samples"]`；VERIFY 將其改為 1 → `N_SAMPLES_MISMATCH_ACCEPTED 1 3000 2000`。 **來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744;docs/GAP2_MARGINAL_IC_TODO.md#100695426a6cb。 [P1] 信心度=9/10；修法：接受優先序但要求非負整數，若 marginal/split rows 同時存在須 exact 一致，否則 raise。
## CODEX-R18-P1-07
**斷言**: ⑭ checklist 只驗列出的鍵是契約子集，無法證明 SPEC L179 的義務全被列入；目前漏 `sample_scope.n_samples_*`、`survivor_record.feature_name`、composite/removed-candidate nested keys。 **碼證**: `test_survivor_contract.py:361-374` 使用 `set(items) <= ...`，沒有反向 exact coverage；35 tests 綠不改變此空洞。 **來源摘要**: tests/momentum/Analysis/test_survivor_contract.py#01de7a2306c6;docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d。 [P1] 信心度=9/10；修法：把 L179 義務建成完整 expected map，對每組做 exact equality，並為 nested composite/removed schema 加 unknown-key tamper test。
## CODEX-R18-P2-08
**斷言**: ⑱ 沒有 regression 覆蓋 naive datetime string，雖 helper 實跑可與 aware/ms/s 對齊。 **碼證**: `test_survivor_contract.py:408-424` 只有 Z-aware string、ms、s；VERIFY `NAIVE_AWARE_SAME True`。 **來源摘要**: tests/momentum/Analysis/test_survivor_contract.py#01de7a2306c6;momentum/Analysis/survivor_contract.py#dd64062f9744。 [P2] 信心度=9/10；修法：在 ⑱ 明確加入 naive string 與 aware/ms/s 的同 hash 斷言。
ASSUMPTIONS_VERIFIED: summary_table 欄名 `ic_mean/icir/p_value_adj` 由 ic_filter_orchestrator.py:3578-3587 實核，pass_class 由 :1191-1195 注入；SplitPlan 欄位由 momentum/core/contracts.py:361-375 實核；SPEC/TODO/AMENDMENTS 均已讀，r18 reconcile synth 尚未存在且非 review brief 前置依賴。
TESTS_RUN: `bash scripts/gap2_mutation_probe.sh --batch B3` rc=0（8/8 RED+GREEN，receipt `handoffs/run_receipts/20260818T231634Z-gap2-B3-probe.log`）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` PASS；`venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` 35 passed；`venv/bin/python -m pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` 5 passed。
FAILURES_SEEN: 初次 probe 被外部執行中止於 V-19b 留下 stale lock；PID 27089 已確認不存在、鎖已清理，第二次同命令 rc=0；受審碼未改。
SCOPE_CHANGES: none；僅產生 brief 指定 probe receipt 與本 review 檔，未改 code、SPEC、TODO、契約 JSON、commit 或 push。 NUMERIC_OR_SCHEMA_IMPACT: none from this review；finding 僅要求修補驗證/整合語意。
HANDOFF_OUTPUT: `handoffs/20260819-gap2-b3-review-codex.md`；family=codex；task-id=20260819-GAP2-B3-REVIEW-R18。
STATUS: DONE
## COMPOSER-R18-P3-00

**斷言**: 本輪對 commit `038fd10b` 段 A–E 與段 B 十項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → 35 passed rc=0；`venv/bin/python -m pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` → 5 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B3` → rc=0（V-10/11/12/17b/19a/b/c/20 各 RED+GREEN）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → PASS；`ic_reporter.py` L447–460 summary_table 欄名含 `ic_mean`/`icir`/`p_value_adj` + L1188–1195 `pass_class` 注入；`_resolve_stage1_fit` L2609–2617 內部 `train_mask`/`pit_expanding` vs 契約 `fit_scope_values` `{train,full_sample}`——B4 映射已於 TODO 4.1 明示；`compute_event_identity` 測試 ⑱ 三種 timestamp 輸入同 hash。

**來源摘要**: momentum/Analysis/survivor_contract.py#dd64062f9744；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0；momentum/Analysis/ic_reporter.py#8f3e2a1b0c9d

本輪核對依據：Task 3.1 步驟 1–4／不可做／邊界／驗證 ①–⑱ 逐條對照 `survivor_contract.py` 與測試檔；段 B 十問獨立重判（型別表、event hash 優先序、n_samples 來源、arange 退路、fallback event 追溯、composite 判別、summary_table 欄名實 grep、status 語意、fit_mode B4 映射、removed_candidates 鍵集）；mutation 探針與 ichc sync 本機重跑；registry G2-R1/R2/R3/R5 觸發條件未滿足。B4 接線注意項（`fit_mode` 映射、`full_index` 傳入）屬已文件化接線義務，非 B3 實作缺陷。

---

## GROK-R18-P3-00

**斷言**: 本輪對 commit `038fd10b` 段 A–E（含段 B 十項實作期決定）逐項核對後無 finding。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_ichc_contract_sync.py -q` → 40 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B3` → rc=0（V-10／11／12／17b／19a-c／20 RED+RESTORED GREEN；receipt `handoffs/run_receipts/20260818T231235Z-gap2-B3-probe.log`）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → PASS；`_build_summary_table` 欄＝`ic_mean`／`icir`／`p_value_adj`（非 `ic_ir`／`p_adj`）；`_stage7_report` 寫 `n_samples=len(features_df)`；`_resolve_stage1_fit`∈{full_sample,train_mask,pit_expanding}≠`fit_scope_values`（B4 須傳 fit_scope）；R1 grep 0；契約 JSON 未動；G2-R1..R5 觸發未成立。

**來源摘要**: momentum/Analysis/survivor_contract.py#96bc6de810e6；tests/momentum/Analysis/test_survivor_contract.py#01de7a2306c6；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0；scripts/gap2_mutation_probe.sh#23baf8fbaefb；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

核對依據：Task 3.1 步驟 1–4／不可做／邊界／①–⑱（⑬ 留 B4）對照源碼與測試；段 B 十問獨立重判並實核 orchestrator／reporter；mutation 八條本機重跑；registry 四殘留觸發未成立。未發現需修補後才能進 B4 之 B3 缺陷。

---


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: codex APPROVED 2026-08-19 sha256:005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5 task:20260819-GAP2-B3-STAMP-R19
RECONCILE-STAMP: grok APPROVED 2026-08-19 sha256:005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5 task:20260819-GAP2-B3-STAMP-R19
RECONCILE-STAMP: composer APPROVED 2026-08-19 sha256:005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5 task:20260819-GAP2-B3-STAMP-R20
