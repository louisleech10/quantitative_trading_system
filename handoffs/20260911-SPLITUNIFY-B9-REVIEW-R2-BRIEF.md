# SPLITUNIFY D-002 閉合輪 R2

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R2
findings-round: R2

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 這一輪要做什麼

R1 你們**三家全數 `blocked`**，共 15 條、收斂為七群、**全部採納零駁回**。
D-002 已依收斂修訂（commit 見下）。依章程 §B8，Block 退回修改後須由**原提出方**確認是否真關閉，
**不憑作者說「已改」**。本輪聚焦兩件事：

1. **逐群複驗**你自己開的 finding 是否真的閉合（給 `CLOSED` 或仍 `blocked`）。
2. **攻修訂本身有沒有引入新問題**——特別是新增的三條義務區塊。

## 審查對象

`docs/SPLITUNIFY_SPEC.D-002.md`（修訂版）。上游收斂：
`handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`（七群）。

## 七群的修訂落點（請對照複驗）

| 群 | 你們指出的問題 | 修訂落點 |
|---|---|---|
| 記帳分母 | 15 處漏記帳／報告鏈；`n_train`／`n_test`／`n_purged` 語意未定義 | 新增 `D-002-C6`（量詞分離，(6.2) 定三量為**事件數**、列數另立新名）；觸及面新增第四層 `D-002-C5` (5.5)；新增 **`Task 9.4`** 專責記帳與報告鏈 |
| 9A 契約 | 只寫到 producer，無返回形狀／跨邊界傳遞／UI 揭露；「可獨立回退」無碼證 | `Task 9.1` 重寫：明定 `discarded: Dict[str,int]` 返回形狀（無丟棄時 `{}` 不得省略）、跨 `_derive_single_symbol` 與分派器之傳遞、**API 與前端三層揭露落點**（缺任一層即 9A 未完成）、獨立回退改為可證偽斷言 |
| timeframe 雙語意 | 觸發 TF 與 feature TF 同名不同義 | 新增 **`D-002-C0`**：`trigger_timeframe` / `feature_timeframe` 分名，(0.4) 明定複合鍵為 `(event_id, feature_timeframe)`，(0.5) 禁用裸 `timeframe` 當新欄名 |
| Task 9.3 改法 | 形狀規則既過度涵蓋 event-level 表、又漏掉真正折疊點 | `Task 9.3` 改為**逐處列名**，每處註明粒度與改法；明寫 `feature_materialization` 的折疊點在 `groupby("event_id")+row_vals.update`；明寫 event-level 表**粒度不變** |
| §G 矛盾 | 「g5 不受影響」與「改交錯 fixture」並陳未區分 | §G 拆為 (G-1) 複合鍵不改 payload 故 g5 不位移／(G-2) 交錯 fixture **會**移動 g5，須新增平行組並保留單標的錨／(G-3) TF 為 parent key 不進 payload |
| mutation 不足 | 六條聚合 mutation 覆蓋不了 15 處與靜默面 | mutation 由 6 條增為 **18 條**，逐處對應（含 `14`／`15` 專攻同側約束、`18` 為過度涵蓋之反向 mutation） |
| 同側約束 | 只規定同簇、未規定同側 ⇒ 異側會靜默組成非法 OOS | 新增 **`D-002-C3`**：(3.1) 同事件所有 feature TF 必須同側；(3.2) 異側則**整事件 purged**；(3.4) 檢查須在投影端完成；§V 配成對可證偽斷言 |

## 前提（範本 §0；請逐條挑戰）

fact-verified: 七群 15 條全部採納零駁回 → `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`
fact-verified: 修訂版 `doc_format_precheck` rc=0、`spec_xref_check --synth` rc=0（處置欄 9 概念皆同步）→ 主委實跑
fact-verified: `event_id` 已含 trigger TF → `frontend/src/lib/eventId.ts` 之 `canonicalEventId(symbol, timeframe, t0)`

assumed: `D-002-C3` 的「異側則整事件 purge」不會誤殺合法樣本
→ 否證觀測：給出「同事件多 feature TF 合法地落在不同側」的情境／我跑了: **沒跑**，這是本輪新增義務
assumed: `D-002-C6` 把 `n_train`／`n_test`／`n_purged` 定為**事件數**是正確選擇
→ 否證觀測：指出某個既有消費者其實需要列數語意／我跑了: 讀既有消費者，**未**實跑
assumed: 18 條 mutation 已覆蓋 16 處消費面與 9A 三層揭露
→ 否證觀測：指出第 19 條該有而沒有的 mutation／我跑了: 逐處對照，**未**實作驗證
assumed: `trigger_timeframe`／`feature_timeframe` 分名後全檔無殘留裸 `timeframe` 語意歧義
→ 否證觀測：指出修訂版中仍歧義的句子／我跑了: 全檔改寫，**未**逐句機械掃描

## 必答（成對，缺一不算完成）

1. **你自己 R1 的 finding 是否閉合**？逐條給判定，並說明你**用什麼方式**確認（讀哪一段、對照哪一句）。
2. **同側約束（`D-002-C3`）**：請嘗試構造「同事件多 feature TF 合法異側」的情境。構造得出 ⇒ 這條義務過嚴、會誤殺；構造不出來也要說明你試了什麼。
3. **量詞分離（`D-002-C6`）**：(6.2) 把三量定為事件數，是否有既有消費者其實需要列數？給碼證。
4. **術語分名（`D-002-C0`）**：修訂版中是否仍有裸 `timeframe` 造成的語意歧義？給行號。
5. **修訂引入的新問題**：本輪新增 `C0`／`C3`／`C6`／`Task 9.4` 四處，有沒有彼此衝突、或與 D-001 既有義務衝突之處？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或行號**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**——若判定可進實作，須說明你主動攻了哪些面而未成功；
④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明，請對號入座）

findings 用 `## <你的家族大寫>-R2-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`
（🔴 R1 有一家寫成 `STATUS: BLOCKED — …`，那不合交件契約，本輪請逐字照寫）。
🔴 **`CLOSED:` 欄只列「你自己家族」R1 開過的 ID**：

- **codex**：`CODEX-R1-P1-01`,`CODEX-R1-P1-02`,`CODEX-R1-P1-03`,`CODEX-R1-P1-04`,`CODEX-R1-P2-05`,`CODEX-R1-P1-06`
- **composer**：`COMPOSER-R1-P1-01`,`COMPOSER-R1-P1-02`,`COMPOSER-R1-P2-01`
- **grok**：`GROK-R1-P1-01`,`GROK-R1-P1-02`,`GROK-R1-P1-03`,`GROK-R1-P2-01`,`GROK-R1-P2-02`,`GROK-R1-P2-03`

裁決塊三行分寫；仍 `blocked` 時 `BLOCKED-BY:` 填你自己家族的 ID，`CLOSED:` 列已閉合者（**不得**寫 `none`）。
