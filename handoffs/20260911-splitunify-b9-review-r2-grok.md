# SPLITUNIFY D-002 閉合輪 R2 — GROK

brief-kind: review  
task-id: `20260911-SPLITUNIFY-B9-REVIEW-R2`  
family: grok  
findings-round: R2  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（修訂版；full sha12 `708a6bafded5`；`## 戳記` 前 body sha12 `493dc21b7d8a`）  
上游收斂: `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`  
SCOPE: review-only；禁改碼、禁改 SPEC  
範本: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`  
探針目錄: `/tmp/grok-splitunify-b9-review-r2/`（交件後清除；保留 `/tmp/claude-501*`）

## §0 挑戰前提（fact-verified vs assumed）

fact-verified: 七群 15 條全部採納零駁回 → 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md` 群集表；本家六條皆在「採納」列、零駁回

fact-verified: `event_id` 已含 trigger TF → 讀 `frontend/src/lib/eventId.ts`：`canonicalEventId(symbol, timeframe, t0)`；模板 `{symbol}:{timeframe}:{t0}`

fact-verified: 同事件多 feature TF 可因 `feature_cutoff_ms` 分落 train／test → 探針 `probe_mixed_side.txt`（1h→train／4h→test）；對照 `split_projection.py:530-553` 逐列依 cutoff 判定

fact-verified: `n_train`／`n_test`／`n_purged` 現況由 pipeline 列求和、UI／wiring 當事件數讀 → `pipeline.py:760-762`；`EventTablesPanel.tsx:361`；`test_splitunify_wiring.py:113`；`pattern_bridge.py:207` 用事件 id 集合

fact-verified: `clusters` 為事件級且消費者 `set_index("event_id")` → `event_split.py:59-75`；`tables.py:229`／`:373`

assumed: 修訂版 `doc_format_precheck`／`spec_xref_check --synth` rc=0 → 本輪未重跑；trust brief；不阻 finding

assumed: C3「異側整事件 purge」不誤殺合法樣本 → 本輪反例構造失敗（見必答 2）；在單一共用 `EventSplitPlan`＋事件級消費者模型下判定不過嚴

assumed: C6 把三量定為事件數是正確選擇 → 消費者碼證支持（見必答 3）；列數須新名

assumed: 18 條 mutation 已覆蓋 16 處與 9A 三層 → 01–18 對表可勾；但 Task 9.2 對 `clusters` 加欄引入新衝突（P1-02），非舊 mutation 表漏列可代表

assumed: C0 分名後全檔無裸 `timeframe` 語意歧義 → **否證**：L136 `discarded_per_tf_rows_by_timeframe` 與 C0 (0.5) 互斥（P1-01）

---

## 必答 1–5

### 1. 本家 R1 finding 是否閉合

| R1 ID | 判定 | 確認方式 |
|---|---|---|
| `GROK-R1-P1-01` | **CLOSED** | 讀 `D-002-C5` (5.5) 第四層記帳鏈＋`D-002-C6`＋**Task 9.4**；對照 R1 所指 `pipeline.py:760-762`／`EventTablesPanel.tsx:361`／wiring `:113` 皆落入 Task 9.4 檔案清單 |
| `GROK-R1-P1-02` | **CLOSED** | Task 9.3 逐字點名 `groupby("event_id")+row_vals.update` 為折疊點，改 `groupby(["event_id","feature_timeframe"])`；mutation `04` 對應「只改 set_index 不改 groupby」 |
| `GROK-R1-P1-03` | **CLOSED** | 新增 `D-002-C3` (3.1)–(3.4)；§V 成對 ASSERT；mutation `14`／`15` |
| `GROK-R1-P2-01` | **CLOSED** | mutation 6→18，逐處對應；含 wiring／記帳／groupby／同側 |
| `GROK-R1-P2-02` | **CLOSED** | §G 拆 (G-1)(G-2)(G-3)；交錯＝平行組、單標的錨保留 |
| `GROK-R1-P2-03` | **CLOSED** | Task 9.1 重寫：返回形狀、跨邊界、API／前端三層、獨立回退可證偽；mutation `01`–`03` |

### 2. 同側約束（`D-002-C3`）— 嘗試構造「合法異側」

**構造嘗試（機械可行、語意不合法）：**

同 `event_id=E1`，`feature_cutoff_ms` 因 TF 對齊不同而分落邊界兩側：

```
1h cutoff=3000 -> train
4h cutoff=4000 -> test
MIXED_SIDES True
```

（探針 `/tmp/grok-splitunify-b9-review-r2/probe_mixed_side.txt`；對照現行投影迴圈 `split_projection.py:530-553` 係逐列依 `feature_cutoff_ms ∈ train_ms/test_ms` 判定——多 feature TF 後**必然**可出現此形。）

**為何不算「合法異側」：**

