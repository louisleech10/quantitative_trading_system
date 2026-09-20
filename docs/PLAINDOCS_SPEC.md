# PLAINDOCS — 白話說明資料夾整理（封存、索引、內容追平） — SPEC

> 來源 PLAN/診斷：使用者 2026-09-19「白話文檔說明跟 HTML 那邊好亂，我已經不知要看哪一份」＋ 2026-09-20「若這是中大任務，那是不是要將白話文檔整理放到最前面」　|　日期：2026-09-20　|　對應 TODO：`docs/PLAINDOCS_TODO.md`（本 SPEC 凍結後產）

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：**中**。非 1 函式／1 test（跨 白話說明/ 全集 ＋ 4 支腳本 ＋ `scripts/fact_keys.json`），故非小；
  未命中 a-d（見下），故非大。
- **命中高風險原則**：**無**。逐條否證：
  - **(a) 數值／資料品質**：本票不產生、不修改任何數值、特徵、標籤或快取。改動集合為 `白話說明/**.md`、
    `scripts/fact_keys.json`、`scripts/plain_docs_sync_check.sh`、`scripts/plain_docs_render.py`、
    `docs/**.md` 之交叉引用行。**零** `momentum/`／`api/`／`data_cache/` 改動。
  - **(b) 跨模組／共用路徑**：`scripts/fact_keys.json` 雖被多支守衛讀取，但本票只改**資料列**
    （路徑字串與生成區塊內容），**不改任何 schema、鍵名或讀取邏輯**。`plain_docs_sync_check.sh` 之
    受管清單為**現讀導出**（`_managed_list()`，`scripts/plain_docs_sync_check.sh:49-51`），
    移入 `Archived/` 即自動脫管，無須改該函式。
  - **(c) 多 phase／難回退**：四 Phase，每 Phase 獨立 commit；回退＝`git revert` 單一 commit（§R）。
  - **(d) ML／回測正確性**：本票不觸及任何模型、回測或統計路徑。
RISK-HIT: none

- **中任務義務**：完整管線（SPEC ＋ TODO ＋ 兩家 adversarial），不得跳步。
- 🔴 **本票之反模式警戒**：本票前身（SEARCH2EVENT）連犯三次「SPEC 寫死未查證之具體值」。
  ⇒ 本 SPEC **刻意不列舉要封存的檔名**。🔴 **v3 更正**：v2 於此宣稱「改為可機械導出的判準」，
  該宣稱已被審查 r1 兩家推翻（見 §C-1 v3）——「白話檔 → 票」無機械對映。v3 改為
  「選擇具名為人工判斷 ＋ 查證逐條機械複驗」。任何把檔名寫死進本 SPEC 的修訂仍為缺陷。

## §A 假設與待使用者確認（事故：拿推論代替問人）

FACT-RECEIPT: 🔴 **本檔不記份數**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））：v2 記「25 份含 README」而乾跑覆蓋 24 份，
兩者皆未含當日稍晚新建之 `EVENTSCAN方向與做法.md` ⇒ 寫死份數必然在下一份白話檔出現時過期。
⇒ 全集一律由 Task 2.1 以 `ls 白話說明/*.md` **現讀**取得（§C-1-6），本 SPEC 與其 TODO **禁記份數**。
FACT-RECEIPT: `scripts/plain_docs_sync_check.sh:49-51` 之 `_managed_list()` 為 `ls *.md` 現讀導出且排除 `Archived/`；註解 `:35` 逐字「受管檔（不含 Archived/；已封存者不再要求同步）」（主委讀碼 2026-09-20）
FACT-RECEIPT: `scripts/live_doc_registry.json:103` 已登記 `白話說明/Archived/`；`scripts/fact_keys.json:169-174` 已列六份既存 Archived 檔 ⇒ 封存為**既有支援之操作**，非本票新造（主委實跑 `grep -n 白話說明 scripts/live_doc_registry.json` 2026-09-20）
FACT-RECEIPT: 封存候選之引用面實跑掃出五類位置：`scripts/plain_docs_sync_check.sh`（WATCHED case 分派，:71/:73/:80/:90/:93/:103/:120/:121）、`scripts/plain_docs_render.py:35-36`、`scripts/fact_keys.json`（:350/:414/:674/:2433-2545）、`白話說明/*.md` 內部連結（`IC健檢偵察結果.md:11,13,126`、`接下來要做什麼.md:8,112,292,366,382`）、`docs/*.md`（`ROADMAP.md:41`、`SCAR_LEDGER.md:22`、`GAP3D2_IMPL_HANDOFF.md:20`、`DOCROT2_TODO.md:64,70,78`、`IC_QUANT_GAP_REGISTRY.md:62`）（主委實跑 grep 2026-09-20）

