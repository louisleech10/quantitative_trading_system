# Reconcile — 20260911-splitunify-b9-stamp-r1

**來源** 20260911-splitunify-b9-stamp-r1-codex.md, 20260911-splitunify-b9-stamp-r1-composer.md, 20260911-splitunify-b9-stamp-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **S1 SPEC 戳記三家 APPROVED**——「本輪對stamp-targetbody（」 | P3 | COMPOSER-R1-P3-00 | 採納（三家皆對 body sha256 06b2d4cb… 以 task 20260911-SPLITUNIFY-B9-STAMP-R1 append APPROVED 戳記行；主委補 provenance 後 `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` **PASS**——十三輪來第一次） |
| **S2 前端型別錨點指錯介面（兩家撞題；主委實錯）**——「Task9.4的兩個TS行號且其語意落點」「`docs/SPLITUNIFY_TOD」 | P1 | CODEX-R1-P1-03, GROK-R1-P2-01 | 採納（主委複驗成立：`types.ts:1582` 屬 `CPCVPathResult`、`:2257` 屬 `MarginalICSection`，兩者與事件批無關；事件批之 `EventAnalyzeResponse` 的 `summary` 是 `Record<string, unknown>`、**無欄位可改**。根因＝我 `grep n_train` 後未讀上下文就當落點，正是「實測 > 假設」同型。改法：刪除兩個錯錨，改寫為「事件路徑現無 typed `n_train` 欄；若 `Task 9.4` 需要 typed 面須另新增事件摘要型別並在該 Task 具名」；`EventTablesPanel.tsx:361` 與六支 vitest 為真消費點、保留） |
| **S3 mutation ID 以裸數字縮寫，機械覆蓋不可證**——「§C-9的34條mutation只有25」 | P1 | CODEX-R1-P1-02 | 採納（`M-SU-D2-14`／`15`／`22` 這種寫法使完整 ID 的機械 extractor 只抽到 25 個 token；語意上無落單，但「機械可證」是本專案對 mutation 網的既有要求。改法：§C-9 內 9 處縮寫補成完整 ID，改後機械 union=34） |
| **S4 xfail node id 與 register 重掃 receipt 未寫成機械驗收項**——「C9未把stagedstrict-xfa」 | P1 | CODEX-R1-P1-04 | 採納（現列命令只到檔案級 rc=0，刪掉 `xfail` 測試或省略重掃都不會紅。改法：①`Task 9.2a` 明列該 xfail 之測試 node id；②`Task 9.3` 指定 receipt 路徑 `handoffs/run_receipts/<UTC時戳>-splitunify-task-9.3-register-rescan.txt` 並列入驗收） |
| **S5 ORCH 活文仍以兩家族規定大型 adversarial**——「ORCH活文仍以兩家族規定大型adver」 | P1 | CODEX-R1-P1-01 | 採納（主委本輪已改 CLAUDE.md 決策表、ORCH 的 :41 與 :195 三處，但 grep 只掃「雙家族」而**漏掉字面為「兩家族」的 ORCH:194** ⇒ 自證用的排除條件再次濾掉待抓目標，與 HANDOFF 坑欄同型。改法：ORCH:194 改為指向 §1 現行分工行，並以**不含排除條件**的 grep 自證完備） |

### 本輪裁定
1. **SPEC 戳記已閉**：`docs/SPLITUNIFY_SPEC.D-002.md`（body sha256 `06b2d4cb…`）三家 APPROVED、`reconcile_stamps_check` rc=0。
2. **TODO §C-9 需修四條（S2–S5）後才算可用**；codex `VERDICT: blocked` 即擋在此，非擋 SPEC。
3. 修完派 **`20260911-splitunify-b9-review-r13`** 三家覆審（同時是 DOCROT 成效量測之第一輪）。
4. 🔴 **具名殘留（`blocked-by`）**：`docs/` 底下其他帶 `RECONCILE-STAMP` 的檔（`GAP3_EVENT_UX_SPEC.D-001.md`、`GAP3_EVENT_UX_TODO.D-001`..`D-006`）之 `reconcile_stamps_check` 同樣結構上為紅——`gate.sh register-output` 原只收 `handoffs/`，provenance 需要指向被戳記檔自身的事件。本輪只把 `docs/SPLITUNIFY_SPEC.D-002.md` 加進既有封閉白名單 `scripts/stampable_artifacts.txt`；**其餘未一併加入**，因為那些檔的戳記是否對應現行 body hash 未經查證，盲加會把未驗證的背書寫成既成事實。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: ORCH 活文仍以兩家族規定大型 adversarial，與 §1 三家現行分工衝突。
**碼證**: CODE-ANCHOR: docs/MULTI_AGENT_ORCHESTRATION.md:193-194
MUTATION: 以此兩行作大型任務派工依據會漏派 Grok，quorum 與流程規定不一致。
**來源摘要**: docs/MULTI_AGENT_ORCHESTRATION.md#e7239f8a774b (sha256)
正文：Q(1a) SPEC 語意可 APPROVED；Q(1b) 最可能的 Task9.1 red 是返回形狀與 pipeline.py caller 的契約，應改 code 不改 SPEC。應改為指向 §1 現行分工行。Q(2a/2b)：9.3∥9.4 可合併成一個 review gate（5 gates），在 B9D/E 以 shared test_splitunify_derive.py 的 rebase/驗收觀測發現分拆無益；Q(6a)：待本輪文件缺口修正且三家 stamp rc=0 才可動 9.1。
## CODEX-R1-P1-02
**斷言**: §C-9 的 34 條 mutation 只有 25 個完整 token，9 個以裸數字縮寫，機械覆蓋不可證。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:581
MUTATION: 對 §C-9 執行 `M-SU-D2-\d{2}` extractor 得 FULL_ID_COUNT=25、缺 15/17/22/24/28/29/30/33/34。
**來源摘要**: docs/SPLITUNIFY_TODO.md#94c6aa2eb64c (sha256)
正文：9 個語意上分屬 9.2b（15/22/24/30）及 9.5（17/28/29/33/34），故 4a 無語意落單、4b 只需把縮寫補成完整 ID；修後機械 union=34。
## CODEX-R1-P1-03
**斷言**: Task 9.4 的兩個 TS 行號且其語意落點錯誤，會漏掉事件摘要的型別面。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:636-640
MUTATION: 只改 frontend/src/lib/types.ts:1582/2257；實際為 CPCVPathResult/MarginalICResult，EventAnalyzeResponse.summary 仍是 Record<string, unknown>。
**來源摘要**: frontend/src/lib/types.ts#e283b4ebba1c (sha256)
正文：實跑行號為 n_train/n_test 在 :1582–1583、:2257–2258，兩處均非事件批型別；正確落點應明列 EventAnalyzeResponse.summary（:3175）或新增事件摘要型別。六支既有前端測試行號均實存且吻合；9.3 新測試檔則目前缺檔但 TODO 已明示須新建。
## CODEX-R1-P1-04
**斷言**: C9 未把 staged strict-xfail 及 9.3 register rescan 的可稽核輸出／node id 寫成機械驗收項。
**碼證**: CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:590-616
MUTATION: 刪除 9.2a xfail 測試或省略 register rescan receipt；現列命令仍可由既有檔案級 rc=0 取得，無法證明兩項要求。
**來源摘要**: docs/SPLITUNIFY_TODO.md#94c6aa2eb64c (sha256)
正文：5a 接受 strict=True；現行 split_projection.py:530-553 仍逐 cutoff 判側且無異側 AlignmentViolationError，fixture 修正後仍不會意外 XPASS。5b 應將 xfail test node 明列於 9.2a，並為 9.3 指定 receipt path（如 handoffs/run_receipts/...-task-9.3-register-rescan.txt）。3a 未有專名承接的 ASSERT 是 G-4d②/③、G-4e 三者全等；3b 的 clusters remain event-level、purged/assignments disjoint、composite-key error message 應補 §V，xfail bridge/legacy duplicate guard 可留 TODO 細節。6b 已查 current blocks、paths/anchors、87 passed、mutation 25/34、active family grep。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04
CLOSED: 2026-09-13
## COMPOSER-R1-P3-00

**斷言**: 本輪對 stamp-target body（sha256 `06b2d4cb…`）與 §B `B9A`–`B9F`＋§C-9 Task 9.1–9.5 逐項核對後無需阻擋收斂之 finding；六批切法、xfail 處置、mutation 認領與 §V  defer 邊界均可接受。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77` rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 87 passed rc=0；34/34 mutation 機械認領（`M-SU-D2-03` defer）；12/12 §C-9 pytest 路徑存在；前端六測試 basename 於 `frontend/src/components/ic-analysis/` 行號 27/30/28/29/24/14 仍命中。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b；docs/SPLITUNIFY_TODO.md#bcf6e35a

