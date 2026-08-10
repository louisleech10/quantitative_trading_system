# 站 2.5 狀態事實入 fact-key — 實作 TODO

> 底本 SPEC：`docs/GOVB25_STATUS_FACTKEY_SPEC.md`（**r5 定案版**）
> 收斂檔：`handoffs/reconcile/20260810-govb25-x-review-r{1,2,3,4}/synth.md`（12＋7＋4＋1 條，全數接受）
> 實作端：主委自任｜審查：codex ＋ composer（兩個非實作者家族）｜日期：2026-08-10

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 0.1 🔴 三項必讀狀態宣告

1. **`CODEX-R4-P1-01` 之關閉尚待原提出方複驗**——本 TODO 之審查輪必答第 1 條即為該複驗。
   在 codex 判定「已關閉」之前，Task 1.3 之票號抽取器**不得視為定案**。
2. **`票 B-51` 事前裁決已於 r2 取得**（codex (C)／composer (A)，兩家皆核可），
   六項條件逐條列於 Task 1.4；**未滿六條前不得動 `tests/governance/test_govb1_factkey_gen.py`、不得建延伸檔**。
3. 本 TODO **不重列** SPEC 已定義之枚舉、集合、判準值——一律 pointer 回 SPEC 或 `scripts/fact_keys.json`。

### 0.2 凍結與 scope 約束（違反即 gate 紅）

- `docs/GOVB1_INPUT_QUALITY_{SPEC,TODO}.md`、`docs/GOVB0_*` **全程唯讀**；`docs/GOVB1_` 為 OOE 硬保護前綴。
- `scripts/govb1_frozen_hashes.txt` 主委專屬；`scripts/governance_families.json` epic 期間不可 commit（`R-15`）。
- `_B45_HARNESS` 五檔 epic 期間禁改：`test_cxrun_stamp_prompt.py`／`test_stamp_taskid_inject.py`／
  `test_rolegate_predispatch.py`／`test_result_state_format_failed.py`／`test_completeness_idlike_fp.py`。
- manifest 分類：`scripts/fact_keys.json`／`scripts/gen_fact_key_blocks.sh`／
  `tests/governance/test_govb1_factkey_{gen,hook}.py`／`tests/governance/fixtures/govb1/` 在 **allow**；
  `HANDOFF.md`／`白話說明/`／backlog 在 **meta**；
  🔴 **`docs/` 下所有檔皆不在 manifest ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer**，
  收尾必跑 `bash scripts/govb1_final_gate.sh --only g7`。

### 0.3 不可違反原則

- 不得以 `git push --no-verify` 繞過 pre-push。
- 不得放寬既有斷言換綠燈（見 0.4）。
- 不得在偵測器內硬編識別碼、狀態值、路徑或豁免項——一律由 `scripts/fact_keys.json` 導出。
- `rc` 禁經 pipe 取；改檔一律用 Edit/Write 工具，禁 `sed -i`／heredoc。

### 0.4 防假綠（diff 斷言驗收）

下列既有斷言**不得放寬或刪除**，收斂前須 `git diff` 逐處說明「為何是新行為而非放寬」：
`test_fixtures_differ_only_in_block_content`／`test_real_repo_check_passes`／
`test_t21_m1a_sort_is_load_bearing`／`test_t21_m1b_locale_pin_removal_breaks_determinism`／
`test_t21_m1c_generation_failure_is_not_swallowed`／`test_reserved_schema_key_is_skipped_not_treated_as_fact_key`／
🔴 `test_empty_registry_is_rc_zero_not_failure`（`CODEX-R5-P1-02`：新增之 schema fail-closed 與此測試
語義互斥，**修法是定唯一語義，不得刪測試或放寬 fail-closed**；語義見 Task 1.2 實作要點 0）。

## §A 假設與事實（facts-resolved）

- facts-resolved: 註冊表現況恰一 key → `LC_ALL=C jq -r 'keys[]' scripts/fact_keys.json` → `_schema` `governance-execution-order`
- facts-resolved: 既有硬斷言位置 → `tests/governance/test_govb1_factkey_gen.py:68`
- facts-resolved: 三條 extractor 實跑輸出 → `B0…B7`（＋`B3R`）／`b1…b10`／`B-15 B-31 B-50 B-53 B3R`
- facts-resolved: 票號抽取器 13 列 TP/TN 矩陣全數符合預期（含 `B3RB3R`／`XB3RB3R` → 空）
- facts-resolved: 偵測詞彙逐檔命中數 → 見 SPEC §A 末條 receipt（`白話說明/` 9 檔共 150 行）
- **待確認：無**

