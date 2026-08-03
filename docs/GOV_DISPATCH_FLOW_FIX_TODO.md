# 派工控制流缺陷修補 TODO

**版本** v4（R1 十七項 → 戳記輪 STAMP2–5 → **R2 十二項**）　|　**基於 SPEC** `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md`（**rev6**，480 行）　|　**日期** 2026-08-03

**授權鏈**：`handoffs/reconcile/20260803-govflow-fix-r5/synth.md`（三家 APPROVED，`reconcile_stamps_check` **rc=0**，
body sha256 `cd533bb8…`）——其 Verdict 預先授權「若 R6 三家一致無 P0，即直接生成 TODO」；
R6 實際結果為**三家一致無 P0**（codex「TODO：GO」／grok 0 findings／composer 可進 TODO），
收斂紀錄見 `handoffs/reconcile/20260803-govflow-fix-r6/synth.md`（**該檔因 grok 未產 sentinel 而無法戳記，已具名揭露**）。

**對抗審**：R1 29 → R2 13 → R3 14 → R4 8 → R5 8 → **R6 6（零 BLOCKING）**。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 硬性禁止（違反即退回，不接受「已修」自述）

1. 🔴 **禁止以放寬判準換綠燈**。本 TODO 四項全是「修誤報」，最大風險是順手放過真陽性。
   每項修補**必須**附「原本能擋的仍然擋得住」的迴歸測試 ＋ mutation。
   〔SPEC §C；R2–R5 連續四輪在此被攻破，四次修法全是**刪或收窄**，無一次靠加機制成功〕
2. 🔴 **禁止修改既有 `tests/governance/` 斷言換綠燈**。既有測試因本次改動轉紅時，
   須逐條說明「該斷言原本鎖的是舊契約」並由委員裁定；`test_registry_v2_shape.py` 的二值 assert
   更新須**明標契約擴張**，不得默默刪 assert。
