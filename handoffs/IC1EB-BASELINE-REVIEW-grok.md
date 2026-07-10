# IC1EB Golden baseline capture — 獨立設計審查（Grok 4.5）

**角色**:獨立審委員（不引用其他委員結論）  
**審查標的**:`handoffs/IC1EB-BASELINE-DESIGN.md` + `scripts/capture_ic1eb_baseline.py`  
**上游**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §A D-A~D-H / §C / §G；`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` §0 + Task 5.1  
**證據範圍**:上述檔 + 對照 production 碼（`ic_filter_orchestrator.py` / `ic_analysis_service.py` / `ic_models.py`）+ 本地可證偽微實驗；未執行完整 10 顆 capture。

---

## 1) 覆蓋足夠性：D-A~D-H「變更面 → 改前快照」

### 1.1 逐裁決對照

| 裁決 | 行為變更面（改後） | 設計之改前快照 | 判定 |
|---|---|---|---|
| **D-A** HAC kernel 取代 pooled i.i.d. p/t | stage5 `p_value`/`t_stat` 語意；**非** ic_mean/icir 等描述欄 | 9 縱向 run 完整 report + G1 五 hash（非顯著欄）+ `p_value_old_sha256` | **AGREE**（主路徑覆蓋） |
| **D-B** block bootstrap 僅 tests/ | 無 production 行為變更 | 不需 golden | **AGREE** |
| **D-C** BH q 進閘、全 evaluated 先 FDR | `p_value_adj`、passed 集合、threshold_log | report 存舊裸 p；`passed_set_sha256`；G-2 用 report | **AGREE**（G-1 不應含 p/q） |
| **D-D** SelectionScope 入 metadata | 新 metadata 欄；契約 raise | 無改前 scope 快照 | **AGREE**（屬新增稽核欄，T-2.3 守；非 G-1 對象） |
| **D-E** event tier→α 語意 | low_confidence α 放寬標記 | **明知排除** event run | 見 §2 |
| **D-F** 欄位語意/前端刪 i.i.d. 推導 | 增欄、UI；點估計欄 byte 不動 | G1 欄集合正確排除 p；t_stat 亦不入 G1（正確，因 xsec 舊 t 也會換） | **AGREE**（後端 G-1）；前端非本 baseline 職責 |
| **D-G** FDR 預設 ON + canonical flag | 預設與 config 鏈；pass 集合 | 預設 config 快照（無 feature_tiers override）= 舊「無 fdr schema」行為 | **AGREE**（G-2/M-G 補 on/off；G-1 不依賴 flag） |
| **D-H** xsec 填誠實 p/t/q；horizon 於改名前解析；**無新門檻** | xsec `p_value`/`t_stat`；ICIR 排序不變 | 矩陣含 1 顆 xsec（3sym×12h/e53e2290） | **CHALLENGE**（納入正確，但 capture **無法保證** xsec 截斷可重放，見 §1.2 / §4） |

### 1.2 同型盲點掃描（曾漏 xsec 一類：「路徑分叉卻假設共用 plumbing」）

**CHALLENGE（BLOCKING）— xsec 不消費 `feature_filter` / `max_features`**

- 事實：`feature_filter` 只在縱向 `analyze()` 的 `_apply_feature_filter`（`ic_filter_orchestrator.py` ~828–830、2072–2075）生效。
- `analyze_cross_sectional` 以 `numeric_df` 全部非 label 數值欄為 `feature_cols`（~985–987），**零** `feature_filter` 引用。
- service xsec 分支把 `feature_filter` 寫進 `config_override`（`_build_config_override`），但 orchestrator xsec **不讀用** → capture 對 xsec 設 `FeatureFilterConfig(max_features=500)` **靜默無效**。
- 後果：xsec 可能掃全庫量級欄（既有旁路產物亦註記全量不可行），或耗時/記憶體與設計「500 欄、可重放」假設不一致；即使勉強跑完，**B5 重放若誤以為 max_features 生效會對錯集合**。
- 這與「漏 xsec 整條路徑」同構：都是 **假設與縱向共用的請求面在 xsec 分叉上實際為 no-op**。

**可證偽**:
```text
# A) 靜態：analyze_cross_sectional 內無 feature_filter / max_features 引用（rg 應為 0）
rg -n "feature_filter|max_features" momentum/Analysis/ic_filter_orchestrator.py
# 僅應出現在 _apply_feature_filter / analyze() 縱向鏈

# B) 動態（小）：同一 xsec 請求 max_features=3 vs 30，n_summary_rows 應變；
#    若兩次 rows 相等且 ≈ 全欄 → 截斷未生效（預期：當前碼下相等）
```

**其他同型/近型點（非皆 BLOCK）**:

