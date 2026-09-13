# Reconcile — 20260911-splitunify-b9-review-r16

**來源** 20260911-splitunify-b9-review-r16-codex.md, 20260911-splitunify-b9-review-r16-composer.md, 20260911-splitunify-b9-review-r16-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 v16 之 keyed 碼證對證在多數列不可執行（三家撞題）**——「Task9.3的keyedreceipt」「v16receipt第5點「逐列keye」「Task9.3v16keyed碼證對證假」 | P1 | CODEX-R16-P1-01, COMPOSER-R16-P2-01, GROK-R16-P2-01 | 採納（🔴 **主委實測確認碼證成立**：以「消費面欄是否含檔名加副檔名再加行號」之樣式機械掃 29 列，**20 列無錨**（`C5-01`..`12`／`15`..`18`／`20`／`22`／`24`／`25`）⇒ v16 之 keyed 對證在 **69% 的列上跑不動**，屬**假閘**。🔴 **處置＝收窄而非補齊**：對有錨的 9 列維持精確 keyed 對證；對其餘列改以「碼證之 basename 須出現在該列消費面文字中」之封閉判準。補齊 20 列 `TARGETS:` 之精確版**降級為具名殘留 `SU-RESID-C5-TARGETS`**，理由類別 `blocked-by`——那要動 20 列已戳記 register 並再走一輪三家重簽，屬「為驗收收據的閘再補一層腳手架」，而 `Task 9.1` 產品實作尚未開始；依 2026-09-12「不再擴建治理工具、同型缺陷降級為具名殘留」裁定。codex 之逐字修法已原樣錄入該殘留，觸發條件為「`Task 9.3` 開工時 basename 判準出現誤判」） |
| **W2 `C5-25` 之施工點與 `M-SU-D2-38` 之破壞點不是同一行碼（兩家撞題）**——「`C5-25`register寫「sur」「`C5-25`寫「`ic_feed`su」 | P2 | COMPOSER-R16-P2-02, GROK-R16-P2-02 | 採納（`C5-25` 消費面原只寫「`ic_feed` survivor **餵入端**」六字、無行號；codex 必答 3a 另指出雜湊 seam 在 `ic_feed.py:56-65`、現行呼叫端在 pipeline 的 406-408 行，兩者不同行。改法：`C5-25` 具名兩處落點，並明定**去重須發生在 seam 內**使任一呼叫端皆受保護、不得只在呼叫端去重。副效果：無錨列由 20 降為 **19**） |

### 本輪裁定
1. **review-r15 之 V1–V5 閉合狀況**：`CODEX-R15-P1-02`／`P1-03`／`P1-04` 由 codex CLOSED；`GROK-R15-P2-01` 由 grok CLOSED；composer 另 CLOSED 六條。**唯一 STILL-OPEN ＝ `CODEX-R15-P1-01`**（即本輪 W1 之前身），已於本輪以收窄＋具名殘留處置。
2. **W1／W2 已修**（SPEC 進 **v17**：`C5-25` 具名落點；TODO 之 `Task 9.3` 驗收第 5 點收窄為兩段式判準並登記 `SU-RESID-C5-TARGETS`）。mutation 條數維持 **40**、ID 01–40 連續、register 維持 **29** 列。
3. **戳記**：v16 之 composer／grok APPROVED 與 codex REJECTED 皆因 body 再變而失效。新 body sha256 為 d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0。

### 🔴 停輪判準之歸類：三家分裂（本節即回報使用者之依據）
r15 已定判準為「若 R16 再出 register 錯配或條數不一致 ⇒ 停輪回報使用者；若只剩 P2 級字面 ⇒ 進 `Task 9.1`」。本輪三家歸類**不一致**：
- **codex**：判「屬 register 錯配／落點不足，不是 P2 級字面」⇒ **停輪並回報使用者，不可進 `Task 9.1`**。
- **composer**：判「屬 P2 級字面——非 mutation 欄錯配、非條數不一致」⇒ **進 `Task 9.1`**，P2 於 `Task 9.3` 驗收補洞。
- **grok**：同 composer，逐字「不是 register 錯配（mutation 欄 ID 指錯）也不是條數不一致」⇒ **進 `Task 9.1`**。

