# Layer 6.5 全模組優化 TODO

> **版本**: V1
> **狀態**: V1 TODO Frozen (Implementation-Ready — Execution/External Validation Gates Pending)
> **Frozen 範圍**: 文件層級已凍結；實作、runtime validation gates 與外部 reviewer handoff 尚未完成
> **基於 SPEC**: [docs/L65_OPTIMIZATION_SPEC.md](L65_OPTIMIZATION_SPEC.md) V1
> **生成日期**: 2026-04-26
> **修訂日期**: 2026-04-26
> **產生工具**: AI Agent (Claude Opus 4.7) 依 `templates/TODO_GENERATION_PROMPT.md`

---

## 0. 全域規則與約束（從 SPEC §0 + §1 提取）

> 本節為「執行 Agent 必讀」。讀完本節即可在不回頭翻 SPEC 的情況下遵守所有規則。

### 0.1 必遵開發規則

#### Rule 1：解耦與架構（SPEC §0.1，憲法 Rule 1-7）

- **R1.1** `momentum/FeatureEngineering/preprocessing/` **禁止** 出現 `from api.*`。
  - 影響 Task：0.1, 0.3, 0.4, 1.1, 1.2, 2.1
  - 驗證：`grep -r "from api\." momentum/FeatureEngineering/preprocessing/` → 0 結果
- **R1.2** 跨 Domain 依賴必須走 Protocol；新 context 物件以 `@dataclass(frozen=True)` 傳入，不直接 `import` 對方 service。
  - 影響 Task：0.3（PreprocessingContext）、0.6（batch service 注入）
  - 範例：
    ```python
    @dataclass(frozen=True)
    class PreprocessingContext:
        symbol: str = "unknown"
        timeframe: str = "unknown"
        config_hash: str = ""
    ```
- **R1.3** `api/services/feature_factory_batch_service.py` 取得 `FeaturePreprocessor` 必須走 `momentum/factories.py`，不直接 `FeaturePreprocessor()`。
  - 影響 Task：0.6
- **R1.4** 新增環境變數統一在 `momentum/core/config.py` 解析，不可散落在多模組各自 `os.environ.get`。
  - 影響 Task：0.1, 0.2, 0.3, 0.6, 1.1, 2.1
- **R1.5** 新增/修改測試必須可單獨 `./venv/bin/pytest` 執行（不依賴 `run_api.py`）。
  - 影響 Task：所有測試任務

#### Rule 2：Logging（SPEC §0.2）

```python
from momentum.core.logging import get_logger
logger = get_logger(__name__)

logger.info(f"[L6.5] symbol={symbol} tf={tf} d_star_cache_hit={hit}/{total}")
logger.warning(f"[L6.5] FracDiff skip column={col} reason=high_nan ratio={ratio:.2%}")
logger.error(f"[L6.5] Fast ADF singular matrix col={col}, fallback to statsmodels", exc_info=True)
```

- **禁止**：在 per-column inner loop 內 `logger.info`，必須以 group/symbol summary。
- 所有 d_star cache hit/miss log 必須以 `[L6.5]` 或 `[d_star_cache]` 為前綴（可被 grep）。
- 影響 Task：所有 Task

#### Rule 3：Error Handling 與 FailureType 分類（SPEC §0.3）

```python
from enum import Enum

class FailureType(Enum):
    OOM = "oom"                  # 不可重試，必須降載
    SINGULAR_MATRIX = "singular" # Fast ADF 失敗，fallback statsmodels
    HIGH_NAN = "high_nan"        # 跳過 column，記 quality warning
    CONFIG_INVALID = "config"    # 不可重試
```

- Fast ADF 在 `np.linalg.LinAlgError` / 對角線 < 1e-12 / condition number > 1e10 時 fallback statsmodels。
- joblib worker 拋 OOM-like exception → batch service 降載 `concurrent_symbols=1` 並記錄。
- 影響 Task：0.6（batch OOM 降載）、1.1（joblib pickle/OOM）、2.1（singular matrix）

#### Rule 4：命名規範（SPEC §0.4）

- 環境變數一律前綴 `FFACT_`。
- d_star cache 檔名格式：`d_star_{SYMBOL}_{TIMEFRAME}_{config_hash[:12]}.json`。
- 新模組以 `_` 前綴標示 internal：`_d_star_cache.py`、`_non_stationary_cache.py`、`_fast_adf_numba.py`、`_slow_path_parallel.py`、`_hurst_prior.py`。
- ❌ 禁止用 `process()`, `do_stuff()`, `temp`, `df1`。
- 影響 Task：0.1, 0.3, 0.4, 0.6, 1.1, 1.2, 2.1

#### Rule 5：Type Hints（SPEC §0.5）

- 所有新函式必須有完整 type hints。
- Python 3.9 相容：用 `Optional[X]` / `Union[X, Y]`，**禁止** `X | Y`。
- 影響 Task：所有實作 Task

#### Rule 6：效能程式碼慣例（SPEC §0.7）

優先順序：**向量化 numpy ≥ Numba ≥ joblib loky（slow path only） ≥ ThreadPool（GIL 安全 Numba fast path） ≥ Python loop**。

- ❌ 不可用 ThreadPool 包 `statsmodels.adfuller`（GIL 鎖死）。
- ❌ 不可在 joblib worker 內傳整張 DataFrame；只傳 `Series.values` + `mmap_mode='r'`。
- 影響 Task：1.1, 2.1

#### Rule 7：向後相容 Profile-based Fallback（SPEC §0.8）

| Phase | Fallback 環境變數 | 預期行為 |
|-------|-----------------|---------|
| Phase 0 | `FFACT_L65_OPTIMIZATION_PROFILE=legacy` | 恢復全 layer fracdiff、precision 0.01；**不得** 恢復 legacy d_star shared cache |
| Phase 0 | `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2,L3,L4` | 恢復舊全 L 行為 |
| Phase 0 | `FFACT_FRACDIFF_PRECISION_OVERRIDE=0.01` | precision 切回 baseline |
| Phase 0 | `FFACT_DSTAR_CACHE_MIGRATE_LEGACY=1` | read-only migration / quarantine（不 direct hit） |
| Phase 1 | `FFACT_L65_SLOWPATH_PARALLEL=0` | 預設 OFF，回到 ThreadPool |
| Phase 2 | `FFACT_USE_FAST_ADF=0` | 預設 OFF，全部走 statsmodels |

- 每個 fallback 必須有測試證明：關閉該 Phase 後數值可回到對應 baseline，且不重新引入 cross-symbol cache 污染。

#### Rule 8：Git/Branch 慣例

- **僅在使用者明確要求建立 branch / commit 時適用**；一般 Agent 實作任務不得自行建立 branch、commit 或 push。
- 若使用者要求 branch：每個 Task 一個 branch：`feat/l65-task-{phase}-{n}-{slug}`。
- 若使用者要求 commit：commit message 前綴 `[L6.5]`，含 Task ID。
- 不可 `--no-verify`，不可 `git push --force`。

### 0.2 硬約束與驗收標準（C-OPT-1~6 + C1~5，SPEC §1.1）

| ID | 約束 | 驗收條件 | 驗證方式 | 是否 N/A |
|----|------|---------|---------|---------|
| C-OPT-1 | 跨 8/16/24/32GB tier 重複穩定 | **Dev Gate**：8GB Tier-A 連續 3 次無 OOM/SIGKILL；**Frozen Gate**：16/24/32GB 或 8GB full-width proxy 各 1 次無 OOM | `scripts/benchmark_l65.py --tier=8gb --repeat=3` + Frozen Gate report | 否 |
| C-OPT-2 | 多 symbol 不 OOM | 10 symbols × 2 tf Tier-A reduced 在 8GB 完成或可 resume；checkpoint 以 `(symbol, timeframe)` 粒度；available<4GB 拒絕新 symbol | T0.P2 + T0.B3 + `tests/api/test_feature_factory_batch_resume.py` | 否 |
| C-OPT-3 | 最高數據品質 | (a) Tier-A：合成 + ETHUSDT 1h 2000 rows fracdiff corr>0.99；(b) d_star isolation；(c) Fast ADF 一致率>99%；(d) L7 float16 roundtrip 全綠；**Frozen Gate**：完整 ETH/BTC 1h+12h corr>0.99（需 24GB+ 或 proxy） | T0.5, T0.11, T2.V1, golden 比對 | 否 |
| C-OPT-4 | Runtime target | **Dev Gate**：Phase0 ≤ 60min、Phase1 ≤ 30min、Phase2 ≤ 15min（short-window）；**Frozen Gate**：full-scale per PLAN §4 | T0.P1, T1.P1, T2.P1, T0.F1, T1.F1, T2.F1 | 否 |
| C-OPT-5 | 最小可行輸出 | L7 parquet 總大小相對 baseline ≤ ±5%；新 d_star JSON 每檔 ≤ 5MB | `scripts/compare_output_size.py` | 否 |
| C-OPT-6 | 不以刪特徵做最佳化 | feature column count、L3 rolling window list 與 baseline schema 一致 | Tier 1 schema diff（T0.1） | 否 |
| C1 | 既有 L6.5 / preprocessing 測試 100% pass | Task 0.0 inventory 全綠；不沿用未驗證固定數字 | `./venv/bin/pytest` 跑 `test_inventory.txt` | 否 |
| C2 | precision 0.01→0.02 fracdiff 偏離可控 | 兩 precision 下 fracdiff series corr > 0.999 | T0.4 | 否 |
| C3 | d_star cache atomic write 無 partial JSON | 模擬 multi-worker 並行寫入 100 次無 corrupt | T0.6 | 否 |
| C4 | Fast ADF threshold 強制 fallback | p-value ∈ [0.08, 0.12] 全數 fallback | T2.B2 | 否 |
| C5 | joblib worker 不傳整 DataFrame | code review + worker memory 監測 | Task 1.1 code review + T1.1 | 否 |

### 0.3 每 Phase 通用驗收流程（SPEC §1.2）

1. 執行 §0.4 Pre-Commit Checklist。
2. 執行 Task 0.0 產出的 `tests/golden/l65/test_inventory.txt`；新增測試所在目錄全綠。
3. 跑 `scripts/benchmark_l65.py --tier=8gb --symbols=ETHUSDT --tfs=1h --max-rows=2000`，比對 Tier 1+2 baseline。
4. 比對 golden：(a) Tier 1 schema diff 為空；(b) Tier 2A/2B fracdiff corr > 0.99、d_star isolation、L7 roundtrip 全綠。
5. 8GB tier 連續 3 次跑 short-window benchmark，記錄 peak RSS、wall time、cache hit rate。
6. 檢查 L7 輸出大小（C-OPT-5）。
7. **Frozen Gate**：取得 24GB+ 環境後補跑 Tier 3 full baseline；若無，跑 8GB full-width proxy 並標 accepted risk。**缺 Tier 3 / proxy 不阻塞 Phase 0→1 開發 Gate，但阻塞真正 Frozen**。

### 0.4 Pre-Commit Checklist（每個 Task 完成後，SPEC §0.9）

```
□ grep -r "from api\." momentum/FeatureEngineering/preprocessing/ → 0 結果
□ 所有新增/修改函式有完整 type hints（Python 3.9 相容，無 X | Y 語法）
□ 測試可獨立 `./venv/bin/pytest` 執行（不依賴 run_api.py）
□ Fallback profile/env var 可切回對應 baseline，且不重新啟用 legacy d_star shared cache
□ 8GB tier benchmark 通過（無 OOM、無 SIGKILL）
□ d_star cache atomic write（temp + rename），無 partial JSON
□ 任何新門檻有 PLAN 或 benchmark 來源
□ logging 不在 per-column inner loop 內
```

### 0.5 全域前置條件

- [x] Python 3.9 環境就緒；`./venv/bin/pytest --version` 可執行
- [x] `psutil`, `joblib`, `numba`, `statsmodels` 已安裝（在 `requirements.txt`）
- [x] `data_cache/feature_preprocessing/` 目錄存在且可寫
- [x] ETHUSDT 1h HDF5 在 `data_cache/feature_klines/kline_cache.h5` 內可讀（Tier 2B 需；2026-04-27 本機 `ETHUSDT/1h/data` 為 17,928 rows，Task 0.0 Tier 2B artifact 已用此資料來源產出）
- [x] Tier 1+2 Golden Output 由 Task 0.0 建立完成（後續 Task 才能比對）

### 0.6 不可違反最佳化原則（SPEC §0.0，**最高優先**）

優先順序：
1. 跨 8/16/24/32GB tier 重複穩定
2. 多 symbol 不 OOM、可降載、可 resume
3. 最高數據品質（不弱化 NaN/inf/float16/cross-symbol isolation gate）
4. 最短可行計算時間（**僅在前 3 項保證下**）
5. 最小可行輸出（不擴大 L7 size）
6. 符合量化金融業界經驗（López de Prado FracDiff、Hurst 僅作 prior）

**禁止以下捷徑**：刪除特徵、減少 feature breadth、縮減 rolling windows、跳過品質檢查、弱化 gate、跨 symbol 共用未隔離 cache、輸出檔案膨脹。

### 0.7 交付物 #3.5 — Adversarial Review Handoff

