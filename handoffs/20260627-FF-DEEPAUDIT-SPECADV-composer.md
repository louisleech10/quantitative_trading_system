# FF 深稽 P0 SPEC+TODO — Adversarial Review (Composer 2.5)

**審查者**: composer | **被審物**: `docs/FF_DEEPAUDIT_P0_SPEC.md` + `docs/FF_DEEPAUDIT_P0_TODO.md` | **設計基準**: `handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md` (雙戳記 sha256:fa597372) | **日期**: 2026-06-27

**結論一行**: **須修補後派工** — reconcile 主幹（warmup config-driven、columns gate、雙 oracle、prepare_inputs equivalence、mutation TDD-first、§B8、BUG-1 兩者都要）已編進 SPEC/TODO，但仍有 reconcile 掉項、BUG-1 消費者空殼、correctness mode 未可執行、§G 受影響範圍未定、章程 §B4 追溯矩陣缺失；修補後可 gate 派 B0。

---

## Verdict：須修補後派工

---

## 被當成事實的未驗證假設（§0）

| # | 陳述位置 | fact / assumption | 驗證狀態 |
|---|----------|-------------------|----------|
| F1 | §A「`generate_features` line 237」 | fact | **已驗證**: `momentum/FeatureEngineering/feature_factory.py:237` 為 `def generate_features(` |
| F2 | §A「`estimate_max_warmup_bars(config, primary_tf, tfs)`」 | 半 fact | **簽名核對**: `warmup_window.py:313-317` 為 `(config, primary_tf, training_tfs: Optional[Sequence[str]])`；第三參數名 `tfs`≠`training_tfs` 但可呼叫；SPEC 已註「實作端須核對」→ OK |
| F3 | Task 1.1「correctness mode 計算失敗須 FAIL」 | **assumption 當 fact** | **未驗證**: repo 無 `correctness_mode` / `CORRECTNESS_MODE` 開關；`statistics_indicators.py:32-35` 等 8 個 engine 皆 `except Exception` → `logger.warning` 繼續。SPEC 要求 mode 但未定義如何開啟 → 實作者會腦補 |
| F4 | Task 1.3「列**所有**舊欄名消費者同步點」 | **assumption 當 fact** | **未驗證**: SPEC/TODO 未列任何路徑；grep 已找到多處（見 BLOCK-2）但文件空白 |
| F5 | §G「未受影響欄 byte 不變」 | **assumption** | 無「受影響閉包」演算法（L2–L7 衍生欄）；實作者無法判定哪些欄可豁免 golden |
| F6 | reconcile「polars/numba 多路徑列入 P0-FF-1」 | 未落地 | reconcile §四有註記；SPEC §N 只寫 P0-FF-3/P1 另批，**無 polars/numba differential Task** |

---

## Findings（按嚴重度）

### 挑戰前提（§0 優先）

**[BLOCKING | High] reconcile C1-1 必含 price_transform，SPEC Task 1.2 掉項**

- **證據**: reconcile §三 C1-1 明文「必含 … + **price_transform(AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE) adapter policy**」；SPEC Task 1.2 必含清單僅「RSI/ATR/…/BETA/CORREL + cycle/statistics/custom 各≥1」，**無四個 price_transform**；僅 Task 1.1 邊界一句帶過。
- **程式路徑**: `talib_wrapper.py:184,262,289-290` — `price_transform` 標 `computed_in_adapter=True`，`compute()` 直接回空 DataFrame（L1 不跑 talib）；reconcile 要求 adapter oracle 政策，否則 C1-2 equivalence 對這 4 指標無意義或假綠。
- **會怎麼失敗**: 實作只做 RSI/ATR 抽樣 → reconcile 覆蓋漏洞未關；`AVGPRICE` 等 adapter 路徑仍零 differential。
- **修法**: Task 1.2 必含清單補 `AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE`；Task 1.1 明訂 `computed_in_adapter` 指標：**排除 C1-2 byte 比對** 或 **adapter 層獨立 oracle**（二選一寫死）。

