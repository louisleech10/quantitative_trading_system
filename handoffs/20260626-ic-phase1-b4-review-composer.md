# IC Phase 1 B4 — Artifact Parquet 獨立 Code Review + 數據正確性確認（Composer）

**Reviewer**: Composer 2.5（非實作者）  
**日期**: 2026-06-26  
**範圍**: Task 3.1（B4 artifact Parquet）  
**對照**: `docs/IC_PHASE1_CONTRACT_TODO.md` Task 3.1、[C-8][R4][R8][T5][T7]  
**驗證命令**:
- `pytest tests/momentum/Analysis/test_ic_artifact.py -v` → **4/4 PASS**
- `grep -rE "from api\." momentum/` → **0**
- 獨立 adversarial probe script（本 review 執行，非 repo 內測試）

---

## Verdict 摘要

| 項目 | 判定 | 一句話 |
|------|------|--------|
| **G2 值守恆** | **PASS（有保留）** | NaN/inf/±0/denorm bit-level 守恆實測成立；`_row_hash` struct.pack 設計正確；但 null float 繞過、合成 fixture、schema nullable 與 DTO 不一致為殘餘風險 |
| **不載全表篩 / O(page)** | **PASS（有保留）** | API 路徑正確（dataset scanner + filter + batch 迭代）；相對 RSS 不變量測試通過但 heuristic 性質強 |
| **Atomic write** | **PASS** | 同目錄 temp + `os.replace`；中斷測試無半檔無孤兒 tmp |
| **Horizon 映射** | **PASS** | `default_horizon` 顯式參數、無猜值；符合 T7 Phase 1 單 horizon |
| **不接 result path / G1** | **PASS** | `api/` 零引用；`get_result` 未改 |
| **解耦** | **PASS** | `grep from api.` momentum/ == 0；logging 用 `momentum.core.logging` |

**總評**: B4 實作達 Task 3.1 驗收門檻，可進 B5；保留項建議 B6 或 B5 接線時補強，非 BLOCKING。

---

## 1. G2 值守恆（寫→讀 Parquet byte 級）

### 1.1 `_row_hash` + `struct.pack(">d")` 設計

**結論：正確**

`test_ic_artifact.py:49-61` 對每列依 `ARTIFACT_COLUMNS` 固定順序：
- float → `struct.pack(">d", value)`（IEEE 754 big-endian 64-bit）
- 其他 → `str(value).encode("utf-8")`
- 欄位間 `\0` 分隔

這比 JSON round-trip 或 `==` 更適合 G2「bit-level」意圖。`ARTIFACT_COLUMNS` 與 `ic_artifact_writer.ARTIFACT_COLUMNS` 同源，寫入時 `_row_to_dict` 強制欄位順序（`ic_artifact_writer.py:165-168`），避免 dict 順序漂移。

### 1.2 實測守恆（含自構反例）

| 反例 | 結果 |
|------|------|
| quiet NaN `7ff8…` | bit-identical |
| signaling NaN `7ff4…` | bit-identical |
| negative NaN `fff8…` | bit-identical |
| `+0.0` vs `-0.0` | 各自 bit 保留（`0000…` vs `8000…`） |
| denormal / `float.max` | bit-identical |
| `math.nan` / `±inf` | pytest 斷言 + hash 全等 |
| `eval_status` 四種 enum | 字串值全等 |
| `batch.to_pylist()` 型別 | 回 Python `float`/`int`/`str`，非 numpy scalar；`isinstance(..., float)` 與 hash 一致 |
| `np.float64` 經 `asdict` | `isinstance(np.float64, float)` 為 True；hash 與 Python float 一致 |

`test_artifact_roundtrip`：`assert _row_hash(loaded) == _row_hash(_dict_rows(rows))` — **4/4 PASS**。

### 1.3 潛在失守情境（adversarial）

