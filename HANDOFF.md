# HANDOFF — 當前任務狀態

**更新**：2026-08-28　**分支**：main　**HEAD**：見 `git log --oneline -1`

## 現在在哪

**GAP-3 事件型 UAT 缺口修補**：42 Task 之**程式已全部落地**。
**B10（Phase 7 全棧接線，9 Task）**——`7.0／7.0b／7.7` 已收案（R1／R2 兩輪 review 收斂）；
本 session 補完 **`7.1／7.2／7.3／7.4／7.5／7.6`**，53 條 mutation `closure=CLOSED`。
🔴 **下一步＝派 R3 三家 code review**（brief 已寫好：`handoffs/GAP3UX-B10-REVIEW-R3-BRIEF.md`）。
唯一入口 `docs/GAP3UX_IMPL_HANDOFF.md`；白話看板 `白話說明/GAP-3施工看板.md`。

## B10 進度

| Task | 狀態 | 已跑之驗收 |
|---|---|---|
| 7.0／7.0b／7.7 | ✅ 已收案 | R1／R2 收斂，34 條 mutation |
| **7.1** | 🔧 待 R3 | vitest `eventContractOptions` **17**（下限 10） |
| **7.2** | 🔧 待 R3 | vitest `contractEnumWiring` **16**（下限 14；兩檔） |
| **7.3** | 🔧 待 R3 | vitest `eventExportDisclosure` **6**（下限 3）＋ 4.1b legacy **5** 仍綠 |
| **7.4** | 🔧 待 R3 | vitest `eventIcDecayDisclosure` **4** ＋ SPEC `grep -c "IC decay"` = 6 |
| **7.5** | 🔧 待 R3 | pytest `-k return_table_by_label` **13**（下限 10）＋ vitest `eventTablesPanelByLabel` **4**（下限 3） |
| **7.6** | 🔧 待 R3 | pytest `-k event_batch_detail_dims` **7**（下限 3）＋ vitest `icEventBatchDisclosure` **9**（下限 7） |

**mutation：53 條 `closure=CLOSED`**（34 舊 ＋ 7.1×2／7.2×4／7.3×1／7.4×1／7.5×6／7.6×5），
verdict 全 PASS、紅集合逐一等於、六個 baseline 還原後皆 rc=0 且空紅。
receipt `handoffs/run_receipts/gap3ux-b10-all-mutations.receipt.json`。

## 🔴 接手第一件事

1. 照 `docs/GAP3UX_IMPL_HANDOFF.md` **§1** 跑稽核。**期望值已更新**：
   event_samples **345**（原 332）／vitest **68 檔 410**（原 61／351）／
   `tests/api -k` 189＋44＋39＝272 不變＋新增 `-k event_batch_detail_dims` **7**／
   golden `163c4cec…` 不變／TODO Task 數 42 不變／tsc 僅 **8 行**既有債。
2. **派 R3**：`handoffs/GAP3UX-B10-REVIEW-R3-BRIEF.md`（三家全員 codex＋composer＋grok；
   實作者不自審）。派工流程見 `docs/GAP3UX_IMPL_HANDOFF.md` §3。

## 本批之三個主委裁定（R3 須請三家攻；全文在 brief）

1. **裁定 A**：`decision_offset_bars` 於 `/search`／`/ic-analysis` 鎖 0（SPEC 7.1 L2864）
   與 7.2 ③「輸入 k ⇒ 落檔 === k」**互斥** ⇒ ③ 落在函式層 round-trip ＋ `/data-preparation`。
2. **裁定 B**：混批 `control_kind` 回 `null` **不取第一列**——實查
   `_HETEROGENEITY_DIMENSIONS` 不含 `control_kind`，SPEC 7.6 之「異質即 Task 1.8 拒收」
   對該欄**不成立**，而 7.5 明禁多數決。另加 `batch_fact_notes.control_kind_values`
   使「混批」與「沒宣告」可分辨（不破壞驗收①之封閉五鍵）。
