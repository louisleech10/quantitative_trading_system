# Governance Harness P0 修補 — SPEC (v3)

> 來源 PLAN/診斷：`handoffs/20260724-REDTEAM-RECONCILE.md`（紅隊 26 findings）；SPEC 審 reconcile：`handoffs/reconcile/p0spec-review-r1/synth.md`（codex+composer 9 findings，completeness PASS 0 掉項）　|　日期：2026-07-24　|　對應 TODO：`docs/GOVERNANCE_HARNESS_P0_TODO.md`（SPEC 通過後生成）
>
> **v2 變更（收 SPEC 審 M1-M5）**：M1 V-C↔V-M 正向 fixture 須真實 audit+3 戳記；M2 裁決 adversarial-only fallback（僅 review 保留）；M3 枚舉 V-B fixture 遷移；M4 校正 legacy no-task 前提（無 grandfather，已驗 29 歷史戳記惰性）；M5 §A/§C/§R/§V 收口。
> **v3 變更（收 closure R2；兩家收斂單一議題）**：Task 3.1 補 impl 路徑呼叫 stamp 前 `export VERIFY_GATE_COMMITTEE_AUDIT_LOG`（CODEX-R2-P1-01 + COMPOSER-R2-P1-01；兩家「補此→APPROVE 進 TODO」）。

## §RISK 風險分級
- **大小**：大（改治理共用強制路徑 `gate.sh`，多處 fail-open→fail-closed，blast radius=往後每次派工）。
- **命中高風險原則**：(b) 跨模組/共用路徑；(c) 多 phase/難回退。**未命中 (a)/(d)**。
- **RISK-HIT 宣告**：
RISK-HIT: b,c
- **P0 closure scope（M5/防過度宣稱）**：本 SPEC 僅關閉紅隊 **4 個 P0 洞 = V-A/B/C/M**。**不宣稱** harness 端到端「0 掉項+蓋章不漏」已成立——殘留 MAJOR（V-D cx_run 旁路 / V-E brief-kind 自報 / V-F P1-1 只 grep / V-H roster 掉項 / V-I register-output / 有 task 假 provenance）另立票，見 `handoffs/20260724-REDTEAM-RECONCILE.md`。

## §A 假設與待使用者確認
- **FACT-RECEIPT V-A（fail-open 已復現）**：三家無 task: 的 APPROVED → `reconcile_stamps_check.sh` → `RECONCILE-STAMP PASS rc=0`（Claude 實跑 2026-07-24）。
- **FACT-RECEIPT V-A 回退面（M4，已驗安全）**：`grep -rE '^RECONCILE-STAMP:.*APPROVED' handoffs/ | grep -v task:` → 29 條歷史無 task 戳記；`grep -rl <這些檔> tests/ scripts/` → **0 命中**（無 active flow/fixture 依賴）；`_is_legacy_allowlisted_stamp` 對 task_id 做 `all()`（verify_task_provenance.py:203）→ legacy allowlist 全帶 task。結論：無 task→FAIL 不破壞任何 active 路徑，**不需 grandfather**（Claude 實跑 2026-07-24）。
- **FACT-RECEIPT V-B（synth 慣例）**：`completeness_check.sh` 支援 `--synth`（預設 session/synth.md）；`ls handoffs/reconcile/*/` → 真實 session 目標檔名恆=`synth.md`（Claude 實跑 2026-07-24）。
- **FACT-RECEIPT V-C/V-M（stamp/completeness 條件）**：`gate.sh:453` stamp 區塊在 `risk=high` 內、`:480` 套 `-n spec`、`:482` adversarial `waived:*) : ;;` 跳過整塊（Claude 讀碼 2026-07-24）；composer 實跑 `RECONCILE_STAMPS_CHECK_OVERRIDE=/bin/false`+`--adversarial waived:`+完整 synth → GATE PASS（stamp 未跑）。
- **FACT-RECEIPT V-C/V-M 正向 fixture（M1）**：V-C/V-M 修後正向路徑（低風險 impl 帶完整 synth）**同時觸發** completeness+stamp，故正向 fixture 須建：真實 audit log（`committee_dispatch` 3 家 task 事件）+ synth 內 3 家 `RECONCILE-STAMP APPROVED`（帶 task+body-hash+provenance）+ **不加任何 override** → 驗 rc=0（TODO 實作期建置並附 receipt）。
- **待確認：無**（修法方向由紅隊 PoC + 兩家 SPEC 審客觀決定；委員 re-review 覆核）。
- **已確認結果**：2026-07-24 使用者選「先修 4 條 P0」；「等 SPEC 完成後白話解釋」（AskUserQuestion + 對話）。

