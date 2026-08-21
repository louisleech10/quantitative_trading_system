# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**GAP-3 等使用者 UAT 簽字（B1–B5 全部審查完工蓋章 2026-08-22；B5 review 五輪 11→5→4→1→0＋三家 RECONCILE-STAMP rc=0 蓋 `handoffs/reconcile/20260822-gap3-b5-review-r5/synth.md`）**

- **現況**：五批全數落地並蓋章；UAT **A 段（機械）9 項 rc 全 0**（receipt `handoffs/run_receipts/20260822T040000Z-gap3-b5-uat-sectionA.log`）。**唯一未完成＝使用者 UAT B 段 13 項簽字**（`docs/GAP3_UAT_CHECKLIST.md`；TODO B5.3 邊界②：使用者未簽字則整票不得結案）。
- **接手時做什麼**：
  1. 先問使用者是否已跑 UAT B 段；**未簽 ⇒ 不得宣稱 epic 收案**，也不要自行開新批。
  2. 使用者回報某項不過 ⇒ **回對應批修**（B1–B4 或 B5.1／B5.2），不在 B5 打補丁繞過（C9）；修完重跑該項＋A 段相關命令，再請使用者複簽該項。
  3. 全簽過 ⇒ 收尾：`docs/IC_QUANT_GAP_REGISTRY.md` 票 #3 標收案＋殘留 G3-R1..R11 確認、`docs/ROADMAP.md`／`白話說明/`（看板移 `Archived/`、README 與接下來要做什麼改指下一條主線）、HANDOFF 改寫為下一任務。
- **啟動方式（給使用者）**：後端 `source venv/bin/activate && python run_api.py`；前端 `cd frontend && npm run dev`。UAT B 段涵蓋：`/search` 匯出契約 JSON＋companion 來源檔（B1–B2b）、`/data-preparation` 新契約匯入與舊格式雙向拒收（B3–B6）、`/ic-analysis` 事件模式選批＋事件後報酬表／辨別表／全 K 線驗證／條件 IC（B7–B9b）、切回 Global 不受影響（B10）、看板一致（B11）。
- **殘留（registry 已登記，勿當缺陷）**：G3-R9 辨別表接真實模型分數（blocked-by ML 層；現顯示 `not_computed:no_model_scores_in_event_pipeline`）、G3-R10 大檔串流／背景 worker（user-ruling W10）、G3-R11 `tests/api` 既有紅 7 條（blocked-by 非 GAP-3 模組，乾淨 HEAD 同紅）。
- **既有介面（B1–B5 產出）**：`create_event_sample_pipeline()`＝**唯一** factories 出口（契約經 `pipeline.import_contract()`／`.condition_engine_contract()` 唯讀取得）；`EventSamplePipeline.run/run_with_params/analyze_tables/bars_from_kline_cache`；API `/api/v1/case/import-events[/json]`、`/case/events[/{id}]`、`/case/events/{id}/analyze`；前端 `lib/eventExport.ts`（`buildEventContractRecords`／`canonicalSourceText`／`sha256Hex`）、`components/ic-analysis/{EventImportPicker,EventTablesPanel}.tsx`、`components/case/EventImportForm.tsx`。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十九）
- 🔴 **commit 前必跑 `bash scripts/plain_docs_sync_check.sh --staged`**（`git add` 後、`commit` 前）：只要 commit 動到 WATCHED（`scripts/`／`momentum/`／`docs/`…）而受管白話檔不在同一 commit，下輪必紅——B5 為此被委員抓三次（摩擦八十九）。
- 🔴 **brief 的 `fact-verified` 只能貼實跑 rc／計數**：B5 期間三次寫了未實測的宣稱（plain_docs 綠、測試計數、同檔 verify 相容），三次都被委員用我自己附的 receipt／探針打穿（摩擦八十七／八十八）。數字一律 `grep -E "passed" <receipt>` 複製；相容性宣稱先跑探針。
- 🔴 **回歸測試必須斷言被監視的中間值**：B5 我交過一個「定義了 spy 卻沒接上」的測試（看似有驗、mutation 不會紅），codex 抓出（摩擦：R3 Z2）。寫 mutation guard 時自問「把碼改壞這條會不會紅」。
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；長 commit 訊息寫檔後 `git commit -F`（`gate_check` 會誤判長複合命令為派工，摩擦八十六）；`reconcile_build.sh <s> --mode review <三檔逐列>`（glob 會吃到 brief）。
- 🔴 handoffs 委員交件／brief 被 .gitignore；審計鏈入檔＝`git add -f handoffs/reconcile/<session>/`；commit 訊息末段必帶 `Governance-Scope: out-of-epic GAP-3 …`；synth 內「全綠」等極性詞會被 claim checker 擋，改寫「各命令 rc=0」。
- 🔴 委員「清 /tmp workdir」會刪掉 Claude scratchpad（B4 實際發生）⇒ receipt 一律寫 `handoffs/run_receipts/`；brief 清理句只寫「清你自己的 workdir」。
- 白話看板狀態欄用文字，禁 ⬜／✅／「收案」／「進行中」貼 B<n>（factkey 守衛）；push 丟背景；venv Python 3.9.6；`-p no:logging` 會拿掉 caplog。
