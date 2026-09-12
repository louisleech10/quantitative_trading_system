# Reconcile — 20260911-splitunify-x-review-r7

**來源** 20260911-splitunify-x-review-r7-codex.md, 20260911-splitunify-x-review-r7-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 成員判定未定義全框→標的內之座標轉換**——「D-001保留producer的全框`S」 | P1 | CODEX-R7-P1-01 | 採納（抽驗屬實且範圍比原報更大：投影端自長度閘、同源對證、訓練與測試時刻集合到測試段起點，全部以全框列號直接索引該標的之短索引；交錯標的時越界或取到錯時刻。修法：轉換邊界上移至入口——取得該標的索引後即以同一支具名 helper 把全框列號整批轉為標的內序號，其後投影內部一律只用標的內序號，不再出現全框值；並補交錯多標的之成員判定固定文法斷言與對應變異） |
| **W2 兩家對同一句讀法相反⇒該句本身有歧義**——「D-001保留producer的全框`S」 | P1 | CODEX-R7-P1-01 | 採納（codex 讀 `feature_index_by_symbol` 為各標的自己的短索引；grok 讀為須能被全框列號合法索引之同一數字空間。採 codex 讀法：簽名註解與第四點逐字皆寫「該標的之 post-trim」與「標的內序號」，grok 讀法會使第四點自相矛盾。修法：於簽名處與第四點各加一句釘死其數字空間，並明示不得以全框索引冒充） |
| **W3 sentinel**——「本輪逐項核對後無finding；本家R6」 | P3 | GROK-R7-P3-00 | 採納（紀錄；該家 R6 三條經重驗皆閉合，轉換層與殘留反查未另開擋項。其必答 2① 之讀法不採，理由見 W2） |

**Verdict**: 需修補後合併——W1 與 W2 皆屬同一 P1 擋項，D-001 依上表修訂後須由原提出方 codex 於 R8 重驗閉合；本輪兩家所附戳記因規格續有實質改動而失效，須於修訂後重簽。

## 本輪程序記錄

- R7 為閉合輪（closure），兩家逐條重驗 R6 六條：`CODEX-R6-P1-02`、`GROK-R6-P1-01`、`GROK-R6-P2-01`、`GROK-R6-P2-02` 皆確認閉合；`CODEX-R6-P1-01` 由原提出方判**未閉合**（指紋面已補、成員判定面未補），即本輪 W1。
- 主委抽驗 codex 碼證：`momentum/Analysis/event_samples/split_projection.py:453-458` 以 `assert_positional_rows(train_plan.row_index, n=index_ms.size)` 直接對該標的索引取長度；`:477` 以 `index_ms[rows[0]]` 與 `index_ms[rows[-1]]` 做同源對證；`:486-488` 以 `index_ms[train_rows]` 與 `index_ms[test_rows]` 建時刻集合與測試段起點。四處同病，故轉換邊界上移至入口。
- 既有可複用之轉換實作：`momentum/core/contracts.py:505-519` 之 `_local_ordinals_for_symbol`（已具全框→標的內能力且映不到即丟例外），b8 應提升為具名共用 helper，不得另寫第二份。
- 兩家戳記（codex sha `79a5e81c…`、grok sha `1b63e785…`）於本輪交件檔內，因 D-001 續改而失效。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R7-P1-01
**斷言**: D-001 保留 producer 的全框 `SplitPlan.row_index`，但新入口只收每 symbol 的 post-trim `feature_index_by_symbol`；主成員判定未定義 global→symbol-local 映射，交錯 symbol 會錯分或越界。
**碼證**: D-001:31-34、50、63-70 明定 per-symbol index、轉換只在 fingerprint；`nl -ba momentum/core/contracts.py | sed -n '638,665p'` → `"""逐 symbol 呼叫 splitter，將 local index 轉回全 frame row position。"""`、`row_index=train_rows`；`nl -ba momentum/Analysis/ic_split_adapter.py | sed -n '230,246p'` → `train_rows = positions[train_local]`／`row_index=train_rows`、test 同形。D-001:81-85 的正向 ASSERT 未釘 membership 的 global→local 路徑。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3fca8643e4c0；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_split_adapter.py#c2dd93482826
影響／修法判定：A/B 交錯時 B 的全框 row 3 對 B-local index 長度 2 會越界，或在較長 index 下取到錯時刻；b8 不能證明 assignment 正確。規格需明定 membership 的 exact global→local 轉換與其 producer-attested 交錯測試，或改採 symbol-local `row_index` 並同步全框消費者。
R6 重驗：`CODEX-R6-P1-01` 未閉合（fingerprint bridge 已補，membership bridge 未補）；`CODEX-R6-P1-02` 已閉合（D-001:77、93-111 已納入 wiring/golden/script、producer 欄與 oracle）；`GROK-R6-P1-01` 已閉合（D-001:56-60）；`GROK-R6-P2-01` 已閉合（D-001:48-49）；`GROK-R6-P2-02` 已閉合（D-001:16-20、28-42）。
必答2①：同一 helper 且只以傳入 symbol index 建立轉換時，不構成第二份 row 語意；但 producer、membership、freeze/oracle 各自重寫映射就會構成第二來源，現行文字未封住 membership 這一處。
必答2②：`SU-RESID-4` 可作後續遷移債，前提是 b8 先釘住上述 membership 映射；以目前文字上線會讓全框與 local 兩套座標在主判定並存，具體結果是交錯資料錯分／IndexError，故尚不能進實作。
必答3：不可進實作；先處理 `CODEX-R7-P1-01`。
ASSUMPTIONS_VERIFIED: D-001、TODO、R6 synth 已讀；D-001 sha256=3fca8643e4c0；producer 全框 row_index 由兩處碼證核對；R5 xref rc=0、D-001 format/template rc=0、consult stamps rc=0、attribution rc=0。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/template_check.sh dext docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` rc=0；`bash scripts/reconcile_cluster_attribution_check.sh handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md` rc=0。
FAILURES_SEEN: R6 synth stamp check rc=1（缺 `## 戳記`）；R6 xref 以錯誤多檔參數呼叫曾 rc=1，改用正確單一 synth/target 參數後 rc=0。
SCOPE_CHANGES: none；只新增本交件檔，未改 tracked code/data、未 commit/push、未跑 governance 全套。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪只審 D-001，未改數值、schema、golden 或輸出資料。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-x-review-r7-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R7-P1-01
CLOSED: CODEX-R6-P1-02
STATUS: DONE
## GROK-R7-P3-00

