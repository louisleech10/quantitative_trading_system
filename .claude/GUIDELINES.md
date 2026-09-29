# 開發快速參考

> 補充 CLAUDE.md 的中文快速查閱。核心規則請見根目錄 `CLAUDE.md`。

---

## Handoff 協議

`HANDOFF.md`（根目錄）是所有 agent 的共同交接文件。更新規則見 `CLAUDE.md`「Multi-Agent 協作協議」（Claude 維護）與 `AGENTS.md`／`.cursorrules`（執行端寫 `handoffs/<YYYYMMDD>-<task-id>.md`，不改根 `HANDOFF.md`）。

---

## 常用指令

```bash
python run_api.py                    # 啟動後端
cd frontend && npm run dev           # 啟動前端
pytest tests/ -q                     # 跑全部測試（含 tests/governance ⇒ 小時級，一律丟背景；平時只跑受影響模組）
pytest --cov=momentum                # 覆蓋率
./scripts/check_decoupling_phase4.sh # 窄版解耦驗證（只查 R1/R2/R3/R6；見 CLAUDE.md Gotchas）
black . && isort .                   # 格式化
```

---

## Git Commit 格式

```
feat: 添加XXX功能
fix: 修復XXX問題
perf: 優化XXX效能
refactor: 重構XXX
test: 添加XXX測試
docs: 更新XXX文件
```

---

## 量化金融特有陷阱

| 問題 | 錯誤 | 正確 |
|------|------|------|
| 過擬合 | 回測勝率 90%+ | 合理勝率 55-65%，嚴格 train/val/test 分離 |
| 數據洩漏 | 使用未來數據計算信號 | 嚴格時間序列切分，測試集只用一次 |
| 跨標的污染 | 共享 cache 跨 symbol | 每個 symbol 獨立 cache，有隔離 key |

---

## 架構快速查找

| 需要 | 看這裡 |
|------|--------|
| 加 API 端點 | `api/routes/optimization.py` 為模板 |
| 加搜索過濾器 | `momentum/DataExtraction/case_search_engine.py` |
| 加圖表元件 | `frontend/src/components/charts/PriceChart.tsx` |
| 加技術指標 | `momentum/Indicator/Base_Indicator_Reference.py` |
| 加 Feature Factory 引擎 | `momentum/FeatureEngineering/atomic/` |
| 加回測策略 | `momentum/Strategy/vectorized_backtest.py` |
| WebSocket 即時更新 | `api/websocket/optimization_ws.py` |
