# Reconcile — 20260911-splitunify-b9-review-r15

**來源** 20260911-splitunify-b9-review-r15-codex.md, 20260911-splitunify-b9-review-r15-composer.md, 20260911-splitunify-b9-review-r15-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **V1 `M-SU-D2-38` 之被測輸入不可達（主委 v15 空殼）**——「`M-SU-D2-38`所稱「多TFsu」 | P1 | CODEX-R15-P1-02 | 採納（🔴 **主委實讀確認**：`ic_feed.py:109` 以 `per_tf["timeframe"] == timeframe` **單一 TF 過濾**，且 `event_context_from_windows` 只吃事件級 `WindowRow`（`event_id`／`label_start_ms`／`label_end_ms`）⇒ v15 寫的「多 TF 下重複三元組」**不可達**。改寫為可達 seam ＝ `event_context_from_windows` **本身**：餵入含重複 `event_id` 之 windows ⇒ `event_manifest_hash` 漂移；具名測試改為**直接呼叫**該函式驗雜湊不變性） |
| **V2 `M-SU-D2-40` 之破壞描述與 pandas 實際行為不符（主委 v15 空殼）**——「`M-SU-D2-40`把raw`set」 | P1 | CODEX-R15-P1-04 | 採納（🔴 **主委實跑 pandas 確認**：重複索引之 `reindex` 直接 `ValueError: cannot reindex on an axis with duplicate labels`，**不是**「靜默取錯 symbol」⇒ v15 描述之破壞不可執行。改為「移除 `tables.py:372` 之顯式去重 reducer」，並要求**成對**測試：①同 `event_id` 之 `symbol` 相同 ⇒ 去重後成功且取到正確值（移除 reducer 即 `ValueError` 轉紅）②`symbol` 衝突 ⇒ fail-closed raise） |
| **V3 `M-SU-D2-39` 只有門檻斷言，計數面無鑑別力**——「`M-SU-D2-39`同時宣稱保護`p」 | P1 | CODEX-R15-P1-03 | 採納（只把 `per_symbol_n` 弄錯而保持門檻去重時，唯一具名測試仍綠 ⇒ 該 mutation 等於半條。改法：同一具名測試**另**斷言 `summary["per_symbol_n"]` 與 `summary["per_symbol_test_n"]` 皆等於各自之 `event_id` 去重計數） |
| **V4 receipt 閘之碼證檢查只驗「存在」，全填同一真實行仍全過（兩家撞題）**——「Task9.3receipt閘仍可用正確」「`Task9.3`receipt閘v15」 | P1 | CODEX-R15-P1-01, COMPOSER-R15-P2-01 | 採納（v15 加的「路徑須存在」被「每列都填同一個真實存在的檔的第 1 行」繞過。改為**逐列 keyed 對證**：第 `C5-NN` 列之碼證檔路徑須與 SPEC register 同一 `C5-NN` 列所載之落點檔相同，行號須落在該列所列範圍內。不需新資料——register 本來就逐列寫了落點） |
| **V5 receipt 閘之殘餘語義面（grok）**——「Task9.3register-resc」 | P2 | GROK-R15-P2-01 | 採納（與 V4 同族之下一層；grok 判「閘收緊維仍可能再 0–1 輪」，其具體殘留併入 V4 之 keyed 對證一併處置） |

### 本輪裁定
1. **review-r14 之 U1–U3 全數由原提出方 CLOSED**（codex 三條、composer 兩條、grok 四條）。
2. **V1–V5 已修**（SPEC 進 **v16**：`M-SU-D2-38`／`40` 改寫為可達／正確反例、`M-SU-D2-39` 補計數值斷言；TODO 同步 `Task 9.3` 之 keyed 碼證對證與該表 `tables`／`ic_feed` 兩列、`Task 9.4` 之計數斷言）。條數維持 **40**。
3. 🔴 **本輪最重要的事實**：四條 P1 **全部打在主委 v15 自己新增的 mutation 上，其中兩條是空殼**（被測輸入不可達／破壞描述與實際行為不符）。這與本檔一路在打的「指向不存在的落點」是**同一型**，只是這次犯在 mutation 欄。⇒ 日後新增 mutation **必須先驗可執行性**（實讀該 seam 或實跑一次），不得只憑描述。
4. **戳記**：v15 之 composer／grok APPROVED 與 codex REJECTED 皆因 body 再變而失效。新 body sha256 為 8607f2b770fb39f967c7c75686a90f4c1bc39a7d1536cc70bca1909e838021a0。
5. **仍不可領 impl token**；最小閉合集合＝V1–V5 修補（已完成）＋ 新 body 之三家 APPROVED 且 `reconcile_stamps_check` rc=0。

