# HANDOFF — 當前任務狀態

**更新**：2026-08-28　**分支**：main　**HEAD**：見 `git log --oneline -1`

## 現在在哪

**GAP-3 事件型 UAT 缺口修補**：42 Task **全部落地且四輪 review 全數收斂**。
**B10（Phase 7 全棧接線，9 Task）**——`7.0／7.0b／7.7` 經 R1／R2 收案；
`7.1–7.6` 經 **R3（八條 findings 全成立、全修）** 與 **R4 閉合輪（原提出方逐條 CLOSED）** 收斂。
**58 條 mutation `closure=CLOSED`**。
🔴 **下一步＝使用者 UAT B 段 13 項簽字**（未簽不收案）＋ 動過 `scripts/` 故須跑一次
`gov_check.sh --no-probe`。唯一入口 `docs/GAP3UX_IMPL_HANDOFF.md`；白話看板 `白話說明/GAP-3施工看板.md`。

## B10 進度

| Task | 狀態 | 已跑之驗收 |
|---|---|---|
| 7.0／7.0b／7.7 | ✅ 已收案 | R1／R2 收斂 |
| **7.1–7.6** | ✅ **R3＋R4 收斂** | vitest `eventContractOptions` 18／`contractEnumWiring` 20／`eventExportDisclosure` 8＋legacy 5／`eventIcDecayDisclosure` 4／`eventTablesPanelByLabel` 4／`icEventBatchDisclosure` 11；pytest `-k return_table_by_label` 13／`-k event_batch_detail_dims` 7 |

**mutation：58 條 `closure=CLOSED`**（34 舊 ＋ 7.1–7.6 之 19 ＋ R3 之 4 ＋ R4 之 1），
verdict 全 PASS、紅集合逐一等於、六個 baseline 還原後皆 rc=0 且空紅。
receipt `handoffs/run_receipts/gap3ux-b10-all-mutations.receipt.json`。

## 四輪 review 之收斂

**R3（八條 findings，三家，全部成立全部修）**：
- **群集 A（P1，三家一致）**：裁定 A 之「鎖 k=0」只有 HTML `min`/`max` 提示，
  輸入未 `readOnly`、`onChange` 未 clamp ⇒ 使用者真的能讓落檔／payload 帶 `k=3`。
  🔴 **我自己把錯的性質釘住了**——⑤ 原本寫 `expect(input.readOnly).toBe(false)`。
- **群集 B（P2，codex＋grok 各自命中）**：`page.tsx` 註解宣稱由 `SEARCH_DISCLOSURE_FIELDS`
  選欄而 JSX 硬編七段（本 epic **第八次**「宣稱大於實作」）。
- **群集 C（P2）**：前端**其實能** import 契約 JSON ⇒ 我 brief 猜錯；但**實作不改**
  （改了會讓 `7.2-M1` 變 false negative），只更正理由陳述。
- **群集 D（P2）**：裁定 A 宣稱的使用者路徑 `/data-preparation` 沒有機械閘。
- **群集 E（P2）**：註解檔名錯。

**R4 閉合輪（原提出方重跑自己的反例）**：R3 八條**全數 CLOSED**
（codex 逐條複驗，`R3-M1..M4` 紅集合 2／3／4／2），composer 與 grok **零 finding**。
codex 新增 **`CODEX-R4-P2-01`（P2）並已修**：`clampDecisionOffset` 之 `Math.trunc`
讓 `1.9` **靜默變成 1**，而契約是 `int`、後端已 `Number.isInteger` 顯式拒絕
⇒ 前端先截掉，使用者永遠看不到那條拒絕。**這是 R3 修法自己引入的相鄰缺陷**（同型第六次）。
修法：clamp 只夾範圍、加 `step={1}`、送出前顯式阻擋、探針兩條、mutation `R4-M1`。

🔴 **我在 R4 brief 具名請委員代打的那格，codex 回答了**：單拆 `readOnly` 而留 clamp
**不會紅** ⇒ `R3-M1` 之「兩層一起拆」成立。那原本是我對自己 mutation 設計的宣稱、我沒自己驗。

## 本批之三個主委裁定（三家已審）

1. **裁定 A**（`k` 鎖 0 與 7.2 ③ 互斥 ⇒ ③ 落函式層＋`/data-preparation`）：
   **實作被判 under-block**（群集 A），裁定本身未被推翻，已補兩層 fail-closed。
2. **裁定 B**（混批 `control_kind` 回 `null` ＋ `batch_fact_notes`）：三家**不升格 finding**。
3. **裁定 C**（保留全批 macro／micro 表）：三家**不升格 finding**——composer 明載
   SPEC 原文無「必須移除舊表」之逐字要求。

