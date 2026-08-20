# Reconcile — 20260821-gap3-b1-review-r1

**來源** 20260821-gap3-b1-review-r1-codex.md, 20260821-gap3-b1-review-r1-composer.md, 20260821-gap3-b1-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；全部寫回 commit e0cecf7c，suite 98 passed）

**Verdict**: 需修補後合併——8 條 findings 全數採納修補（已落檔）；R2 由原提出方（codex 7 條、composer 1 條）重跑同一反例閉合驗證，grok sentinel；全 CLOSED 後三家 RECONCILE-STAMP → 進 B2。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| X1 dedupe 連通分量 | CODEX-R1-P1-02, COMPOSER-R1-P1-01 | **採納**：`dedupe.py` 鏈式掃描改 union-find（overlap ∨ start 差≤gap 即 union）；兩家反例（A/C/B 夾心、a/b/c 鏈）入 `test_dedupe.py` 回歸。**grok 之「相鄰鏈對等價」主張被兩家碼證推翻，採較嚴** |
| X2 mutation guard 生產 seam | CODEX-R1-P1-01 | **採納**：M1 seam `alignment._append_failure`、M3 monkeypatch `load_event_import_contract` 走生產載入、M5 seam `event_split._cluster_weight`、M10 monkeypatch `_classify_one` 端到端走 `classify_counterexamples`（真實 kline 多命中 fixture）；grok「斷言型足夠」之異見不採（較嚴原則） |
| X3 nested 型別閉集 | CODEX-R1-P1-03 | **採納**：契約檔 T8/T9/T10 增 `item_types`；validator 逐欄驗型禁 coercion（數字當字串／字串當 ms／start≥end／list 當 object 皆 `type_error`）；5 參數化反例入 `test_import_contract.py` |
| X4 bar 表 close_time 守護 | CODEX-R1-P1-04 | **採納**：`_validate_bar_table` 對 close_time 同驗 dtype/量級/排序/唯一＋rowwise close>open（違反 ⇒ `tf_boundary_ambiguous`）；兩反例入 `test_alignment.py` |
| X5 row_id 無條件對證 | CODEX-R1-P1-05 | **採納**：全史模式（無 start/end_date）無條件驗 `0≤row_id<len ∧ ms[row_id]==target==ms[pos]`；截斷段顯式 `truncated_mode` 走 timestamp 定位；越界／指他列反例入測試 |
| X6 baseline 非有限值 | CODEX-R1-P1-06 | **採納**：任一 NaN/inf ⇒ loud 拒（與 B1.6「禁 NaN 混入」契約一致，不做 pairwise 靜默刪列）；`n_used` 入逐特徵報告 |
| X7 manifest hash provenance | CODEX-R1-P2-07 | **採納**：`single_feature_binary_baseline(..., feature_manifest_hash=)` 寫入 `receipts.feature_manifest_hash`；測試釘住 |
| — sentinel | GROK-R1-P3-00 | 記錄：87 passed／A-01 float16 複驗／§G-2 重算一致；其 dedupe 等價判斷經 X1 推翻（記入審計，非處置項） |

D-001 三裁決：三家一致「A-01 前提修正非降標、A-02/A-03 成立」。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**：M1/M3/M5/M10 名義 mutation guard 沒有注入 production seam；local `swallowed`、local contract、`assign` 後 DataFrame、local `mutated()` 只能證明測試自身斷言，未證明對應 production mutation 的機械等價。
**碼證**：`test_mutation_guard.py:63-71,86-117,150-165`；指定 targeted run 為 `4 passed, 4 deselected`，但四案未 monkeypatch production。
**來源摘要**：tests/momentum/event_samples/test_mutation_guard.py#e6a324a96632
嚴重度=P1；信心度=高；影響=mutation gate 可對實作 seam 漂移假綠，B1 品質保證不完整；修補=每案以可還原的 production monkeypatch/subprocess mutation 執行，明確斷言 mutated run rc!=0。

## CODEX-R1-P1-02
**斷言**：dedupe 的單鏈簇掃描只比較前一 interval，沒有維持目前簇的 max end/union-find；跨中間事件的 transitive overlap 會被錯拆。
**碼證**：輸入 a=[0,100]、b=[50,60]、c=[90,120]（cluster_gap_ms=0）得到 a,b=`c0`、c=`c1`；區間聯集應三者同簇，且 cluster_first/effective n 會受影響。
**來源摘要**：momentum/Analysis/event_samples/dedupe.py#eba46978fedf
嚴重度=P1；信心度=高；影響=去重、cluster weight、後續 purging/split 的簇邊界可錯；修補=以目前連通元件的最大 end（或 union-find）判斷 overlap，新增三段鏈與 tie/跨 symbol 測試。