**已確認（使用者回覆＋日期）**：
| 項 | 裁定 | 出處（逐字） |
|---|---|---|
| 要不要整理 | 要 | 使用者 2026-09-19：「該 ARCHIVED 就移走」 |
| 內容要不要追平 | 要，且不限白話 | 使用者 2026-09-19：「任何沒更新到最新進展的文檔都要更新」 |
| 排序 | 置於 `RM-EVENTSCAN` **方向定案之後、其實作之前** | 使用者 2026-09-20：「白話文檔整理排在 EVENTSCAN，但先把方向與做法確定定案後，才開始白話文檔整理」 |
| 本 session 邊界 | 本票完工即停，後續另開 session | 使用者 2026-09-20：「這個 Session 就到白話文檔整理完成就停，下一步到新的 Session 開始」 |

**待使用者確認：本任務無。**
理由：本票之三項可能需使用者裁定者（要不要整理／追平範圍／排序）皆已於上表取得逐字裁定；
封存清單之**選擇**為主委人工判斷但須逐份具名 `ticket_id`，其**查證**逐條機械複驗（§C-1 v3）；
選擇之對錯由審查輪把關，不需使用者裁定。若查證求值不出，依 §C-1-4 標 `missing_ticket_row` 並於 Phase 1 處理完畢，
**不得**以「問使用者」繞過判準。

**assumed（請審查方優先攻）**：
🔴 **v3：下列第一、三條已於審查 r1 被否證，保留原文並附裁定**（依本專案「被推翻之假設不得靜默刪除」）。

assumed（**已否證**）: `Archived/` 之檔不被任何機械閘要求同步，故封存後不會產生新紅燈。
→ **裁定：不成立**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））。`Archived/` **只是 `plain_docs_sync_check.sh` 之脫管區**，
移動仍會同時影響 HTML／index 產物與 fact-key 之 target／status scope。
⇒ §C-2 之五類同步點**不可省**，且 Task 2.2 驗收須含 `plain_docs_render.sh --check` 死連結 == 0。
（原否證觀測與主委自述保留：我只讀了 `_managed_list()`，沒有逐支確認其餘守衛的掃描範圍。）

assumed: `scripts/fact_keys.json` 之封存候選引用皆為「資料列」，改路徑字串不會使任何生成區塊之 schema 檢查轉紅。
→ 否證觀測：指出某個 fact key 之 schema 綁定該路徑之目錄層級（例如驗 `白話說明/<name>.md` 之形狀而拒 `白話說明/Archived/<name>.md`），或 `gen_fact_key_blocks.sh` 之收案綁定檢查會因路徑改變而 fail-closed。／我跑了：我只 grep 出現位置，**沒有**讀 `gen_fact_key_blocks.sh` 對這些鍵的驗證邏輯。

assumed（**已否證，且為本票最重要之一條**）: 「票已收票且無待使用者 UAT」此一判準可由現有文件機械導出，不需人工逐份判斷。
→ **裁定：不成立**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md） 兩家獨立撞題）。
**「白話檔 → 票」這一段沒有任何機械來源**，主委先前靠檔名相似度與內容閱讀推定。
反證：`EVTLABEL施工進度.md` 明載四票混合範圍；`接下來要做的票.md` 被判 `permanent` 卻是 `RM-GLOBALH` 之權威路徑。
⇒ §C-1 v3 全面重設計為「選擇具名 ＋ 查證機械」。**「票收了沒」仍可機械查證，不可機械的是「哪份檔算哪張票」。**
（原自述保留：我只對 24 份乾跑過一次，那是我自己判的，沒有第二人複驗。）

assumed（**新增，待攻**）: `ticket_id` 之人工指定，經審查輪把關即足以取代機械對映。
→ 否證觀測：舉出一種情形，使兩位審查者對同一檔之 `ticket_id` 指定產生分歧且無客觀判準可裁；
或指出該指定錯誤不會被 §C-1 三項查證中任何一項擋下（即錯誤指定仍可通過全部查證）。
／我跑了：我只確認三項查證各自可複驗，**沒有**驗證「錯誤的 `ticket_id` 指定是否必然被擋」。

## §C 約束（不重抄，引用 + 只列本任務相關）

### §C-1 封存判準

