# Governance Harness P0 修補 TODO（v2.2；基於 docs/GOVERNANCE_HARNESS_P0_SPEC.md v3；2026-07-24）

> 冷啟動執行端(Grok)不需讀其他檔即可逐 Task 寫碼。SPEC 4 洞=V-A/B/C/M。
> **v2 變更（收 TODO 審 T1-T5）**：T1-T5 見下；**v2.1 再收 closure R2**（`handoffs/reconcile/p0todo-closure-r2/synth.md`）：H1 Task 3.1+4.1 改「最終控制流 hoist（刪整個 L480-527 if…fi + L451 後加 hoisted 區塊）」非刪半截行號（codex 證 `sed 480,492d|bash -n` rc=2）；H2 mutation 測試修（call-count==1 用非 waived adversarial；V-M skip 偵測用 waived impl；未刪舊塊→high call-count==2）；H3 淘汰 impl adversarial-only fallback + fixture 遷移。

## §0 全域規則與約束
- **範圍**：只改治理腳本 `scripts/gate.sh`、`scripts/verify_task_provenance.py` 及 `tests/governance/`；**不碰** `momentum/`/`api/`/`data_cache/`。解耦 7 條與本任務無關（無跨 momentum↔api import）。
- **Logging/Error**：沿用腳本現有風格（bash `echo ... >&2` + `return/exit` 非零；python `return (rc, msg)`）。不新增 logger。
- **fail-closed 方向**：本任務把多處 fail-open 改 fail-closed；**任何不確定一律拒發（rc≠0），不得放行**。
- **防假綠（鐵律）**：不得放寬/刪除既有 `tests/governance/*` 斷言換綠。語義收緊使既有測試紅 → **遷移 fixture 對齊真實慣例（synth.md/帶 task）**，不放寬 gate。新斷言對應新拒發行為。diff 既有斷言驗收。
- **mutation 可證偽**：每支新測試須「revert 修法→轉紅」；提交前實跑 `pytest` 自證並貼 receipt（見各 Task 之驗收命令）。
- **P0 closure scope**：只修 V-A/B/C/M 四洞；**不宣稱** harness 端到端可信（殘留 V-D~I 另票）。

## §B 批次執行策略（依賴拓撲 → 3 批）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | Task 1.1（V-A） | 無 | 單檔 verify_task_provenance.py + 單測 | 小 |
| **B2** | Task 2.1 + 2.2（V-B + fixture 遷移） | 無 | 同改 gate.sh completeness 綁定 + 連動 fixture，須同批 | 中 |
| **B3** | Task 3.1 + 4.1（V-C + V-M） | 無（與 B1/B2 獨立） | **SPEC §R 明定 Phase 3+4 必須同一 commit**（同改 gate.sh stamp 觸發區塊） | 中 |
- **批次間 Gate**：每批獨立 `pytest tests/governance -q` 全綠 + 該批新測試 mutation 自證轉紅 + `bash -n scripts/*.sh` 語法 0。
- **B1/B2/B3 互相獨立**，可平行或依序；B3 內兩 Task 不可拆 commit。

### B1 派工 prompt（可直接複製）
> 前置：main 乾淨。實作 Task 1.1（見下）。驗收：`pytest tests/governance/test_stamp_no_task_rejected.py -q` 綠 + revert 修法後該測試轉紅 + `pytest tests/governance -q` 全綠。commit `fix(governance): V-A 無 task 戳記 fail-closed`。

### B2 派工 prompt
> 前置：main 乾淨。實作 Task 2.1+2.2。驗收：`pytest tests/governance/test_reconcile_target_bound_to_synth.py -q` 綠 + 遷移後 `pytest tests/governance -q` 全綠 + `grep -rn 'reconcile\.md' tests/governance` 僅剩非 gate-target 用途。commit `fix(governance): V-B --reconcile target 綁定 synth.md + fixture 遷移`。

