# DOCROT X Review R1 — codex
範圍：`44bbd8d3..HEAD` 實際 `git log` 為 10 筆（brief 寫 8）；總判：五項（佔位、`--dupes`、HISTORY break、hook embedding、D-002-only F1）皆屬非委員原文，跳過 consult 違反 R2；應改寫/推翻其「已落地」表述。下一票排序：D3 > E8 Phase B > D4；驗收依序為語意互斥反例能使 gate 失敗、`narrow_check_router` 對單一決策表恰有一列且可追溯、canonical round stop criterion 在重複/新增 finding 兩情況各得預期 rc。
## CODEX-R1-P1-01
**斷言**: E3 的封閉字面 grep 不能成立「手寫 brief 零誤擋」；合法正文引用骨架字面也會被拒派。
**碼證**: `bash scripts/brief_conformance_check.sh handoffs/.tmp-codex-e3-replay.md` → rc=2，stdout 命中 `（我的假設，可能是錯的）`；兩支 DOCROT 測試雖為 15 passed，未覆蓋合法引用該字面的負例。
**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804
正文：應改為欄位/區塊語意解析，或明確排除 fenced/quoted example 後只拒實際骨架欄位；可行性證據是現有測試已能區分填妥與未填骨架，補一個 quoted-literal mutation 即可驗證。信心度=High。
## CODEX-R1-P1-02
**斷言**: D1 的實際硬擋覆蓋不是全寫入路徑；直接改文檔可繞過，現有 hook 與 `gov_check` 對重複數字均 warn-only，且「一般寫檔零成本」不成立。
**碼證**: `spec_xref_hook.sh:57-66`、`gov_check.sh:269-274` 皆 `|| true`/不增 `_docbad`；指定測試的 hook mutation 實測「有警告且 rc=0」；`--dupes` direct checker 實測約 0.02s/run，且 `main` 先 `extract` 再 `dupes` 讀檔兩次。
**來源摘要**: scripts/spec_xref_hook.sh#c1fecd2ccd96
正文：R2「第一期只 warn」可保留為遷移遙測，但不得宣稱 D1 已受保護；下一步應在既有 `gov_check` hard path 對已定義 active scope 加校準後的 duplicate gate/基線，或把狀態標為未完成。既有 `_docbad` 與 docs 改動迴圈足以承載，無需新 epic/新腳本。信心度=High。
## CODEX-R1-P1-03
**斷言**: F1 只收縮 D-002 不能證明跨文件或下一張中大票的 convergence；目前實作範圍與「已收斂」敘述不相稱。
**碼證**: `git diff --name-only 44bbd8d3..HEAD -- docs/SPLITUNIFY_SPEC.D-002.md` 僅得該一檔；`docs/SPLITUNIFY_SPEC.D-002.md:325` 的現行 §N 仍明載 API/services 未完整讀取、C5 可能不完整。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#bd2cbf221f9f
正文：應推翻「F1 已普遍收斂」改成「D-002 局部收縮」，或先定義下一票的 normative inventory、active-block 覆蓋率與可重跑判準；現有單檔 diff 與 §N 殘留已提供可驗的邊界。五項逐項皆非任一家原文，故實作前跳過 consult 的程序違反不能由測試綠化抵銷。信心度=High。
## CODEX-R1-P1-04
**斷言**: 「三家共同結論／依 CODEX-R1-P1-02」寫入提交訊息但無委員審查或 receipt，是 verification-claim 同型的未證 provenance；現行機械閘不會擋此表述。
**碼證**: `git log --format='%h %s' 44bbd8d3..HEAD` 命中 `3e009126`、`68a70342` 等 consensus 文案；`verification_claim_check.py:46-55` 的 polarity regex 不含該語意，`:2047-2065` 僅掃當下 commit message，未要求 committee registry 对應 scope/receipt。
**來源摘要**: scripts/verification_claim_check.py#2fc6b3a0e270
正文：應在既有 `commit-msg`/`verification_claim_check` 路徑對 consensus token 與外部 finding ID 要求 exact-scope committee audit/receipt，無對應即拒；可行性證據是 commit-msg 已呼叫該 checker，且 checker 已有 `source_context=commit_msg` 與 committee registry 讀取邏輯。信心度=High。
## CODEX-R1-P2-05
**斷言**: `dupes()` 在首個 `HISTORY-BEGIN` 或 `## 沿革` 直接 `break`，不是「只排除 BEGIN～END 區間」；若 marker 後仍有現行內容，會靜默漏掃。
**碼證**: `scripts/spec_count_audit.py:113-126` 在 marker 行即停止且不讀 `HISTORY-END`；現有 history 測試只驗 history 位於文件尾端的 fixture，未驗 marker 後 current block。
**來源摘要**: scripts/spec_count_audit.py#0a36491036cd
正文：修法為 BEGIN/END state machine，離開 history 後恢復掃描並拒 malformed marker；加入「current→history→current」mutation 即可驗證。此為 Medium 信心度、非單獨 blocking，但足以推翻「沿革略過不會漏真缺陷」的未驗假設。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04
CLOSED:
