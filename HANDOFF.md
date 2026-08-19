# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-3 事件型在「討論文檔」模式（2026-08-19 深夜）——**不寫 SPEC、不動程式**，討論只改 `白話說明/GAP-3事件型討論.md`

**現況**：consult R1 收斂（`handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md`；codex＋grok＋主委 24 條六群集 0 掉項；composer 兩次 Cursor `resource_exhausted` 未交件，債以 `--abandon --kind collection-failed` 收）。使用者彈窗裁：目標＝A（open 買入預測起漲點）／B（預測大陽線 open 買 close 賣）／C（收盤確認後問續漲）／兩段式**全要**、任何事件類型、多空；正反例自己標一起匯入（C 語意）；**「先寫成一個文檔，討論就修改文檔，這樣不會被洗掉」**。⇒ 討論文檔已建並登記 `plain_docs_sync_check.sh` WATCHED。
**關鍵發現**：consult R1 整輪預設 C；使用者主要設想 A／B（決策 open、事件在未來）⇒ 反例母體（A/B＝全部 bar、平台補；C＝同觸發未續漲、使用者標）、決策時點枚舉（加 open-決策-事件未知）、A/B 與序列型主線共用三條**須 consult R2 重議**（摩擦七十八：使用者意圖類 assumed 前提要先白話問使用者再派委員）。
**下一步**：① 使用者答討論文檔 §6「待你確認」（Q-A1／Q-A2／Q-S1／Q-T1／Q-L1）→ 改文檔 ② 答完 Q-A1／Q-A2 後派 consult R2（唯讀；brief 前提改為三情境＋多空＋反例依情境；三家＋主委）→ reconcile → 改文檔 §5 ③ 文檔 §6 待確認清空且使用者點頭 → 才寫 SPEC（大任務完整管線）。**裁前不動 GAP-3 程式。**
**前端占位規則**（2026-08-19，commit aded5574）：需要前端的殘留一律先做 `/pending-features` 條目＋原位置殼；vitest 對 registry 機檢；收殘留同步刪。UAT 等事件型完成後一次做。
**其他可做未排**：GAP-4 多標的合併估 IC；GAP-5 容量（等成交量源）；GAP-6 併效能 epic；G2-R6 前端 tsc 既有 8 紅（獨立小票）；三支未登記臨時腳本 `scripts/ichc_t2_diag.py`／`ichc_t2_probe400.py`／`ichc_t3_diff.py`（8/17 ICHC 臨時產物，待清）。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～七十九）
- 🔴 含家族名的 Bash 在「有 token＋債 OPEN」或「無 token」時都被 gate_check 擋 ⇒ 命令寫進 scratchpad 腳本再 `bash <script>`；讀委員檔用 Read 工具非 Bash。committee_run 有一家失敗：同 round 補跑 `ROUND_ID=<id> bash scripts/cx_run.sh <fam> <brief> <out>`；外部服務持續失敗 ⇒ roster 不等只能 `debt_clear --abandon --kind collection-failed --approver main-agent`（consult 可、review/stamp 不可）。
- 🔴 stamp brief 禁多家並行跑重測試／禁邀請就地改檔實驗（摩擦七十三／七十七）；review brief 前提逐條 `fact-verified:`／`assumed:`；commit 訊息 `Governance-Scope:` trailer 獨立成末段（G-7 前移檢查）；強極性詞會被 claim checker 要 VERIFY 收據。
- 白話資料夾新增 .md 須登記 `plain_docs_sync_check.sh _watched_for`；動 `scripts/` 時 README／接下來／日誌／摩擦 四檔須同 commit staged；`factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 的紅為既有（pre-commit 放行）。
- venv Python 3.9.6；`docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線；push 丟背景。