## §C 約束（合法邊界 — M2/M4 收口）
- **不改既有合法派工通過條件**：真跑 committee + 帶 task + synth 完整者仍須 PASS；只堵繞過。
- **legacy allowlist 語義不變**（`_is_legacy_allowlisted_stamp`，全帶 task）。
- **waived: / stamped-waived: 逐格語義（M4）**：
  | 派工類型 | `--reconcile` | 行為 |
  |---|---|---|
  | **impl（`--spec` 存在，含 template `following`/`impl:real`）** | 顯式 session synth（非 waived） | completeness+stamp **都跑**（不論 risk） |
  | impl | 缺 / `waived:` / `stamped-waived:` | **拒發**（impl 不得豁免 reconcile/stamp） |
  | **review（無 `--spec`，`--template n/a:`）** | 顯式 session synth | completeness 跑；stamp 不強制（review 不 gate impl） |
  | review | 缺（舊式 `--adversarial` 承載 reconcile，M2 fallback） | **保留合法**（僅 review）；completeness 對 adversarial foreach |
  | review | `waived:` / `stamped-waived:` | 合法逃生口（review 專用） |
- **本任務下游共用路徑**：`dispatch.sh`、`committee_dispatch`、既有 `tests/governance/*`（語義收緊須同步 fixture，不放寬 gate）。

## §G Golden / Baseline
移 §N 標 N/A（非數值/特徵/ML 路徑）。

## §P Phase 與依賴

### Phase 1 — V-A 蓋章偽造 fail-open（依賴：無）
**Task 1.1 — 缺 `task:` 的戳記一律 FAIL（無 grandfather）**
- 目標：`check_stamp_provenance` 無 `task:` 時不得 return 成功。
- 檔案：`scripts/verify_task_provenance.py::check_stamp_provenance`（L237-241）。既有 caller：`reconcile_stamps_check.sh`。
- 改法：`if not task_match:` 分支由 `return 0, ""` 改 `return 1, "ERROR: 戳記缺 task:<id>，無 provenance 不予採信"`。**不加 legacy 例外**（§A FACT-RECEIPT M4 已驗：legacy allowlist 全帶 task、29 條歷史無 task 戳記無 active 依賴）。
- **驗證（可證偽）**：V-A PoC（三家無 task APPROVED）改後 `reconcile_stamps_check.sh` → rc≠0；**正向**：現存帶 task 的 allowlist 戳記（`20260701-VERIFYGATE-DELIB-RECONCILE.md`）仍 rc=0。測試：`pytest tests/governance/test_stamp_no_task_rejected.py`（revert L240→`return 0` 應轉紅）。
- **邊界（≥2）**：① 戳記有 task 但無派工事件→維持既有 FAIL；② allowlist 帶 task 戳記→維持 PASS。
- **存活至**：永久常駐。
- **覆蓋風險**：無。
- 不可做：不動 legacy allowlist 判定邏輯；不加密碼學簽章。

