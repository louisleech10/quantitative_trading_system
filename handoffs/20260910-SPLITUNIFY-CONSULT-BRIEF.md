# SPLITUNIFY consult：兩套切分要統一成哪一套？（委員會定共識，不問使用者）

brief-kind: review
task-id: 20260910-SPLITUNIFY-X-CONSULT-R1
findings-round: R1

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0（挑戰前提）與 canonical finding
四欄格式**全文照做**；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`，結尾附 **Verdict**。
本輪之審查對象是**設計方案**（我的提案），不是既有碼——但碼證仍以檔案與函式名指名。

## 這是什麼

**不是 code review，是設計 consult。** 使用者 2026-09-10 明確裁定：
「但要如何切分，你跟委員要討論共識」——**切法由 Claude 與委員會定，不回頭問他**。
本輪要的是**一個可執行的共識方案**，不是列選項。

使用者今晚已離線，並指示「有問題找委員會討論共識，做完前不要停下來」。
故本輪之結論將直接進 SPEC，不再等他點頭。

## 問題

平台現在有**兩套切分**，同一批事件會得到**兩個不同的驗證段**（實測 31 vs 33）：

| | 事件切分（GAP-3） | 時間切分（IC 主線） |
|---|---|---|
| 切什麼 | **事件**分訓練／驗證（每 symbol 各自按時間切，緩衝 ≥ 答案窗） | **K 線列**分訓練／驗證 |
| 隔離 | 緩衝 bars | `purge` ＋ `embargo`（EVTLABEL Task 2.2 後 purge 吃答案窗） |
| 型別 | `EventSplitPlan`（`momentum/Analysis/event_samples/types.py`） | `SplitPlan`（`momentum/core/contracts.py`） |
| 產生者 | `event_samples/event_split.py` | `ic_filter_orchestrator._build_holdout_split_plan` |

**為什麼非統一不可**：使用者 UAT 時會在同一份報告看到兩個驗證段數字，
無法判斷哪一個才是結論的依據；下游（倖存者檔、pattern_bridge）也可能各自綁到不同那一套。

## 現況盤點（fact-verified，我實跑）

- `EventSplitPlan` 之生產端消費者共 **7 個檔**：`event_split.py`、`baseline.py`、`ic_feed.py`、
  `pattern_bridge.py`、`types.py`、`tables.py`、`pipeline.py`；測試端 **6 個檔**。
- `SplitPlan` 走 IC 主線；EVTLABEL Task 2.2 已讓 `purge = max(effective_horizon, label_window_rows)`，
  Task 3.4 之 selection scope 改吃 `split_context["test_timestamps"]`（canonical 測試段時間戳）。
- GAP-3 之規格已 FROZEN ⇒ 動它要走**延伸檔**（`docs/GAP3_EVENT_UX_SPEC.D-00N.md` 之慣例）。

## 我的提案（可被推翻，請正面打）

**以時間切分為準，事件切分「導出」而非平行存在。**

具體：`EventSplitPlan` 不再自行決定邊界，改由 `SplitPlan` 之 `test_timestamps` 交集出
「落在驗證段裡的事件」。理由：
1. EVTLABEL Task 3.4 已經這樣做了（selection scope ＝ 交集），實務上時間切分已是事實權威。
2. `purge`／`embargo` 的隔離語意住在時間切分那一側；事件切分只有「緩衝 bars」，較弱。
3. 交集是**投影**不是第二份算術——沒有可漂的東西（B3 review 的教訓）。

**風險（我自己看到的）**：
- 事件切分之 per-symbol 語意會被全域 scalar 取代 ⇒ 多 symbol 批可能不再等價。
  這正是 `CODEX-R1-P1-02`（EVTLABEL）踩過的「per-scope 冒充」禁令所在。
- `baseline.py`／`pattern_bridge.py` 之 OOS 語意可能依賴 `EventSplitPlan` 之欄位。

## 🔴 必答（請給**可執行的共識**，不是選項清單）

1a. 統一方向：以時間切分為準（我的提案）／以事件切分為準／兩者皆改為由第三方 canonical 來源導出？
1b. 你選的那個方向，**最小可行的落地步驟**（哪些檔改、哪些只讀）。
2a. 多 symbol 批在統一後是否仍等價？若否，該擋（fail-closed）還是該支援 per-symbol？
2b. 若要支援，`SplitPlan` 是否需要 per-symbol 化（`split_per_symbol` 已存在）？
3a. `baseline.py`／`pattern_bridge.py` 對 `EventSplitPlan` 的依賴，哪些是**語意**依賴（不可換）、
   哪些只是型別依賴（可換）？
3b. 有沒有哪一個消費者會因為統一而**改變數值**（而非只是改型別）？
4a. GAP-3 規格已 FROZEN——本次應走延伸檔還是解凍原檔？
4b. 你建議的延伸檔編號與範圍。
5a. 是否存在「兩套都保留但明確標主從」的方案優於統一？若有，它的代價是什麼？
5b. 你的最終建議（一句話）。
6. 這張票應該多大（中／大）？需要幾批？

## 停輪條件
① 必答 1a–6 皆有明確立場（不得只列選項）；② 必答 3b 有具體檔案與函式名；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭），我依較嚴版本收斂並具名殘留。

## ⚠️ 前置
- **禁改碼**。本輪只出設計共識。
- 既有紅基準見 `HANDOFF.md`「既有紅盤點」節（`tests/momentum/Analysis` 20 條，非本票造成）。
- 不得跑 `pytest tests/governance`（小時級）。

## 本 brief 之前提（逐條標）

fact-verified: 消費者檔數（7 生產／6 測試）→ `grep -rln EventSplitPlan momentum api tests`。
fact-verified: EVTLABEL 已收（三 Phase、17 Task、四批三家審全收斂、四個 gate 全 PASS）。
fact-verified: Task 3.4 之 selection scope 已改吃 `test_timestamps` 交集（`CODEX-R1-P1-02` 修補）。

assumed: 時間切分之隔離語意嚴格強於事件切分之緩衝
← 否證觀測：某情境下事件切分擋得住而時間切分擋不住。／我跑了：**沒跑**，只讀碼比較欄位。
請正面打（必答 1a）。

assumed: 統一後多 symbol 批之數值不變
← 否證觀測：多 symbol 批在統一前後得到不同的驗證段成員。／我跑了：**沒跑**。請正面打（必答 2a）。

## 🔴 我沒查的
| claim | observable_if_false | reason_code |
|---|---|---|
| `baseline.py` 之 OOS AUC 是否依賴 `EventSplitPlan` 之 per-symbol 語意 | 統一後 baseline 數值改變 | cost |
| GAP-3 UAT 清單中是否有項目直接驗事件切分邊界 | 統一後既有 UAT 項目失效 | cost |

## 產出
canonical 四欄 findings＋**Verdict（一句話結論＋最小落地步驟）**。**禁改碼**。
收尾清 /tmp workdir（保留 claude-501）。
