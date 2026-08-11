# B-49 永久 path grant（git 物件綁定）— 施工清單 TODO

> 對應 SPEC：`docs/GOV_B49_PATH_GRANT_SPEC.md`（r6 定案，5 條 `[MUST-BEFORE-IMPL]` 已修畢）
> | 日期：2026-08-12 | 實作端：主委自任（`implementer=claude`）
>
> 🔴 **SPEC 不再開審查輪**（依使用者「95% 解法就收」與 epic 斷路器）。
> 本 TODO 之正確性由**施工後的兩個非實作者家族 code review** 承接。

## §0 全域規則與約束

**0-1　凍結面**：`_B45_HARNESS` 五檔中，本批只准觸及**三檔**：
`tests/governance/test_stamp_taskid_inject.py`／`test_rolegate_predispatch.py`／
`test_result_state_format_failed.py`。
`test_cxrun_stamp_prompt.py`／`test_completeness_idlike_fp.py` **rc 本來就 0，不得順手解凍**。

**0-2　reader inventory 不得動**（SPEC §C-5）：
`test_govb1_contract_matrix.py` 之 `:2111`／`:2213`（`len(_B45_HARNESS) == 5`）、
`:2323`（G-7 硬保護集交叉契約）、`:2517-2522`／`:2573-2574`（兩處 source-level oracle）。

**0-3　`hit_harness` 計算式與 `--name-only` 逐字保留**；三道守衛之 diff range 取法**一字不改**。

**0-4　digest 契約唯一實作**＝`_b49_object_identity(path)`（SPEC §C-9），
**不得**有任何參數可切換來源；讀不到一律 fail-closed 判不符。

**0-5　主控端跑驗收時不得動檔**；行為探針一律走**實體隔離副本**（禁 symlink，SPEC §C-10）。

**0-6　誠實邊界**：本機制只防意外與遺忘，**不防具寫入權者蓄意**（SPEC §C-6、§C-9-7、§C-11）。
**不得**宣稱「授權無法自我更新」——同批 rebind 機械上不可區分，交 code review。

**0-7　跑完測試須** `bash scripts/restore_golden_inventory.sh` 還原 golden inventory 副作用。

**0-8　全套 `pytest tests/governance -q` ≈ 600 秒** ⇒ 一律丟背景，勿前景等。

## §B 批次執行策略

**依賴鏈**：`Task 0.2`（前置）→ `Task 1.1` → `Task 1.2` → `Task 2.1` → `Task 2.2` → `Task 2.3` → `Task 3.1`／`3.2`。

🔴 **Task 0.2 是硬前置**：不先做，`Task 1.2` 一 commit 即 G-7 紅（見該 Task）。

🔴 **commit 策略**：Phase 1／2／3 可各自 commit，但**在同一次 push 之前必須全部通過**。
⚠️ 此為**流程要求，非 git 強制**（SPEC §R；repo 無機械閘可擋分次 push）。

🔴 **push 後不可撤銷的是 path grant 本身**（SPEC §R），**不是**「任何程式碼都不能回退」。
`CODEX-R1-P1-01` 指出本節前一版把 SPEC 的回退狀態矩陣抄成「不存在」，那是**抄寫漂移**。
誠實版逐列見 SPEC §R；其中**仍可用**的 operational rollback ＝
revert 其他程式碼，**且不動** grant 常數、三檔內容、closure 證據三者。
push 前須全套綠 ＋ 兩家 code review 通過。

**§0-9　適用性標註**（`CODEX-R1-P1-05`；避免機檢綠掩蓋語義空洞）：
本批只動 `tests/governance/` 與治理腳本，**不碰** `momentum/`／`api/`／`frontend/`／`data_cache/`。
⇒ 7 條解耦規則：**N/A**（無跨 `momentum/`↔`api/` 邊界之改動）。
⇒ 數值／ML／回測正確性：**N/A**（不產生任何數值輸出）。
⇒ `npm run build`：**N/A**（無前端改動）。
⇒ **適用**者僅：`pytest tests/governance`、`govb1_final_gate.sh`、
`plain_docs_sync_check.sh`、`gen_fact_key_blocks.sh --check`、`verification_claim_check`。

---

### Task 0.1 — Phase 0（**已完成，僅列以供 review 對照**）

- 目標：把「凍結檔要怎麼修」由 assumed 變 fact-verified，且不動凍結面。
- 產出：`tests/governance/_role_pin.py`（新）＋ `test_cxrun_selfcheck_prompt.py`（改）。
- **驗證**：`python3 -m pytest tests/governance/test_cxrun_selfcheck_prompt.py -q` → 7 passed；
  `python3 .claude/tmp/rolepin_probe.py` → PASS=7 FAIL=0
