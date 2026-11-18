# TESTSEL I2 逐檔合回清單 — SPEC

> 來源大綱：`handoffs/20261116-testsel-route-outline.md`（I2；確認輪 `handoffs/reconcile/20261116-testsel-x-consult-r5/synth.md`）　|　日期：2026-11-16　|　對應 TODO：`docs/manifests/TESTSEL_I2.json`（本 SPEC 定稿後生成）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中（唯讀分類產出清單；不改程式；但清單決定後續 I3／I6 合回與撤除範圍）。
- **命中高風險原則**：(b) 清單涵蓋跨模組共用路徑（tests/conftest.py、scripts/gate 類、產品 5 檔）之去留判定。
- RISK-HIT: b

## §A 假設與待使用者確認（事故：拿推論代替問人）
- FACT-RECEIPT: `git -C .claude/worktrees/agent-a520620667770e1b9 diff --numstat main...HEAD | wc -l` → 印出 `302`（主委 實跑 2026-11-16）
- FACT-RECEIPT: `bash runs/testsel_route/i2_proto/attribute.sh .claude/worktrees/agent-a520620667770e1b9 | wc -l` → 印出 `193`（排除 handoffs/ 與 __pycache__ 之改動檔；主委 實跑 2026-11-16）
- FACT-RECEIPT: 同上輸出依提交主旨票別前綴計數 → 163 檔單一前綴、28 檔 2–3 種前綴、2 檔無規範前綴（`tests/feature_engineering/numview_helpers.py`、`tests/feature_engineering/test_l7_raw_streaming.py`）（主委 實跑 2026-11-16）
- 待確認：無

## §C 約束（不重抄，引用 + 只列本任務相關）
- 依 `handoffs/reconcile/20261116-testsel-x-consult-r1/synth.md` C3：逐檔逐段分三類（依段落實際行為，不依提交前綴）；tests/registry 不整包丟；conftest 合回時剝兩外掛行。
- 本任務**唯讀**：不改整合樹、不改 main 程式；I7e 全量期間不對整合樹寫檔。
- 清單為單一真相源：分類結果只存於 `runs/testsel_route/i2_mergelist.json`（schema 見 Task 1.1），本 SPEC 不列舉檔名清單。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| TESTSEL-I2-BUDGET-1 | 無重型跑（僅 git 讀取與 JSON 檢查） | 無 | 整合分支改動檔全集 | 秒級（原型 attribute.sh 實跑） | 無 |

