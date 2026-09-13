# Reconcile — 20260911-splitunify-b9-review-r17

**來源** 20260911-splitunify-b9-review-r17-codex.md, 20260911-splitunify-b9-review-r17-composer.md, 20260911-splitunify-b9-review-r17-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **X1 收窄後之 basename 判準對 15 列仍不可執行（三家撞題，三家各自算出同一組 15 列）**——「`Task9.3`的fallback`b」「v17basename收窄判準對**15」「v17basename收窄判準對15個無」 | P1 | CODEX-R17-P1-01, COMPOSER-R17-P1-01, GROK-R17-P1-01 | 採納（🔴 **主委機械掃描與三家逐字一致**：消費面欄完全無檔名者恰 **15** 列＝`C5-01`..`C5-12`／`C5-20`／`C5-22`／`C5-24`。三家並同時指出硬套 basename 的兩種後果——**驗收永久紅**或**實作者靜默跳過而假綠**。改法：`Task 9.3` 驗收第 5 點改為**三段式、29 列互斥窮盡**：(甲) 有 `path:line` 之 **10** 列走精確 keyed；(乙) 有檔名無行號之 **4** 列走 basename；(丙) 這 15 列**明文排除於碼證對證之外**、該欄改填封閉字面 `NO-ANCHOR` 並逐列具名。🔴 **排除不等於免驗**：15 列之重掃結論仍須逐列寫入 receipt、分類欄照常對證 SPEC 現況，只有**碼證欄**不參與對證） |
| **X2 `SU-RESID-C5-TARGETS` 之觸發條件無機械觀測（三家撞題）**——「`SU-RESID-C5-TARGETS」 | P1 | CODEX-R17-P1-02, COMPOSER-R17-P2-02, GROK-R17-P2-02 | 採納（前版寫「`Task 9.3` 開工時若 basename 判準出現誤判」——**無判定人、無時點、無命令、無輸出特徵** ⇒ 該殘留可永久 `blocked-by` 而不升級，正是「殘留不得是偷懶」所禁。改為**兩條客觀事件、任一成立即升級**：①以 `awk` 掃 register 之無檔名列數，輸出 **≠ 15** 即代表 (丙) 組成員變動、排除清單過期；②`Task 9.3` 重掃**實際發現** (丙) 15 列中任一列分類需改動——該列既已有實質改動落點，須在同一次變更補 `TARGETS:`。並明定 **owner ＝ SPLITUNIFY epic 主委**、判定時機＝`Task 9.3` 驗收當下，另附誠實邊界句） |
| **X3 驗收第 5 點之「9 列／20 列」字面在 v17 修 `C5-25` 後已過期（兩家撞題）**——「`Task9.3`驗收第5點仍寫「有pa」 | P2 | COMPOSER-R17-P2-01, GROK-R17-P2-01 | 採納（v17 給 `C5-25` 補錨後，keyed 實測為 **10** 列、無錨為 **19** 列，而驗收條文仍寫 9／20；grok 另指出無錨清單仍含已補錨之 `C5-25`。🔴 **這正是本檔一路在打的「改了 A 沒同步 B」**，且這次是主委在同一輪內自己造成的。已隨 X1 之三段式改寫一併同步為 10／4／15，且 10 列清單已含 `C5-25`） |

### 本輪裁定
1. 🔴 **停輪歸類之共識決（使用者 2026-09-13 逐字「技術問題, 你們委員會共識決。我無法給出答案」交回）**：
   **composer `PROCEED`／grok `PROCEED`／codex `FIX-FIRST`** ⇒ **結論採 `PROCEED`**——進 `Task 9.1` 實作，不先補齊 `TARGETS:`。
   依據**不是數人頭**：①兩家均引 `HANDOFF.md:32` 使用者裁定「不再擴建治理工具；同型缺陷降級為具名殘留」並說明其適用；
   ②codex 自己在必答 1b 寫下退讓條件逐字「**若本立場不採，至少保留 `SU-RESID-C5-TARGETS` 並把這 15 個 ID 具名化**」——
   該條件**已於本輪全額滿足**（15 個 ID 已逐列具名、殘留已保留並補上可執行觸發）⇒ 三家在**實質處置**上其實已無分歧，
   差別只在要不要順便把 20 列錨點補完。
2. **X1–X3 已修**（TODO 之 `Task 9.3` 驗收第 5 點改三段式並具名 15 列；殘留觸發改兩條客觀事件）。
3. **戳記**：composer／grok 對 v17 body `d42b3f14…` APPROVED；codex REJECTED（其 BLOCKED-BY 即 X1／X2，本輪皆已修）⇒ 須對新 body 重簽一輪。
4. **下一步**：對新 body 取三家 APPROVED、`reconcile_stamps_check` rc=0 後，領 impl token 進 `Task 9.1`。