### Phase 2 — V-B target↔synth 未綁定（依賴：無）
**Task 2.1 — `--reconcile` 目標須 realpath == `${sessdir}/synth.md`**
- 目標：completeness 驗的檔 = gate 收到的 `--reconcile` 檔。
- 檔案：`scripts/gate.sh::_run_completeness_gate`（L400-413）。
- 改法：解析 `reconcile_file` realpath 與 **session-root** `synth.md` realpath；皆 resolve 且不相等→拒。相等（或 target 不存在/無 synth 交下游 fail-closed）則照舊 `--lock`。**session-root 用 `_reconcile_sessdir`（`handoffs/reconcile/<第一層>`）與 `_run_completeness_gate` 共用，禁 `dirname`**——否則 `--reconcile <sess>/nested/synth.md` 比對 nested 自己而不拒、completeness 卻驗根 synth → 穿透（F1/code review CODEX-R1-P0-01）。（採唯一合法目標=session-root synth.md；§A FACT-RECEIPT V-B。）
- **驗證（可證偽）**：V-B PoC（synth 完整、`--reconcile` 指向缺項 dropped.md）改後 `gate.sh dispatch` → rc≠0；指向 synth.md 完整→rc=0。測試：`pytest tests/governance/test_reconcile_target_bound_to_synth.py`。
- **邊界（≥2）**：① `--reconcile` 為 `waived:`/`stamped-waived:`→不進本檢查；② symlink→realpath 解析後比對。
- **存活至**：永久常駐。
- **覆蓋風險**：無。
- 不可做：不放寬 gate 遷就 fixture。

**Task 2.2 — fixture 遷移（M3；枚舉 blast radius）**
- 目標：既有用 `--reconcile …/reconcile.md` 的 fixture 改指 `synth.md`，避免 Task 2.1 誤紅。
- 檔案（枚舉，實作期以 `grep -rn 'reconcile.md' tests/governance` 補全）：`tests/governance/test_gate_impl_dispatch.py`（L90-94/L123-124）、`test_completeness_semantic.py`、`test_completeness_degrade.py`。
- 改法：fixture 目標檔名 `reconcile.md`→`synth.md`（內容不變，含本體+戳記）；**不放寬斷言**。
- **驗證（可證偽）**：遷移後 `pytest tests/governance` 全綠；`grep -rn 'reconcile\.md' tests/governance` → 僅剩非 gate-target 用途。
- **邊界（≥2）**：① 遷移後既有攻擊/合法斷言 rc 不變；② 若某 fixture 本意測「非 synth 目標被拒」則保留並改為斷 rc≠0。
- **存活至**：永久常駐。
- **覆蓋風險**：無。
- 不可做：不為過關刪除既有斷言。

### Phase 3 — V-C opt-in 缺口（依賴：無）
**Task 3.1 — impl 派工（`--spec` 存在）無論 risk 一律要求顯式 reconcile+completeness+stamp**
- 目標：`risk=low`+`--spec` 不得跳過 completeness/stamp；**保留 review 的 adversarial-only fallback（M2）**。
- 檔案：`scripts/gate.sh` dispatch 段（現 stamp 區塊在 `if risk=high` L453 內）。
- 改法：新增獨立必檢區塊 `if [ -n "${spec}" ]`（不論 risk）：① `--reconcile` 必填且非 `""|waived:*|stamped-waived:*`，否則 `miss reconcile "impl 派工(--spec)一律須顯式 session reconcile"`；② 跑 completeness（Phase 2 已綁 synth）；③ **呼叫 stamp 前 `export VERIFY_GATE_COMMITTEE_AUDIT_LOG="${AUDIT}"`**（與既有 high-risk 路徑 gate.sh:464 一致，確保 stamp provenance 讀正確 audit log；否則低風險 impl 的 stamp 子行程 fallback 讀 `.claude/gate/audit.log`，M1 隔離正向 fixture 驗不到 rc=0）（CODEX-R2-P1-01 + COMPOSER-R2-P1-01）；④ 跑 stamp（Task 4.1）。**adversarial-only fallback（gate.sh:473-475）僅在無 `--spec`（review）時保留**（§C 矩陣）。
- **驗證（可證偽）**：V-C PoC（`--risk low --spec X` 無 `--reconcile`）改後→rc≠0；帶完整 synth reconcile+真實 audit+3 戳記→rc=0（M1 正向 fixture）。測試：`pytest tests/governance/test_low_risk_impl_requires_reconcile.py`。
- **邊界（≥2）**：① review 派工（`--template n/a:`、無 `--spec`）→不受此限，adversarial-only fallback 維持；② `--spec`+`--reconcile waived:`→拒。
- **存活至**：永久常駐。
- **覆蓋風險**：無。
- 不可做：不對 review/consult 派工強制 reconcile；不淘汰 review 的 fallback。