🔴 **v3 全面重設計（審查 r1 兩家共十條 BLOCKING，主委原設計不成立）**。
被推翻的是 v1／v2 之核心主張：**「哪份檔對應哪張票」可以機械導出**。

**為何不成立**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md），兩家獨立撞題）：
repo 內**不存在**任何「白話檔 → 票」之對映來源。v2 之三值靠檔名相似度與內容閱讀推定，那是**判斷不是機制**。
具體反證：`EVTLABEL施工進度.md` 明載 TIERTOGGLE／SPLITUNIFY／GLOBALH／UAT **四票混合範圍**，
按名可對到其中任一票，而只要那票收了就會被推向封存；
`接下來要做的票.md` 乾跑判 `permanent`，但它是 `docs/ROADMAP.md` 中 `RM-GLOBALH` 之權威路徑
⇒ C-1-0 之括號句「不存在以它為單一主題之列」為假。三值**不互斥**。

**v3 之修法＝把「選擇」與「查證」分開**，不再宣稱前者可機械化：

- **選擇（judgment，須具名）**：每份檔由主委指定其 `ticket_id`（可為多個），
  或標 `permanent`（跨票導航／逐日紀錄）。**此步為人工判斷，SPEC 不假裝它是機械的。**
- **查證（機械，逐條可複驗）**：對每個指定之 `ticket_id`，下列三項**全部**須以
  `<path>:<line>` 引用實檔實行，且該行須逐字含該 `ticket_id`：
  - **C-1-1 票已收票**：該 `ticket_id` 於 `docs/ROADMAP.md` 之 `roadmap-status`、
    `docrot2-batch-status`、`splitunify-residual-status` 任一生成區塊之狀態欄為「已完成」，
    **或**於 `docs/IC_QUANT_GAP_REGISTRY.md` 標 `CLOSED`。
    🔴 **v3 更正**：v2 只列前二來源，漏掉 `docrot2-batch-status`／`splitunify-residual-status`
    兩個生成區塊（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md） 抓出：乾跑用前者封存 `DOCROT2施工進度.md`，而該區塊不在 v2 所列來源內）。
  - **C-1-2 無待使用者動作**：該檔未被 `docs/GAP3_UAT_CHECKLIST.md`、`白話說明/GAP-3驗收清單.md`
    引用為必讀，且其任一 `ticket_id` 於 `docs/IC_QUANT_GAP_REGISTRY.md` 無標「UAT … 待使用者」之列。
  - **C-1-3 非權威路徑**：該檔**未**出現在任何生成區塊之權威路徑欄
    （判準＝`awk -F'|' '/^\| [0-9]/ {print $6}' docs/ROADMAP.md | grep -c '<name>'` == 0）。
    🔴 **v3 新增**：`接下來要做的票.md` 即因此條而不可封存——這是 v2 三值互相打架之根因。

**封存 ⟺ 指定了至少一個 `ticket_id` 且 C-1-1、C-1-2、C-1-3 三者皆為真。**
`permanent` 之檔**不參與**上列查證。其餘一律 `hold`。

🔴 **C-1-4 `hold` 之理由為封閉集合**（四值，擇一）：
`ticket_open`（票未收）／`uat_pending`（待使用者）／`is_authority_path`（是權威路徑）／
`missing_ticket_row`（指定之 `ticket_id` 在四個來源皆查無該列）。
最後一值**必須**在 Phase 1 處理完畢（補列或更正 `ticket_id`），**不得**留到後面 Phase
（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md）：v2 要求 Phase 4 補列後重跑，但清單在 Phase 2 已凍結並移動，
四 Phase 無反向邊 ⇒ 補列後永遠不會被重新求值。v3 把補列前移至 Phase 1，消除該 forward dependency）。

🔴 **C-1-5 例外之禁止**：本 SPEC 與其 TODO **不得**出現「除了 X 以外」「X 另案處理」這類逐檔例外。
查證三項為真即移、任一為假即留。若審查方認為某檔之結果違反直覺，正確修法是**改其 `ticket_id` 指定或改查證項**
並重新對全集求值，不是加例外。

🔴 **C-1-6 全集定義**：`白話說明/*.md` 之**現讀**全集（排除 `README.md`）。
v2 引用之乾跑覆蓋 24 份，**已過期**——審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md） 抓出當時尚未建立之
`EVENTSCAN方向與做法.md` 漏列，現為 25 份。⇒ **Task 2.1 須自己現讀 `ls`，禁引用乾跑之份數**；
乾跑檔 `handoffs/run_receipts/plaindocs_c1_dryrun.md` 自 v3 起**只作歷史紀錄，不得當輸入**。