3. 🔴 **禁止 `GOVERNANCE_TEST_HARNESS=1` 時跳過格式檢查**（那是弱化 production 路徑）。
4. 🔴 **探針一律用隔離副本**，禁直接變異 repo 內 `scripts/*.sh` 或 `tests/**`。
5. 🔴 **禁止手寫數量。數字與表格不一致 ⇒ 視為 TODO 未完成，不得派工。**
   凡「N 列／N passed／N 個 caller」一律以機械計數產生，並在自檢時逐處對照。
   〔主委已**六次**手寫數量出錯：consumer 閉包 12/13/15、戳記檔數 2/31/0、§M 列數、
   SPEC 行為表 13 vs 17、finding ID 引用錯位、**本 TODO v1 的 Phase 2「6 passed」vs 表 7 列**
   ——**最後一次是在寫下本條規則的同一份文件裡犯的**，證明「寫規則」不等於「遵守規則」，
   故本條升級為可驗收的擋門條件而非勸告〕
   🔴 **本條與 SPEC rev6 硬寫數字的衝突處置（R2 定案，`CODEX-R2-P1-03`）**：
   SPEC rev6 在驗證欄寫死 `19/6/8/6/5 passed`，與本條「機械計數」互斥。
   **本 TODO 的機械計數為準**（`--collect-only -q | wc -l` 對照該 Phase 測試表機械展開列數）。
   主委實跑對照如下——**SPEC 的數字有三個 Phase 已過時，照它當 gate 會漏測**：

   | Phase | TODO 表機械展開 | SPEC rev6 寫 | 判定 |
   |---|---|---|---|
   | 1 | **22**（`T1-U1..U18` 展開 18 ＋ M1／B1／B2／R1 共 4） | 19 | ✗ 照 SPEC 漏 3 |
   | 2 | **9** | 6 | ✗ 照 SPEC 漏 3 |
   | 3 | **9**（拆 `T3-U4`／`T3-U5` 後 9 列 ⇒ 9 case） | 8 | ✗ 照 SPEC 漏 1 |
   | 4 | **11** | 6 ＋ 5 ＝ 11 | ✓ 一致 |

   🔴 **SPEC rev6 已凍結，不就地改**——依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md`
   走延伸檔。本 TODO **不阻塞於此**：實作端一律以上表機械數為準，
   並在各 Phase Gate 報告內附 `--collect-only` 實跑輸出供核。
   具名票：**`GOV-SPEC-REV6-STALE-COUNTS`**（見 §N）。
6. **不碰** `momentum/`／`api/`／`frontend/`。允許改動範圍：`scripts/`、`tests/governance/`，
   **以及 Task 2.2 明列的 `docs/P16_COMMITTEE_DEBT_SPEC.md` 及其 D 延伸檔（僅該 Task）**。
   〔v1 寫「僅動 scripts/ + tests/governance/」與 Task 2.2 **互斥**，B2 無法同時合規〕
7. **rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc）。
8. **改檔一律用 Edit 工具**，不得用 Bash 包字串取代。
9. 🔴 **所有點名的函式須實跑 `grep -n 'def <name>'`／`grep -n '<name>()'` 確認存在**後才寫進 TODO。
   〔v1 的 Task 4.2 點名 `check_file`，實際只有 `check_files`／`check_unit`，執行端會搜錯符號〕
10. 🔴 **新增任何 fail-closed 守衛時，必須當場對現行文件實跑一次該守衛**，
    確認**現狀本身通過**才可寫進 TODO。〔`CODEX-R2-P0-01`／`COMPOSER-R2-P1-01`／`GROK-R2-P0-01`
    三家同時命中：STAMP4 加入邊界④ 時，`PHASE_MAP` 自己就有一項違反它，
    B0 生成器照 TODO 實作**會在初始契約上拒絕自己**〕

### 引用 SPEC §A 的 manifest（不整段複製）

`[A-1]` heading 誤報 rc=1／`[A-2]` 重派被拒（`result_state=success`）／`[A-3]` 角色檢查在派工當下才驗／
`[A-4]` 收斂檔 8 處 claim 被擋（7 處在逐字附錄）。四者皆為**實戰事故**，非推測。

### 防假綠

- 新增測試須自證：**revert 修法 → 轉紅**（實跑貼 rc）。
- **不得**以「N passed」當充分證明；須先跑 production-path integration，再跑 full governance suite。
- 每個 mutation 須明定：**改哪一行／隔離副本、預期哪個 pytest node 由 pass 轉 fail、rc 與關鍵 stdout**。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B0** | Task 0.1 | 無 | manifest 生成器是後續所有回歸的驗收基礎，須最先落地 | 小 |
| **B1** | Task 1.1 | B0 | 單一函式、契約為 18 列行為表，可獨立驗收 | 中 |
| **B2** | Task 2.1 ＋ Task 2.2 | B1（**語意耦合**） | 兩者共用 `result_state` 契約與同一組 registry/consumer；拆開會反覆改同一批檔 | 大 |
| **B3** | Task 3.1 | **B2（序列，不可並行）** | 🔴 **Task 2.1 與 Task 3.1 皆修改 `scripts/cx_run.sh`**（實跑 `grep -c '_emit_family_result\|governance_roles' scripts/cx_run.sh` → **5**）；並行會合併衝突或互相覆蓋 | 中 |
| **B4** | Task 4.1 ＋ Task 4.2 | 無（**可與 B1–B3 並行**；須獨立 commit ＋ 隔離 clone 驗證） | 只動 `verification_claim_check.py`，與 `cx_run.sh` **無交集**；改 pre-commit 風險最高，單獨成批 | 大 |

🔴 **執行序**：`B0 → B1 → B2 → B3`（前四者共用 `cx_run.sh`／`completeness_check.sh` 的語意鏈）；
**B4 可全程並行**。〔`GROK-R1-P0-01` [BLOCKING]：v1 誤標 B3 可與 B2 並行〕

**批次間 Gate**：見各 Phase 末的 Phase Gate（引用 Test ID ＋ 可執行命令）。

### B0 派工 prompt（可直接複製）

> 前置：無。
> Task：0.1（manifest 生成器）。
> 驗證：🔴 **Phase 0 Gate 全部 oracle 缺一不可**〔`GROK-R2-P1-02`：本 prompt 原只點名
> T0-N1／T0-N2，執行端照 prompt 驗收會**整批漏做** STAMP3／4 新增的 D 類／錨點／反向／
> `phase_base` oracle〕：
> **可證偽 oracle**：`T0-N1`（B-only 探針，禁用 `doc_format_precheck.sh`）、`T0-N2`、
> `T0-N3`、`T0-N4`、`T0-N5`、`T0-N6`、`T0-B2` **全綠**；
> **其餘**：`T0-U1`／`T0-B1`／`T0-C1`／`T0-C2`／`T0-C3` 全綠。
> 另須交付 `--record-base <N>` 子命令（見 Task 0.1 實作要點 4）。
> **禁用「A 數＋B 數＋C 數」加總**（`doc_format_precheck.sh` 已在 A 聯集內，加總必重複計數）；
> 集合比對用 `comm -3`，但**不得單獨作為 Gate**（與生成器同源）。
> B／C／D 類任一 path 不在 `PHASE_MAP` 或缺 nodeid ⇒ rc!=0。

### B1 派工 prompt

> 前置：B0 已合併。
> Task：1.1（`extract_heading_ids` 判準）。
> 驗證：`venv/bin/python -m pytest tests/governance/test_completeness_idlike_fp.py -q` rc==0，
> 且 collected 數 **== Phase 1 測試表機械展開列數**（`T1-U1..U18` 為 18 個參數化 case，
> 另加 `T1-M1`／`T1-B1`／`T1-B2`／`T1-R1`）。**禁在此寫死數字**，以
> `pytest --collect-only -q tests/governance/test_completeness_idlike_fp.py | wc -l` 對照。

### B2 派工 prompt

> 前置：B1 已合併。
> Task：2.1（emit 順序 ＋ `format-failed`）、2.2（P16 凍結契約同步）。
> 🔴 **Task 2.2 預設走 R**；走 D 須使用者明示裁定並落 SPEC §A。
> 驗證：`pytest tests/governance/test_result_state_format_failed.py -q` rc==0，
> collected 數 **== Phase 2 測試表列數**（以 `--collect-only -q | wc -l` 對照，**禁寫死數字**）；
> `pytest tests/governance/test_registry_v2_shape.py -q` 全綠（三值契約擴張須標註）。

### B3 派工 prompt

> 前置：**B2 已合併**（🔴 序列，不可與 B2 並行——兩者皆改 `scripts/cx_run.sh`，見 §B）。
> Task：3.1（角色 preflight 前移 ＋ 共用 `_role_gate.sh`）。
> 驗證：`pytest tests/governance/test_rolegate_predispatch.py -q` rc==0，
> collected 數 **== Phase 3 測試表列數**（`--collect-only -q | wc -l` 對照，**禁寫死數字**）。

### B4 派工 prompt

> 前置：無。🔴 **須先在隔離 clone 確認 commit 仍可進行**。
> Task：4.1（`sources/` 副本豁免）、4.2（`synth.md` unit 級附錄豁免）。
> 驗證：`pytest tests/governance/test_claimcheck_verbatim_exempt.py -q` rc==0，
> collected 數 **== Phase 4 測試表列數**（`--collect-only -q | wc -l` 對照，**禁寫死數字**）。

---

## Phase 0 — 驗收基礎設施（目標：讓後續回歸有機械可比對的攻擊面清單）

**完成後系統狀態**：repo 內有可執行的 manifest 生成器，`§M` 表格降為人類可讀快照。

### Task 0.1 — manifest 生成器

- **SPEC ref**：§M　**目標**：把攻擊面矩陣從手寫改為腳本生成，並可 CI 驗收。
- **輸入 / 輸出**：輸入＝repo 樹；輸出＝**四欄** manifest `path|phases|nodeid|status`
  〔`CODEX-R1` 指出三欄無法表達**跨 Phase caller**，且未定義缺檔 C 項的 nodeid〕：
  - `phases`：**逗號分隔多值**（同一檔被多 Phase 觸及時全列，如 `1,2`）
  - `nodeid`：對應 pytest node；**非測試檔或尚未存在者寫 `-`**
  - `status ∈ {present, MISSING}`：C 類元件尚未建立時為 `MISSING`（**仍須列出**）
- **實作要點（≥3，含偽碼）**：
  1. 三類聯集：
     ```
     A = grep -rlE 'completeness_check|result_state|committee_process_exempt|STAMP-MODE' scripts tests/governance
     B = 產出端 hook 固定表 { doc_format_precheck.sh, brief_conformance_check.sh,
                              verdict_filled_check.sh, gov_check.sh }
     C = 本 epic 新增元件 { gen_govflow_manifest.sh, _role_gate.sh,
                            test_govflow_manifest.py, test_completeness_idlike_fp.py,
                            test_result_state_format_failed.py, test_rolegate_predispatch.py,
                            test_claimcheck_verbatim_exempt.py }
     D = 【機械抽取，不得手寫】本 TODO 各 Task 自「修改檔案」bullet 起、至下一個「不可做」
         bullet 止，該區間內明列的所有 repo path——涵蓋三種：①修改檔案本身
         ②其「既有 caller/consumer」續行 ③該區間內明列的預期轉紅既有測試檔。
         🔴 **三者都是本 epic 的攻擊面，一律須映射**（定義刻意寬於「只有修改檔案」，
         見下方 STAMP3 自查）。
         awk '/^- \*\*修改檔案\*\*/,/^- \*\*不可做\*\*/' docs/GOV_DISPATCH_FLOW_FIX_TODO.md \
           | grep -oE '(scripts|tests|docs)/[A-Za-z0-9_./-]+' | sed 's/[:.]$//' | sort -u
     manifest = sort -u (A ∪ B ∪ C ∪ D)
     ```
     🔴 **D 類存在的理由**〔來源＝**codex STAMP3 戳記 REJECTED 理由**〕：
     v2 的 B／C 為**手寫固定表**，漏了本 epic 實際會改的檔。codex 具名指出 2 個，
     主委機械重掃發現**共 4 個**漏列：`scripts/gen_govflow_manifest.sh`（Phase 0）、
     `scripts/audit_events.json`（Phase 2）、`docs/P16_COMMITTEE_DEBT_SPEC.md`（Phase 2）、
     `scripts/committee_run.sh`（Phase 3）——**再加一張手寫清單只會再漏一次**，
     故改為從「修改檔案」bullet 機械抽取。
     🔴 **STAMP3 自查追加**：主委實跑上列 `awk` 後，**又抓出 3 個委員未指出的漏列**——
     `scripts/git_hooks/pre-commit`（Phase 4 既有 caller）、`tests/governance/test_debt_emit.py`、
     `tests/governance/test_stamp_taskid_inject.py`（Phase 2 預期轉紅）。
     ⇒ **手寫清單共漏 7 個，委員只抓到 2 個**。這正是「D 類須機械抽取」的實證：
     人工盤點在本 epic 已連續失敗，不可再以「這次有仔細看」作為保證。
  2. 🔴 **`phases` 由生成器內建具名 `PHASE_MAP` 決定，不得由檔名猜測**
     〔來源＝**codex STAMP2 戳記 REJECTED 理由**（非 R1 canonical finding；R1 codex 只有
     `CODEX-R1-P1-01`～`-04`）：v2 只寫「每列補 phase」卻未定義 path→phases 規則，
     實作端無從下手；且與輸出欄位 `phases`（多值）用字不一致〕：
     ```
     🔴 **`phases` 的語意（R2 定死，先前混用兩義是 BLOCKING 根因）**
     〔來源＝`CODEX-R2-P0-01`／`COMPOSER-R2-P1-01`／`GROK-R2-P0-01` **三家獨立同時命中**〕：
     **`phases` ＝ 本 epic 於該 Phase「允許修改」的檔**（＝G-MANIFEST 的允許上界），
     **不是** SPEC §M 的「受影響 Phase」。兩者是不同軸：
     - 受影響但本 epic **不改** ⇒ `-`（旁觀者），仍列於 manifest，故 §M 的覆蓋不會遺失
     - 只有真的會被改的檔才給數字 ⇒ 與邊界④ `{p : phases != '-'} ⊆ (B∪C∪D)` 自洽

     PHASE_MAP（path → phases，逗號分隔多值；`-` ＝旁觀者）
       scripts/gen_govflow_manifest.sh                      → 0      # ← STAMP3 補
       scripts/completeness_check.sh                        → 1
       scripts/cx_run.sh                                    → 2,3   # Task 2.1 與 3.1 皆改此檔
       scripts/audit_events.json                            → 2      # ← STAMP3 補（Task 2.1）
       docs/P16_COMMITTEE_DEBT_SPEC.md                      → 2      # ← STAMP3 補（Task 2.2）
       scripts/committee_run.sh                             → 3      # ← STAMP3 補（Task 3.1）
       scripts/gate.sh                                      → -      # 🔴 R2 修正：旁觀者
       scripts/_role_gate.sh                                → 3
       scripts/verification_claim_check.py                  → 4
       scripts/doc_format_precheck.sh                       → 2      # B 類產出端 hook：
       scripts/brief_conformance_check.sh                   → 2      # 消費 result_state／格式判定
       scripts/verdict_filled_check.sh                      → 2
       scripts/gov_check.sh                                 → 2
       tests/governance/test_govflow_manifest.py            → 0      # ← STAMP3 補
       tests/governance/test_completeness_idlike_fp.py      → 1
       tests/governance/test_result_state_format_failed.py  → 2
       tests/governance/test_registry_v2_shape.py           → 2
       tests/governance/test_rolegate_predispatch.py        → 3
       tests/governance/test_claimcheck_verbatim_exempt.py  → 4
       tests/governance/test_debt_emit.py                   → 2      # ← STAMP3 自查補（預期轉紅）
       tests/governance/test_stamp_taskid_inject.py         → 2      # ← STAMP3 自查補（預期轉紅）
       scripts/git_hooks/pre-commit                         → 4      # ← STAMP3 自查補（既有 caller）
     ```
     🔴 **`0` ＝ Phase 0，`-` ＝旁觀者，兩者不可混用**——v2 誤把旁觀者也寫成 `0`，
     與 Phase 0 撞號（主委自查發現，非委員指出）。
  3. **fail-closed 的界線（兩種路徑，勿混為一談）**：
     - **B／C／D 類**任一 path 不在 `PHASE_MAP`，或應有 nodeid 而缺 ⇒ **非零離開**
       （這些是本 epic 自己的元件與明列修改檔，未映射即為 TODO 漏寫）
     - **A 類**命中但不在 `PHASE_MAP` ⇒ 標 `phases=-`（**旁觀者**：只消費、本 epic 不改它），
       **仍須列出**，不得靜默丟棄。🔴 A 類不可套用非零離開——A 是廣域 grep，
       必然命中大量不屬本 epic 的檔，一律 fail 會使 B0 永遠無法通過。
     🔴 **D 類把「旁觀者」的假綠口收窄**：v2 只有 A／B／C 時，本 epic 明列要改卻不在 B／C 的檔
     （如 `audit_events.json`）會落進 A 類被標旁觀者——**看起來有列、實際分類錯**，
     且 G-MANIFEST 會在 Phase 2 誤判 scope 外洩。D 類納入 fail-closed 後此路封閉。
  4. 🔴 **另須實作 `--record-base <N>` 子命令**〔`COMPOSER-R2-P2-01`：STAMP4 只在 G-MANIFEST 與
     `T0-C3` 寫了此契約，**沒回頭補進本 Task 的實作要點**，實作者只讀 Task 0.1 會整個漏做，
     到 B1 才發現 Gate 缺基準〕：
     ```
     gen_govflow_manifest.sh --record-base <N>
       → append "<N>\t$(git rev-parse HEAD)\t<ISO8601>" 到 handoffs/govflow_phase_base.tsv
       → 同一 <N> 已存在 ⇒ 非零離開（append-only，防事後改寫基準點）
       → 無 <N> 引數或 <N> ∉ {0,1,2,3,4} ⇒ 非零離開
     ```
     不帶 `--record-base` 時為預設的 manifest 生成模式，兩者**不得互相影響輸出**。
  5. 🔴 **命令用 `grep -rlE` 不用 `rg`**——`rg` 不保證存在於所有執行端
     （grok 環境無、codex 環境有 `ripgrep 15.2.0`；**這是可攜性理由，不是「rg 不存在」**）。
- **修改檔案**：新建 `scripts/gen_govflow_manifest.sh`（無既有 caller）。
- **不可做**：不得把 `§M` 表格當成真相源；不得手寫任何列數。
- **邊界（≥2）**：① `C` 類元件尚未存在時 ⇒ 仍須列出並標 `MISSING`，**不得跳過**
  ② `grep` 命中 0 筆 ⇒ 非零離開（表示 pattern 寫錯，不是「沒有 consumer」）
  ③ 🔴 **錨點完整性**（STAMP4 新增）：`D` 類抽取前先驗
  `count('^### Task ') == count('^- \*\*修改檔案\*\*') == count('^- \*\*不可做\*\*')`，
  **三者不等 ⇒ 非零離開**。〔來源＝**codex STAMP4 實驗**：codex 在隔離副本刪掉 Task 4.1 的
  「不可做」錨點，`awk` 區間**跨入 Task 4.2**、多吃一個 path，而 `D ∖ PHASE_MAP` **仍為 0**
  ⇒ 守衛靜默放行。這不是蓄意繞過，是**某 Task 合理缺欄就會發生的意外失效**。〕
  ④ 🔴 **PHASE_MAP 反向收斂**（STAMP4 新增）：`{p : PHASE_MAP[p] != '-'} ⊆ (B ∪ C ∪ D)`，
  違反 ⇒ 非零離開。語意＝**不得把任意 A 類旁觀者檔直接映射進某 Phase 來擴大允許集合**；
  要擴大必須先把該 path 寫進某 Task 的「修改檔案」bullet（⇒ 是一次可見的 TODO 修訂）。
  🔴 **R2 事故**：本守衛加入時，`PHASE_MAP` 自己就有一項 `scripts/gate.sh → 3` 違反它
  （`gate.sh` 不在 `B∪C∪D`——Task 3.1 只在 `committee_run.sh` 的 `gate.sh dispatch` **之前**插入，
  並不改 `gate.sh`）⇒ **B0 生成器照 TODO 實作會在初始契約上拒絕自己**。
  三家獨立同時命中，均判為**意外失效非蓄意**。已改 `gate.sh → -`。
  **教訓**：新增 fail-closed 守衛時，**必須當場對現行文件跑一次該守衛**，
  不能只寫規則不驗自身——本 epic 已因此類「規則與自身狀態不一致」被擋四次。
- **風險緩解**：⊘（新建腳本，無既有行為）
- **存活至**：永久——後續每個 Phase 的回歸驗收都以本腳本輸出為攻擊面基準。
- **覆蓋風險**：無。後續 Phase 只**新增**元件到 C 類清單，不刪改本腳本輸出格式。
  🔴 **反向覆蓋風險（STAMP3 新增）**：本腳本輸出被 **G-MANIFEST** 用作 Phase 1–4 的 Gate ⇒
  本腳本若漏列，會使該 Phase Gate **誤判為 scope 外洩而卡住**（fail-closed 方向，不會假綠）。
- **驗證（`pytest` 見 Phase 0 測試表；rc 皆須 ==0）**：
  1. `bash scripts/gen_govflow_manifest.sh; echo rc=$?` → rc==0
  2. 🔴 **禁用「A 數 ＋ B 數 ＋ C 數」加總**〔來源＝**codex STAMP2 戳記 REJECTED 理由**〕。兩個獨立理由：
     ① `doc_format_precheck.sh` **已在 A 聯集內**（主委實跑
     `grep -rlE '<pattern>' scripts tests/governance | grep -c doc_format_precheck` → **1**）
     ⇒ 加總必重複計數，且「的去重數」無法從三個基數算出；
     ② 寫死「4」「5」違反本 TODO §0 第 5 條（禁寫死數字）。
     改**集合比對**：`comm -3 <(生成器輸出取第 1 欄 | sort -u) <(A∪B∪C∪D 獨立重算 | sort -u)` 須**輸出空**。
  3. 🔴 **集合比對與生成器同源，不能證偽 pattern 寫錯**——兩邊會一起錯、一起綠。
     可證偽的 oracle 是 **T0-N1／T0-N2 變異測試**與 **T0-B2**，Phase Gate 以它們為準。

### Phase 0 測試 ＋ Gate

**測試檔**：`tests/governance/test_govflow_manifest.py`（v1 未指定檔名，`COMPOSER` 指出）

| Test ID | 層級 | 內容 |
|---|---|---|
| T0-U1 | 單元 | 生成器 rc==0 且輸出非空 |
| T0-B1 | 邊界 | C 類缺檔時標 `MISSING` 而非跳過 |
| T0-B2 | 邊界 | pattern 命中 0 筆 ⇒ 非零離開 |
| **T0-N1** | 否定 | 🔴 **刪一個 B-only 項 ⇒ 列數少 1**。⚠️ **探針須用 `gov_check.sh`／`brief_conformance_check.sh`／`verdict_filled_check.sh` 三者之一**，**禁用 `doc_format_precheck.sh`**〔`CODEX-R2-P1-02`〕——它**同屬 A∩B**（主委實跑：A 命中 `doc_format_precheck`=1，其餘三項=0），從 B 刪掉聯集不變，基數斷言在它身上**必然失敗且與語意相反** |
| **T0-N2** | 否定 | 🔴 **於隔離副本新增一個含 `result_state` 的檔 ⇒ 列數多 1**（證明 A 類真的在掃 repo，非讀寫死清單；T0-N1 只涵蓋 B 類）。**禁直接變異 repo 內 `scripts/**`／`tests/**`**，須在 `.claude/tmp/` 下的複製樹跑 |
| **T0-C1** | 契約 | `scripts/cx_run.sh` 被 Phase 2 與 3 同時觸及 ⇒ `phases` 欄為 `2,3`，不得只記一個 |
| **T0-C2** | 契約 | A 類命中但不在 `PHASE_MAP` ⇒ 列出且 `phases=-`（**不是 `0`**，`0` 保留給 Phase 0）；**不是**非零離開 |
| **T0-N3** | 否定 | 🔴 **D 類 fail-closed**：於隔離副本在某 Task「修改檔案」欄插入一個不在 `PHASE_MAP` 的 path ⇒ **生成器非零離開**（證明 D 類真的被機械抽取並強制映射，防「手寫清單再漏一次」） |
| **T0-N4** | 否定 | 🔴 **D 類分類優先於 A**：把 `scripts/audit_events.json` 從 `PHASE_MAP` 拿掉 ⇒ 非零離開，**不得**降級為 `phases=-` 旁觀者 |
| **T0-N5** | 否定 | 🔴 **錨點完整性**（codex STAMP4 實驗直接重現）：於隔離副本刪掉任一 Task 的「不可做」bullet ⇒ **生成器非零離開**。⚠️ 現行守衛在此情境下 `D ∖ PHASE_MAP` **仍為 0 而靜默放行**——本測試就是要讓它紅 |
| **T0-N6** | 否定 | 🔴 **PHASE_MAP 反向收斂**：於隔離副本把一個純 A 類旁觀者檔（如 `scripts/audit_append.sh`）從 `-` 改映射成 `2` ⇒ **非零離開**（該 path 不在 B∪C∪D） |
| **T0-C3** | 契約 | **`handoffs/govflow_phase_base.tsv`**（🔴 全路徑，`GROK-R2-P1-01`：本列原寫短檔名 `phase_base.tsv`，與 G-MANIFEST 正文不一致，會讓測試與真實 Gate 各鎖各的路徑）缺 Phase N 的列 ⇒ G-MANIFEST（N）**FAIL**，不得跳過該 Gate。🔴 **精確 schema oracle**（`CODEX-B0R-P1-02` 修補）：三欄 TSV、40-hex HEAD、ISO8601Z timestamp；壞 timestamp／壞 SHA／欄數錯 ⇒ lookup FAIL；有效列 ⇒ 取得到 base。<br>🔴 **定位＝reference/schema unit oracle，非 production-path integration**（`CODEX-R3-P1-01`）：本測呼叫測試檔內自建的 `_gmanifest_base_lookup()`，**因為 B0 當下 repo 內尚不存在可被呼叫的 production G-MANIFEST consumer**（G-MANIFEST 是 Phase 1–4 的 Gate 條款，屬 B1–B4）。⚠️ **同源風險具名**：測試把 lookup 語意重寫在測試內，故**不能證偽真實 consumer 的行為**，只能證偽 schema。**整合測試見下方 B1 硬前置。** |
| **T0-C4** | 契約 | 🔴 **nodeid 欄契約**（`CODEX-B0R-P1-01` 修補）：至少一個 present `tests/**/*.py` 的 `nodeid` == path，且至少一個 MISSING C 項 `nodeid` == `-`。`nodeid_of()` 退化為全 `-` 時本測必須轉紅 |
| **T0-N7** | 否定 | 🔴 **D 類抽取全毀**（composer P2-01）：隔離副本破壞 `awk`/`grep` 抽取 pattern 使 `tmp_d` 為空 ⇒ **生成器非零離開**（與 T0-N5 錨點計數失衡正交） |

**Phase Gate**：🔴 **T0-N1／T0-N2／T0-N3／T0-N4／T0-N5／T0-N6／T0-N7／T0-B2 全綠**（可證偽 oracle，缺一不可）
＋ T0-U1／T0-B1／T0-C1／T0-C2／T0-C3／T0-C4 全綠。
**不得**以「輸出列數與手動聯集相等」作為 Gate——該比對與生成器同源，pattern 寫錯時兩邊一起錯（見 Task 0.1 §驗證第 3 點）。

🔴 **B1 硬前置（`CODEX-R3-P1-01`，非建議、不得省略）**：
B1 是 **G-MANIFEST 首次真正執行**的 Phase，故 B1 **必須**交付
**`T1-I1` production-path integration test**——以 repo 內**真實**的 G-MANIFEST consumer
（B1 須將 Gate 條款落成可執行元件）對 `handoffs/govflow_phase_base.tsv` 端到端驗證：
缺 Phase 1 列 ⇒ Gate rc!=0；有效列 ⇒ 取得 base 且 rc==0。
須附 mutation 證明（壞 SHA／壞 ISO8601／欄數 !=3 各一 ⇒ rc!=0）。
🔴 **且須機械強制，不得只留文字約束**〔`CODEX-R4-P3-01`：實跑
`rg -n 'G-MANIFEST|T1-I1|govflow_phase_base' scripts` **僅命中生成器**，
`gate.sh`／`committee_run.sh` 仍是 generic dispatch，**現無任何檢查把 `T1-I1` 綁定 Phase 1 通過**〕：
B1 須在 `G-MANIFEST（N=1）` Gate 內機械檢查 `T1-I1` **存在且通過**，
並驗缺列／壞 SHA／壞 ISO8601／欄數錯**均非零**。
**理由**：`T0-C3` 只能證偽 schema，**證偽不了真實 consumer**——兩者是不同的 oracle，
不得以前者充當後者。⚠️ **B1 若未交付 `T1-I1`，Phase 1 Gate 不得判通過。**

### 🔴 G-MANIFEST — Phase 1／2／3／4 共用 Gate 條款（Phase 0 的下游消費者）

〔來源＝**codex STAMP3 戳記 REJECTED 理由**。無此條款時 manifest **零下游消費者**，
Task 0.1 淪為裝飾品，且 §R 「Phase 1/2/3 依賴 Phase 0」的耦合宣稱不成立。〕

每個 Phase N（N ∈ {1,2,3,4}）的 Gate **一律加入**：

```
實改集合 = git diff --name-only <phase-base>..HEAD          # 本 Phase 實際動到的檔
允許集合 = gen_govflow_manifest.sh 輸出中 phases 欄含 N 的 path
實改集合 ∖ 允許集合 == ∅   ⇒ 通過
否則 ⇒ Gate FAIL
```

- **語意**：實作端動了 manifest 沒宣告的檔 ⇒ **要嘛 scope 外洩、要嘛 manifest 漏列**，兩者都須停。
- 🔴 **失敗時禁把該檔補進 manifest 了事**——須先判定是哪一種，
  scope 外洩 ⇒ 回退該改動；manifest 漏列 ⇒ 走 §D 修訂 TODO 後重跑 B0。
- 🔴 **`<phase-base>` 改為機器記錄，不得由人推斷**〔來源＝**codex STAMP4**：v2 定義為
  「該 Phase 第一個 commit 的 parent」，但**「第一個 commit」本身無自證來源**——
  實作端事後任選一個 commit 都能自圓其說，Gate 形同虛設〕：
  - 每個 Batch **開工第一件事**執行 `bash scripts/gen_govflow_manifest.sh --record-base <N>`，
    它把 `<N>\t$(git rev-parse HEAD)\t<ISO8601>` **append** 到 `handoffs/govflow_phase_base.tsv`
  - 該檔 **append-only**：同一 `<N>` 重複出現 ⇒ **非零離開**（防事後改寫基準點）
  - G-MANIFEST 一律從該檔取 base；**缺 Phase N 的列 ⇒ Gate FAIL**（見 `T0-C3`），
    不得回退成「用第一個 commit 猜」
- **反向不檢查**（`允許 ∖ 實改` 可非空）：manifest 是攻擊面**上界**，Phase 未必動到全部。
  🔴 **膨脹路徑已由 Task 0.1 邊界④封閉**：要把某檔加進允許集合，必須讓它進入 `B∪C∪D`，
  而 `D` 是從「修改檔案」bullet 機械抽取 ⇒ **等於一次可見的 TODO 修訂**，
  不能只動 `PHASE_MAP` 一行悄悄放寬。
- ⚠️ **具名殘留**（`GOV-MANIFEST-INFLATION-RESIDUAL`）：上述封閉的是**意外與低成本繞過**。
  蓄意者仍可同時改 TODO 修改檔案欄＋`PHASE_MAP` 來擴大允許集合。
  **本 TODO 不再處理此軸**——理由見 §N；此殘留**不阻塞 B0 派工**。

---

## Phase 1 — heading 判準（目標：修 `E-1` 誤報，且不放過任何現行真陽性）

**完成後系統狀態**：`completeness_check --single` 對 18 列行為表逐列符合預期。

### Task 1.1 — `extract_heading_ids` 四步程序

- **SPEC ref**：§P Phase 1 Task 1.1　**目標**：以有限 allowlist 修誤報，真陽性邊界不縮。
- **輸入 / 輸出**：輸入＝markdown 檔；輸出＝canonical ID 列表 ＋ rc。
- **實作要點（≥3，含偽碼）**：
  ```
  (1) 整行命中 canonical ^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$ → 走 family-binding
  (2) 【完整 heading 文字】∈ ALLOWLIST                      → 放行
        ALLOWLIST = { "E-1～E-7 逐條 Verdict" }             ← 逐字，唯一集合
  (3) 其餘命中 ^[A-Z]+(-[A-Z0-9]+)+$                        → 判畸形
  (4) 不命中 id-like                                        → 放行
  ```
  🔴 **鍵值必須是完整 heading，不是首 token**——若鍵在首 token，裸標題 `## E-1` 亦會被放行
  （現行 rc=1）。這是 R5 的 BLOCKING。
  🔴 **不得**用 `^[A-Z]-[0-9]+$` 這類寬 regex（R3 的 BLOCKING）。
  🔴 **不得**新增「家族前綴＋全字母段 ⇒ 放行」這類規則（R4 的 BLOCKING，會放掉 17 個真陽性）。
