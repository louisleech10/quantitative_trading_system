# SPLITUNIFY b9 偵察 consult R1（claude／主委自產）

task-id: 20260911-SPLITUNIFY-B9-CONSULT-R1
family: claude
findings-round: R1

🔴 本檔為**主委自產版**，依「Claude 自產一版」規則與三家平行產出。
撰寫順序：先自行 grep／讀碼／實跑探針並寫完結論，**之後**才讀委員交件。
撰寫時 composer 已交件，我只瞄過其小節標題（未讀內文）以避免重複勞動；
下列結論與探針輸出均為我自己獨立取得。

## 被當成事實的未驗證假設（§0）——含我自己 brief 中的 assumed

| 我在 brief 寫的前提 | 自我判定 | 依據 |
|---|---|---|
| assumed:「D-001 列的六個檔就是**全部**的單鍵消費面」 | 🔴 **不成立（我自己否證）** | 至少還有：①`frontend/src/app/search/page.tsx:825-835` 以 `event_id` 為鍵的 `Map`（後者覆蓋前者）②`tests/golden/splitunify/clusters_oracle.json` 的 fixture 逐筆以 `event_id` 列出 |
| assumed:「複合鍵可在不動 `EventSplitPlan.assignments` schema 前提下落地」 | **仍為 assumed** | 未驗；`assignments` 目前欄位為 `event_id／symbol／split_label`，無 `timeframe` 欄 |
| assumed:「現行 fail-closed 真的擋得住多 TF 同批」 | 🔴 **不成立（實跑否證）** | 見必答 5：多 TF 同批**不被擋**，未選中的 TF 被**靜默丟棄** |

## 必答 1 — 消費面盤點

**立場：D-001 列的六處是主鏈，但不是全部；至少還有前端與 golden 兩處。**

| 消費點 | 碼證 | 依賴形態 |
|---|---|---|
| `feature_materialization.py:53` | `merge(..., on="event_id", validate="many_to_one")` | 事件表被當成 event_id 唯一 |
| `feature_materialization.py:132` | `set_index("event_id")` | 產出以 event_id 為唯一索引 |
| `baseline.py:92,106` | docstring 明寫「index=event_id」；取 test 段 event_id 清單 | **繼承**上游 set_index 的唯一性 |
| `pattern_bridge.py:125` | `assign.set_index("event_id")["split_label"]` | 非唯一時 `.loc[eid]` 回傳 Series |
| `tables.py:214,229` | `set_index("event_id")` 兩處 | 同上 |
| `ic_feed.py:108,109,118` | 兩處 `set_index("event_id")`＋`ev.loc[keep["event_id"], …]` | 非唯一時取回多列 |
| `dedupe.py:120` | `merge(..., validate="one_to_one")` | 多 TF 下必爆 |
| 🔴 `frontend/src/app/search/page.tsx:825-835` | `new Map<string,…>()` 以 `canonicalEventId(symbol, timeframe, t0)` 為鍵，再 `byEventId.get(String(rec.event_id))` | **不在 D-001 六面內** |
| 🔴 `tests/golden/splitunify/clusters_oracle.json` | fixture 逐筆 `{"event_id": …}` | **不在 D-001 六面內**；多 TF 後 oracle 結構須擴充 |

**掃描範圍（誠實邊界）**：我 grep 了 `momentum/Analysis/event_samples/`、`api/`、`frontend/src`、
`tests/golden/`。`api/` 在我的型樣（`set_index("event_id")`／`on="event_id"`／`validate=`）下**零命中**，
但我**沒有**逐檔讀 `api/services/`，不排除以其他形態（dict 推導、`groupby().first()`）依賴唯一性。

## 必答 2 — 失效形態（會報錯 vs 靜默錯）

**會報錯**（相對安全）：`feature_materialization.py:53` 的 `validate="many_to_one"`、
`dedupe.py:120` 的 `validate="one_to_one"` — pandas 會直接丟 `MergeError`。

🔴 **會靜默取到錯的值**（真正危險）：
1. `pattern_bridge.py:125` `assign.set_index("event_id")["split_label"]` 之後若以 `.loc[eid]` 取值，
   非唯一索引回傳的是 **Series 而非純量**；下游若做 `== "test"` 比較會得到 Series，
   在 `if` 中觸發歧義錯誤**或**被 `.any()`／`.all()` 之類吸收而靜默錯判。
2. `frontend/src/app/search/page.tsx:829` 的 `byEventId.set(...)`：同鍵**後者覆蓋前者**，
   前端顯示的原始列會是最後一筆，**完全無聲**。註解自己寫著「位置對不上就會張冠李戴」——
   換成複合鍵後，這個 Map 就是新的張冠李戴來源。
