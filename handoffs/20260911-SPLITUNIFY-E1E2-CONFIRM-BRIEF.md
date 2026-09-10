# SPLITUNIFY — E1／E2 定向確認輪（R4，只問兩件事）

brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R4
findings-round: R4

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R4-P<0-3>-<NN>`，結尾附 **Verdict**。
審查對象＝`docs/SPLITUNIFY_SPEC.md`（sha256 `384aa22961d0…`）與
`docs/SPLITUNIFY_TODO.md`（sha256 `cd95ee642a9e…`），commit `b6633582`。
**禁改碼**；碼證以檔案:行號指名。

## 🔴 這是**定向確認輪**，不是全面重審

R1 收斂 13 群集、R2 收斂 11 群集、R3 收斂 7 群集（**0 P0**）。P0 已清零，
剩下的兩條 P1 集中在同一個設計缺口，v4 已針對性修復。

⇒ **本輪只問 E1／E2 是否閉合**，外加一次介面可執行性掃描。
**不要**重新審 C-0～C-9、§G、§P 的其他部分——那些已在 R1–R3 收斂並經三家確認。
若你發現其他問題，照列但標 **P2/P3 且註明「不擋 B1」**。

## R3 之 E1／E2 與 v4 的修法

### E1（`CODEX-R3-P1-02`；實質 P0）

**問題**：v3 的投影只用「`event_index ∈ feature_index[row_index]`」做判定，簽名裡沒有
`label_end_ms`。而現行 `momentum/Analysis/event_samples/event_split.py:114` 逐字是
`elif int(rec["label_end_ms"]) > test_start - embargo:` → purge——那是事件側**唯一**
擋標籤窗跨界洩漏的閘。v3 等於把它刪掉 ⇒ 答案窗已跨進測試段的 train 事件會留在 train
＝ 直接 OOS leakage；且 G-5.4 的 leakage negative case 永遠測不出來。
另：C-1 附帶約束①逐字寫著「未證明 containment 前不得刪除任一既有 guard」，v3 自我違反。

**v4 修法**：C-4 改為**兩段式判定且先後不可調**——
①**先**驗答案窗：`label_end_ms >= test_start_ms` 而該事件 `feature_cutoff_ms` 仍在 train 側，
或 `label_start_ms`／`label_end_ms` 在 source bars 上缺 endpoint ⇒ **purged**
（reason 沿用 `interval_crosses_split_boundary`）；
②**再**做集合成員判定決定 train／test。
新增 mutation `M-SU-13`（拿掉第一段 ⇒ `-k leakage_negative` 與 `-k answer_window` 必紅）。

### E2（`CODEX-R3-P1-01`）

**問題**：`event_index: pd.Index` 只有時間、無身份；`dedupe.py:46` 會依
`(label_start_ms, event_id)` **重排** manifest、`alignment.py:197-213` 之 feature cutoff
按輸入事件順序且可有多個 `per_tf` ⇒ positional zip 會**靜默錯分**。

**v4 修法**：改為 keyed 輸入 `event_keys: pd.DataFrame`，必含
`event_id`／`feature_cutoff_ms`／`label_start_ms`／`label_end_ms`／`symbol`／`timeframe`，
以 **`event_id` 為鍵**與 `manifest.table` 對位，**禁 positional zip**。

## 🔴 必答（只有四題）

1. **E1 閉合了嗎**？兩段式判定的**第一段條件式**寫得夠精確嗎？
   具體問：v4 寫的是 `label_end_ms >= test_start_ms`，而既有實作是
   `label_end_ms > test_start - embargo`（`event_split.py:114`）。
   這兩者**不等價**（少了 embargo 那一段緩衝，且 `>` vs `>=`）。
   ⇒ 在 canonical 邊界語意下，正確的條件式應該是什麼？請給**可直接實作的式子**，
   並說明它與 `test_plan.purge_gap`／`embargo` 的關係。
   （主委自評：這很可能是 v4 還沒修乾淨的地方——`test_start_ms` 已經是
   purge＋embargo **之後**的第一根，所以緩衝可能已內含；但我**沒有實跑驗證**，請正面打。）

2. **E2 閉合了嗎**？`event_keys` 的六個欄位夠不夠？誰負責產生它、在哪一批？
   （v4 的 Task 2.2 說「以 event_id 對位」，但**沒說 `event_keys` 由誰組裝**——
   是 B3 接線時由 `manifest.table` ＋ `receipts` 組，還是 B2b 另立 helper？請給立場。）

3. **介面可執行性掃描**（同 R2 之 D7／D8、R3 之 E5 的掃法）：
   v4 每一個「須 raise」的檢查，它要檢查的東西是不是真的在該函式簽名上？
   每一個「復用既有函式」，那個函式是不是真的接受我們要餵的輸入？
   逐條回，發現不一致就標 P1。

4. **可否進 B1**？直接回「可以」或「不可以＋ID」。
   B1 只做文件與枚舉與既有紅清單（**不動生產碼**），E1／E2 屬 B2b 的實作契約——
   請說明你的判準：E1／E2 未完全閉合是否**應該**擋住 B1？

## 停輪條件

① 必答 1–4 皆有明確立場；② 必答 1 有可直接實作的條件式；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭）；
④ 禁以「三家零 finding」當停輪——零 finding 須走 sentinel 契約；
⑤ 🔴 非 E1／E2 之意見一律標 P2/P3 並註明「不擋 B1」。

## 本 brief 之前提（逐條標）

fact-verified: `event_split.py:114` 之現行 purge 條件式為 `label_end_ms > test_start - embargo` → 主委實跑 `sed -n '112,118p' momentum/Analysis/event_samples/event_split.py`。

fact-verified: R3 三家分歧且主委採 codex（少數方）→ `handoffs/reconcile/20260911-splitunify-x-review-r3/synth.md` 之 Verdict 段。

fact-verified: `extract_event_patterns` 有 8 處測試 caller（v3 之 R-4 claim 已更正）→ `grep -rn extract_event_patterns momentum api tests | grep -v pattern_bridge.py`。

assumed: `test_start_ms` 已是 purge＋embargo 之後的第一根，故兩段式第一段不需再減 embargo
← 否證觀測：以 `holdout_test_row_index` 之定義推，`test_rows[0] = split_point + purge_gap + embargo`
⇒ `test_start_ms` 確實在緩衝之後；但事件側之 embargo 是**毫秒**、IC 側是**列數**，
兩者換算後未必等價。／我跑了：**沒跑**。這是必答 1 的核心。

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth。
- 不得跑 `pytest tests/governance`（小時級）。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句必須是「可進 B1」或「不可進 B1：<ID>」）。