## §B 四項平衡實測
- N/A：本項只產分類清單，不改計算路徑或使用者操作。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 1 — 清單產出與檢查（依賴：無；大綱確認輪已結案）
**Task 1.1 — 清單 schema 與產出**
- 目標：產出 `runs/testsel_route/i2_mergelist.json`。　檔案：`runs/testsel_route/i2_mergelist.json`（新建）、`runs/testsel_route/i2_check.py`（新建）　既有 caller／影響面：新建無 caller；I3、I6 讀此清單。
- **文件級身分（必填）**：`worktree`（整合樹 repo 相對路徑）、`main_sha`＝分類當下 `git -C <worktree> rev-parse main`、`base_sha`＝`git -C <worktree> merge-base <main_sha> <head_sha>`、`head_sha`＝分類當下 `git -C <worktree> rev-parse HEAD`。所有母體一律取自這三個固定 sha，不得取工作區或移動中之 `main`／`HEAD`；already-in-main 之依據一律以 `main_sha` 樹為準。
- **母體（兩層）**：檔案層＝`git -C <worktree> diff --raw -M <base_sha> <head_sha>` 之每一筆（含純 mode change、純 rename、空檔新增／刪除、二進位）；文字段層＝`git -C <worktree> diff -U0 -M <base_sha> <head_sha>` 之每個 `@@` hunk。
- **列（hunk 級，全部檔皆然）**：{path, hunk＝`git diff -U0` 之 `@@ -a,b +c,d @@` 標頭，或 `whole-file`（無 `@@` 之檔案層改動——mode change、純 rename、空檔新增／刪除、二進位——一律須 whole-file 列；有 `@@` 之檔亦可整檔一列）, class ∈ {revert-testsel, keep-owner, verify-product}, disposition ∈ {merge, drop, already-in-main, stop-and-review}, owner_ticket, reason, tests[]}。class 依**該段實際行為**判（提交前綴只作提示，不作分類依據）；disposition 定 I3／I6 如何處置；`stop-and-review`＝該段套用時衝突或語意不明，I3／I6 遇之停工回報、不得自創行為。
- **整類列（僅限兩類）**：`path_glob` 只允許 `handoffs/**` 與 `**/__pycache__/**`，每類一列、disposition 必為 `drop`；檢查器以此 glob 展開母體路徑並視為已覆蓋，其餘路徑不得用 glob。**更正（2026-11-18 I1 收尾）**：`handoffs/run_receipts/**` 為 main 追蹤之收據（測試硬依賴），**不屬** `handoffs/**` drop 之範圍——原「handoffs/ 不入 main 版控」之前提與事實不符，致合回漏帶 30 個新增＋1 個修改之收據（`test_probewinsor::test_fixedenv_refreeze_receipt_binds_baseline` 等紅；審碼 `handoffs/reconcile/20261118-testselreceipts-b1-review-r1/synth.md`），已自整合樹 0e624180 帶回；日後同類合回須將 `handoffs/run_receipts/**` 逐檔列 merge／already-in-main。**再更正（同日，審碼 `handoffs/reconcile/20261118-testselsha-b1-review-r1/synth.md`）**：合回為單親提交（d64efa9d），testsel 分支提交不在 main 歷史 ⇒ 以 testsel 限定提交作 git ancestry／歷史查找之收據於 main 失效；TESTREG 改寫收據 `handoffs/run_receipts/testreg-rewrite/test_timeout_registry-rewrite.json`（head a48f7615）經 `venv/bin/python scripts/testreg.py validate` 實得 V07「既有收據之 head 非 HEAD 之祖先」與 m1／m2／m3「session 不在 ledger」⇒ 須於 main 可達提交依 receipts.mutation 合約重跑三 mutant 與 compare 重建收據（不得只換 head 或放寬祖先檢查）；其餘帶回收據之 head 僅作來源紀錄、不作 ancestry 查找（test_icperf_study_receipts_fresh 9 passed、test_probewinsor 1 passed）。測試碼內寫死 testsel 限定提交者（test_framepath_disposition.py 9c930fbf、test_prod_writers_tmp_root.py 72258590）已改為 main 可達之等價提交。
- **tests 欄**：class ∈ {keep-owner, verify-product} 者 `tests` 必非空（nodeid 或測試檔）；revert-testsel 可空。
- **驗證（可證偽）**：`venv/bin/python runs/testsel_route/i2_check.py runs/testsel_route/i2_mergelist.json` rc=0，檢：①`git -C <worktree> rev-parse HEAD` == `head_sha` 且 `git -C <worktree> rev-parse main` == `main_sha`，且 `git -C <worktree> merge-base <main_sha> <head_sha>` == `base_sha`，任一不符 rc≠0（清單過期或祖先錯誤須重產）；②檔案層母體（`diff --raw -M`）每一筆（非 glob 路徑）被 ≥1 列覆蓋，無 `@@` 之檔案層改動須有 whole-file 列；文字段層母體（`diff -U0 -M`）每個 hunk 恰被一列覆蓋（whole-file 列覆蓋其檔全部 hunk）；③glob 列只出現於上述兩類且展開後涵蓋該類全部母體路徑；④class／disposition 值域合法、keep-owner 之 owner_ticket 非空；⑤keep-owner 與 verify-product 之 tests 非空，所列測試檔存在於 head_sha 樹，nodeid 形式者其測試函式名（`::` 末段去參數）以靜態搜尋存在於該檔；**「該測試確實覆蓋該段」機器不判，由 I3／I6 審碼判**。
- **邊界（≥2 具體場景）**：①tests/conftest.py：`pytest_plugins` 兩外掛行 ⇒ revert-testsel／drop；HERMETIC_ROOT、registry／storage 重導、CGSA 預設根、SEED、正式根寫入偵測 ⇒ keep-owner／merge（同檔同提交前綴亦須分列）；②純刪除檔、二進位檔 ⇒ whole-file 列；③某段 main 已含等效改動 ⇒ disposition=already-in-main 並於 reason 附 main 之檔:行。
- **存活至**：I3、I6 完成並合回 main 後即無用（清單非產品）。
- **覆蓋風險**：I1 於 I2 定稿後改整合樹 ⇒ head_sha 不符、檢查 rc≠0，須對新 head 重產並重驗（不沿用舊清單）。
- 不可做：不改任何被分類之檔；不建通用分類框架或自動歸類器（attribute.sh 僅為原型提示）。

**Task 1.2 — 檢查之改壞對照**
- 目標：證 i2_check.py 會抓到漏段、錯身分、濫用 glob、空驗收。　檔案：`runs/testsel_route/i2_check.py`
- 改法：以暫存複本之清單分別：刪一個 hunk 列、把某檔改為漏一段之部分列、改 head_sha 為他值、改 main_sha 為他值、改 base_sha 為他值（例：某較舊之祖先提交）、刪某無 `@@` 檔案層改動之 whole-file 列（母體無此類時以 `git diff --raw` 實例證明其存在與否並記錄）、加一條非允許類之 glob 列、清空某 verify-product 之 tests、將某 tests nodeid 改為不存在之函式名、塞非法 disposition；各應 rc≠0。
- **驗證（可證偽）**：十種改壞各 rc≠0，原清單 rc=0。
- **邊界（≥2 具體場景）**：①同一 hunk 重複兩列 ⇒ rc≠0（恰一列）；②glob 列 disposition≠drop ⇒ rc≠0。
- **存活至**：同 Task 1.1。
- **覆蓋風險**：無。
- 不可做：不擴為通用 schema 檢查框架。

## §V 驗證策略與邊界測試目錄
- mutation：見 Task 1.2（改壞對照十種）。
- 測試層級：本項為分類文件，驗收以 i2_check.py 之可證偽檢查；不新增 tests/ 下測試（清單非產品，合回後即棄）。
- 防假綠：i2_check.py 以 `git diff --raw -M <base_sha> <head_sha>`（檔案層）與 `git diff -U0 -M <base_sha> <head_sha>`（文字段層）當場取兩層母體，不以清單自身為母體。
- 邊界目錄：重複列、純刪除、二進位、already-in-main、身分過期（見 Task 1.1／1.2）。

## §R 回退
- 清單與檢查腳本皆在 runs/，不影響程式；整個 Phase 刪檔即回退。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- §G：N/A — 本項不改數值或特徵計算，只產分類清單。
- §B 四項平衡：N/A — 同上。