> 本節為外部 reviewer 的強制 handoff。任何後續 review 不得只看 Phase Gate 表，必須逐項回覆下列 open risks。若 reviewer 無法取得外部環境或參考實作，必須標 `Accepted Risk`，不得標 `PASS`。

| ID | 待外部審查項目 | TODO 位置 | Reviewer 必須判斷 | Frozen 前處理 |
|----|----------------|-----------|------------------|---------------|
| ARH-1 | **U1 Tier 3 baseline blocker**：無 24GB+ 環境前，所有 C-OPT-3 Tier-B 主張僅基於 short-window proxy | C-OPT-1/3/4、T0.P4/T0.F1、T1.F1、T2.F1 | short-window / full-width proxy 對 full-scale 品質與 RSS 的代表性是否可接受 | 未通過 Tier 3 full baseline 前，只能標 `Accepted Risk`，不可標完全 Frozen |
| ARH-2 | **Hurst R/S 估計實作（Task 1.2）**：TODO 使用 O(N) 簡化 R/S prior | Task 1.2、T1.4 | 與 Mansukhani Hurst R/S、DFA 在金融時序上的差異是否會系統性帶偏 d prior | T1.4 未過時，Task 1.2 不得合併；保留完整二分搜尋 |
| ARH-3 | **Fast ADF MacKinnon p-value 對齊（Task 2.1）**：`statsmodels.tsa.adfvalues.mackinnonp` 在 numba layer 外呼叫 | Task 2.1、T2.P2a | `mackinnonp` 外層呼叫是否能穩定 < 1ms，且不破壞 3-5ms/call 目標 | T2.P2a 未過時，不得宣稱 Fast ADF runtime target 達成 |
| ARH-4 | **U3 `FFACT_L65_SLOWPATH_PARALLEL` 預設值**：本 TODO 強制預設 OFF | Task 1.1、Phase 1 Gate | 8GB tier 連續 3 次 OOM-free 才考慮 ON 是否過於保守 | reviewer 可建議更積極策略，但預設 ON 前仍需 8GB 3-run gate |
| ARH-5 | **R16 多 symbol RSS 累積**：T0.P7 使用 `rss_after_gc_mb <= max(rss_before_item_mb + 1024, rss_peak_item_mb * 0.75)` | Task 0.6、T0.P7 | 此 sanity 公式是否能代表長跑記憶體回收健康度 | 若公式被判不合理，需改寫 T0.P7 並加入 process recycle / worker restart gate |

外部 reviewer 需在 review report 中逐項輸出：`Decision: Accept / Revise / Block`、理由、必要補測、是否影響 Frozen。缺任一項視為 handoff 未完成。

---

## 執行策略（最少批次計劃）

> 將 14 個 Task 依「輸入→輸出」依賴拓撲分組為**最少批次**。每批 = 一次 Agent prompt。

### 依賴拓撲總覽

```
Batch 1：Task 0.0（Golden Baseline + 測試 inventory）── 無前置依賴
    │
    ▼ Gate G1：T0.1 通過 + Tier 1+2 baseline + test_inventory.txt 存在
Batch 2：Task 0.1, 0.2, 0.4, 0.5（互不依賴的 Quick Wins）── 依賴 Batch 1 baseline
    │
    ▼ Gate G2：T0.2, T0.3, T0.4, T0.7, T0.8, T0.B1, T0.B2 通過
Batch 3：Task 0.3（d_star cache 重構，獨立但與 0.6 串接）── 依賴 Batch 1
    │
    ▼ Gate G3：T0.5, T0.6, T0.11, T0.12, T0.B5 通過
Batch 4：Task 0.6（Multi-Symbol Batch Hardening）── 依賴 Batch 3 (cache 隔離)
    │
    ▼ Gate G4：T0.9, T0.B3, T0.B4, T0.B6 通過
Batch 5：Task 0.7（Frontend Batch Panel）── 依賴 Batch 4 WebSocket schema
    │
    ▼ Gate G5：T0.10 通過 + Phase 0 → 1 Gate 全部達成（含 T0.P1-P3, P5, P7）
Batch 6：Task 1.1, 1.2（joblib slow-path + Hurst prior，互不依賴）── 依賴 Phase 0 全綠
    │
    ▼ Gate G6：T1.x + T1.B1-B3 + T1.P1, P3 通過 + Phase 1→2 Gate
Batch 7：Task 2.1, 2.2（Fast ADF + Gate，2.2 依賴 2.1）── 依賴 Phase 1 全綠
    │
    ▼ Gate G7：T2.1, T2.V1, T2.B1-B3, T2.P1-P2 通過 + Phase 2→3 Gate
Batch 8：Task 3.1, 3.2（Benchmark Suite + CI）── 依賴 Phase 2 全綠
    │
    ▼ Gate G8：T3.1, T3.2 通過 + Phase 3 Gate（CI nightly 7 天綠）
Batch 9（Frozen，需外部 24GB+ 或 proxy）：T0.F1 + T1.F1 + T2.F1
```

### 批次明細

| Batch | 包含項目 | 依賴前置 | 合併理由 | 預估規模 |
|-------|---------|---------|---------|---------|
| 1 | Task 0.0 | — | 唯一前置；新建 script + golden 檔，不改現有程式碼 | 中 |
| 2 | Task 0.1 + 0.2 + 0.4 + 0.5 | Batch 1 | 互不依賴：0.1 改 preprocessor layer filter、0.2 改 config、0.4 新增 cache、0.5 改前端文案；改不同函式或檔案 | 中 |
| 3 | Task 0.3 | Batch 1 | 改 cache schema + 新模組 + factory + migration script，獨立 Task；單獨 batch 降低 0.6 依賴錯誤風險 | 中 |
| 4 | Task 0.6 | Batch 3 | 依賴 0.3 的 cache 隔離保證才能展開多 symbol；單一大型重構 | 大（單 Task） |
| 5 | Task 0.7 | Batch 4 | 前端依賴 0.6 的 WebSocket event schema | 小 |
| 6 | Task 1.1 + 1.2 | Phase 0 全綠 | 互不依賴；都新增獨立模組（`_slow_path_parallel.py`、`_hurst_prior.py`）；驗收同 Gate | 中 |
| 7 | Task 2.1 + 2.2 | Phase 1 全綠 | 2.2 是 2.1 的驗證 gate，但 gate 撰寫不依賴 2.1 完成數值 → 可同 batch 完成 | 中 |
| 8 | Task 3.1 + 3.2 | Phase 2 全綠（或 Phase 1 接受後 skip Phase 2） | Benchmark + CI，純基礎設施 | 小 |
| 9 (Frozen) | T0.F1 + T1.F1 + T2.F1 | Phase 0/1/2 全綠 + 24GB+ 環境或 proxy | 跑全尺寸或 proxy gate | 大（純執行）|

### 批次間 Gate 檢查

| 轉換 | 必須通過的驗證 | 驗證命令 |
|------|--------------|---------|
| Batch 1 → 2 | T0.1（baseline + inventory 建立） | `./venv/bin/pytest tests -k l65_golden` 且 `tests/golden/l65/tier1_structure/column_inventory.json` 存在 |
| Batch 2 → 3 | T0.2, T0.3, T0.4, T0.7, T0.8, T0.B1, T0.B2 | `./venv/bin/pytest tests/feature_engineering/preprocessing -k "layer_filter or precision or non_stationary or unknown_layer or high_nan_no_adf"` + `npm run test -- PreprocessingPanel` |
| Batch 3 → 4 | T0.5, T0.6, T0.11, T0.12, T0.B5 | `./venv/bin/pytest tests/feature_engineering/preprocessing -k "d_star_isolation or atomic_write or stale_invalidation or legacy_migration_audit or cache_version_invalid"` |
| Batch 4 → 5 | T0.9, T0.B3, T0.B4, T0.B6 | `./venv/bin/pytest tests/api/test_feature_factory_batch_resume.py` |
| Batch 5 → 6 | Phase 0 → 1 Gate（T0.x 全綠 + T0.P1≤60min + T0.P2 不 OOM + L7 size≤5%） | `./venv/bin/pytest tests/feature_engineering tests/api -k l65` + `scripts/benchmark_l65.py --tier=8gb --max-rows=2000 --max-cols=500 --layers=L1,L2 --repeat=3` |
| Batch 6 → 7 | Phase 1 → 2 Gate（T1.x + T1.P1≤30min） | `./venv/bin/pytest tests/feature_engineering -k "slow_path_parallel or hurst_prior or nested_protection"` + `scripts/benchmark_l65.py --tier=8gb --phase=1 --max-rows=2000 --max-cols=500` |
| Batch 7 → 8 | Phase 2 → 3 Gate（T2.V1 通過 + T2.P1≤15min） | `./venv/bin/pytest tests/feature_engineering -k "fast_adf"` + `scripts/benchmark_l65.py --phase=2 --max-rows=2000 --max-cols=500` |
| Batch 8 → 9 | Phase 3 Gate（T3.x + CI nightly 7 天） | manual review GitHub Actions log |
| Batch 9 (Frozen) | T0.F1, T1.F1, T2.F1 | `scripts/benchmark_l65.py --tier=24gb --full` 或 `--tier=8gb --full-width-proxy` |

### 快速執行參考（複製貼上用）

**Batch 1**:
```
請執行以下 Task：Phase 0 全域前置檢查 + Task 0.0（建立 Golden Baseline Tier1+2 與測試清單）
完成後執行驗證：
  ./venv/bin/pytest --collect-only tests -q   # 產出 test_inventory.txt
  ./venv/bin/pytest tests -k l65_golden
  ls tests/golden/l65/tier1_structure/column_inventory.json
  ls tests/golden/l65/tier2_reduced/synthetic_baseline.parquet
  ls tests/golden/l65/test_inventory.txt
```

**Batch 2**:
```
前置已完成：Batch 1（Task 0.0；Tier1+2 baseline 與 test_inventory.txt 已存在）
請執行：Task 0.1（FracDiff Layer Filter）+ Task 0.2（precision 0.02 + cache version）+ Task 0.4（per-run non_stationary cache）+ Task 0.5（UI 文案）
完成後執行驗證：
  ./venv/bin/pytest tests/feature_engineering/preprocessing -k "layer_filter or precision or non_stationary or unknown_layer or high_nan_no_adf"
  cd frontend && npm run test -- PreprocessingPanel
```

**Batch 3**:
```
前置已完成：Batch 1, 2
請執行：Task 0.3（d_star Cache Key + Schema 修正 + atomic write + legacy migration + 注入 PreprocessingContext）
完成後執行驗證：
  ./venv/bin/pytest tests/feature_engineering/preprocessing -k "d_star_isolation or atomic_write or stale_invalidation or legacy_migration_audit or cache_version_invalid"
  python scripts/migrate_d_star_cache.py --dry-run
```

**Batch 4**:
```
前置已完成：Batch 1-3（cache 隔離已生效）
請執行：Task 0.6（Multi-Symbol Batch Hardening：concurrent_symbols tier table、RAM gate、checkpoint、resume endpoint）
完成後執行驗證：
  ./venv/bin/pytest tests/api/test_feature_factory_batch_resume.py
  ./venv/bin/pytest tests -k "ram_gate or checkpoint_failure or resume_not_found"
```

**Batch 5**:
```
前置已完成：Batch 1-4（resume API + WebSocket schema 已就緒）
請執行：Task 0.7（前端 Batch Panel + Per-Symbol Output + WebSocket 重連）
完成後執行 Phase 0 → 1 Gate 驗證：
  cd frontend && npm run test -- BatchProgressPanel
  ./venv/bin/pytest tests/feature_engineering tests/api -k l65
  scripts/benchmark_l65.py --tier=8gb --max-rows=2000 --max-cols=500 --layers=L1,L2 --repeat=3
  scripts/benchmark_l65.py --tier=8gb --multi --symbols=10 --tfs=1h,12h --max-rows=2000 --max-cols=500
```

**Batch 6**:
```
前置已完成：Phase 0 全綠（Batch 1-5 + Phase 0→1 Gate）
請執行：Task 1.1（joblib slow-path）+ Task 1.2（Hurst prior bounded search）
完成後執行驗證（Phase 1→2 Gate）：
  ./venv/bin/pytest tests/feature_engineering/preprocessing -k "slow_path_parallel or hurst_prior or nested_protection or pickle_fail or hurst_degenerate or short_series_bypass"
  scripts/benchmark_l65.py --tier=8gb --phase=1 --max-rows=2000 --max-cols=500
```

**Batch 7**:
```
前置已完成：Phase 1 全綠
請執行：Task 2.1（Numba Fast ADF）+ Task 2.2（1000+ 樣本 Gate）
完成後執行驗證（Phase 2→3 Gate）：
  ./venv/bin/pytest tests/feature_engineering/preprocessing -k "fast_adf"
  python -m benchmark.adf
  scripts/benchmark_l65.py --phase=2 --max-rows=2000 --max-cols=500
```

**Batch 8**:
```
前置已完成：Phase 2 全綠（或經評估 Skip Phase 2）
請執行：Task 3.1（Benchmark Suite 完整化）+ Task 3.2（GitHub Actions CI workflow）
完成後執行驗證：
  scripts/benchmark_l65.py --smoke
  manual review .github/workflows/l65_benchmark.yml CI 結果
```

