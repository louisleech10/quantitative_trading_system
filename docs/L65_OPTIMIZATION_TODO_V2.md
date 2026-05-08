# Layer 6.5 全模組優化 TODO V2

> **版本**: V1
> **狀態**: V1 Review-Patched（Not Frozen；TODO_ONLY adversarial review findings applied）
> **基於 SPEC**: `docs/L65_OPTIMIZATION_SPEC_V2.md` V1（2026-05-07）
> **生成日期**: 2026-05-07
> **修訂日期**: 2026-05-07
> **生成方式**: 已先產生 V1 draft，並依使用者要求重新按階段 2、3、4 review 一次後就地修補
> **Frozen 限制**: 外部 adversarial review、U-V2 人工確認、full-schema gates 完成前不得標記 Frozen；本文件僅可作為實作 TODO，不可作為 Frozen 證明

---

## 交付物 #0.5 — SPEC 正規化報告

SPEC 結構完整，跳過正規化。

| 結構要素 | 存在? | 處理 |
|---------|-------|------|
| Task ID | ✅ | 原有 13 個 Task ID |
| Test ID | ✅ | 原有 39 個 Test ID |
| Risk ID | ✅ | 原有 8 個 Risk ID |
| Phase 劃分 | ✅ | 原有 Phase 0-3 + Frozen Gate |
| Phase Gate | ✅ | 原有 5 個 Gate |
| 修改檔案 | ✅ | 原有程式碼、測試、script 路徑 |
| 硬約束 / C-OPT | ✅ | 原有 C-OPT-1~6 + C-V2-1~11 |
| Golden / Baseline / 驗收精度 | ✅ | 原有 Tier 1~2D、IC stability、roundtrip 精度 |

---

## 交付物 #1 — SPEC 索引摘要

### A. ID 清單（逐一列出，附原文引用）

#### Task IDs（共 13 個）

| # | ID | 名稱/簡述 | SPEC 原文位置 | 原文節錄（≤30 字） |
|---|-----|---------|-------------|-----------------|
| 1 | Task 0.1 | 多 transform 單次複製 + numpy 直接操作 | §2.1, line 315 | 「多 transform 單次複製」 |
| 2 | Task 0.2 | winsorize numpy direct + 單次 quantile | §2.1, line 355 | 「winsorize — numpy direct」 |
| 3 | Task 0.3 | rank 消除 constant_mask 多餘 rolling pass | §2.1, line 385 | 「消除 constant_mask」 |
| 4 | Task 0.4 | zscore 共用 rolling 物件 + 消除 copy | §2.1, line 426 | 「zscore — 共用 rolling」 |
| 5 | Task 0.5 | Gaussian DataFrame 批次化 + ndtri | §2.1, line 462 | 「Gaussian — DataFrame 批次化」 |
| 6 | Task 1.1 | FeatureFactory pre/post IC pipeline | §3.1, line 540 | 「pre/post IC 兩段式 pipeline」 |
| 7 | Task 1.2 | FeatureStorage raw/processed 雙路徑 | §3.1, line 594 | 「raw/processed 雙路徑」 |
| 8 | Task 1.3 | IC Gatekeeper per-group 讀 L7_raw | §3.1, line 647 | 「per-group 迭代讀取 L7_raw」 |
| 9 | Task 1.4 | Post-IC transform + GC 保護 | §3.1, line 702 | 「Post-IC Transform Service」 |
| 10 | Task 2.1 | byte_stream_split for float32 fallback groups | §4.1, line 842 | 「byte_stream_split」 |
| 11 | Task 2.2 | 整數編碼 Registry | §4.1, line 881 | 「整數編碼 Registry」 |
| 12 | Task 3.1 | Sequential symbol IC-First GC chain | §5.1, line 1012 | 「Sequential Symbol Execution」 |
| 13 | Task 3.2 | Cross-Symbol Rank optional / deferred | §5.1, line 1048 | 「DEFERRED to Phase 3」 |
| **合計** | **13 個** | | | |

#### Test IDs（共 39 個）

| # | ID | 簡述 | SPEC 原文位置 | 原文節錄（≤30 字） |
|---|-----|------|-------------|-----------------|
| 1 | T0.1 | single copy equivalence | §2.2, line 501 | 「test_single_copy_equivalence」 |
| 2 | T0.2 | winsorize numpy equivalence | §2.2, line 502 | 「test_winsorize_numpy_equivalence」 |
| 3 | T0.3 | rank constant mask removed | §2.2, line 503 | 「test_rank_constant_mask_removed」 |
| 4 | T0.4 | zscore shared rolling | §2.2, line 504 | 「test_zscore_shared_rolling」 |
| 5 | T0.5 | gaussian batch equivalence | §2.2, line 505 | 「test_gaussian_batch_equivalence」 |
| 6 | T0.B1 | rank constant window | §2.2, line 511 | 「全常數 array 輸入」 |
| 7 | T0.B2 | winsorize all-NaN column | §2.2, line 512 | 「全 NaN 欄位」 |
| 8 | T0.B3 | zscore empty windows | §2.2, line 513 | 「windows=[]」 |
| 9 | T0.B4 | gaussian NaN column | §2.2, line 514 | 「含 NaN 的欄位」 |
| 10 | T0.P1 | phase0 transform benchmark | §2.2, line 520 | 「L6.5 時間 ≤ 3,000s」 |
| 11 | T1.1 | IC-First routing | §3.2, line 789 | 「test_ic_first_pipeline_routing」 |
| 12 | T1.2 | L7 schema metadata | §3.2, line 790 | 「raw_v1 / processed_v1」 |
| 13 | T1.3 | IC selection stability | §3.2, line 791 | 「selected Jaccard ≥ 0.90」 |
| 14 | T1.4 | memory budget after raw persist | §3.2, line 792 | 「available RAM ≥ config gate」 |
| 15 | T1.5 | run dir and manifest atomicity | §3.2, line 793 | 「complete=true 才可讀」 |
| 16 | T1.B1 | IC empty selection | §3.2, line 799 | 「IC 未篩選到任何特徵」 |
| 17 | T1.B2 | group read failure fail-closed | §3.2, line 800 | 「預設 raise」 |
| 18 | T1.B2a | group read failure partial mode | §3.2, line 801 | 「quality_status=partial」 |
| 19 | T1.B3 | IC-first legacy fallback | §3.2, line 802 | 「FFACT_IC_FIRST_PIPELINE=0」 |
| 20 | T1.B4 | IC cross-symbol isolation | §3.2, line 803 | 「兩份 JSON 路徑不同」 |
| 21 | T1.P1 | IC-first single symbol benchmark | §3.2, line 809 | 「L6.5 時間 ≤ 250s」 |
| 22 | T1.P2 | L7 size IC-first benchmark | §3.2, line 810 | 「L7_raw ≤ 1.5 GB」 |
| 23 | T1.P3 | full-schema streaming benchmark | §3.2, line 811 | 「不得全量 concat readback」 |
| 24 | T2.1 | BSS roundtrip | §4.2, line 963 | 「test_bss_roundtrip」 |
| 25 | T2.2 | rank uint16 roundtrip | §4.2, line 964 | 「≤ 1/(2W)」 |
| 26 | T2.3 | zscore int16 roundtrip | §4.2, line 965 | 「≤ 0.001」 |
| 27 | T2.4 | mixed metadata roundtrip | §4.2, line 966 | 「l7_encoding_registry」 |
| 28 | T2.B1 | rank NaN sentinel | §4.2, line 972 | 「NaN → uint16=0」 |
| 29 | T2.B2 | zscore overflow fallback | §4.2, line 973 | 「不 clip；fallback float32」 |
| 30 | T2.B3 | BSS pyarrow fallback | §4.2, line 974 | 「PyArrow 不支援 BSS」 |
| 31 | T2.B4 | old parquet no metadata | §4.2, line 975 | 「無 l7_encoding_registry」 |
| 32 | T2.P1 | BSS compression benchmark | §4.2, line 981 | 「磁碟大小降低 ≥ 10%」 |
| 33 | T2.P2 | int encoding size benchmark | §4.2, line 982 | 「L7_processed ≤ 0.1 GB」 |
| 34 | T3.1 | multi-symbol IC isolation | §5.2, line 1062 | 「3 symbols × 1 tf」 |
| 35 | T3.2 | multi-symbol resume | §5.2, line 1063 | 「中斷後重跑」 |
| 36 | T3.B1 | RAM gate skip | §5.2, line 1069 | 「available RAM < 4GB」 |
| 37 | T3.B2 | symbol failure no checkpoint | §5.2, line 1070 | 「checkpoint 不寫入」 |
| 38 | T3.P1 | multi-symbol benchmark | §5.2, line 1076 | 「3 symbol serial 完成」 |
| 39 | T3.P2 | 10 symbol 2tf resume dryrun | §5.2, line 1077 | 「磁碟 extrapolation ≤ 18 GB」 |
| **合計** | **39 個** | | | |

#### Risk IDs（共 8 個）

| # | ID | 風險簡述 | SPEC 原文位置 | 原文節錄（≤30 字） |
|---|-----|---------|-------------|-----------------|
| 1 | R1 | numpy 原地操作浮點誤差 | §8, line 1174 | 「float32 vs float64」 |
| 2 | R2 | pandas rolling.rank constant behavior 版本相依 | §8, line 1175 | 「版本相依」 |
| 3 | R3 | zscore int16 overflow | §8, line 1176 | 「超過 ±32.767」 |
| 4 | R4 | IC-First L7 schema 不相容 | §8, line 1177 | 「舊 parquet 無法讀取」 |
| 5 | R5 | group parquet 讀取失敗導致 IC 低估 | §8, line 1178 | 「某 group parquet 讀取失敗」 |
| 6 | R6 | gc 後 OS RSS 不一定下降 | §8, line 1179 | 「allocator 保留 heap」 |
| 7 | R7 | IC selected JSON stale | §8, line 1180 | 「cache 未更新」 |
| 8 | R8 | byte_stream_split ROI 不足 | §8, line 1181 | 「ROI 不足 10%」 |
| **合計** | **8 個** | | | |

