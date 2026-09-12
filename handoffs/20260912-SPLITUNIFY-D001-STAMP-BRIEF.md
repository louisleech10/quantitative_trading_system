# SPLITUNIFY D-001 戳記輪（三家全員；對定案版本重簽）

brief-kind: closure
task-id: 20260911-SPLITUNIFY-X-STAMP-R6
findings-round: STAMP

🔴 **這是戳記輪：只讀、只核可或只拒簽。禁改碼、禁動 tracked 檔；禁在本 repo commit／push；禁跑 `tests/governance` 全套。** 隔離實驗之指令列與暫存路徑**不得含任何委員家族名稱**。

## 背景

D-001 規格階段已於 R13 收斂：**兩家皆 `proceed` 且零實質 finding**，並各自完成九輪收斂檔之逐條保全性對照與四閘構造題否證。歷輪戳記因規格續有修訂**皆已失效**，本輪對**定案版本**重簽。

收斂檔：`handoffs/reconcile/20260911-splitunify-x-review-r13/synth.md`
規格：`docs/SPLITUNIFY_SPEC.D-001.md`

## 範本

**全文照做** `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical finding 四欄（`**斷言**`／`**碼證**`／`**來源摘要**`／正文）、heading ID 文法、末段 `VERDICT`／`BLOCKED-BY`／`CLOSED` 三行機械塊、以及 P0／P1 之「修法必填且須附該修法自身之可行性證據」條款。蓋章情形無 finding 時，以 sentinel `## <FAMILY>-STAMP-P3-00` 收斂，正文寫明蓋章依據。

## 🔴 你要做的事

1. 讀 R13 收斂檔（群集表、本輪程序記錄、逐字附錄）與現行 `docs/SPLITUNIFY_SPEC.D-001.md`。
2. 自行實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-x-review-r13/synth.md`，確認與下列值相符：

   `e3f2847d7faeea35a4b61b297c2c3ac035026cf99b058458aa4de224566bb0c0`

   🔴 **不符即不得蓋章**，請改為拒簽並指出差異。
3. 在你的交件檔輸出**逐字**一行（`<家族>` 換成你自己的家族名，小寫）：

   `RECONCILE-STAMP: <家族> APPROVED 2026-09-12 sha256:e3f2847d7faeea35a4b61b297c2c3ac035026cf99b058458aa4de224566bb0c0 task:20260911-SPLITUNIFY-X-STAMP-R6`

   🔴 `sha256:` 必須是你**自己實跑**的輸出，不得抄貼本文、不得寫 `PLACEHOLDER`（本票曾出現一份 `PLACEHOLDER` 戳記，屬無效）。

## 🔴 必答（蓋章前必須各給一句立場）

1. **body hash 是否相符**？附你實跑的輸出。
2. **收斂檔之群集表與處置，是否忠實反映你本家在 R13（及先前各輪）之立場**？若你認為某條處置扭曲或弱化了你的意見，**拒簽並指名該條**。
3. **是否同意「規格階段可收、進 b8 實作」**？b8 之驗收面為 `M-SU-D1-01`～`23` 與 Task 8.1／8.2／8.3 之固定文法斷言。
4. **拒簽條件**：只要 ①hash 不符 ②群集表扭曲你的立場 ③你仍認為存在未閉合之 P0／P1 —— 三者任一成立即**拒簽**，並依範本開 finding（P0/P1 須附修法與該修法之可行性證據）。

## 交件格式

- 蓋章：上述 `RECONCILE-STAMP` 逐字一行。
- 拒簽：`## <FAMILY>-STAMP-P<0-1>-<NN>` 二級標題之 finding，四欄齊備。
- 末段三行機械塊：`VERDICT: proceed|blocked`／`BLOCKED-BY:`／`CLOSED:`（無內容留空，不得寫 `none`）。
- 完成訊號**逐字** `STATUS: DONE`。

## 前提

fact-verified: R13 兩家皆 proceed 且零實質 finding → `handoffs/reconcile/20260911-splitunify-x-review-r13/synth.md` 群集表 W1／W2
fact-verified: R13 輪債已清 → `debt_clear.sh --round-id --session` rc=0
fact-verified: 規格之格式、範本、歸戶、交叉引用與義務區塊結構閘皆 rc=0 → `doc_format_precheck.sh`／`template_check.sh dext`／`reconcile_cluster_attribution_check.sh`／`spec_xref_check.sh --synth`／`obligation_block_check.sh`
fact-verified: 歷輪戳記已失效 → 規格於 R13 後仍修訂兩處引用漂移，body hash 已變動
assumed: 收斂檔忠實反映三家立場 → 否證觀測：必答 2 指名被扭曲之條目／我跑了: 主委自校一遍，但**自己寫的自己校有盲點**，故以本輪為獨立驗證

## ⚠️ 前置

禁改碼；只讀；收尾清 /tmp workdir（保留 `claude-501`）。