### 收斂判斷（三家對主委必答 6 之加問）
- **composer**：**已進入窮舉遞減報酬**。停輪判準——若 R16 再出「register 錯配」或「條數不一致」⇒ 判未收斂並停輪；若僅 P2 級 receipt 字面 ⇒ 允許進 impl 並在 `Task 9.3` 驗收補洞。
- **grok**：以「同缺陷類在**已宣告窮舉子空間**的復發次數」計——register×mutation **對應**類在 R14 窮舉後本輪 **0 復發**；**閘偏鬆**類本輪 1 條殘餘。⇒ 對應維已入遞減報酬；閘收緊維仍可能再 0–1 輪，但不得再把「對應錯配」當未窮舉重跑整表。
- **codex**：未直接答收斂，但其四條全屬「新增物之品質」而非「存量未窮舉」，與上兩家判斷一致。
- **主委採**：兩家給的停輪判準**一致且可機械套用**，逐字採 composer 版 ⇒ **R16 若出現 register 錯配或條數不一致即停輪並回報使用者；若只剩 P2 級字面則進 impl、於 `Task 9.3` 驗收補洞**。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R15-P1-01
**斷言**: Task 9.3 receipt 閘仍可用正確 `甲/乙/丙` 分類＋每列同一個真實 `docs/SPLITUNIFY_SPEC.D-002.md:1` 繞過；現行新增 path 檢查只驗存在與行數，不驗 C5 對應。
**碼證**: CODE-ANCHOR: scripts/completeness_check.sh:350
MUTATION: 構造 exact C5-01..29、分類全依現況填寫、所有碼證填 `docs/SPLITUNIFY_SPEC.D-002.md:1`、`COMMIT: deadbeef`，執行 TODO:642-651 的 exact-set／row-format／path 檢查；輸出前三者皆 PASS。
**來源摘要**: docs/SPLITUNIFY_TODO.md#23f19deb2784；[MAJOR] 信心度=High。修法：逐列以 C5-NN keyed 對證 register 之 target path:line（允許該列列出的行範圍），不得只驗檔案存在；並以 audit round-start HEAD 對證 COMMIT。可行性：register 已有逐列 path:line，現有 shell/awk 檢查可加入 keyed diff。
## CODEX-R15-P1-02
**斷言**: `M-SU-D2-38` 所稱「多 TF survivor 餵入端未去重」沒有可達的被測輸入：`build_event_ic_inputs` 先按單一 `timeframe` 過濾，分析時 `WindowRow` 也只有事件級資料。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/ic_feed.py:109
MUTATION: 將 receipts.per_tf 放入同一 event 的 1h／4h 兩列並執行 `build_event_ic_inputs(..., timeframe="1h")`；line 109 先只留下 1h，無法形成該 mutation 描述的多 TF survivor 三元組。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#c342d27bdf04；[MAJOR] 信心度=High。修法：把 M38 改成可達的同 TF 重複輸入 invariant，或明確指定多 TF rows 如何進入 survivor hash 並讓具名測試走該 seam；可行性：`ic_feed.py:43-65` 的 hash 輸入與 `:77-109` 的單 TF 餵入落點都已存在。
## CODEX-R15-P1-03
**斷言**: `M-SU-D2-39` 同時宣稱保護 `per_symbol_n`、`per_symbol_test_n` 與 threshold，但唯一具名測試只寫 threshold；只讓 `per_symbol_n` 錯而保持 threshold 去重時，測試仍會綠。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:716
MUTATION: 保留 `per_symbol_n` 對 composite-key rows 的 `value_counts()`、只修 `per_symbol_test_n`，執行 `test_tier_min_test_events_counts_unique_event_ids`；1 event×2 TF 仍判不足，故該 mutant 不轉紅而 summary 計數可錯。
**來源摘要**: docs/SPLITUNIFY_TODO.md#23f19deb2784；[MAJOR] 信心度=High。修法：在同一具名測試另斷言 `summary["per_symbol_n"]` 等於 unique event_id，或把 per-symbol summary 與 threshold 拆成各自 mutation/test。可行性：`split_projection.py:559-569` 已有 summary 計數落點，新增值斷言不需改 API。
## CODEX-R15-P1-04
**斷言**: `M-SU-D2-40` 把 raw `set_index("event_id").reindex(idx)` 描述成「靜默取錯 symbol」，但 pandas 對 duplicate index 會先明確 `ValueError`，因此目前 mutation 不是所述可執行反例。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 以 `venv/bin/python -c 'import pandas as pd; s=pd.Series(["BTC","ETH"], index=["e1","e1"]); print(s.reindex(pd.Index(["e1"])))'` 重現；stdout/stderr 為 `ValueError: cannot reindex on an axis with duplicate labels`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#c342d27bdf04；[MAJOR] 信心度=High。修法：明定正向 same-symbol duplicate 應去重後成功，另以 conflicting-symbol duplicate 驗 fail-closed；M40 反向移除 explicit reducer 時前者才會轉紅。可行性：line 372 已是單一可變異 seam，pandas probe 已證明 raw path 的實際結果。
(1a)(1b) R14 `CODEX-R14-P1-01`、`P1-02`、`P1-03` 均 closed：`rg` 取得 M35/M36 欄位 ASSERT＋軟包禁令＋多 TF＋兩種破壞；receipt probe=`EXACT_ID_SET=PASS ROW_FORMAT=PASS PATH_EXISTENCE=PASS`，新增內容對證會拒全甲且文字綁 audit HEAD；register grep 取得 C5-24→M05/M37、25→M38、27→M39、28=blocked-by、29→M40。R14 `P2-04` 的「保留原指標、另報加強字面數」可接受，仍不視為指標健康證明。(2a)(2b) 檔案逐條對照：M01/M02/M03→derive/disclosure present；M04→feature_materialization；M05/M37→pattern_bridge；M06/M40→tables；M07/M19/M38→gap3_conditional_ic；M08→counterexample；M09→candidate；M10→dedupe；M11→`frontend/src/app/search/eventExportByEventId.test.tsx` ABSENT；M12/M13/M14/M15/M18/M20/M21/M22/M23/M24/M25/M26/M30/M35/M36→derive/wiring present；M16/M17/M27/M28/M29/M33/M34→golden/script present；M31/M32/M39→baseline/derive present。collect-only→196 collected，future nodes（含 M35–40）皆未收集；Task 尚未開工故可接受，完工前不得宣稱 closed。
(3a)(3b) 仍可繞過「分類照抄 register＋全部真實同一行」；最小字面＝每列碼證須等於該 C5-NN register target 的 path:line 之一（keyed 對證），不得只驗存在／行數，並保留 COMMIT＝audit round-start HEAD。M38/M40 另為本輪 P1。(4a)(4b) R14-P2-04 處置可接受；量測中只有主委依使用者／治理 SSOT 於量測結束後改判並重開量測才有權改。
(5a)(5b) body `c674086e…` 判 REJECTED；一次修訂 blockers＝CODEX-R15-P1-01..04，各可由 keyed receipt／可達 mutation／完整計數 assertion／正確 pandas 反例一次關閉。(6a)(6b) 不可領 impl token；須先關四條 P1、三家對同一 body APPROVED stamp，且 `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0。r13/r14 同類仍有新 blocker，判「仍在收斂」；連續兩輪零新 P0/P1 且無新可達性／mutation 缺口才算遞減報酬。§1：矛盾/漏項/不可測/測試＝上述；quant/OOM/cache/API/必要性＝無新 finding；agent 可執行性＝M38/M39/M40。
ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`→`c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0`；counts mutation=40、§C-9=40、register=29、literal=1；兩檔 `doc_format_precheck` 皆 rc=0；`grep -rn '\.run(' api --include='*.py'` 無 canonical pipeline run。TESTS_RUN: collect-only 12 檔→196 collected rc=0；receipt textual probe→exact/row/path PASS；pandas duplicate reindex→ValueError。FAILURES_SEEN: 首次內嵌換行 probe SyntaxError，單行重跑已取得結果。
SCOPE_CHANGES: 僅新增本交件與 SPEC `## 戳記` 之 codex REJECTED 行；未改碼、SPEC 正文、TODO、HANDOFF.md、data_cache。NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更。HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r15-codex.md`。
VERDICT: blocked
BLOCKED-BY: CODEX-R15-P1-01,CODEX-R15-P1-02,CODEX-R15-P1-03,CODEX-R15-P1-04
CLOSED: CODEX-R14-P1-01,CODEX-R14-P1-02,CODEX-R14-P1-03
STATUS: DONE
## COMPOSER-R15-P2-01

**斷言**: `Task 9.3` receipt 閘 v15 第 4 點之「碼證須指向真實行」仍允許 29 列全部填同一 `docs/SPLITUNIFY_SPEC.D-002.md:<n>`，在改前分類照抄 SPEC 第三欄時可假完成重掃。

**碼證**: `docs/SPLITUNIFY_TODO.md:647-651`（僅驗檔存在與行號範圍）；探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt` → `diff` ID set rc=0、29 行同碼證仍過機械閘。

