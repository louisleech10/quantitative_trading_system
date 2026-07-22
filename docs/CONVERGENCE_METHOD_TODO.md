# 委員文件收斂方法 TODO（v3 / DRAFT / 基於 docs/CONVERGENCE_METHOD_SPEC.md v3 / 2026-07-22）

> **v3 變更**：收口 TODO v2 閉合 7 殘留——assert predicate 封極性契約(M3 標守衛非先紅)/red-receipt 補 stdout·fixture·date·commit/oracle6 幻影改 Oracle①子斷言+每oracle契約表/M4a awk 補碼證欄/mutation_red exclude 落 pytest.ini norecursedirs/B2 gate 補 m3/source_digest 專屬 nodeid。

> 冷啟動執行端不需讀其他檔即可逐 Task 寫碼。SPEC=`docs/CONVERGENCE_METHOD_SPEC.md`（v3，三家審+閉合全 APPROVED）。
> **v2 變更**：收口 TODO 三家審 48 findings→26 群集（`handoffs/20260722-convergence-todo-review-RECONCILE.md`）：TC1 B1 紅 gate 不轉綠 / TC2 assert 極性單一主路徑 / TC3 矩陣內嵌 / TC4 M4a owner / TC5 偽碼+函式簽名 / TC6 gate.sh 真實錨點（無 final 子命令）/ TC7 DEGRADED exit3 / TC8 B3 去 forward-dep / TC9 oracle nodeid / TC10 retrofit canonicalizer / TC11 追溯表修正 / …TC26。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **範圍鐵律**（SPEC §範圍）：只做**意外掉項**防護（目標 90-95%）；**不做防蓄意**（dummy 假 body/改 lock/async 偽凍結=out-of-scope）；**不碰** gate 活洞 H1-H7（Task 3.2 只在**現有**高風險派實作閘加 convergence 出口，不改通用 gate 邏輯）。
- **解耦（本任務相關）**：只動 `scripts/`+`tests/governance/`+`templates/`；不碰 `momentum/`↔`api/`；不改 audit.log 語意。**例外**（TC12）：Task 6.1 retrofit **只讀改** 2 個指定歷史 handoff（見 Task 6.1），此為 R6 水位量測明示例外，非違反「只動 scripts/tests/templates」。
- **同步 caller**（TC23）：completeness 掛載影響 `scripts/gate.sh`（派實作閘 L328-344）與 PreToolUse `scripts/gate_check.sh`（消費 gate token，不直接呼 completeness，但改 gate.sh 出口須確認 gate_check 不因新拒發碼誤判）。改動列同步點。
- **禁 bypass**（SPEC §C/Phase5）：不得新增 `--skip-completeness`/`ALLOWLIST`/`COMPLETENESS_ADVISORY_ONLY` 逃生口；正式路徑**主動拒** `COMPLETENESS_ADVISORY_ONLY`（TC24，見 Task 3.1）；回退唯一=`git revert` 整 Phase commit。
- **防假綠**（SPEC §V）：不放寬/刪既有 governance 斷言；既有「應失敗」fixtures（`test_verify_gate_b5.py::test_b5_*_fails`）保持紅；**B6 結束時** `pytest tests/governance -q | grep -c xfail`=0 且無永久 exclude（TC13）。
- **錯誤分類（bash 主體，TC19）**：`completeness_check.sh`/`gate.sh` 為 bash → 錯誤走 **stderr + 整數 exit code**（非 `get_logger`）；`tests/governance/*.py` 測試才用 pytest/Python。exit 語義：`0`=PASS/advisory；`1`=完整性 FAIL/非法輸入/檔缺（fail-closed）；`3`=`DEGRADED_PENDING`（TC7，合法降級，非 final）。
- **變異先紅鐵律**（SPEC §四.2）：機械檢查先寫紅（**禁 XFAIL**）、確認 v0 亮紅、再實作轉綠。

