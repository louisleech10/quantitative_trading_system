# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**起草 GAP-3 事件型 SPEC**（使用者 2026-08-20 裁定「新 session 開始 SPEC」；討論階段已完成，勿再開 consult）

**這是大任務**（命中 a／b／d）→ 完整管線：SPEC 初稿（主委起草）→ 三家 adversarial → reconcile＋三家戳記 → **白話閘給使用者裁** → TODO（凍結）→ 分批實作 B1–B5（主委自任；每批三家 code review＋三家戳記才進下批）。

**取材（唯一地圖＝`白話說明/GAP-3事件型討論.md` §7.5 五層優先序；現為第 11 版；衝突以新使用者意圖為準）**：
1. 討論文檔 §7 U1–U13＋§8 第 8／11 版增補（使用者裁決）——最高權威。**特別注意 8/20 改寫**：標籤基準預設 `close_to_close`（相對 t₀ close；U4b）；決策時點可 t₀−k；反例種類欄選填（平台可依 t₀ 走勢自動分類）；TF／規模不寫死；多標的＝常態必要（U12）。
2. §7 J1–J10（主委判斷，委員已審）。
3. `handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md` C1–C9（K1–K10 全部技術細節；**C1 已被 U4b 改寫**、K1/K2 受 t₀−k 擴充）。
4. `handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md`（只取 R2 未覆蓋：六時間欄不變式、ms 單位閘、taxonomy 正交欄；其 C-情境反例結論**不取**）。
5. 既有契約 pointer：`ic_survivor_contract.json`（擴欄升版）、`SplitPlan`／rows purge、`capability_status` 枚舉、`TEST_DESIGN_CHARTER`、GAP-1 DSR/PBO、成熟度地圖（禁改 `xgboost_batch_service` 訓練殼；不碰回測層）。

**SPEC 要件**：檔名 `docs/GAP3_EVENT_SPEC.md`；創建須 `bash scripts/gate.sh artifact --file docs/GAP3_EVENT_SPEC.md --template-opened templates/SPEC_TEMPLATE.md --sections ...`（PreToolUse gate 擋無 token 創建）；§0 前置裁決 D 系列＝R2 C1–C4 合併 8/20 增補（**這是「最完整精確」的合併點**，對抗審第一項工作＝拿 §7.5 逐條比對「沒漏沒錯沒被舊結論污染」）；Task 分批 B1–B5（K10；一份 SPEC 預設，太大再拆）；§N 殘留（三值理由）：triple-barrier／long-short／T4 T6 資料源／sample_weight 接 ML 訓練／#4 正式 panel IC。**五項「待 SPEC 對抗審確認」**：①決策時點 t₀−k 擴充（K1/K2）②反例自動分類規則 ③多標的必要化與 #4 邊界（K4）④一份 SPEC vs 拆兩份（K10）⑤產生器 G1–G6 落哪批。
**每次使用者補充**：照討論文檔檔頭 **SYNC-GAP3** 六項同步（使用者會帶 Prompt 觸發；缺一項＝沒做完；收尾給「檔 × 改動節」對照表）。SPEC 凍結後討論文檔降為歷史。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十一）
- 🔴 含家族名的 Bash 會被 gate_check 擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；讀委員檔用 Read。committee_run 一家失敗：同 round `ROUND_ID=<id> bash scripts/cx_run.sh <fam> <brief> <out>` 補跑；外部服務連續失敗 ⇒ `debt_clear --abandon --kind collection-failed --approver main-agent`（consult 可、review/stamp 不可）。
- 🔴 委員交件檔有尾隨空白 ⇒ pre-commit index-strip 打破位元綁定（摩擦八十一）：register 兩版 sha 或 sources 副本不入版控；白話表格表態欄用文字不用 ✅（摩擦八十）；「使用者意圖」類 assumed 前提先白話問使用者再派委員（摩擦七十八）。
- review brief 前提逐條 `fact-verified:`／`assumed:`；stamp brief 禁多家並行跑重測試；commit 訊息 `Governance-Scope:` trailer 獨立末段；白話新增 .md 須登記 `plain_docs_sync_check.sh`；`factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 紅為既有；venv Python 3.9.6；`docs/API_SPECIFICATION.md` 格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty；push 丟背景；三支臨時腳本 `scripts/ichc_t2_diag.py`／`ichc_t2_probe400.py`／`ichc_t3_diff.py` 待清（非本線）。
