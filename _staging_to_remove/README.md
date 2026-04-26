# 暫存待移除清單

> **用途**：暫存看起來過時/沒在用的檔案與資料夾，等使用者跑過測試確認沒問題後再刪除。
> **建立日期**：2026-04-26
> **若要還原**：`mv _staging_to_remove/<group>/<item> ./`（或對應子目錄）

---

## 📋 移動清單總覽

| 類別 | 數量 | 子資料夾 |
|------|-----:|----------|
| Logs（執行期日誌） | 10 | `logs/` |
| Pytest/context 文字輸出 | 10 | `scratch_outputs/` |
| Root 級一次性 debug/verify 腳本 | 12 | `one_off_scripts/` |
| 過時/空資料夾 | 6 | `obsolete_folders/` |
| 已不再被引用的比較報告 | 2 | `stale_comparisons/` |
| **合計** | **40** | |

---

## 🗂️ 詳細列表與判斷依據

### 1. `logs/` — 10 個執行期 log
全部都是 `*.log` 結尾的執行期輸出，可隨時重新產生。
- `api.log`, `backend.log`, `frontend.log` — 服務執行 log（由 `dev_stack.sh` 產生）
- `full_test_output.log`, `profile_output.log` — 一次性測試/profile 輸出
- `pytest_full_result.log`, `pytest_output.log`, `pytest_result.log` — pytest 執行紀錄
- `test_final.log`, `test_output.log` — 一次性測試輸出

### 2. `scratch_outputs/` — 10 個 pytest/context 文字輸出
- `pytest_final.txt`, `pytest_full_output.txt`, `pytest_tb_short.txt`
- `test_output.txt`, `test_progress.txt`, `test_results.txt`
- `case_search_context.txt`, `diag_output.txt`, `errors_context.txt`, `full_output.txt`
這些都是過去手動跑測試時的輸出快照。

### 3. `one_off_scripts/` — 12 個 root 級一次性腳本
**已在 `docs/Archived/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` 與 `docs/Archived/Feature_Factory_MultiTF_MultiSymbol_TODO.md` 標記為過時或可歸檔**：
- `analyze_logs.py`, `check_klines.py`, `check_report.py`
- `compare_diff_snippet.py`, `compare_script.py`
- `debug_price_change_method.py`, `diagnostic_roll.py`
- `simple_test.py`
- `test_continuity_edge_cases.py`, `test_price_change_calculation.py`
- `verify_data_integrity.py`, `verify_price_change_csv.py`

> ⚠️ 這些**不在** `tests/` 結構下，pytest 不會收集它們；正式測試在 `tests/` 內。

### 4. `obsolete_folders/` — 6 個過時/空資料夾
| 資料夾 | 移動原因 |
|--------|----------|
| `backend/` | 內部只剩 `.DS_Store`，無實際內容 |
| `data準備移除/` | 名稱字面就是「準備移除的資料」 |
| `test_kline_data_service_cache/` | 只剩 `kline_cache.h5` 測試殘留快取 |
| `verification_data/` | 2025-10 舊驗證資料（`btcusdt_verification_data_20251019_*.xlsx`） |
| `htmlcov/` | 覆蓋率報告（隨時可由 `pytest --cov` 重新產生） |
| `Fix Doc/` | 11 個歷史 fix 摘要 MD（已完成的修復紀錄，不影響執行） |

### 5. `stale_comparisons/` — 2 個未被引用的比較報告
- `V7_vs_V8_Comparison.md`
- `V8_initial_vs_V8_final_Comparison.md`

> 用 `grep -r` 檢查整個 codebase **沒有任何活躍檔案引用**這兩份。
> 留下的 `Pre-opt_vs_V7_Comparison.md` 因為被 `docs/FEATURE_OPTIMIZATION_SPEC.md` 等活躍文件引用，**沒有移動**。

---

## ✅ 沒有移動的疑似候選（保留原因）

| 檔案/資料夾 | 保留原因 |
|--------------|----------|
| `dev_stack` | 是 `scripts/dev_stack.sh` 的 shim，README 中記載 |
| `program.md` | `.github/agents/autoresearch.agent.md` 引用（AutoResearch agent 用） |
| `未來優化清單.md` | `docs/Archived/...` 中明文指定保留 |
| `Pre-opt_vs_V7_Comparison.md` | `docs/FEATURE_OPTIMIZATION_SPEC.md` 等多處引用 |
| `jolly-splashing-harbor.md` | 雖然檔名怪，但內容是「指標架構決策文檔」，有實質內容 |
| `Claude資料備份/` | 名稱就是使用者備份，不擅自移動 |
| `archived/` | 已是歸檔區，不重複歸檔 |
| `sessions/` | 內含活躍 session 文件，使用者工作目錄 |
| `data_cache/` | **真實 K 線資料**，絕不可動 |
| `data/`, `test_data/` | 含 checkpoints / pipeline 設定，仍在使用 |

---

## 🧪 驗證指令

跑完整 Feature Factory 測試掃描，確認沒有破壞任何活躍模組：

```bash
./venv/bin/pytest tests/ -k "feature_factory or feature_preprocessor or feature_extractor or feature_validator or microstructure or large_trade or phase_d or cgsa or atomic or layer1 or layer2 or layer3 or layer4 or layer5 or layer6 or layer7 or preprocessor" --tb=line -q
```
**預期**：381 passed / 0 failed（與 2026-04-26 基線一致）

跑後端啟動測試：
```bash
./scripts/dev_stack.sh start
# 等 5 秒後 curl http://localhost:8000/docs
./scripts/dev_stack.sh stop
```

跑前端 build：
```bash
cd frontend && npm run build
```

---

## 🗑️ 確認沒問題後的刪除指令

```bash
# 確認過後一鍵刪除（不可逆，請先驗證！）
rm -rf _staging_to_remove/
```

或分批刪：
```bash
rm -rf _staging_to_remove/logs
rm -rf _staging_to_remove/scratch_outputs
rm -rf _staging_to_remove/one_off_scripts
rm -rf _staging_to_remove/obsolete_folders
rm -rf _staging_to_remove/stale_comparisons
```

---

## ⏪ 還原指令（若發現有東西被誤移）

```bash
# 還原單一檔案
mv _staging_to_remove/logs/api.log ./

# 還原整個資料夾
mv _staging_to_remove/obsolete_folders/backend ./
```
