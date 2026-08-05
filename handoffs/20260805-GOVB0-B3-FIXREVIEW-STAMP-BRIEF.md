
# B3 修補 review 收斂戳記（**R2 派工前最後一道**）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-b3-fixreview/synth.md

## 任務

複核**群集／處置段**是否忠實反映本輪 findings，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

來源：codex 4 條 ＋ composer 3 條 ＝ 7 條，去重後群集為 `D-1`～`D-4`。

## 🔴 首要攻擊標的：主委在兩家分歧時採了較嚴的一方

| 群 | codex | composer | 主委裁定 |
|---|---|---|---|
| D-1 | BLOCKING | MAJOR，順延 B4 | **本批修** |
| D-2 | BLOCKING | MAJOR，視為過渡 | **本批修** |

主委裁定理由（逐條攻）：

| # | 理由 | 你要判什麼 |
|---|---|---|
| A1 | D-2 是**本批新引入**，不適用「面向未來不溯及既往」——該原則針對舊錯誤 | 這個區分成立嗎？把 fail-open 換成未量測的 fail-closed，算「修復」還是「平移」？ |
| A2 | D-1 落在本批正在加固的同一機制內，順延等於驗收標準自相矛盾 | 但 D-1 **非 B3 引入**（兩家與主委皆確認新舊 rc 同）。既有缺陷在本批修，是否違反使用者「95% 解就收、殘留具名記錄」？ |
| A3 | 兩條修法皆有界（各集中單一函式），不觸發膨脹升級 | 實際查碼確認有界性。**若其實會擴散，主委的裁定就錯了** |

🔴 **composer 立場請特別說明**：你原判順延 B4，主委推翻了你。
**你是否被說服**？若否，請在戳記報告中明確反對並給理由——**不同意就不要蓋章**。

## 逐條歸戶核對

```
D-1 ← CODEX-R14-P0-01 ＋ COMPOSER-R14-P1-01
D-2 ← CODEX-R14-P0-02 ＋ COMPOSER-R14-P1-02
D-3 ← CODEX-R14-P2-03                          （C4 非真 mutation）
D-4 ← CODEX-R14-P2-04 ＋ COMPOSER-R14-P2-01    （凍結 TODO 就地改）
```

🔴 **請逐條核對 ID 對應**。本 epic 主委已犯 7 次 ID 歸錯或對調，機檢對「錯位」無感。

## 其他要判的

| # | 問題 |
|---|---|
| B1 | 「R2 定為確認輪、禁新增 scope」的約束是否寫得夠硬？會不會反而讓 R2 漏掉真問題？ |
| B2 | 「若 R2 再出現修補引入新缺口即觸發斷路器」——這個觸發條件可操作嗎？ |
| B3 | D-2 的修法「O(n) 流式掃描」是否真能同時滿足：關 fail-open、不誤擋、latency <100ms、4MB 有界？**若你認為做不到，現在就說** |

## 不受理範圍（標 `OUT-OF-SCOPE`）

1. C6（多 heredoc 誤擋）——已裁順延 B4。
2. B4 以後的 Task。
3. `audit.log` 大小／封存／latency 主題。
4. 措辭／命名／可讀性。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:eea35be5ad843c324be939736cf0f51aae25dc15589d044347f41992b5dc39a3 task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**。
- **只 append 到 `## 戳記` 區段之後**，不得改動該檔任何其他位元組。

🔴 **grok 的立場**：你是本批 implementer，被角色閘擋在 review 之外，沒有自己的 findings。
請以**第三方複核**立場審，並額外回答：**D-1～D-4 你能不能直接開寫？
D-2 的 O(n) 流式掃描你打算怎麼做，有沒有做不到的地方？**

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **禁改碼、禁改測試**。
3. **rc 一律直接取，禁經 pipe**。
4. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報，不要自行還原。
5. 不要 commit、不要 push；**禁碰 `data_cache/`**。
6. 貼出 `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-b3-fixreview/synth.md`
   與 `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-b3-fixreview/sources.lock` 的完整 stdout 與 rc。

## 產出

改了哪一行（貼 diff）、兩支檢查器 stdout 與 rc、逐條歸戶確認、
**A1–A3 對主委裁定的攻擊**、B1–B3 的判斷、（grok 另答）D-2 修法可行性。
收尾清 /tmp workdir（保留 claude-501）。