**主委處置（不自行裁定，交使用者）**：依「看碼證不數人頭」，三家對**事實**無分歧——20 列無錨為實測確認；分歧只在 r15 那句判準裡「register 錯配」四字是否涵蓋「落點欄不足以支撐新閘」。codex 取廣義、另兩家取狹義（僅指 mutation 欄 ID 指錯）。🔴 **判準本身的語意由誰定不在委員權限內，且 r15 判準之停輪分支明文是「回報使用者」** ⇒ 本輪**照該分支執行：回報使用者**，同時把不受分歧影響的修補（W1 收窄、W2 具名）先落地，使任一裁定方向都不必回頭重做。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R16-P1-01
**斷言**: Task 9.3 的 keyed receipt 對證不可執行：D-002-C5 多數列沒有可解析的 repo-relative `path:line`，C5-25 更只有「ic_feed survivor 餵入端」，因此不能決定 receipt 的路徑是否與同列 register 相同。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:652
MUTATION: 構造合法 TASK/COMMIT 與 C5-01..29 receipt，將 C5-25（或任一無 target 的列）碼證替換成任意真實 `path:line`，執行 TODO:652-656 keyed 對證；該列沒有可比對的 register RHS。
**來源摘要**: docs/SPLITUNIFY_TODO.md#33911fd6b944
[MAJOR] 信心度=High；無完整 file:line 的列為 C5-01/02/03/04/05/06/07/08/10/11/12/15/16/17/18/20/22/24/25；只有 basename/module token 的列為 C5-09/13/14/19/21/23/26/27/29；C5-13/27 雖有多個範圍但仍是同一未限定 basename 檔，沒有明列多檔集合。最小修補：在每列消費面末尾補 `TARGETS: <repo-relative-path>:<start>-<end>[; <repo-relative-path>:<start>-<end>...]`，receipt 僅在 path 精確命中同列 TARGETS 且行號落在範圍內通過；C5-25 至少錨 `momentum/Analysis/event_samples/ic_feed.py:56-65`。不要放寬成任意檔案存在即可。
### 必答
(1a) `CODEX-R15-P1-01` STILL-OPEN；`CODEX-R15-P1-02`、`CODEX-R15-P1-03`、`CODEX-R15-P1-04` CLOSED；同型 `COMPOSER-R15-P2-01` 亦仍受同一 register 落點缺口影響。
(1b) `rg -n 'M-SU-D2-(38|39|40)' docs/SPLITUNIFY_SPEC.D-002.md` 取得 v16 三條修補；hash probe `event_context_from_windows([w])` 對 `[w,w]` 輸出 `same=False` rc=0；pandas probe 輸出 `ValueError: cannot reindex on an axis with duplicate labels`；`pytest -q` 三檔輸出 `93 passed`。
(2a) 逐列 scan 明確列出上述 19 個無完整 target、9 個 basename/module-only；沒有一列明確寫出多檔集合，C5-13/27 是同檔多範圍而非多檔。
(2b) 最小字面為：`每列消費面末尾必有 TARGETS: <repo-relative-path>:<start>-<end>[; ...]；receipt path 必須精確命中同列 TARGETS 且 line 落範圍；禁止 module-only 或裸 :line`；多落點才用明列集合，不採任意檔集合放寬。
(3a) 不是同一個可驗證落點：C5-25 未寫行；現有 caller 是 `momentum/Analysis/event_samples/pipeline.py:406-408`，hash rows/seam 是 `momentum/Analysis/event_samples/ic_feed.py:56-65`。
(3b) 既然 v16 測試直接呼叫函式，正確 seam 應固定為 `ic_feed.py:56-65`，並把 C5-25 改成該 TARGET；若要 caller 去重則改寫 M38 與測試一併固定 `pipeline.py:406-408`，不可兩者混用。
(4a) 有三個既有相關測試不會因新破壞而紅：`test_conditional_ic_feed_emits_event_context`（只驗 hash 形狀）、`test_insufficient_events_in_test_is_per_symbol_not_batch`（無 1 event×2 TF fixture）、`test_discrimination_oos_only_and_kind_strata`（assignments index 唯一）；這不否定 v16 要新增的具名 mutation tests。
(4b) `nl -ba tests/momentum/event_samples/test_gap3_conditional_ic.py | sed -n '104,109p'`、`.../test_splitunify_derive.py | sed -n '1153,1162p'`、`.../test_tables.py | sed -n '106,121p'`；三段皆無重複 TF/duplicate symbol fixture；named test sweep 對 M38/M39/M40 新測試輸出 `missing`。
(5a) 本輪 finding 明確屬「register 錯配／落點不足」，不是 P2 級字面問題；mutation 條數實查為 40、C5 register 為 29。
(5b) 依 r15 停輪判準，本票停輪並回報使用者；不可進 `Task 9.1`。
(6a) body sha256 `8607f2b770fb39f967c7c75686a90f4c1bc39a7d1536cc70bca1909e838021a0` 判 `REJECTED`。
(6b) 唯一阻擋項 `CODEX-R16-P1-01`：一次修訂補齊每列 repo-relative TARGETS、C5-25 的 ic_feed seam，並讓 keyed checker 對 path＋line range；修補後可關閉。
ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`→8607…021a rc=0；兩份 doc_format_precheck rc=0；mutation=40、register=29；direct probes 與 93-test targeted run 如上。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/event_samples/test_tables.py tests/momentum/Analysis/test_splitunify_derive.py`→93 passed rc=0；`pytest --collect-only`→93 collected rc=0；hash probe rc=0；pandas probe預期 rc=1。
FAILURES_SEEN: pandas probe 的 rc=1 是預期 duplicate-index `ValueError`，非未解決測試失敗；無其他未解決失敗。
SCOPE_CHANGES: 新增本交件；僅在 SPEC `## 戳記` append codex REJECTED stamp；未改碼、SPEC 正文、TODO、HANDOFF.md、data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更；僅拒絕 v16 文件簽核。
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r16-codex.md`。
VERDICT: blocked
BLOCKED-BY: CODEX-R16-P1-01
CLOSED: CODEX-R15-P1-02,CODEX-R15-P1-03,CODEX-R15-P1-04
STATUS: DONE
## COMPOSER-R16-P2-01

**斷言**: v16 receipt 第 5 點「逐列 keyed 對證 register 落點檔」對 **20/29** register 列**無法執行**，該子集仍只剩「檔存在＋行號合法」，同-line 假完成風險未全關。

**碼證**: `scratchpad/r16-composer/keyed_class.tsv`（`NO_PATHLINE` 10 列＋`REL_LINE_ONLY` 6 列＋無行號 4 列）；`docs/SPLITUNIFY_TODO.md:652-655`；R15 探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt` 對 `C5-29` 在 keyed 下檔路徑不符，對 `C5-01`／`C5-25` keyed 字面不可判。