**斷言**: 本輪逐項核對後無 finding；本家 R6 三條（P1-01／P2-01／P2-02）於修訂後 D-001 皆已閉合，轉換層與 `SU-RESID-4` 反查不另開擋項。

**碼證**: 對讀 D-001 `:16`／`:20`／`:48`／`:56-69`／`:77-111`／`:132-133`／`:142`；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `1b63e785a82981a8359addc742d453d9969e1b310f669f2e05e85419f2839b3e`；`grep -n '指紋不足以' docs/SPLITUNIFY_SPEC.D-001.md` → 無輸出；list/dict sha 實跑不同；producer `contracts.py:660-677` 仍全框；`_local_ordinals_for_symbol` `:505-519`；freeze `:152` 仍 `ts_ms`（規格已要求 b8 改）。RECHECK: 重讀上表三列＋必答 2。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#3fca8643e4c0;handoffs/20260911-splitunify-x-review-r6-grok.md#2a272f8fa764;handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R7-BRIEF.md#bc8d16405e06;handoffs/reconcile/20260911-splitunify-x-review-r6/synth.md

正文：sentinel only。閉合依據＝規格字面已落入 R6 修法落點表；未改碼、未重跑產品 pytest（closure 範圍）。

ASSUMPTIONS_VERIFIED: R6 三條落點字面皆在；list/dict sha 仍異；舊互斥句已刪；C-4 簽名段限定句在；producer 全框語意未變；`SU-RESID-4` 已登記；轉換層「同一 helper＋僅指紋兩處」與 membership 全框索引可並讀而無必經旁路轉換
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `1b63e785…`；`grep -n '指紋不足以' docs/SPLITUNIFY_SPEC.D-001.md` → 0；`venv/bin/python` list/dict sha 對照 → 不同；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r7-grok.md --family grok` → 見下
FAILURES_SEEN: none（closure-only）
SCOPE_CHANGES: none（僅本產出檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r7-grok.md

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R6-P1-01,GROK-R6-P2-01,GROK-R6-P2-02
STATUS: DONE
