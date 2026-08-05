# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-05 09:0x | **Branch**: main（`ee71585` 已 push）
**狀態**: 🔵 **第 0 批 SPEC R5 已收斂 → 主委須修兩個 P0 → 開 R6（窄確認輪）**

## ▶ 立即接手：修 SPEC 的兩個 P0，然後開 R6

**R5 兩家獨立實跑後結論一致**（codex 先提，composer 補派輪改判同意）：
`G-3`～`G-6` **CLOSED**（四條皆有 receipt）；`G-1`／`G-2` **NOT-CLOSED**，各一個 P0 機制缺口。
出場判準「findings ≤5 且新 P0 <2」→ findings=2 ✓、P0=2 ✗ ⇒ **開 R6**。

**P0-1（Task 2.0 契約第 10 項）**：起點 regex `<<[-]?[[:space:]]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1`
只吃識別字，但 **`EOF-1` 是合法 shell delimiter**。不匹配 ⇒ 不開 span ⇒ 掃描器改在 body 內的
`<<INNER` 開 span ⇒ **吞掉 `EOF-1` 終止行與其後的真派工**。codex 實跑 `ATTACK_EXECUTED` 而掃描器 `ALLOW`。
**修法**：補「合法 `<<` 但 delimiter 無法按契約解析 ⇒ 整段 fail-closed」，或把 grammar 擴至 shell word＋quote removal；
語料補 `EOF-1`／quoted `EOF-1`／body 內假 marker／delimiter 後外部派工的 TP/TN。

**P0-2（Task 3.2 lock）**：SPEC 全文無 `O_EXCL`／`flock`／`mkdir`／`TOCTOU`（`rg` rc=1）。
owner-safe release 只防「舊 owner 解新鎖」，**擋不住兩個 dispatcher 同時通過空檢查**。
codex barrier 模擬 `A:START`＋`B:START` 皆啟動。
**修法**：launch 前以每個 `<out>` 的原子 exclusive create（`mkdir` lock dir 或 `O_CREAT|O_EXCL`）取得 ownership，
失敗者重讀 lock 後拒絕；加 deterministic barrier race test；process-discovery／lock-create 任一錯誤 fail-closed。

**R6 範圍（窄）**：只確認上述兩個缺口已補入 SPEC 並附 heredoc bypass ＋ barrier race 兩組測試。
**不重開** `E-SCOPE`／措辭／命名／已接受殘留。

## 產出位置

- SPEC `docs/GOVB0_FRICTION_SPEC.md`（R5 版，`template_check` rc=0、Task 11、FACT-RECEIPT 10）
- R5 報告 `handoffs/20260805-govb0-spec-r5-{codex,composer}.md`（composer 那份 **format-failed 但內容完整**）
- R4 收斂 `handoffs/reconcile/20260805-govb0-spec-r4/synth.md`（三家 APPROVED，sha `ae304eeb…f88b3fa`）
- 白話日誌 `handoffs/20260804-治理進度-白話日誌.md`｜票 `handoffs/20260801-GOV-AMEND-BACKLOG.md`（37 張）

## 🔴 本日新增／升級的票

`B-37`（新，0.9 批）票的優先順序無數據依據；硬前置＝第 0 批 Phase 0。
`B-31`（**嚴重度上調**）連兩輪 format-failed 且 **prompt 層警告實測無效**；追加修法 ④⑤，建議第 1 批與 `B-19` 同批。

## ⚠️ 坑（照做省時間）

- **`##` 只准是 canonical finding ID**。`completeness_check` 把每個 `##` 當 finding 候選，不符即整份 format-failed。
  **brief 不可同時要求「canonical `##`」與「逐條各一段」**——會誘導委員違規（本日踩 2 次，`B-31`／`B-32`）。
- **brief 改了就不能同輪重派**（`brief_sha256` 不符）⇒ 只能棄輪重開。
- **commit 訊息是零豁免路徑**：operational claim 須 `VERIFY:<receipt-id>` ＋ **可解析 scope**
  （`_extract_scope` 只認 node-id／`test_*`／`tests/**.py`；markdown 路徑不算）或寫明 runtime 類別（`static`／`讀碼`）。
- `VERIFY-EXEMPT` 合法類別**只有 6 個**：`typo`／`doc-example`／`migration-note`／`template-drift`／`tooling-blocked`／`spec-ambiguity`。
- 委員產出交件後一律 `bash scripts/gate.sh register-output <task-id> <path>`，否則 claim checker 擋 commit。
- **`rc` 禁經 pipe**；**禁 `python3 -c`**；`ts_stamp.log` 須 `LC_ALL=C grep -a`（且**禁 export**）。
- 文件維護紀律：狀態文件**只留最新狀態與待辦**，過期的移除並封存 `Archived/`，**不得用附加註記堆疊**。

## 後續順序

第 0 批（R6 → TODO → 實作 Grok → 雙家族 review）→ **第 0.5 批 P1-6 線 C** → 0.9 批 `B-37` → 第 1 批。