## §B 批次執行策略（依賴拓撲 → 最少批次；每批附派工 prompt + 預期 nodeid 集合）
| Batch | 含 Task | 依賴 | 規模 | Batch Gate（可執行；TC1/TC17） |
|-------|---------|------|------|--------------------------------|
| **B1** | Task 1.1（M1-M9 先紅 + red-receipt + pytest.ini exclude） | Phase 0（已完工） | 中 | ①`pytest tests/governance/mutation_red/ -q` → **8 先紅案 assert 紅**（M1,M2,M4a,M5,M6,M7,M8,M9 v0 `rc==0`→`assert rc!=0` 失敗）+ **M3 已綠**（守衛）②`mutation-red.receipt` 9 機械案齊 ③`pytest.ini` 加 `norecursedirs = */mutation_red`（TC13/codex P1-12）→ `pytest tests/governance -q` → **仍 151 passed**（config 排除 mutation_red，不入預設 collection）。**B1 不要求任何 nodeid 轉綠**（轉綠屬 B2-B6）。 |
| **B2** | Task 2.1（canonical ID+digest+DEGRADE 命名空間+範本+M4a body 機檢） | B1 | 中 | `pytest tests/governance/mutation_red -q -k "m3 or m4a or m5 or m6"` 轉綠/守綠（TC/codex P1-13 補 m3 owner）；`pytest tests/governance -q` ≥151（config 已排除 mutation_red） |
| **B3** | Task 3.1（lock/roster/拒收+拒 ADVISORY_ONLY）+Task 3.2（gate 掛載） | B2 | 中（最關鍵） | `pytest tests/governance/mutation_red -q -k "m1 or m7 or m8 or m9 or symlink"` 轉綠 + `test_completeness_lock.py`/`test_gate_impl_dispatch.py` 具名綠；`pytest tests/governance -q` ≥151 |
| **B4** | Task 4.1（self-check，改 completeness_check.sh §self-check）**序列先** → Task 5.1（DEGRADED 狀態機，改同檔 §degrade）**序列後** | B3 | 中 | `pytest -q` `test_completeness_selfcheck.py`/`test_completeness_degrade.py` 具名綠；≥151。**共改 `completeness_check.sh` → 4.1 先 commit、5.1 rebase 後接**（TC12 序列化） |
| **B5** | Task 6.1（5 oracle+retrofit+90% 水位） | B2+B3（+B4 僅 degrade oracle） | 中 | 5 oracle nodeid（`test_oracle1`..`test_oracle5`）全綠+`test_oracle1_p0_not_diluted`+`replay` 兩檔 coverage≥90% 非 vacuous；≥151（TC21 依賴收窄） |
| **B6** | Task 7.1（語意 charter）+`pytest.ini` 移除 `norecursedirs` 收編 mutation_red 入主 suite | B2+B3+B5 | 小-中 | `test_semantic_stamp_after_completeness` 綠；`pytest tests/governance -q | grep -c xfail`=0；移除 exclude 後 `pytest tests/governance -q` 全綠（9 機械案+新 nodeid 全計入，TC13 解除驗收） |
- **分工**：Grok 實作 / Codex+Composer 雙家 code review（實作者不自審）/ 每批 Claude 獨立驗+finding closure。
- **每批派工 prompt**：附於各 Phase 末（前置狀態+Task+`pytest` 驗證命令+預期綠/仍紅 nodeid）。

---

## Phase 0 — 前置地基（已完工，commit 574efba；receipt 豁免）
### Task 0.1 — 修 5 紅 + 單一乾淨腳本【DONE，不重做】
- SPEC ref：Phase 0 Task 0.1　狀態：**已完工**（`pytest tests/governance -q`→151 passed；`git log -1 574efba`）。receipt 豁免冷啟動深度（TC5）。
- 修改檔案：`CLAUDE.md`/`tests/governance/test_verify_gate_b5.py`/`scripts/completeness_check.sh`（已入版）。
- 不可做：不重做、不改既有「應失敗」斷言。
- 邊界：既有 `test_b5_*_fails` 保持紅（防假綠）；空 SPEC→template_check FAIL。
- 驗證：`pytest tests/governance -q` → 151 passed（已達成）。
- **存活至**：永久。**覆蓋風險**：無。

## Phase 1 — 變異測試先寫紅（目標：**8 先紅案在 v0 呈 `assert rc!=0` 失敗 + M3 守衛 v0 已綠** + red-receipt；**完成態=8 案紅+M3 綠，不要求機械 nodeid 轉綠**）
### Task 1.1 — 構造 M1-M9 mutation（8 先紅 + M3 守衛 + red-receipt）
- SPEC ref：Phase 1 Task 1.1（C2/C11/C17；TC1/TC2/TC3/TC4/TC20/TC22/TC25）　目標：**8 先紅案**（M1,M2,M4a,M5,M6,M7,M8,M9）pytest 裸 assert 在 v0 亮紅 + **M3 守衛 v0 已綠** + red-receipt 落審計。
- 輸入 / 輸出：輸入=現 `scripts/completeness_check.sh`（v0，`extract_heading_ids`/`STRICT=1`）；輸出=`tests/governance/mutation_red/test_completeness_mutations.py`（**獨立目錄，不入預設 collection**，TC22）+ `tests/governance/mutation_red/conftest.py`（`_make_session` fixture）+ run 時 `handoffs/reconcile/<session>/mutation-red.receipt`（真 run；測試期落 `tmp_path`）。
- **9 機械案逐案 polarity 矩陣（內嵌，TC3；冷啟動唯一依據）**：

  | 案 | fixture 構造 | pre-impl RC(v0) | post-impl 期望 | 機械 gate? | 轉綠 owner |
  |----|-------------|-----|-----|----|----|
  | M1 少來源 | roster 3 家，sources 目錄只放 2 檔 | 0(漏) | ≠0 | ✓ | Task 3.1 |
  | M2 body 竄改 | synth 某 finding 正文≠來源，ID 同 | 0(漏) | ≠0 | ✓ | Task 6.1(Oracle④) |
  | M3 純prose無ID | 來源檔無 `## ID` heading | **1(STRICT 已擋，v0 已綠)** | ≠0(守不退化) | ✓(守衛) | Task 2.1(守；**非先紅案**) |
  | M4a 空殼heading | `## GROK-R1-P0-01` 後無 `**斷言**` | 0(漏) | ≠0 | ✓ | **Task 2.1**(TC4) |
  | M5 缺欄ID變體 | `## GROK-01`(缺 ROUND/SEVERITY) | 0(漏) | ≠0 | ✓ | Task 2.1 |
  | M6 跨源dup | a.md+b.md 同 `## CODEX-R1-P0-01` | 0(漏) | ≠0 | ✓ | Task 2.1 |
  | M7 late檔 | freeze 後改 source（sha≠lock） | 0(漏) | ≠0 | ✓ | Task 3.1 |
  | M8 跨round | 目錄混入他 round 舊檔 | 0(漏) | ≠0 | ✓ | Task 3.1 |
  | M9 README汙染 | sources 放 `README.md`（非 `*-<family>.md`） | 0(漏) | ≠0 | ✓ | Task 3.1 |
  | **M4b 假body+sha對** | 假正文+digest 對 | — | **out-of-scope** | ✗ | 僅 Oracle④/委員語意（非機械門檻） |