3. 未選中的 TF 被靜默丟棄（見必答 5 的 C 情形）。

## 必答 3 — schema 影響

`EventSplitPlan.assignments` 現行欄位為 `event_id／symbol／split_label`，**無 `timeframe` 欄** ⇒
複合鍵落地必須加欄，屬 schema 變更。`receipts.per_tf` 本來就有 `timeframe`，不需改。
`clusters` 需視必答 4 的折疊語意而定。
golden 位移面：`tests/golden/splitunify/`（含 `clusters_oracle.json`）與 IC 側 digest 皆可能位移——
**我未實跑確認**，這是 assumed。

## 必答 4 — cluster 折疊語意

**立場：時間簇應按「事件級 interval」合併，同一 calendar 事件的不同 TF 落在同一簇。**

理由：簇的目的是承載「同一段時間內的事件彼此不獨立」這個統計事實，而它由 `label_start_ms`／
`label_end_ms` 的時間區間決定，與用哪個 TF 的特徵去描述它無關。若按 `(event_id, timeframe)` 各自成簇，
同一事件的多個 TF 會被當成多個獨立樣本 ⇒ **統計上等於偷偷放大樣本數**，
與本 epic「一個事件批只有一條驗證邊界」的目的直接矛盾。

誠實邊界：這是我的立場，**未實跑**驗證 `dedupe` 現行折疊是否已按 interval。

## 必答 5 — 現行 fail-closed 真實性（實跑）

探針：`build_event_keys(receipts, selected_timeframe=…)`，四種情形。

```
A  NO_RAISE 產出 2 列；event_id=['e1', 'e2']            （選定 TF 下唯一 ⇒ 放行，正確）
B  RAISED  ValueError: timeframe='1h' 下事件有多列 per_tf：['e1']——本票要求每事件恰一列（殘留 SU-RESID-2）
C  NO_RAISE 產出 2 列；event_id=['e1', 'e2']            🔴 同批含 1h 與 4h，只選 1h，4h 兩列被靜默丟棄
D  RAISED  ValueError: 1 個事件在 timeframe='1h' 下缺 cutoff（例：['e2']）——缺就是缺，不補預設
```

**立場：fail-closed 位置合理（`build_event_keys`，在進 derive 之前），但它擋的不是「多 TF 同批」。**
它擋的是「同一 TF 下同一事件重複」（B）與「選定 TF 下缺 cutoff」（D）。
**C 情形完全不擋**：多 TF 同批共存時，未被 `selected_timeframe` 選中的列**靜默消失**，
沒有例外、沒有警告、報告也不會說「本次丟棄了 4h 的 N 列」。

## CLAUDE-R1-P1-01

**斷言**: 多 TF 同批時，未被 `selected_timeframe` 選中的 `per_tf` 列被**靜默丟棄**且不揭露，
使用者無從得知本次分析只用了哪一個 TF、丟掉了什麼。

**碼證**: `split_projection.py:279` `selected = per_tf.loc[per_tf["timeframe"] == str(selected_timeframe)]`
——直接切片，未比對「被丟棄的列數」亦未寫入任何 receipt／summary；
實跑 C 情形：per_tf 四列（e1/e2 × 1h/4h）、選 1h ⇒ `NO_RAISE`、產出 2 列，無任何提示。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#99bfddace904; docs/SPLITUNIFY_TODO.md#e44da6448b01

[P1/high] 失效：使用者以為分析涵蓋了他餵入的所有 TF，實際只用了一個；這與本 epic
「報告不得隱瞞它做了什麼」的既有原則同型。修法（b9 範圍內）：`build_event_keys` 回傳
或 summary 增列「discarded_per_tf_rows_by_timeframe」，在 SU-RESID-2 落地前至少**揭露**；
落地後改為複合鍵不再丟棄。可行性：局部，不動 schema 即可先做揭露。

## 誠實邊界

- IC 端到端真實 run **未跑**。
- `api/services/` 未逐檔讀，只做型樣 grep。
- 必答 3 的 golden 位移面、必答 4 的 `dedupe` 現行折疊語意，皆**未實跑**確認。

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: 必答 1 之九個消費點碼證、必答 2 之靜默形態、必答 5 之四情形實跑
TESTS_RUN: 自產探針 `probe_b9_multitf.py`（A/B/C/D 四情形，輸出如上）；本輪未改碼、未跑測試套件
FAILURES_SEEN: C 情形之靜默丟棄（升為 CLAUDE-R1-P1-01）
SCOPE_CHANGES: none（偵察，未改碼）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改動）

STATUS: DONE