**Batch 9（Frozen，需外部 24GB+ 或 8GB proxy）**:
```
前置已完成：Phase 0/1/2/3 全綠
請執行：T0.F1 + T1.F1 + T2.F1（Frozen Gate full-scale 或 full-width proxy）
驗證：scripts/benchmark_l65.py --tier=24gb --full   或   --tier=8gb --full-width-proxy
注意：proxy 通過僅可標 accepted risk，不可標完全 Frozen
```

---

## Phase 0 — Quick Wins + Multi-Symbol Hardening

### Phase 0 目標與驗收標準

> 在 8GB 開發機上通過 Tier-A reduced Gate（Phase 0 short-window ≤ 60 min），並補齊多 symbol RAM gate / resume，使 10 symbols × 2 tf reduced workload 在 8GB 不 OOM 且失敗可 resume；同時修復 d_star cache cross-symbol 污染、引入 layer filter 與 precision 微調等 Quick Wins。Frozen 目標延後至 Frozen Gate。

### Task 0.0 — 建立 Golden Baseline (Tier 1+2) 與測試清單

- [x] **SPEC ref**: Task 0.0（SPEC §2.1）
- [x] **目標**: 在 8GB MacBook M1 產出 Phase 0 開工前的 Tier 1（結構）+ Tier 2A（合成）+ Tier 2B（真實 short-window）baseline，以及實測既有 L6.5 / preprocessing 測試清單。
- [x] **輸入**:
  - 當前 main commit 的 `momentum/` 程式碼（Phase 0 開工前最後 commit）
  - `data_cache/feature_klines/kline_cache.h5` 內 ETHUSDT 1h（Tier 2B 需，缺則該層標 blocked）
  - `synthetic_l65_dataset` fixture（如尚未建立則於本 Task 一併建）
- [x] **輸出**:
  - `scripts/build_l65_golden.py`（新建，CLI tool）
  - `tests/golden/l65/tier1_structure/column_inventory.json`（schema：`[{name: str, dtype: str, layer: str, source: str}]`）
  - `tests/golden/l65/tier1_structure/schema_hash.txt`（SHA-256 of column_inventory）
  - `tests/golden/l65/tier2_reduced/synthetic_baseline.parquet`（pd.DataFrame, 1000 rows × 100 cols）
  - `tests/golden/l65/tier2_reduced/d_star_synthetic.json`（Dict[str, float]）
  - `tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.parquet`（pd.DataFrame, 1500-2000 rows × ~500 cols；真實市場資料衍生 artifact，預設僅本機產生，不自動 commit）
  - `tests/golden/l65/tier2_reduced/d_star_ETHUSDT_1h_2000rows.json`（預設僅本機產生；若需進版控，須使用者明確批准）
  - `tests/golden/l65/test_inventory.txt`（每行 `<nodeid>`，由 `pytest --collect-only` 產出）
  - `tests/conftest.py` 新增 `synthetic_l65_dataset` fixture（若尚未存在）
- [x] **實作要點**:
  1. CLI 介面（pseudocode）：
     ```python
     # scripts/build_l65_golden.py
     def main():
         parser = argparse.ArgumentParser()
         parser.add_argument("--tier", choices=["1","2a","2b","3"], required=True)
         parser.add_argument("--symbol", default="ETHUSDT")
         parser.add_argument("--tf", default="1h")
         parser.add_argument("--max-rows", type=int, default=2000)
         parser.add_argument("--max-cols", type=int, default=500)
         args = parser.parse_args()
         _ram_gate(min_available_gb=4)  # abort if < 4GB
         if args.tier == "1": build_tier1_structure()
         elif args.tier == "2a": build_tier2_synthetic()
         elif args.tier == "2b": build_tier2_real_shortwindow(args)
         elif args.tier == "3": raise SystemExit("Tier 3 不支援 8GB；需 24GB+ 環境")
     ```
  2. **Tier 1**：跑 Layer 0~5（**不跑 L6.5**）→ 取所有 column 名/dtype/layer/source；序列化為 JSON + SHA-256 hash。8GB 5-15 分鐘。
  3. **Tier 2A**：用 `synthetic_l65_dataset` fixture（1000 rows × 100 cols，stationary_ratio=0.6）跑 L6.5 全開（含 fracdiff）→ 寫 parquet + d_star JSON。8GB 5-10 分鐘。
  4. **Tier 2B**：讀 ETHUSDT 1h 最近 2000 rows，再用 `_select_l1_l2_columns(allow_list_size=500)` 預選欄位 → 跑 L6.5 全開 → 寫 parquet + d_star JSON。8GB 30-60 分鐘。
  5. **Test inventory**：`subprocess.run(["./venv/bin/pytest", "--collect-only", "tests", "-q"])` → 過濾 nodeid 含 `l65|preprocess|feature_preprocessor|fracdiff|adf|d_star` → 寫入 `test_inventory.txt`。若 venv 無 pytest，**禁止** 把 0 tests 視為通過，需在 stdout 印 `BLOCKER: pytest not found` 並 `exit 2`。
  6. 函式簽名草案：
     ```python
     def _ram_gate(min_available_gb: float, label: str) -> bool: ...
     def _estimate_reduced_workload_ram_gate(rows: int, cols: int) -> float: ...
     def build_tier1_structure(out_dir: Path) -> None: ...
     def build_tier2_synthetic(out_dir: Path) -> None: ...
     def build_tier2_real_shortwindow(symbol: str, tf: str, max_rows: int, max_cols: int, out_dir: Path) -> None: ...
     def collect_existing_l65_tests(out_path: Path) -> int: ...   # returns nodeid count, exit 2 if blocker
     ```
  7. Edge cases：
     - **(a) 跑前 RAM 不足**：Task 0.0 reduced workload 不使用固定 `available >= 4GB`，因 8GB macOS 開機後常態可能低於 4GB；改用 `max(1GB, rows × cols × float64 × 128)` 並上限 4GB 的 workload-aware gate。完整/多 symbol gate 仍保留更嚴格門檻。
     - **(b) Tier 2B 真實資料缺失**：`data_cache/feature_klines/kline_cache.h5` 不存在或 ETHUSDT 1h key 缺 → log warning + 寫 `tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.BLOCKED`，繼續其他 tier。
     - **(c) atomic write**：所有輸出檔先寫 `.tmp` → `os.rename`；任何中途失敗則刪 `.tmp` 不留 partial。
     - **(d) Tier 2B 輸出 > 100MB**：不得自動 `git lfs track` 或 staging；改寫入本機 artifact 目錄並產生 manifest/checksum。只有使用者明確批准時才可加入 Git LFS。
- [x] **修改檔案**:
  - `scripts/build_l65_golden.py` → `main()`, `build_tier1_structure()`, `build_tier2_synthetic()`, `build_tier2_real_shortwindow()`, `collect_existing_l65_tests()`, `_ram_gate()`
  - `tests/conftest.py` → 新增 `synthetic_l65_dataset` fixture（若不存在）
  - `tests/golden/l65/{tier1_structure,tier2_reduced}/`（新目錄）
- [x] **不可做**:
  - ❌ 不試圖在 8GB 跑 Tier 3（必爆 RAM）
  - ❌ 不修改 `momentum/` 任何程式碼
  - ❌ 不寫部分完整 baseline 檔案
  - ❌ 不沿用 PLAN §7 引用的「381」固定數字；inventory 必須來自實測
- [x] **風險緩解**: R1（Golden baseline 缺失）— Tier 1+2 充分涵蓋 Phase 0/1 關鍵路徑；Tier 3 走 U1
- [x] **驗證**: T0.1（基本檔案/schema/rows/cols 存在性）；缺真實 HDF5 時 Gate 狀態為 `blocked-not-pass`，不算通過
  - 2026-04-27 本機狀態：Tier 1、Tier 2A、Tier 2B、test inventory 已產出並通過；Tier 2B 使用 `data_cache/feature_klines/kline_cache.h5`（ETHUSDT 1h 共 17,928 rows），在 reduced workload gate 下以 available RAM 1.18GB >= required 1.06GB 成功產出 `ETHUSDT_1h_2000rows.parquet`（2000 rows × 34 cols）與 `d_star_ETHUSDT_1h_2000rows.json`（13 entries），且 `.BLOCKED` 已移除。

### Task 0.1 — FracDiff Apply-To-Layer Filter

- [x] **SPEC ref**: Task 0.1（SPEC §2.1）
- [x] **目標**: 在 `optimized` profile 下預設 `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2`；`legacy` profile 可恢復全 layer fracdiff，但保留 winsor/rank/zscore/gaussian。
- [x] **輸入**:
  - 環境變數 `FFACT_L65_OPTIMIZATION_PROFILE`、`FFACT_FRACDIFF_APPLY_TO_LAYERS`
  - feature column 名（用 layer parser 解析）
- [x] **輸出**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` 內 `_apply_fractional_differencing()` 對 non-target layer 跳過 fracdiff
  - `momentum/core/config.py` 新增 `FFACT_FRACDIFF_APPLY_TO_LAYERS` parser → 回傳 `FrozenSet[str]`
  - 新增 helper `_is_fracdiff_target_layer()`（同檔內 module-level）
- [x] **實作要點**:
  1. Layer parser 規則：欄位名 `L1_xxx`, `L2_xxx`（即第一段以 `L\d+_` 開頭）對應 layer。實作前讀 repo memory `/memories/repo/feature_name_parser.md` 確認解析方式。
  2. Pseudocode：
     ```python
     def _is_fracdiff_target_layer(column: str, allowed_layers: FrozenSet[str]) -> bool:
         if "ALL" in allowed_layers:
             return True
         m = re.match(r"^(L\d+)_", column)
         if not m:
             logger.warning(f"[L6.5] Layer parse failed col={column}, treat as non-target")
             return False
         return m.group(1) in allowed_layers

     # 在 _apply_fractional_differencing(df) 內：
     allowed = config.get_fracdiff_layers()  # 從 momentum.core.config 讀 FFACT_FRACDIFF_APPLY_TO_LAYERS
     for col in fracdiff_candidates:
         if not _is_fracdiff_target_layer(col, allowed):
             continue
         # ... 原邏輯
     ```
  3. Profile 預設：
     - `optimized`（預設） → `L1,L2`
     - `legacy` → `L1,L2,L3,L4`（等同舊行為）
     - `FFACT_FRACDIFF_APPLY_TO_LAYERS=ALL` → 等同 legacy
  4. 函式簽名：
     ```python
     def _is_fracdiff_target_layer(
         column: str,
         allowed_layers: FrozenSet[str],
     ) -> bool: ...
     ```
  5. Edge cases：
     - **(a) 無法 parse layer 的 column**：log warning + 視為非 target。
     - **(b) `FFACT_FRACDIFF_APPLY_TO_LAYERS=ALL`**：等同 legacy 行為。
     - **(c) Empty allow list（空字串）**：視為 `optimized` 預設 `L1,L2`，並 log warning。
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_apply_fractional_differencing()`（line ~979）
  - `momentum/core/config.py` → 新增 `get_fracdiff_layers() -> FrozenSet[str]`
  - 新增測試 `tests/feature_engineering/preprocessing/test_layer_filter.py`
- [x] **不可做**:
  - ❌ 不在 UI 開放 L3+ 任意組合（只允許 expert env override）
  - ❌ 不影響 winsor/rank/zscore/gaussian transform
- [x] **風險緩解**: R2（業界假設失效）— Q1 fallback
- [x] **驗證**: T0.2, T0.3, T0.B1

### Task 0.2 — precision 0.01 → 0.02 + cache version bump

- [x] **SPEC ref**: Task 0.2（SPEC §2.1）
- [x] **目標**: `_find_min_d` 二分搜尋從 7 次降至 6 次，bump d_star cache version 從 `v1` → `v2`，舊 cache 自動失效。
- [x] **輸入**: `config/scan_config.yaml` 之 `fractional_differencing.precision`、`FFACT_FRACDIFF_PRECISION_OVERRIDE` env var
- [x] **輸出**:
  - `config/scan_config.yaml` 改 `precision: 0.02`（optimized 預設）
  - d_star cache schema 增加 `cache_version: "v2"` 欄位
  - `_find_min_d` 在計算前用 config helper 取得 `precision_override`，再決定 `effective_precision`
- [x] **實作要點**:
  1. Pseudocode：
     ```python
     from momentum.core.config import get_fracdiff_precision_override

     precision_override = get_fracdiff_precision_override()
     effective_precision = (
       precision_override if precision_override is not None else self.config["precision"]
     )
     ```
  2. cache schema bump：`_d_star_cache.py`（Task 0.3 建立）內 `CACHE_VERSION = "v2"`，read 時若 `entry["cache_version"] != "v2"` → cache miss + INFO log。
  3. 函式簽名：
     ```python
     # 影響的呼叫者
     def _find_min_d(
         self,
         series: pd.Series,
         *,
         precision: Optional[float] = None,  # 新增可選參數，None 則讀 config
         ...
     ) -> float: ...
     ```
  4. Edge cases：
     - **(a) 使用者自行調 precision**：cache key 含 precision（透過 config_hash），自動隔離。
     - **(b) cache 失效**：log 一次 INFO `[L6.5] cache_version mismatch, rebuild`，避免在 inner loop log。
