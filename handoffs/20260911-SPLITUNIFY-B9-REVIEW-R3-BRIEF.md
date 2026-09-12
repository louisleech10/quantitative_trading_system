# SPLITUNIFY D-002 閉合輪 R3

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R3
findings-round: R3

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 這一輪要做什麼

R2 你們開了 11 條、收斂為九群、**全部採納零駁回**，D-002 已第三次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**。另請攻修訂本身引入的新問題。

## 九群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| 同側約束誤 purge | 資料契約未要求各 feature TF 之 cutoff 對齊，合法事件可能天然異側 | `(3.1)` 改為**先要求定義「可比時點」**，並明寫「實作不得在未定義可比時點前逕行判定異側」；同側要求改為在該定義成立之下才適用 |
| 混側 purge 字面無真相源 | 只說「具名字面」未指定是哪個、也未說要不要進封閉值集 | `(3.2)` 定為**沿用既有** `interval_crosses_split_boundary`，真相源為事件匯入契約之 `split_purge_reasons`，**不新增** reason 字面 |
| 三量一刀切不成立 | `baseline` 的 `n_test` 是實際模型輸入樣本數 | `(6.2)` 改為**逐消費者定義**：報告分母／前端／wiring 維持事件數；`baseline` 之 `n_test` 維持樣本數語意，不得改判 |
| 9B 未要求停止單選 | 只加欄位，`SU-RESID-2` 的丟棄行為原封不動 | 新增 **`Task 9.2`（producer 停止 `selected_timeframe` 單選、輸出全量 keyed rows）**，並標為本批核心；原 schema 工作降為 `Task 9.2a` |
| clusters 粒度衝突 | 要加欄又要維持事件級，weight／count／golden 語意未定義 | `Task 9.2a` **定案：`event_split.build_time_clusters` 之 `clusters` 不加該欄、維持事件級**，同事件多 feature TF 共用同一簇列 |
| mutation 目錄不完整 | 只有前綴加序號，無完整 ID 與應紅測試；survivor hash 無對應 | mutation 改為**表格共 20 條**，每列具完整 ID／改壞什麼／應紅之測試；新增 `M-SU-D2-19`（survivor 六鍵雜湊）與 `M-SU-D2-20`（producer 保留預設單選） |
| timeframe 命名互斥 | (0.5) 禁裸 `timeframe`，作者自己卻定了含它的新鍵；既有 wire 欄位去留未說明 | 新增 **(0.6)**：既有欄位（含 `per_tf.timeframe`）原樣保留不改名不加 alias；新增欄位須分名。summary 新鍵改名為 `discarded_rows_by_feature_tf` |
| 觸及面列出不存在章節 | 宣告仍寫 `D-002-C1`／`C2`，且義務結構閘 rc=1 | 宣告改列實際存在之 `C0`／`C3`／`C4`／`C5`／`C6`；21 條義務項行型改為白名單形狀、5 處裁決編號移出正文。`obligation_block_check.sh` 現為 **rc=0** |
| sentinel | — | 無需修訂 |

## 前提（範本 §0；請逐條挑戰）

fact-verified: 九群 11 條全部採納零駁回 → `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md`
fact-verified: 第三次修訂後三道閘皆 rc=0 → `obligation_block_check.sh`／`doc_format_precheck.sh`／`spec_xref_check.sh --synth` 主委實跑
fact-verified: 前一版之義務項行型缺陷由 `obligation_block_check.sh` 檢出，該閘在前一版**未被跑到** → 主委自陳

assumed: `(3.1)` 的「可比時點」前提**已足以**讓同側判定不再誤殺
→ 否證觀測：在該前提下仍能構造出合法事件被誤 purge 的情境／我跑了: **沒跑**，這是本輪新寫的義務
assumed: `clusters` 維持事件級**不會**讓多 feature TF 的簇權重失真
→ 否證觀測：給出「同事件多 TF 共用一簇會使 `w=1/n` 或 `n_events_effective` 算錯」的情境／我跑了: **沒跑**
assumed: 20 條 mutation 已覆蓋 16 處消費面、9A 三層揭露與 `Task 9.2` 之 producer 行為
→ 否證觀測：指出第 21 條該有而沒有的 mutation／我跑了: 逐處對照，**未**實作驗證
assumed: `(6.2)` 的逐消費者定義**不會**在實作時退化成「各處自己決定」
→ 否證觀測：指出某消費者依本條仍無法判斷該用哪個粒度／我跑了: **沒跑**

## 必答（成對，缺一不算完成）

1. **你自己 R2 的 finding 是否閉合**？逐條給判定，並說明你用什麼方式確認。
2. **可比時點（`(3.1)`）**：在該前提下，還能構造出「合法事件被誤 purge」嗎？構造不出來也要說明你試了什麼。
3. **clusters 維持事件級**：同事件多 feature TF 共用一簇，`w=1/n` 權重與 `n_events_effective` 是否仍正確？給碼證或反例。
4. **`Task 9.2` 是否真的補上了核心**：producer 停止單選後，`SU-RESID-2` 的丟棄行為是否確實消失？還缺什麼？
5. **修訂引入的新問題**：本輪新增 `(0.6)`／`(3.1)` 前提／`Task 9.2`／`Task 9.2a`／20 條 mutation，彼此或與 D-001 既有義務有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明，R2 有兩家踩到）

findings 用 `## <你的家族大寫>-R3-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：
- R2 有一家把**跨輪**的 `CODEX-R1-P1-06` 填進 R2 檔的 `BLOCKED-BY` ⇒ `register-output` 拒收；
- R1 有一家把**他家**的 ID 填進 `CLOSED` ⇒ 同樣被拒。
- **跨輪未閉之條目**請在本輪**以新 ID 重開**（例如 `<家族>-R3-P1-NN`），或於正文敘述，**不要**填進裁決欄。

本輪各家待閉合的自家 ID：
- **codex**：`CODEX-R2-P1-01`～`P1-06`、`CODEX-R2-P2-07`、`CODEX-R2-P1-08`
- **grok**：`GROK-R2-P1-01`、`GROK-R2-P1-02`
- **composer**：R2 已 `proceed`，本輪只需確認修訂未引入新問題

裁決塊三行分寫。