**[BLOCKING | High] BUG-1「列所有舊欄名消費者」= 空殼，實作者無同步清單**

- **證據**: SPEC Task 1.3 / TODO Task 1.3 僅重複「列所有…feature_storage metadata、IC/ML」，**零檔案路徑**。
- **可證偽反例（grep 真實路徑，2026-06-27）**:
  - `tests/_golden/failopen/baseline.json` — 多處 `12h_L1_statistics_BETA` / `CORREL` parquet/npy
  - `tests/_golden/batch2d/provenance.json` — 數百條 `close-volume_12h_statistics_BETA_*` / `CORREL_*` L2–L7 衍生鍵
  - `tests/feature_engineering/test_adf_safe_skip.py:48,164,353` — 硬編 `close-volume_12h_statistics_BETA_5`、pattern `_BETA_`
  - `momentum/FeatureEngineering/utils/adf_safe_skip.py:55` — `_CORREL_` 在 ADF safe-skip whitelist（BUG-1 改語義後須重審）
  - `api/services/feature_factory_service.py:3804` — UI 顯示名 `"BETA": "Beta 係數"`（需對應新欄/variant）
  - `momentum/Analysis/` — **無**硬編 BETA/CORREL 欄名（動態選特徵）；IC 風險在 **golden/已凍結特徵集** 非程式硬編
- **會怎麼失敗**: 只改 `talib_wrapper.py` → golden baseline、adf_safe_skip、failopen 三方簽核全紅或靜默語義錯。
- **修法**: SPEC Task 1.3 附 **Consumer Sync Checklist**（上表 + 實作時 `rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_' tests/ api/ momentum/` 產物須入 checklist）；定義「舊欄」= `close-volume_{tf}_statistics_{BETA|CORREL}_{period}` 閉包含 L2–L7 衍生前綴規則。

**[BLOCKING | High] §G「未受影響欄 byte 不變」無可操作定義**

- **證據**: SPEC §G L30「未受影響欄仍須 byte 不變」；無「受影響」判定。
- **反例**: `batch2d/provenance.json` 中 `close-volume_12h_statistics_BETA_13_Mean_W21` 等 L3 欄 — BUG-1 改 L1 BETA 後 **全部數值變**；若實作者只 exempt `statistics_BETA` 本體而比對 L3 衍生 → golden 必 FAIL 或誤判「順帶污染」。
- **修法**: §G 增「Affected Column Closure」: (1) 直接改名/改 source 的 L1 欄；(2) provenance 圖上可追溯至 (1) 的所有衍生欄 → 更新 golden/差異表；(3) 其餘欄 `nan_ratio exact` + value hash 不變。引用 `tests/_golden/batch2d/provenance.json` 作為閉包來源。

**[BLOCKING | High] correctness mode 要求存在但機制未定義（Agent 不可執行）**

- **證據**: SPEC Task 1.1「correctness mode 對已登錄指標計算失敗須 FAIL」；reconcile §二 B1 修法同旨。
- **程式路徑**: `momentum/FeatureEngineering/atomic/statistics_indicators.py:32-35`（trend/momentum/volatility/volume/cycle/pattern/micro/tail 同型）`except Exception` → warning，**無 mode 分支**。
- **會怎麼失敗**: 實作者各寫各的 env/fixture → 生產仍 fail-open；或只在測試 monkeypatch 未接線 production registry gate。
- **修法**: SPEC 新增 **Task 1.0 或 1.1 子項**：定義 `FactoryConfig.fail_open.indicators`（或 `PYTEST_FF_CORRECTNESS=1`）語義；測試用 `monkeypatch` 驗「刪 MFI from map → compute_all **raise** 非 warning」；列 patch 點檔案清單（8 個 `*_indicators.py`）。

**[MAJOR | High] 章程 §B4 覆蓋追溯矩陣缺失（SPEC 引 charter 但未落地）**

