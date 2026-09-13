# SPLITUNIFY b9 — stamp-r1 五條 finding 閉合再驗證（＝DOCROT 成效量測第一輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 🔴 **`docs/SPLITUNIFY_SPEC.D-002.md` 已於 stamp-r1 取得三家 APPROVED、`reconcile_stamps_check.sh` rc=0**（`AGENTS.md:40` Rule 12 之停工條件**已解除**）。本輪不得再以「SPEC 未蓋章」為由停工。
- 🔴 **本輪不重審 SPEC 內容**。R12 停輪判準已觸發並經三家確認。本輪唯一標的是 **`docs/SPLITUNIFY_TODO.md` §C-9 對 stamp-r1 五條 finding 的修補**。

## 本輪要做什麼（一句話）
**逐條重跑你自己在 stamp-r1 提出的反例**，確認修補真的關閉了該 finding（章程 §B8：閉合須由**原提出方**重跑同一反例，不憑「已修」信任）。

| finding | 提出方 | 修補摘要 |
|---|---|---|
| `CODEX-R1-P1-01` | codex | `docs/MULTI_AGENT_ORCHESTRATION.md:194` 之「兩家族」改為指向 §1 現行分工行；另補改 `docs/DEVELOPMENT_GUIDE.md:59` |
| `CODEX-R1-P1-02` | codex | §C-9 之 `M-SU-D2-NN` 縮寫補成完整字面（三處） |
| `CODEX-R1-P1-03` ／ `GROK-R1-P2-01`（同題） | codex／grok | `Task 9.4` 刪除 `types.ts:1582`／`:2257` 兩個錯錨，改寫為「事件路徑現無 typed `n_train` 欄；要 typed 面須新增事件摘要型別並具名」 |
| `CODEX-R1-P1-04` | codex | `Task 9.2a` 明列 xfail 之 node id 與 `-rxX` 判準（`1 xfailed` 才算過；`1 passed`／`no tests ran` 皆不過）；`Task 9.3` 指定 register 重掃 receipt 路徑與逐條計數相等之機械驗收 |

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`docs/SPLITUNIFY_TODO.md` 之 `§C-9`（`grep -n '^## §C-9' -A260 docs/SPLITUNIFY_TODO.md`）與 `§B` 批次表之 `B9A`–`B9F` 六列。
- **本輪 diff**：`git show 87d38dd9 -- docs/SPLITUNIFY_TODO.md docs/MULTI_AGENT_ORCHESTRATION.md docs/DEVELOPMENT_GUIDE.md CLAUDE.md scripts/stampable_artifacts.txt`
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 之 `HISTORY-BEGIN`～`HISTORY-END` 與「## 沿革與追溯索引」節，以及逐字標記「作廢／前版／舊敘述／原寫」之字面。**finding 之 source anchor 落在歷史段者不受理**（`completeness --single` fail-closed 拒收整份交件）。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: SPEC 戳記已閉 → `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0，三家 APPROVED、body sha256 `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`。派工後預期值: 不變（本輪不動 SPEC）。
fact-verified: 34 條 mutation 在 §C-9 機械全覆蓋 → `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` ＝ **34**，且 `M-SU-D2-01`..`34` 逐號無缺。
fact-verified: §C-9 列出的 pytest 路徑全部存在 → 對 `grep -oE 'tests/[a-zA-Z0-9_/]+\.py' docs/SPLITUNIFY_TODO.md | sort -u` 之 16 條逐條 `test -f` 皆 rc=0。
fact-verified: 前批偷跑生產碼已回退 → `git status --porcelain` 對 `momentum/Analysis/event_samples/` 與 `tests/momentum/` 無條目；實跑 87 passed（receipt `20260913T125919Z-splitunify-b9-revert-verify`，exit_code=0）。
fact-verified: 兩道產出端閘皆過 → `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_TODO.md` rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-stamp-r1/synth.md docs/SPLITUNIFY_TODO.md` rc=0。

assumed: `Task 9.2a` 的 xfail 判準（`-rxX` 輸出須含 `1 xfailed`）**在 pytest 的實際輸出格式下可機械判讀**。**我的否證觀測（已先跑）**：現行該測試是 fail 不是 xfail（`xfail` 標記尚未加），所以我**無法**在現況下實跑驗證那條判準的字面。**我沒查**：`-rxX` 在本專案 pytest 版本與 `-q` 併用時，`1 xfailed` 是否真的出現在 summary 行（若格式不同，該驗收條寫了也判不出來）。← **請直接攻這條**，實跑一個現成的 xfail 測試看輸出字面。

assumed: `Task 9.3` 的 register 重掃 receipt 之計數相等判準可執行——即 `grep -cE '^\| \`C5-[0-9]+\`' docs/SPLITUNIFY_SPEC.D-002.md` 會回 29。**我的否證觀測（已先跑）**：該命令實跑得 **29**，與 register 表列數相符。**我沒查**：該 grep 之反引號在寫進 TODO 的 markdown 之後是否仍為可直接複製貼上的字面（跳脫層數）。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| 家數字面漂移是否還有殘留 | 已改四處：`CLAUDE.md` 決策表、ORCH `:41`／`:194`／`:195`、`DEVELOPMENT_GUIDE.md:59` | 🔴 **請用不含排除條件的 grep 自證完備**（我上一輪只掃「雙家族」，漏掉字面為「兩家族」的 ORCH:194，正是 `CODEX-R1-P1-01`）。已關閉之舊 epic 文件（`FRACDIFF_*`／`FF_*`／`GAP1_*` 等）屬歷史紀錄，依 forward-only 不改——請判此劃界是否成立 |
| `Task 9.4` 之前端落點 | `types.ts` 兩個錯錨已刪；`EventTablesPanel.tsx:361` 與六支既有 vitest 為真消費點 | 那六支 vitest 的**行號**是否仍正確；`EventAnalyzeResponse` 之 `summary` 為 `Record<string, unknown>` 時，`Task 9.4` 的「前端型別面」是否根本不該存在於本 Task |
| 批次切法 `B9A`–`B9F` | composer 於 stamp-r1 判「接受六批、不再合併或再拆」；codex 判「9.3∥9.4 可併成 5 gates」 | 🔴 **兩家分歧未收斂**——請各自給出你的批數與**可執行的發現方式**（若批數錯，在第幾批、跑什麼會看出來） |
| §V ↔ §C-9 對照 | composer 列出三條「§V 有、§C-9 無具名承接」之 ASSERT | codex 另主張「clusters remain event-level／purged-assignments disjoint／composite-key error message 應補進 §V」——**這會動到已蓋章的 SPEC**，請判是否值得為此重開 SPEC（含重新蓋章成本） |
| 受戳記資產白名單 | `scripts/stampable_artifacts.txt` 加入 `docs/SPLITUNIFY_SPEC.D-002.md` 後 provenance 通過 | 該加列本身的 diff 是否合該檔檔頭之封閉性要求（不得含萬用字元／目錄前綴／`..`）；以及「其餘 `docs/` 受戳記檔不一併加入」之殘留理由是否成立 |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 逐條重跑你自己在 stamp-r1 提出的反例，對每條給 `CLOSED` 或 `STILL-OPEN`（codex 四條、grok 一條；composer 本輪無自提 finding，請改為獨立複驗上表四項修補）。
   **(1b)** 對每條判 `CLOSED` 者，寫出**你重跑的那一條命令與觀測到的輸出特徵**——不接受「已確認修好」這類無標的說法。
2. **(2a)** `B9A`–`B9F` 六批 vs codex 的五批（9.3＋9.4 併）：你選哪個？
   **(2b)** 若選錯，主委會在第幾批、跑什麼命令、看到什麼現象而發現？
3. **(3a)** codex 主張補進 §V 的三條（clusters 事件級、purged／assignments 互斥、複合鍵錯誤訊息）：值得為此重開已蓋章的 SPEC 嗎？
   **(3b)** 若判「值得」，請說明重開後的重新蓋章成本由誰付、以及不重開的**具體風險**（哪一個實作分支會因此無測試可紅）；若判「不值得」，請指出這三條在 `§C-9` 的承接是否足以讓「改壞會紅」成立。
4. **(4a)** 現在可以領 impl token 進 `Task 9.1` 了嗎？
   **(4b)** 若可以，說明你檢查了什麼才敢說可以；若不可以，列**最小**閉合集合（不是願望清單）。

## 🔴 本輪格式硬約束（DOCROT／CXSTAMP 2026-09-13 上線；違反會被機械閘退件）
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**（缺則 `completeness_check.sh --single` fail-closed 拒收整份交件）：
   - `CODE-ANCHOR: <path>:<line>`（或 `<path>:<A>-<B>`）
   - `MUTATION: <可執行的破壞>`
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。`**碼證**:` 後接換行再條列＝空殼，會被退件。
4. **零 findings 時**須用 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的零 findings sentinel 形態，且 sentinel 內同樣要有**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**——🔴 **不得填日期**（stamp-r1 codex 填 `CLOSED: 2026-09-13` 被 `verdict_parse` 拒收，整輪卡住）。

## 🔴 本輪是 DOCROT 的成效量測第一輪
`doc_friction_ratio`（唯一權威＝`handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md`）＝本輪 synth 附錄中「碼證／來源摘要之 `path:line` 落在標的之歷史段，或斷言命中封閉字面（多落點／漏一處／同一計數／前版修法／原寫／已作廢主張）」之 canonical finding 數 ÷ 本輪 canonical finding 總數。
**及格線＝本輪與下一輪皆 ≤0.30，且每輪 finding 總數 ≤20。**
⇒ 請照實寫 finding，**不要**為了讓數字好看而少提；但請先確認你的落點**不是歷史段**（見上「不在審查範圍」）。

## 產出
canonical 四欄 findings + **Verdict**。**禁改碼、禁改 SPEC、禁改 TODO**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
