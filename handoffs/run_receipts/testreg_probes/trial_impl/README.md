# TESTREG 試作實作（TODO 審查期主委試作，2026-10-11 保存）

用途：b1 施工（Task 1.1–1.5）之起點。對照之驗收測試＝提交 7351ad1e 之 `tests/registry/`（SPEC v32／契約 version 32）。
基底：暫存 git worktree（detached c15e169a）中開發，測試檔逐輪複製最新版驗證；**未經正式審碼，搬入前須逐檔對照 SPEC 改法**。

## 檔案
- `scripts/testreg.py`：Phase 1 全部（validate V01–V22、收據 E0／E1／mutation、bootstrap、markers、check／hook 路由、assertion 引擎）。含 r22–r30 實測後之效能修正：decreased_defs 完整展開輪廓＋語法樹候選、測試檔差量只算受影響函式、skip_rule、pytest.ini 收集四項與超集不檢、`_Tree.prefetch` 批次讀、HEAD 查詢快取、解析快取、同行程共用引擎、V15 只對有 rewrite_targets 之 entry 讀檔、`_Tree.exists` 集合快取。
- `scripts/testreg_write_guard.sh`：hook 路由（含 `pytest.ini`）。
- `tests/fixtures/testreg_recorder_plugin.py`：記錄器。
- `scripts/framepath_affected_gate.phase2_minimal_wiring.py`：**僅供驗證 Task 2.3 測試（04e／04i）可行之最小接線，非 b1 範圍、非生產碼**。

## 試作驗證結果（暫存工作樹）
- `test_testreg_write_guard.py`＋`test_testreg_validate.py`：281 項綠（排除需真實 repo 之邊界 05／06／07／07b、⑧、掛載與 pre-commit 接線）。
- `test_testreg_recorder.py`：除 §G 收據外綠（§G 須 b1 先凍結基準再接記錄器）。
- `test_testreg_markers.py`：2 紅待 Task 1.4 於 pytest.ini 註冊 flaky_quarantine／timeout。
- `test_testreg_bootstrap.py` 真實 repo 兩項：待 b1 bootstrap 並提交清冊。
- 真實穩態計時（暫存 clone，清冊在 HEAD）：hook 一般 0.18–0.42 秒、最大測試檔刪 helper 斷言 0.77 秒；pre-commit 基線 0.33 秒、最壞 0.95 秒；pytest.ini 收集縮減 1.5–3.0 秒。

## b1 待做（照 manifest batch_card）
§G 基準凍結（recorder_invariance.py）→ 記錄器接入 tests/conftest.py → pytest.ini 標記註冊 → bootstrap 清冊（約 6 分）＋收據 → hook 掛載 .claude/settings.json＋pre-commit＋GOV_ENFORCEMENT_REGISTRY → 跑 gate_cmd 五檔 → 審碼。
