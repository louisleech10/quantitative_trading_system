# Reconcile — 20260911-splitunify-b9-review-r25

**來源** 20260911-splitunify-b9-review-r25-codex.md, 20260911-splitunify-b9-review-r25-composer.md, 20260911-splitunify-b9-review-r25-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **J1 metadata 層仍有兩處 live 字面（同型第六次，三家撞題）**——codex「SPEC`docs/SPLITUNIFY」／composer「`docs/SPLITUNIFY_TOD」／grok「H1六處修補後仍有兩處live字面把`m」 | P1 | CODEX-R25-P1-01, COMPOSER-R25-P1-01, GROK-R25-P1-01 | 採納（🔴 **三家獨立提出、命中同一組**：①`§P Task 9.1` 之 `:187` bullet 仍以**祈使句**要求「須定義 `discarded` 之 producer→metadata **資料流交接**」並規定「驗收須為 producer→summary→metadata **整鏈**測試」，與同 Task 目標句之兩層交付互斥；②`docs/SPLITUNIFY_TODO.md` §E 之 `SU-RESID-9A-UI` 列（`:892`）仍寫「Phase 9A 交付至 producer 層（producer 回傳 → summary → `metadata.split_unify`）」——**該殘留自身**的定義就是把 metadata 層延後，卻在同一句把它列成已交付；**v20 修了 SPEC §N 同名條目，沒改 TODO 這一面**。兩處均**逐字採 grok 之修法**改寫、原字面刪節線保留。碼證：`EventPipelineResult`（`pipeline.py:52-63`）無 `metadata` 欄，三家各自實跑反向斷言得 rc=1。🔴 **主委另做全檔窮舉掃描**（非委員要求）：對 `metadata.split_unify`／`三層`／`整鏈` 三 token 在兩檔逐行列出並逐行判定，確認除本輪兩處外其餘命中皆已帶刪節線或更正註；`TODO:410`（`Task 4.1` 之 IC 路徑五鍵揭露，屬 `D-002-C6`）與 `TODO:469`（已明寫不在本 Task）判為**非互斥**，與三家一致。SPEC 進 **v21**） |

### 本輪裁定

1. **r24 兩條由原提出方 CLOSED**（codex：`CODEX-R24-P1-01`／`CODEX-R24-P2-02`；composer 獨立複核亦判兩條 CLOSED）。codex 並一併 CLOSED 其 r22 三條。
2. 🔴 **composer 誠實把自己 r23 的立場改判 STILL-OPEN**：它在 r23 必答 3 答「舊段無 B9B 互斥」，r24 已證 SPEC 面有漏、本輪再證 TODO §E 同名殘留仍三層字面 ⇒ 自標未閉。**這正是 r25 brief 收緊必答 3 的理由**（只答「無」而不附逐段掃描命令與涵蓋範圍者視為未作答），本輪三家皆附逐段表。
3. **三家對其餘三條必答結論一致**：`M-SU-D2-03` 改標無應紅**不**造成 mutation 條數（40）或 `C5` register（29 列）不一致——register 無任一列指向 `M-SU-D2-03`；`SU-RESID-C5-TARGETS` 之 19／10／4／15／29 兩檔全部一致、無第三處 live 舊數字。
4. **SPEC 進 v21**，新 body sha256 為 755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f ⇒ v20 之三枚 REJECTED 戳記失效，須重簽。回歸六路 **706 passed、1 xfailed**；兩份 `doc_format_precheck` rc=0。
5. 🔴 **brief 之 assumed 第 1 條（「TODO 那一面是否也有把 metadata 當本批交付的舊段」）三家全部證實為真** ⇒ 連續第四輪（R18／R21／R22／R25）主委自標之疑慮被證實，維持「把沒把握的面寫進 brief 交出去攻」。
6. **下一步**：派 `review-r26` 做 J1 閉合再驗證 ＋ 對 v21 新 body 三家重簽；齊備後進 `Task 9.2b`（批次 B9C）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R25-P1-01
**斷言**: SPEC `docs/SPLITUNIFY_SPEC.D-002.md:187` 與 TODO `docs/SPLITUNIFY_TODO.md:892` 仍把本票寫成 producer→`EventSplitPlan.summary`→`metadata.split_unify` 三層；這與同一 v20 的兩層交付、`SU-RESID-9A-UI` 延後決策互斥，會誘導實作者把殘留層當 B9B 交付。
**碼證**: 現行 producer result 僅有 `summary`／`split_plan`，builder 亦無 `discarded` 參數；兩處文字都不是刪節或歷史敘述，故屬可執行契約衝突。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:52
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md:187#c12382d397d9、docs/SPLITUNIFY_TODO.md:892#b0db3a346d63；反向探針實跑 rc=1。修法：兩處均明寫「本延伸只交付 producer→summary 兩層；metadata handoff 待 SU-RESID-9A-UI 另票」；此為單一文件修訂可關閉的 P1。
R25-1a: r24 `CODEX-R24-P1-01` 六處已逐一對齊；r24 `CODEX-R24-P2-02` 的 19/29 數值已對齊；r23 `COMPOSER-R23-P3-00`、`GROK-R23-P3-00` 均為 sentinel/proceed，無待關閉 ID；本輪仍開放 CODEX-R25-P1-01。
R25-1b: `venv/bin/python -c ...EventPipelineResult...` rc=1（預期反例）；六路 pytest rc=0、706 passed/1 xfailed；兩份 `doc_format_precheck.sh` 均 rc=0。
R25-2a: body hash 命令輸出 `c12382d397d96beb732e9514a6cb540519a7833c3921cd5d4bcfab66e1dfad05`，但本輪結論 REJECTED（P1 未閉）。
R25-2b: blocker 僅 CODEX-R25-P1-01；修法是 SPEC/TODO 文字同步，未授權本票直接改正文。
R25-3a: `awk` 排除 `## 沿革與追溯索引` 的逐段掃描結論：SPEC §P 9.1=187 發現、§P 9.2/9.2a/9.2b/9.3/9.4/9.5 無新增；§V 9.1 明確 residual、§V 9.2–9.5 無新增；§R/§N 對齊；TODO 2.1/2.2/2.3 為舊或 SUPERSEDED、4.1 是既有 C-6、9.1–9.5 無新增，僅 §E:892 發現。
R25-3b: 無其他 finding；對兩處直接替換為「本延伸只交付 producer→`EventSplitPlan.summary` 兩層，`metadata.split_unify` 交 `SU-RESID-9A-UI` 待另票解除後定義」。
R25-4a: `awk` 逐列掃 mutation register=40；C5 register IDs=`C5-01`…`C5-29` 共29；M-SU-D2-03 現標 residual/no active red test，與 C5 register mutation 欄逐列核對無衝突。
R25-4b: 無 exact entry/wording mismatch；C5-28 的 mutation dash 與 M-SU-D2-03 不引用 C5，兩者均為意圖而非漏登。
R25-5a: TODO §E 現行分組為 10 keyed + 4 basename-only + 15 no-basename = 29，缺精確錨為 29−10=19；`20` 僅在明示舊值/刪節線，數值一致。
R25-5b: 未發現 SPEC/TODO 現行數值 mismatch；`SU-RESID-C5-TARGETS` 的 19 與觸發門檻 15 均一致。
R25-6a: 目前不可進 Task 9.2b B9C；需先關閉 CODEX-R25-P1-01，並維持 producer→summary 兩層與 metadata residual 邊界。
R25-6b: 最小閉合集為修正 SPEC:187、TODO:892、重跑兩份 precheck、body hash、六路 pytest，再由三家以同一 v20 hash 重簽 APPROVED。
§1 必查：矛盾=上述 P1；端到端=metadata 鏈無入口；回退=兩層現行；可測性=producer/summary 測試已過、metadata 反例 rc=1；資料品質=無變更；解耦=無變更；scope=遵守；性能=無變更；錯誤分類=無變更；併發=無變更；可觀測性=本票不交付終端 visibility。
VERDICT: blocked
BLOCKED-BY: CODEX-R25-P1-01
CLOSED: CODEX-R24-P1-01,CODEX-R24-P2-02,CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03
ASSUMPTIONS_VERIFIED: brief 指定 hash、六路測試、兩份 precheck、r23/r24 debt、C5 29/10/4/15/19 與 mutation 40 均以實跑命令核對；SPEC/TODO 掃描排除歷史區。
TESTS_RUN: `venv/bin/python -m pytest -q -rxX tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → rc=0, 706 passed, 1 xfailed；body/precheck 命令均 rc=0。
FAILURES_SEEN: metadata reverse probe rc=1（預期、證明缺欄）；`reconcile_stamps_check.sh` rc=1（預期，三家最新 R25 stamps 尚 REJECTED）。
SCOPE_CHANGES: none；僅新增本交接檔並追加 SPEC 戳記，未改程式、SPEC 正文或 TODO 正文。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪為 review，未改數值、schema、輸出大小或測試斷言。
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r25-codex.md
STATUS: DONE
## COMPOSER-R25-P1-01

**斷言**: `docs/SPLITUNIFY_TODO.md` §E `SU-RESID-9A-UI` 仍 live 宣稱 Phase 9A 交付含 `metadata.split_unify` 第三層，與 v20 SPEC §N 同名條目（兩層、metadata 已刪節）及 `Task 9.1` TODO `:454` 互斥，實作者讀 TODO 殘留表會誤把 metadata 層當本延伸已交付。

**碼證**: `grep -n 'SU-RESID-9A-UI' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO `:892` 含「`producer 回傳 → EventSplitPlan.summary → metadata.split_unify`」；SPEC §N `:330` 已為「`build_event_keys` 回傳 ＋ `EventSplitPlan.summary` 鍵」且 metadata 刪節。`EventPipelineResult` 無 `metadata` 欄。
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:892
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'