- **邊界**：①傳入生產 `scripts/` ⇒ 拒絕　②釘定無 CLI 配方之家族 ⇒ 拒絕
- **存活至**：永久
- **覆蓋風險**：無（Task 1.2 不覆寫本檔）
- **不可做**：不得寫 repo 的 `scripts/governance_roles.json`；不得硬編家族三元組

### Task 0.2 — 🔴🔴 **BLOCKED — 需使用者裁定，不得逕行施工**

- 目標：讓凍結三檔 ＋ `test_cxrun_selfcheck_prompt.py` 進入 `govb1_scope.manifest` 之 allow 集合。
- 病：四檔皆為**幽靈路徑**（endpoint 淨差為零 ＋ `path-only-OOE` 被無 trailer 之 in-epic commit
  毒化 ＋ 不在 allow）⇒ 一被改動即 G-7 紅，且 **OOE trailer 救不了**。
  盤點：`bash scripts/govb1_ghostpath_check.sh` → 11 條，`_B45_HARNESS` 五檔全在內。
- 🔴 **已證明走不通的路（不得重試）**：直接加 manifest allow 行 ⇒
  `test_t01_f5_manifest_matches_task_decl` 要求 allow 集合**逐條等於**
  `docs/GOVB1_INPUT_QUALITY_TODO.md`「修改檔案」節，而該檔**全程唯讀禁改**；延伸檔亦繞不掉。
- 🔴 **已封存之旁路（不得採用）**：改用 `meta` 動詞可躲開 F5 比對並轉綠，
  但 `meta` 語意是簿記檔，此舉屬「以技術手法充當達標」，使用者已定死禁止。
- 🔴 **第三條路也被證偽**（`GROK-R1-P0-01`，附碼證）：「走凍結檔正式修訂程序改
  `docs/GOVB1_INPUT_QUALITY_TODO.md` 宣告集」**照做不會成功**——改該檔會同時撞上
  `_B5_FORBIDDEN_PREFIXES` 含 `docs/GOVB1_`（`:2203-2207`，**無例外機制**）、
  G-7 未宣告、以及 `_G7_OOE_HARD_PROTECTED` 字面含 `docs/GOVB1_`（trailer 救不了）。
  ⇒ 只是把紅燈由 F5 **換成／疊加** B5＋G-7 硬牆。
- **已證偽之三條路徑（不得重試）**：
  ① 直接加 manifest allow 行 ⇒ F5 紅　② 改用 `meta` 動詞 ⇒ 可行但屬取巧，使用者已禁
  ③ 走凍結檔修訂程序 ⇒ B5＋G-7 硬牆
- **唯一自洽的機械解（機械上成立，但被使用者約束擋住）**：
  把 `docs/GOVB1_INPUT_QUALITY_TODO.md` 納入 B-49 grant 之**第四條路徑** ＋ manifest allow ＋
  **其自身宣告集**（自我宣告）⇒ F5 兩側同時含它而相等；B5 由 grant 例外承接；
  G-7 由 allow 覆蓋（覆蓋優先於 OOE 硬保護）。
  🔴 **但這要求修改一個雙重凍結的檔**（機械強制 ＋ 使用者常駐約束）
  ⇒ **委員無權解除，需使用者裁定。**
- 🔴 **待使用者三選一**：
  (a) 就本次施工解除該檔唯讀，**只准改其宣告集**（不動技術內容）
  (b) 維持唯讀 ⇒ B-49 不可實作 ⇒ **push 長期全擋**
  (c) 另設計（三條已知路徑皆已證偽，主委與兩家委員均未見第四條）
- **驗證**：`bash scripts/govb1_final_gate.sh --only g7` → rc=0 且輸出 0 行未宣告路徑；
  `python3 -m pytest tests/governance/test_govb1_contract_matrix.py -q` → 84 passed / 0 failed；
  `bash scripts/govb1_ghostpath_check.sh` → 四檔皆不在輸出清單內。
  🔴 以上**僅在使用者裁定為 (a) 之後**才適用；裁定前本 Task 不得開工，故無中間驗收態。
- **邊界**：①裁定為 (a) 時只改宣告集、不改技術內容 ②四／五檔以外之路徑不得順手加入
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：🔴 **未獲裁定前不得碰 `docs/GOVB1_INPUT_QUALITY_TODO.md`**；
  不得用 `meta` 動詞規避 F5；不得改 F5 判準本身；不得刪 manifest 既有行；
  🔴 **`decl` 數字不得預先寫死**——40 或 41 取決於該檔是否進 allow（`GROK-R1-P1-02`），
  裁定後才鎖定

### Task 1.1 — `_B49_GRANT_IDENTITY` 常數