**來源摘要**: docs/SPLITUNIFY_TODO.md#c674086e5f66

[P2] doc-literal-only。修法：見必答 3b 第 5 點（path 須為源碼樹＋去重計數下限）；可行性＝shell 迴圈。信心度=High。不阻 v15 戳記與 `Task 9.1` 開工。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R14-P2-01,COMPOSER-R14-P2-02

ASSUMPTIONS_VERIFIED: body sha256 c674086e…；40/40 mutation；29 register；五列 register 複驗；receipt 同-line bypass PASS；M-37/38/40 測試缺失為 Task 9.3 預期狀態  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`；grep/awk 計數與五列複驗；receipt 探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt`；`rg` 具名測試存在性掃描  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；v15 body 已由 0de1a17f 引入）

STATUS: DONE
## GROK-R15-P2-01

**斷言**: Task 9.3 register-rescan receipt 在 v15 加「改前分類＝SPEC 第三欄」與「path:line 須存在」後，仍可用「逐列照抄 SPEC 分類＋全列碼證指向同一真實存在行（例如 `docs/SPLITUNIFY_SPEC.D-002.md:1`）」通過檔案級內容閘，而無需真實重掃各消費面。

**碼證**: 實跑構造 `/tmp/grok-r15-work/bypass-same-anchor.txt`：29 列 `C5-NN <SPEC第三欄> -> <同值> docs/SPLITUNIFY_SPEC.D-002.md:1` → ID set 與 SPEC register `diff` rc=0；改前分類對證 0 fail；path 存在且 line≤檔長 0 fail；`distinct anchors=1`。對照同檔改 `nowhere:0` → 29 fail（證存在性閘有效）。閘字面落點 `docs/SPLITUNIFY_TODO.md:647-651`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#23f19deb2784