- **證據**: `docs/TEST_DESIGN_CHARTER.md` §B4「SPEC 附 `|性質ID|類別|Oracle|測試檔:函式|Mutation probe|`；缺口=BLOCKING」；SPEC §V 只有層級目錄與邊界打勾，**無矩陣表**。
- **會怎麼失敗**: P0-FF-2/4 與 BUG-1/2 無一對一 mutation 追溯；gate 機檢過、邏輯漏。
- **修法**: SPEC §V 末或 TODO §0 增 B4 矩陣（至少 C1-1/C1-2/C2-1/C2-2/C4-3/BUG-1/BUG-2 七列）。

---

### 忠實度（reconcile vs SPEC/TODO）

| reconcile 項 | SPEC/TODO | 判定 |
|--------------|-----------|------|
| C1-2 prepare_inputs equivalence | Task 1.1 | **OK** |
| C1-1 雙 oracle BETA/CORREL | Task 1.2/1.3 | **OK** |
| C1-3 oracle 三級 + 獨立 reference | Task 1.4 | **OK** |
| C2-1 config warmup + columns gate + timestamp 交集 | Task 2.1 | **OK**（warmup 區見下） |
| C2-2 尾端擾動 + warmup 區 assert | Task 2.2 | **OK** |
| C2 config 分級 | Task 3.1 | **OK** |
| C4 requires_kline + DATA_MANIFEST | Task 0.1/0.2 | **OK** |
| mutation TDD-first + §B8 | §0/§V | **OK** |
| BUG-1 兩者都要 + 三方簽核 | §A/§G/Task 1.3 | **OK**（簽核流程見 MAJOR-3） |
| price_transform 必含 | Task 1.2 | **BLOCK 掉項** |
| polars/numba 併 P0-FF-1 | — | **掉項**（可降 P1 但須 §N 明示） |
| P0-FF-3 不取代 | §N/Task 2.1 不可做 | **OK**（已解 R1 矛盾） |

**[MAJOR | Medium] BUG-1 欄名 reconcile vs SPEC 不一致**

- reconcile §一「`Beta_CloseVolume`」；SPEC/TODO「`BetaCloseVolume/CorrelCloseVolume`」。命名影響 golden 鍵與前端搜尋。
- **修法**: 寫死一種（建議對齊既有 `close-volume_{tf}_statistics_*` underscore 慣例：`Beta_CloseVolume` / `Correl_CloseVolume`）。

---

### 可實作性

**[OK | High] `estimate_max_warmup_bars` 簽名**

- 真實: `warmup_window.py:313-317`；`tests/feature_engineering/test_b6_warmup_trim.py:217` 已用 `(config, "12h", ["12h"])`。SPEC 第三參數名 `tfs` 可接受。

**[OK | High] `TALIB_INPUT_SEMANTICS` 表可建**

- 基礎: `_INPUT_TYPE_MAP`（`talib_wrapper.py:187-207`）+ 預設 `single` + `CDL*`→`ohlc`；特殊項 SPEC 已列 MAVP、price_transform。
- **邊界**: 132 指標 registry（`initialize()` L276）；`computed_in_adapter` 4 指標須 **exclude 或 adapter 子表**（見 BLOCK-1）。

**[MAJOR | Medium] Task 0.1 未列 skip→marker 遷移清單**

- **證據**: 至少 10 處 `pytest.skip(...kline...)`（`test_failopen_correctness.py:75`、`test_failopen_matrix.py:90,200`、`test_b6_warmup_trim.py:87,400`、`test_mtf_align_golden.py:190` 等）；Task 0.1 寫「逐一評估」無清單。
- **修法**: TODO Task 0.1 附 **Phase-0 遷移表**（檔案、是否 correctness、是否掛 marker、保留 skip 理由）。

---

### 測試假綠

**[MAJOR | High] C2-1 單獨跑時仍跳過 warmup 區比對**