### §C-2 引用同步（封存後必須同步之五類位置，逐類機械掃）

移動任一檔後，下列五類位置之引用**必須**同步改為 `白話說明/Archived/<name>.md`，
或（當該引用之語意為「必讀」時）改為指向仍在現行區的替代檔：

1. `scripts/plain_docs_sync_check.sh` 之 WATCHED case 分派臂
2. `scripts/plain_docs_render.py` 之渲染清單
3. `scripts/fact_keys.json` 之路徑列與生成區塊內容
4. `白話說明/*.md`（含 `Archived/*.md`）之 markdown 連結
5. `docs/*.md` 之路徑字串

**驗收之唯一判準**：`grep -rn --include='*.md' --include='*.json' --include='*.sh' --include='*.py' '白話說明/<name>.md' .`
之輸出中，**不含 `Archived/` 前綴之命中數為 0**（對每個被移動的 `<name>` 分別求值）。

### §C-3 內容追平之範圍（使用者 2026-09-19「任何沒更新到最新進展的文檔都要更新」）

本票之追平**限於**「該文件宣稱的狀態與 repo 實況不符」這一類，且**只改狀態敘述，不改歷史紀錄**。
逐份判準：文件內任何「現況／進度／下一步」敘述，其所指之票或批次狀態，須與
`docs/ROADMAP.md`＋`HANDOFF.md` 生成區塊一致。歷史流水帳（「📌 <日期>：…」）**不得回頭改寫**
（依「面向未來不溯及既往」：修正只考慮以後）。

### §C-4 不在本票範圍

- 不改任何守衛之**判定邏輯**（只改其資料列與 case 分派臂）。
- 不新建任何治理工具（CLAUDE.md:138）。
- 不改 `docs/site/*.html` 之生成方式；HTML 由既有 `plain_docs_render.sh` 重跑產出。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

🔴 **v3 修正（審查 r1 兩家共同抓出，v2 之 Phase 1 會製造新問題）**：
v2 要求「凡權威路徑以 `白話說明/` 起首者一律改指新建之 `docs/` 技術文件」，三處錯誤：
① **寫死「兩列」而實際四列**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））——`:41` `RM-TIERTOGGLE`、`:44` `RM-GLOBALH`、
   `:47` `RM-EVENTSCAN`、`:49` `RM-PLAINDOCS`；且 v2 把 `RM-GLOBALH` 標成 `:47`，**那行其實是 `RM-EVENTSCAN`**。
   🔴 此為本專案反覆發生之「寫死未查證之值」同型（SEARCH2EVENT 該票內犯三次），主委於本票再犯一次。
② **會逼生空文件**：`RM-EVENTSCAN` 之權威路徑即 `白話說明/EVENTSCAN方向與做法.md`，
   而該檔第 3 行逐字「這份是給你看的方向說明，不是規格」，且 ROADMAP 該列下一步含
   「未有結論前方向不算定案」⇒ 照 v2 會逼主委在方向未定案前替它生一份 SPEC。
③ **會換掉真權威**：`RM-TIERTOGGLE` 之真權威是 `tests/momentum/test_tier_toggle_sync.py`
   與 `scripts/ic_wiring_check.py`，改指主委代寫之新 `docs/` 檔反而是降級；
   且 `RM-FU-3` 列已有先例——其權威路徑為 `.py`，⇒ **權威路徑本來就不限 `docs/`**。

**v3 之 Phase 1 收窄為：只處理「該檔本票會移動」者，且改指既有權威（碼／測試／既有 docs），禁新建文件。**
v3 之順序不變：**Phase 1 權威路徑整治 → Phase 2 導出並移動 → Phase 3 README 重整 → Phase 4 內容追平**。

### Phase 1 — 解除「本票將移動之檔被當技術權威」（依賴：無）

**Task 1.0 — 逐列改正權威路徑，並補齊缺列**
- 目標：使**本票將移動之檔**不出現在任何生成區塊之權威路徑欄。
  檔案：`scripts/fact_keys.json` 之 `roadmap-status`／`docrot2-batch-status`／`splitunify-residual-status` 三區塊。
  既有 caller/影響面：三區塊由 `gen_fact_key_blocks.sh --write` 寫入，須改 fact key 而非手改宿主檔。