| 候選 | 判定 | 理由 |
|---|---|---|
| labels_path xsec horizon（D-H 核心修點） | **AGREE 可不入 golden** | 變更在顯著性/maxlags，非 G-1 描述欄；應由 T-3.1b/M-J 守。若要 G-2 敘事完整可選加 1 顆，非 G-1 必需 |
| rolling_ic_series 全序列 | **CHALLENGE（MINOR）** | SPEC §G 文字列 rolling IC 為不變腿，capture 只 hash summary 描述欄。ic_mean/icir 聚合多半能抓到 stage4 漂移，但**序列本體**未入五 hash |
| ic_reporter CSV/JSON 導出 | **AGREE 不入** | T-2.4；與 service `summary_table` 同源即可 |
| stage6 redundancy / corr（passed 下游） | **AGREE 不入 G-1** | passed 變屬 G-2；描述欄在 stage5 表已固定 |
| `_run_full_sample_fallback` | **AGREE 邊緣** | 非預設；fallback 另路徑，不必進 10 顆矩陣 |
| 目錄內已有 `generate_baseline.py`（N=50、5 run）vs 設計腳本（N=500、10 run） | **CHALLENGE（MAJOR 程序）** | 兩套 schema/矩陣並存 → B5 消費錯產物風險；設計若以 `scripts/capture_ic1eb_baseline.py` 為準，須宣告**唯一**凍結源並作廢/隔離另一套 |

### 1.3 縱向 9 顆矩陣

**AGREE**：3sym × (1h/4a8a0b37, 12h/e53e2290, 12h/f754aad4) 對齊 §G 明文資料面；預設 `ic_train_test_split=True` 打到 stage5 test 段主鏈，合理。

---

## 2) 明知排除：event tier / split-off full run

### 2.1 event tier run（D-E）

**AGREE（排除成立，附條件）**

- 理由成立：無真實事件源而造事件 = 合成，撞 §G「禁合成充 Golden」與 data truth。
- D-E 變更是 **α 政策/標記**（`alpha_source` / `selection_mode`）與 p 閘比較值，不是 G-1 描述欄；應用 T-2.2c 六格 + threshold_log 欄位斷言守住。
- **條件（非否決）**:B5 G-2 敘事不得宣稱「已用真資料覆蓋 event×FDR」；簽核清單應明示 D-E=單元/政策測試，非 golden 腿。

**可證偽**:T-2.2c 故意把 low_confidence 的 `alpha_effective` 不斷言 → 應紅；與 baseline 目錄有無 event report 無關。

### 2.2 split-off full run（Task 2.3 `split_label="full"`）

**AGREE（排除成立，附條件）**

- full 映射主要動 **SelectionScope 契約/metadata**，G-1 五 hash 不涵蓋 scope；用 T-2.3a/b 守成本正確。
- **殘餘風險**:full run 下 stats 窗=全樣本 vs test 段，HAC n_valid/L 分布不同——這是**顯著性**行為，應用單元短樣+G-3，不必再付 1 顆全日 golden。
- **條件**:若實作誤把 full 的描述統計窗與 split 測試窗攪在一起，G-1 預設矩陣（split ON）**抓不到**；需 T-2.1/T-2.3 顯式鎖窗來源。

---

## 3) 五 hash 定義與 canonical 化 vs B5 G-1

### 3.1 對象與欄位集合

**AGREE**：G1_COLUMNS 排除 `p_value`（及未納 `t_stat`/`p_value_adj`）符合「只證非顯著性不變」。  
**AGREE**：`set_index("feature_name").sort_index()` + `reindex(columns=G1_COLUMNS)` 固定 index/欄序，利於比對。

### 3.2 values / nanmask

**AGREE（主路徑）**：逐欄 `to_numeric→float64→tobytes` 避免 object bytes 不穩；`isna().tobytes()` 對 None/NaN 在微實驗中 **nanmask 一致**。

微實驗（本機）:同數值、`None` vs `np.nan` 填缺 → `values`/`nanmask` hash 相同，**`dtypes` hash 不同**。

### 3.3 dtypes — **CHALLENGE（MAJOR）**

- `dtypes_sha256` 吃**原始** `df[c].dtype` 字串；values 已 float64 canonical，dtypes **未** canonical。
- 舊 summary 大量 `None` → object；實作若改寫為 `np.nan`（常見於「統一缺失」），G-1 會在 **數值語意不變** 時因 dtypes 腿紅。
- 與 CODEX-7「五 hash 含 dtypes」不衝突，但落地應定義：**比較前 dtypes 正規化**（例如一律記錄 `float64` after to_numeric），或 G-1 斷言順序改為「先 values+nanmask+index+columns，dtypes 僅在嚴格 byte 模式」並寫進 Task 5.1。

