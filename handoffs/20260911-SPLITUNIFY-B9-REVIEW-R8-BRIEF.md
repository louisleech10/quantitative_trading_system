# SPLITUNIFY D-002 閉合輪 R8

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R8
findings-round: R8

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。上游收斂檔沒有戳記是正常狀態：戳記在審查
收斂之後才蓋；若以「沒戳記」為由拒審，戳記與審查互為前置，任何票的第一輪都無法開始。

## 這一輪要做什麼

R7 三家共 15 條、歸八群、**全部採納零駁回**，`docs/SPLITUNIFY_SPEC.D-002.md` 已第八次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**；另攻本輪修訂引入的新問題。

🔴 **本輪有兩個必須被攻的決策**，它們都不是「補一條就好」，而是**我在兩個互斥選項中挑了一邊**：

1. **§G (G-4)：我選了 (G-4a)——承認換錨會讓邊界事件改側，單 TF golden 於 `Task 9.2b`
   落地後重凍一次**，僅允許「因換錨而改側」這一種差異。另一選項 (G-4b)（維持 cutoff 判側
   以保 exact）我判定等於放棄 `(3.1)`，故不採。**請攻這個取捨本身**：重凍 golden 是否
   等於讓回歸錨失去意義？「僅允許一種差異」在實務上可驗證嗎？
2. **`Task 9.1`：我把終端可見性改為具名殘留**（理由類別 `blocked-by`，碼證＝`api/` 對
   `EventSamplePipeline.run` 零呼叫點）。**請攻這個判斷**：把「使用者看得到」延後到別票，
   是否讓 Phase 9A 的「消除靜默丟棄之誠實性缺陷」名存實亡？殘留理由類別選 `blocked-by`
   是否正確（而非 `needs-research` 或根本不該延後）？

## 八群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| J1 分類改了施工單沒改（三家） | `Task 9.3` 仍要求甲類改複合鍵 | `Task 9.3` 逐條改寫；`(5.3)`／`(5.4)` 舊敘事整段改為現況描述＋以 `(5.1)` 為準；`M-SU-D2-04`／`06`–`11` 七條改為**反向** mutation |
| J2 `dedupe` 粒度矛盾 | 保留集要改複合鍵與甲類互斥 | 改為事件級保留＋保留之 `event_id` **廣播**到 per-TF 列，配「兩 TF 皆存活而簇仍一列」測試 |
| J3 `Task 9.1` dataflow 未封（三家） | IC 主線只有 `holdout_boundary`、無 `discarded` 來源 | **改為具名殘留**（見上方必攻點 2）：本延伸只交付 producer 回傳＋summary 鍵＋`metadata.split_unify` 欄位 |
| J4 位置映射未定義 | `searchsorted` side／前後列歸屬皆可得不同答案 | 判準改以**時間域**表述：`<= train_last_ms` ⇒ train／`>= test_start_ms` ⇒ test／之間 ⇒ `purged`／索引界外 ⇒ raise |
| J5 隔離帶處置＋換錨改側 | golden `gap1`／`gap2` 現為 purged；換錨本身會讓邊界事件改側 | 隔離帶由 raise 改回 **`purged`**；新增 **§G (G-4)** 處理換錨與 exact 的本質衝突（見上方必攻點 1） |
| J6 `baseline` 列數與事件級物化互斥 | 物化維持事件級則 `n_test` 只能是 1 | `baseline` 之 `n_test` 更正為**事件數**；v7 之「一事件兩列、`n_test`＝2」作廢 |
| J7 `M-SU-D2-11` 與排除遷移互斥 | 正確實作就是維持 `event_id` 鍵 | 改為反向 mutation（誤改為複合鍵致匯出 extras 靜默變空） |
| J8 §V `Task 9.1` 仍指作廢三層 | 與正文互斥 | §V 三層標的同步更新為 producer／summary／`metadata.split_unify` |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R7 十五條歸八群、全部採納 → `handoffs/reconcile/20260911-splitunify-b9-review-r7/synth.md`
fact-verified: golden `gap1`／`gap2` 刻意造在隔離帶且現值為 `purged` → `scripts/freeze_splitunify_golden.py:94,101-102` 與 `tests/golden/splitunify/splitunify_golden.json`
fact-verified: `alignment.py:87-93` 之 cutoff 定義允許 `cutoff < decision` → 主委實跑 `sed`
fact-verified: `train_last_ms = int(index_ms[train_rows[-1]])` 為一行可得、與既有 `test_start_ms` 取法對稱 → 主委實跑 `split_projection.py:524-526`
fact-verified: `api/` 對 `EventSamplePipeline.run` 之呼叫點為 0 → 主委與 R7 兩家獨立 grep
fact-verified: 第八次修訂後 obligation／format rc=0、xref 對 r1–r7 七份 synth 皆 rc=0、mutation 表列 26／ID 01–26 連續 → 主委實跑

assumed: §G (G-4a) 之「重凍一次、僅允許因換錨而改側這一種差異」**在實務上可驗證**
→ 否證觀測：說明如何機械區分「因換錨而改側」與「因實作寫錯而改側」；若區分不了，(G-4a) 等於放棄回歸錨／我跑了: **沒跑**
assumed: `Task 9.1` 具名殘留**不會**讓 Phase 9A 名存實亡
→ 否證觀測：指出 9A 交付後「靜默丟棄」在使用者可見面是否仍然完全看不見／我跑了: **沒跑**
assumed: 七條反向 mutation **能真的紅**（誤改為複合鍵時）
→ 否證觀測：指出其中某條在現行測試面下即使誤改也不會紅／我跑了: **沒跑**（尚未實作）
assumed: `dedupe` 之「事件級保留＋廣播」不改變既有 `w=1/n` 與 effective count
→ 否證觀測：構造一事件兩 TF 且同簇之案例，比對廣播前後之權重／我跑了: **沒跑**

## 必答（成對，缺一不算完成）

1. **你自己 R7 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **攻 §G (G-4a)**：重凍 golden 是否讓回歸錨失去意義？如何機械區分「因換錨而改側」與
   「因實作寫錯而改側」？若區分不了，該怎麼辦（給具體替代）？
3. **攻 `Task 9.1` 具名殘留**：把終端可見性延後到別票，Phase 9A 是否名存實亡？
   殘留理由類別選 `blocked-by` 是否正確？
4. **七條反向 mutation 是否真能紅**：逐條說明誤改後哪一條測試會失敗；指出抓不到的那幾條。
5. **修訂引入的新問題**：J1–J8 的落點彼此、或與 D-001／`D-002-C6`／既有 golden 有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R8-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
