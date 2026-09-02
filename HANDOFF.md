# HANDOFF — 當前任務狀態

**更新：2026-09-03 00:40｜狀態：`G3-D2` 灰色項目——開工稽核完成、consult r1 已派（三家跑中）、主委版已寫；使用者離線（委員共識決）**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D2` | **進行中**：大任務完整管線。session `20260903-gap3d2-x-consult-r1`（round `6810e862`）；brief `handoffs/20260903-GAP3D2-X-CONSULT-R1-BRIEF.md`；主委版 `handoffs/20260903-gap3d2-x-consult-r1-claude.md`；探針 `handoffs/20260903-gap3d2-probe-triplets.{py,receipt.txt}` |
| `G3-D1`／`D3`…`D17` | CLOSED |
| `KLINE-1` | OPEN（可穿插） |

## 本 session 開工稽核補正（已寫入 `docs/GAP3D2_KICKOFF_HANDOFF.md` §3 末）
- 🔴 連續網格別名：open 語意之 `label_start_ms` 被 `_close_at` 命中為 t₀−1 close（靜默錯價）⇒ (c) 缺口在 producer 取價，不只 golden。
- `all_bars_eval.py` 已存在（缺模型分數 G3-R9）；`event_known_at_decision` 契約有、碼零實作；`ret_entry`／`ret_label_anchor` 並排已在事件後報酬表。
- 既有 9 批：5 批 (C,k=0)、**4 批 (B,k=1)**（CSV 路徑）；k 改制須揭露「批次記錄 k／本次分析 k」。

## 下一步（consult 回來後）
1. `bash scripts/reconcile_build.sh 20260903-gap3d2-x-consult-r1 --mode discovery <三家檔> <claude 檔>` → 群集／處置 → attribution → completeness → `debt_clear.sh --round-id 6810e862-7640-4990-a54e-22c27d464963 --session 20260903-gap3d2-x-consult-r1`。
2. 白話裁決題寫入 `白話說明/接下來要做什麼.md`（頭條＝主目標 B 之交付有多少是改名／多少是做東西；C 不可表示之殘留 G3-R13）；使用者離線 ⇒ 委員共識決並具名，醒後可否決。
3. SPEC：主委傾向 D 延伸 `docs/GAP3_EVENT_UX_SPEC.D-001.md`（gate artifact）→ 三家 adversarial → 戳記 → TODO → 實作（Claude）→ 三家 review。
4. 派工命名 `<YYYYMMDD>-gap3d2-<batch>-<kind>-r<N>`，**task-id＝session 大寫**（本 session 已被擋一次）。

## 已知紅／不要誤判
- `tests/api` 既有紅（G3-R11）；`test_ic_deep_analysis` 並行 ERROR 單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`、`GOV-DOC-STATUS-1`。
- 債開著時，Bash 指令含家族名會被 gate 當 dispatch 擋（前 session 踩過）。