## CODEX-R1-P1-03
**斷言**：T8/T9/T10 的 nested conditional schema 未 fail-closed 逐欄驗型；`str(...)` 會把數字/容器當成非空字串，T9/T10 也只檢存在性與少數 availability 條件。
**碼證**：`validate_event_import` 對 numeric `reference_symbols`、numeric source_model fields、list/string 混用的 event_interval payload 仍回傳 2 rows；contract JSON 雖列欄名，未形成可執行型別閉集。
**來源摘要**：momentum/Analysis/event_samples/import_contract.py#cd96c17159e6；momentum/Analysis/contracts/event_import_contract.json#e7b8264b1dc0
嚴重度=P1；信心度=高；影響=錯誤 provenance/interval 可進入 alignment 與模型結果；修補=契約檔補 nested object/array/type/enum schema，validator 禁止 coercion 並逐欄拒收。

## CODEX-R1-P1-04
**斷言**：bar validator 只驗 `open_time_ms`，不驗 `close_time_ms` 的 dtype/量級/排序、`close > open` 或 finite；但 cutoff 用 `searchsorted(close_ms)`，因此 PIT 取列依賴未受守護的排序假設。
**碼證**：刻意給 unsorted 且一列 close 早於 open 的 bars；`ev1` 仍產生 receipt（`last_bar_open_ms=1704067200000`、`last_bar_close_ms=1704110400000`），沒有 invalid-bar failure。
**來源摘要**：momentum/Analysis/event_samples/alignment.py#fb29aa1feb90
嚴重度=P1；信心度=高；影響=連續 crypto fixture 的 T9 nominal assumption 未外推到髒/缺 bar，as-of/PIT receipt 可能錯；修補=在入口 fail-closed 驗 close grid/ordering/finite/close>open，並以明確排序前提或安全搜尋實作 cutoff。

## CODEX-R1-P1-05
**斷言**：B1.6 的 row_id 交叉對證只在 `row_id` 位於範圍內且該列 timestamp 恰等 target 時才比較；越界或指向其他列的 row_id 可繞過檢查。
**碼證**：單事件 `row_id=999`、feature row index 僅 `[1000,2000]`、target=2000 時，materializer 仍輸出 feature `f=2.0`，沒有 failure。
**來源摘要**：momentum/Analysis/event_samples/feature_materialization.py#3363ef292405
嚴重度=P1；信心度=高；影響=損壞 alignment receipt 可被當成成功物化，row provenance 不再是證據；修補=無條件驗 `0 <= row_id < len(ms)` 且 `ms[row_id] == target == ms[pos]`，截斷段另以明確 contract 表示。

## CODEX-R1-P1-06
**斷言**：B1.4 對部分 NaN/inf 逐特徵套 finite mask 並靜默刪列；報告仍以刪除前 `n_test` 與 capability=ok 呈現，違反「NaN 不混入」的資料品質語意。
**碼證**：在真實 baseline synth 的一個 test feature cell 注入 NaN，`single_feature_binary_baseline` 回 `ok 1.0 120`；非全 NaN 不拒收，分母與實際 AUC 樣本數不透明。
**來源摘要**：momentum/Analysis/event_samples/baseline.py#13886a51d9c6
嚴重度=P1；信心度=高；影響=缺值可能改變 OOS 統計與 FDR 而無 failure receipt；修補=輸入層對任何非 finite fail-closed，或明確回傳排除 reason/count 並讓 capability/denominator 反映實際樣本。