- 實作要點（≥3，含偽碼；TC2/TC5/TC18/TC20/TC25）：
  1. `_make_session(tmp_path, sources: dict[str,str], synth: str, roster: list[str]) -> Path`：建 `sources/`、寫各 `<name>-<family>.md`、寫 `sources.lock`（schema 見 Task 3.1）、寫 `synth.md`；回 session dir。
  2. 每案一函式，**命名分明**（TC20）：`test_m1_missing_source`/`test_m2_body_tamper`/`test_m3_prose_no_id`/`test_m4a_empty_shell`/`test_m5_malformed_id`/`test_m6_cross_dup`/`test_m7_late_file`/`test_m8_cross_round`/`test_m9_readme_pollution`（+ `test_m4b_fake_body_out_of_scope` 標 OOS，不 assert 機械抓到）。
  3. **單一主路徑 assert = predicate（TC2/TC25；封極性契約 codex P0-02）**：機械案 post 期望一律 predicate **`rc != 0`**（非特定整數值，避免歧義）：
     ```python
     rc = run_completeness(session)   # subprocess → returncode
     assert rc != 0, f"{case} 應被機械擋"   # 8 先紅案(M1,M2,M4a,M5,M6,M7,M8,M9) v0 下 rc==0 → assert 失敗=紅
     ```
     - **8 先紅案**（M1,M2,M4a,M5,M6,M7,M8,M9）：v0 `rc==0` → `assert rc != 0` 失敗=紅（禁 `pytest.mark.xfail`）。
     - **M3（守衛，非先紅）**：v0 STRICT=1 已 `rc==1` → `assert rc != 0` **v0 已綠**；其斷言=「Task 2.1 後仍守不退化 vacuous」（迴歸守衛，B1 即綠）。
     - **M4b（OOS）**：不 assert 機械抓到，只記 receipt。
  4. red-receipt 每案 schema（TC26/codex P1-09 逐案權威）：`{name, cmd, fixture_path, stdout(截斷), observed_rc_v0, expected_predicate:"rc!=0", is_mechanical, date, commit}`，覆蓋 9 機械案（M4b `is_mechanical=false`）。
- 修改檔案：`tests/governance/mutation_red/test_completeness_mutations.py`（新建）+ `tests/governance/mutation_red/conftest.py`（`_make_session`）+ `pytest.ini`（加 `norecursedirs = */mutation_red`，B6 移除；TC13/codex P1-12）。既有 caller：無。
- 不可做：不預先改 `completeness_check.sh`（本批產物=8 案紅+M3 守綠）；不用 XFAIL；不把 red-receipt 當「跳過 pytest assert」的替代。
- 邊界（≥2）：M3 純prose→空 ID 集合→v0 RC=1（守不退化，**非空目錄**）；M4b→標 OOS 不 assert 機械抓到。
- 風險緩解：⊘。
- 驗證：`pytest tests/governance/mutation_red -q` → **8 先紅案 assert 紅**（M1,M2,M4a,M5,M6,M7,M8,M9 v0 `rc==0`→`assert rc!=0` 失敗）+ **M3 守衛已綠**（v0 `rc==1`）；`pytest.ini` 加 `norecursedirs = */mutation_red` 後 `pytest tests/governance -q` → **仍 151 passed**（config 排除，不入預設 collection）；`mutation-red.receipt` 9 機械案齊。
- **存活至**：永久（迴歸網，B6 併入主 suite）。**覆蓋風險**：無（只增）。

**B1 派工 prompt**：`前置=v0 completeness_check.sh(574efba);建 tests/governance/mutation_red/{test_completeness_mutations.py,conftest.py}+pytest.ini norecursedirs;依內嵌矩陣寫 8 先紅案裸 assert rc!=0(禁xfail)+M3 守衛(v0已綠)+M4b OOS+red-receipt;驗證=pytest tests/governance/mutation_red -q 呈 8 紅+M3 綠 & pytest tests/governance -q 仍151。預期:B1 無機械 nodeid 轉綠。`