### B3 派工 prompt
> 前置：main 乾淨。實作 Task 3.1+4.1（**同一 commit**）。驗收：`pytest tests/governance/test_low_risk_impl_requires_reconcile.py tests/governance/test_waived_adversarial_still_stamps.py -q` 綠 + 各 revert 轉紅 + `pytest tests/governance -q` 全綠。commit `fix(governance): V-C impl 一律驗 + V-M stamp 脫鉤 adversarial-waived`。

---

## Phase 1 — V-A 蓋章偽造 fail-open（完成後：無 task 戳記一律 FAIL）

### Task 1.1 — 缺 `task:` 的戳記一律 FAIL（無 grandfather）
- SPEC ref：Phase 1 Task 1.1　目標：`check_stamp_provenance` 無 `task:` 時回失敗。
- 輸入 / 輸出：輸入 stamp_line（str）+ reconcile_file（str）；輸出 `tuple[int, str]`（rc, msg）。
- 實作要點：
  1. 檔案 `scripts/verify_task_provenance.py::check_stamp_provenance`（現 L237-241）。
  2. 現碼：`task_match = STAMP_TASK_RE.search(stamp_line)`；`if not task_match: return 0, ""`。
  3. 改為：先查 legacy allowlist（無 task 者本就不在 allowlist，因 `_is_legacy_allowlisted_stamp` 對 task_id 做 `all()`，L203）；直接把 `if not task_match:` 分支改 `return 1, "ERROR: 戳記缺 task:<id>，無 provenance 不予採信（legacy 除外）"`。
  4. **不加 legacy 無 task 例外**（SPEC §A FACT-RECEIPT M4 已驗：29 條歷史無 task 戳記無 tests/scripts 引用；legacy allowlist 全帶 task）。
- 修改檔案：`scripts/verify_task_provenance.py::check_stamp_provenance`（L237-241 分支）。既有 caller：`reconcile_stamps_check.sh`（透過 check-stamp CLI）。
- 不可做：不動 `_is_legacy_allowlisted_stamp`；不改 `STAMP_TASK_RE`；不加密碼學簽章。
- 邊界：① 戳記**有** task 但無派工事件 → 維持既有 FAIL（走 L248-271，不受本改動影響）；② allowlist 帶 task 戳記（`20260701-VERIFYGATE-DELIB-RECONCILE.md` codex/composer）→ 維持 PASS。
- 風險緩解：⊘（已驗無 active 依賴）。
- **存活至**：永久常駐。　**覆蓋風險**：無。
- 驗證：新測試 `tests/governance/test_stamp_no_task_rejected.py`：
  - `test_no_task_stamp_rejected`：造三家無 task 的 APPROVED（body-hash 自算）→ `reconcile_stamps_check.sh` rc≠0。
  - `test_with_task_allowlist_still_passes`：現存 allowlist 戳記檔 → rc=0（防過度收緊）。
  - **mutation 自證**：把 L240 改回 `return 0, ""` → `test_no_task_stamp_rejected` 須轉紅（提交前實跑貼 receipt）。

### Phase 1 測試 + Gate
- 單元：上兩測。Gate：`pytest tests/governance -q` 全綠 + mutation 轉紅 receipt。

---

## Phase 2 — V-B target↔synth 未綁定（完成後：--reconcile 目標=synth.md 才驗）

