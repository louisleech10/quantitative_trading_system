# GAP3 B1 adversarial review — codex R1

TASK_ID: 20260821-GAP3-B1-REVIEW-R1
TASK_VERDICT: B1.0 基本契約、B1.3 split、B1.5 classifier/邊界與 §G-2 exact oracle 通過；B1.1 close-time/PIT、B1.2 transitive dedupe、B1.6 row_id、B1.4 NaN/provenance 仍有問題。B2 verdict=需修補後派工。
D001_VERDICT: A-01 作為實測推翻原 exact 前提的容差修訂可接受（真實 FF V7 15 欄/14 float16 路徑取證）；A-02 `.D-001.md` 延伸檔格式、A-03 `events=` context 與 `entry_after_label_start >=` 均與測試/規格一致。
ORACLE_AND_MUTATION: §G-2 k0/k1/non-boundary、label mode、next_open exact cases 均在 87-gate 綠；M2/M8/M9/M12 使用 production seam，M1/M3/M5/M10 只改 local result/contract/function，見 CODEX-R1-P1-01。

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
