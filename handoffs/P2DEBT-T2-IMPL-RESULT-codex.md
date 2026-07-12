# RESULT — p2debt-t2

STATIC_CHECK=PASS
RUNTIME_CHECK=FAIL
MUTATION_CHECK=PASS
RECEIPTS=["handoffs/run_receipts/20260711T120742Z-p2debt-t2-unit.json","handoffs/run_receipts/20260711T120746Z-p2debt-t2-mutation.json","handoffs/run_receipts/20260711T120842Z-p2debt-t2-isolation-inventory.json"]
OPEN_PENDING=["p2debt-t2-final-all-orchestrator","p2debt-t2-final-digest-orchestrator","p2debt-t2-scope-concurrent-artifacts"]

## 摘要

- Phase 1：S1–S11 process-global redirect、plugin、root fixture registration、39-test unit/mutation/completeness gate 已實作。
- Phase 2：IC/API/ML/FF markers、API session/module setup lifecycle、S9/S11 wiring、AST inventory 已實作。
- Phase 3：selectable digest harness、Golden A/B/C test、I1–I3、hermetic mutation 已實作；完整 polluting acceptance 未在 sandbox 內完成。
- Phase 4：manual context manager 與 GEN-01..04 bracket 已實作；content gate `c_gen=4 c_overlap=2 expected_overlap=2`。

## Receipts / commands

- `p2debt-t2-unit`: `39 passed`, rc=0, receipt `20260711T120742Z-p2debt-t2-unit`。
- `p2debt-t2-mutation`: `1 passed`, `MUTATION_CANARY=1`, rc=0, receipt `20260711T120746Z-p2debt-t2-mutation`。
- `p2debt-t2-isolation-inventory`: `16 passed`, rc=0, receipt `20260711T120842Z-p2debt-t2-isolation-inventory`。
- B2 combined unit+inventory：`43 passed`, rc=0（未以 receipt wrapper 執行）。
- 靜態：`bash -n scripts/run_ic_persist_hermetic.sh` rc=0；decoupling count=0；`git diff --check` rc=0。

## Failures / delegated

- B1 第 1 輪：S9 import 觸發 Binance ping，`5 failed,19 passed,15 errors`; allowed test setup 補 `Client.ping` stub 後第 2 輪 `39 passed`。
- Mutation 第 1 輪：相對 path 在 sacrificial cwd 正確 pass-through；改用 sacrificial absolute production prefix 後 `1 passed`。
- `DELEGATED-TO-ORCHESTRATOR`: `bash scripts/agent_preflight.sh`（>60s 無輸出，Codex rc=130）。
- `DELEGATED-TO-ORCHESTRATOR`: `bash scripts/run_ic_persist_hermetic.sh --set V1`（>60s；前 8 cases 顯示 tmp redirect，cut1 golden 未完；不得視為 PASS）。
- `DELEGATED-TO-ORCHESTRATOR`: `bash scripts/run_ic_persist_hermetic.sh --set V2`（>60s；第一 materialize test 未完；不得視為 PASS）。
- `DELEGATED-TO-ORCHESTRATOR`: `venv/bin/python scripts/run_with_receipt.py --claim-id p2debt-t2-impl-final -- bash scripts/run_ic_persist_hermetic.sh --set all`（V1/V2 已證實超過 sandbox 60s，未執行/無 receipt）。
- `DELEGATED-TO-ORCHESTRATOR`: final per-file digest command over 11,007 files（>60s，rc=130）；因此 repo `data_cache` 最終 byte-identical 尚未驗證，不作 PASS claim。
- scope exact gate rc=1：除 27 implementation deltas外，多出 mandated receipt/audit 7 files及並行出現的 T3 handoff 3 files；未刪改他人檔。

## Files changed

- TODO whitelist 全 29 檔（其中兩個 cut1 generator 為 pre-dirty overlap）；另依使用者要求產生本 RESULT 與 3 組 receipt JSON/log。
- 未修改 `momentum/`、`api/` production code；未改 root `HANDOFF.md`；未 commit。

ASSUMPTIONS_VERIFIED: process-global gate 跨 asyncio.to_thread；nested reject；S1–S11 completeness；S2/S10 subtargets；non-opt-in subprocess activation_count=0；manual overlap 4/4、2/2
TESTS_RUN: receipts 如上；B2 43 passed；static gates rc=0；V1/V2/final digest timeout 未完成
FAILURES_SEEN: Binance import ping、sacrificial mutation path，皆於兩輪內修正；V1/V2/digest 為 sandbox timeout 未宣稱修正
SCOPE_CHANGES: implementation 未越 TODO whitelist；required receipts/RESULT/handoff 為合約產物；並行 T3 artifacts 導致 raw scope gate rc=1
NUMERIC_OR_SCHEMA_IMPACT: none；未改 production 數值/schema/輸出大小

