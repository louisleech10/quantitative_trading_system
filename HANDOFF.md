# HANDOFF

## 🔴 接手第一件事：讀 `docs/GAP3UX_IMPL_HANDOFF.md`（完整實作交接，191 行）

GAP-3 事件型 UAT 缺口修補，現在的位置：見下方「下一步」。

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
| `docs/GAP3_EVENT_UX_TODO.D-002.md`（**須並讀**，14 條修訂 A-002..A-015） | 三家 APPROVED | `51f1a65e` |

GAP-3 之 42 個 Task：3 個 ✅、1 個 🔧、38 個 ⬜。
第一批＝Task 1.1／1.10／2.1b／4.2（僅 §G S-9 部分），五輪 code review 收斂（3→2→10→7→0）。
看板：`白話說明/GAP-3施工看板.md`；過程：`白話說明/GAP-3施工進度.md`。

## 本 session 之三件工作（皆已 commit + push）

| # | 內容 | commit |
|---|---|---|
| 1 | GAP-3 第一批實作 ＋ 五輪 code review 收斂 | `dec88c10` |
| 2 | repo 內 11 條既有紅測試：10 條修測試、1 條標記已知產品缺陷 | `1f9dceac` |
| 3 | 該產品缺陷之修法（consult → 實作 → review R1 → review R2 收斂） | `0f09e30f` |

## 工具：mutation 併發隔離（使用者 2026-08-25 明示授權，唯一一項獲准之工具改造）

`scripts/mutation_worktree.py`（新，入版控）—— 每個執行者在自己的 **git worktree 副本**內改檔，
主 repo 零觸碰 ⇒ 三家委員可**平行**跑 mutation，不必排隊。
`scripts/verify_mutation.sh` 改為薄殼委派它；**CLI 與 stdout 判詞字串逐字不變**（委員報告會引用）。
`handoffs/*_mutations.py` 之 import 改指 `scripts/`。

掛載策略（實測導出，非臆測）：ignored 之**檔**用複製（可寫、不外洩），**目錄**用符號連結；
`.claude/gate/` 強制複製（治理測試會寫它，連結會穿透回主 repo）；`.claude/tmp/` 跳過（實測 21 GB）。
路徑 fail-closed：`<檔>` 為絕對路徑或含 `..` ⇒ rc=2（否則 `Path(wt)/"/abs"` 會靜默打回主 repo）。

⚠️ `handoffs/*.py` 由 **`.git/info/exclude:21`（本機檔，非 `.gitignore`）** 排除 ⇒
各 epic runner 本身不入版控，只有 `scripts/` 這支 helper 入。

## 下一步

1. **GAP-3 第二批**＝Task 1.2、1.3、1.4、1.8。其中 Task 1.3 需要第一批已建之
   `momentum/Analysis/event_samples/canonical_serialize.py`。
2. GAP-3 之 UAT B 段簽字仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`）。

## receipt

VERIFY:handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json

| 項 | 值 |
|---|---|
| GAP-3 第一批 mutation | 32 條，`closure: CLOSED` |
| survivor_contract 修法 mutation | 7 條，`handoffs/run_receipts/survivor-nsamples-mutation.receipt.json`，`closure: CLOSED` |
| 先前 20 紅檔 ＋ survivor contract ＋ gap2 persist | 457 passed / 0 failed / 0 xfailed |
| `pytest tests/momentum/event_samples/` | 270 passed |
| `python3 scripts/gap3_freeze_golden.py --check` | rc=0，`canonical_sha=163c4cec…`（全程不變） |

mutation 判準＝**轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。該判準本身救過兩次：
一次抓出主委寫的無效 mutation（空紅集合），一次讓委員之併發假失敗可被辨識。

## 具名殘留（不排工，除非使用者指示）

- ~~**R-MUT-1 mutation runner 非併發安全**~~ → 使用者 2026-08-25 明示授權根治，見上「工具」節。
- **R-B1-1 全量跑之測試順序污染**：`pytest tests/momentum tests/api` 全量跑時有若干紅，
  單獨跑較少。歸因未實跑證明（需以 stashed 樹全量跑一次，約 64 分鐘）。
  三值理由 `needs-research`。owner 主委。
- **R-A005-1 producer-backed 表為人工稽核非執跑探針**：producer 若改算式而未同步該表，本閘看不見。
  三值理由 `needs-research`（需把 `CaseSearchEngine` 之未來欄計算段抽成純函式，屬搜尋引擎重構）。
  owner 主委；觸發＝下次動到該段時一併做。
- **D-002 A-004 前端下界值來源**：`blocked-by` Task 2.1（篩選面板）與 Task 1.3（傳輸點）。
- **D-001／D-002 provenance 不可登記**：`gate.sh register-output` 只收 `handoffs/` 或
  `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報
  provenance pending（**非戳記造假**）。provenance 完備之機械標的為對應 `handoffs/reconcile/.../synth.md`。
  三值理由 `user-ruling`。

## 三條鐵律（違反即返工）

- **完成 ＝ 驗證命令 rc=0 ＋ mutation 實跑轉紅還原轉綠 ＋ receipt 入 commit**。只有測試綠不算完成。
- **不得碰治理**（使用者 2026-08-24 定死）。工具壞掉 ⇒ 繞過並具名記錄，不修不開票。
- **一律字面錨點，禁行號**；檢查寫完要用「已知會紅的輸入」試一次。
  🔴 本 session 最大教訓：**不要用原始碼形狀（或任何代理物）去證明執行期性質**——
  形狀有無限多種等價寫法，逐一補斷言是黑名單，永遠列不完。
  正確的問法是「這個性質為什麼需要用猜的」，答案通常是**改設計讓它變成結構保證**。
  🔴 第二教訓：**不要從少數資料點反推規律**。主委由「100 成功／800 失敗／1695 失敗」
  推出「事件數要夠大才過」，被三家實跑推翻——真正的變數是「過濾後列數 vs 全軸切分列數」。

## 收 epic 前須補

動過 `scripts/plain_docs_sync_check.sh` ⇒ 跑 `bash scripts/gov_check.sh --no-probe`（**丟背景**，
十分鐘級；**跑它時不得動檔**）。
