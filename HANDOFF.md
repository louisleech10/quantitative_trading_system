# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（完整實作交接，191 行）

GAP-3 事件型 UAT 缺口修補，現在的位置：見下方「停在哪」——三個取捨等使用者裁定，
主委不自行往下走。

⚠️ 本檔刻意**不寫**批次代號緊接狀態欄之形態——那會與治理 epic 之
`governance-batch-status` fact-key 撞名而誤報（前例：commit `ee69cb7c` 之看板）。
⚠️ 本檔亦刻意避開「某某已完成」之句型——`verify_pretooluse.sh` 會要求 SUPERSEDED 標記
（本 epic 校準期有過 FAIL 紀錄）。狀態一律以下表與 receipt 呈現，不寫成宣稱句。
依使用者 2026-08-24「不得碰治理」之裁定，**繞過並具名，不修工具**。

## 狀態

| 文件 | 狀態 | commit |
|---|---|---|
| `docs/GAP3_EVENT_UX_SPEC.md`（語意權威） | 🔒 FROZEN，42 Task | `4ce3d6d9` |
| `docs/GAP3_EVENT_UX_TODO.md`（操作依據） | 🔒 FROZEN v1.0，42 Task | `afa70967` |
| `docs/GAP3_EVENT_UX_TODO.D-001.md`（**須並讀**） | 三家 APPROVED | `81cbe7ab` |
| `docs/GAP3_EVENT_UX_TODO.D-002.md`（**須並讀**，14 條修訂 A-002..A-015） | ⚠️ 尚未取得委員戳記 | `fa172e44` |

GAP-3 之 42 個 Task：3 個 ✅、1 個 🔧、38 個 ⬜。
第一批＝Task 1.1／1.10／2.1b／4.2（僅 §G S-9 部分）；程式落地於 commit `fa172e44`，
已跑四輪三家 code review。
看板（給使用者看）：`白話說明/GAP-3施工看板.md`；過程：`白話說明/GAP-3施工進度.md`。

## 🔴 停在哪：三個等使用者裁定的點

1. **要不要再開第五輪 code review？** 四輪之 findings 趨勢：3 → 2 → 10 → 7。
   P0 全程 0、P1 連兩輪 0，第一輪之後之 findings 皆屬「測試強度」而非產品邏輯。
   第四輪七條之修法全為機械級（參數化／逐字比對／spy），無一需改設計。但條數未歸零。
   詳見 `handoffs/reconcile/20260824-gap3uxb1-x-review-r4/synth.md` 之收斂趨勢節。
2. **D-002 要不要在開下一批前補跑戳記輪？** 14 條修訂中含一條資料正確性處置（A-005）
   與一次設計改變（A-010）。D-001 是使用者明示要補的；D-002 主委不自行假設。
3. **`R-B1-1`** 要不要花約 64 分鐘釘死（見下）。

## 第一批之 receipt

VERIFY:handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json

| 命令 | 輸出 |
|---|---|
| `pytest tests/api -k "gap3_contract_reason_registry or lookahead_rename_attack or gap3_lookahead_depth or gap3_future_column_inventory_drift"` | 54 passed |
| `pytest tests/momentum/event_samples/ -q` | 270 passed |
| `npm --prefix frontend test -- src/lib/lookaheadDepthLock` | 23 passed（2 檔） |
| `npm --prefix frontend run build` | rc=0 |
| `python3 scripts/gap3_freeze_golden.py --check` | rc=0，`canonical_sha=163c4cec…`（五輪不變） |
| `grep -rn "from api\." momentum/Analysis/event_samples/` | 0 |
| mutation | 32 條；receipt 之 `closure` 欄為 `CLOSED` |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。
該判準本身在第四輪擋下一次問題：主委一條回歸鎖第一版無效（副本又委派回本尊），
因實跑得到**空紅集合**才被抓出。

## 具名殘留（不排工，除非使用者指示）

- **R-B1-1 全量跑之測試順序污染**：`pytest tests/momentum tests/api` 全量跑時 20 檔有 59 條紅，
  單獨跑只有 11 條。差距 48 條與本批之改動面無交集（那 59 條一條都沒碰到本批改過的檔），
  但「順序污染」此一歸因**尚未實跑證明**（要證需以 stashed 樹全量跑一次，約 64 分鐘）。
  旁證：`tests/momentum/event_samples/` 全目錄現為 270 passed／0 failed，
  composer 在第一輪所報之 5 條污染此後未再重現。三值理由 `needs-research`。owner 主委。
- **R-A005-1 producer-backed 表為人工稽核非執跑探針**：producer 若改算式而未同步該表，本閘看不見。
  三值理由 `needs-research`（要執跑探針須把 `CaseSearchEngine` 之未來欄計算段抽成純函式，
  屬搜尋引擎重構，超出本批範圍）。owner 主委；觸發＝下次動到該段時一併做。
- **D-002 A-004 前端下界值來源**：`blocked-by` Task 2.1（篩選面板）與 Task 1.3（傳輸點），皆在後續批次。
- **D-001／D-002 provenance 不可登記**：`gate.sh register-output` 只收 `handoffs/` 或
  `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報
  provenance pending（**非戳記造假**）。D-001 之 provenance 完備標的＝
  `handoffs/reconcile/20260824-gap3uxtodod001-x-stamp/synth.md`（rc=0）。三值理由：`user-ruling`。

## 下一批（使用者裁定收斂後才開）

第二批＝Task 1.2、1.3、1.4、1.8。其中 Task 1.3 需要第一批已建之
`momentum/Analysis/event_samples/canonical_serialize.py`。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24 定死）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
- **一律字面錨點，禁行號**；檢查寫完要用「已知會紅的輸入」試一次。
  🔴 本批之最大教訓：**不要用原始碼形狀（或任何代理物）去證明執行期性質**——
  形狀有無限多種等價寫法，逐一補斷言是黑名單，永遠列不完。
  正確的問法是「這個性質為什麼需要用猜的」，答案通常是**改設計讓它變成結構保證**。

## 收 epic 前須補

動過 `scripts/plain_docs_sync_check.sh` ⇒ 跑 `bash scripts/gov_check.sh --no-probe`（**丟背景**，
十分鐘級；**跑它時不得動檔**）。另 GAP-3 之 UAT B 段簽字仍在使用者手上。
