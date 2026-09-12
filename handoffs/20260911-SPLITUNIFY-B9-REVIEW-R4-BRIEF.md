# SPLITUNIFY D-002 閉合輪 R4

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R4
findings-round: R4

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 這一輪要做什麼

R3 你們開了 15 條、收斂為七群、**全部採納零駁回**，`docs/SPLITUNIFY_SPEC.D-002.md` 已第四次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**。另請攻修訂本身引入的新問題——
🔴 本輪修訂**動到了 R2 的既有裁決**（見下表第 3 列），那是最需要被挑戰的一處。

## 七群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| 核心目標沒補到 | `Task 9.2` 只改被呼叫端，caller 仍必傳 `selected_timeframe` ⇒ 生產路徑丟棄行為原封不動 | `Task 9.2` 檔案範圍改為含 `pipeline.py:747`，逐字寫出現行呼叫 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`，加「只改被呼叫端不算完成」之驗收重點，並要求**一併移除 `str()`**（留著會把 `None` 轉成字面 `"None"`） |
| `(3.1)` 只是把問題往後推 | 「須先定義可比時點」不是定義，實作者拿不到可操作判準 | `(3.1)` 改為**事件級錨定**：split 側一律由 `decision_at_ms` 決定，各 feature TF 之 `feature_cutoff_ms` 只用於取特徵、**不參與判側** ⇒ 同事件各 feature TF **恆**同側為**結構性保證**，非待驗證之約束 |
| 🔴 **連帶修訂 R2 裁決** | （由 `(3.1)` 定案推導，非你們直接提出） | `(3.2)` 異側處置由「整事件 purged、沿用 `interval_crosses_split_boundary` 字面」改為 **fail-closed `AlignmentViolationError`**。理由：R2 該裁決之前提是「可比時點未定義、異側屬合法」；`(3.1)` 消除該前提後，異側只可能來自實作退回 per-TF 判側 ⇒ 屬缺陷，purge 會把缺陷偽裝成樣本流失。既有 `interval_crosses_split_boundary` **維持原義**（標籤區間跨邊界、事件級）不動 |
| 重複 guard 先後未定 | `split_projection.py:284-289` 與 `:441-444` 兩道 guard 與 `D-002-C3` 的先後沒寫 | `Task 9.2a` 定案：兩道一律改為**複合鍵唯一**判準（同事件不同 feature TF 為合法），且**須先於** `D-002-C3` 同側檢查執行（鍵不唯一時「是否同側」無從定義）；錯誤型別維持現狀 |
| §V 驗收缺口 | purged 路徑無複合鍵唯一斷言；`Task 9.1` 的「API 與前端」無具體落點；`Task 9.5` 未指名 golden 生成入口 | §V 補 `purged` 複合鍵唯一與 `n_event_tf_rows_purged`；`D-002-C3` 斷言改為正例（cutoff 不同仍同側且不誤 purge）＋反例（構造異側 THEN raise）成對；`Task 9.1` 指名 `api/routes/case.py:487`／`case_import_service`／`EventAnalyzeResponse.summary`／`EventTablesPanel.tsx:347,361`；`Task 9.5` 指名 `scripts/freeze_splitunify_golden.py` 之 `_plans()`／`_event_keys()`／`_build_actual()`／`main()` |
| `M-SU-D2-19` 方向錯 | survivor 六鍵本就是事件級，「未隨複合鍵調整」不是缺陷 | 改為**反向 mutation**：六鍵**被改成含 feature TF** 才是缺陷；`M-SU-D2-14`／`15` 之應紅測試隨 `(3.2)` 改為 raise 斷言 |
| TODO 狀態同步時點 | `SU-RESID-2` 在 TODO §E 仍是 `needs-research`，何時改沒寫 | §N 補：**三家戳記通過後、`Task 9.1` 動工前**同步改寫，不得提前亦不得遺漏 |

## 前提（範本 §0；請逐條挑戰）

fact-verified: 七群 15 條全部採納零駁回 → `handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md`
fact-verified: `pipeline.py:747` 逐字為 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))` → 主委實跑 `grep -n` ＋ `sed -n '740,755p'`
fact-verified: `EventAnalyzeResponse.summary` 型別為 `Dict[str, Any]`（`api/models/event_import_models.py:306-308`）、前端對應 `Record<string, unknown>`（`frontend/src/lib/types.ts:3176`） → 主委實跑 grep
fact-verified: 第四次修訂後三道閘皆 rc=0（`obligation_block_check.sh`／`doc_format_precheck.sh`／`spec_xref_check.sh --synth` 對 r1/r2/r3 三份 synth） → 主委實跑

assumed: `(3.1)` 之事件級錨定**不會**讓某個 feature TF 拿到「該側不該看到」的特徵
→ 否證觀測：構造一事件其 `decision_at_ms` 落 test 側，但某 feature TF 之 cutoff 早於 train/test 邊界 ⇒ 該列特徵來自 train 期。這**是否**構成洩漏或資訊不足？我跑了: **沒跑**，這是本輪最該被攻的一點
assumed: `(3.2)` 改 fail-closed **不會**讓現行合法資料在 `Task 9.x` 上線後開始 raise
→ 否證觀測：指出現行 `derive_event_split_from_plans` 中有哪條路徑會在合法輸入下產生同事件異側／我跑了: **沒跑**
assumed: 複合鍵唯一 guard 先於同側檢查**不會**讓真正的異側缺陷被前一道 guard 吃掉而改報成重複鍵
→ 否證觀測：構造同時「鍵重複」且「異側」之輸入，看錯誤訊息是否誤導／我跑了: **沒跑**
assumed: 移除 `str()` 後 `selected_timeframe=None` 之路徑在下游（`per_tf` 過濾、summary 鍵）**皆**有定義
→ 否證觀測：指出某下游在 `None` 下會 `TypeError` 或產空表／我跑了: **沒跑**

## 必答（成對，缺一不算完成）

1. **你自己 R3 的 finding 是否閉合**？逐條給判定，並說明你用什麼方式確認。
2. **`(3.1)` 事件級錨定**：上述「某 feature TF 之 cutoff 早於 split 邊界」之情境，是否構成洩漏、資訊不足、或兩者皆非？給碼證或反例，**不得只讀 SPEC 推論**。
3. **`(3.2)` 由 purge 改 fail-closed 是否正確**：這是本輪對 R2 裁決的修訂。你同意還是反對？反對的話，請說明在 `(3.1)` 成立下「異側」還能怎麼合法產生。
4. **`Task 9.2` 這次是否真的補上核心**：`pipeline.py:747` ＋ 移除 `str()` ＋ producer 可選化，三者到位後 `SU-RESID-2` 的丟棄行為是否確實消失？還缺哪個 caller 或設定來源？（🔴 請自己 grep，不要只信本 brief 的「唯一生產 caller」）
5. **修訂引入的新問題**：`(3.2)` 改 raise、guard 先後、§V 新斷言、`M-SU-D2-19` 反向，彼此或與 D-001 既有義務、與 `D-002-C6` 量詞分離有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**；③🔴 **禁以「無 finding」當停輪**；
④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R4-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：
- 跨輪未閉之條目請在本輪**以新 ID 重開**（例如 `<家族>-R4-P1-NN`），或於正文敘述，**不要**填進裁決欄；
- 他家的 ID 一律不得填入任一裁決欄。

本輪各家待閉合的自家 R3 ID：見 `handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md` 之 roster 欄。

裁決塊三行分寫。
