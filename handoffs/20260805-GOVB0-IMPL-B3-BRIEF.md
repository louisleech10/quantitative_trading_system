
# 第 0 批實作 — B3（Task 2.0 詞法契約 ＋ Task 2.1 引號感知）

brief-kind: impl

**唯一權威來源**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）Phase 2 / Task 2.0 ＋ Task 2.1
**前置**：B0／B1／B2 皆已完成並經雙家族 review 通過；驗收 oracle 已補完（commit `e243776`）。

## 🔴 本批風險等級：**全批最高**

B3 是 **Phase 2 第一批**，開始**真的改變判定結果**（前三批皆為「判定行為不變」）。
`scripts/gate_check.sh` 是**每次派工都會走到**的共用控制流，改壞會擋住所有後續工作。

⇒ **任何一步不確定，停下來回報，不要猜。**

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: B0 snapshot 已改為目錄 bundle 並含 4 檔各自 `.sha256`；
  bundle 內 `gate_check.sh` 的 sha256 **==** `git show $(git rev-parse '596fcb4^'):scripts/gate_check.sh`
  **== `871258c9…01606a`**（主委獨立計算，非採信）。
- fact-verified: 覆蓋斷言 `test_01_corpus_a_covers_decision_branches` 自 `gate_check.sh`
  **機械導出**分支清單（讀碼確認），且含反向檢查（語料標了不存在的分支名亦轉紅）。

**假設**（你若發現不成立，**停下來回報，不要硬做**）：

- assumed: 語料 A 現有 13 分支對照表在你動 `gate_check.sh:86` 後**仍然成立**。
  🔴 **你改判定會新增／改變分支** ⇒ 對照表與覆蓋斷言**必須同步更新**，否則覆蓋宣稱失真。
- assumed: 原型③ `handoffs/govb0_probes/b15probe5.sh` 的 26 條語料仍可跑。動工前自行實跑確認。
- assumed: `gate_check.sh` 主判定段仍在 `:86` 附近。**行號可能已因 B1 改動而漂**，
  **務必自行 `grep -n` 複驗，不得照抄行號**。

---

## 範圍：只做 Task 2.0 ＋ Task 2.1

### Task 2.0 — 詞法契約（先定義，後實作）

**完整規格見 TODO 的「Phase 2 / Task 2.0」段，逐條照做。** 重點：

1. **契約 11 項**（`1`／`1b`／`2`–`10`）逐項實作，每項 ≥1 TP ＋ ≥1 TN，**共 ≥22 條**，全進**語料 B**。
2. **產出語料 B ＋ 其 `.sha256` sidecar**（`tests/governance/fixtures/gate_decision_corpus.txt`
   與 `.txt.sha256`）——**producer 是本 Task，且須與語料同一次 commit**。
   🔴 B2 階段的**占位檔**須被本 Task 的真實語料取代。
3. **參考實作＝原型③**（`b15probe5.sh`，26/26）。
   🔴 它**只涵蓋契約第 2、3 項**；第 **4、5、7、8、9、10** 項**尚未在原型中實作**，
   **禁止照抄原型即宣稱完成**。
4. **契約 1b（剝引號）必須跨行有狀態**：用 `awk` 狀態機，
   **禁 `sed 's/"[^"]*"//g'` 行內替換**、**禁正規化為單行**。參考 `b15probe6.sh`（4/4）。
5. **heredoc（契約第 10 項）七條機械規則**逐條落地——
   🔴 **⑥的 delimiter 文法是「允許清單」`([A-Za-z0-9_.:+=,%@^~{}\[\]!*?-]+)` ＋ 完整 token 邊界**，
   **不是排除清單**。⑦「無法依⑥解析 ⇒ 整個掃描 fail-closed」。
   **⑥⑦互補且不重疊，不得有「⑥接受但⑦說要拒絕」的重疊區。**

### Task 2.1 — 引號感知 ＋ `-c` 遞迴

**完整規格見 TODO。** 重點：

