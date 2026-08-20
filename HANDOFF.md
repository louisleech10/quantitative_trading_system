# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**GAP-3 開 B2 施工（B1 已 CLOSED 2026-08-21：四輪 review 8→3→1→0＋三家戳記 rc=0）**

- **依據**：`docs/GAP3_EVENT_TODO.md`（FROZEN）＋延伸檔 `docs/GAP3_EVENT_TODO.D-001.md`（A-01 FF float16 容差分層／A-02 檔名規約／A-03 `events=` context keyword＋`entry_after_label_start >=`）；SPEC FROZEN。
- **B2 批內順序**：B2.1 → B2.2 → **`scripts/gap3_freeze_golden.py --write`（import 復用 `gap2_freeze_golden.py::gap2_canonical_sha`，寫 `handoffs/run_receipts/gap3_golden_pre.json`，獨立 commit）** → B2.3（沿 `event_timestamps` 入口；v2 payload 在 B2.4 前不得寫）→ B2.4（`momentum/Analysis/survivor_contract.py`＋json v1→2）→ B2.5。mutation 本批落 M4/M7/M11；B2 Gate 命令見 TODO §B。
- **B1 產出可用介面**：`event_samples/{import_contract,alignment,dedupe,event_split,feature_materialization,baseline,counterexample_classifier}.py`；`build_event_manifest(..., events=)`／`materialize_features_at_decision(..., events=)` 需帶 events context；`single_feature_binary_baseline(..., feature_manifest_hash=<64hex>)` 必填；`permutation_oracle(values, y, stat_fn, cfg)` 供 B2.2/B2.3 重用（W3）。
- **每批收尾固定動作**：更新 `白話說明/GAP-3施工進度.md`（WATCHED 已登記）＋接下來/README；commit 後背景 push；review 輪 session 命名 `20260821-gap3-b2-review-r<N>`。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十二）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；session 命名規約 `<YYYYMMDD>-<epic>-<batch|x>-<kind>-r<N>`、task-id＝大寫。
- 🔴 FF V7 `features_df` 恆 0 欄——特徵走 `create_feature_reader().load_columns_v2/load_row_index_v2`（row_index＝bar open 秒）；儲存 float16 為主；standard preset 跑 ~150s、minimal 0.8s。kline cache timestamp＝epoch 秒、bar open_time。
- 🔴 戳記時序：stamp-target 先建空 `## 戳記` 區再派；戳記後 `gate.sh register-output <TASK> <synth>` 補 provenance。debt 銷帳 `debt_clear.sh --round-id --session --lock`。
- 白話看板表格狀態欄用文字不用 ⬜／✅（factkey 守衛）；`factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 紅＝既有；push 丟背景；venv Python 3.9.6。