## Phase 2 — canonical ID + 範本（目標：條碼可靠抽取 + M4a 空殼機檢；轉綠 M4a/M5/M6/M3-守）
### Task 2.1 — canonical ID schema（含 digest + body 機檢）+ DEGRADE 命名空間 + 範本
- SPEC ref：Phase 2 Task 2.1（C1/C9/C15/R1；TC4/TC5/TC14/TC16/TC18）　目標：`extract_heading_ids` 升級 + `_validate_finding_body` + digest + DEGRADE 第二命名空間。
- 輸入 / 輸出：輸入=B1 紅測試；輸出=`templates/COMMITTEE_FINDING_TEMPLATE.md`（新建）+ `scripts/completeness_check.sh` 升級。
- 實作要點（≥3，含偽碼+真實函式名 TC18）：
  1. **升級既有** `extract_heading_ids()`（現 grep `HEADING_LINE_RE`）：加 ID 正則 `^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$` 驗證；FAMILY allowlist `{CODEX,COMPOSER,GROK,CLAUDE,AGY}`；不匹配 → collect 為 invalid（exit 1）。
  2. 新 `_validate_finding_body(file)`（TC4，M4a owner）：每 `## <ID>` heading 後至下個 heading 間須**同時**含 `**斷言**` 與 `**碼證**`；缺任一 → exit 1（偽碼；codex P1-11 補碼證欄）：
     ```bash
     awk '
       /^## [A-Z]+-R[0-9]/{ if(id && !(seen_assert && seen_code)) exit 1; id=$0; seen_assert=0; seen_code=0 }
       /\*\*斷言\*\*/{seen_assert=1}
       /\*\*碼證\*\*/{seen_code=1}
       END{ if(id && !(seen_assert && seen_code)) exit 1 }'
     ```
  3. 第四欄 `**來源摘要**: <src_path>#sha256[:12]`（或 harness 注入 `source_digest:`，TC14）；缺 digest 的 P0/P1 → exit 1。
  4. DEGRADE 第二命名空間正則 `^##[[:space:]]+DEGRADE-[A-Z]+-[0-9]{2,}[[:space:]]*$`（TC9）：**不進 union 分母**，只供 Task 5.1 degrade 狀態機；`extract_heading_ids` 須排除 DEGRADE-* 不當 invalid。
  5. severity 全級 missing→FAIL（只排序不免檢）。範本白名單改動（TC16）：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 加「finding 用 canonical 四欄格式」段；`docs/MULTI_AGENT_ORCHESTRATION.md` 派工段加引用行（禁掃全 repo）。
- 修改檔案：`scripts/completeness_check.sh`（`extract_heading_ids` 升級 + 新 `_validate_finding_body`/`_validate_digest`）、`templates/COMMITTEE_FINDING_TEMPLATE.md`（新建）。既有 caller：completeness_check 現呼叫點。
- 不可做：不允許 `UNION-*` 改名繞過；不掃全 repo 改 prose。
- 邊界（≥2）：`GROK-01`→invalid exit 1（M5）；合法 `## DEGRADE-GROK-01`→不觸發 invalid（TC9）；同檔重複 ID→FAIL（TC14/COMPOSER-P2-02）。
- 風險緩解：R1。
- 驗證：`pytest tests/governance/mutation_red -q -k "m3 or m4a or m5 or m6"` 轉綠/守綠；新增 `tests/governance/test_completeness_id.py::{test_missing_digest_p0_fails,test_source_digest_injection,test_degrade_namespace_not_invalid,test_same_file_dup_fails}` 綠（`test_source_digest_injection`=TC14/COMPOSER-P2-03 harness 注入 `source_digest:` 替代欄）；`pytest tests/governance -q` ≥151。
- **存活至**：永久。**覆蓋風險**：無。