**可證偽**:
```python
# 同表 None→nan 只改 dtypes_sha256；若 B5 未正規化，此變更即假紅
```

### 3.4 排序 / 浮點

**AGREE（可接受）**：index 字典序固定；欄序由 G1_COLUMNS 固定。  
**CHALLENGE（MINOR）**：未記錄 numpy/pandas/scipy/statsmodels 版本與 BLAS 線程；跨機重算五 hash 理論上有還原風險。緩解：G-1 比對應在**同一 venv/同機**對「改前凍結 hash」vs「改後重跑」，禁止跨環境重產 baseline。

### 3.5 附加 `raw_tobytes_sha256_appendix`

**AGREE**：標為 appendix 正確；`DataFrame.to_numpy()` 佈局可能與逐欄 concat 不同，**不得**當第五 hash 本體（腳本已分離）。

### 3.6 G-2 素材

**AGREE**：整包 report JSON + passed_set + p_value 排序 hash 足以做 selection-diff。  
**CHALLENGE（MINOR）**：`json.dumps` 對 `float('nan')` 產非標準 `NaN` token；跨語言讀取脆。建議 G-2 消費用 Python 或 `allow_nan` 策略寫死。

### 3.7 xsec reindex 補 NaN

**AGREE**：新舊同程序可比。現況 xsec row 已含 G1 鍵（值多為 null），reindex 多半是防禦性。**不**把舊 xsec `t_stat`（i.i.d.）納入 G1 — 正確。

---

## 4) max_features=500 欄名排序截斷

### 4.1 可重放性

**AGREE（縱向）**：`sorted(ordered)[:N]` + `truncation_order=sorted_column_name` 確定性強；與顯著性無關，G-1 身份穩定。  
**CHALLENGE（BLOCKING，xsec）**：見 §1.2 — xsec 上 N=500 **不可重放為 500**，因過濾未接線。

### 4.2 樣本偏差

**CHALLENGE（NON-BLOCKING for G-1；G-2 解讀要降權）**

- 設計自陳：排序首段偏同族 microstructure → 家族相關性高、BH PRDS 壓力大 — 與 SPEC `fdr_assumption_note` 一致。
- G-1：子集上證「描述欄不動」仍合法。
- G-2：不可把「500 欄真資料 diff」外推為全宇宙 selection 行為；12h `passed_features=0` 時 pass 差更無資訊，價值在 p 層 — 設計已自陳，**AGREE 該自陳必須寫進 G-2 簽核說明**。
- N=500 vs 旁路 N=50：500 對 FDR 素材較好；但若實際凍結的是另一腳本 N=50，則與本設計審查結論不可混用。

**可證偽**:同一 run `sorted(names)[:500]` 的 family 前綴直方圖；若單一 family 占比 ≫ 其餘，G-2 解釋須標 sample bias。

---

## 5) 程序可稽核性

| 項 | 判定 | 理由 |
|---|---|---|
| HEAD 記錄 | **CHALLENGE（MAJOR）** | 有 `git rev-parse HEAD`；**無** dirty tree / `git status --porcelain` / tracked diff hash。當前工作樹已見未提交之 design/script/baseline 目錄 → **僅 HEAD 不足以指認位元組級碼狀態**。 |
| 工作樹凍結 | **CHALLENGE** | 設計文字宣稱凍結；腳本未 enforce（未拒絕 dirty、未寫入 tree fingerprint）。 |
| 唯讀消費 | **AGREE** | 產物落 `handoffs/ic1eb_baseline/`；符合 §G/§0「禁 git stash/checkout 取舊版」。 |
| data_cache 副作用 | **AGREE（披露充分）** | service 既有寫入 `*_filtered.h5` 等；屬 gitignored 衍生物。須在 postflight 預期「capture 期間 data_cache 會變」；**baseline 真源是 handoffs 產物**，不是 filtered.h5。 |
| manifest 頂層 `"mode": "longitudinal"` | **CHALLENGE（MINOR）** | 矩陣含 xsec 時頂層 mode 誤導；應刪或改 `modes: [...]`，以 `runs[]` 為準。 |
| config_hash 8 字前綴 map | **CHALLENGE（MINOR）** | `[:8]` 字典碰撞時靜默覆蓋；應用全長 hash 或碰撞檢測 raise。 |
| 雙產生器並存 | **CHALLENGE（MAJOR）** | `scripts/capture_ic1eb_baseline.py` vs `handoffs/ic1eb_baseline/generate_baseline.py`（不同 N、矩陣、hash 函式）→ 稽核鏈必須指定單一 canonical generator + 產物校驗。 |