#### Phase Gate 條件（共 5 個）

| # | Gate | 條件摘要 | SPEC 原文位置 | 原文節錄（≤30 字） |
|---|------|---------|-------------|-----------------|
| 1 | Phase 0 → Phase 1 | T0 全綠 + T0.P1 ≤ 3,000s | §6, line 1094 | 「T0.1~T0.5 全通過」 |
| 2 | Phase 1 → Phase 2 | T1 全綠 + T1.P1/P2/P3 | §6, line 1095 | 「T1.P3 Frozen 前必跑」 |
| 3 | Phase 2 → Phase 3 | T2 全綠；BSS ROI optional；T2.P2 | §6, line 1096 | 「codec 部分 optional」 |
| 4 | Phase 3 Gate | T3 全綠 + multi-symbol no OOM/resume | §6, line 1097 | 「10 symbols × 2 tf」 |
| 5 | SPEC Frozen | 所有 Gate + U-V2 confirmed/accepted risk | §6, line 1098 | 「U-V2-1~U-V2-3 已確認」 |
| **合計** | **5 個** | | | |

#### 硬約束 IDs（共 17 個）

| # | ID | 約束描述 | 驗收條件 | SPEC 原文位置 |
|---|-----|---------|---------|-------------|
| 1 | C-OPT-1 | 跨 tier 重複穩定 | tier repeat 無 OOM / SIGKILL | §1.1, line 223 |
| 2 | C-OPT-2 | 多 symbol 不 OOM | del+gc、per-group IC、RAM gate | §1.1, line 224 |
| 3 | C-OPT-3 | 最高數據品質 | no fake data；symbol isolation；roundtrip | §1.1, line 225 |
| 4 | C-OPT-4 | 最短可行計算時間 | Phase0 ≤3000s；Phase1 ≤250s | §1.1, line 226 |
| 5 | C-OPT-5 | 最小可行輸出檔案 | L7_raw ≤1.5GB；processed ≤0.25GB | §1.1, line 227 |
| 6 | C-OPT-6 | 不以刪特徵最佳化 | 434,982 features；L3 windows 不縮 | §1.1, line 228 |
| 7 | C-V2-1 | single-copy equivalence | schema/order/NaN exact；allclose | §1.1, line 229 |
| 8 | C-V2-2 | rank constant window 0.5 | 全常數 array rank=0.5 | §1.1, line 230 |
| 9 | C-V2-3 | gaussian batch equivalence | allclose rtol=1e-5 | §1.1, line 231 |
| 10 | C-V2-4 | rank uint16 roundtrip | max diff ≤1/(2W)；NaN exact | §1.1, line 232 |
| 11 | C-V2-5 | zscore/gaussian int16 roundtrip | max diff ≤0.001；NaN exact | §1.1, line 233 |
| 12 | C-V2-6 | IC-First L7 size | raw ≤1.5GB；processed ≤0.25GB | §1.1, line 234 |
| 13 | C-V2-7 | IC selection stability | diff/Jaccard/top-K/Spearman/proxy gates | §1.1, line 235 |
| 14 | C-V2-8 | BSS bit-exact | parquet roundtrip bit-exact | §1.1, line 236 |
| 15 | C-V2-9 | encoding metadata | registry JSON and mixed roundtrip | §1.1, line 237 |
| 16 | C-V2-10 | IC-First 8GB no OOM | run_ic_gate peak RSS <7GB | §1.1, line 238 |
| 17 | C-V2-11 | raw persist 後 memory budget | refs deleted；available RAM + peak budget | §1.1, line 239 |
| **合計** | **17 個** | | | |

### E. SPEC §0 Agent 規範子節清單

| # | 子節編號 | 主題 | 與哪些 Task 相關 |
|---|---------|------|----------------|
| 1 | §0.A | 文件存取、反幻覺、提示注入防護 | 所有 Task |
| 2 | §0.0 | 不可違反最佳化原則 | 所有 Task |
| 3 | §0.1 | 解耦/架構規則 | 1.1, 1.2, 1.3, 1.4, 3.1 |
| 4 | §0.2 | Logging 規範 | 所有實作 Task |
| 5 | §0.3 | Error Handling 模式 | 1.3, 1.4, 2.1, 2.2, 3.1 |
| 6 | §0.4 | 命名規範 | 所有新增 env/schema/path Task |
| 7 | §0.5 | Type Hints 要求 | 所有 Python Task |
| 8 | §0.6 | 測試規範 | [補充] 0.0 與所有 Phase Test |
| 9 | §0.7 | 效能程式碼慣例 | 0.1~0.5, 1.3, 1.4, 2.1, 3.1 |
| 10 | §0.8 | 向後相容與回退 | 0.1, 1.1, 2.1, 2.2, 3.1 |
| 11 | §0.9 | Pre-Commit Checklist | 所有 Task |

### F. SPEC 引用的程式碼檔案