- **修改檔案**：`scripts/completeness_check.sh` 的 `extract_heading_ids()`（awk 區塊，現約 L163-169）。
  **既有 caller**：`cx_run.sh --single`、`debt_clear.sh --lock`、`reconcile_build.sh`、
  `gate.sh`、`reconcile_add_stamp_section.sh`、`reconcile_clear_stamps.sh`（見 Phase 0 manifest）。
- **不可做**：不得改動 canonical ID 正則；不得放寬 family-binding；不得為讓某列變綠而新增未經委員審的 allowlist 項。
- **邊界（≥2）**：① heading 含全形字元或 `～` 分隔 ⇒ 截斷點行為須與行為表一致
  ② heading 為空或僅 `##` ⇒ 不進候選、放行。
- **風險緩解**：R2–R5 四輪 BLOCKING 皆在此 Task；**每次修補後須重跑表外掃描**（見驗證第 3 條）。
- **存活至**：永久——`extract_heading_ids()` 是 `completeness_check` 的核心判準，不會被後續 Phase 取代。
- **覆蓋風險**：**有**——Phase 2 的 `format-failed` 判定**直接依賴**本 Task 改後的 `--single` 行為
  （語意耦合，非 import 耦合）。⇒ 本 Task 若 revert，**Phase 2 全部測試須重跑**；revert 順序見 §R。
