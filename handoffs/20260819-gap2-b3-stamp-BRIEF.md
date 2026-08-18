# GAP-2 B3 code review 收斂檔之 RECONCILE-STAMP 核可（含 M1–M6 修補落地之機械核可）

VERIFY-EXEMPT:doc-example:gap2-b3-stamp-brief-criteria

> 本檔為**給委員的核可判準清單**：各判準是「請你實測的項目」，不是主委的 operational 結論。
> 🔴 **所有實驗一律 in-memory（monkeypatch／exec）；禁寫任何 repo 檔**；探針有互斥鎖（rc=3 ⇒ 稍後重試或讀 receipt）。主委派出後不動工作區。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`005f5472f32e2ed8550b89696b7ead659e6e481c969f397e1ab0c0ea250fe6c5`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
B3 code review（`20260819-GAP2-B3-REVIEW-R18`）三家 10 findings（codex 8／composer sentinel／grok sentinel）收斂為 M1–M7；修補已落在 commit `bfe4da99`（延伸檔 A1-9）。本輪戳記**兼任修補驗收**：通過即 B3 CLOSED → B4。

## 核可判準（逐項查；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b3-review-r18/sources.lock` → PASS；七群集引用全部 10 個 canonical ID。
2. **M1（P0）**：`git show bfe4da99 -- momentum/Analysis/survivor_contract.py`——validator 對 `provenance.fit_mode` 只驗非空字串；**用 codex 反例重跑**：`fit_mode="train_mask"` 之 build→validate 不 raise（`test_provenance_fit_mode_raw_orchestrator_values_accepted`）。
3. **M2**：`resolve_ref` 對絕對路徑／`..`／逃出 root 之 ref raise（`test_resolve_ref_rejects_escape`；**用 codex 之 ABSOLUTE_REF 反例 in-memory 重跑**）。
4. **M3**：(a) event 物件 `mode="timestamps"` 但 hash／計數 null ⇒ raise（codex INCOMPLETE_EVENT 反例）；(b) 無 split 且缺 `full_index` ⇒ raise；有 `full_index`（timestamp index）⇒ `row_identity` 用真實 index（≠ arange）；(c) `root_analysis_status="unexpected_status"` ⇒ raise。
5. **M4（部分接受）**：`n_samples=1` ⇒ raise；`n_samples=6000`（> train+test=5000，purge／embargo 情境）⇒ 合法；marginal `n_test` ≠ split `test_rows` ⇒ raise。**請判**：主委對 codex「exact 一致」改採 `≥`＋test 列 exact 之理由（purge／embargo）是否成立；若你認為 total 也應 exact ⇒ BLOCKED 附理由。
6. **M5／M6**：⑭ checklist 含 `n_samples_total`／`n_samples_test`／`feature_name`／composite／removed／view 巢狀；⑩ tamper 含 `removed_candidates[z]` 與 composite 物件層；⑱ naive 字串同 hash。
7. **未破壞既有**：`venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → 44 passed；`tests/momentum/Analysis/test_ichc_contract_sync.py` → 5 passed；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` → PASS；receipt `handoffs/run_receipts/20260818T232727Z-gap2-B3-probe.log` 八條 RED（可自跑 `--batch B3`，<1 分鐘，勿並行）。
8. Verdict 與內文一致；`git diff 038fd10b bfe4da99 --stat` 之非 hook 產物只含 `survivor_contract.py`／測試檔／AMENDMENTS／handoffs／白話（`.claude/gate/audit.log`、`docs/site/*.html` 為 hook 產物）；契約 JSON 未動。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-19 sha256:<你實跑取得的完整 body sha256> task:20260819-GAP2-B3-STAMP-R19
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target；新缺陷寫在你自己的交件檔並判 BLOCKED。
3. 不得 commit、不得 push；禁就地改檔；探針勿並行。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋判準 1–8 逐項結果。收尾清 /tmp workdir（保留 claude-501）。