- 目標：以字面常數表達「被授權之三條路徑及其 git 物件身分」。
- 檔案：`tests/governance/test_govb1_contract_matrix.py`（模組級新增）
- 改法：三條路徑與其 `<mode> <type> <oid>` 逐字寫死；
  值由 `_b49_object_identity(path)` 對**施工 commit 後**的 HEAD 取得。
  `_B49_HARNESS_GRANT = frozenset(_B49_GRANT_IDENTITY)`。
- **驗證**：`pytest -q tests/governance/test_govb49_path_grant.py -k grant_is_exact` 綠；
  oracle 為**字面期望集合**（路徑集合與三個身分字串逐字比對）
- **邊界**：①常數含 `_B45_HARNESS` 以外路徑 ⇒ 紅　②少於或多於三條 ⇒ 紅
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得用萬用字元／前綴；不得由 `_B45_HARNESS` 導出；
  不得寫成由同一常數導出之式子（同義反覆恆真）

### Task 1.2 — 三道 live 守衛改以 git 物件身分判定豁免

- 目標：讓施工 commit 合法，同時不使三檔變成長期白名單。
- 檔案：三道 `test_waiver_b{3,4,5}_range_does_not_touch_forbidden`
- 改法：`assert not hit_harness` 改為
  `unexcused = {p for p in hit_harness if _b49_object_identity(p) != _B49_GRANT_IDENTITY.get(p)
   or not _b49_worktree_bytes_match(p)}` ＋ `assert not unexcused`。
  `_b49_worktree_bytes_match` ＝ `git cat-file blob <授權 oid>` 與 `Path(p).read_bytes()`
  **逐位元組比對**（不經 index，故 `skip-worktree` 打不敗），並須斷言 regular file。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k waiver` 全綠
- **邊界**：①三檔授權後再改一個位元組 ⇒ 拒　②diff 含第四個 harness 檔 ⇒ 拒
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得無條件扣除；不得改 diff range 取法；不得在身分取不到時回退讀工作樹

### Task 2.1 — 引信改餵「未授權」差集

- 目標：授權三檔後，引信仍反映「另兩檔仍凍結」。
- 檔案：`_b45_freeze_still_active()`
- 改法：餵入路徑改 `sorted(set(_B45_HARNESS) - _B49_HARNESS_GRANT)[0]`；差集空 ⇒ inactive。
  新增 fail-closed：**live guard 數 ≥ 1**，全 dormant 不得回 inactive。
  `len(_B45_HARNESS) == 5` 判準保留。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k b45` 全綠；
  `test_b45_bomb_cannot_be_defused_by_skip` 通過
- **邊界**：①grant＝三檔 ⇒ 引信仍 active　②三道 guard 全 dormant ⇒ 不得回 inactive
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得在引信內寫 `assert not hit_harness` 字面

### Task 2.2 — 炸彈狀態機 R-A

- 目標：使「三檔修好 ＋ 未授權 harness 仍全拒 ＋ 票可 CLOSED」可達。
- 檔案：`test_b45_unfreeze_requires_roles_sot_closure`
- 改法：freeze active 時，`status == "CLOSED"` ⇒ 呼叫 `_assert_b49_closure_evidence()` 後 return；
  否則 `assert status == "OPEN"`。freeze inactive ⇒ `assert status == "CLOSED"`。
  docstring `:2463-2467` 之票文①②③④逐條與 Task 2.3 對照表同步改寫。
- **驗證**：`pytest -q tests/governance/test_govb1_contract_matrix.py -k "b45 or bomb"` 全綠
- **邊界**：①票 CLOSED 且證據齊 ⇒ 綠　②票 CLOSED 而證據缺 ⇒ 紅
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得把 `_assert_b49_closure_evidence()` 寫成字面比對；
  不得破壞 `test_b45_bomb_cannot_be_defused_by_skip` 要求之三項

### Task 2.3 — 閉合證據：六格獨立 selector

