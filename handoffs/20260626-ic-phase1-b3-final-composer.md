# IC Phase 1 B3 — Composer round-3 聚焦重驗（L2 / L4）

> **Reviewer**: Composer（adversarial，非簽核式）  
> **Scope**: round-3 殘留修補 — `validate_split_pair_integrity` local ordinal、`_normalize_symbol_value` strip+sentinel、`split_per_symbol` normalize 路徑  
> **Baseline**: 上輪 15 probe（`handoffs/20260626-ic-phase1-b3-resignoff-composer.md`）未覆蓋 ① 交錯多 symbol 的 L2 pair purge、② 字串 sentinel 的 L4  
> **Date**: 2026-06-26

---

## Verdict

**L2 / L4 round-3：PASS**

round-3 兩項修補在 adversarial 重驗下**關閉原殘留向量**，未發現等同嚴重度的**新洩漏洞**足以 BLOCK 此二項。  
（B3 全體 L5/L6 等其餘項目不屬本次 scope，狀態不變。）

---

## 方法

1. 讀 `momentum/core/contracts.py`：` _local_ordinals_for_symbol` / `validate_split_pair_integrity` / `_normalize_symbol_*` / `split_per_symbol`。
2. 跑 `pytest tests/momentum/core/test_split_contract.py`（25 項，含 round-3 新增 4 項 L2/L4 測試）。
3. 自構 **32 組 adversarial probe**（L2×10、L4×21、round-3 回歸×4），實跑 Python 腳本；0 LEAK。

---

## ① L2 — local ordinal pair purge/embargo

### round-3 修補（碼證）

| 機制 | 位置 | 行為 |
|------|------|------|
| 全域 row → 同 symbol local ordinal | `_local_ordinals_for_symbol` (443-458) | `searchsorted` + 邊界 assert，防跨 symbol 誤映射 |
| 禁區按 local contiguous ranges | `validate_split_pair_integrity` (536-549) | `test_local` 壓段後 `[start-purge, end+purge+embargo)` |
| train 洩漏判定 | 同上 | `train_local` 落入禁區 → `SplitPairLeakageError` |

**與 round-2 差異**：round-2 有 pair-level 檢查但仍用**全域 row position** 算禁區；交錯 frame 下 ETH/SOL 列會扭曲 BTC 的 purge 窗口（上輪 15 probe 皆單 symbol 或純 cross-symbol purity，未測此路）。

### Adversarial 探針

| ID | 場景 | 預期 | 結果 |
|----|------|------|------|
| L2-A | 3 symbol 交錯（BTC/ETH/SOL），train 在同 symbol test purge 區 | BLOCK | ✅ `SplitPairLeakageError` |
| L2-B | 3 symbol，train 遠早於 test | PASS | ✅ 無誤殺 |
| L2-C | 2 symbol 交錯，**非連續** test 兩段，train 落第一段 embargo 尾 | BLOCK | ✅ blocked |
| L2-D | 非連續 test，train 在兩段 test **間隙** | PASS（設計） | ✅ 允許（見 §Residual） |
| L2-E | 全域相鄰但不同 symbol 列塞入 BTC train plan | BLOCK | ✅ `CrossSymbolLeakageError`（purity） |
| L2-F | 2 symbol 交錯乾淨 train/test | PASS | ✅ 無 false positive |
| L2-G | ETH row_index 宣告為 BTC train | BLOCK | ✅ purity |
| L2-H | 非連續 test 第二段 purge 前 train | BLOCK | ✅ blocked |
| L2-I | **4 symbol** 交錯，train 踩第二段 test | BLOCK | ✅ blocked |
| L2-J | 4 symbol 乾淨 split | PASS | ✅ |
| 既有 | `test_l2_interleaved_multisymbol_local_ordinal` / `_far_train_passes` | — | ✅ pytest PASS |
| 既有 | `test_l2_pair_integrity_blocks_train_inside_test_embargo`（單 symbol） | — | ✅ pytest PASS |

**判定**：交錯 3+ symbol、非連續 test 段、purge+embargo 鄰域 — **真擋、正例不誤殺**（在 SplitPlan `purge_gap < len(row_index)` 約束內）。

---

## ② L4 — symbol normalize strip + sentinel fail-closed

### round-3 修補（碼證）

`_normalize_symbol_value` (396-416)：`strip()` → 拒 `{ "", nan, null, none, na, n/a }`（大小寫不敏感）；`None` / `pd.isna` / 非法 bytes → `CrossSymbolLeakageError`。  
`split_per_symbol` (581, 586-587)：`groupby(..., dropna=False)` + 全 frame normalize，與 validate 共用規則。

### Adversarial 探針

