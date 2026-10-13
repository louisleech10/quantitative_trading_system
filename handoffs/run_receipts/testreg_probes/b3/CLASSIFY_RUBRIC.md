# TESTREG Task 3.1 逐檔分類規則（主委與三家共用；諮詢 r3 定案，`handoffs/reconcile/20261010-testreg-x-consult-r3/synth.md`）

## r3 定案之補充規則（優先於下文）
1. **空表判定（`hollow-empty-df`）**：`generate_features` 之回傳 `features_df` 只有索引（`momentum/FeatureEngineering/feature_factory.py:4005-4006`）。以**函式與斷言**為單位：比對其值、欄名、雜湊、NaN／inf、跨標的值隔離者 ⇒ note 標 `hollow-empty-df`、該函式列入 rewrite_targets（改讀落盤原始輸出或 registry 群組值，且須斷言非空欄集合與產出清冊；範例 `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py:121-128`）；只驗索引、列數、特徵數、metadata、落盤路徑者**不算**空心。標 correctness 而讀空表值者一律空心。
2. **既有紅**：範圍內已實證 29 支（逐支首個壞提交見 `handoffs/20261010-testreg-x-consult-r3-claude.md` 題二與 `20261013-light-sweep.tsv`）。note 標 `existing-red:<首個壞提交>`；FRAMEPATH b1 造成之兩支另標 `framepath-b1-caused`（owner FRAMEPATH，本表照常分類）。能不動斷言修者列 rewrite 並於 note 寫修法；須改斷言者 note 標 `needs-existing-red-receipt`（SPEC v44 收據）。
3. **FRAMEPATH 治理檔**：`framepath_governed_in_scope.txt`（52 檔）內之檔，note 加 `governed`——其實體改寫待 FRAMEPATH 檢查② 修訂戳記後（分類照做）。
4. **重複執行**：同一設定重複生成而無獨立斷言差異者 note 標 `dup-run:<對照 nodeid>`（例：V-6 之 use_searchsorted 參數化在 CGSA 路徑為同一實作，`momentum/FeatureEngineering/timeframe/tf_aligner.py:72` 只在已無生產呼叫者之 `align_to_primary` 內）；去重須以 rewrite（斷言不減、附收據）為之，不得以慢為淘汰理由。
5. **real_kline 欄**：輸入表之 `real_kline` 只認字面，經輔助函式讀真實 K 線者會誤標 N——以讀碼為準。
6. **碼證**：`repo 相對路徑:行` 或 `repo 相對路徑:起-訖`。
7. **比對器**：`compare_classify.py` 為 fail-closed（缺列／多列／重複／值域／nodeid 形與存在／碼證檔行／tab 任一違反即 rc 1；反例 `compare_classify_mutations.out`），交件表須能通過。

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
- 範圍內 29 支既有紅與歸因：`handoffs/20261010-testreg-x-consult-r3-claude.md` 題二表與其「追加」段、`20261013-light-sweep.tsv`。
- FRAMEPATH 治理檔：`framepath_governed_in_scope.txt`。
- 主委版分類表：`claude_G{1..4}.md`（Claude 子代理逐檔讀碼、未實跑；三家須獨立判定後逐列攻之）。
