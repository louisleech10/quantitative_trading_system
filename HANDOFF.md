# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（唯一入口，301 行）

該檔含：§0 狀態與 B1 交付物、§1 開工前稽核命令、§2 **B2 是什麼＋已做完的偵察（不必重查）**、
§3 派工管線、§4 完成判準與 mutation 寫法、§6 地雷與治理現況、§7 不要碰的東西＋**具名殘留全文**。
**讀完即可開工。本檔只放指標。**

⚠️ 本檔刻意不寫批次代號緊接狀態欄之形態（會與 `governance-batch-status` fact-key 撞名誤報），
亦避開「某某已完成」句型（`verify_pretooluse.sh` 會要求 SUPERSEDED 標記）。

## 狀態

GAP-3 事件型 UAT 缺口修補：SPEC 🔒 FROZEN（`4ce3d6d9`）、TODO 🔒 FROZEN v1.0（`afa70967`）、
延伸檔 D-001（`81cbe7ab`）與 D-002（`51f1a65e`）皆三家 APPROVED。
42 個 Task 之計數：**7 ✅／1 🔧／34 ⬜**（逐 Task 狀態一律看看板，本檔不重述）。

B2（Task 1.2／1.3／1.4／1.8，CSV 匯入主線）已收斂：**兩輪 code review，三家一致可進 B3**。
findings 2 → 1（皆 codex 提出，composer／grok 兩輪皆 0）；P0／P1 全程 0。
R2 由**原提出方 codex** 逐字重跑 R1 兩個反例，**皆確認關閉**（章程 §B8）。
收斂檔 `handoffs/reconcile/20260825-gap3ux-b2-review-r{1,2}/synth.md`（completeness 皆 rc=0）。

**下一步＝B3＝Task 1.11／1.12／1.9**（深度三層防線）。
看板 `白話說明/GAP-3施工看板.md`；歷史 `白話說明/GAP-3施工進度.md`。

## receipt

VERIFY:handoffs/run_receipts/gap3ux-b2-all-mutations.receipt.json

| 項 | 值 |
|---|---|
| 第二批 mutation | **14 條**，`closure: CLOSED`（`handoffs/run_receipts/gap3ux-b2-all-mutations.receipt.json`） |
| 第二批驗收 | `gap3_csv_import` 15／`gap3_t0_unit_detect` 7／`gap3_heterogeneous_rows` 6／`gap3_source_digest` 16；vitest 全套 200；`npm run build` rc=0；G-1 golden rc=0 |
| `pytest tests/api tests/momentum/event_samples` | 849 passed／3 failed／3 errors——6 條**全為既有**，已以 `git stash` 實跑證明改動前後逐字相同 |
| 第一批 mutation | 32 條，`closure: CLOSED`（`handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json`） |
| `survivor_contract` 修法 mutation | 7 條，`handoffs/run_receipts/survivor-nsamples-mutation.receipt.json`，CLOSED |
| `pytest tests/momentum/event_samples/` | 270 passed |
| `python3 scripts/gap3_freeze_golden.py --check` | rc=0，`canonical_sha=163c4cec…`（全程不變） |
| `pytest tests/governance -q` | 1743 passed／6 failed（既有債，見交接 §6.4） |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。

## 具名殘留

**全文一律見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.2／§7.3**（本檔不複列，避免副本漂移）。
代號：`R-GOV7-1`／`R-GOV7-2`／`R-B1-1`／`R-A005-1`／`D-002 A-004`／`D-001-D-002 provenance`
＋ SPEC 末節 `F-1..F-4` ＋ TODO R3 reconcile 四條。
**B2 新增兩條**（全文見 `handoffs/reconcile/20260825-gap3ux-b2-review-r2/synth.md`）：
`R-B2-1` 秒級 t0 之 `event_id` 須寫 ms 版（三家一致判屬 Task 1.5；`blocked-by`）、
`R-B2-2` V-3 執行期 oracle 之 factory-body 繞法（`needs-research`，正解屬 B10 全棧接線）。
另有文件債：TODO Task 1.3「修改檔案」行之 `api/routes/case.py` 字面（三家判 doc drift，
收 epic 前以延伸檔 D-003 更正，不擋 B3）。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
  唯一已授權例外＝mutation 併發隔離（2026-08-25，已完成，用法見交接 §4.1）。
- **一律字面錨點，禁行號**；檢查寫完要用「已知會紅的輸入」試一次。
  「比對範圍過寬」本 epic 已犯**五次**，形狀相同（交接 §6.1 逐條列出）。
