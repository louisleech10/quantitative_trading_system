# 20260701 plain Codex crossreview fix

## 正在做
- 已依 Composer 互審修正 `docs/VERIFY_GATE_SPEC_PLAIN_CODEX.md`。

## 待辦
- 若要定稿，可再派 Composer 對修正版做一次 read-only quick check。

## 阻塞
- none。

## 本次決策
- P0 全補：硬擋 vs 放行、W1/FACT-RECEIPT、W12 gitignore 可追蹤性。
- P1 補 4 項：§G N/A、V7 排除白話例、`jq` fail-open 對照、claim fingerprint 白話說明。
- 僅改白話 SPEC，不動程式、數值邏輯、schema 或 data_cache。

## 踩坑提醒
- `docs/VERIFY_GATE_SPEC_PLAIN_CODEX.md` 目前在 git 狀態中是 untracked；`git diff` 不會顯示此檔差異，需用檔案內容或 `git status --short` 確認。