## Phase 3 — 來源集合鎖定 + gate 掛載（目標：少交/竄改來源被出口擋；轉綠 M1/M7/M8/M9/symlink/lock/gate_incomplete）
### Task 3.1 — physical per-round 目錄 + lock schema + 拒收 + 拒 ADVISORY_ONLY
- SPEC ref：Phase 3 Task 3.1（C8/C12/C17/R2；TC6/TC14/TC15/TC24）　目標：sources.lock 鎖定 + 拒收非法 + 缺席硬狀態機 + 拒 advisory flag。
- 輸入 / 輸出：輸入=B2 ID 解析；輸出=`scripts/completeness_check.sh`（讀 lock）+ **lock writer helper**（TC15：放 `scripts/gate.sh` dispatch 主體或新 `scripts/write_sources_lock.sh`，**非** dispatch.sh 薄 wrapper）+ runtime `handoffs/reconcile/<session>/{sources/,sources.lock}`。
- 實作要點（≥3，含 schema）：
  1. **`sources.lock` schema（JSON，TC12/TC22）**：`{"version":1,"session_id":str,"expected_roster":[fam...],"sources":[{"realpath":str,"sha256":str,"family":str}](sorted by realpath),"freeze_ts":iso8601,"closure_state":"FROZEN"}`。**version 不符 → 拒發 exit 1**（TC14/GROK-P1-06）。
  2. completeness 讀 lock（新 `_load_lock`/`_check_roster`）；**禁 argv/env 覆寫**；正式路徑**主動拒** `COMPLETENESS_ADVISORY_ONLY`（TC24）：`[ -n "${COMPLETENESS_ADVISORY_ONLY:-}" ] && { echo "FAIL: advisory-only 逃生口禁用" >&2; exit 1; }`（僅 `tests/governance/` 隔離 env 例外）。
  3. 拒收（偽碼）：對每 source `realpath`，`[[ $rp != $sessdir/sources/* ]]`（子目錄/root 外/symlink 出目錄）→ exit 1；`[[ $f != *.md || $(basename) != *-<family>.md ]]`（M9 README）→ exit 1；`sha256(f) != lock.sha256`（M7 late）→ exit 1。
  4. **缺席硬狀態機（無第三態，TC8）**：`roster 缺檔 ∧ 無合法 DEGRADED_PENDING`（Task 5.1 提供）→ **exit 1**（B3 階段 degrade 尚未實作 → B3 只測「缺檔→exit 1」，合法降級路徑測試在 B4/Task 5.1）。
- 修改檔案：`scripts/completeness_check.sh`（`_load_lock`/`_check_roster`/`_validate_sources`/`_reject_advisory_flag`）、`scripts/gate.sh` dispatch 主體或 `scripts/write_sources_lock.sh`（新建 lock writer）。既有 caller：dispatch.sh 透傳（不破 token 流程）。
- 不可做：**分工鐵律**——腳本只鎖目錄+跑檢查；不接管派工/重試/降級；不把 roster 判定交回 LLM；lock writer 不放 dispatch.sh wrapper（TC15）。
- 邊界（≥2）：`outside-link.md` symlink→拒收 exit 1；空目錄/lock 缺/version 不符→exit 1（非 vacuous）。
- 風險緩解：R2（最關鍵）。
- 驗證：`pytest tests/governance/mutation_red -q -k "m1 or m7 or m8 or m9 or symlink"` 轉綠；`test_completeness_lock.py::{test_empty_dir_not_vacuous,test_lock_version_mismatch_fails,test_advisory_only_rejected}` 綠；≥151。
- **存活至**：永久。**覆蓋風險**：無。

### Task 3.2 — 現有高風險派實作閘掛 completeness（**gate.sh 無 final 子命令**；TC6）
- SPEC ref：Phase 3 Task 3.2（C6/R2；TC6）　目標：在**現有** reconcile 核可咽喉加 completeness，非虛構 `gate.sh final`。
- 輸入 / 輸出：輸入=Task 3.1 lock；輸出=`scripts/gate.sh` L328-344 區塊擴充。
- 實作要點（≥3，行為錨點 TC6）：
  1. **錨點=`scripts/gate.sh` 現有 `if [ -n "${spec}" ]` 高風險派實作區塊（~L328-344），`reconcile_stamps_check.sh` 成功之後、發 token 之前**（無 `final` 子命令；completeness 掛在拒發實作 token 的同一裁決點）。
  2. 新 `_run_completeness_gate(reconcile_file)`：從 reconcile 檔同目錄或固定 `handoffs/reconcile/<session>/sources.lock` 解析 lock 路徑（session 由 --reconcile 檔路徑推導）；`bash completeness_check.sh --lock <lock>`；`rc=$?`。
  3. `rc==1` → 拒發 token exit 1；`rc==3`（DEGRADED_PENDING）→ 拒發 final token exit 1（degrade 非 final）；`rc==0` → 續發。completeness 腳本不存在 → 拒發（fail-closed）。
- 修改檔案：`scripts/gate.sh`（`if [ -n "${spec}" ]` 區塊加 `_run_completeness_gate` 呼叫，緊接 reconcile_stamps_check 之後）。既有 caller：gate.sh 現有 stamp 檢查（不改 H1-H7 通用邏輯，TC12）。
- 不可做：不新增 `final` 子命令；不改 reconcile_stamps_check 本身；不改 PreToolUse gate_check.sh 判 token 邏輯（僅確認新拒發碼不誤判，TC23）。
- 邊界（≥2）：mock lock+缺 ID → 派實作 gate exit 1；lock 標 DEGRADED_PENDING → 拒發 final。
- 風險緩解：R2/C6。
- 驗證：`test_gate_impl_dispatch.py::{test_gate_rejects_incomplete_sources,test_gate_rejects_degraded_final}` 綠（**後者 mock DEGRADED，實 degrade 狀態機在 B4；B3 用固定 rc=3 stub 檔驗 gate 反應**，TC8）；≥151。
- **存活至**：永久。**覆蓋風險**：無。