[MAJOR] 信心度=High。修法＝必答 (3b) 最小字面（碼證 path 須落在該 C5 第 2 欄具名檔；禁 `docs/`／`handoffs/`；distinct path 下限）。可行性：register 第 2 欄已具名消費路徑（如 `pattern_bridge`／`tables.py:372`），機械比對只需從該欄抽 path token，無需新架構。不阻擋 Task 9.1；阻擋的是 Task 9.3「重掃已做」之語意驗收。非空殼。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R14-P1-01,GROK-R14-P1-02,GROK-R14-P2-03,GROK-R14-P2-04

ASSUMPTIONS_VERIFIED: body sha `c674086e…`；mutation 40 連續；§C-9 認領 40；register 29；doc_format 雙綠；C5-24..29／M-35..40 字面落地；M-35 欄位存在斷言探針；receipt 照抄＋同錨 bypass 與 nowhere:0 對照；具名測試 def 探針；SU-RESID-9A-UI recheck 字面存在
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `c674086e…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；receipt sim bypass／nowhere 對照；`grep -rn 'def test_assignments_composite_key_unique' tests/` → NONE（及 M-36／M-39 同）；pandas 欄位存在斷言探針
FAILURES_SEEN: none
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅 append APPROVED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r15-grok.md

STATUS: DONE
