# 第 0 批 SPEC R7 — **這兩項的最後一輪**

brief-kind: review

target: docs/GOVB0_FRICTION_SPEC.md（R7 版）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。本 brief 只收斂範圍。

## 🔴 產出格式（**本輪唯一允許的 `##` 標題清單**）

`## Verdict`／`## §0 前提宣告`／`## 逐條確認表`／`## 出場判準核算`／
finding heading `## <家族大寫>-R7-P<嚴重度>-<序號>`。
**除上列外不得出現其他 `##` 標題**（分段用 `###`）。
不符 schema 的 `##` 會被 `completeness_check` 判 invalid finding ID ⇒ 整份 format-failed（`票 B-31`，本批已踩兩次）。

🔴 **若你本輪的結論是「零 findings」，請在報告中明寫一行 `FINDINGS_COUNT: 0`**，
避免收集端無法區分「真的沒問題」與「格式錯誤讀不到」（`票 B-38`，本批已因此棄輪一次）。

## 🔴 本輪是這兩項的**最後一輪**（終止條件，逐字）

依使用者定死的「**95% 解法就收・殘留先記錄**」與「兩輪斷路器」：

- SPEC 的 P0-1／P0-2 已歷經 **R5 提出 → R6 修 → R6 證偽 → R7 修** 共兩輪補丁。
- **本輪之後不再為這兩項開 R8。**
- 你若發現新缺口，**除非**能證明「該缺口使本批交付物**本身失效**」（＝實作者照 SPEC 做出來的
  gate 仍會漏放真派工，或仍會讓兩個 CLI 並存），否則一律**降為具名殘留**寫入 `票 B-15`／`B-31` 家族，
  **不阻擋進入 TODO 生成**。
- 請在 `## 出場判準核算` 明確分類每條新 finding：**deliverable-invalidating** 或 **named-residual**。

⚠️ 這不是要你放水。**該找的照找、該證偽照證偽**；差別只在「找到之後怎麼處置」。
本條的目的是**讓審查有終點**——本批前一階段（P1-6 線 B）曾因無終止條件連跑 6 輪、50% 純開銷。

## §0 前提宣告

**已查證**：

- fact-verified: R6 兩家結論相反——composer 判兩項 CLOSED、codex 判 3 findings（2 P0＋1 MAJOR）。
  主委採 codex（它跑出可重現反例；composer 只重跑了 brief 點名的既有向量）。
  來源 `handoffs/20260805-govb0-spec-r6-{codex,composer}.md`。
- fact-verified: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0
  → receipt `r7-spec-template-pass`；Task 數 `11`、FACT-RECEIPT 數 `10`。

**假設**（請優先攻）：

- assumed: **允許清單 `[A-Za-z0-9_.:+=,%@^-]` 已涵蓋實務上會用到的合法 delimiter 字元**。
  未查證：`~`／`{`／`}`／`[`／`]`／`!`／`#` 等在 delimiter 中是否常見且合法。
  **若漏收會造成誤擋**（走⑦ fail-closed）——這與本批「止血摩擦」的目標衝突，請評估此風險。
- assumed: **reclaim lock 協定沒有引入新的競態**。
  未查證：`<out>.reclaim.lockdir` 本身的釋放路徑（協定④）若在釋放前 crash 會如何。
- assumed: **⑪⑫ 的反向 mutation 在實作端可構造**（注入 process-discovery 錯誤、移除回收權）。未實跑。

## 本輪範圍：**只驗 R6 的三條是否關閉**

### R6-P0-01 → 修法：允許清單＋完整 token 邊界