- **證據**: Task 2.1 只比 `full.iloc[warmup:-k]`；Task 2.2 才有「warmup 區不得有非 NaN 差異」。R1 反例：post-warmup-only 可比區掩蓋 warmup 洩漏。
- **程式對照**: `test_failopen_correctness.py` 用 `_warmup_cutoff_row`（data-dependent）；本 SPEC 已禁，但若 C2-1 mutation 只紅在 `iloc[warmup:-k]`，`shift(-1)` 影響僅 warmup 內 → **C2-1 單測可綠**。
- **修法**: Task 2.1 增 **warmup 區顯式 assert**（`[0:warmup)` 兩 run NaN mask 一致或 values 一致）；與 2.2 同檔共用 helper。

**[MAJOR | Medium] C2-1 mutation probe 過於模糊**

- **證據**: Task 2.1 驗證「mutation 某層注入 `shift(-1)`/`center=True` rolling/全量 fit」— **無檔案:行號**。
- **對照**: Task 1.1 有「刪 ATR from `_INPUT_TYPE_MAP`」；Task 1.4 有「EOM `*`→`/`」。
- **修法**: 至少列 3 個 canonical mutant，例如:
  1. `momentum/FeatureEngineering/layers/layer3_rolling.py`（或實際 rolling 模組）`center=True`
  2. `momentum/FeatureEngineering/preprocessing/causal_winsor.py` 全量 fit 路徑
  3. L4 lag `shift(-1)` 若存在
  每個附 `pytest ...` 與預期 fail 摘要。

**[MAJOR | Medium] BUG-2 簡化變體 golden「三方簽 off」時序矛盾**

- **證據**: Task 1.4「簡化變體 golden 來自三方簽 off 非實作反推」；實作順序 B1 含 1.4，**簽核在 B1 gate 之後**。
- **會怎麼失敗**: 實作者用現 Klinger 輸出 freeze → 自指 oracle（R1 BLOCK-5 重現）。
- **修法**: Task 1.4 拆兩步：(a) 先產 **文獻/reference 差異表**（可 fail）；(b) 三方簽 off 後才寫入 golden JSON；(c) metadata `variant=simplified` 與簽核 commit hash 綁定。

---

### TODO 覆蓋與批次拓撲

**[OK | High] 9 Task 全覆蓋**

- TODO 覆蓋追溯 L89-90：0.1–3.1 九項對齊 SPEC §P。

**[OK | Medium] B1/B2 並行**

- B2 全鏈 MR 測的是 **同版** `full` vs `trunc` 不變量，不依賴 BUG-1 語義正確；BUG-1 改 columns 後 B2 仍應成立（columns gate 同步變）。**B3 gate 已要求 B1+B2** → 三方簽核在 B1 後合理。
- **風險（非 BLOCK）**: 若 B2 先 merge、B1 後 merge，production golden（§G）須在 B1 後重凍 — TODO Batch Gate 應加一句「§G baseline 凍結在 B1 BUG 落地後」。

**[MINOR | Medium] §G baseline 凍結時機與 B1 衝突**

- SPEC §G「動工前」凍結 baseline；BUG-1/2 必改特徵 → baseline 會廢棄一次。
- **修法**: §G 改「B0 後、B1 BUG 修前凍結 v0；B1 後凍結 v1 + 差異表」。

---

### 遺漏的高風險 (a)(d)

**[MAJOR | High] (d) IC 消費端：無硬編欄名但 golden/特徵選擇語義漂移未覆蓋**

- BUG-1 改 BETA 語義 → 已選 `statistics_BETA` 的 IC study **數值全變**；SPEC 只提「IC/ML 消費者」無驗證。
- **修法**: Task 1.3 增 **IC regression smoke**：固定 1 symbol×TF×horizon，BUG 修前後 IC 符號/量級變化寫入差異表（不要求「不變」，要求 **明示變更** + 三方簽）。

**[MAJOR | Medium] (a) ADF safe-skip 與 BETA/CORREL 白名單**