**B3 派工 prompt**：`前置=B2 綠;實作 Task3.1 lock/roster/拒收/拒advisory + Task3.2 gate.sh:328-344 掛 _run_completeness_gate(reconcile_stamps_check 後);驗證=mutation_red -k "m1|m7|m8|m9|symlink" 轉綠 + lock/gate 具名測試綠 + ≥151。預期仍紅:selfcheck/degrade/oracle nodeid。`

## Phase 4 — 派工前自我體檢（目標：advisory 自檢+write-once receipt；轉綠 selfcheck/first_draft）
### Task 4.1 — self-check advisory + immutable 初稿 receipt（write-once）
- SPEC ref：Phase 4 Task 4.1（C13/R3；TC12 序列先）　目標：`--self-check` advisory + write-once receipt + advisory/error 極性分離。
- 輸入 / 輸出：輸入=B3 lock；輸出=`scripts/completeness_check.sh`（`--self-check` 分支）+ `handoffs/reconcile/<session>/{first_draft.sha256,coverage.json}`。
- 實作要點（≥3）：
  1. `--self-check` 分支：列漏 ID，`ADVISORY_MISSING` → exit 0（不阻塞）；執行/輸入錯誤（檔缺/lock 壞）→ exit 1（不吞，TC7 極性分離）。
  2. write-once receipt（偽碼）：`[ -f first_draft.sha256 ] && { echo "FAIL: 初稿 receipt 已存在不可回寫" >&2; exit 1; }`；寫 `coverage.json{"missing_ids":[],"draft_sha256":str,"id_coverage":float}`。
  3. 最終稿由**獨立出口重跑**（Task 3.2 gate，非自檢那次）；績效=post-review residual（Oracle⑤，Task 6.1）非 self-check PASS。
- 修改檔案：`scripts/completeness_check.sh`（`_self_check`/`_write_first_draft_receipt`）。**共改檔序列（TC12）：B4 內 4.1 先 commit，5.1 rebase 後接**。既有 caller：主委派工流程（文件）。
- 不可做：不得用 self-check PASS 當「省委員」理由。
- 邊界（≥2）：自檢 100% 仍不得跳語意審；self-check 輸入失敗→exit 1（不當 advisory 吞）。
- 風險緩解：R3。
- 驗證：`test_completeness_selfcheck.py::{test_selfcheck_advisory_exit0,test_first_draft_write_once_tamper_fails,test_selfcheck_input_error_exit1,test_deleted_receipt_downstream_still_fails}` 綠（末者=TC14/COMPOSER-P1-05：刪 receipt→獨立出口仍 FAIL）；≥151。
- **存活至**：永久。**覆蓋風險**：無。

## Phase 5 — 降級 SOP（目標：合法降級=DEGRADED_PENDING exit3；轉綠 degrade/min_families/degraded_final）
### Task 5.1 — DEGRADED_PENDING 狀態機（exit 3，非字串灰態）
- SPEC ref：Phase 5 Task 5.1（C9/R4；TC7/TC14）　目標：合法降級狀態機 + min≥2 + 顯式 DEGRADE 事件 + 數值 exit 契約。
- 輸入 / 輸出：輸入=B3 lock、B4 self-check（序列後）；輸出=`scripts/completeness_check.sh`（degrade 分支）+ `handoffs/reconcile/<session>/degrade.json`。
- 實作要點（≥3，數值介面 TC7）：
  1. **exit 契約**：合法降級 → **`exit 3`** + stdout 唯一 token `DEGRADED_PENDING`（**禁 RC=0+字串灰態**）；gate（Task 3.2）以 `rc==3` 拒 final。
  2. **禁 `waived:/skip` 字串**；`min_families<2` → 硬停 exit 1；`P0/P1 不得 waiver`。
  3. degrade receipt schema `degrade.json`：`{"absent_family":str,"reason":str,"approver":str,"expiry":iso8601,"remediation_owner":str,"round":int}`；缺席家族須顯式 `## DEGRADE-<FAM>-01`；連續 2 輪同家族（`round≥2`）→ 升級使用者（AskUserQuestion 阻塞，主委端流程）。
- 修改檔案：`scripts/completeness_check.sh`（`_degrade_state`/`_check_degrade_event`）。**B4 序列後（承 4.1）**。既有 caller：Task 3.2 gate（已掛）。
- 不可做：不提供任何 `--skip-completeness`/`ALLOWLIST`/`COMPLETENESS_ADVISORY_ONLY` 逃生口。
- 邊界（≥2）：grok 缺席 ∧ 無 `## DEGRADE-GROK-01`→exit 1；min_families=1→硬停 exit 1；合法降級（2 家+DEGRADE 事件+receipt）→exit 3。
- 風險緩解：R4（防重蹈 H3）。
- 驗證：`test_completeness_degrade.py::{test_absent_without_degrade_event_fails,test_min_families_one_hardstop,test_p0_waiver_rejected,test_legal_degrade_exit3,test_degraded_cannot_final_stamp}` 綠（`test_legal_degrade_exit3`=TC14/COMPOSER-P2-05 正向）；≥151。
- **存活至**：永久。**覆蓋風險**：無。

