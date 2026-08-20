# GAP3_EVENT_TODO — D 延伸 001（B1 施工期第一份修訂）

BASE: docs/GAP3_EVENT_TODO.md @ 45fa3774
PREDECESSOR: none

改什麼: ①Task B1.6 驗證①②之數值容差由 atol=1e-12／exact 改為「儲存量子級」逐欄判準（NaN mask 仍 exact）②TODO 標頭所稱延伸檔 `docs/GAP3_EVENT_TODO_AMENDMENTS.md` 依凍結文件修訂規約以本 dext 檔名格式實現。
為什麼: 容差前提被實測推翻——FF V7 特徵儲存以 float16 為主（實測 minimal preset 15 欄中 14 欄 float16），1e-12 從根本不可達；詳細碼證見「## 內容」。檔名依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.2（`*.D-NNN.md` 機讀規約；`*_AMENDMENTS.md` 會被 doc 檢查誤判為 todo 型別）。

## 觸及面宣告

新增: none
覆寫: ### Task B1.6 — 特徵物化與決策列選取（`票 #3`；批內順序在 B1.3 之後、B1.4 前）
依賴: none

## 內容

### A-01 — B1.6 驗證①②容差修訂（儲存量子級）

- **原文義務**（BASE Task B1.6 驗證欄）：①「足長段物化 vs 全史物化取同事件列逐值 `atol=1e-12` 一致」②「截斷 `decision_at` 之後的資料重算，事件列逐值不變（exact）」。
- **前提推翻之碼證**（2026-08-20 主委實跑，ETHUSDT/12h minimal preset）：
  1. 儲存 dtype 實測：15 欄中 14 欄 float16、1 欄 float32（reader `load_columns_v2` 直讀 parquet dtypes）。float16 相對精度 ~2⁻¹⁰ ⇒ 1e-12 判準物理不可達。
  2. 末端截斷（end_date）重算：15 欄中 **14 欄逐值 exact==0**；唯 `meta_12h_Volume_PriceChange`（float32 儲存、含 float16 中間路徑）rel≈3.4e-4——差值恰為 float16 量化級，非 look-ahead（look-ahead 會使多欄大幅變動；此處全部價格/動能欄 exact）。
  3. 段起點截斷（start_date）：遞迴族（EMA/MACD/Wilder-RSI）具無限記憶，「足長段＝全史」僅漸近成立——實測前置 **57 根**時 RSI-14 差 0.59（rel≈1%）、前置 **≥200 根**時全欄收斂至儲存量子內（MACD-Hist 差恰 1 個 float16 量子 0.015625）。⇒「足長段」操作定義＝**首事件前置 ≥200 根**；低於此屬警示範圍，B1.6 測試以 ≥250 根取證。
- **修訂後義務**：B1.6 驗證①②改為——同事件列逐欄 `|diff| ≤ max(atol, rtol×|全史值|)`；NaN mask 仍須 exact；具名例外欄 `meta_12h_Volume_PriceChange` 恆為 `rtol=1e-3`；其餘欄分層：②末端截斷（因果 invariant）`rtol=2⁻¹⁰`＋atol=0（實測 14/15 欄 exact==0，帶只吸例外路徑）、①段起點截斷（足長段）`rtol=2⁻⁸`＋atol=1e-12（遞迴族 float16 儲存路徑之收斂帶——前置 258 根時 EMA_55 仍差 2 個量子＝rel 1.5e-3；帶取 2⁻⁸≈3.9e-3 覆蓋並附此實測界）。實作＝`tests/momentum/event_samples/test_feature_materialization.py::assert_frames_equal_with_exception`。
- **不變**：因果 invariant 的語意不變（末端截斷下 14/15 欄仍 exact==0 為實際強度）；「禁固定窗」「as-of 取列」「記帳守恆」全部照舊。

### A-02 — 延伸檔檔名規約

- BASE 標頭寫「修訂走延伸檔 `docs/GAP3_EVENT_TODO_AMENDMENTS.md`」；該名含 `TODO` 會被 `doc_format_precheck` 判為 todo 型別而要求完整 TODO 錨點（GOV-DEXT-TEMPLATE-KIND 同型事故）。依規約改以 `docs/GAP3_EVENT_TODO.D-<NNN>.md` 系列實現，本檔＝001；語意不變（凍結文件不就地改）。

### A-03 — B1 施工期之簽名細化備忘（供 review 對讀，非義務變更）

- `build_event_manifest`／`materialize_features_at_decision` 增**選用** keyword `events=`（位置簽名與 BASE 一致）：receipt_schema 為契約閉集不得擴欄，symbol/timeframe context 由 manifest 層攜帶（B1.3 切分與 time-cluster bucket 必要輸入）。
- `entry_after_label_start` 實作為 `entry_at >= label_start`：連續 crypto 網格下 `next_open` 之 entry_at 恰等於 t₀ close，SPEC D2-1 明定該組合 ⇒ true，故 `>` 不可行（`alignment.py` 內註記）。

## 戳記

（B1 批 code review 三家 RECONCILE-STAMP 蓋此區）
