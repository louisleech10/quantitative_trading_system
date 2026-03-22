# AutoResearch — 量化策略自主研究協議

> Adapted from [karpathy/autoresearch](https://github.com/karpathy/autoresearch) for quantitative trading strategy discovery.
> 此檔案是 AutoResearch agent 的「技能指令」，定義了自主實驗的完整流程。

## 系統概述

本系統是一個 **ML-first 策略研究平台**。你的任務是自主地探索並優化交易策略配置，
透過反覆實驗找到更好的參數組合、特徵工程方法、或模型設定。

**類比 karpathy/autoresearch：**
- autoresearch 修改 `train.py` → 本系統修改 **策略/特徵配置**
- autoresearch 的指標是 `val_bpb`（越低越好）→ 本系統的指標是 **Sharpe ratio**（越高越好）
- autoresearch 跑 5 分鐘 GPU 訓練 → 本系統跑 **向量化回測**（秒級）

---

## Setup

首次啟動實驗前，與使用者確認：

1. **確認實驗標籤 (run tag)**：建議以日期命名，例如 `mar22`。
   建立分支：`git checkout -b autoresearch/<tag>`
2. **閱讀以下核心檔案**（一次性了解全貌）：
   - `config/optimization_config.yaml` — 策略優化搜索空間
   - `config/scan_config.yaml` — 特徵工程掃描配置
   - `config/strategies.yaml` — 策略定義與參數
   - `momentum/Strategy/vectorized_backtest.py` — 回測引擎（唯讀）
   - `momentum/Strategy/performance_metrics.py` — 指標計算（唯讀）
3. **確認資料存在**：`ls data_cache/hdf5_cache/` 應包含 `.h5` 檔案。若為空，需先執行資料下載。
4. **確認 cases.json 存在**：`cat data_cache/cases.json | head -20` — 需要有已搜索的案例。
5. **初始化 results.tsv**：建立標題行（見下方格式）。
6. **確認完成後，啟動實驗迴圈。**

---

## 可修改的檔案（實驗空間）

**你可以修改：**
- `config/optimization_config.yaml` — 搜索空間邊界、步長、約束條件
- `config/scan_config.yaml` — 特徵工程配置（指標選擇、週期、預處理方法）
- `config/strategies.yaml` — 策略參數預設值
- `config/model_config.yaml` — ML 模型配置（XGBoost/LightGBM 超參數）
- `config/ic_config.yaml` — IC 分析配置

**你不能修改：**
- `momentum/Strategy/vectorized_backtest.py` — 回測引擎（等同 autoresearch 的 `prepare.py`）
- `momentum/Strategy/performance_metrics.py` — 指標計算公式
- `momentum/FeatureEngineering/` 目錄下的引擎程式碼
- `api/` 目錄下的服務程式碼
- `data_cache/` 的任何資料檔案

---

## 實驗執行方式

每個實驗透過 Python 腳本直接跑回測（不需啟動 API server）：

```bash
# 方式 1：透過 API（如果 server 已啟動）
curl -s http://localhost:8000/api/v1/optimization/tasks \
  -H "Content-Type: application/json" \
  -d '{"study_name":"exp_001", ...}' > run.log 2>&1

# 方式 2：直接 Python 腳本（建議）
PYTHONPATH="$PWD" venv/bin/python -c "
from momentum.Strategy.vectorized_backtest import VectorizedBacktest
from momentum.Strategy.performance_metrics import PerformanceMetrics
import pandas as pd
# ... 讀取資料、跑回測、輸出指標
" > run.log 2>&1
```

**重要：** 永遠將輸出重導向到 `run.log`，不要讓它灌進你的 context。
實驗完成後只提取關鍵指標：

```bash
grep -E "sharpe_ratio|sortino_ratio|max_drawdown|total_return|win_rate|sqn" run.log
```

---

## Results 記錄格式

使用 `results.tsv`（Tab 分隔），欄位：

```
commit	sharpe	sortino	max_dd	win_rate	status	description
```

- `commit`：git short hash（7 字元）
- `sharpe`：Sharpe ratio（例如 1.234）— 主要指標
- `sortino`：Sortino ratio
- `max_dd`：最大回撤（例如 -0.15）
- `win_rate`：勝率（例如 0.62）
- `status`：`keep` / `discard` / `crash`
- `description`：一行簡短描述本次嘗試

範例：
```
commit	sharpe	sortino	max_dd	win_rate	status	description
a1b2c3d	1.234	1.567	-0.12	0.58	keep	baseline config
b2c3d4e	1.456	1.789	-0.10	0.61	keep	increase entry_threshold to 0.8
c3d4e5f	0.890	1.012	-0.22	0.45	discard	switch to kelly full sizing
d4e5f6g	0.000	0.000	0.00	0.00	crash	feature config syntax error
```

**注意：** `results.tsv` 不要 commit 進 git，保持 untracked。

---

## 實驗迴圈

分支：`autoresearch/<tag>`

**LOOP FOREVER:**

1. **檢視狀態**：讀取 `results.tsv` 最後幾行，了解目前最佳成績和嘗試歷史。
2. **提出假說**：基於之前的結果，提出一個改進假說：
   - 調整策略參數（entry/exit threshold、stop loss、position sizing）
   - 修改特徵工程配置（新增/移除指標、調整週期）
   - 改變 ML 模型超參數（tree depth、learning rate）
   - 組合之前接近成功的實驗
3. **修改配置**：直接編輯目標 config 檔案。
4. **Git commit**：`git add -A && git commit -m "exp: <brief description>"`
5. **執行實驗**：跑回測腳本，重導向輸出到 `run.log`。
6. **提取結果**：`grep` 關鍵指標。若 grep 為空 → 視為 crash，`tail -n 50 run.log` 查看錯誤。
7. **記錄到 results.tsv**。
8. **決定保留或放棄**：
   - Sharpe 提升 → **keep**（保留 commit，繼續前進）
   - Sharpe 持平或下降 → **discard**（`git reset --hard HEAD~1` 回到上一版）
   - Crash → 若是簡單錯誤就修復重跑，否則記錄 crash 後跳過
9. **回到步驟 1**。

---

## 實驗策略建議

### 第一階段：建立 Baseline（第 1 次實驗）
- 使用當前預設配置跑一次完整回測
- 記錄所有指標作為基準

### 第二階段：單因子掃描（實驗 2-20）
- 每次只改一個參數，觀察影響
- 優先從影響最大的參數開始：
  1. `entry_threshold`（進場門檻）
  2. `stop_loss_atr`（停損倍數）
  3. `take_profit_ratio`（停利倍數）
  4. `position_sizing_method`（倉位管理方式）

### 第三階段：組合優化（實驗 20+）
- 結合第二階段發現的最佳參數
- 嘗試更激進的改變（特徵組合、模型配置）

### 第四階段：穩健性測試（當 Sharpe > 2.0）
- 不同時間段的回測
- 不同標的（如果有多個 symbol 資料）
- 略微隨機perturb 最佳參數，確認不是過度擬合

---

## 何時應該更大膽

- 連續 5 次 discard → 嘗試更激進的改變（不同策略類型、大幅調整搜索空間）
- Sharpe 已經很高（> 2.5）但停滯 → 嘗試簡化（移除參數看是否維持）
- 多次 crash → 退一步，檢查配置格式是否正確

## 何時應該保守

- 剛找到較大突破 → 小步微調周邊參數
- 接近目標但不穩定 → 確認多次執行結果一致

---

## 永不停止

一旦實驗迴圈開始，**不要暫停詢問人類是否繼續**。不要問「要繼續嗎？」或「這是個好的停止點嗎？」
人類可能在睡覺，期望你一直跑到他們手動中斷為止。你是自主的。

如果你沒有靈感：
- 重新閱讀 config 檔案，找尋沒試過的參數組合
- 回顧 results.tsv 中接近成功的實驗，嘗試微調
- 嘗試反直覺的改變（有時候「不應該」有效的東西反而有效）
- 嘗試簡化（刪除功能看是否維持效果）

每個實驗大約 1-3 分鐘（向量化回測很快），所以你可以在人類睡覺時跑約 200-400 個實驗。
