# 第 0 批 SPEC R7 收斂戳記（**規格階段最後一道**）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-spec-r7/synth.md

## 任務

複核 `handoffs/reconcile/20260805-govb0-spec-r7/synth.md` 的**群集／處置段**是否忠實反映 R7 的 findings，
確認無誤後 **append 一行 RECONCILE-STAMP** 到該檔的 `## 戳記` 區段。

**本輪過關 ⇒ 第 0 批規格階段結束，進 TODO 生成。**
來源：codex 2 條 ＋ composer 2 條 ＝ 4 條，群集為 `H-1`／`H-2`。

## 你要確認的（逐條，不是形式蓋章）

### 1. 歸戶正確性

`H-1` ← `CODEX-R7-P1-01`＋`COMPOSER-R7-P2-01`（允許清單不完整 ⇒ 誤擋）
`H-2` ← `CODEX-R7-P1-02`＋`COMPOSER-R7-P2-02`（reclaim lock 孤兒 ⇒ 路徑鎖死）

🔴 **請逐條核對 ID 對應，不要只看語意**。本批七輪中主委已犯 **7 次** ID 歸錯或對調，
`completeness_check --lock` 與主委自檢**對「錯位」皆無感**（兩者只驗「ID 是否出現」），
僅委員語意複核抓得到（其中 3 次為三家各自獨立指出）。本表以 `awk` 自附錄機械抽對照後填。

### 2. **主委在 R7 之後改了 SPEC，請確認改動與收斂表一致**

依 `H-1` 的處置，主委把⑥(c) 允許清單由 `([A-Za-z0-9_.:+=,%@^-]+)`
擴為 `([A-Za-z0-9_.:+=,%@^~{}\[\]!*?-]+)`（補入 `~{}[]!*?` 八字元）。

**依據**：codex 實跑 `BASH_UNQUOTED[~|{|}|[|]|!|*|?] rc=0`，證實 bash 皆接受為合法 delimiter。
**主委的理由**：這些字元在 delimiter 位置只做 quote removal、**不做展開**（無 glob／brace／tilde expansion），
故納入允許清單**不會**造成掃描器與 shell 判定分歧。

🔴 **請攻這個理由**：
- 上述「不做展開」的說法是否正確？有無反例（某字元在 delimiter 位置確實會被 shell 特殊處理）？
- 補入這 8 字元是否**引入任何 fail-open**？（原本它們走⑦ BLOCK＝安全方向；現在會開 span）
- composer 另點名 `#`，**主委未納入**（codex 的 probe 未實測 `#`）⇒ 目前 `#` 仍走⑦ fail-closed。
  此決定是否恰當？

### 3. 兩條殘留的分類是否正確

兩家皆判 **named-residual、非 deliverable-invalidating**，主委採納並寫入 SPEC §N。

🔴 **請獨立驗證這個分類**，不要因為兩家已同意就跳過：
- `H-1` 殘留：允許清單仍非完整 grammar ⇒ 未列字元走⑦ **BLOCK**。方向是**過擋**還是可能**漏放**？
- `H-2` 殘留：reclaim 孤兒 ⇒ 該 `<out>` 鎖死待人工清。最壞後果是否真的**不會**造成雙 CLI 並存？

**若你認為任一條實為 deliverable-invalidating，請拒章並寫明失效路徑**——
本輪是規格階段最後一道閘，過了就進 TODO 生成與實作。

### 4. `E-SCOPE` 與既有殘留維持不變

`票 B-35`／`B-34`／`B-24` 機械強制面／`B-15` FP-2／`B-36` ID 錯位，**本輪不再徵詢**。
若改變立場請拒章並寫明失效路徑。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**，brief 內範例一律不得採用。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄為 byte-faithful 委員原文）。

🔴 **grok 的立場**：你是 implementer、被角色閘擋在 R7 review 之外（`票 B-34`），**沒有自己的 findings**。
⇒ 請以「**第三方複核**」立場審：群集表對附錄逐字 findings 的歸戶是否正確、
主委的 SPEC 改動（第 2 點）與殘留分類（第 3 點）是否有掩飾成分。

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **驗收＝狀態，不是 rc**：貼出三者的完整 stdout 與 rc——
   `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md`／
   `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r7/sources.lock`（須 0）／
   `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md`（須 0）。
3. **rc 一律直接取，禁經 pipe**。
4. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
5. 不蓋章一樣要交產出說明理由，**不要留空檔**。

## 產出

改了哪一行（貼 diff）、三支檢查器完整 stdout 與 rc、逐條歸戶確認結果、
對第 2 點（SPEC 改動理由）與第 3 點（殘留分類）的攻擊結果。
收尾清 /tmp workdir（保留 claude-501）。