1. 依 Task 2.0 契約實作剝引號前處理，**純 shell／`sed`／`awk`，禁 subprocess 呼叫 python**（熱路徑）。
2. `(bash|sh|zsh) -c` 與 `eval` 的引號引數**遞迴掃描**，上限 3 層，逾限 fail-closed。
3. 命令位置定義含 `^ ; & | ( \` $( && || eval後 xargs後`。

---

## 🔴 本批的驗收核心：判定**會**改變，所以要證明「只改了該改的」

前三批的保證是「判定完全不變」。**本批不同**——判定會改。所以：

1. **語料 A（invariance）必須仍然全綠**
   （動工前基線 `VERIFY:b3-baseline-invariance`，**真跑** `pytest tests/governance/test_gate_deny_fields.py`
   → `22 passed`，主委實測 2026-08-05）：
   語料 A 驗的是 Phase 0 的不變式。B3 改判定後，**語料 A 中原本 ALLOW/BLOCK 的條目若翻轉，
   代表你改到了不該改的東西** ⇒ **BLOCKING，停下回報**。
   🔴 **不得為了讓語料 A 變綠而修改語料 A**。
2. **語料 B（decision）記錄「應該改變」的判定**：TODO 列舉的每一條轉向都須有對應條目。
3. **分支對照表與覆蓋斷言同步更新**（見 §0 assumed 第 1 條）。

## 🔴 硬性禁令

1. **禁碰 `data_cache/`**。
2. **禁 `git checkout`／`git restore`／`git clean`**；不要 commit、不要 push。
3. **禁修改既有測試斷言**；**禁恆真斷言**；**禁改檢查器或加排除清單換綠燈**。
4. **禁修改語料 A** 使其變綠（見上）。
5. **測試基線只增不減**——主委親跑的最近基線＝`VERIFY:b3-baseline-invariance`
   （**真跑** `pytest tests/governance/test_gate_deny_fields.py` → `22 passed`，即 Phase 0 那一檔）。
   全套數字前一輪實作者回報 734，**主委未親跑，不以其為斷言基礎**；
   🔴 **本輪全套基線由你實跑後回報**，且完工後只增不減。
6. **不做 B4 以後的任何 Task**（`2.2`／`2.3`／`2.4`／`2.5`／`3.*` 一律不碰）。
7. **bash 3.2 相容**；**`rc` 一律直接取，禁經 pipe**；**hot path 不新增 log**。
8. 讀 audit／log 一律 `LC_ALL=C grep -a`，**禁 `export LC_ALL`**；
   中文路徑比對必須 `git -c core.quotepath=false`。

## 收尾必做

1. `pytest tests/governance -q`（**丟背景導檔再取尾**）——貼總數與 rc。
2. `bash scripts/restore_golden_inventory.sh` 後貼 `git status --short tests/golden/`（須為空）
   ——**不得以該腳本 rc 為證**。
3. 每個 mutation **貼實跑 rc**（契約 11 項各一個）。
4. 清 /tmp workdir（**保留 `/private/tmp/claude-501`**）。

## 產出

1. **契約 11 項 → 語料 B 條目**對照表（每項 TP／TN 各至少一條）
2. 語料 B 與其 `.sha256` sidecar；**與 B2 占位檔的差異說明**
3. 原型③ 26 條語料的實跑結果（新實作與原型逐條比對，差異須具名）
4. **語料 A 仍全綠的證明**——動工前基線 `VERIFY:b3-baseline-invariance`
   （**真跑** `pytest tests/governance/test_gate_deny_fields.py` → `22 passed`）；
   請貼你完工後同一命令的實跑輸出，須仍全數通過
5. 更新後的分支對照表與覆蓋斷言
6. 11 個 mutation 的實跑 rc
7. `git diff --stat`、`pytest` 總數、`git status --short tests/golden/`

🔴 **任何一步做不到或發現 TODO 有誤，停下來回報，不要自行改 TODO**（Internal Frozen，
修訂須走 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` 的延伸檔程序）。