## CODEX-R1-P2-07
**斷言**：B1.6 產出 `feature_manifest_hash`，但 B1.4 對外簽名只收 DataFrame/labels/plan，report receipts 只帶 seed/n_perm，hash 沒有進入 baseline provenance。
**碼證**：TODO 明定 B1.4 輸入 `features_at_decision（含 feature_manifest_hash）`；目前 `feature_materialization` 回傳 tuple 的 hash，baseline 不接也不輸出。
**來源摘要**：momentum/Analysis/event_samples/feature_materialization.py#3363ef292405；momentum/Analysis/event_samples/baseline.py#13886a51d9c6
嚴重度=P2；信心度=高；影響=同名特徵表/不同 config 的 baseline report 可缺少可追溯分辨；修補=用 typed wrapper 或顯式 hash 參數傳入並寫入 report receipt，補重跑一致性測試。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、B1 review brief、SPEC/TODO/D-001、templates；base diff 為 45fa3774..df45bc82；B1 event_samples 全 gate 87 passed、真實 kline/FF V7 路徑已執行；D-001 A-01/A-02/A-03 與上述限定一致。T9 nominal 僅在連續 fixture 取證，髒 close-time case 未被守護。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` => 87 passed in 9.25s；targeted M1/M3/M5/M10 => 4 passed, 4 deselected；另以固定 adversarial probes 重現 P1-02/P1-03/P1-04/P1-05/P1-06，均 rc=0 且輸出如各 finding。
FAILURES_SEEN: none during requested gate; probes 的 malformed input 被接受或錯拆，已記為 findings，未改碼重跑。
SCOPE_CHANGES: review-only；只新增本交件檔，未改 implementation/tests/SPEC/TODO/D-001，未碰 data_cache，未 commit。
NUMERIC_OR_SCHEMA_IMPACT: implementation 無變更；review 揭示 cluster membership、PIT receipt、NaN denominator 與 feature provenance schema 風險。
HANDOFF_OUTPUT: handoffs/20260821-gap3-b1-review-r1-codex.md
STATUS: DONE
## COMPOSER-R1-P1-01

**斷言**: `build_event_manifest` 以「排序後僅與前一事件比 overlap」建簇，未實作 TODO B1.2 要求之 interval overlap union-find；存在 label 窗仍相交卻被分到不同 `dedupe_cluster_id` 之反例，且與 `uniqueness_weight`（全表兩兩 overlap 計數）不一致。

**碼證**: `momentum/Analysis/event_samples/dedupe.py:51-63` 鏈式 `cluster_ids`（僅 `i-1` 比對）；`docs/GAP3_EVENT_TODO.md` B1.2 偽碼「interval overlap … union-find 成簇」。RECHECK:
```
venv/bin/python - <<'PY'
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.types import AlignmentReceipts, DedupePolicyConfig
import pandas as pd
def mk(rows):
    ev = pd.DataFrame([{"event_id": e, "t0_ms": s, "decision_offset_bars": 0, "decision_at_ms": s,
         "entry_at_ms": s, "entry_price_source_bar_open_ms": s, "entry_price_source_field": "open",
         "label_start_ms": s, "label_end_ms": t, "entry_after_label_start": False} for e,s,t in rows])
    return AlignmentReceipts(event_level=ev, per_tf=pd.DataFrame())
m = build_event_manifest(mk([("A",0,100),("C",30,35),("B",40,50)]), DedupePolicyConfig(scenario="A"))
print(m.table[["event_id","dedupe_cluster_id","uniqueness_weight"]])
PY
→ A:c0/0.333, C:c0/0.5, B:c1/0.5；A 與 B 區間 [40,50]⊂[0,100] 仍相交卻不同簇
```

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#eba46978fedf; docs/GAP3_EVENT_TODO.md#b7bbe799d905

[MAJOR] 信心度=High。失敗模式：scenario C 之 `cluster_first` 代表選錯、A/B 之 `uniqueness_weight` 與 `dedupe_cluster_id` 脫鉤，B2 顯著性／effective n 偏誤。修法：改為對全部事件對做 interval overlap 連通分量（union-find 或 sweep-line 等價），並加「薄夾層事件拆開寬窗」回歸測試。

---

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——B1.0–B1.6 對 TODO 驗收／D-001 三裁決／mutation 可證偽性／§G-2 手算／PIT 品質均未發現需列 P0–P2 的可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 87 passed rc=0；git diff 45fa3774..df45bc82 僅契約／event_samples／tests／D-001；§G-2 重算 T0_100=1708387200000 與 1h/4h/12h cutoff 字面一致且 kline 12h 全連續；A-01 複驗 float16×14＋因果截斷 exact 14/15；warmup 任一 NaN→failures、M2/M12 seam 可證偽。

**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_TODO.D-001.md#69d05c3d05e6；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；momentum/Analysis/event_samples/alignment.py#fb29aa1feb90；tests/momentum/event_samples/test_mutation_guard.py#e6a324a96632；tests/momentum/event_samples/test_feature_materialization.py#2749aa26d9a1

正文：adversarial 候選（M10 假綠、dedupe 非 UF、causal rtol 未機器強制「14/15 exact」文案）逐一核對後不成立或不達可證偽 finding 門檻——M10 baseline 斷言會抓生產改猜；interval 排序相鄰鏈對 overlap 連通分量等價；A-01 修訂義務即分層 rtol（文案 14/15 為誠實性證據非機器義務）。禁捏造湊數。

ASSUMPTIONS_VERIFIED: A-01 float16／14/15 exact；A-03 `>=` 網格等式；kline 連續；白名單 diff；87 passed
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 87 passed rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT: handoffs/20260821-gap3-b1-review-r1-grok.md
STATUS: DONE
