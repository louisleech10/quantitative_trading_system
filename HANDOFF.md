# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-06 03:xx | **Branch**: main
**狀態**: 🛑 **B3 斷路器觸發，設計已重審定案** → 下一步＝寫 **B3R SPEC**

## ▶ 接手第一件事：寫 B3R SPEC

**依據**（三家戳記 APPROVED，`sha256:862f7bee…`）：
`handoffs/reconcile/20260805-gatelex-redesign2/synth.md`

B3R＝詞法層重寫，**獨立批**，五步：
①訂 lexer 輸出契約並**逐條對照 11 契約** ②`/tmp` 原型 ③差分驗證 ④TP/TN＋parity＋mutation＋時限 ⑤通過才寫入 repo。

🔴 **差分基準已定死**：凍結 snapshot ＋ `phase2_expected_flips` 合成不可變 old/expected 矩陣，
**非預期差集為零**。禁用工作區現況當 oracle（它自己帶缺陷）。

**B4 必須等 B3R 過關**；三家一致「禁在 B3 內再補一刀後併 B4」。

## 🔴 工作區有未 commit 的 B3 修補（**不要 commit**）

`scripts/_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/*`／fixtures／`docs/GOVB0_FRICTION_TODO_AMENDMENTS.md`

**保留**是兩害相權（全回退會重開三條原始 fail-open），但**風險未經證明**：
仍帶 E-1 換行繞道（fail-open）與 E-2 大輸入 O(n²)（500K→30s）。
⚠️ **不得宣稱現況安全**——主委原稱「10K→0.09s 故非即時風險」已被 codex 推翻並撤回。

## 這一輪發生什麼（B3 三次修補都沒過）

```
B3 → 審查 3 洞 → 修補R1 → 審查 2 洞(1新引入) → 修補R2 → 審查 2 洞(1新引入)
→ 🛑 斷路器（連續兩輪修補引入新缺口）→ 三家設計重審 → B3R
```

> <!-- claim-context: discussion -->
> **主委三項判斷被推翻**（轉述三家委員判定，非主委實跑；出處＝上方戳記收斂檔）：
> 1. 「E-1 根因＝轉換＋grep 架構」→ 真因是 `_gate_cmd_is_self_gate` 用**字面 `\n`** 比對，早退 `exit 0`
> 2. 「E-1／E-2 同根因」→ 根因獨立
> 3. 「latency 改 min-of-N」→ 冷路徑真退化時仍高機率全綠 ⇒ **統計手法達標**，撤回

## latency 結論（使用者提問，已定案）

**三家一致：維持現狀，不用花力氣。** 100ms **有出處**（`docs/P16_COMMITTEE_DEBT_SPEC.md:507`）；
抖動根因＝**CPU 競爭**（併 8 負載→144ms 紅／靜止→74.9ms 綠）；
該測試走 Task 通道**不經 lexer**，與重寫無關。**偶發紅請重跑，勿據單次下結論。**

## 本日重複犯的錯（同一型）

**「驗了 A 就當作 B 也成立」——本日 5 次**：封存只驗 1/20 個消費者／看 C5 測試當 C4 也真突變／
小輸入量測宣稱整體安全／composer 亦犯（跑無引號路徑當引號路徑）。

**ID 錯位 9 次**（第 8 次自檢抓到、第 9 次 codex＋grok REJECTED）。
`completeness_check` **對「歸錯群」無感** ⇒ 已列待開票：群集須附斷言摘句 + 腳本比對。

## 已修的機制

- `status_marker_check.sh`：正則 `[a-z][a-z0-9]{8}` 會誤判任何 9 字元詞（`redesign2` 中招）
  ⇒ 改為 `b`+8 位英數 **且** 任務檔須真存在；用原始漏網訊息做 mutation 測試（4/4 過）
- `plain_docs_sync_check.sh`：日誌納入受管；新增「進度單一出處」守衛（rc=2 fail-closed）
- `ts_stamp.sh`：B 類門檻 60→120s（使用者定）

## 待開票（未進 backlog）

1. **`票 B-38` 應提前**——本日撞 8 次，已從儀式成本升級為**擋住斷路器紀錄／擋住派工**
2. 收斂檔群集須附**斷言摘句**並機械比對（治 ID 錯位）
3. 戳記機檢要三家但 roster 只兩家 → 漏派 grok 多一輪
4. `reconcile_build` 預設 discovery、銷帳要 review → 第一次必失敗
5. **`票 B-32` 覆蓋缺口**：B2 只修產生器，**未涵蓋主委手寫 brief**（本日害整輪三家作廢）

## 坑（沿用）

`rc` 禁經 pipe（本日又犯）｜禁 `cd <專案路徑>` 前綴（本日又犯）｜中文路徑 `git -c core.quotepath=false`｜
`rm` 在 deny 用 `git rm`｜commit 訊息用 `-F 檔案`｜brief 用兩支檢查器一次驗｜
**brief 必寫 `##` 標題白名單**，否則委員照抄小節代號 → 整輪作廢
