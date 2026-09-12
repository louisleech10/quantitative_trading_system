# SPLITUNIFY D-002 閉合輪 R10

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R10
findings-round: R10

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。上游收斂檔沒有戳記是正常狀態。

## 這一輪要做什麼

R9 三家共 21 條、歸十一群（十群採納、一群部分採納），`docs/SPLITUNIFY_SPEC.D-002.md` 已第十次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**。

🔴 **本輪有一個特別的必答：檢驗我的「自證步驟」是否真的執行。**

R9 收斂時我具名記載了一個判斷：九輪 findings 數（15／11／15／8／11／16／15／14／21）**無下降趨勢**，
但**不符合「無法收斂」的停輪條件**（每輪皆為具體可閉合、有碼證、多條三家獨立撞題）；真正的問題是
**我的修訂紀律**——近三輪有四項屬「寫了要做卻沒做」或「引錯依據」。因此我承諾第十次修訂改做法：
**每項改完立即逐條 grep 自證它落在該落的段落**（§V 驗行號區間、§N 驗強制欄、mutation 驗表列與 ID 連續）。

**請檢驗這件事本身**：第十次修訂的十一項，是否每一項都真的落在它該在的位置？有沒有又出現
「§G 寫了但 §V 沒有」「宣稱登記但沒登記」「條數與表列不符」這類？（我自己在跑閘前抓到一處：
mutation 表列已 31 而正文仍寫 26，已修正——請確認還有沒有我沒抓到的。）

## 十一群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| L1 (G-4c) 擋不住兩邊同錯（三家） | 同步改寫 oracle 只抓不對稱錯誤 | 新增 **(G-4e)**：保留 (G-4c) 作 regression，另加**第三份判準**（三段式純函式算期望側，與投影／oracle 雙邊比對，三者不全等即 FAIL） |
| L2 (G-4d) 未進 §V（兩家） | 只寫在 §G 散文 | §V 增五條 ASSERT（零位移／邊界 fixture／三者全等／early／late）＋mutation `27`–`31` |
| L3 目標句仍要終端可見（三家） | 與 §N 殘留互斥 | `Task 9.1` 目標句改為「交付至 producer 層；終端可見性見 §N」 |
| L4 K3 引錯權威（三家） | brief 範本不治理 SPEC §N | 改引 `SPEC_TEMPLATE.md:107-112`（三值＋強制欄），補 `為何現在不做:`；類別 `blocked-by` 維持（阻塞對象為**層**） |
| L5 K4 逃逸句（三家） | 二擇一未決 | **擇定三層**並刪逃逸句（依據：新鍵值為 `Dict[str, int]`，不落入 `test_segment_count_keys` 之整數判準 ⇒ 實改三處） |
| L6 §G L127 一刀切互斥 | 與允許重凍衝突 | 改為「(G-4d) 允許集合內之位移除外」 |
| L7 缺 producer→metadata 交接（codex 獨得） | 會產出孤立欄位單測 | `Task 9.1` 增資料流交接定義，驗收改整鏈驗值 |
| L8 baseline 兩量不恆等（codex 獨得） | 物化失敗使 `n_test` 少算 | 改為同時輸出 `n_test_events` 與 `n_test_samples`，配物化失敗 fixture |
| L9 Step 0 未驗 pair（codex 獨得） | validator 從未被呼叫 | Step 0 補 train／test 非空、row set 不重疊、呼叫 `validate_split_pair_integrity`；**駁回**其 `train_last == test_start` 前提並具名引用不變量 |
| L10 殘留無 owner（兩家） | 只活在 SPEC §N | `docs/SPLITUNIFY_TODO.md` §E 登記，附可執行 recheck 命令與 owner |
| L11 §V 缺 early／late | 步驟 0 可被漏實作 | 併入 L2 之五條 |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R9 二十一條歸十一群 → `handoffs/reconcile/20260911-splitunify-b9-review-r9/synth.md`
fact-verified: 現行 golden fixture **全部事件** `decision == cutoff`（`freeze_splitunify_golden.py:117` 直接複製）⇒ 換錨差異現在一筆都測不到 → 主委實跑 `sed`
fact-verified: `validate_split_pair_integrity` 存在但 derive 路徑**從未呼叫** → R9 codex 碼證＋主委複驗
fact-verified: `discarded_rows_by_feature_tf` 之值為 `Dict[str, int]`，不落入 `test_segment_count_keys`（其判準為「鍵名含 `test` 且值為整數」）→ 主委實讀 `split_unify.json`
fact-verified: mutation 表列 31、ID 01–31 連續、正文宣稱 31 → 主委實跑計數（**修正前正文為 26**）
fact-verified: 第十次修訂後 obligation／format rc=0、xref 對 r1–r9 九份 synth 皆 rc=0 → 主委實跑

assumed: 第十次修訂的十一項**每一項都落在該落的位置**
→ 否證觀測：逐項 grep，指出「§G 有而 §V 無」「宣稱登記而未登記」「條數不符」之殘留／我跑了: 只自查了 mutation 條數一項，**其餘未逐項驗**
assumed: (G-4e) 第三份判準**不會**與 (G-4c) 形成三份同錯
→ 否證觀測：說明三份判準若由同一人同一次寫成，如何避免同錯；或指出這是無解而該接受／我跑了: **沒跑**
assumed: `baseline` 同時輸出兩量後，下游消費者**不會**再混用
→ 否證觀測：指出哪個消費者會拿錯那一個／我跑了: **沒跑**
assumed: Step 0 補 pair 驗證後，`Task 9.2b` 之三段式**確定**互斥且窮盡
→ 否證觀測：在補完 pair 驗證的前提下，仍構造出同時命中兩條或都不命中的位置／我跑了: **沒跑**

## 必答（成對，缺一不算完成）

1. **你自己 R9 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **檢驗我的自證步驟**（本輪特有）：第十次修訂十一項，逐項指出是否落在該落的位置；列出我漏掉的。
3. **攻 (G-4e)**：三份判準若由同一次改動寫成，如何避免三份同錯？若無解，該如何誠實標註？
4. **攻 L8／L9 的修法**：`baseline` 雙量是否足夠（下游會不會拿錯）？Step 0 補 pair 後三段式是否真的互斥且窮盡？
5. **修訂引入的新問題**：L1–L11 的落點彼此、或與 D-001／既有 golden／TODO §E 有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R10-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
