# SPLITUNIFY D-002 閉合輪 R11

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R11
findings-round: R11

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。上游收斂檔沒有戳記是正常狀態。

## 這一輪要做什麼

R10 三家共 13 條、歸八群（**全部採納**），`docs/SPLITUNIFY_SPEC.D-002.md` 已第十一次修訂（v11）。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**。

🔴 **本輪特別必答（延續 R10）：檢驗我的「自證六條」是否真的執行。**

R10 兩家複驗我的自證步驟，結論是「九項對、兩項漏」，漏的兩種形態是①被取代的舊內容沒同步改掉
②新增的 mutation 指向不存在的驗收條款。我已把自證清單由四條擴為**六條**：
①新增內容落點 ②**被取代的舊內容是否同步改掉** ③**每條 mutation 是否有 §V 母斷言**
④條數與表列一致 ⑤Task 正文與 §V 對稱 ⑥骨架佔位已刪。

**請檢驗這件事本身**：本輪十項改動（M1–M8 ＋ 兩項主委自產），是否每一項都落在該落的位置？
自證六條有沒有又漏掉第七種形態？（我自己在跑閘前抓到三處：兩處「16 處」未同步、
(G-4d)① 與座標 adapter 兩條 mutation／改法缺 §V 母斷言，已補——請確認還有沒有我沒抓到的。）

## 八群＋兩項自產的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| M1 (G-4e) 第三份仍會三份同錯（三家） | 第三份是「同一三段式的另一次編碼」 | 改為 fixture 內**人手逐筆填入**之字面 `expected_side`；**明禁** import／呼叫投影、`_oracle_membership` 或兩者之共用 helper；§V 第 3 條同步改寫；並具名登記**殘餘誠實邊界**（人手填錯仍會三份一致＝散文紀律、非機械保證） |
| M2 §V metadata 斷言不對稱（三家） | 只 `ASSERT … 帶該鍵` | 升級為值相等：`metadata == summary == producer 回傳` |
| M3 `(6.2)`／`Task 9.4` 仍寫舊語意（兩家） | 同檔互斥，實作者依任一側都可自稱合規 | L92／L208／L211 **三處同改**；`baseline` 回傳 schema 定為 **exact**、舊鍵 `n_test` **刪除**（不得保留、不得設 alias）；v10 之「或要求完整物化」二擇一作廢 |
| M4 §V 無 `Task 9.4` 條目 | `M-SU-D2-31` 指向不存在的條款 | §V 新增 `Task 9.4` 母斷言三條 |
| M5 座標 adapter（codex 獨得，實跑 `IndexError`） | `row_index_local` 局部 vs validator 全域 | `Task 9.2b` 步驟 0③ 要求二擇一寫死（傳 full-universe `row_index`／定義 local→global rebase adapter），補「非連續 global positions」fixture 與 §V 母斷言 |
| M6 (G-4d)① 不可驗（codex 獨得） | `--write` 直接覆寫、golden 無 v8 鍵 | 指定不可變檔 `splitunify_golden.v8.json` ＋ `.v8.sha256` ＋版本化新鍵 `g1_membership_v9`／`g3b_oracle_v9` ＋ `--write` 對 `.v8.json` 拒寫；§V 補第 6 條母斷言；另定義「允許差異集合」之可執行形式 |
| M7 條數兩套並存（codex 獨得） | 標題 16、四層可數出 20 | 新增 **(5.6) 消費面 register**（唯一計數依據，**25 條**，逐條帶分類／處置／Task／mutation；mutation 欄為 `—` 者標為具名缺口）＋ **(5.7) 維護義務**；`Task 9.3` 標題、§RISK、§R 回退句全部改指 register |
| M8 殘留觸發式漏報（codex 獨得） | 窄 regex 只匹配 inline constructor | SPEC §N 與 `docs/SPLITUNIFY_TODO.md` §E 同步改為**廣義生產 call-site 掃描**（AST ＋ canonical 實參驗證），並明寫「不得以窄 regex 零命中當作不存在之證據」 |
| 自產 A | 主委自證抓到 | `Task 9.2b` 判準第 4 條與步驟 0④ **冗餘**，刪除並保留字面供追溯 |
| 自產 B | 主委自證抓到 | mutation 新增 `M-SU-D2-32`（`baseline` 保留舊鍵 `n_test` 即紅），條數 31 → **32** |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R10 十三條歸八群、全部採納 → `handoffs/reconcile/20260911-splitunify-b9-review-r10/synth.md`
fact-verified: mutation 表列 **32**、ID 01–32 連續且無重複、正文宣稱 32 → 主委實跑 `grep -c` ＋ `comm` 缺號比對 ＋ `uniq -d`
fact-verified: `D-002-C5` (5.6) register 表列 **25** 條，與標題、§RISK、§R 回退句三處一致 → 主委實跑 `grep -c`
fact-verified: `tests/golden/splitunify/splitunify_golden.json` 頂層為 **11 鍵**（`_doc`／`g1_membership`／`g3b_oracle`／`g4_per_symbol_n`／`g5_answer_window`／`g5_row_fingerprint_first_ms`／`g5_row_fingerprint_last_ms`／`g5_row_fingerprint_n`／`g5_row_fingerprint_positions`／`g5_row_fingerprint_sha256`／`purge_reasons`），**無任何 v8 鍵**，該目錄下亦**無** `.v8.json` → 主委實跑 `jq -r 'keys[]'` ＋ `ls`（🔴 R10 codex 原述「只有 g1／g3b／g4／g5」不精確，SPEC v11 已依實測更正——**請一併複驗我的更正是否正確**）
fact-verified: 第十一次修訂後 `obligation_block_check` rc=0、`doc_format_precheck` rc=0（SPEC 與 TODO）、`spec_xref_check --synth` 對 **r1–r10 十份** synth 皆 rc=0 → 主委實跑
fact-verified: R10 債已清（`debt_clear.sh` rc=0，`round_id=6b721c53-aed2-4f3e-bc11-fe3186c99018`）→ 主委實跑