**可證偽（HEAD 稽核）**:
```bash
git rev-parse HEAD
git status --porcelain
# 理想：manifest 含 dirty=false 或 contents_tree_sha；dirty=true 則拒簽 freeze
```

---

## 6) 挑戰編排端前提：§G 覆蓋清單的「第二個 xsec 型」結構盲點

編排端前提：「§G 明文 3sym 矩陣 +（後補）1 xsec = 變更面改前快照齊」。

**獨立結論：存在第二個同構盲點，且比「漏 xsec」更隱蔽。**

1. **主盲點（BLOCK）**:假定 `ICAnalyzeRequest.feature_filter.max_features` 對 longitudinal **與** cross_sectional 同樣生效；**production xsec 分叉未接 `_apply_feature_filter`**。把 xsec 加進矩陣卻沿用縱向截斷語義 = 覆蓋表紙面完整、執行語義空洞。  
2. **次盲點（MAJOR 程序）**:假定「一個 capture 腳本 + handoffs/ic1eb_baseline/」單一事實源；目錄內已存在不同參數的 `generate_baseline.py` 產物 → §G 程序前提被雙軌稀釋。  
3. **SPEC 文案 vs 實作（MINOR）**:§G 寫 rolling IC 等非顯著量不變，五 hash 僅 summary 子集——可接受的工程收斂，但**不得**在簽核時宣稱「全 report 非顯著 payload 已五 hash」。  

**不是第二盲點（排除成立）**:event tier、split-off full——理由見 §2；屬範圍外測試責任，非「漏路徑卻假裝已覆蓋」。

---

## 7) 總表（審查點 → AGREE/CHALLENGE）

| # | 題旨 | 判定 |
|---|---|---|
| 1 | D-A~D-G 主路徑改前快照 | **AGREE** |
| 1b | D-H xsec 納入矩陣 | **AGREE 意圖** / **CHALLENGE 落地**（max_features no-op） |
| 1c | 同型第二盲點 | **CHALLENGE BLOCK**：xsec feature_filter 分叉 |
| 2a | 排除 event tier | **AGREE**（條件：D-E 不靠 golden） |
| 2b | 排除 split-off full | **AGREE**（條件：窗來源單元鎖） |
| 3 | values/nanmask/index/columns | **AGREE** |
| 3b | dtypes 未 canonical | **CHALLENGE MAJOR** |
| 4 | N=500 可重放（縱向） | **AGREE** |
| 4b | N=500 可重放（xsec） | **CHALLENGE BLOCK** |
| 4c | 排序樣本偏差 | **CHALLENGE**（G-2 降權，不獨否決 G-1） |
| 5 | HEAD/唯讀/副作用披露 | **AGREE 方向** + **CHALLENGE** dirty/雙軌/manifest 瑕疵 |

---

## 8) 解 BLOCK 最低條件（供編排端，非指令）

1. **xsec 截斷語義二選一並寫死可證偽收據**:(a) capture 在進 `analyze_cross_sectional` 前對欄名 `sorted(...)[:N]` 物化子集（與旁路 generate 同構）；或 (b) 生產碼 xsec 接 `_apply_feature_filter`（屬 scope 擴大，需另核）。**禁止**維持「請求帶 max_features 但 xsec 全欄」並宣稱與縱向同 N。  
2. **唯一 canonical generator + 產物**：廢棄或隔離非選中腳本產物；manifest 記錄 generator 路徑、N、run 列表、完整 config_hash。  
3. **dtypes 策略**：G-1 比較前 dtypes 正規化，或明文「缺測用 NaN+float64」並在改前重產一次，避免 None/NaN 假紅。  
4. **稽核**：manifest 增加 dirty/tree fingerprint；dirty 則不得標 immutable freeze。

---

## 結構化收尾（委員）

```
ASSUMPTIONS_VERIFIED:
  - _apply_feature_filter 僅縱向 analyze 呼叫；analyze_cross_sectional 無 feature_filter
  - ic_train_test_split 預設 True（schema）
  - xsec summary 含 G1 鍵與 t_stat/p_value；無 _apply_thresholds
  - five_hash：None vs NaN → dtypes 變、values/nanmask 不變（本機微實驗）
TESTS_RUN:
  - 靜態讀碼：orchestrator/service/capture/design/SPEC/TODO
  - python 微實驗 None vs NaN dtypes/values/nanmask（見 §3.2–3.3）
  - 未跑 10 顆全量 capture（非本審範圍）
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none（只寫本審查檔）
NUMERIC_OR_SCHEMA_IMPACT: none
```

VERDICT: BLOCK(xsec 上 max_features/feature_filter 靜默無效=第二結構盲點；須先修截斷語義並單一化 canonical 產物/dtypes 策略後再凍結 G-1)
