# IC Phase1 1-align — R2 閉合複驗 (Composer)

**Task-id**: ic1a-align-specadv-r2  
**Agent**: Composer (R1 原提出方)  
**Date**: 2026-07-08  
**Scope**: `docs/IC_PHASE1_1A_ALIGN_SPEC.md` v2 + `docs/IC_PHASE1_1A_ALIGN_TODO.md` v2  
**Method**: 重跑 R1 同一 receipt/反例 + 條文對照 v2 §ADV-RESOLUTION / D-1~D-3 / Task 1.2 / 2.4 / M5

---

## 總判

**VERDICT: REJECT**

**原因**: R1 **BLOCKING** `ADV-COMPOSER-1A`（event_filter 路徑）v2 修法（Task 2.4 timestamp 交集）在 materialize 主路徑（features **int64 秒 Index**）上實跑仍不閉合——交集恆空 → 規格自訂「交集為空→raise」會 100% 誤殺 event_filter on 路徑。另有一項 **NEW-ISSUE MAJOR**（index 同型化義務未寫清）不單獨觸發 REJECT，但應併入下一版。

---

## 逐條結論（R1 BLOCKING / MAJOR）

| R1-ID | 嚴重度 | 判定 | 依據 |
|-------|--------|------|------|
| ADV-COMPOSER-1A | BLOCKING | **STILL-OPEN** | TypeError 反例仍成立：`python -c "…DatetimeIndex…df.loc[11:49]"` → `TypeError: cannot do slice indexing on DatetimeIndex with these indexers [11] of type int`。v2 Task 2.4 改為 `features_df.index.intersection(filtered_ts)`，但 materialize 路徑 features 仍 int64（見 COMPOSER-2 receipt）；**實跑** int64 Index ∩ DatetimeIndex → **size=0**（非 TypeError，但 Task 2.4 ④「交集為空→raise」→ event_filter 全拒）。條文未要求 stage3 前對 `features_df.index` 做 D-1 實體正規化。 |
| ADV-COMPOSER-1B | BLOCKING | **CLOSED** | §C#4 + Task 2.3 明列 `_slice_raw_data_by_mask`(:462-479) 與 `_slice_by_mask` 同規則；邊界④ raw int64 vs feature datetime→D-1 轉型後比對。 |
| ADV-COMPOSER-1C | BLOCKING | **CLOSED** | §C#7 + Task 2.6 接 Tier-1(index 驗+per-symbol 覆蓋率)；`:754-756` reindex 路徑已列。 |
| ADV-COMPOSER-1D | BLOCKING | **CLOSED** | 外部 labels 早退(:1642-1644)依 Task 2.2 在 stage0 先 gate（§C#2）；analyze 主鏈 stage0→stage2，無繞過條文。 |
| ADV-COMPOSER-2 | BLOCKING | **CLOSED** | D-1 接受 int64 秒 Index + gate 內轉 datetime；G-2 明定必測 materialize→`_load_features_hdf5`。**實跑** hermetic H5 roundtrip（鏡像 :2469-2471）：`dtype=int64, is DatetimeIndex=False, sample=[1704067200,…]`；v2 不再要求 Tier-1 硬拒此型別。 |
| ADV-COMPOSER-3 | BLOCKING | **CLOSED** | D-2 bar-ordinal + Task 1.1 Tier-2 用 `close.iloc[i+lag]`；禁日曆查找。**實跑** 缺棒序列：bar oracle @01:00 用 close@03:00，日曆 t+1h=02:00 不在 index——v2 條文與 `label_generator.py:43-47` `shift(-horizon)` 一致。 |
| ADV-COMPOSER-4 | BLOCKING | **CLOSED** | Task 1.2 共用 resolver + §0「禁直接讀 default_horizon 當 lag」+ M7 mutation；§ADV-RESOLUTION CODEX-7 對齊。生產碼 `:110-120` 仍 `del labels_df`（未實作，屬預期）；**條文**已覆蓋反例 `return_5`+default=1→purge 同源。 |
| ADV-COMPOSER-5 | MAJOR | **CLOSED** | D-3 兩段政策 + ③ gate 不取代 split `_validate_expected_frequency`（職責明文）。**實跑** 合成 2h jump：strict split FAIL、D-3 mode cadence=1h gap_count=1——屬**刻意**分工非遺漏；§G 補單點 gap hermetic。`data_cache/kline_cache.h5` ETHUSDT/1h：322 rows、gaps=1、infer_freq=None（R1 receipt 可復現）。 |
| ADV-COMPOSER-6 | BLOCKING | **CLOSED** | §C 測試遷移義務 + Task 2.4 邊界③ + B3 Gate 白名單 pre-existing 2 failed；`test_load_features_hdf5` RangeIndex 保留。`pytest tests/momentum/test_ic_filter_orchestrator.py -q` → **2 failed, 32 passed**（與 R1 同）。 |
| ADV-COMPOSER-7 | MAJOR | **CLOSED** | M5 雙腿（腿A raises PASS / 腿B no-op→同測 FAIL）+ M6 sha256 對照；§G G-2 off=monkeypatch 非 production flag。較 R1 三元 hash 提案略弱，但可證偽性已達「gate 接線」+ M1-M4 轉紅。 |
| ADV-COMPOSER-8 | MAJOR | **CLOSED** | M1 頭 2+尾 2+變異區（Task 1.1 / §V）；M6 測試 monkeypatch no-op（§G/§R）；M3 與 D-1 相容（int64 秒放行、雙 RangeIndex 拒）。 |
| ADV-COMPOSER-9 | MAJOR | **CLOSED** | §N defer Phase 3 cut2；保留 direct-vs-reindexed 雙探針另立 epic。 |
| ADV-COMPOSER-10 | NON-BLOCKING | **CLOSED** | §N 交付 handoff 凍結 `effective_horizon` 供 1e+1b。 |
| ADV-COMPOSER-11 | NON-BLOCKING | **CLOSED** | §N#10 ML label 消費另立 epic，不暗示 IC gate 全平台覆蓋。 |