- `_CORREL_` 在 `adf_safe_skip.py:55`；BETA 註解 L16 說保留 ADF。BUG-1 後標準 BETA(high,low) 統計性質變 → **須重審 whitelist**，SPEC 未提。
- **修法**: Task 1.3 子項「重跑 adf_safe_skip 相關測試 + 更新 whitelist 註解」。

**[RISK | Low] (a) 跨 symbol cache — reconcile P1-FF-5 N/A 合理**；本批不 BLOCK。

---

## §1 必查十類（摘要）

| # | 結果 |
|---|------|
| 1 矛盾/互斥 | 無（P0-FF-3 已解）；欄名 BetaCloseVolume vs Beta_CloseVolume 見 MAJOR |
| 2 漏項/端到端 | **有** — price_transform、polars/numba、consumer 清單 |
| 3 不可測驗收 | **有** — correctness mode、§G 受影響範圍 |
| 4 可疑 quant | **有** — ADF whitelist、IC 語義漂移 |
| 5 過度工程 | 無 |
| 6 OOM/並行 | 無（本批測試為縮窗 kline） |
| 7 Cache | 無新增 cache 需求 |
| 8 API/相容 | BUG-1 需 `feature_factory_service.py` 顯示名 — 未列 |
| 9 測試品質 | **有** — C2 warmup、mutation 具體性、B4 矩陣 |
| 10 Agent 可執行 | **有** — correctness mode、consumer 清單、C2 mutant 路徑 |

## §2 範本錨點

- §RISK/§A/§C/§G/§P/§V/§R/§N：**齊全**（gate 可過）
- §G 可證偽：**有** atol/rtol + hash，但受影響欄定義缺 → 半空殼
- §B4 矩陣：**缺** → BLOCKING

---

## RISK / OK

### OK（reconcile 忠實落地）

- C1-2 / C1-1 雙 oracle / C1-3 三級 / C2 warmup+columns gate / C4 marker+manifest
- mutation TDD-first + §B8 閉合
- BUG-1「兩者都要」+ 三方簽核要求
- P0-FF-3 範圍解、9 Task TODO 對齊
- `estimate_max_warmup_bars` 真簽名可用

### RISK（不擋派工但須實作注意）

- §G baseline「動工前」與 BUG 修順序
- B2∥B1 後須重凍 golden
- `logging` 規則寫 `api.core.logging` 但 `momentum/` engine 用 `momentum.core.logging`（既有慣例，勿混用）

---

## 對 TODO 的具體補強

1. **Task 0.1** — 附 skip→marker 遷移表（10+ 檔案）；驗證命令保留。
2. **Task 1.1** — 增 `TALIB_INPUT_SEMANTICS` 對 `computed_in_adapter` 的 exclude 規則；**新增子 Task「correctness mode 接線」**（8 個 engine + 開關語義 + mutation: 刪 MFI）。
3. **Task 1.2** — 必含清單補 `AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE`。
4. **Task 1.3** — 貼入 **Consumer Sync Checklist**（本 review BLOCK-2 表）；Affected Column Closure 規則；`adf_safe_skip.py` 重審；IC 語義差異 smoke；欄名統一為 `Beta_CloseVolume` / `Correl_CloseVolume`（或 SPEC 定案名）。
5. **Task 1.4** — 拆 reference 差異表 → 三方簽 → golden 三步；簽核 hash 寫 manifest。
6. **Task 2.1** — warmup 區 `[0:warmup)` assert；列 3 個具體 mutation patch 點（檔:行）。
7. **§B Batch** — B1 gate 後才凍 §G v1；B3 前完成三方簽核 checklist（Claude+Codex+Composer 各一行「資料正確」+ 差異表路徑）。
8. **§0 或附錄** — 補章程 §B4 追溯矩陣 7+ 列。

---

## 驗證命令（審查時已跑）

