# SPLITUNIFY D-002 閉合輪 R7

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R7
findings-round: R7

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。**上游收斂檔沒有戳記是正常狀態**：戳記在審查
收斂之後才蓋；若以「沒戳記」為由拒審，戳記與審查互為前置，任何票的第一輪都無法開始。

## 這一輪要做什麼

R6 三家共 16 條、歸八群、**全部採納零駁回**，`docs/SPLITUNIFY_SPEC.D-002.md` 已第七次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**；另攻本輪修訂引入的新問題。

🔴 **本輪的重點與前六輪不同**。前六輪都在問「還有沒有第 N 層沒補到」，而 R6 的結果顯示
**方向已經反轉**：八群裡有四群是**我派工過度或派錯**（物化層本該維持事件級、16 處清單用形狀
判準誤列、`Task 9.1` 指的 route 永遠走不到、前端匯出 Map 改鍵會弄壞使用者的 CSV）。

所以本輪請**兩個方向都攻**：
- **仍漏的**：`Task 9.2`/`9.2a`/`9.2b`/`9.3`/`9.4`/`9.5` 合起來，是否還有讓全量路徑失效的關卡？
- **🔴 過度的**：第七次修訂新寫的每一條「維持事件級／排除於遷移之外」，是否有**判錯**的？
  我這次是自己逐處讀了 16 處才分類的——**請挑戰我的分類**，特別是 (甲) 那一類：
  若某處其實該改而我判成「維持」，複合鍵上線後它會靜默取到錯的列。

## 八群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| I1 不等式在隔離帶不等價（三家） | gap 上集合成員給 `purged`、不等式給 `train` | `Task 9.2b` 改**三段式且順序不得調換**：先驗是否落在隔離帶 `[split_point, split_point+purge_gap+embargo)`（落入即 fail-closed raise）→ 再用不等式定側 → 落在兩 plan 覆蓋區外同樣 fail-closed |
| I2 (3.2) 抓不到 purged∩assignments（三家） | `purged` 無 `split_label`，只驗唯一性結構上抓不到 | `Task 9.2b` 增跨表互斥斷言；答案窗 purge 改**按事件側一次決定並廣播** |
| I3 物化層與下游契約 | `_combined_columns` 同名欄 loud 拒；記帳不變式用 `nunique()`；`baseline`／`pattern_bridge` 以事件級 Index 交集 | `Task 9.3` 對 `feature_materialization` **整段改寫為維持事件級橫向合併** |
| I4 形狀規則自相矛盾 | `Task 9.3` 既要 `tables` 改複合鍵、又要事件級表不變 | `D-002-C5` (5.1) **全面重新分類**為三類（甲事件級維持／乙複合鍵改／丙去重取唯一值） |
| I5 `Task 9.1` 未擇一（三家） | 規格要實作者擇一，自己沒擇 | **定案採 (b)**；原指名之四個落點**全部作廢**（字面保留供追溯） |
| I6 前端 Map 改鍵破壞匯出 | `eventExport.ts` 之 record 無 `feature_timeframe`，改鍵全數 miss | `Task 9.5` 將該 Map **排除**於複合鍵遷移之外 |
| I7 門檻被 TF 膨脹 | `tier_min` 與 `per_symbol_n` 吃列數 | `Task 9.4` 增該路徑改 `event_id` 去重計數，**並要求同批補終端揭露** |
| I8 mutation 以 OR 合併兩缺陷 | 違反一 mutation 一 defect | 拆為 `M-SU-D2-23`／`26`，條數 25 → **26**（主委自數：表列 26、ID 01–26 連續） |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R6 十六條歸八群、全部採納 → `handoffs/reconcile/20260911-splitunify-b9-review-r6/synth.md`
fact-verified: 隔離帶區間定義逐字取自 `split_preview.holdout_test_row_index`（`split_point = floor((1-oos_test_size)*n)`、`test = arange(split_point+purge_gap+embargo, n)`、train = `arange(0, split_point)`）→ 主委實跑 `sed`
fact-verified: `purged` 僅 `["event_id","reason"]` 兩欄、無 `split_label` → 主委實跑 `split_projection.py:556`
fact-verified: `_combined_columns:22-32` 逐字「多 TF 特徵欄名合併；衝突 ⇒ loud 拒」；`feature_materialization:138-140` 之 `n_input` 用 `nunique()` → 主委實跑
fact-verified: mutation 表列 26、ID 01–26 連續、正文宣稱 26 → 主委實跑計數與排序
fact-verified: 第七次修訂後 obligation／format rc=0、xref 對 r1–r6 六份 synth 皆 rc=0 → 主委實跑

assumed: `D-002-C5` (5.1) 之三分類**逐處判對了**
→ 否證觀測：指出被我判為「(甲) 事件級維持」的某一處，其實在複合鍵上線後會**靜默取到錯的列**／我跑了: 逐處讀碼取證，但**未**以多 TF fixture 實跑每一處
assumed: `Task 9.2b` 三段式判準**覆蓋所有位置情形**
→ 否證觀測：構造一個既不在隔離帶、也不在兩 plan 覆蓋區、又不在索引界外的位置／我跑了: **沒跑**
assumed: 答案窗 purge 改「按事件側一次決定」**不會改變單一 feature TF 之現行行為**
→ 否證觀測：以單 TF fixture 對照改前改後之 `purged` 集合／我跑了: **沒跑**（這條若不成立會動到既有 golden）
assumed: `Task 9.1` 採 (b) 後，IC 主線**確實有** `discarded` 可揭露
→ 否證觀測：指出 IC 投影路徑上 `build_event_keys` 的 `discarded` 如何傳到 IC 的回應與畫面／我跑了: **沒跑**，只確認了事件掃描端不可行

## 必答（成對，缺一不算完成）

1. **你自己 R6 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **挑戰我的三分類**：`D-002-C5` (5.1) 的 (甲)(乙)(丙) 有沒有判錯的？特別是 (甲) 類——
   若某處其實該改，請給出「複合鍵上線後它會取到哪一列、錯在哪」的具體情境。
3. **三段式判準是否完備**：有沒有位置落在三種情形之外？答案窗 purge 改事件側後，
   單一 feature TF 的現行行為會不會變（會不會動到既有 golden）？
4. **`Task 9.1` 採 (b) 之後**：IC 主線上的 `discarded` 要怎麼傳到回應與畫面？還缺哪些具名落點？
5. **修訂引入的新問題**：I1–I8 的落點彼此、或與 D-001／`D-002-C6`／既有 golden 有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R7-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
