# IC1CFR-STOPGAP TODO r2 adversarial review — Codex
task-id: `IC1CFR-STOPGAP-TODO` | date: 2026-07-14 | basis: SPEC v1.0 Frozen + TODO r2 + T-S1~T-S8

結論: REJECT。原 5B 中 T-S1/B1、T-S3/B3 已關閉；T-S2/B2、T-S8/B4、T-S7/B5 未完全關閉，另有 1 個新 BLOCKING。

1. **B1（T-S2）sanitizer 仍不可按 scope/逐掛點驗收**（TODO:7,41-44）。「momentum-side 純函式」仍未指定新檔路徑；執行端合約禁止自行選 scope。且稱「逐掛點具名」卻只列 cache/raw JSON/export_all/CSV/idempotent，漏 service `_serialize_deep_report`、兩處 task storage + `get_deep_analysis_result`、AI JSON、Markdown 的具名斷言。須指定 sanitizer 檔案，並讓 §0 七類掛點每類至少一個可定位測試（storage/get 可合併一條完整 round-trip）。
2. **B2（T-S8）baseline nodeid 仍沒有機械 gate**（TODO:20,26）。目前只有 `pytest ... -q` 加集合包含關係的文字；既有紅時 pytest rc=1，沒有產生 post nodeid、解析 failed+collection-error、與 baseline 做 subset 並以差集決定 exit code 的命令/flag。須在 freeze/check 腳本提供明確 `--baseline-nodeids`/`--check-nodeids`（或等價命令），且 B0/B2 使用完全相同 suite/收集規則。
3. **B3（T-S7）direct allowlist 漏現存 factory constructor**（TODO:26,48-50）。實跑 `rg -n "FactorReturnAnalyzer\(" momentum api scripts tests` 除 orchestrator、phase24、待 quarantine tmp 外，還命中 `momentum/factories.py:454` 的必要 `return FactorReturnAnalyzer(...)`；r2 明列 direct allow 只有 orchestrator+phase24，守衛會對未改 repo 自紅，或迫使執行端自由校準。須明列允許 `momentum/factories.py:454`（或明定 scanner 排除 factory 定義體），並讓 B0 artifact 與測試使用同一正規化規則。
4. **B4（新洞）前端 gate 實跑零測試**（TODO:20）。實跑 `npm --prefix frontend run test -- "NetIC|FactorReturn|FactorEquity"` → Vitest v4.1.5 把整串視為 literal file filter，`No test files found, exiting with code 1`。須傳三個獨立檔案/filters，並明列將新增的 FactorReturn、FactorEquity test 檔路徑，確保 M3/M4 真被選中。

已關閉: T-S1 canonical artifact/hash 分離且不剔 FR 本體；T-S3 M3→FactorReturn、M4→Equity 且追溯同步；T-S4/T-S5/T-S6 文字均已落點。
非阻塞: canonical 排除仍有「等漂移欄」字樣，實作時宜凍成精確 JSON-path allowlist，避免廣義 key-name 刪除資料計數。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、Frozen SPEC、TODO r2、reconcile、r1 Codex review；以現碼核對 cache/API/reporter/caller/type/chart 掛點。
TESTS_RUN: `npm --prefix frontend run test -- "NetIC|FactorReturn|FactorEquity"` → FAIL, no test files, rc=1；`rg` caller 掃描確認 factories.py:454/orchestrator/phase24/tmp 命中；未跑會寫 baseline/cache 的 backend suites（唯讀限制）。
FAILURES_SEEN: 前端驗收命令 rc=1（計畫 gate 缺陷，未改 repo）。
SCOPE_CHANGES: 僅新增本檔；未改 HANDOFF.md、docs、runtime、tests、data_cache；REJECT 故未追加 RECONCILE-STAMP。
NUMERIC_OR_SCHEMA_IMPACT: none（文件唯讀審查）。
TODO-REVIEW-R2: REJECT(4 BLOCKING)