| 類別 | 輸入 | 結果 |
|------|------|------|
| None / `np.nan` / `float('nan')` / `pd.NA` / `pd.NaT` | normalize | ✅ blocked |
| 字串 sentinel | `nan, NaN, null, None, na, n/a, "   ", "\t\n", " null "` | ✅ blocked |
| bytes sentinel | `b'nan', b'null', b'', b'   '` | ✅ blocked |
| 非法 bytes | `b'\xff\xfe'` | ✅ blocked |
| 非 str 型別 | `int(12345)` | ✅ blocked |
| 正常 symbol | `BTCUSDT`, `" ETHUSDT "`, `b'SOLUSDT'`, `np.str_('LINKUSDT')` | ✅ normalize 通過 |
| 子字串非 sentinel | `ANONEUSDT`, `NULLCOIN`, `btcusdt` | ✅ 通過（精確集合比對，非 substring） |
| Unicode 空白 | `\u00a0` (NBSP) | ✅ strip 後空 → blocked |
| universe 遠端 NaN | row_index 未含 NaN 列 | ✅ `validate_split_integrity` 全陣列掃描 blocked |
| `split_per_symbol` | frame 含 `"nan"` symbol 列 | ✅ normalize 時 fail-closed |
| 既有 pytest | `test_l4_*` × 10 | ✅ 全 PASS |

**判定**：各類缺值 sentinel **擋**；正常 symbol（含空白 trim、bytes decode）**不誤殺**。

---

## ③ round-3 新洞掃描

| ID | 攻擊面 | 結果 |
|----|--------|------|
| R3-A | 空 train `row_index` 進 pair 檢查 | ✅ `SplitPairLeakageError`（非 silent pass） |
| R3-B | `base_universe_hash` 不一致 | ✅ `ValueError` |
| R3-C | train/test 不同 symbol | ✅ `CrossSymbolLeakageError` |
| R3-D | 非連續 test 段間隙 train | ℹ️ 允許（per-segment 禁區，見下） |
| R3-E | `split_per_symbol` 3 symbol 快樂路徑 + purge_gap=1 | ✅ 產 3 plans，pair 驗證通過 |
| R3-F | `_local_ordinals_for_symbol` 外 symbol row | ✅ `CrossSymbolLeakageError` |

**未發現 round-3 引入的新 LEAK**（local ordinal / sentinel normalize 本身無 bypass）。

---

## §Residual（非本次 L2/L4 BLOCK）

| ID | 風險 | 嚴重度 | 說明 |
|----|------|--------|------|
| R-D1 | 非連續 test **段間** train 允許 | LOW | `validate_split_pair_integrity` 對每段 contiguous test 獨立算禁區；段間 gap（如 local 10–11 在 test [5,6]+[14,15] 之間）不屬任一禁區 → **by design**，非 round-3 回歸。若 CPCV 多段 test 需全域 embargo，屬 adapter/契約擴展，非 L2 local ordinal bug。 |
| R-D2 | `split_per_symbol` 無專項 pytest | MINOR | 邏輯與 adapter 同构；本次 probe 手跑 3-symbol 路徑 PASS；HANDOFF 已列 G3 待補。 |
| R-D3 | `SplitPlan` 建構 `purge_gap >= len(row_index)` | INFO | 單列 train + purge_gap≥1 在建構期拒絕，非 validate 漏檢；caller 須滿足契約。 |

---

## 測試摘要

```
pytest tests/momentum/core/test_split_contract.py -v  → 25 passed
adversarial probes (L2/L4/R3)                       → 32 run, 0 LEAK, 0 FAIL
grep -r 'from api\.' momentum/                      → 0 (解耦維持)
```

---

## 與上輪 15 probe 差距（教訓）

| 漏測 | 原因 | round-3 是否關閉 |
|------|------|------------------|
| L2 交錯多 symbol purge 用全域 position | 上輪 probe 多為單 symbol 或 purity，未構造 BTC 列夾 ETH/SOL 的 frame | ✅ local ordinal |
| L4 字串 sentinel / strip | 上輪只測 `pd.NA` + bytes decode，未測 `"nan"`/`"None"`/空白 | ✅ sentinel set |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: round-3 源碼 local ordinal + sentinel normalize 與 handoffs/20260626-b3-l2-l4-leak-fix.md 描述一致；kline_cache.h5 存在且 pytest 可用
TESTS_RUN: pytest tests/momentum/core/test_split_contract.py (25/25 PASS); 32 adversarial probes 0 LEAK
FAILURES_SEEN: 初版 probe 5 項因 purge_gap>=len(row_index) 建構約束誤判 FAIL → 修正探針後全 PASS
SCOPE_CHANGES: none（唯讀驗證 + 本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**STATUS: DONE**