- **驗證（`pytest tests/governance/test_completeness_idlike_fp.py` rc==0；三條逐項如下）**：
  1. `venv/bin/python -m pytest tests/governance/test_completeness_idlike_fp.py -q` rc==0，
     collected 數 **== SPEC 行為表列數（`awk` 機械計數）＋ Phase 1 測試表其餘列**。
     🔴 **禁在此寫死數字**；以 `pytest --collect-only -q <該檔> | wc -l` 對照 SPEC 表計數。
  2. **mutation**（第 19 例）：把 `extract_heading_ids()` 複製到隔離副本，
     以 SPEC 所列「rev2 已刪的三條方向」**完全取代**四步程序（**非疊加**），其餘不動；
     預期 `## ADV-CODEX-1` 由 `rc==1` **轉為 `rc==0`** ⇒ 該用例**轉紅**；
     恢復修法後同一 node **轉綠**。**兩段 receipt 皆須貼 rc 與關鍵 stdout。**
  3. **表外掃描**：對至少 20 個未列入行為表的 heading text 掃描，
     確認**無** `current rc=1 → new rc=0` 的漏網（codex R6 已示範此法）。

### Phase 1 測試 ＋ Gate

| Test ID | 層級 | 內容 |
|---|---|---|
| T1-U1..U18 | 單元 | 行為表 18 列逐列（參數化） |
| T1-M1 | mutation | 三方向取代 ⇒ `ADV-CODEX-1` 轉紅；恢復後轉綠 |
| T1-B1 | 邊界 | 全形／`～` 截斷 |
| T1-B2 | 邊界 | 空 heading |
| T1-R1 | 回歸 | 表外 20 個 token 無漏網 |