3. **裁定 C**：**保留**既有之全批 macro／micro 表，三組另外垂直排在其下
   （`primary_macro` 是批次層統計、不屬任何一組）。若三家判 SPEC 要求取代，即為 finding。

## 本批自己抓到的三個問題（皆非產品碼）

- 🔴 **`7.2-M1` 錄到空紅集合**：我把真契約注入生產元件 ⇒ UI 與期望值**兩側同源**，
  「契約改了而 UI 沒跟」永遠不紅。改為「元件走鏡像、期望值走真契約」後才錄到紅。
- **`tsc` 抓到我測試檔的重複鍵**：其餘四維度被 `...UNSET` 灌成空字串而測試照樣綠
  （`npm run build` **不涵蓋測試檔**，§3 第 8 條）。
- **新文案撞既有斷言**：4.1c 禁「重新匯出」四字。**沒有放寬既有守衛**，改自己措辭為「不必再匯出一次」。

## 工具面：mutation runner 之潛伏缺陷已修

`scripts/mutation_worktree.py` 之 `git diff HEAD` **缺 `--binary`** ⇒ repo 內**被版控的**
numba 快取（`**/__pycache__/*.py39.nbi`，跑過測試就髒）產生二進位 stub，
`git apply` 直接失敗、**整個 runner 起不來**。前九批僥倖沒踩到。

## 磁碟：`.claude/tmp` 20G 已清

委員／治理隔離工作樹不自清，累積到 **20G**（單一目錄 9.5G——複製時沒排除 `.claude/`，
把整包 `.claude/tmp` 套進 `iso/.claude/`）。已清（**只刪目錄、散檔全留**，
`fact_keys.json` 引為證據的兩個檔完好）。新增 `scripts/clean_agent_tmp.sh`
並掛進 `agent_postflight.sh`（派工後必跑 ⇒ 機械強制，不靠紀律）。

## 待辦

- [ ] 🔴 **派 R3 三家 code review** ＋ reconcile ＋ 閉合輪（由原提出方重跑自己的反例）
- [ ] **收 epic 前**：使用者 **UAT B 段 13 項簽字**（未簽不收案）
- [ ] 本批**動過 `scripts/`**（`mutation_worktree.py`／`agent_postflight.sh`／新 `clean_agent_tmp.sh`）
      ⇒ 收 epic 前跑 `bash scripts/gov_check.sh --no-probe`（**丟背景**，十分鐘級）
- [ ] repo 外之磁碟清理（我權限被擋，指令已給使用者）：`com.apple.wallpaper/aerials` 11G、
      `Caches/VSCodeInsiders.ShipIt` 1.5G、`Claude/vm_bundles` 11G（需先關 Claude 桌面版）

## 具名殘留（全文見 `docs/GAP3UX_IMPL_HANDOFF.md` §7.3）

**B10 已解除**：`R-B3-3`（per-symbol purge 下界）、`R-B8-1`（glossary definition 收窄——
Task 7.5 已補三個分組標籤＋兩個 `not_computed` 文字進 `event_metrics_glossary.json`）。
**仍在**：`R-B7-1`（`label_value` 走 `_is_num` 仍收 NaN）、`R-B2-2`（工廠繞法）、
`R-D005-1`、`R-B9-1..5`、`MEASURE-CANCEL-1`、`R-BRIEF-1..4`。

## 給下一個 session 的坑

- 🔴 **`.nbi` 是被版控的**：跑完測試 `git status` 會多出 22 個 numba 快取改動。
  commit 前先 `git checkout --` 還原，否則會把快取雜訊混進 commit。
- 🔴 **前端測試不得把真契約注入生產元件**：那會讓「契約漂移」類的機械閘永遠不紅（本批實證）。
- 🔴 **收案前固定跑 `npx tsc --noEmit`**：`npm run build` 不涵蓋測試檔，本批靠它抓到真缺陷。
- `pytest tests/api` **會改寫** `data_cache/features/registry.json`；各 Task 用 `-k` 選擇器。
- `git commit -F` 每次走權限分類器約 13 秒；`npm run build`／mutation runner 被哨兵報 A 類卡頓是**誤報**。
