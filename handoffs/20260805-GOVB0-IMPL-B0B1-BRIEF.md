# 第 0 批實作 — B0 ＋ B1

brief-kind: impl

**唯一權威來源**：`docs/GOVB0_FRICTION_TODO.md`（**Internal Frozen**，`TODO-STATUS: INTERNAL-FROZEN`）
**背景規格**：`docs/GOVB0_FRICTION_SPEC.md`（R7，七輪收斂，三家戳記）

## §0 前提宣告

**已查證**：

- fact-verified: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0。
- fact-verified: TODO 已凍結 → `grep -c '^TODO-STATUS: INTERNAL-FROZEN' docs/GOVB0_FRICTION_TODO.md` → `1`。
- fact-verified: 現有治理測試基線 → `VERIFY:govb0-test-baseline`
  （主委實跑 `python3 -m pytest tests/governance -q` → **`701 passed in 230.48s`**，2026-08-05）。
  🔴 **出生事故**：本行初版直接抄 TODO §0.4 的數字**未實跑**，被 claim checker 擋下才去驗。
  數字碰巧正確，但**過程是錯的**——同型「寫下引用未確認」本日第 5 次，正是 `票 B-16` 擴充要擋的。
- fact-verified: `data_cache/` 有 **1 個 `.h5` 實檔、0 個 tracked** ⇒ **絕對不可刪、不可 commit**。

**假設**（你若發現不成立，**停下來回報，不要硬做**）：

- assumed: `scripts/gate_check.sh` 的 `_append_gate_deny_audit()` 位於 `:21-30`、判定段位於 `:86`，
  且 `:117`／`:128` 是其僅有的兩個 caller。**動工前請自行 `grep -n` 複驗**。
- assumed: `scripts/audit_events.json` 具備 `required_fields_per_event`／`event_object_allowed_keys`／
  `unknown_event_policy` 三個 key。**動工前請自行 `jq` 複驗**。

## 本批範圍：**只做 B0 與 B1，其餘一律不碰**

### B0 — 凍結 pre-Phase2 snapshot（**純步驟，無 Task**）

TODO §B 的 B0 列。**必須在任何 Phase 2 工作之前完成並 commit。**

產出兩個檔（**同一次 commit**）：
```
tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot          # 現行 gate_check.sh 的逐位元組副本
tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot.sha256   # 上檔的 sha256 單行
```

🔴 **為何獨立成 B0**：若等到 B5 才複製，`gate_check.sh` 已被 B3／B4 改過 ⇒
Task 2.5 差集報表的「舊版」會含新修法 ⇒ **merge gate 失去 oracle**（`CODEX-TODO-P0-03`）。

**B0 驗收**：`git ls-files --error-unmatch <兩檔>` rc=0；
且 `sha256sum` 實算值 == sidecar 內容（**兩者都要貼實跑輸出**）。

### B1 — Task 0.1：`gate_deny` 記錄被擋指令與命中規則

**完整規格見 TODO 的「Phase 0 / Task 0.1」段，逐條照做。** 重點提醒：

1. **先判定、後記錄**——`grep -Eo` 取片段**絕不可放進判定前主路徑**，
   其結果**不得回饋進判定**（`grep` 失敗或效能變化會改 rc）。
2. **enum 與 required_fields 寫進 `scripts/audit_events.json`**，`gate_check.sh` **只引用不自列**。
   TODO 已逐 key 列出待新增項，**不必猜**。
3. **不變式**：對**語料 A**，改前／改後的 `(rc, kind)` 序列逐項相等。
   🔴 **不是要求 audit JSON diff 為空**——本 Task 的目的就是新增欄位，audit 必然不同。
4. **兩份語料檔各自獨立**：語料 A（`gate_invariance_corpus.txt`，本批建）
   與語料 B（`gate_decision_corpus.txt`，Phase 2 才建）**sha256 必須不同**，各自入版控。

**B1 驗收**：TODO 列的 `TEST-0.1-*` 全部落為 `pytest tests/governance/test_gate_deny_fields.py` 斷言，
包含 `TEST-0.1-MUT`（移除欄位寫入 → `TEST-0.1-FIELDS` 轉紅，**須貼實跑 rc**）。

## 🔴 硬性禁令（違反即整批退回）

1. **禁碰 `data_cache/`**（有不可復原的真實 kline，**絕不 commit、絕不造假、絕不刪**）。
2. **禁 `git checkout`／`git restore` 任何 tracked 檔**；**禁 `git clean`**；不要 commit、不要 push。
3. **禁修改既有測試斷言**；**禁恆真斷言**；**禁改檢查器或加排除清單換綠燈**。
4. **既有測試基線為下限**（`VERIFY:govb0-test-baseline`；**真跑** `pytest tests/governance` →
   `701 passed`，receipt 的 `runtime_class` 為 `mutation_runtime`），
   完工後總數只增不減；任何既有測試轉紅**須具名說明並停下回報**。
5. **不做 B2 以後的任何 Task**（`1.1`／`2.*`／`3.*` 一律不碰）。範圍外的改動一律退回。
6. **bash 3.2 相容**：禁 `declare -A`、禁 `flock`；**`rc` 一律直接取，禁經 pipe**
   （`cmd | tail; echo rc=$?` 讀到的是 `tail` 的 rc）。
7. **hot path 不新增 log**（`gate_check.sh:86` 判定段為 hot path）。
8. 讀 audit／log 一律 `LC_ALL=C grep -a`，**禁 `export LC_ALL`**（會洩漏進 pre-push 弄紅治理測試）。

## 收尾必做

1. `pytest tests/governance -q`（**丟背景，輸出導檔再取尾**，全套約 110 秒）——貼總數與 rc。
2. `bash scripts/restore_golden_inventory.sh` 之後，
   **貼 `git status --short tests/golden/` 的輸出（須為空）**——**不得以該腳本 rc 為證**。
3. 每個 mutation **貼實跑 rc**。
4. 清 /tmp workdir（**保留 `/private/tmp/claude-501`**）。

## 產出

改了哪些檔（貼 `git diff --stat`）、B0 兩檔的 `sha256sum` 實跑輸出、
`TEST-0.1-*` 各條的實跑結果、mutation 的實跑 rc、
`pytest tests/governance -q` 總數、`git status --short tests/golden/` 輸出。

🔴 **任何一步做不到或發現 TODO 有誤，停下來回報，不要自行改 TODO**
（它是 Internal Frozen，修訂須走 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` 的延伸檔程序）。