**Phase Gate**：T1-* 全綠 ＋ `pytest tests/governance -q` 全綠（既有測試不得因本 Task 轉紅）
＋ 🔴 **G-MANIFEST（N=1）**。

---

## Phase 2 — `result_state` 收窄（目標：格式不合規不得記 success，使同輪可重派）

**完成後系統狀態**：格式失敗的家族可在同輪重派；`debt_clear` 仍拒絕以 `format-failed` 銷帳。

### Task 2.1 — 格式檢查移到 audit append 之前

- **SPEC ref**：§P Phase 2 Task 2.1　**目標**：消除 orphan-success。
- **輸入 / 輸出**：輸入＝委員 CLI 結果 ＋ 產出檔；輸出＝`committee_family_result` 事件。
- **實作要點（≥3，含偽碼）**：
  ```
  brief-kind ∈ {review, consult, closure} 且 cli_rc==0 且產出非空：
      先跑 completeness_check --single  →  再 _emit_family_result
        格式 rc==0 → result_state=success        + 非空 output_sha256
        格式 rc!=0 → result_state=format-failed  + 非空 output_sha256
      其餘（cli_rc!=0 或產出空）        → result_state=failed + 空 sha
      格式 checker 無法執行             → fail-closed，不得記 success
  brief-kind ∈ {impl, stamp}：判準與行為皆不變
  process exit code：format-failed 時維持現行 exit 3（主委現形）
  ```
  🔴 **順序是規則本身**——現行 `_emit_family_result`（`cx_run.sh:445`）跑在格式檢查（`:475`）**之前**，
  audit 是 append-only，`success` 一旦寫入不可變。**只改判準無效。**
  🔴 **所有**呼叫 `_emit_family_result` 的入口（含 `CX_STUB_MODE` 未知值分支 `:404-411`）須遵守同一順序。
  🔴 `format-failed` 須先加進 `scripts/audit_events.json` 的 `enums.result_state`，
  否則 `audit_append.sh:550-557` 會拒寫。