```bash
# warmup 簽名
rg "def estimate_max_warmup_bars" momentum/FeatureEngineering/warmup_window.py

# BETA/CORREL 現況
rg "close_volume.*BETA|BETA.*CORREL" momentum/FeatureEngineering/atomic/talib_wrapper.py

# fail-open
rg "except Exception" momentum/FeatureEngineering/atomic/*_indicators.py

# kline skip 熱點
rg 'pytest\.skip.*kline' tests/ --glob '*.py'

# BETA 消費者
rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_' tests/ momentum/ api/ --glob '*.{py,json}' | head -40
```

---

ASSUMPTIONS_VERIFIED: estimate_max_warmup_bars 簽名、generate_features:237、talib_wrapper BETA/CORREL close_volume、8 engine fail-open、price_transform computed_in_adapter 空 DF、grep 消費者路徑
TESTS_RUN: rg/grep 唯讀驗證（見上）；未改 repo
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none（僅寫 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查）

STATUS: DONE

---

## R2 閉合再驗證 (2026-06-27, §B8)

逐條核對 R1 BLOCK/MAJOR vs 修正後 `docs/FF_DEEPAUDIT_P0_SPEC.md` + `_TODO.md`：

| R1 ID | 判定 | 證據 |
|-------|------|------|
| BLOCK price_transform | **關閉** | Task 1.2 必含 AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE; Task 1.1 寫死排除 C1-2 byte 比對 |
| BLOCK Consumer Sync Checklist | **關閉** | Task 1.3 列 adf_safe_skip:55、test_adf_safe_skip:48/164/353、baseline/provenance、feature_factory_service:3804、IC smoke; rg 命令入 checklist |
| BLOCK Affected Column Closure | **關閉** | §G L31-34 三步演算法 + provenance.json; L29 全欄 per-column value hash(非抽樣) |
| BLOCK correctness mode | **關閉** | Task 1.0 定義 FF_CORRECTNESS_MODE/FactoryConfig + 8 engine + 刪 MFI→raise 可證偽 |
| BLOCK §B4 矩陣 | **關閉** | SPEC §V L117-127 共 8 列(≥7) |
| MAJOR 欄名 | **關閉** | Beta_CloseVolume/Correl_CloseVolume 寫死 §A/Task 1.3 |
| MAJOR skip→marker 表 | **關閉** | TODO Task 0.1 L35 遷移表 + rg 補全 |
| MAJOR C2-1 warmup | **關閉** | Task 2.1 四段 gate ③ `[0:warmup)` NaN mask |
| MAJOR C2-1 mutation | **關閉** | numba_rolling.py/causal_winsor.py/L4 shift(-1) 具體路徑 + pytest 命令 |
| MAJOR BUG-2 時序 | **關閉** | Task 1.4 三步 (a)差異表→(b)三方簽→(c)golden |
| MAJOR §G 凍結 | **關閉** | §G v0/v1 + TODO §B Batch Gate |
| MAJOR polars/numba | **關閉** | §N 明示降 P1-FF-7 |
| MAJOR IC/ADF | **關閉** | Task 1.3 IC smoke + ADF whitelist 重審 |
| MAJOR logging | **關閉** | TODO §0 momentum.core.logging |

反例重跑: `adf_safe_skip.py:55` `_CORREL_` 仍存在; hash=`6b752202...` 與 codex R2b 一致。

RECONCILE-STAMP: composer APPROVED 2026-06-27 sha256:6b75220205f6a23b12ca1c29cdc708448a3f061408c8f0d65e165f7684233e8a task:ff-specadv-r2

ASSUMPTIONS_VERIFIED: R1 反例路徑 grep 仍真、SPEC/TODO 條款對位 reconcile 18 點
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/20260627-FF-DEEPAUDIT-SPECADV-RECONCILE.md`; rg 核對 SPEC 錨點
FAILURES_SEEN: none
SCOPE_CHANGES: append RECONCILE stamp 一行 + 本 handoff 段
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