- 改法：
  ① 現讀列出權威路徑欄以 `白話說明/` 起首之**全部**列（禁引用本 SPEC 之數字，見上 ①）；
  ② 逐列判該檔是否為本票之封存候選（＝ Task 2.1 之 `ticket_id` 指定結果，故 Task 2.1 之**指定**
     須先於本 Task 執行，其**查證**則在 Task 2.1 完成——兩者同 Phase 內序）；
  ③ 是候選者，改指**既有**權威（優先序：該票之 `docs/` SPEC／TODO → 釘住該行為之測試檔 → 相關 `scripts/`）。
     **禁新建任何文件充當權威**；找不到既有權威者，該檔**改判 `hold` 且 `hold_reason="is_authority_path"`**，
     不移動、不改其權威路徑列。
  ④ 非候選者（如 `RM-EVENTSCAN` → 方向書、`RM-PLAINDOCS` → README）**不動**，本票不處理。
  ⑤ 補齊 `hold_reason="missing_ticket_row"` 之列（C-1-4 要求在本 Phase 完成，不得留到後面）。
- **驗證（可證偽）**： 對 Task 2.1 之每個 `decision=="archive"` 之 `<name>`：
  `awk -F'|' '/^\| [0-9]/ {print $6}' docs/ROADMAP.md | grep -c '<name>'` == 0；
  且 `jq -r '.[] | select(.hold_reason=="missing_ticket_row") | .name' handoffs/run_receipts/plaindocs_archive_set.json | wc -l` == 0（本 Phase 結束時）。
  **改前須先實跑同一 awk 並記錄其值 >= 1**，否則無從分辨「已整治」與「本來就沒有」。
- **邊界（≥2 具體場景）**：
  ① 某票之唯一紀錄確實只有白話檔且無既有權威可指（乾跑候選 `RM-TIERTOGGLE`）
     ⇒ 依改法③改判 `hold`，**不得**新建文件把它「整治」掉。
  ② 某列之權威路徑欄為 `—` 或空 ⇒ 不在本 Task 範圍，不得順手填。
- **存活至**：本票收票後保留。
- **覆蓋風險**：無；Phase 2 只移動檔案，不改權威路徑欄。
- 不可做：不得手改 ROADMAP 生成區塊；不得為了讓驗收 grep 轉綠而刪整列。

### Phase 2 — 導出封存清單並移動（依賴：Phase 1 Task 1.0）

**Task 2.1 — 逐份指定 `ticket_id` 並機械查證，凍結為 receipt**
- 目標：把「選擇」與「查證」分開——選擇具名為人工判斷，查證每條可機械複驗。
  檔案：新建 `handoffs/run_receipts/plaindocs_archive_set.json`（純 receipt，非治理工具）。
  既有 caller/影響面：新建無 caller。
- 改法：以 `ls 白話說明/*.md` **現讀**全集（排除 `README.md`；禁引用乾跑份數，見 C-1-6）逐份輸出：
  `{name, kind: "permanent"|"ticketed", ticket_ids: [str], checks: {c1_1, c1_2, c1_3}, decision: "archive"|"hold"|"permanent", hold_reason: str|null}`
  其中每個 `checks.*` 為 `{value: bool, evidence_path: str|null, evidence_line: int|null}`。
  **`kind="permanent"` 者三項查證一律 `null` 且 `decision="permanent"`**，不參與查證。
- **驗證（可證偽，禁「更穩定/確認正確」）**： `jq '[.[] | select(.decision=="archive")] | length' handoffs/run_receipts/plaindocs_archive_set.json`
  == `jq '[.[] | select(.checks.c1_1.value==true and .checks.c1_2.value==true and .checks.c1_3.value==true)] | length' <同檔>`；
  且 `jq -r '.[] | select(.decision=="hold") | .hold_reason' <同檔> | sort -u` 之每一值
  屬封閉集合 `ticket_open|uat_pending|is_authority_path|missing_ticket_row`；
  且 `jq '[.[] | select(.decision!="permanent")] | length' <同檔>` == `ls 白話說明/*.md | grep -vc README.md` 減去 permanent 數。
  🔴 **v3 更正**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））：v2 之等式為 `c1_1==true and c1_2==false`，
  與 C-1-2 之命名（無待使用者＝true 才可封存）及其邊界②互相矛盾 ⇒ 該 Task **永不可能轉綠**。
  三項一律以 `==true` 為封存條件。
- **邊界（≥2 具體場景）**：
  ① 指定之 `ticket_id` 在四個來源皆查無該列 ⇒ `c1_1.value=false`、`evidence_path=null`、
     `hold_reason="missing_ticket_row"`，且**該檔須回到 Phase 1 補列或更正 `ticket_id`**（C-1-4）。
  ② 某檔 C-1-1 為真但被 UAT 清單引用 ⇒ `c1_2.value=false`、`hold_reason="uat_pending"`、
     `c1_2.evidence_path` 指向該 UAT 清單之實際行。
