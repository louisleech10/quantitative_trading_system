# GAP-2 B4 code review 收斂檔之 RECONCILE-STAMP 核可（含 N1–N2 修補落地之機械核可）

VERIFY-EXEMPT:doc-example:gap2-b4-stamp-brief-criteria

> 本檔為**給委員的核可判準清單**：各判準是「請你實測的項目」，不是主委的 operational 結論。
> 🔴 **所有實驗一律 in-memory；禁寫任何 repo 檔**；探針 `--batch B4` 約 20 分鐘且互斥 ⇒ **請讀 receipt 勿重跑**；`test_gap2_golden.py` 含 bench（~2.5 分鐘），可只跑 `-k "not bench"`；主委派出後不動工作區。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260819-gap2-b4-review-r21/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`969664ed8f7e400a619974c58d0bf9d949251b76b204b556de9485913d8971a8`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b4-review-r21/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
B4 code review（`20260819-GAP2-B4-REVIEW-R21`）三家 4 findings（codex 2 P1／composer sentinel／grok sentinel）收斂為 N1–N3；修補已落在 commit `e4e3bb97`（延伸檔 A1-11）。本輪戳記**兼任修補驗收**：通過即 B4 CLOSED → B5（前端）。

## 核可判準（逐項查；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b4-review-r21/sources.lock` → PASS；三群集引用全部 4 個 canonical ID。
2. **N1（落盤鏡像）**：`git show e4e3bb97 -- momentum/Analysis/ic_filter_orchestrator.py`——`_persist_outputs` 於五鍵注入後重存報告；**用 codex 反例重跑**（真實 fixture `run_analyze(sidefx_dir=tmp)` 後讀 `tmp/reports/ic_report_ic_gatekeeper.json`）⇒ `metadata.survivor_output` 五鍵存在且 == 回傳 report（`test_persisted_report_json_mirrors_survivor_output`）。
3. **N2（effective config）**：override `{"ic_calculation":{"methods":["kendall"]},"labels":{"return_type":"log"}}` ⇒ 倖存者檔 `provenance.ic_method=="kendall"`、`label_return_type=="log"`（`test_provenance_uses_effective_config`）。
4. **未破壞既有**：`venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` → 73 passed（約 6 分鐘；含 bench）；`bash scripts/mutation_probe_check.sh <三新測試檔>` → PASS；`bash scripts/ic_wiring_check.sh` rc=0；`venv/bin/python scripts/gap2_freeze_golden.py --check` → CHECK PASS（約 25 秒）。
5. **探針**：receipt `handoffs/run_receipts/20260819T011504Z-gap2-B4-probe.log` 七條 RED＋還原綠（修補後重跑）；**勿並行重跑**。
6. Verdict 與內文一致；`git diff ab53c24e e4e3bb97 --stat` 之非 hook 產物只含 `ic_filter_orchestrator.py`／`test_gap2_survivor_persist.py`／AMENDMENTS／handoffs／白話。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-19 sha256:<你實跑取得的完整 body sha256> task:20260819-GAP2-B4-STAMP-R22
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段（**請務必 append，勿只寫在交件檔**）；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target；新缺陷寫在你自己的交件檔並判 BLOCKED。
3. 不得 commit、不得 push；禁就地改檔；探針勿重跑。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋判準 1–6 逐項結果。收尾清 /tmp workdir（保留 claude-501）。
