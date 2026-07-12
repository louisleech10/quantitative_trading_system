# P2DEBT T5 implementation result (Codex)
Task-id: t5-impl-codex | Date: 2026-07-12 | Status: DONE

## 正在做/已完成
- R2 provenance 已寫回兩份 meta：三事由分述、rebaselined_at、append-only events、canonical projection。
- 兩支 freeze 已加 input_manifest(H5/meta SHA256) 與 symbol/tf/schema/index/order/registry top-N fail-closed guard。
- 新增 `tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py`；未改生產碼/舊 golden 斷言/data_cache。

## 待辦/阻塞
- none。主委裁決 Gate B 為手動重建限制，不列乾淨 checkout committed gate。

## 本次決策
- Gate A 以 pinned H5/meta SHA、identity/schema/order 與語意 replay 閉合；不自動覆寫 canonical inputs。
- Gate B 的 config_hash、command 與 gitignored registry/FF 漂移限制記於 meta；缺 input 時仍可在具 registry 的環境手動重建。
- canonical projection exempt fields 明列 `generated_at` / `task_id_used_for_freeze`；禁用 raw baseline file SHA 作 replay gate。

## VERIFY receipts
- `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q --tb=short` → 10 passed, 4 warnings in 46.98s（6 mutation + 2 synthetic Gate B + 2 Gate A replay）。
- `python -m json.tool` 兩 meta、`venv/bin/python -m py_compile` 三 Python 檔、`git diff --check` → exit 0。
- 實體 Gate B 未執行；依主委裁決記為非乾淨環境手動重建限制，未宣稱 source→input 已重放。
- 稽核欄 diff：復原 reason/date，無不相干數值理由，新增 events/manifest/projection。

## 踩坑提醒
- `py_compile` 預設寫 `~/Library/Caches` 會被 sandbox 擋；`PYTHONPYCACHEPREFIX=/tmp/t5-pycache` 後通過。
- 產出：`handoffs/P2DEBT-T5-IMPL-RESULT-codex.md`
