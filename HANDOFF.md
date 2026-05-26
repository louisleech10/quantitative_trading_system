# Handoff

**Agent**: Claude Code | **Time**: 2026-05-26 | **Branch**: main

## 正在做
無（本 session 完成 Copilot → Claude Code 遷移與多 Agent 協作基礎建設）

## 待辦
- （無當前排隊任務）

## 阻塞
- （無）

## 本次決策（接手前必讀）
- SESSION_PhaseX.Y.md 系統廢棄 → 改用 HANDOFF.md（原系統太複雜從未被實際使用）
- gstack 已安裝於 `~/.claude/skills/`：用 `/review`（改完功能後）、`/investigate`（debug卡住時）、`/cso`（加 API 時）、`/qa`（改前端後）
- SessionStart hook 自動注入 HANDOFF.md；PreCompact hook 在 context 壓縮前強制提醒更新

## 踩坑提醒
- `momentum/` 絕不 import `api/`（7 Decoupling Rules，見 CLAUDE.md）
- 所有引擎透過 `momentum/factories.py` 的 `create_*()` 建立，不直接 instantiate
- 數據只從真實 API 或實際計算，絕不 hardcode