### Task 2.1 — `--reconcile` 目標須 realpath == `${sessdir}/synth.md`
- SPEC ref：Phase 2 Task 2.1　目標：completeness 驗的檔=gate 收到的 --reconcile 檔。
- 輸入 / 輸出：`_run_completeness_gate` 收 `reconcile_file`；輸出 rc（0 過 / 1 拒）。
- 實作要點（**T4：檢查放 `--reconcile` 呼叫點，非共用函式內**；review codex-R1-P1-04）：
  1. **不改** `_run_completeness_gate` 函式本體（它被兩處呼叫：dispatch `--reconcile` 主路徑 L447、review adversarial-only fallback L505-510；改函式內會誤傷 review fallback）。
  2. 在 **dispatch `--reconcile` 主呼叫點**（L446-448 `*)` case 內、`_run_completeness_gate "${reconcile}"` **前**）插入 realpath 綁定檢查：
     ```bash
     # session-root 用與 _run_completeness_gate 共用的 _reconcile_sessdir（handoffs/reconcile/<第一層>），
     # **禁 dirname**（否則 --reconcile <sess>/nested/synth.md 比對 nested 自己而不拒，completeness 卻驗根 synth → 穿透）。
     _rp_target="$(realpath "${reconcile}" 2>/dev/null)"
     _sess="$(_reconcile_sessdir "${reconcile}")"; _rp_synth="$(realpath "${_sess}/synth.md" 2>/dev/null)"
     # 僅在「target 與 session-root synth 皆可 resolve 且不相等」時於此拒；
     # target 不存在 / session 無 synth → 交下游 _run_completeness_gate fail-closed（保留 classic/不存在訊息）。
     if [ -n "${_rp_target}" ] && [ -n "${_rp_synth}" ] && [ "${_rp_target}" != "${_rp_synth}" ]; then
       echo "ERROR: --reconcile 目標須為 session synth.md（防 target/synth 未綁定掉項）: ${reconcile}" >&2; exit 1
     fi
     ```
     > **F1 修正（code review CODEX-R1-P0-01）**：session-root 抽成 `_reconcile_sessdir` 共用函式（V-B 檢查 + `_run_completeness_gate` 都用），杜絕 dirname vs 根推導漂移的 nested 繞過。回歸測試 `test_nested_synth_target_rejected`（+mutation probe）。
  3. realpath 檢查僅加於 `--reconcile` 主呼叫點；**不改** `_run_completeness_gate` 本體，故其他呼叫點（如 impl adversarial-only completeness fallback，B3 前仍存在）不受此綁定。**U2（R3）**：不再宣稱有「no-spec review fallback」——現碼 L505-510 在 `if [ -n spec ]` 內，review（無 --spec）永不進入；B3 後整段淘汰。
  4. realpath 解析後比對（含 symlink 展開）。
- 修改檔案：`scripts/gate.sh` dispatch 段 `--reconcile` case（L446-448）。既有 caller：dispatch 主路徑。
- 不可做：不放寬 gate 遷就 fixture（fixture 改對齊，見 Task 2.2）；不改 completeness_check.sh；**不改 `_run_completeness_gate` 函式本體**。
- 邊界（**T4/U2 相容矩陣**）：① `--reconcile` 為 `waived:`/`stamped-waived:` → 呼叫端 case 已擋，不進本檢查（維持）；② symlink 指向 synth.md → realpath 展開後相等 → 放行；③ **無 `--reconcile` 的派工（如 `--template n/a:` review）→ 不進本檢查點，不被 realpath 綁定影響**（檢查僅置於 `--reconcile` 主呼叫點，非共用函式）。
- 風險緩解：Task 2.2 遷移既有 fixture。
- **存活至**：永久常駐。　**覆蓋風險**：無。
- 驗證：新測試 `tests/governance/test_reconcile_target_bound_to_synth.py`：
  - `test_dropped_target_rejected`：session synth 完整、`--reconcile` 指向缺項 dropped.md → `gate.sh dispatch` rc≠0。
  - `test_synth_target_passes`：`--reconcile` 指向 synth.md（完整）→ 通過本檢查（可停在下游檢查，證明本閘放行）。
  - `test_symlink_to_synth_passes`：symlink→synth.md → 放行。
  - `test_no_reconcile_dispatch_not_rejected_by_realpath`（**U2 回歸，order-independent**）：無 `--reconcile` 的派工（如 review `--template n/a:`）→ 不被 realpath 綁定拒發（通過 realpath 階段；證明檢查僅 scope 到 `--reconcile` 參數，非其他路徑）。
  - **mutation 自證**：移除 realpath 檢查 → `test_dropped_target_rejected` 轉紅。