**來源摘要**: docs/SPLITUNIFY_TODO.md#8607f2b770fb

[P2] doc-literal-only。修法：見必答 2b（Task 9.3 驗收第 6 點 fallback ＋ 優先補 `C5-25` 等待補列之 `path:line`）。可行性：`awk` 分類已實跑。信心度=High。不阻 v16 戳記與 `Task 9.1`。

---

## COMPOSER-R16-P2-02

**斷言**: `C5-25` register 寫「survivor **餵入端**」而 `M-SU-D2-38` v16 鎖定 `event_context_from_windows` 函式體（`ic_feed.py:56-65`），施工點（`pipeline.py:406` caller 去重）與 mutation／測試 seam **可能落在不同行**，實作者依 register 在 caller 去重時直接測函式仍可能漏紅。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:120`（`C5-25` 無行號）vs `:315`（M-38 seam）；`momentum/Analysis/event_samples/pipeline.py:406` 未去重；`ic_feed.py:56-59` 組 `rows` 不去重。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#8607f2b770fb

[P2] doc-literal-only。修法：見必答 3b。可行性：實讀三處碼。信心度=High。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R15-P2-01,CODEX-R15-P1-01,CODEX-R15-P1-02,CODEX-R15-P1-03,CODEX-R15-P1-04,GROK-R15-P2-01

ASSUMPTIONS_VERIFIED: body sha256 8607f2b7…；40/40／29 register；hash_probe drift=True；pandas ValueError；keyed 20/29 不可執行；C5-25≠M-38 同行  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`；`bash scripts/doc_format_precheck.sh`（兩檔 rc=0）；`scratchpad/r16-composer/verify_r16.sh`（部分）；`hash_probe.py`；`pandas_probe.py`；`rg` 具名測試掃描  
FAILURES_SEEN: verify_r16.sh 初跑 hash_probe 缺 PYTHONPATH（已以 `PYTHONPATH=.` 重跑通過）  
SCOPE_CHANGES: none（`docs/SPLITUNIFY_SPEC.D-002.md` 戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）

