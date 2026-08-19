# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-3 事件型——討論文檔第 7 版＋委員 R2 意見檔已出，**等使用者醒來點頭才寫 SPEC**（2026-08-20 凌晨）

**現況**：使用者 8/19 五輪對談把意圖定版（U1–U11，見 `白話說明/GAP-3事件型討論.md` §7：A／B／C／兩段式全要、任何類型、多空分開、正反例自標＋CSV＋搜尋條件一起匯入、事件產生器完整版列入、前端同頁事件模式、全部 K 線驗證交委員、現有頁面升級不翻掉）。consult R2（`handoffs/20260819-gap3-consult-r2-BRIEF.md`；三家齊＋主委版）逐項審＋K1–K10 定案 ⇒ reconcile `handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`（26 條九群集 C1–C9；債已清）。給使用者的對應檔 `白話說明/GAP-3事件型討論-委員意見.md`。三家一致：可進 **decision-gated SPEC**；無 U 不可行；J1–J10 無一推翻。
**R2 四項硬結論（SPEC 必寫死）**：C1 `entry_price_semantic`＋`label_return_mode`（A/B open→答案窗末 close；禁沿用 IC 主線 close-to-close）；C2 per-TF `feature_cutoff` 收據＋六時間欄＋失敗枚舉 loud；C3 條件引擎欄位三角色 `feature／selection_predicate／label`、typed AST＋digest、純函式落 `momentum/`，`/search`／`event_filter` 皆 adapter；C4 全樣本驗證 evaluation manifest 固定分母＋`prevalence_learn` vs `prevalence_full`＋lift，不碰回測層。其餘 C5 去重（C 簇首／A-B 全留唯一性權重；敏感度非 B1 門檻；sample_weight UNWIRED）、C6 pooled 最小版（macro primary、time-cluster、不關閉 #4）、C7 三表／T8-T10 欄位／DSR-PBO 只在 B3 後、C8 K7 特徵清單、C9 分批 B1→B5（主委定）。
**下一步**：① 使用者讀兩份檔、點頭（或改意見 ⇒ 改討論文檔第 8 版；若動 K 定案須再問委員）② 點頭後寫 `docs/GAP3_EVENT_SPEC.md`（gate artifact；SPEC_TEMPLATE；前置裁決 D1–D4＝C1–C4；Task 分批 B1–B5；§N 殘留：triple-barrier／long-short／T4 T6 資料源／sample_weight 接線／#4 正式 panel）→ 三家 adversarial → 白話閘 → TODO → 分批實作（主委）→ 三家 review＋戳記。**點頭前不寫 SPEC、不動 GAP-3 程式。**
**前端占位規則**（commit aded5574）：需要前端的殘留一律先做 `/pending-features` 條目＋原位置殼；vitest 對 registry 機檢。
**其他可做未排**：GAP-4（#4 正式 panel IC；GAP-3 只做最小 pooled 不關閉 #4）；GAP-5 容量；GAP-6 效能；G2-R6 前端 tsc 既有 8 紅；三支未登記臨時腳本 `scripts/ichc_t2_diag.py`／`ichc_t2_probe400.py`／`ichc_t3_diff.py` 待清。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十）
- 🔴 含家族名的 Bash 在「有 token＋債 OPEN」或「無 token」時都被 gate_check 擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；讀委員檔用 Read 工具。committee_run 有一家失敗：同 round 補跑 `ROUND_ID=<id> bash scripts/cx_run.sh <fam> <brief> <out>`；外部服務持續失敗 ⇒ roster 不等只能 `debt_clear --abandon --kind collection-failed --approver main-agent`（consult 可、review/stamp 不可）。R2 三家齊 ⇒ 正常 `debt_clear --lock`（需 `--mode review` lock）。
- 🔴 consult brief 之「使用者意圖」類 assumed 前提要先白話問使用者再派委員（摩擦七十八）；白話表格表態欄用文字不用 ✅（factkey 守衛誤判，摩擦八十）。
- 白話資料夾新增 .md 須登記 `plain_docs_sync_check.sh _watched_for`；動 `scripts/` 時 README／接下來／日誌／摩擦 四檔須同 commit staged；`factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 的紅為既有（pre-commit 放行）。
- stamp brief 禁多家並行跑重測試；review brief 前提逐條 `fact-verified:`／`assumed:`；commit 訊息 `Governance-Scope:` trailer 獨立末段；venv Python 3.9.6；`docs/API_SPECIFICATION.md` 受格式快閘不可編輯；`scripts/governance_families.json` 既有 no-op dirty 非本線；push 丟背景。