[P3] 信心度=High。本輪 `brief-kind: closure`／stamp 補簽。

---

## GROK-R1-P2-01

**斷言**: `docs/SPLITUNIFY_TODO.md` Task 9.4 將前端型別修改錨在 `frontend/src/lib/types.ts:1582` 與 `:2257`，但該兩行分屬 `CPCVPathResult.n_train`／`MarginalICSection.n_train`，與事件批 `EventAnalyzeResponse.summary: Record<string, unknown>`（`types.ts:3176`）無關；依原文改碼會動到錯誤介面。

**碼證**: `sed -n '1578,1584p;2239,2258p;3174,3177p' frontend/src/lib/types.ts` → 1582∈`CPCVPathResult`、2257∈`MarginalICSection`、3176=`summary: Record<string, unknown>`；`EventTablesPanel.tsx:361` 仍正確讀 `s.n_train`／`s.n_test`／`s.n_purged`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#94c6aa2eb64c

修法（非本輪執行）：Task 9.4「修改檔案」之 `types.ts` 兩錨改為 (a) 刪除（因 summary 為 `Record` 無欄位可改）或 (b) 具名到真實事件 summary／baseline 消費型別（若後續新增）；**不得**改 CPCV／MarginalIC。可行性：事件路徑現無 typed `n_train` 欄，刪錯錨不會丟交付面；`EventTablesPanel.tsx:361` 與六支 vitest 仍為真消費點。本條不擋 Task 9.1；須在 `B9E`／Task 9.4 動工前關閉。

---