## §B 批次執行策略（依賴拓撲 → 最少批次）

| 批 | Task | 前置 | 為何不可再拆 | 大小 |
|---|---|---|---|---|
| **C1** | `1.1`／`1.2`／`1.3`／`1.4` | 無 | SPEC §R 四列約束交集：schema 契約與消費者、`status_keys` 與其所指 key、新 key 與斷言、陣列型 `target` 與多宿主程式，**任一拆開中間 commit 即轉紅** | 大 |
| **C2** | `2.1`／`2.2` | C1 | 偵測器先落地 ⇒ 真實 repo 37 行命中、`--check` 立刻擋死所有 push | 大 |

**Gate**（🔴 `CODEX-R5-P1-01`：本表逐項複製自 SPEC §R，**以 SPEC §R 為準**；
前版只列三項，弱於 SPEC 之每-commit 閘 ⇒ 照 TODO 做會漏三項）：

| # | 檢查 | C1 → C2 | C2 → 完工 |
|---|---|---|---|
| 1 | `bash scripts/gen_fact_key_blocks.sh --check`（真實 repo）rc=0 | ✔ | ✔ |
| 2 | `pytest tests/governance/test_govb1_factkey_gen.py tests/governance/test_govb1_factkey_hook.py -q` rc=0 | ✔ | ✔ |
| 3 | `pytest tests/governance -q` **全套**全綠 | ✔ | ✔ |
| 4 | 凍結 hash 閘綠（`docs/GOVB1_INPUT_QUALITY_{SPEC,TODO}.md` sha 不變） | ✔ | ✔ |
| 5 | `bash scripts/govb1_final_gate.sh --only g7` rc=0 | ✔ | ✔ |
| 6 | 誤擋率 receipt 產出且經非實作者家族複核 | — | ✔ |

🔴 **只交 C1 不交 C2 ＝ 靜默欠收，判 BLOCKED 非完成**（SPEC §R 末列）。
🔴 全套 `pytest tests/governance -q` 約 330 秒 ⇒ **一律丟背景**，並於跑完 `bash scripts/restore_golden_inventory.sh`。

## Phase 1 — 機制、schema、資料與斷言（批 C1；單一 commit）

### Task 1.1 — `target` 支援多宿主檔 ＋ projection oracle

- **新建**：無
- **修改**：`scripts/gen_fact_key_blocks.sh`（`_fk_target` → `_fk_targets`；`_fk_check`／`_fk_write`／
  `_fk_reject_unregistered_blocks` 三處迴圈）、`tests/governance/test_govb1_factkey_gen.py`（新增斷言）
- 實作要點：
  1. `_fk_targets <key>` 逐行輸出目標路徑：`.[$k].target` 為 `string` ⇒ 單元素；為 `array of string` ⇒ 逐筆；
     其餘型別 fail-closed。空陣列／重複路徑／絕對路徑／含 `..` 一律 fail-closed。
  2. 三處迴圈改為對每個 target 各做一次既有處理；路徑檢查**逐筆**套用。
  3. **projection oracle**：同一 key 之所有 target 之區塊內容須逐位元組相同。
     實作方式＝生成一次 `_fk_gen_block`，對每個 target 各比對同一份內容（自然滿足），
     並新增測試證明「兩宿主各自自洽但彼此不同」時 rc≠0。
- **驗證**：`pytest tests/governance/test_govb1_factkey_gen.py -q` rc=0；三條 ASSERT 見 SPEC Task 1.1。
- **邊界**：SPEC Task 1.1 四項逐條各一測試。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得引入 glob／目錄遞迴宿主。

### Task 1.2 — `_schema` 增訂四項封閉集合宣告

- **新建**：無
- **修改**：`scripts/fact_keys.json`（`_schema`）、`scripts/gen_fact_key_blocks.sh`（驗證邏輯）、
  `tests/governance/test_govb1_factkey_gen.py`