- **存活至**：本票收票後保留（供日後新增白話檔時重跑同一查證）。
- **覆蓋風險**：無。Phase 3、4 皆不改本檔。
- 不可做：不得在本 Task 內移動任何檔案；不得把查證結果手寫進 SPEC 或 TODO；
  **不得宣稱 `ticket_id` 之指定是機械導出的**（它不是，見 §C-1 v3 之說明）。

**Task 2.2 — 依 receipt 移動檔案並同步五類引用**
- 目標：把 `archive==true` 之檔移入 `白話說明/Archived/`，並依 §C-2 同步全部引用。
  檔案：`白話說明/**`、`scripts/plain_docs_sync_check.sh`、`scripts/plain_docs_render.py`、
  `scripts/fact_keys.json`、`docs/*.md`。
  既有 caller/影響面：§A 之 FACT-RECEIPT 已列出五類共 19 處命中行號，為同步點之下界（實作時須重掃取最新）。
- 改法：`git mv` 逐檔；每移一檔即對該檔名執行 §C-2 之驗收 grep，rc 不合即當場修，不累積。
- **驗證（可證偽）**： 對 `archive==true` 之每個 `<name>`：
  `grep -rn --include='*.md' --include='*.json' --include='*.sh' --include='*.py' "白話說明/<name>.md" . | grep -vc Archived` == 0；
  且 `bash scripts/plain_docs_sync_check.sh` rc=0、`bash scripts/plain_docs_order_check.sh` rc=0、
  `bash scripts/plain_docs_render.sh --check` rc=0（死連結數 == 0）。
  **改前須先實跑同一 grep 並記錄其值 >= 1**，否則無從分辨「已同步」與「本來就沒引用」。
- **邊界（≥2 具體場景）**：
  ① 某引用之語意為「必讀」（例：`docs/GAP3D2_IMPL_HANDOFF.md:20` 之「每批完成後更新」）
     ⇒ 不得只改路徑，須改為指向仍在現行區之檔，或於該行註明該票已收票、該白話檔已封存。
  ② `scripts/fact_keys.json` 之生成區塊內容改動後，須跑 `bash scripts/gen_fact_key_blocks.sh --write`
     並確認其收案綁定檢查 rc=0（若 fail-closed 報錯，屬 assumed 被否證，開 finding 而非繞過）。
- **存活至**：本票收票後保留。
- **覆蓋風險**：Phase 3 會重寫 `README.md`，其中含封存檔之連結；Phase 3 須以本 Task 之結果為輸入，不得各自判斷。
- 不可做：不得 `rm` 任何檔（一律 `git mv`）；不得改任何守衛之判定邏輯。

### Phase 3 — README 結構重整（依賴：Phase 2 全部 Task）

**Task 3.1 — README 只留「索引 ＋ 待決 ＋ 指向歷史」三段**
- 目標：使用者打開 `白話說明/README.md` 一屏內看完「有哪些、看哪份、現在在哪」。
  檔案：`白話說明/README.md`、`scripts/fact_keys.json` 之 `plaindocs-index` 鍵。
  既有 caller/影響面：`plaindocs-index` 生成區塊由 `gen_fact_key_blocks.sh` 寫入，須同步改 fact key 而非手改 README 生成區。
- 改法：README 改為固定四段且**依此順序**：
  ① 一行「只想知道現在怎樣 → 看 `現在做到哪.md`」；
  ② `plaindocs-index` 生成區塊（含現行區與 `Archived/` 兩張表）；
  ③ `handoff-pending` 生成區塊（等你決定的事）；
  ④ 一行指向 `白話說明/歷史紀錄.md`。
  現有 README 之「以下是歷史紀錄」整段（📌 條目）**原文搬移**至新檔 `白話說明/歷史紀錄.md`，不改寫內容。
- **驗證（可證偽）**： `grep -c '^> 📌' 白話說明/README.md` == 0；
  `grep -c '^> 📌' 白話說明/歷史紀錄.md` 等於搬移前 README 之同一計數（搬移前先存 `/tmp` 基準）；
  `grep -n 'BEGIN GENERATED' 白話說明/README.md` 恰兩處且順序為 `plaindocs-index` 先於 `handoff-pending`。