---

## v2 新增裁決 — 新洞檢查

| 裁決 | 判定 | 依據 |
|------|------|------|
| D-1 int64 相容 | **CLOSED**（spec 層） | 條文 + hermetic roundtrip receipt；loader schema 不改。 |
| D-2 bar-ordinal | **CLOSED** | 條文 + 缺棒 oracle 實跑分歧 receipt。 |
| D-3 兩段 freq | **CLOSED** | 條文 + strict vs mode 合成 receipt + 真 kline gap receipt。 |
| Task 1.2 horizon resolver | **CLOSED** | 條文/Task 1.2/M7 覆蓋 COMPOSER-4；fallback warning+metadata 與「不可解析→raise」邊界②一致（可解析欄名優先）。 |
| Task 2.4 event_filter | **NEW-ISSUE BLOCKING** | 見 ADV-COMPOSER-1A STILL-OPEN：修法引入「int64∩DatetimeIndex=∅」新失敗模式，未在 R1 反例集合中但由 v2 新條文实跑導出。 |
| M5 雙腿 | **CLOSED** | §V / TODO B2 Gate 雙 receipt 要求明確。 |
| **NEW-ISSUE MAJOR — index 同型化** | **NEW-ISSUE MAJOR** | Task 2.1 把 label 軸 datetime 化，但未寫 `features_df.index` 實體正規化；Task 2.3「len 相等须 equals 才 iloc」在 int64 features × datetime labels 同長時路徑未定（非雙 RangeIndex、非 equals）→ 實作歧義。建議：stage0/2.1 後統一 D-1 正規化並寫回兩邊 index，或 Task 2.4 交集前對 features 做同款 D-1 轉型。 |

---

## 重跑 receipt 摘要

```bash
# TypeError (R1 COMPOSER-1A) — 現行碼行為，v2 尚未實作
python -c "import pandas as pd; df=pd.DataFrame({'f':range(5)}, index=pd.date_range('2024-01-01',periods=5,freq='1h')); df.loc[11:49]"
# → TypeError: cannot do slice indexing on DatetimeIndex with these indexers [11] of type int

# Task 2.4 交集漏洞 (NEW)
python -c "import pandas as pd; ts_int=pd.Index([1704067200,1704110400]); ts_dt=pd.to_datetime(ts_int,unit='s'); print(len(pd.DataFrame({'f':[1,2]},index=ts_int).index.intersection(ts_dt)))"
# → 0

# materialize roundtrip int64 (COMPOSER-2) — hermetic H5 鏡像 :2469-2471
# → dtype int64, is DatetimeIndex=False

# bar vs calendar oracle (COMPOSER-3)
# → 缺 02:00 棒时 bar oracle 用 03:00 close

# pytest (COMPOSER-6)
pytest tests/momentum/test_ic_filter_orchestrator.py -q
# → 2 failed, 32 passed

# gap 真資料 (COMPOSER-5)
# data_cache/kline_cache.h5 ETHUSDT/1h → 322 rows, gap_count=1, infer_freq=None
```

---

## 建議下一版最小修補（供 reconcile）

1. **Task 2.4**：交集前對 `features_df.index`（及 `label_series.index`）做與 D-1 相同之 datetime 正規化（或 `_coerce_timestamp_array` 兩側比對後 positional 選列）；禁止裸 `Index.intersection` 跨 dtype。
2. **Task 2.1 / §C**：明寫 gate PASS 後 orchestrator 層 **寫回** 同型 datetime index（features+labels 同源），避免 slice/event_filter/IC 三路 index 分裂。
3. §ADV-RESOLUTION 第 24 行「Task 2.1 含 event_filter」→ 更正為 **Task 2.4**（文檔筆誤，非阻擋項）。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
- R1 TypeError receipt 仍可复現（2026-07-08 实跑）
- int64 Index ∩ DatetimeIndex = 0（Task 2.4 修法反例实跑）
- _load_features_hdf5 hermetic roundtrip → int64 秒 Index（D-1 适用）
- bar-oracle vs calendar 缺棒分歧（label_generator shift 语义）
- ETHUSDT/1h data_cache/kline_cache.h5 gap_count=1 infer_freq=None
- pytest orchestrator 2 failed/32 passed（pre-existing 白名单一致）
TESTS_RUN:
- python TypeError / intersection / oracle / roundtrip snippets（见上）
- pytest tests/momentum/test_ic_filter_orchestrator.py -q → 2 failed, 32 passed
FAILURES_SEEN: none（审查任务；pre-existing 2 failed 非回归）
SCOPE_CHANGES: none（只读+写本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none（未改生产 code）
產出檔: handoffs/IC1A-ALIGN-SPECADV-R2-composer.md
```

STATUS: DONE
