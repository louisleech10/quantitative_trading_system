# CODEX R12 — SPLITUNIFY D-002 唯讀閉合審查
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R12；family: CODEX；依 brief 與 SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT 執行。
R11 closure：CODEX-R11-P1-01 未閉合→本輪 P1-01；P1-02 register 缺漏已閉合；P1-03 座標契約已閉合；P1-04 仍受外部錨未具體化影響→本輪 P1-02。
N1 可實作性：producer→summary 在 EventSamplePipeline.run 可做，但 §V 同時要求 metadata 等值且 §N 將 metadata 列殘留，故部分採納、不誠實地宣稱整鏈完成。
N2 可實作性：register 29 條連續無重複；routes/services 掃描未見具名 split 計數模型，API 計數模型駁回成立；另見本輪 P2-01。
N3 可實作性：成立；split_per_symbol、ic_split_adapter、ic_filter_orchestrator 均在 validator 呼叫點持有 full ts/symbols 與兩個 plan，且 D-001-C2(4.10) 與四案真值表可遵守。
N4 可實作性：O_EXCL、外部錨、主檔 11-key guard 若均已落地，可擋同步改 v8/旁檔與主檔覆寫；但外部錨尚無字面，形成本輪 P1-02。
N5/N6：M-SU-D2-29 已指向新檔與三項 guard；M-SU-D2-03 已要求值等於 summary/producer；未見新增 mutation 字面問題。TODO §E 延後同步時點與 D-002 §N 明確一致。
分類檢核：矛盾=P1-01/P2-01/P2-02；E2E=P1-01；驗收可測=P1-02；quant=無新 finding；過度設計=無；OOM/parallel=無；cache=無；API/type=駁回成立；test=P1-01/P2-02；agent=可實作性如上；必要性/短命=無新 finding。
## CODEX-R12-P1-01
**斷言**：`metadata.split_unify` 等值斷言不能在 brief 指定的 `EventSamplePipeline.run` 入口執行；該入口只產生 `EventPipelineResult.summary`，而 metadata 產生點在另一條沒有 `discarded`/`build_event_keys` 的 IC 路徑。
**碼證**：`pipeline.py:693-768`（`run` 回傳 summary、沒有 metadata）；`rg -n 'build_split_unify_disclosure|split_unify' momentum/Analysis api` 只命中 `ic_filter_orchestrator.py:1530` builder；其呼叫僅傳 `n_test/test_timestamps/per_symbol_counts`；API AST 掃描輸出 `AST_RUN_CALLS=2`，僅 `uvicorn.run`、`asyncio.run`。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；momentum/Analysis/event_samples/pipeline.py#55ca7327764f；momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293；MAJOR 信心度=高；修法是把當輪驗收明確縮成 producer→summary，metadata 等值移至生產接線後的殘留驗收，或補一條真正承接 EventSplitPlan 的生產 handoff。
## CODEX-R12-P1-02
**斷言**：v12 的 (G-4d)(vi) 外部錨要求無法執行，因 SPEC §V 目前沒有首次 SHA-256 字面或精確 anchor 欄位，實作者無法完成「與 SPEC 所錨首次值比對」的母斷言。
**碼證**：`rg -n '[0-9a-f]{64}' docs/SPLITUNIFY_SPEC.D-002.md` 輸出空；`find tests/golden/splitunify -maxdepth 1 -name '*v8*'` 輸出空；`jq` 顯示現行主檔 11 鍵；但 `D-002:269` 要求與 SPEC §V 首次字面比對，`Task 9.5:252-255` 檔案清單也未納入 SPEC。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；scripts/freeze_splitunify_golden.py#e331623163d2；tests/golden/splitunify/splitunify_golden.json#f270e007ca98；MAJOR 信心度=高；修法是先定義不可改寫的 anchor 欄位/值、納入施工與驗收範圍，再讓 main 只讀該值；否則 M-SU-D2-33 的外部錨分支仍不可驗。
## CODEX-R12-P2-01
**斷言**：D-002 §C:155 仍把唯一 register 說成 25 條，與同文件標題、RISK、§R 及實際 29-row register 矛盾。
**碼證**：`awk`/`rg` 機械核對輸出 `C5_REGISTER count=29 expected=29 duplicates=none missing=none`；`D-002:155` 仍輸出「register 之 25 條消費面」，而 `:70,:90,:317` 均為 29。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；MINOR 信心度=高；修法是把 §C:155 的 25 改為 29 並移除舊 v11 註記，避免施工者依敘述漏改四個消費面。
## CODEX-R12-P2-02
**斷言**：若依 §V/§1.9 交付 metadata exact-key 擴充，Task 9.1 所稱「實際須改三處」不完整；若 metadata 確實殘留，則 §188/§259 的當輪 metadata 交付斷言又未被同步降級。
**碼證**：`D-002:190` 明稱實際三處；`momentum/Analysis/contracts/split_unify.json:49-55` 仍是五鍵；`tests/api/test_splitunify_disclosure.py:149-151,270-277` 對五鍵做 exact set；`D-002:259` 又要求 metadata 值等於 producer。**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#2780d73f7282；momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15；tests/api/test_splitunify_disclosure.py#f1bd211204f7；MINOR 信心度=高；修法是二選一寫死：補列 contract JSON 與 exact-key 測試為施工面，或把 metadata assertion/contract 變更完整移入 SU-RESID-9A-UI 殘留。
ASSUMPTIONS_VERIFIED: N1/N3/N4/API/register 假設均以指定路徑實讀、AST/rg/awk/jq 命令核對；D-001/golden/TODO §E 交叉檢核完成。
TESTS_RUN: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；兩份 `doc_format_precheck.sh` rc=0；D-002 `spec_xref_check --synth` PASS；register=29、mutation=33 均無重複/缺號；API AST `AST_RUN_CALLS=2`。
FAILURES_SEEN: 首次 `spec_xref_check` 少傳 target 僅印用法，未改檔；補正後 D-002 xref PASS；TODO target 的 xref FAIL 反映 §E 延後同步之既有狀態，已按 §N 判為非本輪新衝突；指定 completeness command 未啟動即被 PreToolUse 擋下（本輪 debt OPEN，無 rc），未以旁路執行。
SCOPE_CHANGES: 僅新增本交接檔，未改碼/SPEC/TODO；NUMERIC_OR_SCHEMA_IMPACT: 未改動，提出 P1/P2 規格修正建議；OUTPUT: `handoffs/20260911-splitunify-b9-review-r12-codex.md`
VERDICT: blocked
BLOCKED-BY: CODEX-R12-P1-01,CODEX-R12-P1-02
CLOSED: CODEX-R11-P1-02,CODEX-R11-P1-03
STATUS: BLOCKED — completeness_check exact command was preflight-blocked by OPEN debt; no rc was produced