- [x] **修改檔案**:
  - `config/scan_config.yaml` → `fractional_differencing.precision: 0.02`
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_find_min_d()`（line ~1353）
  - `momentum/core/config.py` → `get_fracdiff_precision() -> float`
  - `momentum/FeatureEngineering/preprocessing/_d_star_cache.py` → `CACHE_VERSION = "v2"`（依賴 Task 0.3）
  - 新增測試 `tests/feature_engineering/preprocessing/test_precision_corr.py`
- [x] **不可做**:
  - ❌ 不改變 `_find_min_d` 之 ADF threshold、weight_threshold 等其他參數
- [x] **風險緩解**: R3（精度偏離）— Q3 fallback（env override 切回 0.01）
- [x] **驗證**: T0.4, C2
  - 2026-04-27 Batch 2 範圍說明：已在既有 d_star cache load/save helper 內實作 `cache_version: "v2"`、precision mismatch 失效與 atomic replace；Task 0.3 的 `_d_star_cache.py` / context / migration 架構仍保留為獨立任務，未在本批擴展。

### Task 0.3 — d_star Cache Key 與 Schema 修正

- [x] **SPEC ref**: Task 0.3（SPEC §2.1）
- [x] **目標**: cache key 從寫死 `("default","default")` 改為 `(symbol, timeframe, config_hash)`；引入 `PreprocessingContext` dataclass + `data_fingerprint` 防 stale；atomic write；legacy quarantine/migration audit。
- [x] **輸入**:
  - 既有 cache 檔（legacy `default/default` JSON）
  - `FeaturePreprocessor` 構造時可選 `PreprocessingContext`
  - HDF5 / parquet metadata（用於 data_fingerprint 計算）
- [x] **輸出**:
  - 新模組 `momentum/FeatureEngineering/preprocessing/_d_star_cache.py`：`DStarCache` 類別 + `PreprocessingContext` dataclass
  - 修改 `feature_preprocessor.py`：建構接 `Optional[PreprocessingContext]`
  - 修改 `momentum/FeatureEngineering/feature_factory.py` → `_layer6_5_preprocessing()` 建立 context
  - 修改 `momentum/factories.py` → `create_feature_preprocessor(context: PreprocessingContext)`
  - 新增 `scripts/migrate_d_star_cache.py`（read-only quarantine + audit JSONL）
  - cache 路徑：`data_cache/feature_preprocessing/d_star_{SYMBOL}_{TIMEFRAME}_{config_hash[:12]}.json`
  - audit log：`data_cache/feature_preprocessing/d_star_migration_audit.jsonl`
- [x] **實作要點**:
  1. Dataclass：
     ```python
     @dataclass(frozen=True)
     class PreprocessingContext:
         symbol: str = "unknown"
         timeframe: str = "unknown"
         config_hash: str = ""
         data_fingerprint: str = ""
         feature_schema_hash: str = ""
         time_range: Optional[Tuple[int, int]] = None
         row_count: int = 0
         source_data_version: str = ""

     CACHE_VERSION = "v2"

     class DStarCache:
         def __init__(self, context: PreprocessingContext, cache_dir: Path) -> None:
             self._ctx = context
             self._dir = cache_dir
             self._path = cache_dir / f"d_star_{context.symbol}_{context.timeframe}_{context.config_hash[:12]}.json"
             self._dirty = False
             self._entries: Dict[str, Dict] = self._load_or_init()

         def get(self, column: str) -> Optional[float]:
             if self._ctx.symbol == "unknown":  # context unknown → cache disabled
                 return None
             entry = self._entries.get(column)
             if not entry: return None
             if entry.get("input_fingerprint") != self._ctx.data_fingerprint:
                 return None  # stale
             return entry.get("d_star")

         def set(self, column: str, d_star: float) -> None:
             self._entries[column] = {
                 "d_star": d_star,
                 "input_fingerprint": self._ctx.data_fingerprint,
                 "computed_at": datetime.utcnow().isoformat(),
             }
             self._dirty = True

         def flush_atomic(self) -> None:
             if not self._dirty: return
             tmp = self._path.with_suffix(".tmp")
             payload = {
                 "cache_version": CACHE_VERSION,
                 "symbol": self._ctx.symbol,
                 "timeframe": self._ctx.timeframe,
                 "config_hash": self._ctx.config_hash,
                 "adf_threshold": ..., "precision": ..., "max_lag": ...,
                 "weight_threshold": ..., "adf_engine_version": ...,
                 "data_fingerprint": self._ctx.data_fingerprint,
                 "feature_schema_hash": self._ctx.feature_schema_hash,
                 "time_range": list(self._ctx.time_range or []),
                 "row_count": self._ctx.row_count,
                 "sample_size": ..., "nan_policy": ...,
                 "source_data_version": self._ctx.source_data_version,
                 "entries": self._entries,
             }
             tmp.write_text(json.dumps(payload))
             os.rename(tmp, self._path)  # POSIX atomic
             self._dirty = False
     ```
  2. data_fingerprint 計算（deterministic）：
     ```python
     def compute_data_fingerprint(df: pd.DataFrame, hdf5_meta: Optional[Dict]) -> Tuple[str, bool]:
         """Returns (fingerprint, weak)."""
         # 優先用 HDF5 metadata
         if hdf5_meta and all(k in hdf5_meta for k in ("symbol","timeframe","start_ts","end_ts","row_count","schema_hash","last_updated")):
             return sha256(stable_json(hdf5_meta)).hexdigest()[:32], False
         # 否則用 dataframe 特徵
         summary = {
             "dtype": str(df.dtypes.to_dict()),
             "shape": df.shape,
             "row_count": len(df),
             "col_count": len(df.columns),
             "nan_summary": df.isna().sum().to_dict(),
             "first_idx": str(df.index[0]) if len(df) else "",
             "last_idx": str(df.index[-1]) if len(df) else "",
             "value_samples": [df.iloc[int(p*len(df))].tolist() for p in (0,0.25,0.5,0.75,0.99)],
             "deterministic_sample": df.sort_index().iloc[::max(1,len(df)//1024)].head(1024).values.tobytes().hex()[:64],
         }
         weak = "first_idx" not in summary or not summary["first_idx"]
         return sha256(stable_json(summary)).hexdigest()[:32], weak
     ```
     - 若 weak → cache 只能在同一 process run 內 hit，不可跨 run hit。
  3. config_hash 必須涵蓋：fracdiff config、precision、threshold、max_lag、weight_threshold、sample_size、nan_policy、apply_to_layers、adf_engine_version。任一不同 → cache miss。
  4. Atomic write：`.tmp → os.rename`（POSIX atomic on same fs）。
  5. Legacy migration script（`scripts/migrate_d_star_cache.py`）：
     ```python
     # 對所有 legacy `default/default` cache 檔：
     #   - 讀取 → 嘗試從檔內 metadata 推 (symbol, timeframe, config_hash)
     #   - 推得到 → 寫到新 path（migrated）
     #   - 推不到 → 移到 quarantine 目錄（quarantined）
     # 每筆寫入 d_star_migration_audit.jsonl：
     #   {old_path, new_path, decision, reason, timestamp, entry_count, config_hash, data_fingerprint_status}
     ```
  6. 函式簽名：
     ```python
     class FeaturePreprocessor:
         def __init__(self, config: Dict, context: Optional[PreprocessingContext] = None) -> None: ...
     # momentum/factories.py
     def create_feature_preprocessor(
         config: Dict,
         *,
         context: Optional[PreprocessingContext] = None,
     ) -> FeaturePreprocessor: ...
     ```
  7. Edge cases：
     - **(a) 多 worker 並行寫**：atomic rename 保證不 partial。
     - **(b) JSON parse 失敗**：log warning + cache miss + 重建。
     - **(c) schema_hash / data_fingerprint mismatch**：cache miss + WARN log（一次 per run）。
     - **(d) context unknown（unit test 直接構造）**：cache disabled + log one warning per instance。
     - **(e) weak fingerprint**：標記 `cache status=weak_fingerprint`，禁止跨 run hit。
- [x] **修改檔案**:
  - 新增 `momentum/FeatureEngineering/preprocessing/_d_star_cache.py`
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 構造 + `_find_min_d`（line ~1353）+ cache lookup（line ~1394）
  - `momentum/FeatureEngineering/feature_factory.py` → `_layer6_5_preprocessing()` 建立 `PreprocessingContext`
  - `momentum/factories.py` → 新增 `create_feature_preprocessor()`
  - 新增 `scripts/migrate_d_star_cache.py`
  - 新增測試：`test_d_star_isolation.py`, `test_d_star_atomic_write.py`, `test_d_star_stale_invalidation.py`, `test_d_star_legacy_migration_audit.py`, `test_cache_version_invalid.py`
- [x] **不可做**:
  - ❌ 不允許 fallback 到 `("default","default")` 寫入新 cache
  - ❌ 舊 cache 只讀不寫
  - ❌ 不在 schema 缺欄時硬要 hit
- [x] **風險緩解**: R4（cross-symbol 污染）、R15（fingerprint 過弱）
- [x] **驗證**: T0.5, T0.6, T0.11, T0.12, T0.B5, C3

### Task 0.4 — per-run non_stationary classification cache

- [x] **SPEC ref**: Task 0.4（SPEC §2.1）
- [x] **目標**: 同一 run 內 FracDiff 與 ADF 共用 non_stationary 判定結果，避免重複 ADF。
- [x] **輸入**: `(column, adf_threshold, sample_size, nan_policy, input_fingerprint)`，per-instance lifetime
- [x] **輸出**:
  - 新模組 `momentum/FeatureEngineering/preprocessing/_non_stationary_cache.py`
  - 修改 `feature_preprocessor.py` → `_get_non_stationary_columns()`、`_select_columns()` 共用 cache
- [x] **實作要點**:
  1. Pseudocode：
     ```python
     class NonStationaryCache:
         def __init__(self) -> None:
             self._cache: Dict[Tuple, bool] = {}

         def make_key(self, column: str, threshold: float, sample_size: int, nan_policy: str, series: np.ndarray) -> Tuple:
             fp_input = {
                 "dtype": str(series.dtype),
                 "shape": series.shape,
                 "nan_count": int(np.isnan(series).sum()) if series.dtype.kind == "f" else 0,
                 "first_valid": float(series[~np.isnan(series)][0]) if series.size else 0.0,
                 "last_valid": float(series[~np.isnan(series)][-1]) if series.size else 0.0,
                 "value_digest": hashlib.sha1(series.tobytes()).hexdigest()[:16],
             }
             input_fingerprint = hashlib.sha1(stable_json(fp_input).encode()).hexdigest()[:16]
             return (column, threshold, sample_size, nan_policy, input_fingerprint)

         def get(self, key) -> Optional[bool]: return self._cache.get(key)
         def set(self, key, is_non_stationary: bool) -> None: self._cache[key] = is_non_stationary
     ```
  2. 在 `_get_non_stationary_columns()` 與 `_select_columns()` 兩處使用同一 instance。
  3. **僅 per-run 有效**（FeaturePreprocessor lifecycle），絕不寫磁碟。
  4. 函式簽名：
     ```python
     class NonStationaryCache:
         def make_key(self, column: str, threshold: float, sample_size: int, nan_policy: str, series: np.ndarray) -> Tuple: ...
         def get(self, key: Tuple) -> Optional[bool]: ...
         def set(self, key: Tuple, is_non_stationary: bool) -> None: ...
     ```
  5. Edge cases：
     - **(a) cache 命中 → 跳過 ADF**：mock test 確認 `adfuller.call_count == 1`。
     - **(b) cache miss → 跑 ADF 後寫入**。
     - **(c) 不同 symbol 為不同 FeaturePreprocessor instance**：天然隔離。
     - **(d) series 含 NaN**：fingerprint 包含 NaN count，避免假命中。
- [x] **修改檔案**:
  - 新增 `momentum/FeatureEngineering/preprocessing/_non_stationary_cache.py`
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_get_non_stationary_columns()`（line ~1276）、`_select_columns()`（line ~1267）
  - 新增測試 `tests/feature_engineering/preprocessing/test_non_stationary_cache.py`
- [x] **不可做**:
  - ❌ 不寫磁碟（避免 cross-run 污染）
  - ❌ 不用裸 `series.tobytes()` 作 fingerprint（必須含 dtype/shape/NaN summary）
- [x] **風險緩解**: Q6（cross-symbol 統計差異）— per-instance 自動隔離
- [x] **驗證**: T0.7, T0.B2

### Task 0.5 — UI 文案修正（FracDiff/ADF 警告）

- [x] **SPEC ref**: Task 0.5（SPEC §2.1）
- [x] **目標**: 修正 PreprocessingPanel 文案，避免使用者誤期 ADF 為 FracDiff fallback；新增 8GB 全開估時警告。
- [x] **輸入**:
  - 現有 [PreprocessingPanel.tsx](frontend/src/components/feature-factory/PreprocessingPanel.tsx)（U4：開工前先讀 + diff）
  - SPEC PLAN §3.6（兩段文案）+ PLAN §4 Tier 4 估時
- [x] **輸出**:
  - 修改後 React component
  - 新增 Storybook / unit test snapshot
- [x] **實作要點**:
  1. 開工第一步：`read_file` 讀現有 panel（U4），記錄當前文案，再 diff。
  2. 顯示邏輯（pseudocode）：
     ```tsx
     {fracdiffEnabled && adfEnabled && (
       <Alert variant="warning" className="bg-yellow-50 border-yellow-200">
         <p>{PLAN_3_6_PARA_1 /* "ADF 不作為 FracDiff 的 NaN fallback..." */}</p>
       </Alert>
     )}
     {fracdiffEnabled && (
       <Alert variant="warning" className="bg-yellow-50 border-yellow-200">
         <p>{PLAN_3_6_PARA_2 /* "L6.5 最慢子模組..." */}</p>
       </Alert>
     )}
     {fracdiffEnabled && allLayersEnabled && (
       <Alert variant="warning" className="bg-yellow-50 border-yellow-200">
         <p>「8GB 機預估 18-20 小時」</p>
       </Alert>
     )}
     ```
  3. 文案常數抽取到同檔頂層 `const PREPROCESSING_WARNINGS = { ... }`，方便 i18n 後續擴充。
  4. Edge cases：
     - **(a) 文案僅顯示，不阻擋送出**：警告為 `Alert` 而非 modal。
     - **(b) 警告等級色彩**：`bg-yellow-50 border-yellow-200`（黃色）。
     - **(c) 文案 i18n 預留**：常數放頂層，未來可換 i18n key。
- [x] **修改檔案**:
  - `frontend/src/components/feature-factory/PreprocessingPanel.tsx`
  - 新增測試 `frontend/src/components/feature-factory/__tests__/PreprocessingPanel.test.tsx`（snapshot）
- [x] **不可做**:
  - ❌ 不修改後端行為
  - ❌ 不阻擋使用者操作
  - ❌ 不寫死 symbol 或時間數字到 component（用 const）
- [x] **風險緩解**: R14（UI 估時警告過時）— Phase 0 完成後同步更新
- [x] **驗證**: T0.8

### Task 0.6 — Multi-Symbol Batch Hardening

- [ ] **SPEC ref**: Task 0.6（SPEC §2.1）
- [ ] **目標**: 多 symbol 任務不 OOM，可 resume。引入 RAM gate、tier-aware concurrent_symbols、checkpoint 與 resume API。
- [ ] **輸入**:
  - `psutil.virtual_memory()`（每次新 symbol 啟動前檢查）
  - 環境變數 `FFACT_CONCURRENT_SYMBOLS_OVERRIDE`
  - 既有 batch request payload
- [ ] **輸出**:
  - 修改後 `feature_factory_batch_service.py`：class-level lock、tier table、RAM gate、checkpoint、`gc.collect()` per item
  - 修改 `hardware_utils.py`：`get_tier_concurrent_symbols(tier_gb: int) -> int`
  - 新增 `POST /api/v1/features/batch/{batch_id}/resume` endpoint
  - 新增 checkpoint schema：`data_cache/feature_preprocessing/batch_state_{batch_id}.json`
  - WebSocket event schema 擴充
- [ ] **實作要點**:
  1. **Class-level lock**：
     ```python
     class FeatureFactoryBatchService:
         _heavy_batch_lock = asyncio.Lock()  # class-level，整個 process 一個
         async def execute_batch(self, request):
             async with self._heavy_batch_lock:
                 await self._execute_with_checkpoint(request)
     ```
  2. **Tier table**（`hardware_utils.py`）：
     ```python
     from momentum.core.config import get_concurrent_symbols_override

     TIER_CONCURRENT_SYMBOLS = {8: 1, 16: 1, 24: 2, 32: 3}
     def get_tier_concurrent_symbols(tier_gb: int) -> int:
         override = get_concurrent_symbols_override()
         if override is not None:
             return override
         return TIER_CONCURRENT_SYMBOLS.get(tier_gb, 1)
     ```
  3. **RAM gate**：每個 `(symbol, tf)` 啟動前 `if psutil.virtual_memory().available < 4 * 1024**3: raise HTTPException(429, "RAM gate")`。
  4. **Checkpoint schema**：
     ```python
     {
         "batch_id": str,
         "request_hash": str,
         "config_hash": str,
         "started_at": iso8601,
         "last_updated_at": iso8601,
         "completed_items": [{"symbol": str, "timeframe": str, "output_paths": [str], "rss_peak_item_mb": int, "rss_after_gc_mb": int}],
         "failed_items": [{"symbol": str, "timeframe": str, "reason": str, "failure_type": str}],
         "queued_items": [{"symbol": str, "timeframe": str}],
     }
     ```
     - 每完成一個 `(symbol, tf)` 寫入；atomic rename。
  5. **Per-item GC + memory tracking**：
     ```python
     for sym, tf in items:
         rss_before = psutil.Process().memory_info().rss
         peak = rss_before
         try:
             output_paths = await self._process_one(sym, tf)
             peak = max(peak, psutil.Process().memory_info().rss)
         finally:
             gc.collect()
             rss_after = psutil.Process().memory_info().rss
         self._update_checkpoint(sym, tf, output_paths, peak, rss_after)
         await ws.send_event({"current_symbol": sym, "current_timeframe": tf,
                              "rss_before_item_mb": rss_before//1024**2,
                              "rss_peak_item_mb": peak//1024**2,
                              "rss_after_gc_mb": rss_after//1024**2})
     ```
     - T0.P7 公式是 **memory-sanity heuristic**，不是 no-OOM 證明：
       `rss_after_gc_mb <= max(rss_before_item_mb + 1024, rss_peak_item_mb * 0.75)`。
       含義：允許每 item 最多 1GB 合理常駐成長，或要求 peak 後至少釋放約 25%。
     - 若任一 item 公式失敗：checkpoint 標 `memory_sanity_failed=true`，下一 item 前強制 process recycle / worker restart（或降載 `concurrent_symbols=1`），且 Phase Gate 不得通過直到 reviewer 重新判斷 ARH-5。
     - 同時保留 20 items RSS 累積門檻：總體 `rss_after_gc_mb` 不得單調累積超過 1.5GB；此門檻與單 item 公式任一失敗都算 T0.P7 fail。
  6. **Resume endpoint**：
     ```python
     # api/routes/feature_factory.py
     @router.post("/batch/{batch_id}/resume", response_model=BatchResumeResponse)
     async def resume_batch(batch_id: str):
         ckpt = load_checkpoint(batch_id)
         if not ckpt: raise HTTPException(404, "batch not found")
         skipped = ckpt["completed_items"]
         queued = ckpt["queued_items"]
         await service.execute_resume(ckpt)
         return BatchResumeResponse(batch_id=batch_id, resumed_from=ckpt["last_updated_at"],
                                    skipped_items=len(skipped), queued_items=len(queued), status="running")
     ```
  7. **巢狀防護**：透過 `momentum.core.config.get_batch_nested_enabled()` 讀 `FFACT_BATCH_NESTED`；若已是 1 → log warning + 強制 `concurrent_symbols=1`。同時由 batch service 在子層執行 context 明確注入 nested flag（`FFACT_BATCH_NESTED=1`），但讀取集中在 config helper，不在 service 內散落 `os.environ.get`。
  8. 函式簽名：
     ```python
     async def execute_batch(self, request: BatchRequest) -> BatchExecuteResponse: ...
     async def execute_resume(self, ckpt: Dict) -> None: ...
     def _update_checkpoint(self, sym: str, tf: str, output_paths: List[str], peak_rss: int, after_gc_rss: int) -> None: ...
     def _ram_gate(self, min_available_gb: float = 4.0) -> None: ...  # raises HTTPException(429)
     def get_tier_concurrent_symbols(tier_gb: int) -> int: ...
     ```
  9. Edge cases：
     - **(a) checkpoint 寫入失敗**：log error 但任務不終止（避免 disk full 殺整 batch）。
     - **(b) resume 找不到 batch_id**：回傳 404。
     - **(c) 同一 symbol 重複入隊**：去重，並 log warning。
     - **(d) class-level lock 已被佔用**：第二個 batch 立即回 429 + Retry-After。
- [ ] **修改檔案**:
  - `api/services/feature_factory_batch_service.py` → 整體重構
  - `momentum/FeatureEngineering/utils/hardware_utils.py` → 新增 `get_tier_concurrent_symbols()`、`get_current_tier_gb()`
  - `api/routes/feature_factory.py` → 新增 `POST /batch/{batch_id}/resume`
  - `api/models/feature_factory.py`（或對應 model 檔）→ 新增 `BatchResumeResponse` Pydantic model
  - `api/websocket/feature_factory_ws.py` → 擴充 event schema
  - 新增測試 `tests/api/test_feature_factory_batch_resume.py`
- [ ] **不可做**:
  - ❌ 不允許 batch 與 batch 並行 heavy task（class-level lock）
  - ❌ 不允許多層 process pool
  - ❌ 不在 query string 傳 batch_id（用 path param）
  - ❌ 不寫死 tier 數字（用 `hardware_utils`）
- [ ] **風險緩解**: R10（checkpoint 失敗）、R12（I/O 瓶頸）、R13（16GB 鎖為 1）、R16（多 symbol RSS 累積）
- [ ] **驗證**: T0.9, T0.B3, T0.B4, T0.B6, T0.P2, T0.P7, C-OPT-2

### Task 0.7 — Frontend Batch Panel + Per-Symbol Output

- [ ] **SPEC ref**: Task 0.7（SPEC §2.1）
- [ ] **目標**: 前端顯示 batch 進度、ETA、即時 per-symbol 輸出檔案路徑/下載連結；失敗時 resume 按鈕。
- [ ] **輸入**:
  - WebSocket `/features/batch/{task_id}` 事件流（schema 由 Task 0.6 定義）
  - Task 0.6 resume API
- [ ] **輸出**:
  - 修改 `BatchProgressPanel.tsx`、`GenerationProgress.tsx`、`BatchGenerationPanel.tsx`（優先擴充既有，必要時才新建）
  - 修改 `featureFactoryStore.ts`：新增 batch 狀態 slice
  - WebSocket 重連邏輯（5s retry × 3 次）
- [ ] **實作要點**:
  1. Zustand slice 擴充：
     ```ts
     interface BatchState {
       batchId: string | null;
       status: 'idle'|'running'|'completed'|'failed'|'paused';
       totalItems: number;
       completedItems: number;
       failedItems: number;
       currentSymbol: string | null;
       currentTimeframe: string | null;
       etaSeconds: number;
       resumeAvailable: boolean;
       outputPaths: Array<{symbol:string; timeframe:string; path:string}>;
       perItemRss: Array<{symbol:string; timeframe:string; rssPeakMB:number; rssAfterGcMB:number}>;
     }
     ```
  2. WebSocket 訂閱（重用既有 `feature_factory_ws.py` `/features/batch/{task_id}`）：
     ```ts
     useEffect(() => {
       const ws = new WebSocket(`${WS_URL}/features/batch/${batchId}`);
       let retry = 0;
       ws.onmessage = (e) => store.applyEvent(JSON.parse(e.data));
       ws.onclose = () => {
         if (retry < 3) { retry++; setTimeout(() => reconnect(), 5000); }
       };
       return () => ws.close();
     }, [batchId]);
     ```
  3. ETA 計算：`(totalItems - completedItems) * (elapsed / completedItems)`，在 `completedItems > 0` 才顯示。
  4. Per-symbol output：完成 1 個立即顯示 `<a href={downloadUrl}>{path}</a>`。
  5. Resume 按鈕（失敗時顯示）：`POST /api/v1/features/batch/{batchId}/resume`。
  6. Edge cases：
     - **(a) WebSocket 斷線**：5s retry × 3 次，超過顯示 "Connection lost, please refresh"。
     - **(b) 空 state**：`<EmptyBatchState />` component。
     - **(c) loading**：skeleton。
     - **(d) error**：紅色 alert + retry 按鈕。
- [ ] **修改檔案**:
  - `frontend/src/components/feature-factory/BatchProgressPanel.tsx` → 主面板擴充
  - `frontend/src/components/feature-factory/GenerationProgress.tsx`、`BatchGenerationPanel.tsx`（如有重疊功能則整合）
  - `frontend/src/store/featureFactoryStore.ts` → 新增 batch slice
  - 新增 `frontend/src/components/feature-factory/__tests__/BatchProgressPanel.test.tsx`
- [ ] **不可做**:
  - ❌ 不在 UI 寫死 symbol list（Data Truth Principle）
  - ❌ 不省略 empty/loading/error 狀態
- [ ] **風險緩解**: R14（UI 文案）— 一併同步 ETA / 估時警告
- [ ] **驗證**: T0.10

### Phase 0 測試清單

#### 單元測試

| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☑ | T0.1 | golden baseline 建立(Tier 1+2) | 4 種輸出檔存在；inventory 含實測 nodeids | Tier 1 / Tier 2A / Tier 2B / inventory 通過；Tier 2B 使用 `data_cache/feature_klines/kline_cache.h5` 並由 reduced workload gate 放行 | §2.2 |
| ☑ | T0.2 | layer filter 跳過 L3+ | L3/L4 column 不被 fracdiff，winsor/rank/zscore 仍套用 | transform call 計數比對 | §2.2 |
| ☑ | T0.3 | layer filter fallback | `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2,L3,L4` 行為等同 baseline | golden corr > 0.999 | §2.2 |
| ☑ | T0.4 | precision 微調 | precision 0.02 vs 0.01 fracdiff series corr | corr > 0.999（C2） | §2.2 |
| ☑ | T0.5 | d_star cache 隔離 | ETHUSDT vs BTCUSDT 同 column 名不互相污染 | 兩 cache 獨立 | §2.2 |
| ☑ | T0.6 | atomic write 並行 | 100 次 multi-thread 寫入無 partial JSON | 全數 valid JSON | §2.2 |
| ☑ | T0.7 | per-run cache hit | 同 column 重複呼叫 ADF 計數 = 1 | mock `adfuller.call_count == 1` | §2.2 |
| ☑ | T0.8 | UI 文案 snapshot | PreprocessingPanel 顯示新文案 | snapshot match | §2.2 |
| ☐ | T0.9 | batch resume | 模擬中斷 → resume 跳過 completed | route `POST /api/v1/features/batch/{batch_id}/resume`；completed_items 不重跑 | §2.2 |
| ☐ | T0.10 | batch panel UI | 進度顯示 + resume 按鈕 | manual + Playwright | §2.2 |
| ☑ | T0.11 | d_star stale invalidation | 改 data_fingerprint/feature_schema_hash/sample_size/nan_policy | cache miss + 重算 | §2.2 |
| ☑ | T0.12 | legacy migration audit | legacy `default/default` 遷移或隔離 | audit JSONL；無 direct hit；無寫回 legacy | §2.2 |

#### 邊界條件測試

| ☐ | Test ID | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|
| ☑ | T0.B1 | unknown layer column | column 名無法 parse layer | 跳過 fracdiff + log warning | §2.2 |
| ☑ | T0.B2 | high NaN column | NaN ratio > 50% | fracdiff skip + 不觸發 ADF（Q2） | §2.2 |
| ☐ | T0.B3 | RAM gate 觸發 | available RAM < 4GB | 拒絕新 symbol + 429 status | §2.2 |
| ☐ | T0.B4 | checkpoint 寫入失敗 | mock OSError | log error 但任務繼續 | §2.2 |
| ☑ | T0.B5 | cache schema 不相容 | 舊 v1 或 legacy `default/default` 讀入 | quarantine/migrate；不 direct hit；重建 v2 | §2.2 |
| ☐ | T0.B6 | resume 找不到 batch_id | invalid batch_id | 回傳 404 | §2.2 |

#### 效能驗收測試（Tier-A 8GB 必跑）

| ☐ | Test ID | 驗收標準 | SPEC ref |
|---|---------|---------|---------|
| ☐ | T0.P1 | 8GB ETHUSDT 1h 2000rows × ~500 cols：wall ≤60min、peak RSS≤6GB | §2.2 |
| ☐ | T0.P2 | 8GB 10 symbols×2 tf reduced：不 OOM、可 resume、`concurrent_symbols=1`、checkpoint 粒度正確、RAM gate 觸發 | §2.2 |
| ☐ | T0.P3 | 8GB 第二次 cache hit：wall ≤10min、cache hit ≥90% | §2.2 |
| ☐ | T0.P5 | 合成 1000×100 全開 L6.5：wall ≤5min、無 OOM | §2.2 |
| ☐ | T0.P7 | per-item memory sanity：`rss_after_gc_mb <= max(rss_before_item_mb+1024, rss_peak_item_mb*0.75)`；20 items RSS 累積 ≤1.5GB；任一失敗需 process recycle / worker restart 且 Gate fail | §2.2 / ARH-5 |

#### Tier-B / Frozen 驗收（**Frozen blocker，不阻塞 Dev Gate**）

| ☐ | Test ID | 驗收標準 | SPEC ref |
|---|---------|---------|---------|
| ☐ | T0.P4 | 16/24/32GB 全尺寸（PLAN §4 表）— 需外部機 | §2.2 |
| ☐ | T0.P6 | 8GB 全尺寸 best-effort，記錄 wall/peak RSS，不作 pass/fail | §2.2 |
| ☐ | T0.F1 | Phase 0 Frozen Gate：Tier 3 full 或 8GB full-width proxy；proxy 僅 accepted risk | §2.2 |

### Phase 0 → Phase 1 Gate

- [ ] 所有 T0.x、T0.Bx、Tier-A T0.Px 通過；T0.P4/T0.P6/T0.F1 若缺外部硬體標 Frozen blocker / accepted risk
- [ ] C-OPT-1, 2, 3 (Tier-A), 5, 6 達成（C-OPT-3 Tier-B 列為 U1 Frozen blocker）
- [ ] §1.6 U6 已取得實測值；U4 已確認 UI 路徑；U1 仍為 Frozen blocker
- [ ] 8GB tier 連續 3 次跑 T0.P1 無 OOM
- [ ] 既有 L6.5 測試 100% pass（C1）
- [ ] L7 輸出大小變化 ≤ 5%（C-OPT-5）

---

## Phase 1 — Safe Parallelism（joblib slow-path）

### Phase 1 目標與驗收標準

> 將 Phase 0 後的單 symbol 全開時間從 ~3-5h（8GB）降至 ~1-2h；多 symbol 比例同步下降。透過 joblib loky slow-path 並行 + Hurst prior bounded search 取代純二分。**預設 OFF，驗證後 ON**。

### Task 1.1 — joblib loky slow-path 並行

- [ ] **SPEC ref**: Task 1.1（SPEC §3.1）
- [ ] **目標**: FracDiff/ADF slow path 用 `joblib.Parallel(backend='loky', mmap_mode='r')`；保留 fast path ThreadPool 與 chunked OOM 防護。
- [ ] **輸入**:
  - 環境變數 `FFACT_L65_SLOWPATH_PARALLEL`、`FFACT_BATCH_NESTED`、`OMP_NUM_THREADS`、`MKL_NUM_THREADS`
  - tier 資訊（`hardware_utils.get_current_tier_gb()`）
- [ ] **輸出**:
  - 新模組 `momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py`：`ParallelSlowPath` 類別
  - 修改 `feature_preprocessor.py` slow path 區塊
  - `momentum/core/config.py` 新增 env 解析
- [ ] **實作要點**:
  1. tier-aware n_jobs：
     ```python
     from momentum.core.config import (
         get_batch_nested_enabled,
         get_slowpath_parallel_enabled,
     )

     SLOWPATH_NJOBS_TIER = {8: 2, 16: 4, 24: 6, 32: 8}
     def get_slowpath_n_jobs(tier_gb: int) -> int:
         if get_batch_nested_enabled():
             return 1  # 巢狀防護
         if not get_slowpath_parallel_enabled():
             return 1  # 預設 OFF
         return SLOWPATH_NJOBS_TIER.get(tier_gb, 2)
     ```
  2. 只傳 `Series.values` + metadata（C5）：
     ```python
     def _process_one_column_values(values: np.ndarray, col_meta: Dict) -> Dict:
         # 純函式，可被 loky pickle；不依賴 self
         ...
         return {"d_star": ..., "fracdiff_values": ...}
     ```
  3. BLAS 環境：
     ```python
     env_overrides = {"OMP_NUM_THREADS":"1", "MKL_NUM_THREADS":"1"}
     with parallel_backend("loky", n_jobs=n_jobs, inner_max_num_threads=1):
         results = Parallel()(delayed(_process_one_column_values)(s.values, meta) for s, meta in items)
     ```
  4. fallback：
     ```python
     try:
         results = run_loky(items)
     except (PicklingError, _RemoteTraceback) as e:
         logger.error(f"[L6.5] joblib pickle failed, fallback to serial chunked slow path: {e}", exc_info=True)
         results = run_existing_serial_chunked_slow_path(items)
     except MemoryError as e:
         logger.error(f"[L6.5] joblib OOM, raise to batch service for downscale", exc_info=True)
         raise
     ```
  5. 函式簽名：
     ```python
     def get_slowpath_n_jobs(tier_gb: int) -> int: ...
     class ParallelSlowPath:
         def __init__(self, n_jobs: int) -> None: ...
         def map(self, items: List[Tuple[np.ndarray, Dict]], fn: Callable) -> List[Dict]: ...
     ```
  6. Edge cases：
     - **(a) loky worker 拋 OOM**：raise MemoryError → batch service 降 `concurrent_symbols=1`。
      - **(b) joblib pickle 失敗**：fallback 既有 serial/chunked slow path + log error；不得新增 per-column ThreadPool 包 `statsmodels.adfuller`。
     - **(c) Windows 平台**：本 SPEC Linux/macOS only，Windows 強制 `n_jobs=1` + log warning。
     - **(d) 預設 OFF**：`FFACT_L65_SLOWPATH_PARALLEL=0`。
- [ ] **修改檔案**:
  - 新增 `momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py`
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_transform_single()` slow path
  - `momentum/core/config.py` → `get_slowpath_parallel_enabled()`, `get_slowpath_n_jobs()`
  - 新增測試 `tests/feature_engineering/preprocessing/test_slow_path_parallel.py`
- [ ] **不可做**:
  - ❌ 不傳整 DataFrame（C5）
  - ❌ 不允許巢狀 process pool（R6 防護）
  - ❌ 不在預設值 ON
  - ❌ 不用 ThreadPool 包 statsmodels.adfuller
- [ ] **風險緩解**: R5（joblib OOM）、R6（巢狀 pool）、R11（macOS spawn 慢）
- [ ] **驗證**: T1.1, T1.2, T1.B1, T1.P1, T1.P3, C5

### Task 1.2 — Hurst prior + bounded search 取代純二分

- [ ] **SPEC ref**: Task 1.2（SPEC §3.1）
- [ ] **目標**: `_find_min_d` 從 7 次 ADF 降至平均 3-5 次，bounded `predict_d ± 0.2`；超出退完整二分。
- [ ] **輸入**: column series（np.ndarray）、precision、adf_threshold、adf_fn callable
- [ ] **輸出**:
  - 新模組 `momentum/FeatureEngineering/preprocessing/_hurst_prior.py`
  - 修改 `_find_min_d()` 在 series 長度 ≥ 100 時走 prior + bounded search
- [ ] **實作要點**:
  1. Hurst R/S 估計（O(N) numpy）：
     ```python
     def estimate_hurst_rs(series: np.ndarray) -> float:
         n = len(series)
         if n < 100:
             return float("nan")
         # R/S analysis: 切多個 window，計算 log(R/S) vs log(window) 斜率
         windows = [n//8, n//4, n//2]
         rs_values = []
         for w in windows:
             chunks = [series[i:i+w] for i in range(0, n - w + 1, w)]
             rs_chunk = []
             for c in chunks:
                 mean = c.mean()
                 dev = (c - mean).cumsum()
                 R = dev.max() - dev.min()
                 S = c.std(ddof=1)
                 if S > 1e-12: rs_chunk.append(R / S)
             if rs_chunk: rs_values.append((w, np.mean(rs_chunk)))
         if len(rs_values) < 2: return float("nan")
         logs = np.log([w for w,_ in rs_values])
         logrs = np.log([rs for _,rs in rs_values])
         slope, _ = np.polyfit(logs, logrs, 1)
         return float(slope)  # ≈ Hurst exponent
     ```
  2. Bounded search：
     ```python
     def find_min_d_with_prior(series, *, precision, adf_threshold, adf_fn) -> float:
       if len(series) < 100:
         return _find_min_d_full_bisection(series, precision, adf_threshold, adf_fn)

       h = estimate_hurst_rs(series)
       if not np.isfinite(h) or h < 0 or h > 1:
         return _find_min_d_full_bisection(series, precision, adf_threshold, adf_fn)

       # Bracket invariant：low 必須是 non-stationary，high 必須是 stationary。
       # 先測 d=0/d=1，避免 Hurst lower bound 已經 stationary 時高估 d_star。
       p_zero = adf_fn(_apply_fracdiff(series, 0.0))
       if p_zero <= adf_threshold:
         return 0.0

       p_one = adf_fn(_apply_fracdiff(series, 1.0))
       if p_one > adf_threshold:
         logger.warning("[L6.5] d=1 still non-stationary, fallback to full bisection")
         return _find_min_d_full_bisection(series, precision, adf_threshold, adf_fn)

       predict = h - 0.5
       prior_lo = max(0.0, predict - 0.2)
       prior_hi = min(1.0, predict + 0.2)
       p_lo = adf_fn(_apply_fracdiff(series, prior_lo))
       p_hi = adf_fn(_apply_fracdiff(series, prior_hi))

       if p_hi > adf_threshold:
         logger.warning("[L6.5] Hurst prior bounded fail, fallback to full bisection")
         return _find_min_d_full_bisection(series, precision, adf_threshold, adf_fn)

       if p_lo <= adf_threshold:
         # prior lower bound 已 stationary，最小 d 可能在 [0, prior_lo]。
         lo, hi = 0.0, prior_lo
       else:
         lo, hi = prior_lo, prior_hi

       # bounded binary refine；保持 low non-stationary / high stationary。
       while (hi - lo) > precision:
         mid = (lo + hi) / 2
         if adf_fn(_apply_fracdiff(series, mid)) <= adf_threshold:
           hi = mid
         else:
           lo = mid
       return hi
     ```
  3. 共用 Phase 0 Task 0.4 per-run `(column, d)` ADF p-value cache。
  4. **Hurst method review gate（ARH-2）**：本 Task 的 O(N) R/S estimator 只允許作為 prior，且必須先對照 Mansukhani Hurst R/S 與 DFA reference。
      - 樣本：至少 200 條金融時序，跨 symbol/timeframe/layer/feature type，包含 2020-03 等異常 regime。
      - Gate：`median_abs_delta_h_vs_reference <= 0.10`、`p95_abs_delta_h_vs_reference <= 0.20`、`d_prior_bucket_agreement >= 80%`（bucket: mean-reverting / neutral / persistent）。
      - 若 Gate 失敗：不得合併 Task 1.2；保留完整二分搜尋，不啟用 Hurst prior。
      - Reviewer 必須明確標註信心度：`Medium`（方法依場景而定）；不得只用 Hurst prior 加速結果作為品質證據。
  5. 函式簽名：
     ```python
     def estimate_hurst_rs(series: np.ndarray) -> float: ...
     def compare_hurst_estimators(samples: List[np.ndarray]) -> Dict[str, float]: ...
     def find_min_d_with_prior(
         series: np.ndarray,
         *,
         precision: float,
         adf_threshold: float,
         adf_fn: Callable[[np.ndarray], float],
     ) -> float: ...
     ```
  6. Edge cases：
     - **(a) Hurst 極端值（< 0 或 > 1 或 NaN）**：忽略 prior，走完整搜尋。
     - **(b) 樣本 < 100**：bypass prior。
     - **(c) bounded 區間 ADF 全不通過**：Q4 fallback 完整 [0,1] 二分搜尋。
     - **(d) series 全常數**：Hurst undefined → fallback。
      - **(e) Mansukhani R/S 或 DFA reference 不可用**：T1.4 狀態為 `blocked-not-pass`，不得把 simplified R/S gate 視為通過。
- [ ] **修改檔案**:
  - 新增 `momentum/FeatureEngineering/preprocessing/_hurst_prior.py`
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_find_min_d()`（line ~1353）
  - 新增測試 `tests/feature_engineering/preprocessing/test_hurst_prior.py`
- [ ] **不可做**:
  - ❌ 不把 Hurst 結果作為決策輸出（僅作 prior）
  - ❌ 不在 series < 100 時用 prior
- [ ] **風險緩解**: R7（Hurst 極端值帶偏）— Q4 fallback
- [ ] **驗證**: T1.3, T1.B2, T1.B3

### Phase 1 測試清單

#### 單元測試

| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T1.1 | joblib slow-path 結果一致 | 開/關 slow-path parallel 輸出 fracdiff series | corr > 0.9999、d_star 完全一致 | §3.2 |
| ☐ | T1.2 | 巢狀 pool 偵測 | `FFACT_BATCH_NESTED=1` → `n_jobs=1` | mock joblib n_jobs == 1 | §3.2 |
| ☐ | T1.3 | Hurst prior 加速與等價 | adfuller call_count + d_star 比對 + bracket invariant | call_count median ≤ 5；d_star median \|diff\| < 0.02、P95 \|diff\| < 0.05；low non-stationary/high stationary invariant 全程成立；fallback 完全等同完整搜尋 | §3.2 |
| ☐ | T1.4 | Hurst estimator reference check | simplified O(N) R/S vs Mansukhani Hurst R/S + DFA | 200+ 金融時序；median \|ΔH\|≤0.10、P95 \|ΔH\|≤0.20、d-prior bucket agreement ≥80%；reference 缺失則 blocked-not-pass | ARH-2 |

#### 邊界條件測試

| ☐ | Test ID | 邊界 | 預期行為 | SPEC ref |
|---|---------|------|---------|---------|
| ☐ | T1.B1 | joblib pickle 失敗 | 不可序列化 lambda | fallback 既有 serial/chunked slow path + log error；不得新增 per-column ThreadPool ADF | §3.2 |
| ☐ | T1.B2 | Hurst 極端值 | series 全常數或全 NaN | 不啟用 prior，完整搜尋 | §3.2 |
| ☐ | T1.B3 | 樣本 < 100 | 短序列 | bypass prior | §3.2 |

#### 效能驗收

| ☐ | Test ID | 驗收標準 | SPEC ref |
|---|---------|---------|---------|
| ☐ | T1.P1 | 8GB Phase 1 short-window：wall ≤30min、peak RSS≤6GB | §3.2 |
| ☐ | T1.P3 | 8GB Phase 1 cache hit：≤5min | §3.2 |
| ☐ | T1.P2 | 16/24/32GB 全尺寸（PLAN §4）— 需外部機，**Frozen blocker** | §3.2 |
| ☐ | T1.F1 | Phase 1 Frozen Gate：Tier 3 full 或 full-width proxy | §3.2 |

### Phase 1 → Phase 2 Gate

- [ ] T1.x 全綠
- [ ] U3 確認：`FFACT_L65_SLOWPATH_PARALLEL` 在 8GB 連續 3 次無 OOM 後才考慮 ON；未確認則保持 OFF
- [ ] C-OPT-3（品質）不退化
- [ ] L7 輸出大小無變化（C-OPT-5）

---

## Phase 2 — Fast ADF（Algorithm Replacement，條件性）

### Phase 2 目標與驗收標準

> 將 ADF 從 statsmodels ~30ms/call 降至 numba-OLS ~3-5ms/call；單 symbol 全開降至 ≤ 1h（8GB 推導）。**預設 OFF**，需 T2.V1 1000+ 樣本 gate 通過後才 ON。

### Phase 2 Skip 條件（SPEC §4.0）

| 條件 | 判斷方式 | Skip 後採用 |
|------|---------|-----------|
| Phase 1 完成後 8GB tier 全開 ≤ 1.5h 已達使用者接受度 | T1.P1 實測 + 使用者確認 | Phase 1 結果（~1-2h） |
| Fast ADF 1000+ 樣本 classification agreement < 99% | T2.V1 失敗 | 退回 Phase 1 結果 |

> ⚠️ 評估 Skip 條件後再決定是否執行 Task 2.1 / 2.2。

### Task 2.1 — Numba Fast ADF 實作

- [ ] **SPEC ref**: Task 2.1（SPEC §4.1）
- [ ] **目標**: 實作 `adf_pvalue_fast(series, lag)` 達 ~3-5ms；使用 statsmodels-compatible MacKinnon p-value 或明確命名為 classification-only。
- [ ] **輸入**: `np.ndarray`（contiguous, dtype float64）、optional lag、sample_size
- [ ] **輸出**:
  - 新模組 `momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py`
  - 公開 API `adf_pvalue_fast()`（若只實作 classification 則命名 `adf_classification_fast()`）
  - micro benchmark `benchmark/adf.py`
- [ ] **實作要點**:
  1. AR(p) OLS + t-statistic + MacKinnon p-value：
     ```python
     from numba import njit
     from statsmodels.tsa.adfvalues import mackinnonp  # 在外層使用，非 njit 內部

     @njit(cache=True, fastmath=False)
     def _adf_ols_core(y: np.ndarray, lag: int) -> Tuple[float, float, int]:
         """Returns (adf_stat, stderr, condition_flag)."""
         n = len(y)
         dy = y[1:] - y[:-1]
         x = np.empty((n - lag - 1, lag + 2))
         x[:, 0] = y[lag:n-1]      # y_{t-1}
         for k in range(lag):
             x[:, k+1] = dy[lag-k-1:n-k-2]
         x[:, -1] = 1.0             # constant
         yvec = dy[lag:]
         xtx = x.T @ x
         # singular guard: min diagonal magnitude. This is not a condition number.
         min_diag = 1e18
         for i in range(xtx.shape[0]):
             if abs(xtx[i,i]) < min_diag: min_diag = abs(xtx[i,i])
         if min_diag < 1e-12:
             return 0.0, 0.0, 1   # singular flag
         # 不在 njit 內捕捉 generic exception；若 solve 在 numba runtime 失敗，交由 Python wrapper fallback。
         beta = np.linalg.solve(xtx, x.T @ yvec)
         resid = yvec - x @ beta
         sigma2 = (resid @ resid) / (len(yvec) - x.shape[1])
         var_beta = sigma2 * np.linalg.inv(xtx)[0, 0]
         se = np.sqrt(max(var_beta, 0.0))
         if se < 1e-12: return 0.0, 0.0, 1
         t_stat = beta[0] / se
         return t_stat, se, 0

     def adf_pvalue_fast(
         series: np.ndarray,
         *,
         lag: Optional[int] = None,
         sample_size: int = 500,
     ) -> Tuple[float, bool]:
         """Returns (pvalue, used_fallback)."""
         if np.isnan(series).any():
             return _adf_fallback_statsmodels(series), True
         n = len(series)
         if lag is None:
             lag = int(round(12 * (n / 100.0) ** 0.25))  # statsmodels default
         values = np.ascontiguousarray(series.astype(np.float64, copy=False))
         try:
             t_stat, _, flag = _adf_ols_core(values, lag)
         except Exception:
             return _adf_fallback_statsmodels(series), True
         if flag == 1:
             return _adf_fallback_statsmodels(series), True
         # min_diag 只是 singular guard，不是 condition number。
         # 若需 condition-number gate，於 wrapper 對小型 xtx 做 np.linalg.cond；不可把 min_diag 當成 cond>1e10 證據。
         pvalue = mackinnonp(t_stat, regression="c", N=1)
         # Threshold band：[0.08, 0.12] 強制 fallback (C4)
         if 0.08 <= pvalue <= 0.12:
             return _adf_fallback_statsmodels(series), True
         return pvalue, False
     ```
  2. **MacKinnon p-value overhead gate（ARH-3）**：`mackinnonp` 在 numba layer 外呼叫，必須單獨量測。
      - `T2.P2a`：10000 次 `mackinnonp(t_stat, regression="c", N=1)`，mean ≤ 1ms、P99 ≤ 2ms。
      - 若未通過：不得宣稱 Fast ADF 達 3-5ms/call；需改為 classification-only critical-value API、vectorized p-value lookup，或保留 statsmodels fallback。
  3. 預設 OFF：`FFACT_USE_FAST_ADF=0`。
  4. 函式簽名：見上。
  5. 命名一致性：API 名稱必須與實際輸出一致；若只可靠輸出 classification，**禁止** 命名 `adf_pvalue_fast`。
  6. Edge cases：
     - **(a) series 含 NaN**：fallback statsmodels。
     - **(b) lag is None**：用 `int(round(12 * (n/100) ** 0.25))`。
      - **(c) singular matrix（min_diag < 1e-12、LinAlgError 或 numba runtime exception）**：fallback。
      - **(d) condition number > 1e10**：fallback；若無法在 numba core 低成本計算，必須在 Python wrapper 對 small `xtx` 做明確 `np.linalg.cond` 或記錄為不支援並 fallback，不可用 min_diag proxy 取代。
     - **(e) p-value ∈ [0.08, 0.12]**：強制 fallback（C4）。
- [ ] **修改檔案**:
  - 新增 `momentum/FeatureEngineering/preprocessing/_fast_adf_numba.py`
  - 新增 `benchmark/adf.py`
  - `momentum/core/config.py` → `get_fast_adf_enabled() -> bool`
  - 新增測試 `tests/feature_engineering/preprocessing/test_fast_adf_synthetic.py`
- [ ] **不可做**:
  - ❌ 不開 fastmath（避免精度退化）
  - ❌ 不在預設值 ON
  - ❌ 不在無法可靠輸出 p-value 時謊稱輸出 p-value
- [ ] **風險緩解**: R8（OLS singular）、R9（threshold 邊界誤判）
- [ ] **驗證**: T2.1, T2.B1, T2.B2, T2.B3, T2.P2, C4

### Task 2.2 — Fast ADF 驗證 Gate

- [ ] **SPEC ref**: Task 2.2（SPEC §4.1）
- [ ] **目標**: 1000+ 樣本分層抽樣驗證 classification agreement、d_star diff、threshold band fallback 全綠。
- [ ] **輸入**: 4 symbols（含 ETH/BTC + 2 個其他）× 2 tf × 跨 layer L1/L2/L3 × 跨 column type 的真實資料
- [ ] **輸出**:
  - 新測試 `tests/feature_engineering/preprocessing/test_fast_adf_gate.py`
  - 驗證 report `tests/golden/l65/fast_adf_gate_report.json`（每次跑覆寫）
- [ ] **實作要點**:
  1. 樣本準備：
     ```python
     def collect_gate_samples() -> List[Dict]:
         samples = []
         for sym in ("ETHUSDT", "BTCUSDT", "BNBUSDT", "SOLUSDT"):
             for tf in ("1h", "12h"):
                 df = load_kline(sym, tf, max_rows=2000)
                 # 跨 layer L1/L2/L3，跨 column type (price-like/return/rank/zscore)
                 cols = stratified_column_sample(df, n_per_stratum=30)
                 for col in cols:
                     samples.append({"symbol": sym, "tf": tf, "col": col, "values": df[col].values})
         assert len(samples) >= 1000, f"sample size {len(samples)} < 1000"
         return samples
     ```
  2. Metric 計算：
     ```python
     def evaluate_gate(samples) -> Dict:
         agreements, d_star_diffs, fallback_count = [], [], 0
         for s in samples:
             p_fast, used_fb = adf_pvalue_fast(s["values"])
             p_ref = statsmodels_adf(s["values"])
             cls_fast = p_fast <= 0.10
             cls_ref = p_ref <= 0.10
             agreements.append(cls_fast == cls_ref)
             # d_star (用 prior 路徑算)
             d_fast = find_min_d_with_prior(s["values"], adf_fn=lambda x: adf_pvalue_fast(x)[0])
             d_ref = find_min_d_with_prior(s["values"], adf_fn=statsmodels_adf)
             d_star_diffs.append(abs(d_fast - d_ref))
             if 0.08 <= p_ref <= 0.12 and not used_fb:
                 fallback_count += 1  # threshold band 必須 fallback
         agreement = np.mean(agreements)
         return {
             "classification_agreement": agreement,
             "d_star_median_diff": np.median(d_star_diffs),
             "d_star_p95_diff": np.percentile(d_star_diffs, 95),
             "threshold_band_violations": fallback_count,
             "final_dstar_corr_vs_baseline": ...,  # 完整 d_star 序列 vs baseline corr
         }
     ```
  3. Pass 條件（**所有 metric 同時 pass**）：
     - `classification_agreement > 0.99`
     - `d_star_median_diff < 0.02`
     - `d_star_p95_diff < 0.05`
     - `threshold_band_violations == 0`
     - `final_dstar_corr_vs_baseline > 0.99`
  4. 函式簽名：
     ```python
     def collect_gate_samples() -> List[Dict]: ...
     def evaluate_gate(samples: List[Dict]) -> Dict[str, float]: ...
     ```
  5. Edge cases：
     - **(a) 樣本不足（< 1000）**：assert 失敗 → 阻塞 + manual confirm。
     - **(b) 任一 metric 失敗**：寫 report，pytest assert fail，觸發 Skip 條件。
     - **(c) 真實 HDF5 缺失**：標 blocked + skip（不算 pass）。
- [ ] **修改檔案**:
  - 新增 `tests/feature_engineering/preprocessing/test_fast_adf_gate.py`
  - 新增 `tests/golden/l65/fast_adf_gate_report.json`（runtime 產出）
- [ ] **不可做**:
  - ❌ 在 gate 通過前 ON `FFACT_USE_FAST_ADF`
  - ❌ 樣本 < 1000 時當作 pass
- [ ] **風險緩解**: R8、R9
- [ ] **驗證**: T2.V1

### Phase 2 測試清單

#### 單元測試

| ☐ | Test ID | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|
| ☐ | T2.1 | 100 個合成 stationary/non-stationary | classification 100% match | §4.2 |
| ☐ | T2.V1 | 1000+ 樣本跨 symbol/tf/layer | §1.5 Q5 全 metric 通過 | §4.2 |

#### 邊界條件測試

| ☐ | Test ID | 邊界 | 預期 | SPEC ref |
|---|---------|------|------|---------|
| ☐ | T2.B1 | 共線 design | fallback statsmodels | §4.2 |
| ☐ | T2.B2 | p-value ∈ [0.08, 0.12] | 強制 fallback | §4.2 |
| ☐ | T2.B3 | series 含 NaN | fallback | §4.2 |

#### 效能驗收

| ☐ | Test ID | 驗收標準 | SPEC ref |
|---|---------|---------|---------|
| ☐ | T2.P1 | 8GB Phase 2 short-window：≤15min、peak RSS≤6GB | §4.2 |
| ☐ | T2.P2 | ADF micro benchmark（10000 calls）：mean ≤5ms、P99 ≤15ms | §4.2 |
| ☐ | T2.P2a | MacKinnon p-value overhead：10000 calls `mackinnonp` mean ≤1ms、P99 ≤2ms；未過不得宣稱 Fast ADF 3-5ms/call | ARH-3 |
| ☐ | T2.P3 | 16/24/32GB 全尺寸 — **Frozen blocker** | §4.2 |
| ☐ | T2.F1 | Phase 2 Frozen Gate：Tier 3 full 或 full-width proxy | §4.2 |

### Phase 2 → Phase 3 Gate

- [ ] T2.x 全綠
- [ ] T2.V1 gate 通過（< 99% 則 Skip Phase 2）
- [ ] L7 float16 roundtrip gate 全綠
- [ ] 既有測試 100% pass

---

## Phase 3 — 持續監控與 Benchmark Suite

### Phase 3 目標與驗收標準

> 建立可持續回歸的 benchmark suite，跨 tier CI 自動化。防止後續變更回歸；不直接帶來時間提升。

### Task 3.1 — L6.5 Benchmark Suite

- [ ] **SPEC ref**: Task 3.1（SPEC §5.1）
- [ ] **目標**: 標準化 benchmark 入口，支援 tier、phase、symbol 參數；自動 flag 回歸（> 20% 退化）。
- [ ] **輸入**:
  - tier sim：`resource.setrlimit`（best effort）
  - 歷史 benchmark `benchmark_results/l65/*.json`
- [ ] **輸出**:
  - 完整化 `scripts/benchmark_l65.py`（Phase 0 起步、本 Task 完整化）
  - `tests/performance/test_l65_perf.py` 標 `@pytest.mark.slow`
  - 結果 `benchmark_results/l65/{tier}_{phase}_{timestamp}.json`
- [ ] **實作要點**:
  1. CLI：
     ```python
     parser.add_argument("--tier", choices=["8gb","16gb","24gb","32gb"], default="8gb")
     parser.add_argument("--phase", choices=["0","1","2"], default="0")
     parser.add_argument("--symbols", default="ETHUSDT")
     parser.add_argument("--tfs", default="1h")
     parser.add_argument("--repeat", type=int, default=1)
     parser.add_argument("--max-rows", type=int, default=2000)
     parser.add_argument("--max-cols", type=int, default=500)
     parser.add_argument("--multi", action="store_true")
     parser.add_argument("--memory-sanity", action="store_true")
     parser.add_argument("--smoke", action="store_true")
     parser.add_argument("--full", action="store_true")
     parser.add_argument("--full-width-proxy", action="store_true")
     parser.add_argument("--best-effort", action="store_true")
     parser.add_argument("--layers", default="L1,L2")
     ```
  2. tier sim（best effort）：
     ```python
     try:
         resource.setrlimit(resource.RLIMIT_AS, (tier_bytes, tier_bytes))
     except (ValueError, OSError) as e:
         logger.warning(f"tier sim failed: {e}")
     ```
  3. 結果 JSON schema：
     ```json
     {
       "tier_gb": 8, "phase": 0, "timestamp": "...",
       "wall_time_seconds": 1234, "peak_rss_mb": 5800,
       "cache_hit_rate": 0.92, "l7_size_mb": 145,
       "n_symbols": 1, "n_timeframes": 1, "rows_per_item": 2000,
       "regression_flag": false
     }
     ```
  4. 回歸偵測：載入最近 7 天歷史，若 wall_time 退化 > 20% 或 peak_rss > 20% → flag。
  5. 函式簽名：
     ```python
     def run_benchmark(args) -> Dict: ...
     def detect_regression(current: Dict, history: List[Dict]) -> bool: ...
     ```
  6. Edge cases：
     - **(a) sim 失敗**：log + 跳過 sim，正常跑。
     - **(b) 歷史不足**：跳過回歸偵測。
     - **(c) HDF5 缺失**：標 blocked，不算 pass。
- [ ] **修改檔案**:
  - `scripts/benchmark_l65.py`（完整化）
  - `tests/performance/test_l65_perf.py`
- [ ] **不可做**:
  - ❌ 不在 8GB 跑 `--full` 而不加 `--best-effort`
- [ ] **風險緩解**: R1（無 baseline 比對 → 無法偵測退化）
- [ ] **驗證**: T3.1

### Task 3.2 — 跨 tier CI 回歸

- [ ] **SPEC ref**: Task 3.2（SPEC §5.1）
- [ ] **目標**: GitHub Actions 在 8GB / 16GB sim 環境跑 nightly benchmark；失敗發 issue。
- [ ] **輸入**:
  - 既有 GitHub Actions runner
  - reduced fixture（100 cols × 1000 rows，即 Tier 2A）
- [ ] **輸出**:
  - 新增 `.github/workflows/l65_benchmark.yml`
- [ ] **實作要點**:
  1. workflow yaml 結構：
     ```yaml
     name: L6.5 Benchmark
     on:
       schedule:
         - cron: '0 18 * * *'  # nightly 02:00 Asia/Taipei
       workflow_dispatch:
     jobs:
       smoke:
         strategy:
           matrix:
             tier: ['8gb','16gb']
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v4
           - uses: actions/setup-python@v5
           - run: python -m pip install -r requirements.txt
           - run: python scripts/benchmark_l65.py --smoke --tier=${{ matrix.tier }}
           - if: failure()
             run: gh issue create --title "L6.5 Benchmark fail (${{ matrix.tier }})" --label benchmark-regression
     ```
  2. smoke 用 reduced fixture，避免 CI 跑太久。
  3. Edge cases：
     - **(a) GitHub Actions runner OOM**：tier 8gb sim 在 GH runner（通常 7GB）可能超限 → workflow 加 `continue-on-error: true` 並改成只記錄不 fail。
     - **(b) gh CLI 缺失**：fallback 用 `actions/github-script`。
- [ ] **修改檔案**:
  - 新增 `.github/workflows/l65_benchmark.yml`
- [ ] **不可做**:
  - ❌ 不在 CI 跑 full baseline
- [ ] **驗證**: T3.2

### Phase 3 測試清單

| ☐ | Test ID | 驗證 | 通過條件 | SPEC ref |
|---|---------|------|---------|---------|
| ☐ | T3.1 | 4 tier × 3 phase 全可跑 | 全部產出 JSON | §5.2 |
| ☐ | T3.2 | nightly CI 觸發 | GitHub Actions log 綠 | §5.2 |

### Phase 3 Gate

- [ ] T3.x 全綠
- [ ] CI nightly 連續 7 天無誤觸 alert

---

## Frozen Gate（Batch 9）

### T0.F1 / T1.F1 / T2.F1（SPEC §2.2 / §3.2 / §4.2）

- [ ] **目標**: 在 24GB+ 環境補跑 Tier 3 full baseline；若無，跑 8GB full-width proxy 並標 accepted risk。
- [ ] **驗證命令**:
  - `scripts/benchmark_l65.py --tier=24gb --full`（preferred）
  - 或 `scripts/benchmark_l65.py --tier=8gb --full-width-proxy`
- [ ] **通過條件**:
  - **真正 Frozen**：Tier 3 full baseline runtime + quality report 全綠
  - **Accepted Risk**：proxy 通過但無 Tier 3 → 狀態為 `Accepted Risk`，不可標完全 Frozen

---

## ⚠️ 全 TODO 審查修補標記

本 TODO 已完成內部 adversarial review 修補並達到文件層級 Frozen / implementation-ready。不得再保留「無矛盾」作為審查結論；後續實作與 reviewer 仍需依 §0.7 逐項執行與判斷。

| ID | 原問題 | 修補狀態 | 修改位置 |
|----|--------|----------|----------|
| IR-1 | TODO 一方面要求 env var 統一於 `momentum/core/config.py`，一方面在 pseudocode 中直接使用 `os.environ.get` | 已修補：pseudocode 改用 config helper；必要 import 指向 `momentum.core.config` | Task 0.2、0.6、1.1 |
| IR-2 | Rule 8 會誘導 Agent 未經使用者要求自行 branch/commit | 已修補：Rule 8 改為僅在使用者明確要求時適用 | Rule 8 |
| IR-3 | Hurst R/S prior 缺少外部方法對照，可能系統性偏誤 | 已修補：新增 T1.4 與 ARH-2 | Task 1.2、Phase 1 測試清單 |
| IR-4 | Fast ADF `mackinnonp` 外層呼叫缺 micro gate，可能無法達到 < 1ms overhead | 已修補：新增 T2.P2a 與 ARH-3 | Task 2.1、Phase 2 效能驗收 |
| IR-5 | T0.P7 RSS sanity 公式未說明用途與失敗處理 | 已修補：公式標為 sanity heuristic，失敗需 process recycle / worker restart | Task 0.6、T0.P7 |
| IR-6 | Task 1.1 fallback 寫成 ThreadPool，可能誘導用 ThreadPool 包 statsmodels ADF | 已修補：fallback 改為既有 serial/chunked slow path，不得新增 per-column ThreadPool ADF | Task 1.1 |
| IR-7 | Fast ADF pseudocode 在 numba 內部捕捉 generic exception，且把 min_diag 誤稱 condition number | 已修補：exception fallback 放到 Python wrapper；min_diag 只作 singular guard，condition number 另行檢測或 fallback | Task 2.1 |
| IR-8 | Task 0.0 可能自動將真實市場資料衍生 parquet 加入 Git LFS | 已修補：真實 Tier 2B artifact 預設僅本機產生，需使用者明確批准才可加入 LFS | Task 0.0 |
| IR-9 | Hurst bounded search 沒有維持 low non-stationary / high stationary bracket invariant，可能高估 d_star | 已修補：先測 d=0/d=1，prior bound 只用於選擇搜尋區間，bounded 失敗回 full bisection | Task 1.2 |
| IR-10 | CI workflow 範例未建立 venv 卻呼叫 `./venv/bin/python` | 已修補：改用 `python -m pip install` 與 `python scripts/benchmark_l65.py` | Task 3.2 |

