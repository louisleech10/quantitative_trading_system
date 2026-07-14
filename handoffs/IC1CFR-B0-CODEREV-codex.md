# IC1CFR-B0 Code Review — Codex

- task-id: `IC1CFR-B0`; scope: Frozen TODO Task 0.1；唯讀審查（本檔為唯一產出）。
- verdict: REJECT（1 BLOCKING）。

## BLOCKING

1. `--check-nodeids` fail-open，且 collection-error regex 會把一般 test-level `ERROR path.py::test` 誤加成 file-level allowlist。`collect_pytest_failed_nodeids()` 在 pytest `returncode != 0` 且解析為空時僅 WARN 後回 `[]`（script:596-604）；`check_nodeids()` 將空集合視為 baseline 子集並 PASS（:620 起）。因此 pytest INTERNALERROR/中斷/exit 5 可假綠。另 :559 的 `(\S+\.py)\b` 會匹配 `path.py::test` 前綴；現 baseline 的 3 個 file-only path 與同檔 test nodeid 並存，未證為真 collection errors，且會豁免日後同檔新 collection error。B2 gate 必須保留 subprocess rc，非 0 且無可完整解析 failure/collection receipt 時 exit 1；file-level regex 必須排除 `::`，重建 B0 nodeids 後再審。

## 其餘指定項

- ① PASS：exclude 為完整 JSON-path 常數；`*` 只接受單一 numeric list-index，非廣義 key 刪除。獨立注入頂層 `generated_at` 不改 hash；注入 `report.results.factor_returns.generated_at` 會改 hash。
- ② PASS：未重跑 deep；以獨立 `jq del(精確 paths)` + stdlib sort-key dump 重算得 `2b6489daaeb92fad717c039fc6cd5d4414f7282b9543c3f27629416f73f512ca`，與 `before.sha256` 相同。
- ③ PASS：create symbol 拆字串且兩類掃描都明確排除 scanner self；factory 定義只從 caller 排除，direct 保留 `factories.py:454`。規則集中於 `normalize_factory_scan_hits()`，B0 writer 與未來 guard 可共用；artifact 與獨立 `rg` 現況一致。
- ④ REJECT：suite args 與 parser 在 B0/B2 確實共用；79 行為 76 個 `::` + 3 file-only，但上述 parser 使集合不可信且 gate fail-open。
- ⑤ PASS：`git diff --name-only -- momentum api frontend` 無輸出；指定 B0 內容只有新 script/handoffs artifacts，未見 runtime 變更。
- ⑥ PASS：`before.json` 中 `factor_returns` 狀態為 `completed`，有 4,298 個 finite numeric leaves；`total_execution_time_s=1.779752958` 與 error timestamp 原值仍在 artifact。strict-JSON sanitizer 只把 non-finite 轉 null，finite 對照未被 sanitize。

## Receipts / notes

- 實跑：`jq del(<10 個精確 paths>) before.json | python -S -c <sort_keys+sha256>` → hash match；同名 key path sensitivity probe → expected match/diff。
- 實跑：`jq '[.report.results.factor_returns|..|numbers|select(isfinite)]|length'` → 4298；`wc/rg` → 79/76/3；兩個 factory `rg` → artifact entries 一致。
- RESULT 的 CMD A raw hash `4fd711...` 與目前 artifact raw hash `c72dd1...` 不同，應是後續 canonical 重跑覆寫；canonical 相同，故列 receipt 精度 NB，不另計 blocking。

CODE-REVIEW: REJECT(1 BLOCKING)
