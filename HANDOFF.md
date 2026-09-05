# HANDOFF — 當前任務狀態

**更新：2026-09-06｜狀態：`G3-D2` B-D5（最後一批）**實作完成、審碼中**。**

## 🔴 當前＝B-D5 審碼

**唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`**——§2 每批七步不得跳步、§3 地雷、§5 收據、
§6「B-D5 開工前必知」。實作已 commit＋push（`1110077b`→`1cafd564`→`c999f475`）。

**下一步＝派三家 code review（codex＋composer＋grok；實作者不自審）**，
baseline 已建：`.claude/gate/b5_r1_baseline.sha`（1535 檔，`shasum -c` 全 OK）。
收件後**先對證再讀 findings**。

## B-D5 實作（一行）

`platform_random_bars` 全鏈：契約 typed nested schema（鍵級 `required:false`）→
產生器 `random_control.py::sample_random_bars` → `POST /case/import-events/random-control`
＋規則身分閘四段（唯一 owner `ic_analysis_service.compare_random_control`）→ 前端入口 → golden `--kind`。
逐條數字見 `docs/GAP3D2_IMPL_HANDOFF.md` §5 之 B-D5 列。

mutation **32/32 符合預期**；🔴 第一輪 30/32，**抓到四個真實測試缺口**（皆補測試，非改期望）。

新殘留三條**待登記** registry：`B5-SPECGAP-1`／`B5-SINGLECLASS-1`／`B5-GENERATOR-WIRE-1`。

## 收案前必做（B-D5 完工時）

- `B1-VERIFY-1`（三值＝cost）：`tests/api` 與 `tests/governance` **各再跑一次**
  （上次跑的是 B-D3 以前的碼）。`tests/governance` 小時級，**丟背景**。
- registry `G3-D2` 改 CLOSED、`G3-R7` 收回、UAT B3 改「可選項全部通過」待使用者驗。

## 環境現況

開放債為零。工作區餘 2026-09-01 遺留之三個 `uat_samples/*`、八個 `.claude/gate/*baseline*`
與 `market_data/*` 快取異動——**皆非主線產物，勿順手 commit**。
🔴 紀律：`pytest tests/governance` 小時級且不含量化測試，只有「動共用控制流」**且**「收 epic 前」
兩條件皆成立才跑；跑前先問「跑完我要依結果做什麼」。