- **修改檔案**：`scripts/cx_run.sh`（`_emit_family_result` 與其**所有**呼叫點順序）、
  `scripts/audit_events.json`（`enums.result_state`）。
  **既有 caller/consumer**：`committee_run.sh`、`audit_append.sh`（空 sha 例外僅 `failed`）、
  `debt_clear.sh:327`（守衛⑤）、`_debt_ledger_core.py`、`cx_run.sh:255`（守衛⑥）、
  `test_registry_v2_shape.py:58`（硬編二值）。
- **harness 遷移（裁定採①）**：`CX_STUB_MODE=success` 在 findings-kind 下改寫**最小合法四欄 finding**。
  🔴 **交付物：具名 node 清單**〔`COMPOSER-R1-P1-04`；SPEC L235 要求〕——B2 執行時須實跑
  `venv/bin/python -m pytest tests/governance/test_debt_emit.py tests/governance/test_stamp_taskid_inject.py -q`，
  產出**「因本次改動由 pass 轉 fail 的具名 node 清單」**（含 nodeid 與 rc），
  作為 **Phase 2 Gate 的必要輸入**。🔴 **不得只寫檔名或形容詞。**
  預期轉紅的既有檔：`test_debt_emit.py`、`test_stamp_taskid_inject.py`
  ——🔴 **實際數量以實跑清單為準**（SPEC 曾寫「大量」被 grok 實測推翻）。
- **不可做**：🔴 **不得放寬 `debt_clear` 守衛⑤**（放寬會讓空殼／畸形 findings 進收斂檔）；
  不得讓 `format-failed` 自動觸發重派；不得把 rc 改成 0 讓整輪看似全綠。
- **邊界（≥2）**：① `output_sha256` 空值例外僅 `failed` ⇒ `format-failed` 用非空 sha
  ② 格式 checker 不存在／不可執行 ⇒ fail-closed，不得記 success。
- **風險緩解**：本 epic **三次**因此缺陷卡死（R4 codex／R6 grok／R2 codex 連鎖）。
- **存活至**：永久——`result_state` 三值與 emit 順序是派工控制流的長期契約。
- **覆蓋風險**：**有（單向）**——Task 2.2 會把本 Task 的枚舉擴張同步進 P16 凍結契約，
  屬**補完**非覆蓋；本 Task 的 runtime 行為不會被 2.2 改寫。無其他 Phase 覆蓋。
- **驗證**：`pytest tests/governance/test_result_state_format_failed.py -q` rc==0，
  collected 數 **== Phase 2 測試表列數**（`--collect-only -q | wc -l` 對照，🔴 **禁寫死數字**）；
  含 **orphan-success 否定 oracle**（格式紅時 audit 最新 `result_state` **不得**為 `success`）。

### Task 2.2 — P16 凍結契約同步

- **SPEC ref**：§P Phase 2 Task 2.2　**目標**：`result_state` 擴張同步到凍結契約，避免三方漂移。
- **輸入 / 輸出**：輸入＝Task 2.1 的枚舉擴張；輸出＝P16 的修訂（D 延伸或 R）。
- **實作要點（≥3）**：
  1. 🔴 **預設走 R**（依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1「爭議一律預設 R」）
     ——`success` 語意被 R4 事故**證偽**並收窄，不是錯字級補充。
  2. **僅在使用者明示裁 D** 且觸及面與 `D-002` 合併後無互斥時才走 D，
     且該裁定須寫進 SPEC §A「已確認結果」（含日期與使用者原話）。
  3. 更新 `test_registry_v2_shape.py` 為三值，**須在報告標明「契約擴張」**，禁默默刪 assert。
- **修改檔案**：`docs/P16_COMMITTEE_DEBT_SPEC.md`（`enums.result_state` 相關 heading）、
  `tests/governance/test_registry_v2_shape.py`。**既有 caller**：見 Phase 0 manifest。
- **不可做**：🔴 **實作者不得自行選較輕路徑**；不得只改腳本不改凍結契約。
- **邊界（≥2）**：① 委員裁定為 R ⇒ 走完整重審，不得自判 D
  ② `D-002` 未經使用者裁定前**不得預先合併**。
- **風險緩解**：`cx_run.sh:461-463` 註解**自承**「改 success 條件須走凍結修訂程序」。
- **存活至**：永久——凍結契約與 runtime 的一致性須長期維持。
- **覆蓋風險**：無。本 Task 是 Task 2.1 的契約補完，不會被後續 Phase 刪改。
- **驗證**：`bash scripts/template_check.sh dext <延伸檔>` rc==0（若走 D）；
  對應收斂檔 `reconcile_stamps_check` rc==0；`pytest tests/governance/test_registry_v2_shape.py -q` 全綠。

### Phase 2 測試 ＋ Gate

| Test ID | 層級 | 內容 |
|---|---|---|
| T2-U1 | 單元 | 格式紅 ⇒ `result_state==format-failed` |
| T2-U2 | 單元 | 格式綠 ⇒ `success`，重派仍被拒 |
| T2-U3 | 單元 | `format-failed` ⇒ 同輪重派**允許** |
| T2-N1 | 否定 | **orphan-success**：格式紅時 audit 最新不得為 `success` |
| T2-B1 | 邊界 | 空 sha 例外僅 `failed` |
| T2-B2 | 邊界 | checker 不可執行 ⇒ fail-closed |
| T2-C1 | 契約 | `debt_clear` 對 `format-failed` **仍拒銷帳** |
| **T2-C2** | 契約 | 🔴 **`brief-kind=impl` ⇒ 判準與行為皆不變**（SPEC Task 2.1 驗收第六項；v1 漏） |
| **T2-C3** | 契約 | 🔴 **`format-failed` 雙軌**：audit 記 `format-failed` **且** cx_run process rc==3（v1 實作要點有寫、無測試 node） |

**Phase Gate**：T2-* 全綠 ＋ `pytest tests/governance -q` 全綠（轉紅的既有測試須逐條標契約擴張）
＋ 🔴 **G-MANIFEST（N=2）**。

---

## Phase 3 — 角色 preflight 前移（目標：不相容組合在 gate 前擋下，零副作用）

**完成後系統狀態**：`brief-kind` 與角色不相容時，不開債、不發 token、不啟動任何 `cx_run`。

### Task 3.1 — 共用角色閘 ＋ 前移

- **SPEC ref**：§P Phase 3 Task 3.1　**目標**：消除半失敗輪。
- **輸入 / 輸出**：輸入＝brief 路徑 ＋ 家族 CSV；輸出＝rc ＋ 完整不相容清單。
- **實作要點（≥3，含偽碼）**：
  1. 🔴 **禁止新增 brief parser**——reuse `brief_conformance_check.sh`（或其 `--emit` 輸出）取 `brief-kind`
     〔`committee_run.sh:100-109` 已有明文禁令〕。
  2. 抽 `scripts/_role_gate.sh`，`committee_run.sh` 與 `cx_run.sh` **呼叫同一份**。
  3. 🔴 **`governance_roles.json` 的 `_rules` 是散文，不可直接比對**〔`CODEX-R1`〕
     ——**由它導出的可執行判定表（四行，寫死於 `_role_gate.sh`）**：
     ```
     brief-kind=impl     → 家族必須 == implementer
     brief-kind=review   → 家族必須 != implementer
     brief-kind=consult  → 不限制（仍須通過下方 family→CLI 映射）
     brief-kind=closure  → 不限制（同上）
     未知 brief-kind      → fail-closed 拒絕
     ```
     對傳入的**每一個**家族逐條套用。
  4. **family → CLI 正規化映射**（**禁 raw set intersection**）：
     ```
     map = { codex→codex, grok→grok, composer→cursor-agent }
     家族合法 ⟺ 家族 ∈ review_families 且 map[家族] ∈ executor_clis
     map 查無此家族（claude／agy）⇒ fail-closed 拒絕
     ```
     🔴 `review_families=['codex','composer','grok']` 與 `executor_clis=['agy','codex','cursor-agent','grok']`
     是**異質命名空間**；raw intersection 為 `['codex','grok']`，**會誤拒合法的 composer**（R3 的 BLOCKING）。
  5. 任一不相容 ⇒ 印**完整清單**（非只第一個）並非零離開。〔`GROK-R2-P2-02`：原為第二個「4.」〕
  6. **暫存檔契約**：`_role_gate.sh` **內部自行** `mktemp` ＋ `trap` 清理，`committee_run.sh` 只呼叫
     ——避免與 `cx_run.sh:39-44` 的「單一 EXIT trap」約束衝突（trap 是覆寫非疊加）。
