# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-05 10:0x | **Branch**: main（`1e60553`）
**狀態**: 🟢 **第 0 批規格階段收斂完成（R7 三家戳記 APPROVED）→ 下一步＝TODO 生成**

## ▶ 立即接手：生成 TODO

SPEC `docs/GOVB0_FRICTION_SPEC.md` 已凍結可用（`template_check` rc=0、Task 11、FACT-RECEIPT 10）。
收斂檔 `handoffs/reconcile/20260805-govb0-spec-r7/synth.md` 三家 APPROVED，
sha `b502bac9…0f82fa4bd`。**無 OPEN 債**。

**TODO 生成用** `templates/TODO_GENERATION_PROMPT.md`。🔴 **§0 必須明文載入下列三項**，否則失真：

1. **`B-24` 部分完成** —— 紀律面隨本批交付、機械強制面已 SPLIT 移出，code review 不得宣稱 `B-24` 全綠。
2. **reclaim 孤兒回收未實作 ⇒ 需人工清理**（R7 殘留 `H-2`），不得宣稱 lock 機制全綠。
   修法三擇一由實作者定：(a) 清 orphan 運維腳本 (b) reclaim lock 加 TTL／lease＋受保護 CAS (c) 改用 `flock`。
3. **timeout 未達定稿門檻時標 `PROVISIONAL`**（每家族 ≥50 筆＋≥3 個不同 session／UTC 日期），
   且 Task 3.3 不得宣稱完工、`票 B-14` 不得標定稿。

之後：實作（Grok，見 ORCH §1 現行分工行）→ **雙家族 code review**（非實作者兩家）。

## 七輪收斂軌跡（規格階段已結束，勿重開）

`R1 19(5 P0) → R2 17(7 P0) → R3 11(3 P0) → R4 8(2 P0) → R5 2(2 P0) → R6 3(2 P0) → R7 4(0 P0)`

R7 為 P0-1／P0-2 的**最後一輪**（brief 明文終止條件）。兩家在互不相見下收斂到同樣兩條殘留。
🔴 **`E-SCOPE` 四項＋`B-36` ID 錯位＋R7 兩條殘留（`H-1`／`H-2`）皆已具名寫入 SPEC §N，不得在實作階段重開。**

## 🔴 本日票異動

`B-37`（新，0.9 批）票的優先順序無數據依據；硬前置＝Phase 0。
`B-38`（新，第 1 批）委員回報 0 findings 反而無法正規銷帳 ⇒ 推高 ABANDONED 比率；
　　　修法建議的 `FINDINGS_COUNT` 欄位**同時能解 `B-35`**（截斷偵測）⇒ 兩票應合併評估。
`B-31`（嚴重度上調）連兩輪 format-failed 且 **prompt 層警告實測無效**；追加修法 ④⑤。
票數 **38**、待辦 **30**；三份文件同步，票號雙向對帳差集空。

## ⚠️ 坑（照做省時間）

- **`##` 只准是 canonical finding ID**；brief **不可同時要求「canonical `##`」與「逐條各一段」**（會誘導違規）。
  有效作法＝**明列本輪允許的 `##` 清單＋要求用表格**（移除誘因，非警告誘因；R6/R7 實測有效）。
- 委員若零 findings，請要求其明寫 `FINDINGS_COUNT: 0`（否則 completeness 判 FAIL，見 `B-38`）。
- **brief 改了就不能同輪重派**（`brief_sha256` 不符）⇒ 只能棄輪重開。
- **commit 訊息零豁免**：operational claim 須 `VERIFY:<receipt-id>` ＋ 可解析 scope
  （`_extract_scope` 只認 node-id／`test_*`／`tests/**.py`）**或**寫明 runtime 類別（`static`／`讀碼`）。
- `VERIFY-EXEMPT` 合法類別**只有 6 個**：`typo`／`doc-example`／`migration-note`／`template-drift`／`tooling-blocked`／`spec-ambiguity`。
- 委員產出交件後一律 `bash scripts/gate.sh register-output <task-id> <path>`。
- 正規銷帳需 `sources.lock` 為 **review mode**：`reconcile_build.sh <session> --mode review --rebuild`（不接受委員檔參數）。
- **`rc` 禁經 pipe**；**禁 `python3 -c`**；`ts_stamp.log` 須 `LC_ALL=C grep -a`（**禁 export**）。
- 狀態文件**只留最新狀態與待辦**，過期的封存 `Archived/`，**不得用附加註記堆疊**。

## 後續順序

第 0 批（TODO → 實作 → 雙家族 review）→ **第 0.5 批 P1-6 線 C** → 0.9 批 `B-37` → 第 1 批（`B-19`／`B-29`／`B-31`／`B-38`）。