### Task 2.2 — fixture 遷移（M3）
- SPEC ref：Phase 2 Task 2.2　目標：既有 `--reconcile …/reconcile.md` fixture 改指 synth.md。
- 實作要點（**T3：改「改指+保留」非「改名」**；review codex-R1-P1-03 + composer-R1-P1-01）：
  1. `grep -rn 'reconcile\.md' tests/governance` 列全。**gate-target 共 5 處/3 檔**（`test_gate_impl_dispatch.py:90,123`、`test_completeness_semantic.py:336,452`、`test_completeness_degrade.py:538`）；`test_verify_gate_b4.py` 的 `fake/real_reconcile.md` 是 `reconcile_stamps_check.sh` **直測非 gate-target**，**排除不動**。
  2. **⚠️ 禁「改名」**：這些 session **本來就已建 `synth.md`**（`test_gate_impl_dispatch.py:78,105`、`test_completeness_semantic.py:302`、`test_completeness_degrade.py:512`），把 `reconcile.md` rename 成 `synth.md` 會**覆蓋既有 synth 的 finding/degrade union**。
  3. 正解：把該 fixture 傳給 gate 的 `--reconcile` **參數值**由 `…/reconcile.md` 改指**既有的 `…/synth.md`**；刪除多餘的 `reconcile.md` 假檔（若其內容與 synth 相同/僅作 gate-target）。**不寫入、不覆蓋 synth.md 內容**。
  4. **不放寬既有斷言**；若某 fixture 本意測「非 synth 目標被拒」則改斷 rc≠0 並保留。
- 修改檔案：上列測試檔的 fixture 建置段（改 `--reconcile` 參數值 + 刪多餘假檔）。
- 不可做：不為過關刪除既有斷言；不改被測 gate 邏輯；**不覆蓋既有 synth.md 內容**。
- 邊界：① 遷移後既有攻擊/合法斷言 rc 不變；② 混用 reconcile.md 作**非** gate-target（純內容 fixture）者保留。
- **遷移守恆斷言**：遷移前後既有 synth.md body-hash **不變**（`shasum` 比對；防覆蓋 union），且既有 rc/coverage/degrade oracle 不變。
- 風險緩解：⊘。
- **存活至**：永久常駐。　**覆蓋風險**：無。
- 驗證：遷移後 `pytest tests/governance -q` 全綠；`grep -rn 'reconcile\.md' tests/governance` 僅剩非 gate-target 用途（人工確認每一處）。

### Phase 2 測試 + Gate
- Gate：Task 2.1 三測 + 全 suite 綠 + mutation 轉紅 + grep 確認。

---

## Phase 3 — V-C opt-in 缺口（依賴：與 Phase 4 **同 commit**）

### Task 3.1 + 4.1 — impl 派工（--spec）無論 risk 一律驗 reconcile+completeness+stamp；stamp 脫鉤 adversarial-waived（V-C + V-M）
> **T1/H1（最終控制流 hoist，非刪行段）** review codex-R2-P0-01/02 + composer-R2-P2-01/02。**兩 Task 同一 commit**。
- SPEC ref：Phase 3 Task 3.1 + Phase 4 Task 4.1。
- 輸入 / 輸出：dispatch 段讀 `${spec}`/`${reconcile}`/`${risk}`/`${adversarial}`；輸出發 token 或 `exit 1`。
- **現況控制流（實測；`sed -n '443,527p' scripts/gate.sh`）**：
  - `_comp_ran=0` + 通則 completeness case（L443-451，**已在 risk=high 外**，對所有 risk 跑；T4 realpath 加於此 case 的 `*)` 分支）。
  - `if [ "${risk}" = "high" ]`（L453）**內**含 `if [ -n "${spec}" ]`（L480-527）整塊：stamp 分支（L481-498，被 `case adversarial waived) skip` 包住＝**V-M bug**）+ adversarial-only completeness fallback（L505-514）+ 雙 waived 拒發（L515-526）。→ **這整塊巢狀在 high 內＝V-C bug**（low impl 完全不跑）。