- **修改檔案**：新建 `scripts/_role_gate.sh`；`scripts/committee_run.sh`（`gate.sh dispatch` **之前**插入）；
  `scripts/cx_run.sh:72-94`（改為呼叫共用函式）。
- **不可做**：不得移除 `cx_run.sh` 的角色閘（前移是早退，不是取代）；不得用第三份 inline awk/sed。
- **邊界（≥2）**：① `governance_roles.json` 讀取失敗／JSON 壞 ⇒ fail-closed
  ② 三家中僅一家不相容 ⇒ **整批拒絕**（不得只派相容的兩家）。
- **風險緩解**：R1 輪因此賠掉一整輪（codex/composer 已跑完才發現 grok 不可派）。
- **存活至**：永久——`_role_gate.sh` 為 `committee_run` 與 `cx_run` 的共用單一真相源。
- **覆蓋風險**：無。`cx_run.sh` 的既有角色閘**刻意保留**（defense-in-depth），
  本 Task 只把它改為呼叫共用函式，不刪除該檢查點。
- **驗證**：`pytest tests/governance/test_rolegate_predispatch.py -q` rc==0，
  collected 數 **== Phase 3 測試表列數**（`--collect-only -q | wc -l` 對照，🔴 **禁寫死數字**），含：
  `composer` 正例（防誤拒回歸）／傳入 `claude` ⇒ rc!=0／傳入 `agy` ⇒ rc!=0／
  不相容時 **`.claude/gate/audit.log` 無新 `committee_dispatch`、無新 round、無 gate token**。

### Phase 3 測試 ＋ Gate

| Test ID | 層級 | 內容 |
|---|---|---|
| T3-U1 | 單元 | `review` ＋ implementer ⇒ rc!=0 且零副作用 |
| T3-U2 | 單元 | `consult` ＋ 同組 ⇒ 正常進行 |
| T3-U3 | 單元 | **`composer` 正例**（防 raw intersection 誤拒） |
| T3-U4 | 單元 | `claude` ⇒ rc!=0 |
| T3-U5 | 單元 | `agy` ⇒ rc!=0 〔🔴 `COMPOSER-R2-P1-02`＋`GROK`：原為 `T3-U4/U5` **單列涵蓋兩 case**，pytest 展開為 9 而表列 8，`collected == 表列數` 契約自相矛盾。拆列後兩者皆 9〕 |
| T3-B1 | 邊界 | SoT JSON 壞 ⇒ fail-closed |
| T3-B2 | 邊界 | 三家中一家不相容 ⇒ 整批拒 |
| T3-C1 | 契約 | `cx_run.sh` 既有角色閘通過同一組用例（共用後不漂移） |
| **T3-U6** | 單元 | 🔴 **`brief-kind=impl` ＋ 非 implementer ⇒ rc!=0、零副作用**（SPEC Task 3.1 明列；v1 漏） |

**Phase Gate**：T3-* 全綠 ＋ `pytest tests/governance -q` 全綠 ＋ 🔴 **G-MANIFEST（N=3）**。

---

## Phase 4 — claim checker 豁免（目標：逐字治理產物可進版控，豁免不外溢）

**完成後系統狀態**：`handoffs/reconcile/**` 的逐字副本與附錄可 commit；主委撰寫段仍受檢。

### Task 4.1 — `sources/` 副本的註冊路徑正規化

- **SPEC ref**：§P Phase 4 Task 4.1　**目標**：副本可豁免，且不放寬其他路徑。
- **輸入 / 輸出**：輸入＝檔案路徑 ＋ 內容；輸出＝豁免 bool。
- **實作要點（≥3）**：
  1. 對 `handoffs/reconcile/<session>/sources/<name>.md` **精確形態**，回退比對
     `handoffs/<name>.md` 的已註冊 hash。
  2. **限定**：須綁定同 session 的 `sources.lock`，且 **raw-byte hash 與原註冊值相符**才豁免。
  3. 🔴 **修正 staged／worktree 不一致**：checker 從 **staged blob** 取內容掃描，
     但現行豁免對 **working-tree** 重算 hash ⇒ **兩者須取同一份 bytes**。
- **修改檔案**：`scripts/verification_claim_check.py` 的 `_committee_output_rel`／`_is_committee_process_exempt`。
  **既有 caller**：`scripts/git_hooks/pre-commit`、`verify_pretooluse.sh`、`verify_hooks_health.sh`、`gov_check.sh`。
- **不可做**：不得改 `gate.sh register-output` 的全域語意。
- **邊界（≥2）**：① 副本被竄改（hash 不符）⇒ **不豁免** ② session 外路徑／duplicate basename／symlink ⇒ **不豁免**。
- **風險緩解**：⊘
- **存活至**：永久——豁免判定是 pre-commit 的長期契約。
- **覆蓋風險**：無。Task 4.2 處理 `synth.md` 的**不同路徑**（unit 級），與本 Task 的檔級路徑判定不重疊。
- **驗證（`pytest tests/governance/test_claimcheck_verbatim_exempt.py` 的 T4-U1／N1／N2／C1／B2，rc==0）**：見 Phase 4 測試表。

### Task 4.2 — `synth.md` 的 unit 級附錄豁免

- **SPEC ref**：§P Phase 4 Task 4.2　**目標**：附錄豁免、群集段永不豁免。
- **輸入 / 輸出**：輸入＝`synth.md` 內容；輸出＝逐 unit 的豁免旗標。
- **實作要點（≥3）**：
  1. 現行 `committee_process_exempt` 是**整檔 bool**（`:1387` 一次算完、`:1394-1400` 對所有 unit 傳同一 flag）
     ⇒ **必須改為 unit/line 級**。
  2. 豁免區＝自匹配 `^## 附錄` 的標題起，至下一個 `^## `（H2）前或 EOF。
     ⚠️ 實際標題為 `## 附錄：findings 逐字保留（byte-faithful；…）`
     ⇒ **須以 `^## 附錄` 前綴匹配**，不得要求精準等於 `## 附錄`。
  3. `## 群集 / 處置` 段**永不豁免**，含其下的 H3/H4 nested unit。
- **修改檔案**：`scripts/verification_claim_check.py` 的**三個掛點**——
  **`check_files()`（L1407）／`check_unit()`（L1244）／`_scan_file_content()`（L1375）**。
  🔴 **v1 誤寫 `check_file`（單數）——該符號不存在**；已實跑 `grep -n 'def check_file'` 確認。
  🔴 **`_scan_file_content` 是 `CODEX-R1-P1-04` 碼證明列的第三個掛點**，v2 首版仍漏，
  由 codex 於戳記輪 REJECTED 時補正——**只改前兩個掛點不完整**。
- **不可做**：🔴 不得用 `VERIFY-EXEMPT` 檔頭豁免整份收斂檔；不得改動 claim ledger 的 fingerprint 衝突判定。
- **邊界（≥2）**：① 附錄後又出現 `## 群集`（順序顛倒）⇒ 群集段仍不豁免
  ② 檔內有兩個 `## 附錄` ⇒ 行為須具名並測。