| # | 檔案路徑 | 出現在 SPEC §X.X |
|---|---------|----------------|
| 1 | `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | §0.A, §2.1, §3.1 |
| 2 | `momentum/FeatureEngineering/feature_factory.py` | §0.A, §3.1 |
| 3 | `momentum/FeatureEngineering/feature_storage.py` | §0.A, §3.1, §4.1 |
| 4 | `momentum/Analysis/ic_engine.py` | §0.A, §3.1 |
| 5 | `api/services/ic_analysis_service.py` | §3.1 |
| 6 | `api/services/feature_factory_batch_service.py` | §0.1, §3.1, §5.1 |
| 7 | `api/routes/ic_analysis.py` | §3.1 |
| 8 | `api/routes/feature_factory.py` | §5.1 |
| 9 | `momentum/core/config.py` | §0.1 |
| 10 | `momentum/factories.py` | §0.1 |
| 11 | `momentum/FeatureEngineering/feature_reader.py` | [補充] 現有 V7 parquet reader，受 Task 1.2 V2 path 影響 |
| 12 | `tests/conftest.py` | §7 |
| 13 | `scripts/benchmark_l65_v2.py` | §1.0, §1.1, §1.2, §2.2, §3.2, §4.2, §5.2 |
| 14 | `scripts/build_l65_golden.py` | §1.4 |

### G. 環境變數 / Feature Flag / 設定項

| # | 名稱 | 用途 | 出現在 SPEC §X.X |
|---|------|------|----------------|
| 1 | `FFACT_L65_OPTIMIZATION_PROFILE` | Phase 0 optimized/legacy profile | §0.8, §2.1 |
| 2 | `FFACT_IC_FIRST_PIPELINE` | Phase 1 IC-First on/off | §0.4, §0.8, §3.1 |
| 3 | `FFACT_L7_CODEC_UPGRADE` | Phase 2 codec upgrade on/off | §0.8, §4.1 |
| 4 | `FFACT_MULTI_SYMBOL_IC_FIRST` | Phase 3 IC-First batch on/off | §0.8, §5.1 |
| 5 | `allow_partial_ic` | IC group read failure partial mode | §0.3, §3.1 |
| 6 | `ic_gate_required_available_gb` | IC Gate 前 available RAM budget | §3.1 |
| 7 | `tier_peak_budget_gb` | run_ic_gate peak RSS budget | §3.1 |
| 8 | `l7_encoding_registry` | parquet schema metadata key | §0.4, §4.1 |
| 9 | `schema_version` | `raw_v1` / `processed_v1` | §0.4, §3.1 |

### H. SPEC 引用的外部文件

| # | 檔案路徑 | 出現在 SPEC §X.X | 狀態 |
|---|---------|----------------|------|
| 1 | `.github/copilot-instructions.md` | §0 | ✅ 已讀 |
| 2 | `docs/ARCHITECTURE.md` | §0, Appendix B | ✅ 已讀 |
| 3 | `docs/DEVELOPMENT_GUIDE.md` | §0, Appendix B | ✅ 已讀 |
| 4 | `docs/L65_OPTIMIZATION_PLAN_V2.md` | header, Appendix B | ✅ 已讀 V2 關鍵章節 |
| 5 | `docs/L65_OPTIMIZATION_SPEC.md` | header, Appendix B | ✅ 已讀 V1 關鍵章節 |
| 6 | `docs/L65_OPTIMIZATION_TODO.md` | header, Appendix B | ✅ 已讀 V1 TODO 結構重點 |
| 7 | `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` | §3.5 | 需外部 review 時使用 |

---

## 交付物 #1.5 — 矛盾與過時檢測報告

### 發現的矛盾（共 5 個）

| # | 類型 | 來源 A | 來源 B | 矛盾描述 | 建議 |
|---|------|-------|-------|---------|------|
| 1 | SPEC vs 程式碼 | SPEC Task 1.2 | `feature_storage.py` | SPEC 提到 legacy `write()`，現有類別主要為 `save_factory_output()` 與 `persist_registry_to_parquet()`，沒有同名 `write()` | TODO 中以「legacy writer」泛稱；新增 V2 method 不覆蓋現有 method |
| 2 | SPEC vs 程式碼 | SPEC Task 1.2 / 1.3 | `feature_reader.py` | SPEC canonical path 是 `{symbol}/{tf}/{config_hash}/raw`，現有 reader 讀 `{symbol}/{config_hash}` | Task 1.2 必須同步更新 FeatureReader V2 path + legacy fallback |
| 3 | SPEC vs 程式碼 | SPEC Task 1.1 | `feature_factory.py::_layer6_5_preprocessing(all_features, config)` | SPEC 偽碼用 `groups: Dict[str, DataFrame]`；現有函式簽名回傳 DataFrame，CGSA path 透過 registry side effect | Task 1.1 保留 DataFrame/CGSA 雙路徑，不強行 dict-only API |
| 4 | SPEC vs 程式碼 | SPEC Task 1.3 | `ic_engine.py` | SPEC 要求 `compute_ic_from_l7_raw()`，現有 `ICEngine` 只提供 in-memory `compute_ic()` | 新增 method/result dataclass；不改壞既有 API |
| 5 | 憲法 vs SPEC 潛在矛盾 | SPEC Task 1.3 | ARCH Rule 1-3 | 若讓 `momentum/Analysis` import `api.services` 會違反 Rule 1 | IC core 只加純 momentum method；API service 透過 factory/Protocol 呼叫 |

### 過時風險（共 2 個）

| # | 文件 | 問題 | 影響的 SPEC 章節 |
|---|------|------|----------------|
| 1 | `docs/ARCHITECTURE.md` | Artifact table 仍寫 Feature 輸出為 HDF5，但現有 V7 已有 per-group parquet writer/reader | Task 1.2 / 1.3 |
| 2 | `docs/ARCHITECTURE.md` | FeatureReader V7 路徑仍是 `{symbol}/{config_hash}`，未包含 timeframe/raw/processed 分層 | Task 1.2 / 1.3 |

### 結論

- [ ] 無矛盾，可繼續
- [x] 有矛盾但不阻塞 TODO 生成（已在 Task 中標注）
- [ ] 有嚴重矛盾，建議人工確認後再繼續

---

## 交付物 #2 — 完整 TODO 文件內容

## 0. 全域規則與約束（從 SPEC §0 + §1 提取）

### 0.1 必遵開發規則

1. **解耦與架構**：`momentum/FeatureEngineering/`、`momentum/Analysis/` 禁止 import `api.*`；API service 透過 `momentum.factories` 或 Protocol 呼叫 core。驗證：`grep -r 'from api\.' momentum/FeatureEngineering momentum/Analysis | wc -l` 必須為 0。
2. **Logging**：使用本 domain logger；不可用 `print()`；不得在 per-column/per-group inner loop spam log。
3. **Error Handling**：IC read 預設 fail-closed；`allow_partial_ic=True` 只可產 partial quality，不能通過 Frozen；codec encode fail fallback float32，不 clip。
4. **命名與 Metadata**：env flag 由 `momentum/core/config.py` 解析；schema version 固定 `raw_v1` / `processed_v1`；encoding registry key 固定 `l7_encoding_registry`。
5. **Type Hints**：Python 3.9 相容，使用 `typing.Optional` / `List` / `Dict`，不使用 `X | Y`。
6. **效能**：IC raw 必須 per-group streaming；full-schema gate 不得全量 `pd.concat` readback。
7. **Fallback**：`FFACT_L65_OPTIMIZATION_PROFILE=legacy`、`FFACT_IC_FIRST_PIPELINE=0`、`FFACT_L7_CODEC_UPGRADE=0`、`FFACT_MULTI_SYMBOL_IC_FIRST=0` 必須能回退。

### 0.2 硬約束與驗收標準

| ID | 約束 | 驗收條件 | 驗證方式 |
|----|------|---------|----------|
| C-OPT-1 | 跨 tier 重複穩定 | 8/16/24/32GB repeat=3 無 OOM/SIGKILL | benchmark |
| C-OPT-2 | 多 symbol 不 OOM | raw persist 後 gc；IC per-group；RAM gate | pytest + psutil |
| C-OPT-3 | 最高數據品質 | no fake data；selected JSON per symbol/tf；roundtrip gate | golden + tests |
| C-OPT-4 | 最短可行時間 | Phase0 ≤3000s；Phase1 ≤250s | benchmark |
| C-OPT-5 | 最小可行輸出 | L7_raw ≤1.5GB；processed ≤0.25GB | file size gate |
| C-OPT-6 | 不以刪特徵最佳化 | L1-L6 434,982 features；L3 windows 不縮 | schema/count diff |
| C-V2-1 | single-copy equivalence | schema/order/NaN exact；allclose | T0.1 |
| C-V2-2 | rank constant 0.5 | full constant window rank=0.5 | T0.B1 |
| C-V2-3 | gaussian batch equivalence | allclose rtol=1e-5 | T0.5 |
| C-V2-4 | rank uint16 roundtrip | max diff ≤1/(2W)；NaN exact | T2.2 |
| C-V2-5 | zscore/gaussian int16 roundtrip | max diff ≤0.001；NaN exact | T2.3 |
| C-V2-6 | IC-First L7 size | raw ≤1.5GB；processed ≤0.25GB | T1.P2 |
| C-V2-7 | IC selection stability | IC diff/Jaccard/top-K/Spearman/proxy gates | T1.3 |
| C-V2-8 | BSS bit-exact | parquet roundtrip bit-exact | T2.1 |
| C-V2-9 | encoding metadata | registry exists；mixed roundtrip correct | T2.4 |
| C-V2-10 | 8GB IC-First no OOM | run_ic_gate peak RSS <7GB | T1.P1/T1.P3 |
| C-V2-11 | raw persist memory budget | refs deleted；available RAM + peak budget pass | T1.4 |

### 0.3 每 Phase 通用驗收流程

1. 跑該 Phase unit/boundary tests。
2. 跑 short-window gate：`scripts/benchmark_l65_v2.py --tier=8gb --symbols=ETHUSDT --tfs=1h --max-rows=2000`。
3. Frozen 前跑 full-schema streaming gate：`scripts/benchmark_l65_v2.py --tier=8gb --symbols=ETHUSDT --tfs=1h,12h --full-schema --streaming-checks`。
4. 比對 golden：schema diff empty、NaN mask exact、IC stability pass。
5. 8/16/24/32GB tier repeat=3。
6. 切 fallback env var，確認可回 legacy baseline。

### 0.4 Pre-Commit Checklist

```text
□ grep -r 'from api\.' momentum/FeatureEngineering momentum/Analysis → 0
□ 所有新增/修改函式有 Python 3.9 相容 type hints
□ 測試可用 ./venv/bin/pytest 單獨執行，不依賴 run_api.py
□ fallback env var 可切回 baseline
□ 8GB tier benchmark 無 OOM / SIGKILL
□ roundtrip gates 通過
□ persist_l7_raw 後有 del + gc.collect()，IC Gate 前 memory budget 通過
□ IC engine per-group streaming，不一次全載
□ logging 不在 per-column/per-group inner loop
```

### 0.5 全域前置條件

- [ ] `scripts/benchmark_l65_v2.py` 與 `scripts/build_l65_golden.py --mode=ic_first` 已由 [補充] Task 0.0 建立或延伸。
- [ ] `tests/golden/l65/tier2_icfirst/` 可寫。
- [ ] `./venv/bin/pytest` 可用；slow/full-schema tests 有 skip/block reason，不可用 fake market data 代替。
- [ ] V1 Phase 0 Task 0.6 multi-symbol RAM gate/checkpoint 完成後才執行 Phase 3。

### 0.6 不可 Frozen 的人工確認項

以下項目在實作與 benchmark 完成後仍必須由 User / 架構負責人確認；未確認前只能標 `accepted risk`，不得把 TODO 或 SPEC 標 Frozen：

| ID | 決策項 | 最低必要證據 | 未確認前保守行為 |
|----|--------|--------------|----------------|
| U-V2-1 | IC-First 後 selected feature count 是否符合研究目標 | 真實 full-schema run 的 selected count、threshold、IC 分布、下游 proxy 指標 | 不把 selected count 當固定常數；只用 C-V2-7 stability gate 判斷可用性 |
| U-V2-2 | rank integer encoding 是否支援所有 config windows 與 sentinel 規則 | 每個 window 的 registry roundtrip、NaN sentinel collision test | `window` 必須 per-column metadata；缺 window 或 window≤0 一律 fallback float32 |
| U-V2-3 | `data_fingerprint` 是否需納入額外 business metadata | fingerprint 欄位清單、cache miss/hit 測試、label horizon/split metadata | 缺 symbol/tf/time_range/row_count/source checksum/schema hash/config hash/algorithm version/IC params/label horizon/split 任一欄位即 cache miss |

### 0.7 補充測試定義與命令矩陣

[補充] 測試不可只出現在 Task 描述中；若新增 Test ID，必須在此定義名稱、通過條件與命令。

| Test ID | 名稱 | 通過條件 | 建議命令 |
|---------|------|---------|----------|
| T0.S1 | `test_l65_v2_benchmark_cli_help` | CLI 存在，`--help` exit 0，列出 `--phase/--tier/--ic-first/--full-schema/--streaming-checks` | `./venv/bin/python scripts/benchmark_l65_v2.py --help` |
| T0.S2 | `test_l65_v2_golden_builder_cli_help` | golden builder 支援 `--mode=ic_first`；缺真實資料時回 `blocked_missing_data`，不得產 fake market data | `./venv/bin/python scripts/build_l65_golden.py --mode=ic_first --help` |
| T0.B5 | `test_zscore_constant_window_legacy_equivalence` | constant/single-observation window 的 NaN/0 行為與 legacy 完全一致；若 SPEC 假設 `std=0 → 0` 與 legacy 不同，必須 fallback 或改 SPEC | `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_zscore_constant_window_legacy_equivalence` |
| T1.B5 | `test_ic_selection_no_oos_leakage` | IC selected JSON 必含 training window / split / label horizon；backtest 或 ML OOS 驗證不得用 full-history labels 生成 selection | `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py::test_ic_selection_no_oos_leakage` |
| T2.S1 | `test_phase2_skip_evidence_manifest` | 跳過 Phase 2 時必須寫 skip evidence JSON，含 file sizes、FracDiff 狀態、float32 fallback count、config hash、schema hash | `./venv/bin/pytest tests/feature_engineering/test_l7_codec.py::test_phase2_skip_evidence_manifest` |

### 0.8 Phase 2 Skip Evidence 最低規格

Phase 2 可以 skip，但不能口頭 skip。任何 skip 都必須留下 `phase2_skip_evidence.json`，至少包含：`symbol`、`tf`、`config_hash`、`feature_schema_hash`、`l7_raw_size_bytes`、`l7_processed_size_bytes`、`fracdiff_enabled`、`float32_fallback_group_count`、`pyarrow_version`、`reason`、`created_at`。若缺 evidence，Phase 2 Gate 一律 FAIL。

## 執行策略（最少批次計劃）

```text
Batch 1: [補充] Task 0.0 + Task 0.3 + Task 0.5
Batch 2: Task 0.1
Batch 3: Task 0.2 + Task 0.4
Batch 4: Task 1.1
Batch 5: Task 1.2
Batch 6: Task 1.3
Batch 7: Task 1.4
Batch 8: Task 2.1 + Task 2.2（可依 skip 條件跳過）
Batch 9: Task 3.1（條件性）
Batch 10: Task 3.2（OPTIONAL / deferred；僅使用者明確要求 CSR API 時執行）
```

| Batch | 包含項目 | 依賴前置 | Gate |
|-------|---------|---------|------|
| 1 | [補充] 0.0, 0.3, 0.5 | 無 | T0.3, T0.5, T0.B1, T0.B4 smoke |
| 2 | 0.1 | Batch 1 | T0.1 |
| 3 | 0.2, 0.4 | Batch 2 | T0.1~T0.5, T0.B1~B4, T0.P1 |
| 4 | 1.1 | Phase 0 Gate | T1.1, T1.B3 |
| 5 | 1.2 | Batch 4 | T1.2, T1.5 |
| 6 | 1.3 | Batch 5 | T1.3, T1.B2, T1.B2a, T1.B4 |
| 7 | 1.4 | Batch 4-6 | T1.4, T1.P1, T1.P2, T1.P3 |
| 8 | 2.1, 2.2 | Phase 1 Gate | T2.x or skip evidence |
| 9 | 3.1 | Phase 1 Gate + V1 Task 0.6 | T3.x |
| 10 | 3.2 | explicit CSR request | separate CSR tests |

## Phase 0 — Per-Transform 微優化

### [補充] Task 0.0 — V2 測試 / Golden / Benchmark 基礎建設

- [x] **SPEC ref**: [補充] 由 SPEC §1.0、§1.2、§1.4、§7 推導。
- [x] **目標**: 建立 V2 tests/golden/benchmark 可執行基礎。
- [x] **輸入**: SPEC V2、既有 benchmark/golden scripts、`tests/conftest.py`。
- [x] **輸出**: `scripts/benchmark_l65_v2.py`、`scripts/build_l65_golden.py --mode=ic_first`、fixtures、golden dir。
- [x] **實作要點**:
  - CLI 支援 `--phase`, `--tier`, `--ic-first`, `--full-schema`, `--streaming-checks`, `--resume-check`, `--check-bss-roi`。
  - benchmark summary 至少含 wall time、peak RSS、available RAM、L7 sizes、schema count、OOM status。
  - full-schema gate 只做 per-group streaming checksum/schema/count。
  - Edge: 缺真實資料時回 `blocked_missing_data`，不得產 fake market data。
  - Edge: `--help` 必須 exit 0。
- [x] **修改檔案**: `scripts/benchmark_l65_v2.py → run_l65_v2_benchmark()`；`scripts/build_l65_golden.py → build_ic_first_golden()`；`tests/conftest.py → synthetic_l65_dataset(), ic_first_factory()`。
- [x] **不可做**: 不可全量 concat readback；不可用 fake market data 代替 benchmark。
- [x] **風險緩解**: C-OPT-1~3, C-V2-10/11。
- [x] **驗證**: [補充] T0.S1/T0.S2 CLI smoke。

### Task 0.1 — 多 transform 單次複製 + numpy 直接操作

- [x] **SPEC ref**: Task 0.1；C-V2-1；R1。
- [x] **目標**: 將 L6.5 transform 從多次 `df.copy()` 收斂為一次 numpy copy + 最後結構 copy。
- [x] **輸入**: DataFrame path 或 CGSA registry group；現有 `_transform_single_group()` / `_transform_single()`。
- [x] **輸出**: optimized helper，schema/order/NaN exact，numeric allclose。
- [x] **實作要點**:
  - ⚠️ 現有 `_transform_single_group()` 是 registry/group/context side effect，需保留 registry 行為，另建 DataFrame helper。
  - 偽碼：select numeric columns → `arr = df[columns].to_numpy(copy=True)` → sequential transform → assign once to `result = df.copy()`。
  - 函式草案：`_transform_single_group_optimized(...) -> None`、`_transform_single_optimized_df(...) -> pd.DataFrame`。
  - Edge: no selected columns no-op；non-numeric columns 原樣保留；append mode 欄位順序與 legacy 一致。
- [x] **修改檔案**: `feature_preprocessor.py → _transform_single_group(), _transform_single(), _transform_single_group_optimized(), _transform_single_optimized_df()`；`momentum/core/config.py → get_l65_optimization_profile()`。
- [x] **不可做**: 不可改原始 df in-place；不可刪 legacy path；不可把 FracDiff/ADF slow path 誤塞 fast path。
- [x] **風險緩解**: R1；legacy fallback。
- [x] **驗證**: T0.1, T0.P1。

### Task 0.2 — winsorize numpy direct + 單次 quantile

- [x] **SPEC ref**: Task 0.2；C-V2-1；R1。
- [x] **目標**: 用一次 `np.nanquantile(arr, [lower_q, upper_q], axis=0)` 取上下界。
- [x] **輸入**: selected numeric array；winsor config。
- [x] **輸出**: `_winsorize_2d_inplace()`；NaN mask exact。
- [x] **實作要點**:
  - 偽碼：compute bounds → `np.clip(..., out=arr)`。
  - 函式草案：`_winsorize_2d_inplace(arr, lower_q, upper_q, method="linear") -> np.ndarray`。
  - Edge: all-NaN column 保持 NaN；`lower_q == upper_q` 合法；sigma method 保留現有語義。
- [x] **修改檔案**: `feature_preprocessor.py → _apply_winsorization(), _winsorize_2d_inplace()`。
- [x] **不可做**: 不可改 quantile interpolation；不可把全 NaN 填 0。
- [x] **風險緩解**: R1。
- [x] **驗證**: T0.2, T0.B2。

### Task 0.3 — rank 消除 constant_mask 多餘 rolling pass

- [x] **SPEC ref**: Task 0.3；C-V2-2；R2。
- [x] **目標**: 驗證 pandas rolling.rank constant behavior 後，安全移除 max/min rolling pass。
- [x] **輸入**: `_apply_rank_transform()`；rank window/mode。
- [x] **輸出**: rank output constant window=0.5，legacy equivalent。
- [x] **實作要點**:
  - 先加 `test_rank_constant_window()` 鎖定目前 pandas 行為。
  - Path A：pandas already 0.5 → 移除 max/min pass；Path B：使用 rolling.std() 單 pass fallback。
  - 函式草案：`_rolling_rank_2d_v2(arr: np.ndarray, window: int) -> np.ndarray`。
  - Edge: constant column 0.5；NaN output preserved；single-value window 依 legacy 鎖定。
- [x] **修改檔案**: `feature_preprocessor.py → _apply_rank_transform(), _rolling_rank_2d_v2()`。
- [x] **不可做**: 不可把 rolling rank 改全歷史 rank；不可改 `pct=True` / `method="average"`。
- [x] **風險緩解**: R2。
- [x] **驗證**: T0.3, T0.B1。

### Task 0.4 — zscore 共用 rolling 物件 + 消除 copy

- [x] **SPEC ref**: Task 0.4；C-V2-1；R1。
- [x] **目標**: 每 window 共用 rolling object，接入 single-copy path。
- [x] **輸入**: selected array/DataFrame；windows；epsilon；mode。
- [x] **輸出**: `_rolling_zscore_2d()`；replace/append semantics preserved。
- [x] **實作要點**:
  - 偽碼：`r = df.rolling(window, min_periods=1); mean = r.mean(); std = r.std(); z=(df-mean)/(std+epsilon)`。
  - 函式草案：`_rolling_zscore_2d(arr, windows, epsilon, mode) -> Union[np.ndarray, Dict[int, np.ndarray]]`。
  - Edge: `windows=[]` no-op；constant/single-observation window 的 NaN/0 行為必須先由 T0.B5 鎖定 legacy；不得直接把 `std=0` 全部改成 0 除非 legacy equivalence 通過；NaN preserved；append column order legacy。
- [x] **修改檔案**: `feature_preprocessor.py → _apply_adaptive_zscore(), _rolling_zscore_2d()`。
- [x] **不可做**: 不可改 replace/append suffix naming；不可刪 epsilon。
- [x] **風險緩解**: R1。
- [x] **驗證**: T0.4, T0.B3, T0.B5。

### Task 0.5 — Gaussian DataFrame 批次化 + ndtri

- [x] **SPEC ref**: Task 0.5；C-V2-3；R3。
- [x] **目標**: 將 per-column loop 改為 DataFrame rank + vectorized `scipy.special.ndtri`。
- [x] **輸入**: numeric selected columns；clip range；mode。
- [x] **輸出**: `_gaussian_2d()`；allclose rtol=1e-5。
- [x] **實作要點**:
  - 偽碼：`ranked_df = selected.rank(pct=True)` → clip → `ndtri(vals)`。
  - 函式草案：`_gaussian_2d(arr, lower=0.001, upper=0.999) -> np.ndarray`。
  - Edge: NaN preserved；constant column 0.5；`HAS_SCIPY=False` 保持 warning + skip。
- [x] **修改檔案**: `feature_preprocessor.py → _apply_gaussian_normalize(), _gaussian_2d()`。
- [x] **不可做**: 不可改成 rolling rank；不可填 NaN 為 0。
- [x] **風險緩解**: R3。
- [x] **驗證**: T0.5, T0.B4。

### Phase 0 測試清單

| ☐ | Test ID | 測試名稱 | 驗證內容 |
|---|---------|---------|---------|
| [x] | T0.1 | `test_single_copy_equivalence` | optimized vs legacy schema/NaN/allclose |
| [x] | T0.2 | `test_winsorize_numpy_equivalence` | numpy quantile vs pandas quantile |
| [x] | T0.3 | `test_rank_constant_mask_removed` | rank output vs legacy |
| [x] | T0.4 | `test_zscore_shared_rolling` | shared rolling vs legacy |
| [x] | T0.5 | `test_gaussian_batch_equivalence` | ndtri batch vs erfinv loop |
| [x] | T0.B1 | `test_rank_constant_window` | full constant window rank=0.5 |
| [x] | T0.B2 | `test_winsorize_all_nan_column` | NaN mask exact |
| [x] | T0.B3 | `test_zscore_empty_windows` | no-op / no append |
| [x] | T0.B4 | `test_gaussian_nan_column` | NaN mask exact |
| [x] | T0.P1 | `benchmark_phase0_transform` | 8GB short-window L6.5 ≤3000s |

### Phase 0 → Phase 1 Gate

- [x] T0.1~T0.5 通過。
- [x] T0.B1~T0.B4 通過。
- [x] T0.P1 通過。
- [x] `FFACT_L65_OPTIMIZATION_PROFILE=legacy` 可回退。

## Phase 1 — IC-First Pipeline

### Task 1.1 — FeatureFactory pre/post IC 兩段式 pipeline

- [x] **SPEC ref**: Task 1.1；C-V2-7；R4。
- [x] **目標**: pre_ic 只做 winsor + FracDiff L1/L2；post_ic 只對 selected features 做 rank/zscore/gaussian。
- [x] **輸入**: L1-L6 features / CGSA registry；FactoryConfig；selected features。
- [x] **輸出**: `_layer6_5_legacy()`, `_layer6_5_pre_ic()`, `_layer6_5_post_ic()`。
- [x] **實作要點**:
  - ⚠️ 現有 `_layer6_5_preprocessing(all_features, config)` 為 DataFrame/CGSA side-effect path，需保留 compatible signature。
  - 偽碼：if env off → legacy；selected is None → pre_ic；selected list → post_ic。
  - 函式草案：`_layer6_5_preprocessing(..., selected_features: Optional[List[str]] = None) -> pd.DataFrame`。
  - Edge: selected empty → empty output + warning；CGSA registry 不 finalize 兩次；env off byte/allclose legacy。
- [x] **修改檔案**: `feature_factory.py → _layer6_5_preprocessing(), _layer6_5_legacy(), _layer6_5_pre_ic(), _layer6_5_post_ic()`；`momentum/core/config.py → get_ic_first_pipeline_enabled()`。
- [x] **不可做**: pre_ic 不做 rank/zscore/gaussian；post_ic 不讀全量 features；不刪 legacy。
- [x] **風險緩解**: R4；`FFACT_IC_FIRST_PIPELINE=0` fallback。
- [x] **驗證**: T1.1, T1.B3。

### Task 1.2 — FeatureStorage raw/processed 雙路徑 + Reader 合約

- [x] **SPEC ref**: Task 1.2；C-V2-9；R4, R7。
- [x] **目標**: 建立 canonical V2 path、atomic manifest、schema metadata，並讓 writer/reader 同路徑。
- [x] **輸入**: symbol, tf, config_hash, groups/registry。
- [x] **輸出**: `data_cache/features/{symbol}/{tf}/{config_hash}/raw|processed` + `feature_manifest.json`。
- [x] **實作要點**:
  - ⚠️ 現有 `persist_registry_to_parquet()` 與 `FeatureReader` 路徑為 `{symbol}/{config_hash}`；新增 V2 helpers，不破壞 legacy。
  - 偽碼：write `.tmp-{uuid}` → validate → atomic replace → final manifest `complete=true`。
  - 函式草案：`feature_run_dir(symbol, tf, config_hash)`, `write_raw()`, `write_processed()`, `load_manifest_v2()`, `stream_groups_v2()`。
  - Edge: existing dir atomic replace；`write_raw()` 收到 empty groups 必須 fail-closed（raw 應代表 ALL winsorized features，空 raw 會違反 C-OPT-6）；只有 `write_processed()` 在 T1.B1 empty selection 情境可產 `total_features=0` 且 `quality_status="empty_selection"` 的 complete manifest；old parquet no metadata uses legacy float path。
- [x] **修改檔案**: `feature_storage.py → feature_run_dir(), write_raw(), write_processed(), _write_feature_manifest_v2()`；`feature_reader.py → load_manifest_v2(), stream_groups_v2(), load_columns_v2()`；`momentum/factories.py` if needed。
- [x] **不可做**: 不可破壞 HDF5/V7 legacy writer；不可讓 temp dir cache hit；raw 不寫 rank/zscore。
- [x] **風險緩解**: R4, R7。
- [x] **驗證**: T1.2, T1.5, T2.B4。

### Task 1.3 — IC Gatekeeper per-group 迭代讀 L7_raw

- [x] **SPEC ref**: Task 1.3；C-V2-7, C-V2-10；R5, R7。
- [x] **目標**: 新增 raw streaming IC computation，逐 group 讀 parquet 計算 IC，atomic write selected JSON。
- [x] **輸入**: V2 raw manifest, label config, IC params, `allow_partial_ic`。
- [x] **輸出**: `ICSelectionResult` 與 `ic_selected_features_{symbol}_{tf}.json`。
- [x] **實作要點**:
  - ⚠️ 現有 `ICEngine.compute_ic()` 是 in-memory API；新增 `compute_ic_from_l7_raw()`，不破壞 existing API。
  - 偽碼：validate manifest → for group in reader.stream_groups_v2(raw) compute IC → del/gc → threshold select → atomic JSON。
  - 函式草案：`compute_ic_from_l7_raw(symbol, tf, config_hash, *, allow_partial_ic=False) -> ICSelectionResult`。
  - IC selection 必須防止 train-test contamination：selected JSON 需記錄 `label_horizon`、`selection_window` / `split_id`、IC params；ML/backtest OOS 驗證不得用 full-history labels 產生 selected list。
  - Edge: empty raw → fail-closed（raw empty 不是合法 IC 空選擇）；read failure fail-closed；fingerprint mismatch forces recompute；空選擇只能來自 valid raw + IC threshold 後 selected=[]。
- [x] **修改檔案**: `ic_engine.py → ICSelectionResult, ICReadError, compute_ic_from_l7_raw(), _write_ic_selected_json_atomic()`；`api/services/ic_analysis_service.py` service integration；`momentum/core/protocols.py` if injection needs stream Protocol。
- [x] **不可做**: 不可一次全載 raw；不可讀 processed；不可跨 symbol/tf 共用 selected JSON。
- [x] **風險緩解**: R5, R7。
- [x] **驗證**: T1.3, T1.B2, T1.B2a, T1.B4, T1.B5, service integration, T1.P3 scaffold。

### Task 1.4 — Post-IC Transform Service + GC 保護

- [x] **SPEC ref**: Task 1.4；C-V2-6, C-V2-10, C-V2-11；R6。
- [x] **目標**: 串接 pre_ic → write raw → del/gc + budget gate → IC streaming → post_ic selected → write processed。
- [x] **輸入**: raw path, selected list, config, memory tier config。
- [x] **輸出**: processed parquet + memory logs + `run_ic_first_pipeline()`。
- [x] **實作要點**:
  - 偽碼：run L1-L6/pre_ic → write_raw → `del pre_ic_groups; gc.collect()` → check available RAM → run IC → read selected only → post_ic → write_processed。
  - 函式草案：`transform_selected(selected, groups, config)`；`run_ic_first_pipeline(symbol, tf, config) -> FeatureFactoryResult`。
  - Edge: selected empty → processed manifest with 0 selected；available RAM below gate raises MemoryError; RSS fixed 5GB drop only diagnostic。
- [x] **修改檔案**: `feature_preprocessor.py → transform_selected()`；`feature_factory.py → run_ic_first_pipeline()` and memory helper integration。
- [x] **不可做**: 不可在釋放 pre_ic 前跑 IC；不可用 `resource.ru_maxrss` 判斷 gc 後當前 RSS；post_ic 不讀全量。
- [x] **風險緩解**: R6；available RAM + peak RSS gate。
- [x] **驗證**: T1.4, T1.B1, T1.P1, T1.P2, T1.P3。

### Phase 1 測試清單

| ☐ | Test ID | 測試名稱 | 驗證內容 |
|---|---------|---------|---------|
| [x] | T1.1 | `test_ic_first_pipeline_routing` | pre/post/env fallback |
| [x] | T1.2 | `test_l7_schema_version_metadata` | raw_v1/processed_v1 metadata |
| [x] | T1.3 | `test_ic_selection_stability` | C-V2-7 gates |
| [x] | T1.4 | `test_memory_budget_after_raw_persist` | refs deleted + budget pass |
| [x] | T1.5 | `test_feature_run_dir_and_manifest_atomicity` | complete=true only cache hit |
| [x] | T1.B1 | `test_ic_empty_selection` | empty processed + warning |
| [x] | T1.B2 | `test_ic_group_read_failure_fail_closed` | raise + no JSON |
| [x] | T1.B2a | `test_ic_group_read_failure_partial_mode` | partial quality cannot Frozen |
| [x] | T1.B3 | `test_ic_first_legacy_fallback` | legacy all features |
| [x] | T1.B4 | `test_ic_cross_symbol_isolation` | selected JSON isolated |
| [x] | T1.B5 | `test_ic_selection_no_oos_leakage` | label horizon / split metadata |
| [x] | T1.P1 | `benchmark_ic_first_single_symbol` | ≤250s, RSS <7GB |
| [x] | T1.P2 | `benchmark_l7_size_ic_first` | raw/processed size gates |
| [x] | T1.P3 | `benchmark_ic_first_full_schema_streaming` | scaffold full-schema streaming, no concat readback |

### Phase 1 → Phase 2 Gate

- [x] T1.1~T1.5 全通過。
- [x] T1.B1~T1.B4 + T1.B2a 全通過。
- [x] T1.P1/T1.P2 通過；T1.P3 Frozen 前必跑。
- [x] `FFACT_IC_FIRST_PIPELINE=0` 可回退。

## Phase 2 — L7 Codec 改善

### Phase 2 Skip 條件

- [ ] 若 Phase 1 後 L7_processed ≤0.1GB，可 skip Task 2.2 的「寫入整數 encoded parquet」部分；但不得跳過 backward-compatible reader、metadata absence test（T2.B4）與 skip evidence manifest（T2.S1）。
- [ ] 若 FracDiff OFF 且無 float32 fallback groups，可 skip Task 2.1；T2.P1 必須有 `phase2_skip_evidence.json`，不可只在 log 中宣稱 optional。

### Task 2.1 — byte_stream_split for float32 fallback groups

- [ ] **SPEC ref**: Task 2.1；C-V2-8；R8。
- [ ] **目標**: 對 float32 fallback columns 啟用 BYTE_STREAM_SPLIT，保持 bit-exact readback。
- [ ] **輸入**: Arrow table, output path, float32 fallback column list, codec flag。
- [ ] **輸出**: `_write_parquet_with_codec()`；BSS or zstd fallback parquet。
- [ ] **實作要點**:
  - 偽碼：if codec disabled/no cols → current zstd writer；else `pq.write_table(..., column_encoding={col: "BYTE_STREAM_SPLIT"})`。
  - 函式草案：`_write_parquet_with_codec(table, output_path, *, float32_cols, schema_metadata=None)`。
  - Edge: no float32 cols no encoding; PyArrow not support BSS → zstd fallback + warning; ROI <10% optional。
- [ ] **修改檔案**: `feature_storage.py → _write_parquet_with_codec(), _persist_parts_parallel()`；`momentum/core/config.py → get_l7_codec_upgrade_enabled()`。
- [ ] **不可做**: 不可對 float16 groups 強制 BSS；不可改 float16 gate；不可用 snappy 取代 zstd。
- [ ] **風險緩解**: R8。
- [ ] **驗證**: T2.1, T2.B3, T2.P1。

### Task 2.2 — 整數編碼 Registry

- [ ] **SPEC ref**: Task 2.2；C-V2-4, C-V2-5, C-V2-9；R3, R4。
- [ ] **目標**: 對 processed rank/zscore/gaussian columns 實作 per-column encode/decode + metadata registry。
- [ ] **輸入**: L7_processed table, transform metadata, codec flag。
- [ ] **輸出**: integer encoded parquet columns + `l7_encoding_registry` + read-time decode。
- [ ] **實作要點**:
  - rank：NaN sentinel 0；decode tolerance ≤1/(2W)。
  - zscore/gaussian：×1000 int16；sentinel -32768；overflow fallback float32，不 clip。
  - 函式草案：`encode_rank_as_uint16()`, `decode_rank_from_uint16()`, `encode_zscore_as_int16()`, `decode_zscore_from_int16()`。
  - Edge: rank window invalid fallback float32; zscore overflow fallback; mixed columns decode independently。
- [ ] **修改檔案**: `feature_storage.py` encode/decode helpers + registry builder；`feature_reader.py` metadata decode hook。
- [ ] **不可做**: 不可對 winsorize/FracDiff/L7_raw integer encode；不可弱化 float16 gate；不可 clip overflow。
- [ ] **風險緩解**: R3, R4。
- [ ] **驗證**: T2.2, T2.3, T2.4, T2.B1, T2.B2, T2.B4, T2.P2。

### Phase 2 測試清單

| ☐ | Test ID | 測試名稱 | 驗證內容 |
|---|---------|---------|---------|
| ☐ | T2.1 | `test_bss_roundtrip` | bit-exact parquet roundtrip |
| ☐ | T2.2 | `test_rank_uint16_roundtrip` | diff ≤1/(2W), NaN exact |
| ☐ | T2.3 | `test_zscore_int16_roundtrip` | diff ≤0.001, NaN exact |
| ☐ | T2.4 | `test_mixed_encoding_metadata_roundtrip` | registry + decode correct |
| ☐ | T2.B1 | `test_rank_nan_sentinel` | sentinel roundtrip |
| ☐ | T2.B2 | `test_zscore_overflow_fallback_float32` | no clip, fallback float32 |
| ☐ | T2.B3 | `test_bss_pyarrow_version_fallback` | zstd fallback |
| [x] | T2.B4 | `test_old_parquet_no_metadata` | legacy float path |
| ☐ | T2.S1 | `test_phase2_skip_evidence_manifest` | skip evidence JSON 完整 |
| ☐ | T2.P1 | `benchmark_bss_compression` | ROI ≥10% or optional |
| ☐ | T2.P2 | `benchmark_int_encoding_size` | processed ≤0.1GB |

### Phase 2 → Phase 3 Gate

- [ ] T2.1~T2.4 全通過，或 skip 條件有 `phase2_skip_evidence.json` 且 T2.S1 通過。
- [ ] T2.B1~T2.B4 全通過。
- [ ] T2.P1 通過或 optional；T2.P2 通過或 skip evidence。
- [ ] `FFACT_L7_CODEC_UPGRADE=0` 可回退。

## Phase 3 — 多 Symbol 工廠產線整合

### Phase 3 Skip 條件

- [ ] 若使用場景僅單 symbol，Phase 3 可 defer。
- [ ] 若 V1 Phase 0 Task 0.6 未完成，Phase 3 必須 defer。

### Task 3.1 — Sequential Symbol Execution with IC-First GC 鏈路

- [ ] **SPEC ref**: Task 3.1；C-OPT-2；R6。
- [ ] **目標**: 在 batch service sequential loop 中串聯 RAM gate → `run_ic_first_pipeline()` → checkpoint → per-symbol gc。
- [ ] **輸入**: `BatchGenerateRequest`, checkpoint JSON, symbol/tf queue, batch flag。
- [ ] **輸出**: 每 symbol/tf raw+processed+selected JSON + checkpoint completed/failed records。
- [ ] **實作要點**:
  - 偽碼：for item → `_ram_gate()` → skip completed → run IC-first → checkpoint success → always gc；MemoryError no completed checkpoint。
  - 函式草案：`_compute_single_ic_first(...)->Dict[str, str]` 或 structured output；legacy `_compute_single()` 保留。
  - Edge: RAM gate fail pause/skip; MemoryError no checkpoint; env off legacy。
- [ ] **修改檔案**: `api/services/feature_factory_batch_service.py → _run_batch(), _process_item_wave(), _compute_single(), _record_item_result()`；`momentum/factories.py` if wiring needed。
- [ ] **不可做**: 不可跨 symbol/tf 共用 selected JSON；不可 failed symbol 寫 completed checkpoint；不可省略 gc。
- [ ] **風險緩解**: R6；V1 RAM gate/checkpoint。
- [ ] **驗證**: T3.1, T3.2, T3.B1, T3.B2, T3.P1, T3.P2。

### Task 3.2 — Cross-Symbol Rank（OPTIONAL / DEFERRED）

- [ ] **SPEC ref**: Task 3.2。
- [ ] **目標**: 僅當使用者明確要求 CSR API 時，建立 cross-sectional rank 獨立批次。
- [ ] **輸入**: completed multi-symbol L7_raw manifests, aligned timestamps, requested columns。
- [ ] **輸出**: optional CSR artifact / API result。
- [ ] **實作要點**:
  - 偽碼：load selected columns per timestamp via streaming → align symbols → `rank(axis=0, method="average")` → write isolated CSR output。
  - 函式草案：`run_cross_symbol_rank(symbols, tf, config_hash, columns) -> Path`。
  - Edge: any incomplete raw manifest fail-closed; timestamp alignment missing reports dropped rows; requires separate API contract。
- [ ] **修改檔案**: Deferred；啟用時另建 mini SPEC/TODO。
- [ ] **不可做**: 不可混入 per-symbol loop；不可 raw incomplete 時 partial output；不可取代 per-symbol IC selected。
- [ ] **風險緩解**: optional/deferred boundary。
- [ ] **驗證**: 無原 SPEC Test ID；啟用時補 CSR-specific tests。

### Phase 3 測試清單

| ☐ | Test ID | 測試名稱 | 驗證內容 |
|---|---------|---------|---------|
| ☐ | T3.1 | `test_multi_symbol_ic_isolation` | selected JSON isolated |
| ☐ | T3.2 | `test_multi_symbol_resume` | completed skip, failed rerun |
| ☐ | T3.B1 | `test_ram_gate_skip` | low RAM pause/skip no OOM |
| ☐ | T3.B2 | `test_symbol_failure_no_checkpoint` | failure no completed checkpoint |
| ☐ | T3.P1 | `benchmark_multi_symbol_ic_first` | 3 symbols serial RSS <7GB/symbol |
| ☐ | T3.P2 | `benchmark_10_symbol_2tf_resume_dryrun` | 10 symbols ×2 tf resume/isolation/full-schema, disk ≤18GB |

### Phase 3 Gate

- [ ] T3.1~T3.2 全通過。
- [ ] T3.B1~T3.B2 全通過。
- [ ] T3.P1~T3.P2 通過。
- [ ] `FFACT_MULTI_SYMBOL_IC_FIRST=0` 可回退。

## SPEC Frozen Gate

- [ ] Phase 0 → 1 Gate 通過。
- [ ] Phase 1 → 2 Gate 通過，且 T1.P3 full-schema streaming gate 通過。
- [ ] Phase 2 → 3 Gate 通過或 skip evidence accepted。
- [ ] Phase 3 Gate 通過或 Phase 3 skip condition accepted。
- [ ] C-V2-7 IC stability gates 通過。
- [ ] U-V2-1, U-V2-2, U-V2-3 已人工確認或標 accepted risk。
- [ ] 外部 adversarial review 完成且 blocking findings 已修補。

---

## 交付物 #3 — 自主驗證報告

### Pass 1：追溯完整性

| 類型 | SPEC 數量 | TODO 覆蓋數量 | 缺失 |
|------|-----------|---------------|------|
| Task IDs | 13 | 13（另有 [補充] Task 0.0） | 0 |
| Test IDs | 39 | 39（另有 [補充] T0.S1/T0.S2/T0.B5/T1.B5/T2.S1，已於 §0.7 定義） | 0 |
| Risk IDs | 8 | 8 | 0 |
| Phase Gates | 5 | 5 | 0 |
| Hard Constraints | 17 | 17 | 0 |
| SPEC §0 子節 | 11 | 11 | 0 |

### Pass 2A：模板結構完整性

| 必要段落 | 存在? | 判定 |
|---------|------|------|
| Header / status / SPEC ref | ✅ | PASS |
| SPEC index | ✅ | PASS |
| 矛盾與過時報告 | ✅ | PASS |
| Global rules / constraints / checklist | ✅ | PASS |
| Batch execution plan | ✅ | PASS |
| Phase 0-3 tasks | ✅ | PASS |
| Phase test tables + gates | ✅ | PASS |
| Autonomous validation report | ✅ | PASS |
| External review handoff | ✅ | PASS |

### Pass 2B：深度全掃描

| Task | 實作要點 ≥3? | 有偽碼/函式草案? | Edge ≥2? | 修改檔案到函式名? | 判定 |
|------|-------------|----------------|---------|----------------|------|
| [補充] 0.0 | ✅ | ✅ | ✅ | ✅ | PASS |
| 0.1 | ✅ | ✅ | ✅ | ✅ | PASS |
| 0.2 | ✅ | ✅ | ✅ | ✅ | PASS |
| 0.3 | ✅ | ✅ | ✅ | ✅ | PASS |
| 0.4 | ✅ | ✅ | ✅ | ✅ | PASS |
| 0.5 | ✅ | ✅ | ✅ | ✅ | PASS |
| 1.1 | ✅ | ✅ | ✅ | ✅ | PASS |
| 1.2 | ✅ | ✅ | ✅ | ✅ | PASS |
| 1.3 | ✅ | ✅ | ✅ | ✅ | PASS |
| 1.4 | ✅ | ✅ | ✅ | ✅ | PASS |
| 2.1 | ✅ | ✅ | ✅ | ✅ | PASS |
| 2.2 | ✅ | ✅ | ✅ | ✅ | PASS |
| 3.1 | ✅ | ✅ | ✅ | ✅ | PASS |
| 3.2 | ✅ | ✅ | ✅ | Deferred | PASS |

### Pass 3：索引回驗報告

| SPEC ID | 索引記錄位置 | 重新查找結果 | 判定 |
|---------|-------------|--------------|------|
| Task 0.1 | §2.1 line 315 | 找到「多 transform 單次複製」 | PASS |
| Task 1.2 | §3.1 line 594 | 找到「raw/processed 雙路徑」 | PASS |
| Task 3.2 | §5.1 line 1048 | 找到「DEFERRED to Phase 3」 | PASS |

### Pass 4：一致性檢查

| 檢查項 | 結果 |
|--------|------|
| Task/Test/Risk/Gate/Constraint count 一致 | ✅ |
| 所有 Phase 結尾有 Test ID checklist | ✅ |
| 補充項目均標 `[補充]` | ✅ |
| 受矛盾影響 Task 均標 `⚠️` 或在 Task 描述中修補 | ✅ |
| 條件 Phase/Optional Task 有 skip/deferred path | ✅ |
| 執行策略 Batch 覆蓋所有 Task | ✅ |

### Pass 5：語義正確性報告

| 檢查項 | 結果 | 說明 |
|--------|------|------|
| Cross-Task 矛盾 | PASS | Task 1.2 vs 1.3 reader path 已補；Task 2.1/2.2 合併同 Batch |
| 實作可行性 | PASS | 每個 Task 有輸入/輸出/函式草案/edge cases |
| 程式碼引用 | PASS | 現有函式存在者已核對；不存在者標 new helper |
| 規則合規 | PASS | no api import in momentum、config parser、fallback path 均標註 |
| 資料流銜接 | PASS | pre_ic → raw → IC → selected → post_ic → processed → batch |
| Test-Task 對齊 | PASS | 39 個 SPEC Test ID 全覆蓋 |
| 驗證可執行性 | PASS | [補充] Task 0.0 補 benchmark/golden scaffold |
| 副作用與回歸風險 | PASS | legacy fallback 和 reader/writer compatibility 均列入 |
| 全棧整合完整性 | PASS | core/storage/API service/multi-symbol batch 均覆蓋；無前端需求 |

---

## 交付物 #3.5 — 外部 Adversarial Review Handoff

請使用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 審查本次產物。

變數填寫：

- `{{PLAN_FILE}}`: `docs/L65_OPTIMIZATION_PLAN_V2.md`
- `{{SPEC_FILE}}`: `docs/L65_OPTIMIZATION_SPEC_V2.md`
- `{{TODO_FILE}}`: `docs/L65_OPTIMIZATION_TODO_V2.md`
- `{{REVIEW_FOCUS}}`: `L6.5 / IC-First / multi-symbol OOM / codec metadata / cache isolation`
- `{{REVIEW_MODE}}`: TODO_ONLY
- `{{STRICTNESS}}`: MAXIMUM

外部 reviewer 請優先檢查：

1. Task 1.2 是否足以避免 FeatureStorage/FeatureReader V2 path split-brain。
2. U-V2-1 selected feature count、U-V2-2 rank window/sentinel、U-V2-3 data_fingerprint metadata 是否需人工決策。
3. C-V2-7、C-V2-10/11、C-V2-9、C-OPT-2 是否有 hidden gap。

---

## 交付物 #4 — TODO_ONLY Adversarial Review 修補紀錄（2026-05-07）

### Executive Verdict

| 欄位 | 判定 |
|------|------|
| Verdict | PASS WITH FIXES |
| 主要阻塞原因 | B1~B5 已在本文件就地修補；未重新跑 benchmark/test 前仍不可 Frozen |
| 最高風險區域 | IC-First leakage/cache fingerprint；raw/processed storage manifest；Phase 2 skip evidence |
| 是否建議 Frozen | No |

### 🔴 Blocking Findings（已修補）

| ID | 類型 | 位置/原文 | 問題 | 失敗模式/影響 | 驗證方式 | 必要修補 |
|----|------|-----------|------|---------------|----------|----------|
| B1 | 不可測 / 狀態誤導 | Header: `V1(Internal Frozen — Pending External Adversarial Review)`；Final: `V1(Internal Frozen...)` | 文件在尚未完成外部 review / U-V2 決策 / full-schema gate 前接近 Frozen 語義 | 下一位 Agent 可能把 TODO 當 Frozen 執行，跳過必要審查與人工確認 | 搜尋 `Internal Frozen`；檢查 Frozen Gate 是否仍未勾選 | 狀態改為 `V1 Review-Patched（Not Frozen）`；Final 同步改寫 |
| B2 | 漏項 / 不可驗收 | `Pass 1: Test IDs 39（另有 [補充] T0.S1/T0.S2）`；Task 0.0 驗證提到 `[補充] T0.S1/T0.S2` | 補充 Test ID 被納入覆蓋敘述，但沒有正式定義名稱、命令與通過條件 | Agent 無法實作或驗收 bootstrap scripts，可能用 smoke log 取代測試 | 搜尋 `T0.S1` / `T0.S2`，確認是否有定義表 | 新增 §0.7，定義 T0.S1/T0.S2/T0.B5/T1.B5/T2.S1 |
| B3 | Quant 假設 / 資料污染 | Task 1.3: `atomic write selected JSON`；未要求 `selection_window/split_id` | IC selected list 若用 full-history labels 建立，會污染 ML/backtest OOS 驗證 | IC selection 對未來資料或測試集過度擬合，讓後續 proxy/backtest 樂觀失真 | T1.B5：selected JSON 必含 label horizon / selection window / split；OOS 不用 full-history selection | Task 1.3 補 train-test contamination 防護與 fingerprint 欄位要求 |
| B4 | Cache / Gate 漏項 | Phase 2: `skip 條件有 evidence`、`ROI <10% optional` | skip evidence 沒有格式；可用口頭或 log 跳過 codec/metadata Gate | codec 不實作也能通過 Gate，導致 metadata/backward compatibility 未驗 | T2.S1 檢查 `phase2_skip_evidence.json` 欄位 | 新增 §0.8 與 T2.S1；Phase 2 Gate 改為必須有 skip evidence JSON |
| B5 | 數據品質 / C-OPT-6 | Task 1.2: `empty groups manifest complete but total_features=0` | raw 是 ALL winsorized features；raw empty 若 complete 會把失敗 generation cache 成成功 | 後續 IC 讀空 raw 得到空 selection，假性通過但實際刪掉所有特徵 | T1.5 + T1.B1：raw empty fail-closed；processed empty 僅允許 valid IC empty selection | Task 1.2 改為 `write_raw()` empty fail-closed；processed empty 需 `quality_status="empty_selection"` |

### 🟡 Important Findings（已修補或降風險）

| ID | 類型 | 位置/原文 | 問題 | 失敗模式/影響 | 驗證方式 | 建議修補 |
|----|------|-----------|------|---------------|----------|----------|
| I1 | 測試品質 | Task 0.4: `std=0 → 0` | pandas rolling std 對 single-observation 可能是 NaN；直接固定 0 可能改 legacy 語義 | zscore 邊界值與既有 baseline 不一致 | T0.B5 constant/single-observation legacy equivalence | Task 0.4 改為先鎖 legacy；不直接硬改 0 |
| I2 | Agent 可執行性 | `驗證方式: benchmark`、`file size gate` | 部分 Gate 只寫抽象驗證方式，缺實際 CLI 或測試 ID | Agent 可能只做手動觀察，不產可重跑證據 | §0.7 命令矩陣與 Phase test tables | 補命令矩陣；後續實作 PR 需把所有 abstract gate 轉成 pytest/CLI |
| I3 | 相容性 | `Review Mode: FULL` in handoff | 使用者本輪要求 TODO_ONLY；FULL 可能讓 reviewer 審上游 PLAN/SPEC 並擴大範圍 | 審查輸出偏離本輪目標，阻塞 TODO 內部修補 | 搜尋 `{{REVIEW_MODE}}` | Handoff 改成 TODO_ONLY |

### 🟢 Suggestions

| ID | 類型 | 位置/原文 | 建議 | 理由 |
|----|------|-----------|------|------|
| S1 | 文件維護 | §差異修復說明 | 後續每次外部 review 都新增 dated addendum，不覆蓋舊 finding | 保留審查歷史，避免重複踩同一 failure mode |
| S2 | 測試矩陣 | §0.7 | 實作時把補充測試 ID 回填 SPEC 或另開 TODO patch | 避免 SPEC/TODO Test count 永久不一致 |

### Coverage Matrix

| 檢查項 | 狀態 | 問題 ID |
|--------|------|---------|
| PLAN → SPEC 決策承接 | N/A | TODO_ONLY，不推定上游正確性 |
| SPEC → TODO Task 承接 | PASS WITH FIXES | B2, B5 |
| TODO 可執行性 | PASS WITH FIXES | B2, I2 |
| 驗收標準可測性 | PASS WITH FIXES | B2, B4, I2 |
| 跨 tier / no OOM | PASS | 無新增 blocking；既有 C-V2-10/11 + T1.P3/T3.P2 覆蓋 |
| 數據品質 / cache isolation | PASS WITH FIXES | B3, B4, B5 |
| 計算時間與 output size | PASS WITH FIXES | B4 |
| Quant finance assumptions | PASS WITH FIXES | B3, I1 |
| 測試品質 | PASS WITH FIXES | B2, I1, I2 |
| 過度工程 | PASS | 無 blocking；Phase 2 skip 已加 evidence 防止無效工程 |

### Untestable Requirements

| 原需求 | 問題 | 可測改寫 | 建議驗證方式 |
|--------|------|----------|--------------|
| `有 skip 條件有 evidence` | evidence 格式不明 | skip 必須產 `phase2_skip_evidence.json` 並通過 T2.S1 | `./venv/bin/pytest ...::test_phase2_skip_evidence_manifest` |
| `[補充] T0.S1/T0.S2 CLI smoke` | 未定義通過條件 | CLI `--help` exit 0，列出必要 flags；缺資料時 blocked 不 fake | T0.S1/T0.S2 |
| `std=0 → 0` | 未驗證是否符合 legacy | constant/single-observation zscore 必須 legacy equivalent | T0.B5 |

### Missing Items

| 缺漏項 | 應補位置 | 為何必要 | 建議內容 |
|--------|----------|----------|----------|
| U-V2 決策明細 | TODO | Frozen Gate 只列 ID，Agent 不知道要問什麼 | §0.6 已補 U-V2-1~3 |
| 補充 Test ID 定義 | TODO / 後續 SPEC patch | 避免 test count 與可驗收性落差 | §0.7 已補；後續同步 SPEC |
| Phase 2 skip manifest | TODO | 避免 optional codec 變成口頭跳過 | §0.8 已補 |
| IC selection split metadata | TODO | 防止 OOS leakage | Task 1.3 已補 |

### Questionable Industry Assumptions

| 假設 | 為何可疑 | 風險 | 更保守替代方案 | 驗證 Gate |
|------|----------|------|----------------|----------|
| IC selected list 可由 raw full data 直接產出 | Quant confidence: High。feature selection 若用 full-history label，會污染後續 OOS 驗證 | OOS/backtest proxy 被高估，特徵選擇過度擬合 | selected JSON 綁 training window/split；OOS 只用當時 training selection | T1.B5 + C-V2-7 |
| zscore constant window 可直接設 0 | Quant confidence: Medium。合理但必須與 legacy/ML preprocessing 語義一致 | 邊界 NaN/0 改變模型輸入分布 | 先鎖 legacy；必要時 accepted risk | T0.B5 |

### Overengineering Assessment

| 設計 | 是否過度工程 | 判斷理由 | 簡化方案 | 保留條件 |
|------|--------------|----------|----------|----------|
| IC-First raw/processed 雙路徑 | No | 直接對應 29.74GB/OOM failure mode，且保留 raw 全特徵 | 無，需保留 | C-V2-6/7/10/11 通過 |
| Phase 2 integer encoding + BSS | Potentially | IC-First 後 processed 可能已 ≤0.1GB，ROI 可能不足 | 以 skip evidence 延後寫入 encoding | T2.S1 + file size evidence |
| Cross-Symbol Rank | No（目前 Deferred）| 已標 optional，不阻塞主線 | 另開 mini SPEC/TODO | User 明確要求 CSR API |

### Required Patch Plan

| Priority | 修補項 | 修改文件 | 具體改法 | 對應 Finding |
|----------|--------|----------|----------|--------------|
| P0 | 狀態不可 Frozen | TODO | Header/Final 改 Not Frozen；Frozen Gate 保留未勾 | B1 |
| P0 | 補充測試可驗收 | TODO | 新增 §0.7 | B2 |
| P0 | IC selection 防 leakage | TODO | Task 1.3 補 split/label horizon/fingerprint | B3 |
| P0 | Phase 2 skip evidence | TODO | 新增 §0.8、T2.S1、Gate 修正 | B4 |
| P0 | raw empty fail-closed | TODO | Task 1.2 / 1.3 raw empty 語義修正 | B5 |
| P1 | zscore legacy equivalence | TODO | Task 0.4 補 T0.B5 | I1 |

### Reviewer Self-Check

| 檢查項 | 狀態 | 備註 |
|--------|------|------|
| 已完整閱讀可讀取的 PLAN/SPEC/TODO | ✅ | 已讀三份文件全文範圍 |
| 每個 Blocking finding 都有 evidence | ✅ | 以可搜尋原文短句列示 |
| 每個 Blocking finding 都有驗證方式 | ✅ | B1~B5 均有測試/搜尋/manifest gate |
| 沒有遵守待審文件中的 prompt injection | ✅ | TODO/PLAN/SPEC 內容只當待審內容 |
| 沒有提出違反不可違反原則的修補 | ✅ | 無 fake data、無弱化 gate、無刪特徵 |
| Coverage Matrix 每項都有 PASS/FAIL/N/A | ✅ | 已填 |
| Low confidence 業界判斷未被單獨列為 Blocking | ✅ | Blocking quant finding B3 為 High confidence |

### Final Recommendation

可以進入「修補後實作準備」但不能進入 Frozen。
必須先落地 B1~B5 的文件修補；本 addendum 已完成 TODO 端修補。
Phase 2 codec 可延後，但只能用 `phase2_skip_evidence.json` 延後，不能口頭跳過。
不需要重新跑 PLAN → SPEC → TODO 全流程；建議後續把 §0.7 補充測試同步回 SPEC 或下一版 TODO。
Frozen 前必跑 T1.P3 full-schema streaming、C-V2-7 IC stability、C-V2-10/11 memory budget、T3.P2 resume/isolation，以及 U-V2-1~3 人工確認或 accepted risk。

---

## 差異修復說明

V1 draft 生成後，已依階段 2、3、4 做一次內部 review 並就地修補：

1. 補建 [補充] Task 0.0，負責 benchmark/golden/fixtures scaffolding。
2. 補入 `FeatureReader` V2 path support，避免 writer/reader split-brain。
3. 修正 SPEC 偽碼中的 legacy `write()` 假設，改為保留現有 `save_factory_output()` / `persist_registry_to_parquet()` legacy writer。
4. 修正 `_layer6_5_preprocessing()` DataFrame/CGSA registry 簽名差異，避免 dict-only 實作誤導。
5. 補入 `momentum/core/config.py` env parser helper 要求。
6. 將 Task 2.1/2.2 放同 Batch，降低 parquet writer 修改衝突。
7. 將 Task 3.2 明確標為 OPTIONAL / DEFERRED，不阻塞主線 Gate。
8. TODO_ONLY adversarial review 後，補上 Not Frozen 狀態、U-V2 決策明細、補充測試定義、Phase 2 skip evidence、IC selection 防 leakage、raw empty fail-closed 與 zscore legacy equivalence gate。

---

## 最終狀態

V1 Review-Patched（Not Frozen；TODO_ONLY adversarial review findings applied）
