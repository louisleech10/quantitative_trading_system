SPLITUNIFY B9 REVIEW R25 / family=codex / task=20260911-SPLITUNIFY-B9-REVIEW-R25
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
