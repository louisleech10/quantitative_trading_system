# 第 0 批 SPEC R6 — 窄確認輪（只驗兩個 P0）

brief-kind: review

target: docs/GOVB0_FRICTION_SPEC.md（R6 版）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 請完整讀取並照做（canonical finding heading 格式、§0 挑戰前提、Verdict 段）。
本 brief 只**收斂範圍**，不取代該範本的格式要求。

## 🔴 產出格式（**本輪唯一允許的 `##` 標題清單**）

`## Verdict`／`## §0 前提宣告`／`## 逐條確認表`／`## 出場判準核算`／
以及 finding heading `## <家族大寫>-R6-P<嚴重度>-<序號>`。

**除上列外，本報告不得出現任何其他 `##` 標題**（要分段請用 `###`）。
原因：`completeness_check.sh` 把每個 `##` 當 finding ID 候選，不符 schema ⇒ **整份 format-failed、該輪帳無法銷**。
本輪已因此連續失敗兩次（`票 B-31`），故本 brief **不再要求「逐條各一段」**，改要求**單一表格**（見下）。

## §0 前提宣告（主委攤開，錯前提請直接當 finding 打回）

**已查證**：

- fact-verified: R5 兩家獨立實跑後結論一致——`G-1`／`G-2` NOT-CLOSED、`G-3`～`G-6` CLOSED。
  來源 `handoffs/20260805-govb0-spec-r5-codex.md`、`handoffs/20260805-govb0-spec-r5-composer.md`。
- fact-verified: SPEC 已補入原子取得 lock 的文字 → receipt `r6-p0-2-atomic-lock`
  （`grep -cE 'O_EXCL|lockdir|原子 exclusive claim'` → `6`）
- fact-verified: SPEC 已補入非識別字 delimiter 語料 → receipt `r6-p0-1-heredoc-grammar`
  （`grep -cE 'EOF-1'` → `5`）
- fact-verified: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0；
  Task 數 `11`、FACT-RECEIPT 數 `10`，與 §V／§A 宣稱值一致。

**假設**（請優先攻）：

- assumed: **⑥的 shell word 文法 `([^[:space:]|&;()<>]+)` 已窮舉實務上的合法 delimiter**。
  未查證：反引號、`$`、`{`、`}`、`*`、`?`、`[`、`]`、`!`、`~`、`#`、`=` 等字元在 delimiter 中的行為未逐一實測。
- assumed: **⑦的「無法解析即 fail-closed」不會造成實務誤擋暴增**。未量測本 repo 內既有 heredoc 用法的命中率。
- assumed: **⑨的 barrier race 測試在 CI 環境可穩定重現**（deterministic barrier，非 sleep 競速）。未實跑。
- assumed: **`mkdir` 方案在本專案支援的所有檔案系統上原子**（含 macOS APFS 與 CI 的 linux ext4／overlayfs）。未實測。

## 本輪範圍：**只驗兩件事**

### P0-1（Task 2.0 契約第 10 項，新增⑥⑦）

**R5 缺口**：起點 regex 只吃識別字 `[A-Za-z_][A-Za-z0-9_]*`，但 `EOF-1` 是合法 shell delimiter。
不匹配 ⇒ 不開 span ⇒ 掃描器在 body 內的 `<<INNER` 開錯位置的 span ⇒ 吞掉真派工 ⇒ **fail-open**。
（codex 實跑：`ATTACK_EXECUTED` 印出，掃描器回 `ALLOW`。）

**R6 修法**：
⑥ delimiter 文法改為 **shell word**：`'([^']*)'`／`"([^"]*)"`／`([^[:space:]|&;()<>]+)` 三選一，去引號取字面值。
⑦ `<<` 無法依⑥解析 ⇒ **整個掃描 fail-closed（BLOCK）**，不得略過該 `<<` 繼續掃描。
語料新增：`<<EOF-1`／`<<'EOF-1'`／**body 內含假 marker 且 delimiter 後接真派工**（TP 必須 BLOCK）／`<<E'O'F`（依⑦ fail-closed）。

**你要確認**：⑥⑦ 是否**真的關閉**了該攻擊鏈？**請重跑 codex 的原始反例**驗證現在會 BLOCK。
另請嘗試**新的**繞過向量（尤其針對⑥的字元集合）。

### P0-2（Task 3.2 lock，新增 acquire 原子性條款＋斷言⑨⑩）

**R5 缺口**：全文無 `O_EXCL`／`flock`／`mkdir`／`TOCTOU`。owner-safe release 只防「舊 owner 解新鎖」，
擋不住兩個 dispatcher 在 precheck 都看到「無存活 lock」後各自啟動。
（codex barrier 模擬：`A:START`＋`B:START` 兩者皆啟動。）

**R6 修法**：acquire 須為**單一原子操作**（`mkdir <out>.lockdir` 或 `O_CREAT|O_EXCL`）；
取得成功者才啟動 CLI；失敗者重讀判 stale，非 stale ⇒ 拒絕（不寫 `result_state`），
stale ⇒ 仍須以同一原子操作接管，不得直接覆寫；`lock-create`／process-discovery 任一錯誤 ⇒ **fail-closed**。
斷言⑨（barrier race，含**反向 mutation**：換回兩步檢查則必須 FAIL）、⑩（lock-create 錯誤 fail-closed）。

**你要確認**：⑨的 mutation 設計是否**真的可證偽**（換回兩步就一定 FAIL，不會僥倖通過）？
stale takeover 的「先原子刪除再原子建立」是否仍有窗口？

## 🔴 不受理範圍（不得重開，命中請標 `OUT-OF-SCOPE` 且不計入 findings）

1. `E-SCOPE` 四項：截斷 oracle（`票 B-35`）／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位。
2. `G-3`～`G-6`（R5 兩家已判 CLOSED，四條皆有 receipt）。
3. **防蓄意繞過**類——本批目標是**擋意外**。
4. 措辭／可讀性／命名一致性。
5. 既有票已涵蓋者（請指名該票，不列 finding）。
6. **「委員債務無 OPEN」不必查**——`committee_run.sh` 派工本身就會開債，
   任何 brief 宣告此事在你審查當下必為 rc=1。此為流程固有競態，非事實錯誤（R5 已澄清）。

## 出場判準（逐字）

> **findings ≤5 且新 P0 機制缺口 <2 ⇒ 進 TODO 生成。**

「新 P0 機制缺口」＝ SPEC 缺少必要機制致實作者無法機械驗收；**不含**措辭、範例、命名。
請在 `## 出場判準核算` 段給出逐項數字與是否開 R7 的結論。

## 逐條確認表（**用表格，不要用標題**）

| 項 | 你的判定 | 依據（實跑命令＋結果） |
|---|---|---|
| P0-1 攻擊鏈是否關閉 | CLOSED／NOT-CLOSED | |
| P0-1 是否有新繞過向量 | 有（列出）／無 | |
| P0-2 原子取得是否足夠 | CLOSED／NOT-CLOSED | |
| P0-2 ⑨ mutation 是否可證偽 | 是／否 | |

## 硬性要求

1. **禁改碼、禁改 SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
4. 每條 finding 須附**可執行的修法**，不得只說「應更嚴謹」。
5. 若你判定兩條皆 CLOSED，請明說「可進 TODO 生成」。

## 產出

上述表格、findings（若有）、`## 出場判準核算`、以及對 §0 四條假設的攻擊結果。
收尾清 /tmp workdir（保留 claude-501）。