**來源摘要**: docs/SPLITUNIFY_TODO.md#b0db3a346d63; docs/SPLITUNIFY_SPEC.D-002.md#c12382d397d9

[BLOCKING] 信心度=High；同型第五次發作之 TODO 面漏同步（R24 已修 SPEC §N 六處、未修 TODO §E 同名條目）。修法：`:892` 改為與 SPEC §N `:330` 逐字對齊之兩層表述＋刪節線追溯；一次修訂可關。

---

## GROK-R25-P1-01

**斷言**: H1 六處修補後仍有兩處 live 字面把 `metadata` 層當本延伸交付／驗收義務：SPEC §P Task 9.1 `:187` 要求定義 producer→metadata 資料流交接並做「producer→summary→metadata 整鏈」驗收；TODO §E `SU-RESID-9A-UI` `:892` 寫 Phase 9A 交付鏈含 `metadata.split_unify`——皆與 v20 已定「只交兩層、metadata 入殘留」及 `EventPipelineResult` 無 `metadata` 欄互斥。

**碼證**: `sed -n '187p' docs/SPLITUNIFY_SPEC.D-002.md` 仍含「須定義…producer→metadata…整鏈」且無刪節線；`sed -n '892p' docs/SPLITUNIFY_TODO.md` 仍含「producer 回傳 → `EventSplitPlan.summary` → `metadata.split_unify`」；對照 SPEC `:330`／TODO `:454`／`:469` 已兩層。`venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; print(sorted(EventPipelineResult.__annotations__)); assert "metadata" in EventPipelineResult.__annotations__'` → 欄位無 metadata、**AssertionError**（rc=1）。
CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:187
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; assert "metadata" in EventPipelineResult.__annotations__'

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R25-BRIEF.md#086baa8628f1; docs/SPLITUNIFY_SPEC.D-002.md#c12382d397d9; docs/SPLITUNIFY_TODO.md#b0db3a346d63

[BLOCKING] 信心度=High。同型「改 A 漏 B」：R24 修了 SPEC 六處與 TODO 數字，**未**改 §P `:187`（codex R24 斷言曾點名 handoff）與 TODO §E 同名殘留列。修法見必答 3b；一次文件修訂可關；不重開 9.2b 設計。

---