- 本批消費者（`baseline`／`pattern_bridge`／`tables`／`ic_feed` 事件級路徑）皆以 `event_id` 聚合；異側 pair 會把 train 特徵與 test 標籤（或反向）組成非法 OOS——正是 C3 (3.3) 所擋。
- 「1h 一個實驗、4h 另一個實驗」⇒ 應是**兩次** pipeline／兩個 plan，不是同一 `EventSplitPlan` 內異側共存。
- 嘗試「train + purged（答案窗）算不算異側」：C3 字面舉例是 train vs test；purge 不是 split 側。此邊界本輪**不**另開 P1（未證明會洩漏）；若實作把 purge 當第三側做 all-or-nothing，屬可接受的保守擴張。

**結論：構造不出「在本 epic 消費者模型內合法的異側」。C3 不過嚴。**

### 3. 量詞分離（`D-002-C6`）— 是否有消費者需要列數語意掛在 `n_train` 名下

**碼證（現況＝列求和；讀方當事件數）：**

- `pipeline.py:760-762`：`n_train`／`n_test`＝`assignments` 列數；`n_purged`＝`len(purged)`
- `EventTablesPanel.tsx:361`：無單位顯示三數（事件語感）
- `test_splitunify_wiring.py:113`：`n_train+n_test+n_purged == len(records)`（事件數守恆）
- `pattern_bridge.py:207`：`n_train=len(train_ids)`（**事件 id 集合**）

**立場：(6.2) 把三量定為事件數是正確選擇。** 沒有既有消費者**需要**裸名 `n_train`／`n_test`／`n_purged` 承載 (event×TF) 列數；列數應走 C6 新名（`n_event_tf_rows_*`）。複合鍵後若保留今日 pipeline 的列求和算法，才是缺陷——Task 9.4／mutation `13` 已指派。

### 4. 術語分名（`D-002-C0`）— 裸 `timeframe` 殘留

| 行 | 原文要點 | 判定 |
|---|---|---|
| L28–36 | C0 正文定義分名 | 規範本身；OK |
| L30 | `canonical_event_id(symbol, timeframe, t0)` | **既有 API 形參**；C0 已標為 trigger；可接受 |
| L32 | `per_tf.timeframe`／`selected_timeframe` | **既有欄／參數**；C0 (0.3) 映射到 feature；可接受 |
| **L136** | **`discarded_per_tf_rows_by_timeframe`** | **新增 summary 鍵名含裸 `timeframe`**，與 C0 (0.5)「禁用裸 timeframe 當新欄名」**互斥** → **P1-01** |
| L145 | Task 9.2 三表加 `feature_timeframe` | 名稱合 C0；但 **clusters 不該加** → P1-02 |

### 5. 修訂引入的新問題（C0／C3／C6／Task 9.4）

- **C0 ↔ Task 9.1**：新鍵名互斥（P1-01）。
- **Task 9.2 ↔ Task 9.3／既有 clusters 消費者**：對事件級 `clusters` 表「各加 `feature_timeframe`」與「簇仍事件級、`set_index("event_id")`」衝突（P1-02）。
- C3 ↔ C6：異側整事件 purge 後，`n_purged`（事件）vs `len(purged)`（可能多 TF 列）——Task 9.4／§V 守恆式已覆蓋；**不另開 finding**。
- C3 ↔ D-001 座標語意：C3 在投影端、不動 `row_index_local`；**無衝突**。
- C6 ↔ Task 9.4：義務與派工已對齊（補上 R1 的內部不自洽）；**無衝突**。

---

## GROK-R2-P1-01

**斷言**: Task 9.1 規定的新 summary 鍵 `discarded_per_tf_rows_by_timeframe` 含裸 `timeframe`，與同檔 `D-002-C0` (0.5)「實作新增之欄位名須逐字採用 trigger_timeframe／feature_timeframe、禁用裸 timeframe 當新欄名」互斥；實作者無法同時滿足兩條義務。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md` L36＝(0.5) 禁令；L136＝Task 9.1 強制鍵名 `EventSplitPlan.summary["discarded_per_tf_rows_by_timeframe"]`；L133–134 雖正確寫 discarded 之 dict 鍵為 `feature_timeframe`，但 summary 鍵本身仍裸用 `timeframe`。RECHECK: `grep -n 'by_timeframe\|禁用裸' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5

[BLOCKING] 信心度=High。驗收時一邊要求「鍵名逐字＝Task 9.1」、一邊要求「新欄名合 C0」⇒ 必有一條紅或假綠（改名則 9.1 斷言紅；不改名則 C0 違規）。**修法**：將 summary／API／前端鍵**統一**改為不含裸 `timeframe` 之名，例如 `discarded_per_tf_rows_by_feature_timeframe`（或更短但須含 `feature_timeframe` 字面）；同步 §V ASSERT 與 mutation `01`–`03` 的鍵名。**可行性**：此鍵尚未落地（全 repo 僅 SPEC 出現）；改名零遷移成本，只改 SPEC 字面與後續實作契約。

---

## GROK-R2-P1-02