**R6 缺口**：⑥用排除清單 `([^[:space:]|&;()<>]+)`，**接受**了⑦要求拒絕的 `E'O'F`／`E"O"F`／`$'EOF'`
（⑥⑦有重疊區＝規則自相矛盾）；且 `E\ F` 前綴匹配成 `E\`、`EOF$(` 前綴匹配成 `EOF$`
⇒ span 界定錯誤 ⇒ codex 實跑 `ESCAPED_ATTACK_EXECUTED` 而掃描器 `ALLOW`。

**R7 修法**：⑥(c) 改為**允許清單** `([A-Za-z0-9_.:+=,%@^-]+)`，且**必須完整 token**
（其後緊接空白／換行／字串結尾，**禁前綴匹配**）。明文寫入「⑥與⑦互補且不重疊」。
語料新增五向量（`E'O'F`／`E"O"F`／`$'EOF'`／`E\ F`／`EOF$(`）各須 TP，
並加 mutation：改回排除清單或移除 token 邊界 ⇒ 至少一條轉 ALLOW。

**你要確認**：五向量現在是否全部 BLOCK？允許清單是否**漏收**合法字元而造成誤擋？

### R6-P0-02 → 修法：stale takeover 協定（回收權＋owner CAS）

**R6 缺口**：「stale ⇒ 先原子刪除再原子建立」的**刪除未綁定 observed owner**
⇒ A、B 皆判 stale 時，A 會刪掉 B 剛建立的 live lock ⇒ 兩者皆啟動（codex 實跑 `B:START,A:START`）。

**R7 修法**：①`mkdir <out>.reclaim.lockdir` 原子取得回收權，EEXIST ⇒ 拒絕且**不得碰主 lock**；
②重讀主 lock，attempt id **仍等於**觀察值才可刪；不等 ⇒ 拒絕且不得刪；
③相等才刪並原子建立，建立 EEXIST ⇒ 拒絕且不得再刪；④釋放回收權前確認仍為己有。
斷言⑫（stale takeover barrier，`STALE_TAKEOVER_STARTS == 1`）＋反向 mutation。

**你要確認**：此協定是否仍有窗口？特別是**回收權持有者在步驟③與④之間 crash** 的情況。

### R6-P1-03 → 修法：新增⑪ process-discovery 錯誤 fail-closed

**你要確認**：⑪的斷言是否可實作、mutation 是否真的可證偽。

## 🔴 不受理範圍（命中標 `OUT-OF-SCOPE`，不計入 findings）

1. `E-SCOPE` 四項（`票 B-35`／`B-34`／`B-24` 機械強制面／`B-15` FP-2 定位）。
2. `G-3`～`G-6`（R5 兩家已判 CLOSED）。
3. **防蓄意繞過**類——本批目標是**擋意外**。
4. 措辭／可讀性／命名一致性。
5. 既有票已涵蓋者（指名該票即可）。
6. 「委員債務無 OPEN」不必查（派工本身會開債，此為固有競態）。

## 出場判準

> **findings ≤5 且 deliverable-invalidating 缺口 = 0 ⇒ 進 TODO 生成。**

🔴 **注意判準已改**：R6 用的是「新 P0 機制缺口 <2」，本輪改為
「**deliverable-invalidating = 0**」——因為依上述終止條件，非 deliverable-invalidating 者一律轉具名殘留。

## 逐條確認表（**用表格，不要用標題**）

| 項 | 判定 | 依據（實跑命令＋結果） | 若 NOT-CLOSED：deliverable-invalidating 或 named-residual |
|---|---|---|---|
| R6-P0-01 五向量是否全 BLOCK | | | |
| R6-P0-01 允許清單是否漏收合法字元 | | | |
| R6-P0-02 takeover 協定是否仍有窗口 | | | |
| R6-P1-03 ⑪是否可實作且可證偽 | | | |

## 硬性要求

1. **禁改碼、禁改 SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
4. 每條 finding 附**可執行修法**。
5. 若判定可進 TODO 生成，請明說。

## 產出

上表、findings（若有，須分類 deliverable-invalidating／named-residual）、
`## 出場判準核算`、對 §0 三條假設的攻擊結果。收尾清 /tmp workdir（保留 claude-501）。