- **實作＝把 impl 要求 hoist 出 risk=high 並簡化**（**用「最終結構」描述，禁按舊行號刪半截**）：
  1. **刪除整個** `if [ -n "${spec}" ]; then … fi` 區塊（現 L480-527，完整 if…fi，語法安全；`bash -n` 驗）。其功能（stamp/雙waived拒）由下方 hoisted 區塊承接；adversarial-only completeness fallback 因 impl 改「一律須顯式 --reconcile」而淘汰（見不可做）。
  2. **在通則 `esac`（L451）後、`if [ "${risk}" = "high" ]`（L453）前**插入 hoisted 區塊（對所有 risk）：
     ```bash
     # V-C：impl(--spec) 一律須顯式 session reconcile（不論 risk）；V-M：stamp 依 reconcile 非 waived 觸發，與 adversarial 無關
     if [ -n "${spec}" ]; then
       case "${reconcile}" in
         ""|waived:*|stamped-waived:*)
           # V-C：無顯式 reconcile → miss（fail-closed 累加，dispatch 尾拒發）；**不跑 stamp**
           miss reconcile "impl 派工(--spec)一律須顯式 session reconcile（不論 risk）"
           ;;
         *)
           # reconcile 非空且非 waived：completeness 已由通則(L443-451)跑過(T5)；此處只補 stamp
           export VERIFY_GATE_COMMITTEE_AUDIT_LOG="${AUDIT}"   # M1/R2：stamp provenance 讀正確 audit log
           _stamp_bin="${RECONCILE_STAMPS_CHECK_OVERRIDE:-${SCRIPT_DIR}/reconcile_stamps_check.sh}"
           bash "${_stamp_bin}" "${reconcile}" \
             || { echo "ERROR: impl reconcile 未獲委員核可。委員須 append RECONCILE-STAMP APPROVED。"; exit 1; }
           ;;
       esac
     fi
     ```
     > **U1（R3）**：stamp 放 `*)` 分支——waived/空 reconcile 只 `miss` 不跑 stamp（否則 stamp 收非法參數 + call-count 誤增）。
  3. **V-M 自然脫鉤**：stamp 現在只依 `-n spec` 且 reconcile 非 waived，**不再**被 `case adversarial waived) skip` 包住 → `--adversarial waived:` 不再跳過 stamp。
  4. **impl dispatch stamp 單一 caller**（hoisted 這一處）；adversarial 處理路徑另有自己的 stamp 呼叫（gate.sh L327/L336，見 U3），故**全域 `grep reconcile_stamps_check` 會 ≥2 處，不是驗收依據**——驗收依 U3 的「只計 arg==reconcile synth」。
  5. `following`/`impl:real` 等 template 值不影響——判定依 `-n "${spec}"`。保留 L528+ 高風險 template-spec 檢查不動。
