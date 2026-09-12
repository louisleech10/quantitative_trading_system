# SPLITUNIFY D-002 閉合輪 R9

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R9
findings-round: R9

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。上游收斂檔沒有戳記是正常狀態。

## 這一輪要做什麼

R8 三家共 14 條、歸八群（七群採納、一群部分採納），`docs/SPLITUNIFY_SPEC.D-002.md` 已第九次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**；另攻本輪修訂引入的新問題。

🔴 **本輪請特別攻三處**：

1. **(G-4c) 我用「同步改寫獨立 oracle」取代你們提的 allowlist 方案**。理由：`_oracle_membership`
   的 docstring 已明文「與被測函式無因果關係、不 import 投影」，所以讓它也換錨之後，
   G-3b 自動成為區分閘。**請攻這個替代是否真的等效**：有沒有「兩邊都改錯成同一個錯」
   而 G-3b 仍綠的情形？逐行重寫的紀律靠什麼保證（它是散文，不是閘）？
2. **K3 我駁回了 composer 的前提**（`blocked-by` 須指名票號）。依據是
   `templates/BRIEF_REVIEW_TEMPLATE.md:71` 的四值閉集與 `R-BRIEF-1` 的架構型實例。
   **請攻這個駁回**：我引的範本是否適用於 SPEC 的 §N（而非只適用 brief review）？
3. **K4 我把 `metadata.split_unify` 的加鍵成本攤開後，留了一句「若成本超出 9A 定位，
   應改為只交付前兩層並併入殘留」**——這等於把決策再次推給實作者。**請攻**：這句是否
   又是一個「二擇一但自己沒擇」（R7 就因同型問題開過 J3）？該不該現在就擇定？

## 八群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| K1 (G-4a) 不可機械歸因（三家） | commit 訊息不是閘 | 新增 **(G-4c)** 同步改寫 oracle 使 G-3b 成為區分閘；**(G-4d)** 保留 v8 baseline 不覆寫、`decision == cutoff` 零位移、邊界 fixture 進 §V 與 mutation |
| K2 殘留決策未落地（三家） | 目標句／§N／mutation 02-03／`Task 9.4` 未同步 | 四處同批改完，並**真的**在 §N 新增 `SU-RESID-9A-UI` |
| K3 殘留類別判定 | `blocked-by` 須指名票號 | **部分採納**：駁回該前提（範本閉集四值、`R-BRIEF-1` 以架構為對象），採納「須真的入 §N」 |
| K4 `metadata.split_unify` 是 exact-key 契約（codex 獨得） | 加鍵會被 contract gate 擋 | `Task 9.1` 補列五處同步施工面與 `Dict[str, int]` 型別；並註明成本超標時應改交付範圍 |
| K5 時間域四條規則重疊（codex 獨得） | 越界可先被判 train/test | 新增**步驟 0 前置條件** `index_ms[0] <= decision_at_ms <= index_ms[-1]` |
| K6 `(6.2)` 與 `Task 9.4` 互斥（兩家） | 義務仍寫複合鍵列數 | `(6.2)` 之 baseline 例外句更正為事件數＝樣本數 |
| K7 反向 mutation 現行不紅（兩家） | 應紅測試未具名 | §V `Task 9.3` 逐條指到具名檔；明寫「測試存在前不得宣稱 mutation 網已閉」 |
| K8 `M-SU-D2-02`／`03` 互斥 | 應紅面已被延後 | 改指 summary 與 `metadata.split_unify` |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R8 十四條歸八群 → `handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md`
fact-verified: `_oracle_membership` docstring 逐字「與被測函式無因果關係」「不 import 投影」，且目前以 `feature_cutoff_ms` 判側 → 主委實跑 `sed -n '133,158p' scripts/freeze_splitunify_golden.py`
fact-verified: `reason_code` 閉集為 `blocked-by`／`needs-research`／`cost`／`out-of-scope`，`R-BRIEF-1` 以「現行派工架構」為 `blocked-by` 對象 → `templates/BRIEF_REVIEW_TEMPLATE.md:71,171`
fact-verified: §N 已新增 `SU-RESID-9A-UI`（主委實跑 `grep -c` ＝ 3，含兩處交叉引用）
fact-verified: 第九次修訂後 obligation／format rc=0、xref 對 r1–r8 八份 synth 皆 rc=0、mutation 表列 26／ID 01–26 連續 → 主委實跑

assumed: (G-4c) 之「同步改寫 oracle」與你們提的 allowlist **等效**
→ 否證觀測：構造「投影與 oracle 都被改成同一個錯誤語意」而 G-3b 仍綠的情形；或說明「逐行重寫、不 import」這條散文紀律如何被機械保證／我跑了: **沒跑**
assumed: 步驟 0 前置條件**窮盡**了重疊情形
→ 否證觀測：指出通過前置後、三條規則仍有重疊或缺口的位置／我跑了: **沒跑**
assumed: `SU-RESID-9A-UI` 之觸發條件（`api/` 出現走投影分支之生產 `run()`）**可機械判定**
→ 否證觀測：說明誰會去檢查這個觸發條件、什麼時候檢查；若無人檢查，殘留等於永久沉睡／我跑了: **沒跑**
assumed: `(6.2)` 改為「樣本數＝事件數」後與 `D-002-C6` 其餘條目一致
→ 否證觀測：指出 C6 內仍有把兩者當不同量的句子／我跑了: **沒跑**

## 必答（成對，缺一不算完成）

1. **你自己 R8 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **攻 (G-4c)**：同步改寫 oracle 是否真能取代 allowlist？給「兩邊同錯而 G-3b 仍綠」的具體構造，或說明為何構造不出來。
3. **攻 K3 的駁回**：我引的 `BRIEF_REVIEW_TEMPLATE` 是否適用於 SPEC 的 §N？若不適用，正確的類別依據在哪份文件？
4. **攻 K4 的「成本超標時改交付範圍」**：這是否又是一個自己沒擇的二擇一？該不該現在擇定？擇哪邊？
5. **修訂引入的新問題**：K1–K8 的落點彼此、或與 D-001／既有 golden／`SU-RESID-9A-UI` 觸發條件有無衝突？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R9-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