**斷言**: Task 9.2「assignments／purged／**clusters** 三表各加 `feature_timeframe`」與 Task 9.3「時間簇仍按**事件級** interval 合併、同事件多 feature TF 同簇」及既有 `clusters.set_index("event_id")` 消費者互相衝突——照 Task 9.2 字面做會破壞簇表事件級唯一性或留下無定義欄。

**碼證**: SPEC L145「三表各加 `feature_timeframe`」；L156「時間簇仍按事件級 interval 合併」；`event_split.build_time_clusters`（`event_split.py:59-75`）一 manifest 列→一 `event_id` 列、無 feature TF 維；`tables.py:229`／`:373` 對 `clusters` 做 `set_index("event_id")` 後 `.loc`／`reindex`（預設事件唯一）。若為加欄而把 clusters **展開**成 `(event_id, feature_timeframe)`，`set_index("event_id")` 變非唯一→與本 epic 要消的靜默類同構；若**不展開**只加一欄，多 feature TF 事件該填哪個值無定義。RECHECK: 讀 Task 9.2／9.3 兩句＋`tables.py:229,373`＋`build_time_clusters` 回傳欄。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/tables.py#843ba7f68172;momentum/Analysis/event_samples/event_split.py#943d0721b059

[BLOCKING] 信心度=High。不改則 Task 9.2 實作時二選一皆錯：要嘛弄破 `tables`／discrimination 的簇索引，要嘛寫入無語意的 `feature_timeframe` 佔位。**修法**：Task 9.2 改為「`assignments`／`purged` 加 `feature_timeframe`；**`clusters` 維持事件級、不加該欄**」（與 Task 9.3 同簇句、C5 (5.2)、mutation `18` 之「勿過度涵蓋 event-level」一致）。若未來要 per-TF 重述簇列，須另開任務並改所有 `set_index("event_id")` 消費者，不在本句偷渡。**可行性**：`build_time_clusters` 今日即無 TF 欄；從 Task 9.2 刪除 clusters 即可，零碼阻礙。

---

## 11 類快掃（§1）

1. 矛盾／互斥：C0↔Task 9.1（P1-01）；Task 9.2 clusters↔Task 9.3／消費者（P1-02）  
2. 漏項：本家 R1 六條已補；新漏＝上列  
3. 不可測：C3／C6／9A 皆有 ASSERT；上列互斥會讓驗收命令自相矛盾  
4. quant：C3 反例構造支持不過嚴  
5. 過度工程：無（兩階段仍合理）  
6. OOM：無  
7. Cache：無本輪新洞  
8. API／型別：9A 鍵名待 C0 對齊（P1-01）  
9. 測試：18 mutation 對舊面足夠；clusters 誤加欄無對應「反向」mutation（修 P1-02 時可考慮加「clusters 被加 feature_timeframe 應紅」或併入 `18`）  
10. Agent 可執行：Task 9.2「三表」字面會誤導  
11. 短命工：無（9A 揭露欄非白工）

## 主動攻擊面（停輪③；成功開洞見上）

1. 本家 R1 六條逐條對修訂落點 → 皆 CLOSED  
2. C3 合法異側構造 → 機械可、語意不可；不過嚴  
3. C6 消費者是否要列數掛舊名 → 否；支持事件數  
4. 全檔裸 `timeframe` 掃描 → **L136 新鍵互斥**（P1-01）  
5. C0／C3／C6／Task 9.4 交叉衝突 → **clusters 三表一刀切**（P1-02）  
6. mutation 18 與 event-level 過度涵蓋 → 與 P1-02 同向，強化「clusters 不該複合鍵化」  
7. survivor 六鍵是否仍要複合鍵 → **否**：`event_context_from_windows` 雜湊事件窗集合，屬事件級；不開洞  

不修就進 Task 9.x：①9A 鍵名與 C0 驗收互相打臉；②clusters 加欄弄破事件級索引或寫入無定義值。

---

## 被當成事實的未驗證假設（§0 彙總）

1. 「修訂已消掉 R1 全部洞」——對**本家六條**成立；但修訂**新引入** P1-01／P1-02。  
2. 「C3 不誤殺」——本輪反例構造失敗 ⇒ 支持；未跑真實多 TF IC e2e（§N 誠實邊界同）。  
3. 「C6 事件數正確」——消費者碼證支持。  
4. 「C0 已清歧義」——被 L136 否證。

ASSUMPTIONS_VERIFIED: 本家 R1 六條 CLOSED（逐條對讀）；C3 異側機械可／語意不合法；C6 消費者要事件數；L136 與 C0 (0.5) 互斥；Task 9.2 clusters 與 tables.set_index(event_id) 衝突  
TESTS_RUN: 探針 `probe_mixed_side.txt`／`probe_n_train_consumers.txt`（review 未改碼）；交件前 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r2-grok.md --family grok`  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r2-grok.md`

VERDICT: blocked
BLOCKED-BY: GROK-R2-P1-01,GROK-R2-P1-02
CLOSED: GROK-R1-P1-01,GROK-R1-P1-02,GROK-R1-P1-03,GROK-R1-P2-01,GROK-R1-P2-02,GROK-R1-P2-03
STATUS: DONE