STATUS: BLOCKED — final hermetic all receipt、final 11,007-file digest 與 raw scope gate 尚未通過

## Chair-finding C-1 fix

- Fix：`scripts/run_ic_persist_hermetic.sh` V1 skip whitelist 由不存在於 `pytest -q -ra` summary 的函式名，改為穩定 reason token `RUN_IC_E2E_PERF`。
- V7 audit：現行規則已用 summary 中的檔名 `tests/test_feature_factory_e2e.py` + reason phrase，不依賴函式名，未改。
- Polarity command：從腳本抽出 `assert_skips_allowed`，以 `/tmp` report 注入真實 perf summary，再注入額外非白名單 skip；輸出 `POLARITY_LEGIT_RC=0`、`SKIP_WHITELIST_FAIL[V1]=1`、`POLARITY_EXTRA_SKIP_RC=1`，總 rc=0；臨時檔已刪。
- V1 direct observation：`bash scripts/run_ic_persist_hermetic.sh --set V1` 在合法 perf skip 後未出現 whitelist fail，但整組 >60s，停於 golden case，已 Ctrl-C；不宣稱 PASS。
- Final command：`venv/bin/python scripts/run_with_receipt.py --claim-id p2debt-t2-impl-final2 -- bash scripts/run_ic_persist_hermetic.sh --set all; echo RC=$?`；V1 >60s，依派工規則 Ctrl-C，wrapper rc=1，未產生完成 receipt，V2/V5/V6/V7 未跑。
- DELEGATED per-set：`bash scripts/run_ic_persist_hermetic.sh --set V1`；chair 完成後再以指定 final command 跑 V1-V7。
- Files changed：`scripts/run_ic_persist_hermetic.sh`、`handoffs/P2DEBT-T2-IMPL-RESULT-codex.md`；未碰 redirect fixture/production/data_cache，未 commit。

ASSUMPTIONS_VERIFIED: pytest skip summary 含 RUN_IC_E2E_PERF reason；V7 使用 summary 可見識別；V1 gate 雙極性 rc=0/1
TESTS_RUN: bash -n rc=0；polarity command rc=0；V1/full acceptance 均 >60s 中止，未宣稱 PASS
FAILURES_SEEN: C-1 已修；Codex sandbox 長測試 >60s，完整 acceptance 委派
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: BLOCKED — DELEGATED V1/full hermetic acceptance 需 chair 代跑

## C-1 second fix

- Diff：`scripts/run_ic_persist_hermetic.sh` 的共同 skip 擷取由 `rg 'SKIPPED'` 收斂為 `rg '^SKIPPED \['`；V1、V7、else 三分支因此只接收 pytest short-summary 行，既有 V1 `RUN_IC_E2E_PERF` 與 V7 file+reason whitelist 保留。
- 合法極性（`/tmp/p2debt-t2-legit-report.txt`）：同時放入 live-progress 行與 `SKIPPED [1] ... RUN_IC_E2E_PERF ...` summary；實跑相同 anchor+V1 reason filter，`LEGIT_CAPTURED_LINES=1`、`POLARITY_LEGIT_RC=0`。
- 違規極性（`/tmp/p2debt-t2-extra-report.txt`）：在合法內容後注入 `SKIPPED [1] tests/momentum/test_unexpected.py:99: maintenance window`；`EXTRA_CAPTURED_LINES=2`、`POLARITY_EXTRA_SKIP_RC=1`。兩個 `/tmp` 報告於驗證後刪除。
- 語法：`bash -n scripts/run_ic_persist_hermetic.sh`，rc=0。
- Full re-run：DELEGATED TO CHAIR；依派工指示未嘗試 `bash scripts/run_ic_persist_hermetic.sh --set all`（Codex sandbox 已知 >60s hang）。
- Files changed：`scripts/run_ic_persist_hermetic.sh`、`handoffs/P2DEBT-T2-IMPL-RESULT-codex.md`；未碰 `data_cache/`，未 commit。

ASSUMPTIONS_VERIFIED: pytest live-progress 行不以 `SKIPPED [` 起首；summary 行以 `SKIPPED [` 起首；V1 合法/非法 skip gate 極性為 rc=0/1
TESTS_RUN: `bash -n scripts/run_ic_persist_hermetic.sh` rc=0；`/tmp` 雙報告 anchor+reason-filter polarity rc=0（合法 gate=0、額外 skip gate=1）
FAILURES_SEEN: first C-1 reason-only fix 在 live-progress+summary 混合輸出下不足；本次以 summary anchor 修正
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: BLOCKED — full hermetic all re-run DELEGATED to chair
