# TESTREG Task 3.1 逐檔分類規則（主委與三家共用；草案，待諮詢 r3 定案）

## 權威來源（本檔只摘要，不另立定義）
- 欄位與值域：契約 `tests/registry/testreg_schema.json` 之 `catalog.entries`、`enums`（`charter_category`、`oracle`、`claim`、`file_disposition`、`retire_evidence_level`）。
- 類別、Oracle、保證等級之定義：`docs/TEST_DESIGN_CHARTER.md` §0（Oracle 與 claim）、§A（A1–A22）、§B1（可證偽／oracle 獨立性）、§E1（Feature Factory 模組→必做類別）。
- 淘汰證據：契約 `receipts.E0`／`E1`／mutation 規則；SPEC `docs/TESTREG_SPEC.md` §C「淘汰只以碑、只憑收據」、Task 3.1（第 130–136 行）。

## 逐欄判定
| 欄 | 判定 |
|---|---|
| guarantee | 該檔**斷言實際所守**之章程類別 A1–A22（多選；依斷言內容，不依檔名或 docstring）。至少一個。 |
| oracle | 該檔斷言實際用到之等級聯集：EXACT／TOLERANCE／METAMORPHIC／STATISTICAL／PROPERTY／SMOKE。期望值由待測自身導出（自指，§B1.2）者不得標 EXACT／TOLERANCE 作正確性 oracle，須於 note 標 `self-ref`。 |
| claim | correctness（數值／資料／洩漏，且有可證偽依據：同檔 mutation 探針、或獨立 oracle 經 mutation 證可紅）／contract／regression（golden 而無探針）／smoke／perf。多選。無可證偽依據之數值類降 regression 或 contract，note 標 `no-probe`。 |
| disposition | keep 或 rewrite。rewrite 只用於**測試本身有具體缺陷**：既有紅之前提過期、自指 oracle、空心或假綠、斷言與 docstring 宣稱不符、覆蓋缺口須改既有函式補強。純新增測試不算 rewrite（於 note 寫 `add:<要補什麼>`）。 |
| rewrite_targets | disposition=rewrite 時之函式層 nodeid（`path::[Class::]func`，不含參數化後綴），逗號分隔；整檔＝`-`。keep 時一律 `-`。 |
| tombstones | 擬立碑，每項 `nodeid:E0|E1|E2:replaced_by1|replaced_by2`（無 replaced_by 寫 `-`），逗號分隔；無則 `-`。E0＝HEAD 失敗於 import 已被某提交自生產碼刪除之符號；E1＝與另一測試函式及其 fixture 閉包 AST 完全相同；E2＝另一測試已覆蓋且可產 mutation 收據。**不得以慢、久未跑、年代久為理由**；`tests/_golden/prered/allowed_red.json` 中 owner 未收案之 nodeid 不得擬淘汰。 |
| evidence | 碼證 `file:line`（至少一個；分類依據之斷言行），逗號分隔。 |
| note | 簡述（中文）：已知紅與歸因、覆蓋缺口、重複成本、`self-ref`、`no-probe`、`add:` 等；無則 `-`。不得含 tab。 |

## 交件格式（逐字）
在交件檔中放一個 fenced block，開頭行逐字為 ```` ```testreg-classify ````、結尾行為 ```` ``` ````；第一列為表頭（tab 分隔，逐字）：
```
path	guarantee	oracle	claim	disposition	rewrite_targets	tombstones	evidence	note
```
其後每檔一列，**範圍清單內每檔恰一列**、不得多列範圍外檔；多值以半形逗號分隔；空值寫 `-`。

## 輸入
- 範圍清單：`handoffs/run_receipts/testreg_probes/b3/G{1..4}.txt`（聯集＝`phase3_scope.txt`，149 檔）。
- 逐檔輸入表：`handoffs/run_receipts/testreg_probes/b3/20261013-phase3-input.tsv`（測試數、行數、真實 K 線、標記、記錄器最近結果與耗時合計〔`unknown`＝無紀錄，不得當成 0〕、複查訊號、首末提交日）。
- FRAMEPATH 諮詢 r4 已判之 30 檔：`handoffs/reconcile/20260928-framepath-x-consult-r4/synth.md:76-107`、`:194-213`（①本批必跑／②覆蓋等價／③已刪節點／④重型；為 FRAMEPATH b1 處置用，不等於本表欄位，僅作輸入）。
- 範圍內 12 支既有紅與歸因：`handoffs/20261010-testreg-x-consult-r3-claude.md` 題二表。