### 🔴 具名殘留（不得讀作已解決）
`SU-RESID-C5-TARGETS`：(丙) 那 15 列之 receipt **碼證欄不受機械對證保護**，只靠分類欄對證 SPEC 現況。
這是**已知且具名**之覆蓋缺口，理由類別 `blocked-by`，觸發條件與 owner 見 TODO 該段。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R17-P1-01
**斷言**: `Task 9.3` 的 fallback `basename` 對證在 20 列中有 15 列無任何檔名副檔名，故這 15 列的 receipt 無法被現行判準執行性地核對：`C5-01`..`C5-12`、`C5-20`、`C5-22`、`C5-24`。
**碼證**: VERIFY: `awk` 掃 SPEC register 得 `count=15` 且上述 ID；`C5-20` 對應實際 assignments seam。  
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:555  
MUTATION: 在 Task 9.2a 移除 `split_projection.py:555` 的 `feature_timeframe` 寫入，再跑 TODO:659 的 basename 對證；C5-20 仍無 `split_projection.py` basename 可綁定該破壞。
**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c; momentum/Analysis/event_samples/split_projection.py#99bfddace904。 [MAJOR] 信心度=High；目前 `grep -qF` 對 15 列只能永遠找不到帶副檔名的 basename，合法 receipt 會被卡住，或若以模組名代替則失去 path 身分。一次修訂可關閉：為這 15 個 ID 補實際 repo-relative source basename／line range；預期重掃 `NO_BASENAME=0`。排除 receipt 對證會弱化既有 gate，不採用。
## CODEX-R17-P1-02
**斷言**: `SU-RESID-C5-TARGETS` 的現行觸發句沒有判定人、精確時點、輸入 receipt、獨立重掃產物或比較命令；現有 Task 9.3 條文也沒有專用重掃機械閘，因此「receipt 通過但實際未重掃」可無限期不觸發。
**碼證**: VERIFY: `rg -n 'register-rescan|Task 9\.3|basename' scripts` 只命中一般 basename／既有文字工具，沒有 Task 9.3 receipt 重掃實作；現行觸發字面在 TODO:667-668。  
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:667  
MUTATION: 構造一份通過 receipt 第 1–4 點且碼證指向既有檔案行的交件，再不做獨立重掃；現行條文沒有任何命令會產生或比較第二份重掃結果，故無法觸發升級。
**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c。 [MAJOR] 信心度=High；一次修訂可關閉：直接把觸發改成「判定人=Task 9.3 驗收執行者；時點=首個 implementation commit 前；輸入=唯一通過第 1–4 點的 receipt 與同時點獨立重掃檔；命令=`TASK93_RECEIPT="$r" TASK93_RESCAN="$s" bash -c 'test -s "$TASK93_RECEIPT" -a -s "$TASK93_RESCAN" && diff <(sed -n "3,$p" "$TASK93_RECEIPT" | awk "{print \$1,\$2,\$3,\$4}") <(sed -n "3,$p" "$TASK93_RESCAN" | awk "{print \$1,\$2,\$3,\$4}")'`；rc≠0 或任一 fallback basename `grep -qF` 失敗即升級 `TARGETS` 並重簽」。
### 必答
1a=`FIX-FIRST`；1b：若錯選而應 `PROCEED`，首個 receipt 會以 `grep -qF` 在 15 列失敗，重跑上述 awk 應仍見 `count=15`；若本立場不採，至少保留 `SU-RESID-C5-TARGETS` 並把這 15 個 ID 具名化。
2a=適用於「補 20 列 TARGETS 以加一層收據腳手架」；`HANDOFF.md:32` 與 b16bed64 的原始裁定均把同型治理缺陷降為具名殘留，且 TODO:664-668 已明文套用。2b=N/A；機械分界是「補現有契約缺失的實際落點」可修，新增／加嚴驗收工具或以排除替代證據則屬治理擴建／弱化。
3a=15 列：`C5-01`..`C5-12`、`C5-20`、`C5-22`、`C5-24`。3b=補實際檔名與行範圍；不把它們排除於 receipt，因那會降低 fail-closed 覆蓋。
4a=不可執行；現句沒有 owner/time/command/independent rescan，且沒有現成專用命令。4b=採 P1-02 中的 owner、時點、雙 receipt `diff` 命令字面；任一分類差異或 basename check rc≠0 即升級並重簽。
5a=`REJECTED`；body hash 實跑為 `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`，C5-25 seam 實讀為 `ic_feed.py:56-65`、呼叫端 `pipeline.py:406-408`，本身無新增 finding。5b=阻擋項為 `CODEX-R17-P1-01`、`CODEX-R17-P1-02`，各可在一次修訂內關閉。
ASSUMPTIONS_VERIFIED: `git show 0908ffad` 指定 diff；register=29、exact anchors=9、fallback 無 basename=15、mutation IDs=40 且 01–40 連續；C5-25 seam／呼叫端與 brief 相符；HANDOFF ruling scoped search 未找到更早的「SPEC 欄位 vs 治理工具」分界定義。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → d42b3f14… rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r17-codex.md --family codex` → `COMPLETENESS_RC=0`；register awk → 15 IDs；`nl -ba` seam 56–65／406–408 實讀。
FAILURES_SEEN: review skill alias 路徑先誤拼後已改正；gstack analytics 寫入 ~/.gstack 被 sandbox 拒絕，未影響專案交件。
SCOPE_CHANGES: 僅新增本交件與 append SPEC 戳記；未改 production、tests、TODO 或根 HANDOFF.md；未 commit。
NUMERIC_OR_SCHEMA_IMPACT: none；review-only，SPEC body 未改，僅新增 r17 codex REJECTED stamp。
OUTPUT_ARTIFACT: `handoffs/20260911-splitunify-b9-review-r17-codex.md`; TMP_CLEANUP: `/private/tmp` 無本輪可辨識 workdir，`claude-501` 保留；`.BBE…`、root-owned `powerlog`、`sessions` 未動。
VERDICT: blocked
BLOCKED-BY: CODEX-R17-P1-01,CODEX-R17-P1-02
CLOSED:
STATUS: DONE
## COMPOSER-R17-P1-01

**斷言**: v17 basename 收窄判準對 **15/19** 個 no-anchor 列不可執行——消費面無任何 `*.py`／`*.tsx`／`*.json` 字面，填真實測試路徑之 basename 無法 `grep -qF` 命中，receipt 仍可能假過。

**碼證**: `awk` 掃 register → `/tmp/r17-register-scan.tsv`：`no_fname_in_no_anchor=15`（`C5-01`..`12`／`20`／`22`／`24`）；`docs/SPLITUNIFY_TODO.md:659-660` basename 判準；模擬 `test_splitunify_derive.py` basename 對 15 列全 FAIL。  
CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:96  
MUTATION: 對 `C5-01` receipt 填 `tests/momentum/Analysis/test_splitunify_derive.py:1` 且消費面仍為 `` `receipts.event_level` `` ⇒ basename `grep -qF` FAIL 但檔存在檢查 PASS。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d42b3f14c4e3

[P1] 修法：見必答 3b（`SU-RESID-C5-BASENAME-EXCEPT` 白名單 15 列 ＋ mutation-first-test-path 第 6 點）。可行性：§V 已具名各 `M-SU-D2-NN` 應紅檔，無新腳本。信心度=High。不阻 v17 戳記（與 v17 收窄＋`SU-RESID-C5-TARGETS` 殘留同向）。

---

## COMPOSER-R17-P2-01

**斷言**: `Task 9.3` 驗收第 5 點仍寫「有 path:line 的 **9** 列／其餘 **20** 列」，但 v17 修 `C5-25` 後 register 實測為 keyed **10** 列、no-anchor **19** 列，字面與機械掃描不一致。

**碼證**: `docs/SPLITUNIFY_TODO.md:656-659`（9／20）；`docs/SPLITUNIFY_SPEC.D-002.md:120`（`C5-25` 已含 `ic_feed.py:56-65`）；`/tmp/r17-register-scan.tsv`：`C5-25 anchor=1`；keyed 列＝`C5-13`/`14`/`19`/`21`/`23`/`25`/`26`/`27`/`28`/`29`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#d42b3f14c4e3

[P2] doc-literal-only。修法：將 L656-659 改為「**10** 列 keyed／**19** 列 basename」，keyed 清單加入 `C5-25`。可行性：單次字面替換。信心度=High。

---

## COMPOSER-R17-P2-02

**斷言**: `SU-RESID-C5-TARGETS` 觸發條件「basename 判準出現誤判」無機械觀測，殘留可永久 `blocked-by` 而不升級 `TARGETS:`。

**碼證**: `docs/SPLITUNIFY_TODO.md:667-668`；無對應 `scripts/` 或 `pytest` 節可判定「誤判」。

**來源摘要**: docs/SPLITUNIFY_TODO.md#d42b3f14c4e3

[P2] doc-literal-only。修法：見必答 4b（register 重掃分類不一致即觸發）。可行性：重用既有 `Task 9.3` 動工前置重掃流程，無新腳本。信心度=High。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R16-P2-01,COMPOSER-R16-P2-02

ASSUMPTIONS_VERIFIED: body sha256 `d42b3f14…`；register 29／keyed 10／no-anchor 19／no-filename 15；mutation 40 ID 01–40；`C5-25` seam 56–65 實讀正確；HANDOFF.md:32 適用  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `d42b3f14…`；`bash scripts/doc_format_precheck.sh` 兩檔 rc=0；`awk` register 掃描 → `/tmp/r17-register-scan.tsv`；`python3` basename 模擬 15 列 FAIL  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（`docs/SPLITUNIFY_SPEC.D-002.md` 戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）

STATUS: DONE
## GROK-R17-P1-01

**斷言**: v17 basename 收窄判準對 15 個無錨列不可執行——該列消費面無任何檔名副檔名字面，真實碼證之 basename 無法 `grep -qF` 命中，Task 9.3 驗收第 5 點對該 15 列無法完成（或被迫跳過檢查變成假閘）。

**碼證**: 探針 `/tmp/grok-r17-work/basename_scan.txt`：`UNANCH_NO_BASENAME=15`（`C5-01`..`12`／`20`／`22`／`24`）；`docs/SPLITUNIFY_TODO.md:659-660` 要求 basename 出現在消費面；模擬 `bn=test_splitunify_derive.py` ⇒ 15／15 FAIL；對照有檔名之 4 列（`C5-15`..`18`）可執行。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:659
MUTATION: 對 `C5-01` receipt 填 `tests/momentum/event_samples/test_splitunify_derive.py:1` 且消費面仍為 `` `receipts.event_level` `` ⇒ 檔存在檢查可 PASS，但 basename `grep -qF test_splitunify_derive.py` 對消費面 FAIL。

**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c

[P1] 信心度=High。修法＝必答 3b（15 列改對 mutation 應紅測試路徑、不走 basename）。可行性：§V 各 `M-SU-D2-NN` 已具名應紅檔，無新腳本、不需先補全表 `TARGETS:`。不阻 `Task 9.1`；擋的是 `Task 9.3` 第 5 點可完成性。非空殼。

---

## GROK-R17-P2-01

**斷言**: `Task 9.3` 驗收第 5 點仍寫「有 path:line 的 9 列／其餘 20 列」，但 v17 修 `C5-25` 後 register 實測 keyed＝10、無錨＝19，且無錨清單仍含已有錨之 `C5-25`。

**碼證**: `docs/SPLITUNIFY_TODO.md:653-659`（9／20 與清單含 `C5-25`）；`docs/SPLITUNIFY_SPEC.D-002.md:120`（`C5-25` 已含 `ic_feed.py:56-65`／`pipeline.py:406-408`）；探針 `ANCHORED=10` 含 `C5-25`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c

[P2] doc-literal-only。信心度=High。修法：改為「**10** 列 keyed（清單加入 `C5-25`）／**19** 列走 basename 或例外白名單」；殘留文「20 列」同步改 19。可行性：單次字面替換。

---

## GROK-R17-P2-02

**斷言**: `SU-RESID-C5-TARGETS` 觸發條件「basename 判準出現誤判」無機械觀測（無執行者／無命令／無輸出特徵），殘留可永久 `blocked-by` 而不升級 `TARGETS:`。

**碼證**: `docs/SPLITUNIFY_TODO.md:667-668`；repo 內無對應 `scripts/` 或 pytest 節可判定該「誤判」。

**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c

[P2] doc-literal-only。信心度=High。修法＝必答 4b（重掃分類不一致或 basename 不可執行即觸發）。可行性：重用 `Task 9.3` 動工前置重掃，無新治理腳本。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R16-P2-01,GROK-R16-P2-02

ASSUMPTIONS_VERIFIED: body sha `d42b3f14…`；mutation 40 連續；register 29；keyed 10／無錨 19／無檔名 15；`C5-25` seam 56-65 實讀正確；doc_format 雙綠；HANDOFF.md:32 適用 → PROCEED
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `d42b3f14…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；python basename 探針 → 15 no-filename／basename_fail=15；`wc -l ic_feed.py pipeline.py` → 162／807
FAILURES_SEEN: none
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅 append APPROVED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r17-grok.md

STATUS: DONE