| ID | 嚴重度 | 情境 | 現狀 |
|----|--------|------|------|
| F-G2-1 | **MINOR** | `write([dict])` 繞過 `ICArtifactSchema`，`ic_mean=None` | Arrow schema `nullable=True`（`ic_artifact_writer.py:38-42`）接受 null；讀回 `None`；`_row_hash` 對 None 走 `str()` 非 `struct.pack`。**正常路徑** `build_ic_artifact_rows` 用 `float()` 不產 null | 
| F-G2-2 | **MINOR** | `ICArtifactSchema.ic_mean: float`（非 Optional）vs Parquet nullable float | 契約與 on-disk schema 不一致；僅 dict 直寫可觸發 |
| F-G2-3 | **INFO** | TODO 驗證欄寫「真實 IC 輸出」 | 測試用 `_ic_result()` 合成 fixture，非 IC engine 端到端；對 B4 純 IO 層可接受，但 G2 尚未綁真實計算輸出 |
| F-G2-4 | **INFO** | `float(result.ic_mean)` 若上游為 float32 | `float()` 擴寬；Parquet f64 存寬化值；通常正確，極端 subnormal 理論上有 widening 差異 |
| F-G2-5 | **INFO** | zstd 壓縮 | 對 float 欄位 lossless；不影響值守恆 |

**未能構造**讓 `test_artifact_roundtrip` 失敗的 IEEE float 反例（在 `ICArtifactSchema` 正常路徑下）。

---

## 2. 不載全表篩 / predicate pushdown / O(page) RSS

### 2.1 Read 路徑審查

`read()`（`ic_artifact_writer.py:98-135`）：
1. `ds.dataset(path, format="parquet")`
2. `_normalize_filters` → `ds.Expression`（tuple / Expression 皆可）
3. `dataset.scanner(filter=expression, batch_size=limit or 8192)`
4. `scanner.to_batches()` 迭代 — **非** `read_table()` 整表載入
5. `page` 限制輸出列數；`columns` 支援投影

符合 Task 3.1「pyarrow dataset + predicate pushdown + iter_batches」。

### 2.2 Pushdown 實效（adversarial）

| 觀察 | 影響 |
|------|------|
| 40k rows 單檔 → **1 row group**（實測 `num_row_groups=1`） | Row-group 級 skip 無效；filter 在單一 RG 內套用，仍可能解壓大量 column pages |
| `page=5000` 但 filter 僅命中 10 列 | 測試驗的是「結果 len 正確」+ RSS 相對不變，非 page 截斷邏輯 |
| `page=None` | 累積全部 batch → **O(total)** Python list；caller 責任，文件未強調 |

### 2.3 `test_artifact_filter_no_full_load` 可信度

**通過條件**（實測 PASS）：
- small 20k vs large 40k rows，同 filter（10 features）
- `large_peak <= small_peak + 128MB`
- 絕對上限 `< 2GB`（8GB tier × 0.25）

**保留（heuristic 性質）**：

| ID | 說明 |
|----|------|
| F-T5-1 | `psutil.Process().memory_info().rss` 含 Python heap、Arrow pool、allocator 碎片；單次探針曾見 filter 路徑 delta **高於** 全表讀（噪聲） |
| F-T5-2 | **128MB** 容差寬；可掩蓋中等規模 O(n) 增長直至 n 很大 |
| F-T5-3 | 無 mock/spy 證明 row group / page 級 skip；僅相關性 heuristic |
| F-T5-4 | 未測 `columns=` 投影對 RSS 的影響 |

**判定**：相對不變量（2× rows → peak 不變）在現有規模下**可信但非嚴格證明**；符合 TODO 刻意選 psutil 非 tracemalloc 的設計，B6 可考慮多檔/partitioned parquet 加壓。

### 2.4 Write 路徑記憶體

`write()` 第 78 行 `row_dicts = [_row_to_dict(row) for row in rows]` — **寫入 O(total)** 記憶體。Task 3.1 重點在 read 不載全表；寫入全量 materialize 屬預期，非本刀缺陷。

---

## 3. Atomic write（temp + `os.replace`）

### 3.1 實作

```python
fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
# ...
pq.write_table(table, temp_path, compression="zstd")
os.replace(temp_path, destination)
```

- `mkstemp` 與 destination **同目錄** → POSIX 同檔系統 `rename`/`replace` 原子
- `except BaseException` → `temp_path.unlink(missing_ok=True)` → 無孤兒 tmp
- 讀者不會看到 `.name.*.tmp` 半成品（不同檔名）

### 3.2 測試

`test_artifact_atomic`：monkeypatch `pq.write_table` 寫 garbage 後 raise → `artifact_path` 不存在、`*.tmp` 空。**PASS**。

### 3.3 未覆蓋（非 BLOCKING）