**B4 派工 prompt**：`前置=B3 綠;序列:Task4.1(--self-check+write-once receipt)先 commit → Task5.1(degrade exit3 狀態機)rebase 接,兩者共改 completeness_check.sh;驗證=selfcheck/first_draft/degrade/min_families/degraded_final nodeid 轉綠 + ≥151。`

## Phase 6 — 驗收 5 oracle + 水位量測（目標：5 oracle 1:1 nodeid 可證偽 + 90% 非 vacuous）
### Task 6.1 — 5 獨立 oracle（1:1 nodeid）+ retrofit canonical ID 量 90%
- SPEC ref：Phase 6 Task 6.1（C4/C5/C7/C10/R5/R6；TC9/TC10/TC12/TC13）　目標：5 oracle 各具名 nodeid + committee_accepted_ids schema + retrofit canonicalizer + id_coverage≥90%。
- 輸入 / 輸出：輸入=B2-B4 機制；輸出=`tests/governance/test_completeness_oracles.py`（5 oracle 分組）+ `scripts/replay_convergence_coverage.sh` + `handoffs/reconcile/<session>/{coverage.json,committee_accepted.json}`。
- 實作要點（≥3；TC9/TC10）：
  1. **5 oracle 1:1 nodeid + 契約（TC9；codex P1-10 補 fixture/輸出/極性，恰 5 個無幻影第六）**：

     | Oracle | nodeid | fixture | 輸出/斷言 | 極性 |
     |--------|--------|---------|-----------|------|
     | ① ID completeness | `test_oracle1_id_completeness` | synth 漏 1 union ID | `id_coverage<1.0` | rc≠0 |
     | ①b P0 不稀釋 | `test_oracle1_p0_not_diluted` | 總 92% 但含 1 P0 missing | `p0p1_missing≠[]` | rc≠0（**屬 Oracle① 子斷言，非第六 oracle**） |
     | ② invalid/dup/unknown | `test_oracle2_invalid_dup_unknown` | synth 多 unknown ID/跨源 dup | 拒收 | rc≠0 |
     | ③ closure/late/round | `test_oracle3_closure_late_round` | lock freeze 後 late 檔 | sha 不符 | rc≠0 |
     | ④ body hash 機械 | `test_oracle4_body_hash_mechanical`（純 byte 級，不含語意，不依賴 Phase 7） | synth body≠source | body-hash 不符 | rc≠0 |
     | ⑤ post-review residual | `test_oracle5_post_review_residual` | `committee_accepted.json` 缺 1 ID | `residual>0` | rc≠0 |
  2. **`committee_accepted_ids` producer/schema（TC9）**：委員語意審後（Phase 7）產 `committee_accepted.json{"accepted_ids":[...]}`；Oracle⑤ residual=`|union_ids \ accepted_ids|`，>0 → FAIL。**B5 階段用固定 fixture committee_accepted.json 驗 oracle⑤**（Phase 7 charter 在 B6）。
  3. **retrofit canonicalizer（TC10）**：`replay_convergence_coverage.sh` 對 2 檔（**寫死**：`handoffs/20260722-ic-map-WHOLEMAP-v2.md` + `handoffs/20260722-pipeline-design-review-UNION.md`）：finding 單元=`## heading` 至下個 heading；retrofit **只允許新增 `## FAM-R1-Pn-NN` heading 行**；body-hash canonicalizer=strip heading-ID 行後正規化換行再 sha256（**digest=原始 pre-retrofit 內容 hash，避免整檔 sha 循環**）。分母 `id_coverage=|synth∩union|/|union|`（union 空→守衛不算 PASS）；**P0/P1 missing 獨立 hard gate（不被比例稀釋）**；PASS 下限 90%；`coverage.json{session,union_size,synth_size,coverage,p0p1_missing[]}`。
- 修改檔案：`tests/governance/test_completeness_oracles.py`（新建，5 nodeid）+ `scripts/replay_convergence_coverage.sh`（新建）。既有 caller：無。
- 不可做：不得 aggregate 比例掩蓋 P0/P1 缺漏；不得改回放目標檔正文語意（只加 heading）。
- 邊界（≥2）：某輪 P0 missing 但總 92%→仍 FAIL；union 空（分母 0）→不算 PASS。
- 風險緩解：R5/R6。
- 驗證：`pytest -q` 5 oracle nodeid（`test_oracle1_id_completeness`..`test_oracle5_post_review_residual`）+ `test_oracle1_p0_not_diluted`（Oracle① 子斷言，非幻影第六）+ `test_retrofit_body_hash_preserved` 全綠（exit 0）；`replay_convergence_coverage.sh` 兩檔 retrofit 後 `id_coverage` 非 vacuous 可算；`pytest tests/governance -q` ≥151。
- **存活至**：永久。**覆蓋風險**：無。