- **邊界（≥2 具體場景）**：
  ① 搬移後 `歷史紀錄.md` 本身成為受管檔（`_managed_list()` 會納入）⇒ 須於
     `plain_docs_sync_check.sh` 新增其 WATCHED case 臂，否則該閘 fail-closed 報「受管檔無 WATCHED」。
     🔴 **v3 指定其 WATCHED 為 `白話說明/README.md`**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））：
     v2 未指定監看集合；若沿用 README 之 `scripts/ docs/GOV tests/governance/`，
     則每次動治理腳本都會要求更新歷史紀錄 ⇒ **強迫改寫 §C-3 明文禁止改寫的歷史流水帳**。
     指定為 README 之語意＝「README 新增歷史條目時，該條目應搬進本檔」，與其職責一致且不逼改舊條目。
  ② README 現存之過期敘述「這裡有四份，各有各的用途」（實為 25 份）須刪除；
     驗收＝`grep -c '這裡有四份' 白話說明/README.md` == 0。
- **存活至**：本票收票後保留。
- **覆蓋風險**：無。Phase 4 只改各份之現況段文字，不動本 Task 所建之 README 四段結構（🔴 v3 更正：v2 此處寫「Phase 3 只改各份內文」，與本 Task 自己就在 Phase 3 矛盾——codex 審查 r1 之對應 finding）。
- 不可做：不得手改生成區塊內容（一律改 `fact_keys.json` 後跑 `gen_fact_key_blocks.sh --write`）；
  不得在搬移時「順手改寫」歷史條目文字（§C-3）。

### Phase 4 — 現行區各份內容追平（依賴：Phase 3）

**Task 4.1 — 逐份比對狀態敘述與 repo 實況並修正**
- 目標：現行區每一份的「現況／進度／下一步」敘述與 `docs/ROADMAP.md`＋`HANDOFF.md` 一致。
  檔案：Phase 1 後仍在 `白話說明/` 根目錄之全部 `.md`（`README.md` 已由 Phase 3 Task 3.1 處理）。
  既有 caller/影響面：各份之 WATCHED 路徑（`plain_docs_sync_check.sh` case 臂）。
- 改法：逐份取出其「現況段」，與 ROADMAP 對應票列之狀態欄逐項比對；不符者改**該份**之現況段。
  **每改一處須記下 ROADMAP 之行號為依據**，寫入 `handoffs/run_receipts/plaindocs_content_sync.json`。
- **驗證（可證偽）**： `bash scripts/plain_docs_sync_check.sh` rc=0；
  且對 `plaindocs_content_sync.json` 之每一列，其 `roadmap_line` 所指之 ROADMAP 行確實含該列之 `ticket_id`
  （`sed -n '<line>p' docs/ROADMAP.md | grep -c '<ticket_id>'` == 1）。
- **邊界（≥2 具體場景）**：
  ① 某份之現況段所指之票在 ROADMAP 中狀態為「已完成」但該份寫「進行中」⇒ 改該份；
     **反向不成立**：若 ROADMAP 落後於該份，須改 ROADMAP 並於 receipt 標 `direction=roadmap`。
  ② 某份完全沒有「現況段」（純快照類，例 `IC健檢偵察結果.md` 自述「不隨進度更新」）
     ⇒ 記 `skipped: snapshot_by_design`，不強加現況段。