- 實作要點：
  0. 🔴 **唯一語義（`CODEX-R5-P1-02`；三處同步：SPEC Task 1.2、本欄、`_schema.invariants`）**——
     新增之 fail-closed **不得**與既有「空註冊表 rc=0」契約衝突
     （`tests/governance/test_govb1_factkey_gen.py:297-303` 對 `{}` 期待 rc=0）：
     · 註冊表**無任何 fact-key** ⇒ `--check` rc=0（既有契約不變，該測試須維持綠）。
     · 註冊表**有 ≥1 fact-key** ⇒ `_schema` 四欄必須存在且合法，否則 fail-closed。
     ⇒ 驗證函式須**先判有無 fact-key**，再決定是否套用四欄檢查。
  1. 新增 `status_enum`／`status_keys`／`status_scope`／`status_scope_grandfathered` 四欄，
     值域與編碼規則見 SPEC Task 1.2（**本 TODO 不重列值**）。
  2. `fields.target` 型別說明改為 `string | array of string`；
     `_schema.invariants` 增列上述唯一語義（取代原「本檔為空物件 ⇒ rc=0」之單句，使兩種情形皆明示）。
  3. 生成器新增 `_fk_validate_schema_sets`（**僅在有 ≥1 fact-key 時執行**）：
     四欄缺席／非陣列／空陣列／含非字串 ⇒ fail-closed；
     `status_keys` 含未註冊 key ⇒ fail-closed；`status_scope` 含 wildcard 字元（`*`／`?`／`[`）⇒ fail-closed。
- **驗證**：三條 ASSERT 見 SPEC Task 1.2；`pytest … -q` rc=0。
- **邊界**：SPEC Task 1.2 四項；另加「`_schema` 仍被當保留鍵跳過」回歸。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得在任何 markdown 重列四欄之值。

### Task 1.3 — 新增兩個狀態 fact-key、宿主標記、fixtures

- **新建**：`tests/governance/fixtures/govb1/factkey_clean/白話說明/接下來要做什麼.md`、
  `…/factkey_clean/白話說明/治理待辦總覽.md`、`…/factkey_drifted/白話說明/接下來要做什麼.md`、
  `…/factkey_drifted/白話說明/治理待辦總覽.md`
- **修改**：`scripts/fact_keys.json`、`docs/GOVERNANCE_EXECUTION_ORDER.md`、
  `白話說明/接下來要做什麼.md`、`白話說明/治理待辦總覽.md`、
  `tests/governance/fixtures/govb1/factkey_{clean,drifted}/docs/GOVERNANCE_EXECUTION_ORDER.md`、
  `tests/governance/test_govb1_factkey_gen.py`、
  🔴 `tests/governance/test_govb1_factkey_hook.py`（`CODEX-R5-P1-03`：其宿主安裝 helper
  `:41,82-92` 只有單一 `TARGET_REL` 與一次 `shutil.copy2`，新增雙宿主 target 後 clean hook 驗證
  會先報 `MISSING TARGET`；helper 須改為**安裝全部已登記 target**，
  且 clean／drifted 之原有斷言**不得放寬**）
- 實作要點：
  1. 依 SPEC §E1–E3 之命令**實跑**取得三組識別碼，逐筆記錄 `snapshot`（`git rev-parse HEAD`）
     與逐檔 blob SHA；任一來源工作樹與 HEAD blob 不一致 ⇒ 停手，先 commit 或還原。
  2. 票號抽取器照抄 SPEC 參考實作（**絕對位移版**；樣式以字串傳入 `match()`）。
  3. 新增兩 key 與其 `target` 陣列；於四個宿主檔置入空 `BEGIN/END` 標記；跑 `--write` 生成。
  4. 兩個 fixture 根各補齊新宿主檔；`factkey_drifted` 僅於既有 `GOVERNANCE_EXECUTION_ORDER.md`
     保留單列竄改，新增宿主檔與 clean 相同（維持既有「恰一列不同」對照力）。
  5. 新增測試：逐筆比對 E1–E3 輸出與 key rows 第 2 欄；TP/TN 13 列矩陣。