**B5 派工 prompt**：`前置=B2+B3(+B4 degrade oracle)綠;實作 5 oracle 1:1 nodeid + committee_accepted.json schema(fixture) + replay_convergence_coverage.sh(2 檔寫死,canonicalizer strip-ID hash);驗證=5 oracle 綠 + coverage≥90% 非 vacuous + P0 不稀釋。`

## Phase 7 — 委員語意審 charter（目標：語意 stamp 順序在機械 PASS 後 + committee_accepted producer；轉綠 semantic_stamp）
### Task 7.1 — 委員語意審範本 + fresh=NONE 收斂 + committee_accepted 產出
- SPEC ref：Phase 7 Task 7.1（C14；TC9/TC13/TC14）　目標：語意 charter（禁列 ID）+ 行為 oracle（順序不可逆）+ 產 committee_accepted.json + 解除 mutation_red exclude。
- 輸入 / 輸出：輸入=B2/B3/B5；輸出=`templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md`（新建）+ 委員產 `committee_accepted.json`（餵 Oracle⑤）。
- 實作要點（≥3）：
  1. charter 明訂委員只審「講水/降級/錯併」語意層，**禁列漏掉的 ID**（那是 Task 4 的活）；產 `committee_accepted.json{accepted_ids[]}`。
  2. fresh review=NONE 新 finding → 收斂蓋章（**正向路徑 TC14/GROK-P1-09/COMPOSER-P1-06**：`test_fresh_none_allows_final_stamp`）。
  3. 順序=機械層（Task 3.2 gate）PASS 在前、語意 stamp 在後（行為 oracle）；**解除 B1 的 mutation_red exclude**（TC13）：移除 `--ignore`／marker，`mutation_red` 併入主 `pytest tests/governance -q`，新 nodeid 全綠計入。
- 修改檔案：`templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md`（新建）+ `tests/governance/test_completeness_semantic.py`（`test_semantic_stamp_after_completeness`/`test_fresh_none_allows_final_stamp`）+ `pyproject.toml`/`pytest.ini`（解除 mutation_red exclude，TC13）。既有 caller：無。
- 不可做：委員不得代替機械層找掉 ID（防退化）。
- 邊界（≥2）：機械層未 PASS→委員不得蓋 final（順序不可逆）；委員只列 missing ID 無語意→charter 判非法。
- 風險緩解：⊘。
- 驗證：`grep -c "禁列.*ID\|只審語意" templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md` ≥1（smoke）；`pytest -q` → `test_semantic_stamp_after_completeness`、`test_fresh_none_allows_final_stamp` 綠（exit 0）；`pytest tests/governance -q | grep -c xfail`=0 且 mutation_red 併入後全綠（TC13）。
- **存活至**：永久。**覆蓋風險**：無。

**B6 派工 prompt**：`前置=B5 綠;建 COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md(禁列ID/只審語意)+committee_accepted 產出+行為 oracle;解除 mutation_red exclude 併主 suite;驗證=semantic/fresh_none 綠 + grep charter + xfail=0 + 全 suite 綠。`

---

## 追溯表（100% SPEC 覆蓋自檢；TC11 修正）
- **9 Task**：Phase0.1(DONE receipt 豁免)/1.1→B1/2.1→B2/3.1+3.2→B3/4.1→B4先/5.1→B4後/6.1→B5/7.1→B6 ✓
- **9 機械 mutation 案 + M4b OOS**：全落 Task 1.1 內嵌矩陣（TC11 修正計數：**9 機械案 + M4b out-of-scope**，非「8+1」）✓
- **5 oracle**：Task 6.1 各 1:1 nodeid（`test_oracle1`…`test_oracle5`）✓
- **C1-C17 逐項→Task（TC11 補全）**：C1→2.1｜C2→1.1｜C3→**§0 禁 bypass + 5.1 exit3 契約**（TC11 補）｜C4→6.1｜C5→6.1 canonicalizer｜C6→3.2｜C7→6.1 Oracle④去 fwd-dep｜C8→3.1 缺席狀態機｜C9→2.1 DEGRADE 命名空間+5.1｜C10→6.1 Oracle⑤+committee_accepted｜C11→1.1 M4a/M4b｜C12→3.1 lock schema｜C13→4.1 write-once｜C14→7.1 charter+3.2 順序｜C15→2.1 白名單｜C16→**0.1 具名 fixtures**（TC11 補）｜C17→3.1+1.1 M9 ✓
- **R1-R6**：R1→2.1｜R2→3.1/3.2｜R3→4.1｜R4→5.1｜R5→6.1｜R6→6.1 ✓
- **合計**：9 Task / 9 機械案+M4b OOS / 5 oracle / 6 批次 / C1-C17 全對應 / R1-R6 全對應；0 遺漏。

## Frozen 前 handoff
`SPEC=docs/CONVERGENCE_METHOD_SPEC.md TODO=docs/CONVERGENCE_METHOD_TODO.md FOCUS=冷啟動深度(偽碼/nodeid/gate真實錨點)+B1紅gate+範圍紀律`。三家（含 codex REJECT 方）閉合複驗 TC1-TC26 關閉後才 Frozen。未過=**Internal Frozen**。
