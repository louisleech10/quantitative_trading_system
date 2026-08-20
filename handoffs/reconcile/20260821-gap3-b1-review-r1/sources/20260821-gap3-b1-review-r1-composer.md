# GAP-3 B1 批 code review — COMPOSER R1

family: composer  
task-id: 20260821-GAP3-B1-REVIEW-R1  
scope: B1 實作碼＋測試（`git diff 45fa3774..df45bc82`）；權威 `docs/GAP3_EVENT_TODO.md` FROZEN＋`docs/GAP3_EVENT_SPEC.md`＋`docs/GAP3_EVENT_TODO.D-001.md`  
brief: `handoffs/20260821-gap3-b1-review-brief.md`  
禁改碼：review-only

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R1 複核結論 |
|---|---|---|
| B1 Gate 87 passed（含 §G-2／mutation 8 條） | fact-verified（brief） | **本輪重跑** `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 87 passed rc=0；mutation 8 條子集 → 8 passed rc=0 |
| FF V7 14/15 欄 float16、末端截斷 14/15 exact | fact-verified（brief） | 未重跑 probe；`test_causal_invariant_truncate_future` 綠（`atol=0` 路徑）佐證因果 invariant 未弱化 |
| kline 連續網格、helpers 秒→ms | fact-verified（brief） | `test_alignment.py` 字面整數 ms oracle 與 `load_bars` 一致 |
| D-001 A-01 分層容差＝誠實前提修正非降標 | **攻後＝成立** | 因果截斷仍 exact；段起點僅放寬至 `2^-8` 且 D-001 附 200+ 根收斂實測；非 look-ahead 型漂移 |
| `entry_after_label_start` 用 `>=` | **攻後＝成立** | `alignment.py:192-194` 註記＋`test_next_open_close_to_close_two_number_disclosure` 綠 |
| `events=` context keyword 不違 receipt 閉集 | **攻後＝成立** | symbol/timeframe 走 manifest／materialize 層 join，未擴 `receipt_schema` |
| T9 名目 `decision_at` 與對齊層一致 | **攻後＝條件成立** | 連續網格＋`t0` 必為 bar open 時名目＝實際；離網格由 B1.1 `no_boundary_match` 先擋 |

VERIFY（本輪實跑）:
```
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 87 passed in 9.11s rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k "M1 or M2 or M3 or M5 or M8 or M9 or M10 or M12" → 8 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_feature_materialization.py::test_causal_invariant_truncate_future -q → 1 passed rc=0
git diff 45fa3774..df45bc82 --name-only → 21 檔，皆白名單內新增（無 §0-6 外既有檔）
```

---

## 必答（brief 六題）

### 1. 逐 Task 對 TODO 驗收（B1.0–B1.6）

| Task | verdict | 摘要 |
|---|---|---|
| B1.0 匯入契約 | **PASS**（測試覆蓋） | `import_contract.py` fail-closed；`test_import_contract.py` 覆蓋鍵集／枚舉／ms 閘／digest／direction 混值／二元缺類別；M3/M12 mutation 可證偽 |
| B1.1 PIT 對齊 | **PASS** | 無 silent skip；`failures{event_id,reason}`；記帳守恆；W11 `decision_at≤t0`；M1/M2/M9 有 seam |
| B1.2 去重 manifest | **FAIL（演算法）** | 見 `COMPOSER-R1-P1-01`：未實作 TODO 要求之 interval overlap **union-find**，鏈式掃描可拆開仍相交之事件 |
| B1.3 事件切分 | **PASS** | per-symbol ms 切分；purge；macro/micro 標示；`degraded:single_symbol`；M5 權重和斷言 |
| B1.6 特徵物化 | **PASS**（D-001 修訂後） | 連續 FF 物化＋as-of 取列；warmup→failures 非 NaN 混入；記帳守恆 W5 |
| B1.4 baseline oracle | **PASS** | permutation 三道硬檢；M8 monkeypatch `_permute`；label 置亂落帶 |
| B1.5 反例分類 | **PASS** | 多類不猜；boundary `±1e-9`；M10 可證偽 |

越權改檔：**none**（diff 僅新增檔）。

### 2. D-001 三條裁決

| 條目 | verdict | 依據 |
|---|---|---|
| A-01 儲存量子級容差 | **前提修正（非降標）** | `test_feature_materialization.py::assert_frames_equal_with_exception` 分層 `2^-10`／`2^-8`／`1e-3`；因果路徑 `atol=0` 仍 exact；差異限於 float16 量化級 |
| A-02 延伸檔檔名 `*.D-NNN.md` | **成立** | `docs/GAP3_EVENT_TODO.D-001.md` 依 FROZEN 修訂規約落地，未就地改 FROZEN TODO |
| A-03 `events=`／`entry_after_label_start>=` | **成立（備忘與實作一致）** | `dedupe.py`/`feature_materialization.py` 選用 `events=`；`alignment.py:194` 用 `>=` 且有測試 |

### 3. mutation guard 可證偽性（M1/M2/M3/M5/M8/M9/M10/M12）

| ID | 生產 seam | 可證偽性 |
|---|---|---|
| M1 | 記帳守恆（無專用 monkeypatch） | **部分**：測試內模擬吞失敗列驗算式，非 patch `align_events`；但 `test_accounting_conservation_m1` 覆蓋真路徑守恆 |
| M2 | `_select_cutoff_idx` | **強**：monkeypatch + `feature_after_decision` |
| M3 | contract `ms_magnitude_min` | **強**：鬆閘後秒級 t0 通過 |
| M5 | 測試內改 `cluster_weight` | **強**（斷言層，語意＝棄 1/n） |
| M8 | `_permute` | **強**：恆等排列觸發硬檢 ii |
| M9 | `_decision_idx` | **強**：k 竄改 exact oracle 紅 |
| M10 | `_classify_one` 邏輯 | **強**：測試內 mutated 函式對照 |
| M12 | `_T9_AVAILABILITY_ENFORCED` | **強**：flag False 後 research_only 檢查移除 |

無「僅測試路徑生效」之假綠縫隙（M12 flag 在 `import_contract.py` 正式路徑讀取）。

### 4. §G-2 手算 oracle（test_alignment）

**正確。** `test_g2_k0_integer_exact`／`test_g2_k1_offset_exact`／`test_g2_nonboundary_1h_anchor_asof` 以連續網格算術寫死整數 ms，`==` 容差 0；與 `alignment.py` 之 `searchsorted` as-of 規則一致。RECHECK：`pytest tests/momentum/event_samples/test_alignment.py -q` → 11 passed。

### 5. PIT／資料品質（§3）

- **silent skip**：`alignment.py` 全事件 either receipt or failure；`feature_materialization.py` 記帳守恆 AssertionError
- **NaN 弱化**：warmup 事件入 `warmup_insufficient_<tf>`，非填 0（`feature_materialization.py:116-118`）
- **look-ahead**：PIT 鏈 `feature_cutoff≤decision_at`；M2/M9 可證偽
- **alignment 失敗枚舉**：`missing_bar`／`unsorted_bar`／`duplicate_bar`／`warmup_insufficient_*`／`label_window_incomplete`／`feature_after_decision` 等有測試覆蓋；未見靜默吞事件
- **B1.6 warmup**：任一 NaN＝`warmup_insufficient_<tf>`（`test_warmup_event_goes_to_failures_not_nan` 綠）

### 6. 可進 B2？

**需修補後派工** — B1.2 簇演算法與 TODO union-find 語意不符且 manifest 內部不一致（見 P1-01）；其餘六 Task 與 Gate 可接受。建議修 `dedupe.py` 為真正 interval-overlap 連通分量（union-find 或等價）並補回歸用例後再進 B2。

---

## §1 必查（11 類摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾/互斥 | B1.2 實作 vs TODO「union-find」— 見 P1-01 |
| 2 漏項/端到端 | 无（七 Task 皆有模組＋測試） |
| 3 不可測驗收 | 无 |
| 4 可疑 quant 假設 | P1-01（重疊權重／簇 ID 錯誤 ⇒ RISK-d） |
| 5–11 | 无 |

---

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

## Verdict：需修補後派工

1 條 MAJOR（B1.2 dedupe union-find）。D-001 三條裁決均成立。B1 Gate 測試全綠但不足以覆蓋 P1-01 反例。修補 `dedupe.py`＋測試後可進 B2 quorum。

---

ASSUMPTIONS_VERIFIED: pytest 87+mutation 8 本輪重跑；dedupe 反例腳本；diff 白名單；D-001 因果 exact 探針  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 87 passed rc=0；mutation 8 條 → 8 passed rc=0  
FAILURES_SEEN: none（review 過程）  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）  
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b1-review-r1-composer.md`

STATUS: DONE
