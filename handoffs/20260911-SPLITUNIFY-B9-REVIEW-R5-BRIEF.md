# SPLITUNIFY D-002 閉合輪 R5

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R5
findings-round: R5

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

本輪**禁改碼、禁改 SPEC**，屬唯讀審查。`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為
「**動工前**若所依 reconcile/SPEC 的 `RECONCILE-STAMP` 未全數 APPROVED → 輸出
`STATUS: BLOCKED — reconcile 未核可`，**不動工**」——該條管的是**實作動工**，
不是唯讀審查。**上游收斂檔沒有戳記是正常狀態**：戳記在審查收斂之後才蓋，
若以「沒戳記」為由拒審，戳記與審查互為前置，任何票的第一輪審查都永遠無法開始。

事實佐證：本批 `b9` 的 R1／R2／R3 收斂檔之 `RECONCILE-STAMP` 數**皆為 0**，
而三家在那三輪分別交付了實質 findings。R4 有一家以此為由零實質審查，已被駁回並
記為**欠一輪**，其 R3／R4 應審內容併入本輪。

## 這一輪要做什麼

R4 三家共 8 條、歸五群：**7 條採納、1 條駁回**，`docs/SPLITUNIFY_SPEC.D-002.md` 已第五次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**；另攻本輪修訂引入的新問題。

🔴 **本輪最該被攻的主張**：我宣稱「`Task 9.2` ＋ `Task 9.2a` ＋ `Task 9.2b` 三者到位後，
`SU-RESID-2` 的靜默丟棄才會消失」。這個主張**已經被推翻過三次**（每次都是我以為補齊了）：
R3 說「沒改 caller」→ 補了 caller；R4 說「四參數閘會先擋死」→ 補了該閘。
**請假設還有第四層我沒看到，並自己從 `EventSamplePipeline.run` 的入口一路走到 `assignments` 產出。**

## 五群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| G1 四參數閘（grok 獨得） | `pipeline.py:723-732` 要求四者同時非 `None`，傳 `None` 會在抵達 `build_event_keys` 前 fail-closed | `Task 9.2` 檔案範圍加 `pipeline.py:723-732` 與 `:711-715` docstring；投影門檻改三者同時，`selected_timeframe` 降可選；驗收改**端到端**經 `EventSamplePipeline.run` |
| G2 (3.1) 無施工落點 | `split_projection.py` 全檔 `decision_at_ms` 命中 0，`:530-553` 仍逐列用 `feature_cutoff_ms` 判側 | **新增 `Task 9.2b`**：以 `manifest.table` 之 `decision_at_ms` 每事件定側並廣播；答案窗 purge 改按事件側；`feature_cutoff_ms` 不再參與 `split_label` |
| G3 §V 驗收缺口 | `Task 9.2` 斷言只驗 schema，`M-SU-D2-20` 無對位句 | §V 增端到端全量列數斷言＋「`selected_timeframe=None` 不 raise」；原 schema 句改掛 `Task 9.2a`；新增 `Task 9.2b` 錨定反例；mutation 20 → **23 條** |
| G4 (5.2) 舊語意 | 仍寫 selected-only／event-only，與 `Task 9.2`／`9.2a` 矛盾 | `(5.2)` 改寫為**落地後契約**（全量複合鍵 producer、兩表含 `feature_timeframe`、`clusters` 維持事件級、側別以 `decision_at_ms` 為錨） |
| G5 拒審（**駁回**） | 以上游未戳記為由不審 | 見本檔開頭；該家欠一輪，本輪補審 |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R4 八條歸五群、7 採納 1 駁回 → `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md`
fact-verified: `pipeline.py:723-732` 逐字為 `given = [k for k, v in projection_args.items() if v is not None]` 後 `if given and len(given) != len(projection_args): raise` → 主委實跑 `sed -n '705,750p'`
fact-verified: `split_projection.py` 全檔 `decision_at_ms` 命中數為 0，`:531-533` 為 `cutoff = int(rec["feature_cutoff_ms"])` → 主委實跑 `grep -c` 與 `sed`
fact-verified: `manifest.table` 確有 `decision_at_ms`（`event_split.py:62,68,147` 已在使用）→ 主委實跑 grep
fact-verified: 第五次修訂後 obligation／format rc=0、xref 對 r1–r4 四份 synth 皆 rc=0、歸戶與 completeness rc=0 → 主委實跑

assumed: `Task 9.2`＋`9.2a`＋`9.2b` 三者到位後，生產路徑不再丟列
→ 否證觀測：從 `EventSamplePipeline.run` 入口走到 `assignments`，指出**第四處**會讓全量路徑失效的關卡／我跑了: **沒跑**（前三輪各被推翻一次，本輪假設仍未實跑驗證）
assumed: `Task 9.2b` 之「以 `decision_at_ms` 每事件定側並廣播」不會與 `purged` 的答案窗判定衝突
→ 否證觀測：構造事件其 `decision_at_ms` 落 train 而 `label_end_ms >= test_start_ms`，檢查改按事件側判定後 purge 行為是否與現行逐列版本不一致／我跑了: **沒跑**
assumed: `(5.2)` 改寫為「落地後契約」不會讓實作者誤以為現況已是如此
→ 否證觀測：指出 `(5.2)` 現文有哪一句在讀者不看 `D-002-C4` 時會誤判現況／我跑了: **沒跑**
assumed: mutation 23 條已覆蓋三個 Task 與四參數閘
→ 否證觀測：指出第 24 條該有而沒有的 mutation／我跑了: 逐處對照，**未**實作驗證

## 必答（成對，缺一不算完成）

1. **你自己 R4 的 finding 是否閉合**？逐條給判定並說明確認方式。（R4 零實質審查那一家：請改答「你的 R3 條目是否閉合」＋本輪完整審查）
2. **第四層在哪**：從 `EventSamplePipeline.run` 入口走到 `assignments` 產出，列出**所有**會讓「全量多 feature TF」失效的關卡。找不到第四層也要說明你走過哪些分支。
3. **`Task 9.2b` 的 purge 語意**：答案窗 purge 由「逐列 `in_train`」改為「按事件側」，行為差異是什麼？給反例或碼證。
4. **`(3.2)` fail-closed 與 `Task 9.2b` 的上線順序**：若先上 `(3.2)` 的 raise 而 `9.2b` 未完成，合法輸入會不會開始 raise？規格有沒有把這個順序寫死？
5. **修訂引入的新問題**：`Task 9.2b`／§V 新斷言／`(5.2)` 改寫／三條新 mutation，彼此或與 D-001、`D-002-C6` 有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R5-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