### Phase 4 — V-M adversarial waived 跳過 stamp（依賴：Phase 3，**同 commit**）
**Task 4.1 — impl 路徑 stamp 檢查與 adversarial waived 脫鉤**
- 目標：`--spec` impl 派工只要 `--reconcile` 非 waived，一律跑 `reconcile_stamps_check`，與 `--adversarial waived:` 無關。
- 檔案：`scripts/gate.sh` L480-498（stamp 區塊現包在 `case adversarial waived:*) skip`）。
- 改法：stamp 檢查移入 Task 3.1 的 `if [ -n "${spec}" ]` 必檢區塊，觸發條件＝「`--spec` 且 `--reconcile` 非 waived」，與 adversarial waived 無關。adversarial waived 僅豁免 adversarial 檢查本身。
- **驗證（可證偽，M1 oracle 強化）**：用 stamp **stub 記錄呼叫次數**（非只斷 gate rc）：攻擊路徑（`--spec`+`--reconcile synth`+`--adversarial waived:`+synth 無戳記）→ **stamp 被呼叫且 rc≠0**（`COMPLETENESS_CHECK_OVERRIDE=/bin/true` 隔離 completeness 干擾）；合法路徑（3 家 APPROVED 帶 task）→ **stamp 被呼叫且 rc=0**。測試：`pytest tests/governance/test_waived_adversarial_still_stamps.py`。
- **邊界（≥2）**：① 純 review `--adversarial waived:`（無 `--spec`）→不跑 stamp；② `--reconcile waived:` 明示豁免→Phase 3 已擋 impl 用 waived。
- **存活至**：永久常駐。
- **覆蓋風險**：無。
- 不可做：不移除 review 合法 waived 逃生口。

## §V 驗證策略與邊界測試目錄
- **mutation（必附）**：四支常駐測試＝紅隊 PoC 固化。**可證偽性**：斷言「攻擊→gate 拒發（rc≠0）」，revert 修法→轉紅。**Phase 4 用 spy/stub 證 stamp 被呼叫**（M1；否則「completeness 先 fail」會混淆 rc，mutation 假綠）。反向對照：合法路徑（真 audit+3 戳記+帶 task+synth 完整）→ rc=0，防過度收緊。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級：整合（實跑 `gate.sh`/`reconcile_stamps_check.sh` 子行程斷 rc + stdout + stamp 呼叫次數）。可獨立 `pytest tests/governance/` 跑。
- **防假綠**：不放寬既有斷言換綠；語義收緊使既有測試紅→遷移 fixture 對齊真實慣例（synth.md/帶 task），不放寬 gate。
- **正向 fixture 建置（M1）**：TODO 須含「建真實 audit+3 戳記 session」helper，供 V-C/V-M 正向路徑驗 rc=0。
- **CI**：四支新測試納入 `tests/governance/`，由 `.github/workflows/governance.yml` 自動跑。

## §R 回退
- **Phase 1/2 可獨立 commit/revert**。**Phase 3+4 必須同一 commit**（同改 gate.sh stamp 觸發區塊；單獨 revert Phase 4 會留「low impl 要 reconcile 但不要 stamp」半套態，M5/COMPOSER-P2-01）。Phase 2.2 fixture 遷移與 Phase 2.1 同 commit。
- 任一測試 FAIL → 不 merge。治理閘收緊屬正確性修復，不預設關閉（feedback「驗過就別預設關閉」）。

## §N N/A 登記
- **§G Golden**：N/A — 本任務不碰數值/特徵/ML/回測正確性（RISK-HIT 未含 a/d）；驗收靠 rc + provenance + stamp 呼叫次數斷言，非數值 baseline。