- 目標：每格可由**自己的** rc／pass／skip 獨立判定，對應票文條件 1／2-①②③／3。
- 檔案：`test_govb1_contract_matrix.py`（新增私有函式）＋ `tests/governance/test_govb49_path_grant.py`（新）
- 改法：照 SPEC Task 2.3 之六格表逐格實作。重點三條：
  ① **1-a 用原始碼層封閉規則**——取該函式原始碼片段（含 decorator 行），
     斷言不出現**不分大小寫**子字串 `skip`。**禁字面 `pytest.skip` 子字串掃描**。
  ② **1-b 之 selector 須先參數化**：`for kind in (...)` 改
     `@pytest.mark.parametrize("kind", ...)` ⇒ `passed == 4` 即 per-kind visit receipt。
  ③ **2-② 禁自我參照**：判準寫字面 `passed == 3`，另與外部字面集合對照；
     **不得**寫 `passed == len(review_families)`。
  🔴 **六格 selector 名稱與判準逐格列入（`CODEX-R1-P1-02`；不得只指回 SPEC）**：

  | 票文 | selector | 固定判準 |
  |---|---|---|
  | 1-a | `test_govb49_path_grant.py::test_v12_body_has_no_skip_escape` | 原始碼片段（含 decorator）不含不分大小寫 `skip`；`passed == 1` |
  | 1-b | `test_stamp_taskid_inject.py::test_v12_non_stamp_kinds_no_stamp_target_ok` | `passed == 4` 且 `skipped == 0` |
  | 2-① | `test_govb49_path_grant.py::test_stamp_path_invalid_implementer_turns_red` | base `rc == 0`；mutation 後 `rc != 0`；mutation 後 `skipped == 0`；外層 `rc == 0` |
  | 2-② | `test_govb49_path_grant.py::test_impl_path_works_for_every_cli_family` | 字面 `passed == 3`；逐一釘定後 `returncode == 0` 且 `skipped == 0` |
  | 3-a | `test_govb49_path_grant.py::test_dispatch_set_equals_review_families` | 相等（非 subset）；`passed == 1` |
  | 3-b | `test_govb49_path_grant.py::test_review_families_subset_of_eligible` | `passed == 1` |

  🔴 **runner 之 fail-closed 判準（`CODEX-R1-P1-03`；缺一即紅）**：
  ① `scripts/` **實體 copy**，且 setup 後斷言 `Path(copy).is_symlink() is False`
  ② env 最小集＝`{PATH, HOME, LANG=C.UTF-8}`，其餘**清空**（非繼承）
  ③ `-p no:cacheprovider` ＋明確 `cwd` ＋逾時上限
  ④ 子程序前後對 repo 做 snapshot diff，**不相等即紅**
  ⑤ 上述 ①–④ 任一步之 rc 非零 ⇒ **直接紅**，**不得**被子程序自身的 `rc == 0` 掩蓋
- **驗證**：Task 3.1 之 mutation 逐格轉紅
- **邊界**：①selector 不存在（改名／刪除）⇒ 紅　②子程序逾時 ⇒ 紅
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得以整檔 `exit 0` 取代具名 selector；不得在主工作樹跑；
  不得以任一格之 receipt 兼充另一格；不得把票文條件 4 列為可判定項

### Task 3.1 — mutation 矩陣（實跑 17 格）

- 目標：證明每一條判定都承重。
- 檔案：`tests/governance/test_govb49_path_grant.py`
- 改法：照 SPEC Task 3.1 之 ①–⑯（含 ⑩b／⑩c；**⑫ 已刪，不得復原**）逐格於實體隔離副本變異。
  🔴 特別注意 ①：`pytest.skip` 改回**且釘定仍在**（使其成死碼）⇒ **1-a 須紅、1-b 不會紅**
  ——這一格正是要證明 1-a／1-b 拆開的必要性。
- **驗證**：`pytest -q tests/governance/test_govb49_path_grant.py` → 17 格全綠；
  逐格「移除該判定後重跑 ⇒ 對應斷言 rc 由 1 轉 0」
- **邊界**：①grant 為空 dict　②grant 含非 harness 路徑 —— 皆須拒，非「全授權」
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得以「測試通過」作為驗收；不得復原 mutation ⑫

### Task 3.2 — 行為不變對照（OLD vs NEW）

- 目標：證明「grant 常數不存在」時對既有行為逐字無影響。
- 檔案：`tests/governance/test_govb49_path_grant.py`
- 改法：以**施工前固定之 immutable pre-B49 SHA** 為對照基準，
  `git show <PRE_B49_SHA>:tests/governance/test_govb1_contract_matrix.py`，
  對同一組假 diff 比對 OLD vs NEW 之 reject 布林。
  🔴 **不得寫 `HEAD`**（`CODEX-R1-P1-04`）：`HEAD` 會隨施工 commit 前移，
  第二個 commit 之後 baseline 就變成「已含 grant 的版本」⇒ 對照退化為自己比自己。
  ⇒ 施工前先把該 SHA 寫進本檔並凍結；或明定 Task 3.2 必須在**第一個 implementation commit 之前**完成。
- **驗證**：矩陣逐格 `old_reject == new_reject`
- **邊界**：①diff 含 harness　②diff 不含 harness
- **存活至**：永久
- **覆蓋風險**：無
- **不可做**：不得只做靜態推理充當對照

---

## 收尾（全部 Task 完成後）

1. 背景跑全套 `pytest tests/governance -q`；跑完 `bash scripts/restore_golden_inventory.sh`
2. `bash scripts/govb1_final_gate.sh --only g7` → rc=0
3. `bash scripts/govb1_ghostpath_check.sh` → 四檔應已不在清單內
4. 🔴 **兩個非實作者家族 code review**（實作者不自審）
5. 通過後才 push；**push 前須確定**——一旦 push 即不可回退
