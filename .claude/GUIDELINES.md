# 開發快速參考

> 補充 CLAUDE.md 的中文快速查閱。核心規則請見根目錄 `CLAUDE.md`。

---

## Session Status 管理

每次工作必須追蹤 Session，格式：`SESSION_PhaseX.Y.md`

**六大更新時機**：
1. 提出 PLAN → 記錄到計劃列表（PLANNED）
2. 開始執行 → PLANNED → IN_PROGRESS
3. 完成任務 → IN_PROGRESS → COMPLETED
4. 遇到阻塞 → BLOCKED + 原因
5. 切換 AI → 記錄切換點
6. Debug → 記錄問題和解決方案

**工作流程**：
```
開始新工作 → 讀取 .claude/STATUS.md + 最新 SESSION_Phase*.md
提出 PLAN → 先更新 Session，再實作
完成後 → 更新 SESSION
```

---

## 常用指令

```bash
python run_api.py                    # 啟動後端
cd frontend && npm run dev           # 啟動前端
pytest tests/ -q                     # 跑測試
pytest --cov=momentum                # 覆蓋率
./scripts/check_decoupling_phase4.sh # 解耦驗證
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
