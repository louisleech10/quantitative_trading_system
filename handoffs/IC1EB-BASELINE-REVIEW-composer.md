# IC 1e+1b Golden Baseline Capture — 獨立設計審查（Composer）

**審查標的**：`handoffs/IC1EB-BASELINE-DESIGN.md` + `scripts/capture_ic1eb_baseline.py`  
**上游依據**：`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §A(D-A~D-H)/§C/§G；`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` §0 + Task 5.1  
**審查方法**：獨立讀 SPEC/設計/執行碼 + 對照 `ic_filter_orchestrator.py` / `ic_analysis_service.py` 現行生產路徑；**未引用**其他委員結論。  
**實測錨點**：`handoffs/ic1eb_baseline/manifest.json`（部分產物，max_features=50，與設計稿 500 不一致）僅用於驗證「執行碼與設計是否對齊」，不作他方報告依據。

---

## 1. D-A~D-H 覆蓋足夠性（變更面 → 改前快照）

| ID | 變更面（SPEC） | 設計/腳本覆蓋 | 判定 | 理由與可證偽建議 |
|---|---|---|---|---|
| **D-A** | 縱向 stage5：p-value 由 pooled i.i.d. → bar-level HAC；IC 點估計不動 | 9 顆縱向 service 全真路徑 + 完整 `report_*.json` + G-1 五 hash + `p_value_old_sha256` | **AGREE** | 舊路徑 `compute_ic_statistics(rolling_ic)` 仍為現行 HEAD 行為；改後 G-1 比非 p 欄、G-2 比 p。**驗證**：`pytest tests/momentum/ -k ic1eb_golden` 落地後，任選 `long_*_12h_e53e2290` 五 hash 全等 + 同 run `p_value` 與 manifest `significance_old_iid` 一致。 |
| **D-B** | block bootstrap 僅測試側 | 不入 golden | **AGREE** | 生產零接線；T-1.3 守。**驗證**：`grep block_bootstrap momentum/` → 僅 tests。 |
| **D-C** | 全 evaluated BH + p 閘改消費 q | 縱向 report 含全列 summary + 舊裸 p；`passed_set_sha256` | **AGREE**（縱向） | FDR 變更在 G-2 腿，舊 p 已落檔。**驗證**：B5 後比 `fraction_nan_p` + per-feature q；mutation「僅對 passed 子集算 FDR」→ M-B 轉紅。 |
| **D-D** | SelectionScope metadata | 無改前 scope（新路徑新欄） | **AGREE** | 屬新增稽核欄，非 regression 對象；T-2.3a/b 契約守。**驗證**：`test_scope_contract` + report `selection_scope.n_tests==len(evaluated)`。 |
| **D-E** | event tier → FDR α 六格 | 明知排除（無 event_query） | **AGREE**（見 §2） | 預設 tier=sufficient；α 變更僅在 event 路徑。**驗證**：T-2.2c 六格 hermetic。 |
| **D-F** | 新欄 t_stat/p_value_adj；前端刪 i.i.d. 推導 | 舊 report 保留 i.i.d. `p_value`；G-1 排除 p/t | **AGREE** | 前端不在 golden；summary 舊 p 在 G-2。**驗證**：讀 baseline JSON 有 `p_value`、無 `p_value_adj`；實作後有 adj 且 G-1 仍過。 |
| **D-G** | FDR 預設 ON | 舊路徑無 FDR（裸 p 閘） | **AGREE** | baseline 目的即「改前」；FDR off 對照由 M-G/T-4.3 構造資料守，不需 golden。**驗證**：T-4.3 兩態 e2e。 |
| **D-H** | xsec：p 由 None → HAC；horizon 修復；排序不變 | 設計 +1 顆 xsec run | **CHALLENGE** | 已補 xsec 方向正確，但**執行路徑與縱向不對齊**（見 §1.1、§4）— 同型於「曾漏 xsec」的盲點：有 run 矩陣、無法在現行 API 上可靠產出可比快照。 |

### 1.1 同型盲點（xsec 之外）

| 盲點 | 嚴重度 | 判定 | 理由與可證偽建議 |
|---|---|---|---|
| **xsec 忽略 `feature_filter.max_features`** | BLOCKING | **CHALLENGE** | `analyze_cross_sectional`（`ic_filter_orchestrator.py:921+`）**不呼叫** `_apply_feature_filter`；`capture_ic1eb_baseline.py` 傳入的 `FeatureFilterConfig(max_features=500)` 對 xsec **無效**。縱向在 `analyze()` L828 才截斷。若直接跑 capture 腳本，xsec 會載入全寬 ~218k 欄/符號 → 與設計「500 欄可重放」矛盾，且與縱向 universe 不可比。現有 `xsec_3sym_12h_e53e2290.report.json`（50 欄）來自 `handoffs/ic1eb_baseline/generate_baseline.py` 預物化，**非** `capture_ic1eb_baseline.py` 路徑。**驗證**：`grep _apply_feature_filter ic_filter_orchestrator.py` 僅出現在 `analyze` 鏈；對 xsec 請求帶 `max_features=10` 跑一顆，斷言 `metadata.total_features_input>10` → 必轉紅直到修復。 |
| **G-1 未覆蓋 `rolling_ic_series` / 頂層 `ic_decay` / `grouped_ic`** | MAJOR | **CHALLENGE** | SPEC §G 明文「rolling IC/ic_decay/grouped_ic byte 不動」，但五 hash 僅掃 `summary_table` 內 10 欄；`ic_half_life` 只覆蓋 decay 摘要一欄，**非** `rolling_ic_series` 全序列。若 Task 2.1 誤觸 stage4 輸出，G-1 **靜默漏檢**。**驗證**：對 baseline 與改後 report 各取 `sha256(json.dumps(rolling_ic_series, sort_keys=True))` 入 B5 附加斷言；mutation 改 rolling IC 一點 → G-1 仍綠則設計缺口成立。 |
| **M-J（labels_path `return_5`）未入 golden** | MINOR | **AGREE**（可接受） | xsec baseline 走 `_append_cross_sectional_labels` → `return_1`（h=1），非 `return_5` 外部 labels。horizon 邊界由 T-3.1b/M-J hermetic 守。**驗證**：T-3.1b 綠即可；若要做 golden，另加「labels_path return_5」小樣本 run（非本矩陣）。 |
| **FDR disabled / maxlags override** | MINOR | **AGREE** | 屬 config 變體，M-G / T-1.1 raise 守；default 路徑已覆蓋。 |
| **雙捕獲腳本 + 產物歧義** | BLOCKING（程序） | **CHALLENGE** | 目錄內並存 `generate_baseline.py`（N=50、JSON 五 hash）與 `scripts/capture_ic1eb_baseline.py`（N=500、float64 bytes 五 hash）；現行 `manifest.json` 為前者且僅 6/10 run。**驗證**：B5 消費端硬編碼只讀 `baseline_manifest.json` + `capture_ic1eb_baseline.five_hash`；刪除或歸檔舊腳本產物後重跑。 |
| **run 矩陣未齊** | 執行中 | **CHALLENGE**（暫） | 設計 10 顆；manifest 缺 ETH/BCH 1h、全部 f754aad4 共 5 顆。**驗證**：`baseline_manifest.json.runs` 長度=10 且每 tag 與設計表一致。 |

---

## 2. 明知排除是否成立

### 2.1 event tier run（D-E α 語意）

**AGREE** — 理由成立。

- SPEC §A：event tier 調的是**閾值 α**，與本刀 FDR-on-p 正交；無真實事件源時造事件 = 合成 fixture，違 §G「禁合成充 Golden」。
- 預設 capture（無 `event_query`）永遠 tier=sufficient，舊/新 α 相同，golden 增量低。
- **可證偽**（VERIFY-EXEMPT:doc-example:committee-proposed-future-test）：T-2.2c 六格（sufficient/marginal/low_confidence × fdr on/off）全綠；若生產路徑在無 event 時寫入 `alpha_source=event_tier_*` → 視為回歸。

### 2.2 split-off full run（Task 2.3 `split_label="full"`）

**AGREE** — 理由成立。

- baseline 預設 `ic_train_test_split=True` → stage5 消費 test mask（`scope="test"`），與「full 映射」不同 split 語意。
- full 映射屬契約邊界，T-2.3a/b + `SelectionScope.__post_init__` 守；重跑 full 無 split 真資料的 golden 成本不合理。
- **可證偽**：契約測試 `split_label="full"` 合法建構 + stage5 無 split 時 metadata 映射與 SPEC 一致；mutation 塞 `split_label="test"` 假值 → raise。

---

## 3. 五 hash 與 canonical 化（B5 G-1）

| 子項 | 判定 | 理由與可證偽建議 |
|---|---|---|
| **index / columns 順序** | **AGREE** | `feature_name` → `sort_index()`；columns 固定 `G1_COLUMNS` 順序；符合 CODEX-7。 |
| **xsec 缺欄 reindex 補 NaN** | **AGREE** | 與現行 xsec summary 子集（無 monotonicity/coverage 等）對齊；新舊同用 `summary_to_g1_frame` 即可比。 |
| **values：逐欄 `to_numeric→float64→tobytes`** | **AGREE**（附條件） | 避免 object `tobytes` 不穩；與 SPEC §G 一致。**條件**：B5 測試必須 import **同一** `five_hash()`，禁止複製 `generate_baseline.py` 的 JSON 序列化版。 |
| **nanmask：`isna().to_numpy().tobytes()`** | **AGREE** | 在 float64 化之前取 mask，None/NaN 皆覆蓋。 |
| **dtypes hash** | **CHALLENGE**（低） | hash 的是**原始** `df[c].dtype`，values 卻 coerce 為 float64；summary 從 JSON 重建時可能 object vs float64 漂移 → `dtypes_sha256` 假陰性。**驗證**：對 baseline report 做 `json.loads→DataFrame→five_hash` 連跑兩次 dtypes 恆等；若飄移則改為 hash「coerce 後 dtype」。 |
| **浮點穩定性** | **AGREE** | float64 固定寬度 bytes；IC 欄位非累積運算鏈，跨平台穩定足夠。注意 `-0.0` vs `0.0` 理論可分裂 hash，實務機率低。**驗證**：選一顆 run，Linux/macOS 各算 values_sha256 應一致。 |
| **`raw_tobytes_sha256_appendix`** | **AGREE** | 2D `tobytes` 與逐欄 concat **佈局不同**；標為附錄、不進 G-1 判定，符合 CODEX-7。 |
| **identity 覆蓋率** | **CHALLENGE** | 見 §1.1 rolling_ic 缺口；五 hash 能證「summary 非 p 欄 + feature 對齊」，**不能**證 §G 列舉的全部描述性產物 byte 不動。 |

---

## 4. max_features=500 欄名排序截斷

| 子項 | 判定 | 理由與可證偽建議 |
|---|---|---|
| **可重放性（縱向）** | **AGREE** | 與 orchestrator 一致：`sorted(ordered)[:N]`（`ic_filter_orchestrator.py:2072-2075`），`truncation_order=sorted_column_name`。同 symbol/tf/hash + 穩定 H5 欄集合 → 同一 500 欄。 |
| **可重放性（xsec）** | **CHALLENGE** | 見 §1.1；設計假設 500 對 xsec 成立，**現行生產碼不成立**。 |
| **樣本偏差 / FDR 素材** | **AGREE**（附披露） | 字母序前 500 偏 microstructure 同族（設計已自陳）；縱向 9 顆跨 sym/config 補多樣性。500 欄 ≈498 finite p（設計實測）足 BH。**驗證**：manifest 記 `truncation_order` + 欄名列表 hash；G-2 附 `fdr_assumption_note` + 家族相關性披露。 |
| **全寬成本** | **AGREE** | 設計誠實披露 ingestion 後截斷、全寬 CPU 仍付；屬工程取捨非正確性缺陷。 |
| **N=50 殘留產物** | **CHALLENGE** | 與設計 N=500 衝突；B5 若誤讀舊 manifest 會導致 n_tests 規模錯誤。**驗證**：capture 完成後 `max_features==500` 且刪除/隔離 max_features=50 產物。 |

---

## 5. 程序可稽核性

| 子項 | 判定 | 理由與可證偽建議 |
|---|---|---|
| **HEAD 記錄** | **AGREE** | `git rev-parse HEAD` → manifest `head_sha`；設計要求 capture 期凍結工作樹。 |
| **唯讀消費** | **AGREE**（附條件） | SPEC §0 / Task 5.1 禁 stash/checkout；產物目錄 immutable。**條件**：須單一 canonical 腳本 + 檔名（`baseline_manifest.json` vs 現有 `manifest.json` 需統一）。 |
| **data_cache 副作用** | **AGREE**（已披露） | 每顆覆寫 `{SYM}_{tf}_filtered.h5`；`ic_report_ic_gatekeeper.json` 為 reporter 慣例路徑（gitignored）。非 baseline 產物，但 capture 前後應 `agent_postflight.sh` 確認 **tracked data_cache 零變**。**驗證**：preflight/postflight 快照 diff=0；baseline 目錄外 data_cache 無新增 tracked 檔。 |
| **manifest 完整性** | **CHALLENGE** | `capture_ic1eb_baseline.py` manifest 硬編 `"mode": "longitudinal"`（L156）卻含 xsec run；缺 `generated_at_utc`、缺 `report_sha256`（舊 generate 有）。**驗證**：manifest schema 測試：10 runs、每 run 含 `g1_five_hash` 五鍵、`p_value_old_sha256`、`passed_set_sha256`。 |
| **G-2 素材** | **AGREE** | 完整 report JSON + passed_set hash + p 排序 hash 足夠組 IC1EB-GOLDEN-DIFF；`stage5_threshold_log` 在 report 內。 |

---

## 6. Task 5.1 對照摘要

| Task 5.1 要求 | 設計滿足？ |
|---|---|
| G-1：預產五 hash vs 改後 | 縱向滿足；xsec 路徑待修；rolling_ic 覆蓋不足 |
| G-2：舊 p + diff 快照 | 滿足（report JSON + p hash） |
| G-3：fail-closed 場景 | 不入 baseline，單測腿 — 合理 |
| 禁 git 取舊版 | 滿足 |
| fraction_nan_p（12h） | 設計依賴 G-2 實作，baseline 應含 12h 三 sym — 待 capture 齊 |

---

## 7. 修復建議（最小集，供編排端）

1. **xsec 與 500 欄對齊**：在 capture 腳本內對三 sym 取欄名交集後 `sorted()[:500]` 物化（可復用 `generate_baseline.py` 的 reader 路徑），再呼叫 `analyze_cross_sectional`；或 Task 3.1 前在 orchestrator xsec 入口接 `_apply_feature_filter`（範圍較大）。
2. **廢止雙腳本歧義**：以 `scripts/capture_ic1eb_baseline.py` 為唯一 canonical；歸檔 `generate_baseline.py` 及 N=50 產物；manifest 統一命名 `baseline_manifest.json`。
3. **G-1 補強（建議非阻塞）**：對 `rolling_ic_series`（或 stage4 ic_results 子集）加輔助 hash 入 manifest，與 §G「byte 不動」對齊。
4. **跑齊 10 顆**（含 3×f754aad4、2×1h 缺 sym）後再凍結 HEAD。

---

VERDICT: BLOCK（xsec 路徑在現行生產碼下無法套用 max_features=500，與縱向 universe 不可比；且 handoffs/ic1eb_baseline/ 已有 N=50/異構五 hash 的競爭產物，B5 消費端存在誤用風險；G-1 未覆蓋 rolling_ic_series 等 §G 明文不變產物，存在與「曾漏 xsec」同型的靜默漏檢面。修復 §7.1–7.2 並跑齊 10 顆後可重審。）