STATUS: DONE
## GROK-R16-P2-01

**斷言**: Task 9.3 v16 keyed 碼證對證假設「register 同列已載落點檔」，但 `C5-01`／`02`／`03`／`04`–`12`／`17`／`20`／`22`／`24`／`25` 等共 17 列第 2 欄無 repo-relative 檔路徑（或僅模組名），機械「path 相同」對證對這些列無定義或必靠未成文的模組 map。

**碼證**: 分類探針（本輪）：`NO_PATH_TOKEN`＝C5-01,02,22；`MODULE_ONLY_NO_LINE`＝C5-03,07,10,11,12,17,20,25；`MODULE_PLUS_LINE_NO_REPO_PATH`＝C5-04,05,06,08,09,24。閘字面 `docs/SPLITUNIFY_TODO.md:652-656`。對照：具檔／模組 token 之 23 列上，全填 `docs/SPLITUNIFY_SPEC.D-002.md:1` 會被 keyed 殺掉（原 GROK-R15-P2-01 構造已閉）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#33911fd6b944

[MAJOR] 信心度=High。doc-literal-only（閘前提）。修法＝必答 (2b)「檔集合包含＋固定 map＋空集回退消費面測試路徑」。可行性：map 對 `event_samples/<mod>.py` 九個消費模組已唯一；空集列僅三個契約名。不擋 Task 9.1；擋的是 Task 9.3 receipt 語意驗收之可執行性。非空殼。

---

## GROK-R16-P2-02

**斷言**: `C5-25` 寫「`ic_feed` survivor 餵入端」去重，而 `M-SU-D2-38`／Task 9.3 要求直接呼叫 `event_context_from_windows` 驗不變性——若實作只在 `pipeline.py:407` caller 去重，則破壞點（函式內 `rows`）與施工點不是同一行，具名測試與 register 語意分裂。

**碼證**: `momentum/Analysis/event_samples/ic_feed.py:56-65` 現無去重、重複輸入雜湊漂移（實跑 DRIFT=True）；caller `momentum/Analysis/event_samples/pipeline.py:406-408` 直接傳 `prepared.windows`。register `C5-25` 落點仍無 `path:line`（`docs/SPLITUNIFY_SPEC.D-002.md` register 列）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#8607f2b770fb

[MAJOR] 信心度=High。修法＝必答 (3b)（釘死函式入口去重、禁只改 caller）。可行性：單函式入口一處 `drop_duplicates`／dict 保序即可同時滿足直接呼叫測試與 caller 路徑。不擋 Task 9.1；屬 Task 9.3 施工說明。非空殼。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R15-P2-01

ASSUMPTIONS_VERIFIED: body sha `8607f2b7…`；mutation 40 連續；register 29；doc_format 雙綠；M-38 hash DRIFT；tables.py:372 raw reindex；Task 9.3 keyed／Task 9.4 計數字面落地；keyed 不足 17 列分類；同 doc 錨對有 token 列可殺；具名應紅 def＝NONE
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `8607f2b7…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；`event_context_from_windows` unique/dup hash probe → DRIFT=True；register 落點分類探針 → 17 insuff；`grep -rn 'def test_tier_min_test_events_counts_unique_event_ids' tests/` → NONE
FAILURES_SEEN: hash probe 初缺 `horizon_bars` → KeyError，補 LD 後通過
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅 append APPROVED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r16-grok.md

STATUS: DONE