- 修改檔案：`scripts/gate.sh` dispatch 段（刪 L480-527 完整區塊、L451 後加 hoisted 區塊）。既有 caller：`dispatch.sh`。**與 Task 2.1（T4 realpath）不同 commit**（Phase 2 vs Phase 3+4）。
- **fixture 影響（impl adversarial-only 淘汰）**：既有測試若有「impl(`--spec`) + `--adversarial` 但無 `--reconcile`」派工，改後會被 V-C `miss reconcile` 拒發。實作前 `grep -rn '\-\-spec' tests/governance` 逐一檢查帶 --spec 的 dispatch fixture：有 --reconcile 者不受影響；adversarial-only 者遷移為帶 `--reconcile <synth>` 或改斷 rc≠0（保留其「拒發」意圖）。全 suite 綠為驗收門檻。
- 不可做：**淘汰 impl 的 adversarial-only fallback**（impl 一律須顯式 `--reconcile`；既有「impl 用 --adversarial 承載無 --reconcile」派工須遷移為帶 --reconcile，見 fixture 遷移）；不對 review/consult（無 --spec）強制 reconcile 或 stamp（無 spec 不進本區塊，維持）；不移除 review 的 waived 語義。
- 邊界（**相容矩陣，用 spy 驗 call-count**）：① low impl（`--spec`+完整 synth reconcile）→ stamp call-count==1；② high impl 同 → ==1（防雙跑）；③ impl `--adversarial waived:` + 非 waived reconcile → stamp **仍==1**（V-M）；④ review（無 --spec，含 `--adversarial waived:`）→ stamp call-count==0；⑤ impl 無 --reconcile / `--reconcile waived:` → `miss`/拒發。
- 風險緩解：Phase 3+4 同 commit（§R）。
- **存活至**：永久常駐。　**覆蓋風險**：無。
- 驗證（`pytest tests/governance/test_low_risk_impl_requires_reconcile.py tests/governance/test_waived_adversarial_still_stamps.py`）：
  - 新測試 `tests/governance/test_low_risk_impl_requires_reconcile.py`：
    - `test_low_spec_no_reconcile_rejected`：`--risk low --spec X`（無 --reconcile）→ rc≠0。
    - `test_low_spec_waived_reconcile_rejected`：`--spec X --reconcile waived:` → rc≠0。
    - `test_low_spec_full_synth_passes`：`--risk low --spec X --reconcile <完整 synth>` + 真實 audit+3 戳記+無 override（§V helper）→ rc=0。
    - **mutation**：把 hoisted 區塊移回 `if risk=high` 內 → `test_low_spec_no_reconcile_rejected`（low）轉紅（low 不再被擋）。
  - 新測試 `tests/governance/test_waived_adversarial_still_stamps.py`（**stamp stub call-count oracle**；需 `GOVERNANCE_TEST_HARNESS=1`（否則 gate.sh:43-49 反 bypass 守衛拒 override）+ `RECONCILE_STAMPS_CHECK_OVERRIDE=<把每次呼叫的第一個參數 append 到計數檔的 stub>` + `COMPLETENESS_CHECK_OVERRIDE=/bin/true`）。**U3（R3）**：gate.sh 的 adversarial 處理路徑（L317-329，對非 `handoffs/*-ADV-<family>.md` 檔）也會呼叫 stamp → 斷言時**只計「參數 == reconcile synth 路徑」的呼叫次數**（隔離 hoisted impl stamp vs adversarial-processing stamp），或 adversarial fixture 用合規 `*-ADV-<family>.md` 命名避免額外呼叫：
    - `test_low_impl_nonwaived_adv_calls_stamp_once`：`--risk low --spec X --reconcile <synth 無戳記> --adversarial <真實檔>` → **call-count==1 且 rc≠0**。
    - `test_high_impl_nonwaived_adv_calls_stamp_once`：`--risk high --spec X …非 waived adversarial` → **call-count==1**（防雙跑；此為抓「未刪舊 L480-527」的 mutation oracle）。
    - `test_impl_waived_adv_still_calls_stamp`：`--spec X --reconcile <synth 無戳記> --adversarial waived:` → **call-count==1 且 rc≠0**（V-M：waived adversarial 不再跳 stamp）。
    - `test_review_no_spec_skips_stamp`：**無 --spec** + `--adversarial waived:` → **call-count==0**（review 維持）。
    - `test_impl_full_stamp_passes`：3 家 APPROVED 帶 task（真 stamp）→ rc=0。
    - **mutation**：(a) 把 stamp 觸發改回「`case adversarial waived) skip`」→ `test_impl_waived_adv_still_calls_stamp` 轉紅（call-count==0）；(b) 保留舊 L480-527 不刪（雙區塊並存）→ `test_high_impl_nonwaived_adv_calls_stamp_once` 轉紅（call-count==2）。