- `os.replace` 自身失敗（極罕見）
- 跨檔案系統 destination（若 caller 改 parent 策略）
- 寫入成功後讀者 cache 舊 inode（應用層議題）

---

## 4. `build_ic_artifact_rows` / horizon

**結論：合理，無誤標**

- `ICResult` 無 horizon 欄（`contracts.py:293-309`）— 屬實
- `horizon=int(default_horizon)` 由 caller 傳入（`ic_artifact_writer.py:51-70`）
- `test_build_rows_single_horizon`：13 / 21 兩組 assert `horizon == default_horizon`
- `eval_status=str(result.eval_status.value)` — 存 enum value 字串，與 roundtrip 一致
- **未**將 `monotonicity_score` 等 ICResult 擴展欄寫入 artifact — 符合 `ICArtifactSchema` 明確欄位表，非遺漏

**殘餘風險**：caller 傳錯 `default_horizon` 會靜默寫錯；Phase 1 設計接受，B5 接線時須從 run config 傳入。

---

## 5. 不接 task result path（G1 隔離）

| 檢查 | 結果 |
|------|------|
| `grep ic_artifact` in `api/` | **0 matches** |
| `ic_analysis_service.py::get_result` | 無 artifact 分支（L276 仍 v1） |
| `momentum/` 內 caller | 僅 `factories.create_ic_artifact_writer()` + 測試 |
| `api/services/ic_analysis_service.py` modified? | git status 有改動但與 B4 artifact **無關**（eval_status 等 B2 路徑） |

**G1 未被 B4 污染。**

---

## 6. 解耦與其他

| 檢查 | 結果 |
|------|------|
| `grep -rE "from api\." momentum/` | **0** |
| `grep -r "from api" momentum/` | **0** |
| Logging | `momentum.core.logging.get_logger` ✓ |
| `ICArtifactSchema` | `@dataclass` 非 `frozen=True`；TODO §0 建議不可變契約用 frozen — **MINOR 風格債** |
| 空表 roundtrip | 探針：0 rows 可寫可讀；**無專屬 pytest** |
| `schema_version` | file metadata `b"schema_version": b"1"` + 列欄位 — 雙寫一致 |

---

## Findings 清單（按嚴重度）

| ID | 嚴重度 | Finding | 建議 |
|----|--------|---------|------|
| F-G2-1 | MINOR | dict 直寫可產 null float，偏離 G2 hash 語意 | `write()` 拒 null float 或 `ICArtifactSchema` validator；或測試覆蓋 |
| F-G2-2 | MINOR | DTO `float` vs Arrow `nullable=True` | 統一為 non-null 或 DTO 改 `Optional[float]` |
| F-G2-3 | INFO | G2 測試非真實 IC engine 輸出 | B5/B6 可加一條 engine→artifact golden（可選） |
| F-T5-1..4 | INFO | RSS 測試 heuristic、單 RG、寬容差 | B6 考慮 partitioned parquet + tracemalloc 輔助 |
| F-STY-1 | MINOR | `ICArtifactSchema` 未 frozen | 與 SplitPlan 等對齊改 `frozen=True` |
| F-TEST-1 | INFO | 缺 `test_empty_artifact_roundtrip` | 一行探針即可補 |

**無 BLOCKING / MAJOR 級缺陷。**

---

## ASSUMPTIONS_VERIFIED

- `_row_hash` 使用 big-endian IEEE754 `struct.pack(">d")`；NaN 變體、±0、denorm、inf 經 Parquet zstd roundtrip bit-identical
- `to_pylist()` 回 Python 原生型別；hash 路徑與 pytest 一致
- 40k rows 預設寫入為 1 row group（pushdown 粒度受限）
- `api/` 無 artifact 引用；`get_result` 未接 B4
- `grep from api. momentum/` == 0

## TESTS_RUN

- `pytest tests/momentum/Analysis/test_ic_artifact.py -v` → 4 passed
- 獨立 adversarial probe（NaN 變體、null dict、RSS 對照、row group 計數）→ 見上文

## FAILURES_SEEN

none（review 過程無未解失敗）

## SCOPE_CHANGES

none（read-only review）

## NUMERIC_OR_SCHEMA_IMPACT

無改碼。審查確認：B4 新增 Parquet artifact schema v1；不改既有 IC 計算或 v1 JSON result。

---

STATUS: DONE