assumed: (5.6) register 之 **25 條涵蓋全部**單鍵消費面，且甲／乙／丙分類逐條正確
→ 否證觀測：指出不在表內的消費面（附檔:行），或指出分類錯誤且複合鍵上線後會靜默取錯列的那一列／我跑了: **只從 (5.1)–(5.5) 既有敘述逐條抽出並拆開複合項，沒有重新掃過 repo**
assumed: (G-4e) 改用 fixture 字面 `expected_side` 後，「三份同錯」之風險**顯著降低但未消除**，且這個殘餘只能靠散文紀律
→ 否證觀測：構造一個「人手填值也會照同一錯誤理解填」的具體情境；或提出一個**機械**解（不靠人手也不靠第三次編碼）／我跑了: 探針 `handoffs/20260912-splitunify-b9-probe-g4e-triple.py` 只驗「獨立實作」與「三份同錯」兩情形，**未驗人手填值情境**
assumed: `baseline` **刪除**舊鍵 `n_test` 不會打破任何下游消費者
→ 否證觀測：指出仍讀 baseline 之 `n_test` 的生產消費者（前端／API／報告任一）／我跑了: R10 前查過三項碼證（`baseline.py:120` 為唯一寫入點、前端命中皆屬別的 `n_test`、該鍵不在 `split_unify.json` 登記內），**本輪未重跑**
assumed: M6 之落地順序 (i)–(iv) **無法**被繞過
→ 否證觀測：構造一條繞過路徑（例如重凍時先刪 `.v8.sha256`、或把新鍵寫進既有鍵）／我跑了: **沒跑**
assumed: M5 之座標 adapter 二擇一（full-universe `row_index` 或 local→global rebase）**窮盡**
→ 否證觀測：指出第三種座標情形，或指出兩個選項各自會壞掉的批／我跑了: **沒跑**（codex 的 `IndexError` 反例我未複跑）

## 必答（成對，缺一不算完成）

1. **你自己 R10 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **檢驗我的自證六條**（本輪特有）：十項改動逐項指出是否落在該落的位置；列出我漏掉的，並指出自證清單缺的第七種形態（若有）。
3. **攻 (5.6) register**：25 條是否涵蓋完全、分類是否逐條正確？mutation 欄標 `—` 的四列（`C5-15`／`C5-16`／`C5-17` 與其他）是否該補 mutation，還是具名缺口即可？
4. **攻 (G-4e) 的殘餘誠實邊界**：人手填 `expected_side` 是否真的比「第三次編碼」好？有沒有機械解？若無，我現在的標註方式夠不夠誠實？
5. **攻 M6／M5**：不可變 v8 baseline 的落地順序可否繞過？座標 adapter 二擇一是否窮盡？請附**具體構造**。
6. **修訂引入的新問題**：M1–M8 與兩項自產之落點彼此、或與 D-001／既有 golden／`docs/SPLITUNIFY_TODO.md` §E 有無衝突？

## 停輪條件

①必答 1–6 皆有立場；②必答 2、3、4、5 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 `Task 9.x` 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R11-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