### Phase 3+4 測試 + Gate
- Gate：兩 Task 全測 + 全 suite 綠 + 各 mutation 轉紅 + **同一 commit**。

---

## §V helper（M1 正向 fixture 建置，供 Task 3.1/4.1；**T2 完整契約** review codex-R1-P0-02 + composer-R1-P1-03）
於 `tests/governance/conftest.py` 或測試檔內建 helper `make_impl_passing_session(tmp_path)`，**可複用** `test_verify_gate_b4._append_committee_dispatch`（L120-143 dispatch event schema）+ `mutation_red/conftest._make_session`（建 lock+sources）+ `scripts/reconcile_body_hash.sh`。逐步（缺一則正向 rc≠0）：
1. **session 路徑**：`sess=handoffs/reconcile/<uniq>/`（`_run_completeness_gate` 只認 `handoffs/reconcile/<session>/` 結構，L380-395）。
2. **sources/**：建 3 個 `sess/sources/<name>-{codex,composer,grok}.md`，各含 canonical `## <FAMILY>-R1-P0-01`（+`**斷言**`/`**碼證**` 防空殼）。
3. **sources.lock**：`write_sources_lock.sh --session sess --roster codex,composer,grok --mode discovery`（需 `GOVERNANCE_TEST_HARNESS=1`）；schema=version/session_id/expected_roster/sources[sha256/family]/freeze_ts/closure_state=FROZEN/mode。
4. **synth.md**：union 3 家 3 個 `## FAMILY-R1-P0-01` 逐字（body-hash 對得上 sources）+ 末尾 `## 戳記` 區段。
5. **body-hash**：`h=$(bash scripts/reconcile_body_hash.sh sess/synth.md)`（`## 戳記` 前內容雜湊）。
6. **3 家戳記**：於 `## 戳記` 後 append 3 行 `RECONCILE-STAMP: <fam> APPROVED <date> sha256:${h} task:<tid_fam>`，每家獨立 `tid`。
7. **audit log**：寫 `sess_audit`（或 gate 的 `${GATE_DIR}/audit.log`）3 條 `committee_dispatch`（`_append_committee_dispatch` 格式），每條 `task_id==tid_fam`、`output_path==sess/synth.md`、`output_sha256==h`（滿足 `_stamp_event_satisfies` L175-194）。
8. **gate wiring**：正向 gate 測試以 `GATE_DIR_OVERRIDE=<tmp gate dir>` 隔離，並確保 gate dispatch 內 `export VERIFY_GATE_COMMITTEE_AUDIT_LOG=${AUDIT}`（Task 3.1 已加）指向步驟 7 的 audit；**無** `RECONCILE_STAMPS_CHECK_OVERRIDE`/`COMPLETENESS_CHECK_OVERRIDE`（真跑）。
9. **驗收**：`gate.sh dispatch --risk low --spec <SPEC> --reconcile sess/synth.md …` → **rc=0**（無 override 實跑；helper 正確則 stamp+completeness 皆過）。
- **存活至**：永久常駐（tests/ helper）。　**覆蓋風險**：無。
- 驗證：`test_make_impl_passing_session_rc0`：獨立呼叫 helper → gate rc=0（證 helper 契約完整）。

## Frozen 前 handoff
`SPEC=docs/GOVERNANCE_HARNESS_P0_SPEC.md TODO=docs/GOVERNANCE_HARNESS_P0_TODO.md FOCUS=完整審查（fail-closed 正確性/回歸/mutation 可證偽/M1 helper 可行性）`
未過外部 adversarial review 前僅 Internal Frozen。
