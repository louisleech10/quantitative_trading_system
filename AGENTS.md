# Agents — Codex / Multi-Agent Protocol

## 第一步：讀 HANDOFF.md
開始任何工作前，讀取根目錄的 `HANDOFF.md`。這是所有 agent 的共同交接文件。

## 最後一步：更新 HANDOFF.md
完成工作或交接前，更新 `HANDOFF.md`（≤ 30 行）：
- 正在做 / 待辦 / 阻塞 / 本次決策 / 踩坑提醒

---

## 專案概覽

量化交易研究平台。Stack：FastAPI (`api/`) → 核心引擎 (`momentum/`) → Next.js 15 (`frontend/`)

## 7 大解耦規則（零容忍）

1. `momentum/` 絕不 import `api/` → `grep -r "from api\." momentum/` → 必須 0 結果
2. 跨域依賴 → Protocol injection（`momentum/core/protocols.py`）
3. 服務用 factories，不直接 instantiate → `from momentum.factories import create_*`
4. 服務不互相 import
5. Config 單一來源：`momentum/core/config.py`（引擎）或 `api/core/config.py`（API）
6. 測試不依賴 `run_api.py` → `pytest tests/momentum/` 獨立運行
7. DTO 不跨域 → `api/models/`（API）或 `momentum/core/contracts.py`（引擎）

## 常用指令

```bash
source venv/bin/activate && python run_api.py  # backend :8000
cd frontend && npm run dev                      # frontend :3000
pytest                                          # 全部測試
grep -r "from api\." momentum/                 # 解耦驗證
```

## 完整規範

見根目錄 `CLAUDE.md`。