## 本批自己抓到的三個問題（皆非產品碼）

- 🔴 **`7.2-M1` 錄到空紅集合**：我把真契約注入生產元件 ⇒ UI 與期望值**兩側同源**。
- **`tsc` 抓到我測試檔的重複鍵**（`npm run build` **不涵蓋測試檔**，§3 第 8 條）。
- **新文案撞既有斷言**（4.1c 禁「重新匯出」四字）：**沒有放寬既有守衛**，改自己措辭。
- 🔴 **`7.3-M1` 之字面錨點被群集 B 的修訂改掉，runner 當場 fail-loud**（非靜默跳過）
  ——B8 付過代價換來的設計正確生效；重新對錨後紅集合逐字相同。

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

- [x] ~~R3 三家 code review ＋ reconcile ＋ R4 閉合輪~~ ✅ **已收斂**
      （`handoffs/reconcile/20260828-gap3ux-b10-review-r{3,4}/synth.md`；兩輪 attribution／
      completeness 皆 rc=0、債皆已清）
- [ ] 🔴 **UAT 進行中，已抓到兩件事，收案條件因此改變**（見 `docs/IC_QUANT_GAP_REGISTRY.md`
      之 **`G3-D1`／`G3-D2`**；使用者照 `白話說明/GAP-3驗收清單.md` 走到 B5）
  - **`G3-D1`（缺陷，方向已裁）**：匯出前篩選只有一組條件、同時套用正反例
    ⇒ 條件引用 `future_*` 時兩類同時被結果截斷、反例不再是對照組，畫面無提示。
    修法：①正反例各自獨立條件 ②篩選不再兼差推導深度、改直接問使用者
    「哪個 timeframe 的第幾根」 ③purge ＝ 正反例深度取大者。
    **動 SPEC Task 2.1／2.1b／1.9 ⇒ 須走延伸檔 `D-006`；排程未定**
    （使用者尚未在「擋在收案前／另開票＋先止血／只止血」之間裁定）。
  - **`G3-D2`（交付未完成）**：五維度中三類值永久灰著**不算交付**——使用者裁定要真的做出來。
    ⇒ **UAT B3 在三者完成前一律記未完成**，畫面正確地灰掉不算過。
  - 🔴 **已修並 push 之 UAT 缺陷**：兩階段搜尋之 `/two-stage/combined/{a}/{b}` 漏附
    `source_file_digest`（Task 1.3 只掛在 `/search/task/{id}/result` 一條上）
    ⇒ 使用者按匯出必然被前端 fail-closed 擋下。已補**機械閘**（AST 枚舉所有回傳
    `SearchResponse` 之 GET route）；該閘第一版是子字串比對＝廉價綠燈，實測不紅，已改。
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

- 🔴 **動到 `scripts/` 的 commit 要帶 `Governance-Scope: out-of-epic <理由>` trailer**
  （與 `Co-Authored-By:` **同一段**，見 `govb1_final_gate.sh:347,420`）。
  **本批三個 `scripts/` 改動都沒帶** ⇒ 進了 G-7 的淨差清單。已 push 之 commit
  前向補不了（要改歷史），下批**在寫 commit message 當下就加**。
  🔴 **誠實邊界**：G-7 現列 18 個路徑，其中 **5 個是本批的**
  （`agent_postflight.sh`／`clean_agent_tmp.sh`／`mutation_worktree.py` 三個真的 out-of-epic、
  以及兩個 GAP-3 測試檔——後者屬 epic 內但不在 `govb1_scope.manifest`）。
  其餘 13 個是更早期累積（GAP-2 時代檔案）。**不要把本批這 5 個也算進 `R-GOV7-1` 的既有帳**。
- 🔴 **`.nbi` 是被版控的**：跑完測試 `git status` 會多出 22 個 numba 快取改動。
  commit 前先 `git checkout --` 還原，否則會把快取雜訊混進 commit。
- 🔴 **前端測試不得把真契約注入生產元件**：那會讓「契約漂移」類的機械閘永遠不紅（本批實證）。
- 🔴 **收案前固定跑 `npx tsc --noEmit`**：`npm run build` 不涵蓋測試檔，本批靠它抓到真缺陷。
- `pytest tests/api` **會改寫** `data_cache/features/registry.json`；各 Task 用 `-k` 選擇器。
- `git commit -F` 每次走權限分類器約 13 秒；`npm run build`／mutation runner 被哨兵報 A 類卡頓是**誤報**。