- **風險緩解**：⊘
- **存活至**：永久——unit 級豁免邊界是收斂檔可進版控的長期前提。
- **覆蓋風險**：無。與 Task 4.1 的檔級路徑判定互補，不重疊。
- **驗證（`pytest tests/governance/test_claimcheck_verbatim_exempt.py` 的 T4-U2／N3／N4／N5／B1／N6，rc==0）**：見下表。

### Phase 4 測試 ＋ Gate

| Test ID | 層級 | 內容 |
|---|---|---|
| T4-U1 | 單元 | `git add -f` reconcile `sources/` ＋ commit ⇒ rc==0 |
| T4-N1 | 否定 | 副本被竄改 ⇒ **不豁免**，rc!=0 |
| T4-N2 | 否定 | session 外路徑／duplicate basename／symlink ⇒ 不豁免 |
| T4-C1 | 契約 | **staged 與 worktree 內容不同** ⇒ 豁免判定與掃描取同一份 bytes |
| T4-U2 | 單元 | 附錄段內無 backing 的 claim ⇒ **PASS** |
| T4-N3 | 否定 | `## 群集 / 處置` 段同樣文字 ⇒ **FAIL** |
| T4-N4 | 否定 | 群集段下 nested H3/H4 內 claim ⇒ **FAIL** |
| T4-N5 | 否定 | 一般 handoff 檔偽造 `## 附錄` ⇒ **仍 FAIL** |
| T4-B1 | 邊界 | 兩個 `## 附錄` ⇒ 行為具名 |
| T4-B2 | 邊界 | 原註冊檔已刪／`sources.lock` 缺失 ⇒ 不豁免 |
| T4-N6 | 否定 | `docs/` 一般文件無 backing 的 claim ⇒ **仍 FAIL** |

**Phase Gate**：T4-* 全綠（collected 數 **== 本表列數**，`--collect-only` 對照，🔴 **禁寫死數字**）
＋ 🔴 **隔離 clone 確認 commit 仍可進行** ＋
`pytest tests/governance -q` 全綠 ＋ 🔴 **G-MANIFEST（N=4）**。

---

## §R 回退

- 🔴 **兩個獨立 rollback 邊界**（**非三個**）：**① Phase 0＋1＋2＋3**　**② Phase 4**。
  〔來源＝**codex STAMP2 戳記 REJECTED 理由**：v2 仍寫「①Phase 1＋2 ②Phase 3 ③Phase 4」，
  但 §B 自己已認定 **Task 2.1 與 Task 3.1 皆修改 `scripts/cx_run.sh`**（實跑
  `grep -c '_emit_family_result\|governance_roles' scripts/cx_run.sh` → **5**）而列為序列不可並行。
  同一份耦合事實不能在 §B 是「序列」、在 §R 卻是「獨立邊界」——**兩節自相矛盾**。〕
- **邊界 ① 的耦合鏈（三段，皆為單向依賴）**：
  - Phase 2 → Phase 1：Phase 2 呼叫 Phase 1 所改的 checker
  - Phase 3 → Phase 2：**同檔 `scripts/cx_run.sh`**
  - Phase 1／2／3 → Phase 0：三者的 Phase Gate 皆執行 **G-MANIFEST**（下定義）
    〔🔴 **來源＝codex STAMP3 戳記 REJECTED 理由**：本行 v2 原寫「三者的 Phase Gate 皆引用
    Phase 0 產生的 manifest」，但實跑 `sed -n '250p;337p;401p'` 顯示三個 Gate **完全沒提 manifest**
    ——**主委捏造了耦合依據**，且是在修「未機械驗證完整性宣稱」的同一次修訂中再犯。
    處置＝**不是刪掉這行，而是把它變成真的**：Phase 1–4 Gate 一律加入 G-MANIFEST，
    否則 Task 0.1 產出的 manifest **零下游消費者**，B0 錯了也永遠不會被發現。〕
  ⇒ 🔴 **revert 須逆序 `3 → 2 → 1 → 0`；不得只 revert 鏈中任一段**
  （只 revert Phase 2 會留下 Phase 3 對同檔的改動 ⇒ `cx_run.sh` 落入未定義中間態）。
  若確需保留部分成果，**改為前滾修補**（新 commit 修正），不做部分 revert。
- **邊界 ② Phase 4 獨立**：只動 `verification_claim_check.py`，與邊界 ① **無檔案交集**
  ⇒ 可單獨 revert；**獨立 commit ＋ 隔離 clone 驗證**（改 pre-commit 風險最高）。
- 任一 Phase 造成 `pytest tests/governance` 轉紅或 pre-commit 全面失效 ⇒ **立即 revert 該 Phase**。

## §N 不在本 TODO 範圍（具名，非遺漏）

- `GOV-COMPLETENESS-FAMILYPREFIX-FP`（家族前綴型誤報，17 個）
- `GOV-GATECHECK-DEBTCLEAR-DEADLOCK`（清債指令被誤判 dispatch）
- `GOV-CLAIMCHECK-VS-VERBATIM` 的 claim ledger fingerprint 分支
- `GOV-RECONCILE-LOCK-IMMUTABLE-DEADLOCK`（lock 寫入後無法修正）
- `.git/info/exclude` 收窄（屬凍結程序 v2.0 §6.3 輔案，歸 v2.0 階段 1）
- 🔴 **`GOV-BRIEF-IDPATTERN-UNVALIDATED`**（B0 review 輪具名開票，**不阻塞**）：
  brief 內指定給委員的 finding ID 格式**沒有任何機制驗證它是否符合** `completeness_check.sh`
  的 `CANONICAL_ID_RE='^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$'`。
  **實證事故**：主委在 B0 review brief 指定 `<FAMILY>-B0R-P<0-3>-<NN>`，`B0R` 不合 `R[0-9]+`
  ⇒ codex 照指示產出後被交件檢查判不合規、整輪只能 `--abandon`；composer 則自行退回
  `COMPOSER-R1-*`（格式合法但與 TODO R1 輪撞號）。**是主委下錯指令，非委員之過。**
  修法方向：`doc_format_precheck.sh` 對 `brief-kind ∈ {review, consult}` 的 brief，
  抽取其中的 ID 樣板並對 `CANONICAL_ID_RE` 驗證。
  ⇒ 產出端檢查目前**只擋委員的產出，不擋主委在 brief 下的錯誤指令**——強制點裝在消費端。
- 🔴 **`GOV-SPEC-REV6-STALE-COUNTS`**（R2 具名開票，**不阻塞 B0**）：
  SPEC rev6 驗證欄的 `19/6/8 passed`（Phase 1／2／3）與 TODO 機械展開數 `22/9/9` 不符
  ——照 SPEC 當 gate 會分別漏測 3／3／1 個 case。Phase 4 的 `6+5=11` 一致。
  SPEC rev6 **已凍結**，依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` 走延伸檔修訂，
  **不就地改**。實作端一律以 §0 第 5 條的對照表為準。
- 🔴 **`GOV-MANIFEST-INFLATION-RESIDUAL`**（STAMP4 具名開票，**不阻塞 B0**）：
  蓄意者同時修改「修改檔案」bullet 與 `PHASE_MAP` 即可擴大 G-MANIFEST 的允許集合。
  **不在本 TODO 處理的理由**（三條，皆非「做不到」）：
  ① 本 epic 的 scope 是**修四個既有缺陷**，不是建構抗蓄意的供應鏈信任模型；
  ② 該路徑需要**兩處協同修改一份已戳記的 TODO**，必然留下 diff 與戳記失效軌跡
  ——已從「一行悄悄放寬」降為「可見的文件修訂」，意外與低成本繞過已封閉；
  ③ 對抗審在「防蓄意」框架下無收斂終點（本 epic 線 B 已有前例：六輪 30+ 次派工、
  50% 純開銷）。依使用者定死之「**95% 解法就收、殘留具名記錄不當阻塞**」條款收斂。
  **重啟條件**：出現真實（非假想）的繞過事故，或本 epic 外另立抗蓄意 epic。
