# CODEX-R1 SPLITUNIFY B9 審查交件
範圍：D-002 §P/§V/§N、TODO §B9A–B9F/§C-9、本輪指定 diff；SPEC body hash 實跑符合 brief，SPEC APPROVED；TODO/C9 因下列 P1 缺口 blocked。

## CODEX-R1-P1-01
**斷言**: ORCH 活文仍以兩家族規定大型 adversarial，與 §1 三家現行分工衝突。
**碼證**: CODE-ANCHOR: docs/MULTI_AGENT_ORCHESTRATION.md:193-194
MUTATION: 以此兩行作大型任務派工依據會漏派 Grok，quorum 與流程規定不一致。
**來源摘要**: docs/MULTI_AGENT_ORCHESTRATION.md#e7239f8a774b (sha256)
正文：Q(1a) SPEC 語意可 APPROVED；Q(1b) 最可能的 Task9.1 red 是返回形狀與 pipeline.py caller 的契約，應改 code 不改 SPEC。應改為指向 §1 現行分工行。Q(2a/2b)：9.3∥9.4 可合併成一個 review gate（5 gates），在 B9D/E 以 shared test_splitunify_derive.py 的 rebase/驗收觀測發現分拆無益；Q(6a)：待本輪文件缺口修正且三家 stamp rc=0 才可動 9.1。
## CODEX-R1-P1-02
**斷言**: §C-9 的 34 條 mutation 只有 25 個完整 token，9 個以裸數字縮寫，機械覆蓋不可證。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:581
MUTATION: 對 §C-9 執行 `M-SU-D2-\d{2}` extractor 得 FULL_ID_COUNT=25、缺 15/17/22/24/28/29/30/33/34。
**來源摘要**: docs/SPLITUNIFY_TODO.md#94c6aa2eb64c (sha256)
正文：9 個語意上分屬 9.2b（15/22/24/30）及 9.5（17/28/29/33/34），故 4a 無語意落單、4b 只需把縮寫補成完整 ID；修後機械 union=34。
## CODEX-R1-P1-03
**斷言**: Task 9.4 的兩個 TS 行號且其語意落點錯誤，會漏掉事件摘要的型別面。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:636-640
MUTATION: 只改 frontend/src/lib/types.ts:1582/2257；實際為 CPCVPathResult/MarginalICResult，EventAnalyzeResponse.summary 仍是 Record<string, unknown>。
**來源摘要**: frontend/src/lib/types.ts#e283b4ebba1c (sha256)
正文：實跑行號為 n_train/n_test 在 :1582–1583、:2257–2258，兩處均非事件批型別；正確落點應明列 EventAnalyzeResponse.summary（:3175）或新增事件摘要型別。六支既有前端測試行號均實存且吻合；9.3 新測試檔則目前缺檔但 TODO 已明示須新建。
## CODEX-R1-P1-04
**斷言**: C9 未把 staged strict-xfail 及 9.3 register rescan 的可稽核輸出／node id 寫成機械驗收項。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:590-616
MUTATION: 刪除 9.2a xfail 測試或省略 register rescan receipt；現列命令仍可由既有檔案級 rc=0 取得，無法證明兩項要求。
**來源摘要**: docs/SPLITUNIFY_TODO.md#94c6aa2eb64c (sha256)
正文：5a 接受 strict=True；現行 split_projection.py:530-553 仍逐 cutoff 判側且無異側 AlignmentViolationError，fixture 修正後仍不會意外 XPASS。5b 應將 xfail test node 明列於 9.2a，並為 9.3 指定 receipt path（如 handoffs/run_receipts/...-task-9.3-register-rescan.txt）。3a 未有專名承接的 ASSERT 是 G-4d②/③、G-4e 三者全等；3b 的 clusters remain event-level、purged/assignments disjoint、composite-key error message 應補 §V，xfail bridge/legacy duplicate guard 可留 TODO 細節。6b 已查 current blocks、paths/anchors、87 passed、mutation 25/34、active family grep。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04
CLOSED: 2026-09-13