- **存活至**：本票收票後保留。
- **覆蓋風險**：無。
- 不可做：不得改寫歷史流水帳（§C-3）；不得為了讓 `plain_docs_sync_check.sh` 轉綠而只改一字
  （該閘之誠實邊界自述「可只改一字換綠燈」，本 Task 之 receipt 即為防此而設）。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 為 `none` 且本票無「宣稱驗正確性」之新測試 ⇒ 見 §N 之 mutation N/A 登記。
  **但 Task 2.1 之查證為本票唯一有判斷語意者**，故對它設 mutation。

  🔴 **v3 全面更換（v2 之 mutation 為假存活，兩家獨立撞題）**：
  v2 要求「改 receipt 之 `archive` 值 ⇒ `plain_docs_sync_check.sh` 轉紅」。
  **該閘根本不讀 receipt**——實跑 `grep -c archive_set scripts/plain_docs_sync_check.sh` == 0、
  `grep -c plaindocs_archive scripts/plain_docs_sync_check.sh` == 0；
  其唯一輸入為 `_managed_list()` 之 `ls 白話說明/*.md`（`:49`）。
  改 receipt 對它零影響 ⇒ 該 mutation **必然存活**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））。
  且 §C-4 禁止改守衛判定邏輯，故本票**不得**把該閘改成讀 receipt。

  **v3 之處置：不設 `ASSERT` 條、不新建任何腳本**，理由兩條（皆為實測而非偏好）：
  ① 本檔之 `ASSERT` 文法禁 shell 元字元（實測：含 `|`／`"`／`$` 之 `jq` 單行一律被拒），
     而本票唯一有判斷語意處之複驗**本質上需逐列迴圈** ⇒ 要滿足該文法就必須新建一支腳本；
  ② 新建腳本會擴大本票範圍，且與「不新建治理工具」擦邊。
  ⇒ mutation 改以**具名登記於 §N** ＋ 把可證偽之複驗寫進 Task 2.1／2.2 之驗證欄（該欄不限字元）。

  🔴 **本票之 mutation 實質內容**（由 Task 2.1／2.2 之驗證欄承載，此處只述其設計）：
  - **翻轉一列 `decision`**（挑 `decision=="archive"` 且三項查證皆 true 者）⇒ Task 2.2 之
    「非 Archived 引用 grep == 0」與「檔案實際位置」兩項須至少一項轉紅。
  - **把任一 `evidence_line` ±1** ⇒ Task 2.1 之「`sed -n '<line>p' <path> | grep -c '<ticket_id>'` == 1」須變 0。
    這是證明「引用不是擺設」的唯一方法。
  - **把一個已移動之檔搬回** ⇒ Task 2.2 之位置檢查須轉紅。
  **配對條件**（記取 SPLITUNIFY R-5 之假存活教訓）：翻轉對象**不得挑 `permanent` 之列**——
  其三項查證皆 `null`，翻轉不改變任何判定 ⇒ 必然假存活。
- 測試層級：整合（既有三支守衛腳本）＋ Golden 對照（Phase 3 之 📌 計數基準）。
  可獨立跑，不需 `run_api.py`。
- **防假綠**：不得為換綠燈而放寬或刪除 `plain_docs_sync_check.sh`／`plain_docs_order_check.sh` 之任何既有斷言；
  本票對這兩支只允許**新增** WATCHED case 臂與**移除**已封存檔之臂，不得改其判定函式。
- **邊界目錄**（本任務適用者）：空輸入（`白話說明/` 若全空 ⇒ `_managed_list()` fail-closed，見 `:52`）／
  重複·亂序（`plain_docs_order_check.sh` 之編號遞增）／並發寫（不適用，單人序列作業）。

## §R 回退

- 四 Phase 各自獨立 commit，可單獨 `git revert`。
- Phase 2 之移動全為 `git mv`，revert 即復原，無資料遺失。
- 任一守衛轉紅且非本票造成者，先以 `git stash` 隔離再排查，不得 `--no-verify` 繞過。
- 本票無 feature flag（無執行期行為）。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）

- **§G Golden / Baseline**：N/A — 本票 RISK-HIT 為 `none`，不碰數值／ML／回測，無 golden 可凍。
  唯一之對照基準（Phase 2 之 📌 條目計數）已寫入該 Task 之驗證欄，不另立 §G。
- **§V mutation（整票層級）**：N/A — 無新增「宣稱驗正確性」之測試。
  已對唯一有判斷語意處（Task 2.1 之查證）設最小 mutation，見 §V。

**殘留（本票不做、留待以後）**：

| 殘留 ID | 內容 | 為何現在不做 |
|---|---|---|
| `PD-RESID-ORDER` | 白話文檔整理相對 EVENTSCAN 之排序，主委建議前移但未取得使用者明示放行 | `user-ruling:2026-09-20 使用者提問「是不是要將白話文檔整理放到最前面」，主委已答建議前移並說明理由；使用者尚未回覆否決與否。依「省步唯一允許＝動工前明列讓使用者否決」，本票先行開工，使用者若否決即整票暫停` |
🔴 **v3 刪除 `PD-RESID-HTML`**（審查 r1 兩家／單家之對應 finding（逐條見 handoffs/reconcile/20260920-plaindocs-x-review-r1/synth.md））：v2 把它列為殘留，理由欄卻寫
「故列為 Phase 3 之收尾動作而非獨立殘留——若未產出 html 即為本票缺陷」——**一面列殘留一面說它不是殘留**。
HTML 生成本來就在本票範圍內（§C-4 已寫「HTML 由既有 `plain_docs_render.sh` 重跑產出」），
且每個 Phase 之 commit 都會跑它。⇒ 不是殘留，是每個 Phase 的收尾動作，已寫入 §R。
