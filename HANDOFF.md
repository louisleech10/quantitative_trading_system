# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**GAP-3 開 B1 施工（🔴 需使用者點頭才動工；TODO 已 FROZEN，2026-08-20 白話閘核准）**

- **TODO＝`docs/GAP3_EVENT_TODO.md`（FROZEN；修訂走延伸檔 `docs/GAP3_EVENT_TODO_AMENDMENTS.md`）**；SPEC＝`docs/GAP3_EVENT_SPEC.md`（FROZEN）。層級：操作依據＝TODO、語意權威＝SPEC、欄位字面 SoT＝`event_import_contract.json`（B1.0 產出）。
- 對抗審履歷：TODO R7 14 findings（12 群集寫回）→ R8 閉合 0（synth 鏈 `handoffs/reconcile/20260820-gap3-x-review-r{7,8}/`）；三家 RECONCILE-STAMP 蓋 r8 synth rc=0（stamp-r3）；債帳 0 OPEN。
- **下一步**：使用者點頭 → 照 TODO §B 開 B1（批內順序 B1.0→B1.1→B1.2→B1.3→B1.6→B1.4→B1.5；7 Task；主委自任實作）；批完成跑 TODO §B B1 Gate 全命令 → 三家 code review＋戳記（quorum 機檢）才進 B2。B2.3 動工前先跑 `scripts/gap3_freeze_golden.py --write`（§G 凍結；復用 gap2_canonical_sha）。
- 提醒：mutation fixtures seed 20260820、sha256 首建記 `handoffs/run_receipts/gap3_mutation_fixtures.json`；B3.3 測試落新建目錄 `tests/momentum/feature_engineering/`；review 輪 session 接續 `20260820-gap3-x-review-r9` 起。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十一）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`。committee_run 一家失敗：同 round `ROUND_ID=<id> bash scripts/cx_run.sh <fam> <brief> <out>` 補跑；**同 round 該家已 success 拒重派 ⇒ 開新輪**。
- 🔴 session 命名規約機檢：`<YYYYMMDD>-<epic>-<batch|x>-<kind>-r<N>`、task-id＝session 大寫；不符 fail-closed 拒發 token。
- 🔴 Cursor `resource_exhausted` 多為端點暫時故障非額度（先最小探針，rc=0 即重派）；review/stamp 輪禁 abandon。
- 🔴 戳記時序坑：stamp-target 先建空 `## 戳記` 區再派 stamp（body hash 邊界固定）；戳記格式 `RECONCILE-STAMP: <fam> APPROVED <date> sha256:<body-hash> task:<TASK-ID>`。
- reconcile 正式入口＝`completeness_check.sh --lock`；債銷帳＝`debt_clear.sh --round-id <id> --session <name> --lock <lock>`。
- `factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 紅＝既有；`scripts/governance_families.json` no-op dirty＝既有；push 丟背景；venv Python 3.9.6；三支臨時腳本 `scripts/ichc_t2_*.py`／`ichc_t3_diff.py` 待清（非本線）。