- **驗證**：三條 ASSERT 見 SPEC Task 1.3；`pytest tests/governance/test_govb1_factkey_{gen,hook}.py -q` rc=0。
- **邊界**：SPEC Task 1.3 四項。
- **存活至**：永久。
- **覆蓋風險**：無（Task 2.2 只改敘述段，不動生成區塊）。
- **不可做**：不得放寬 `test_fixtures_differ_only_in_block_content`；不得把不在 union 之票塞進 key。

### Task 1.4 — 延伸檔與測試斷言修訂（六條件前置）

- **新建**：`docs/GOV_B25_SCOPE_AMENDMENT.md`
- **修改**：`tests/governance/test_govb1_factkey_gen.py`（`test_registry_is_valid_json_object_with_the_single_initial_key`）
- 實作要點：
  1. 動碼前逐條核對 SPEC Task 1.4 之六項條件，於延伸檔內逐條記錄核對結果。
  2. 斷言改為集合相等，並加兩條 normative 交叉斷言（延伸檔新增集 ＝ Task 1.3 兩 key；
     registry 全集 ＝ 凍結期單一 key ∪ 新增集）。**禁 `issubset`／`>=`／`in`**。
  3. 延伸檔缺失／key 重複／含未知 key ⇒ 測試 fail-closed。
- **驗證**：`pytest tests/governance/test_govb1_factkey_gen.py -q` rc=0；四條差分自證見 SPEC Task 1.4。
- **邊界**：SPEC Task 1.4 四項；含凍結 hash 閘綠、OOE trailer、`--only g7`。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得就地改凍結 TODO；不得放寬成「至少包含」。

## Phase 2 — 偵測器與副本拆除（批 C2；單一 commit，須含兩 Task）

### Task 2.1 — 手寫狀態偵測器

- **新建**：`handoffs/20260810-govb25-fp-receipt.md`（誤擋率 receipt）
- **修改**：`scripts/gen_fact_key_blocks.sh`（新增 `_fk_reject_handwritten_status`，掛 `_fk_check` 尾端）、
  `tests/governance/test_govb1_factkey_gen.py`
- 實作要點：
  1. 列舉：`git ls-files --cached --others --exclude-standard -z --` 全樹，
     **在腳本內**依 `status_scope` 之 exact／directory-prefix 規則過濾（**不得**把字串當 pathspec）。
  2. 減去 `status_scope_grandfathered`；豁免清單以**集合相等**與測試期望值比對。
  3. 非 regular file（symlink／gitlink／模式非 `100644`/`100755`）⇒ rc≠0 並具名路徑。
  4. 對每檔取生成區塊以外之行，命中「識別碼 ∩ `status_enum`」⇒ rc≠0，訊息含檔名、行號、命中值。
  5. 誤擋率 receipt：全量掃描、逐筆 TP/FP、Wilson 95% CI ≤5%、分母與命中清單指紋。
- **驗證**：四條 ASSERT 見 SPEC Task 2.1；`pytest … -q` rc=0；
  🔴 **receipt 未產出或未經非實作者家族複核 ⇒ 本 Task 判 BLOCKED**。
- **邊界**：SPEC Task 2.1 七項逐條各一測試。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得硬編任何識別碼／狀態值／路徑／豁免項；不得改用關鍵字黑名單擴張。

### Task 2.2 — 範圍內檔案拆除字面狀態

- **新建**：無
- **修改**：`docs/GOVERNANCE_EXECUTION_ORDER.md`（17 行）、`白話說明/接下來要做什麼.md`（2 行）、
  `白話說明/治理待辦總覽.md`（18 行）
- 實作要點：
  1. 逐行改為指向生成區塊之指標，或改為不含狀態值之歷史敘述。
  2. 產出改寫前後逐行對照表（37 行），逐行標處置類別，附於 commit 訊息或 `docs/GOV_B25_SCOPE_AMENDMENT.md`。
- **驗證**：`bash scripts/gen_fact_key_blocks.sh --check` rc=0（真實 repo）；
  `bash scripts/plain_docs_sync_check.sh` rc=0；`bash scripts/govb1_final_gate.sh --only g7` rc=0。
- **邊界**：SPEC Task 2.2 三項。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得動 `status_scope_grandfathered` 所列 7 個歷史日誌檔；不得以同義詞規避偵測。
