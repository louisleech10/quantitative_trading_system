# 第 0 批摩擦止血 TODO

**狀態**: DRAFT（未過外部 adversarial review 前不得標 Frozen）
**基於 SPEC**: `docs/GOVB0_FRICTION_SPEC.md`（R7 版，七輪收斂，`handoffs/reconcile/20260805-govb0-spec-r7/synth.md` 三家 `RECONCILE-STAMP APPROVED`，sha `b502bac9…0f82fa4bd`）
**日期**: 2026-08-05
**涵蓋票**: `B-15`／`B-14`／`B-30`／`B-32` ＋ `B-24`（**僅紀律面**）

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 0.1 🔴 三項必讀狀態宣告（**本批交付物的誠實邊界，不得省略、不得改寫**）

1. **`票 B-24` ＝部分完成，不是全綠。**
   本批只交付**紀律面**（驗收欄一律寫執行後狀態斷言，零新增元件）。
   **機械強制面**（`acceptance_state_check.sh` ＋ grandfather SoT ＋ 具名 owner／UTC 到期日／到期後 fail-closed）
   已由 SPEC R1 裁定 SPLIT 移出獨立排期。
   ⇒ **code review 不得宣稱 `B-24` 全綠**；票面須維持「部分完成」。

2. **`reclaim` 孤兒回收未實作 ⇒ 需人工清理。**（R7 具名殘留 `H-2`，見 SPEC §N）

RESIDUAL: reclaim-orphan-manual-cleanup

   stale takeover 持有者若在協定步驟③（刪主 lock＋建新 lock）之後、④（釋放回收權）之前 crash，
   `<out>.reclaim.lockdir` 會殘留 ⇒ 後續 takeover 於步驟①即 `EEXIST` 拒絕 ⇒ **該 `<out>` 路徑鎖死至人工清理**。
   codex 實跑證據：`CRASH_CHILD_RC=137`／`MAIN_LOCK_AFTER_CRASH=present`／`RECLAIM_LOCK_AFTER_CRASH=present`／`NEXT_DISPATCH=REJECT_EEXIST`。
   ⇒ **不得宣稱 lock 機制全綠。** 修法三擇一由實作者定（見 Task 3.2 實作要點 8）。

3. **timeout 未達定稿門檻時一律標 `PROVISIONAL`。**
   門檻＝每家族累積 **≥50 筆** `committee_family_result`（`result_state=success`、含 duration 三欄）
   **且跨 ≥3 個不同 session／UTC 日期**。未達 ⇒ 機制照常上線並以暫定值運作，但
   ①本 §0 與 duration manifest **含 `PROVISIONAL` 字樣**；②Task 3.3 **標記為未完工**；③`票 B-14` 票面**含「未定稿」**。
   **三者任一缺失即 FAIL**（Task 3.3 驗證已機械化此條）。

> **本 TODO 產出時的 `PROVISIONAL` 狀態**：Task 3.1 尚未上線 ⇒ 三家族累積筆數皆為 0 ⇒
> **timeout 值全部標 `PROVISIONAL`**，Task 3.3 標記為**未完工**，`票 B-14` 維持**未定稿**。

### 0.2 SPEC §A 假設引用（**引用 manifest ID，不整段複製**）

- `[OPEN-1]` timeout 暫定值（codex 50m／grok 70m／composer 75m／外層 90m）——依 0.1 第 3 條處理。
- `[OPEN-3]` `B-15` FP-2 定位——已列 `E-SCOPE` 不受理，補查條件＝Phase 0 後 ≥200 筆 `gate_deny` 或 ≥30 日。
- 🔴 `[OPEN-2]`／`[D-8]` **locale 相依守衛＝已知 MAJOR 債**（`票 B-33`；`COMPOSER-TODO-P1-01` 指出主委初版漏列）：
  `LC_ALL=C` 下 `gate.sh` 的 Verdict 守衛與 `doc_format_precheck.sh` **雙雙 fail-open**（實測 2 例），
  `template_check.sh spec` 則**誤報**（1 例）。委員 CLI 與 CI runner 的 locale 不在主委控制範圍
  ⇒ **非 UTF-8 環境會靜默失去這兩道守衛**。
  **本批不修**（SPEC R1 兩家一致裁定避免 scope 膨脹，排第 1 批之後）。
  ⇒ **實作者須知**：本批新增的任何守衛，**若依賴中文字串比對，在非 UTF-8 環境同樣會失效**；
  請優先用 ASCII 錨點（正則、rc、數字），避免加深此債。
- SPEC §A 共 **10 條** FACT-RECEIPT（導出命令 `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md`），本 TODO 不重抄，需要時回查。

### 0.3 憲法約束（本任務相關者）

- **解耦**：本批只動 `scripts/`，**不得** import `api/`／`momentum/`，不觸及 7 條解耦規則。
- **Logging**：`scripts/` 為 shell，沿用既有 `echo`／audit 事件；**hot path 不新增 log**（`gate_check.sh:86` 判定段為 hot path）。
- **Error 分類**：gate 判定失敗一律 **fail-closed**（拒絕）；不得因 `grep`／`jq` 失敗而放行。
- **bash 3.2 相容**：禁 `declare -A`、禁 `flock`（macOS 無）；`rc` 一律直接取，**禁經 pipe**。
- **平台**：取 mtime 須 `stat -c %Y` 前置再 fallback `stat -f %m`（linux／macOS 差異，見 `gate_check.sh:70-74`）。
- **locale**：讀 audit／log 一律 `LC_ALL=C grep -a`，**禁 `export LC_ALL`**（會洩漏進 pre-push 弄紅治理測試）。

### 0.4 不可違反原則

- **不弱化既有斷言**；**禁恆真斷言**；**禁改檢查器或加排除清單換綠燈**。
- **既有 701 passed 為下限**，本批完工後總數只增不減；任何既有測試轉紅須具名說明。
- **每個新測試須 mutation 自證**：revert 修法 → 該測試轉紅，並貼實跑 rc。
- 跑完測試須 `bash scripts/restore_golden_inventory.sh`，
  **驗收以 `git status --short tests/golden/` 輸出為空為準，不得以該腳本 rc 為證**。
- **禁用統計手法讓門檻看起來達標**；做不到就提案改 SPEC，不得就地放寬。

### 0.5 防假綠（diff 斷言驗收）

- 每批交付須附 `git diff` 的既有測試檔段落，證明**未修改既有斷言**。
- 每個 mutation 須貼**實跑 rc**（`pytest ... ; echo rc=$?`，rc 直接取）。
- `ASSERT … THEN rc=…` 為範本固定文法，保留；但**每一條 `rc` 斷言都必須有同 Task 內對應的狀態斷言**，
  否則不成立（SPEC §V `票 B-24` 紀律面）。**code review 須逐條檢查「有 rc 斷言但無對應狀態斷言」者。**

---

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B0** | （無 Task，**純前置步驟**） | 無 | 🔴 **凍結 `gate_check.sh` 的 pre-Phase2 snapshot 並 commit**（`CODEX-TODO-P0-03` 修正）。主委初版把此步驟寫在 Task 2.5 內、卻把 B5 排在 B3/B4 之後 ⇒ **自相矛盾**：若 B3 已改 `gate_check.sh` 才複製 snapshot，Task 2.5 差集的「舊版」已含新修法，**merge gate 失去 oracle**。故獨立為 B0，**必須在 B3 動工前完成**。產出＝`tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot`（含其 sha256 寫入同目錄 `.sha256` 檔） | 小 |
| **B1** | `0.1` | 無 | Phase 0 單 Task；**Phase 2 驗收完全依賴它**，須最先落地並可獨立 merge（純觀測，判定行為不變） | 中 |
| **B2** | `1.1` | 無 | Phase 1 單 Task；與 B1 完全獨立，可並行；**Task 3.2 依賴其 prompt 路徑對齊** | 小 |
| **B3** | `2.0`／`2.1` | B1, **B0** | `2.0` 是詞法契約（純文件＋測試語料），`2.1` 是其第一個實作點；分開派會讓契約無驗證載體 | 大 |
| **B4** | `2.2`／`2.3`／`2.4` | B3 | 三者同改 `gate_check.sh:86` 判定段的不同 alternation，**同檔同段，分派必衝突** | 中 |
| **B5** | `2.5` | B3, B4 | 差集報表須在所有判定改動落地後才有意義；語料 B snapshot 須在 Phase 2 動工前凍結（見 Task 2.5 實作要點 2） | 中 |
| **B6** | `3.1`／`3.2` | B2 | `3.2` 的 lock／publish 與 `3.1` 的 duration 欄位同改 `_emit_family_result`，**同函式** | 大 |
| **B7** | `3.3` | B6 | timeout 值依賴 `3.1` 產出的 duration manifest；且 `3.3` 的逾時判定依賴 `3.2` 的 terminal marker | 中 |

**批次間 Gate**（引用具體 Test ID ＋ 可執行驗證命令，皆為 `pytest tests/governance/` 或 `bash scripts/*.sh` 且 rc == 0）：

- **B0 → B3**（🔴 **硬前置**）：`tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` **已存在且已 commit**
  （`git ls-files --error-unmatch <該檔>` rc=0），且其 sha256 與同目錄 `.sha256` 檔內容**相等**。
  **未過此 Gate 不得動工 B3**——否則 Task 2.5 的差集 oracle 失效。
- **B1 → B3**：`pytest tests/governance/test_gate_deny_fields.py -q` rc=0
  且 `TEST-0.1-INVARIANCE`（語料 A decision trace diff 為空）通過。
- **B2 → B6**：`pytest tests/governance/test_cxrun_stamp_prompt.py -q` rc=0，含 `TEST-1.1-UNKNOWN-NOSIDEEFFECT` 四項無副作用斷言。
- **B3 → B4**：`pytest tests/governance/test_gate_lexical_contract.py -q` rc=0，契約 **11 項** 各 ≥1 TP＋1 TN（共 ≥22 條）。
- **B4 → B5**：`pytest tests/governance/test_gate_decision.py -q` rc=0。
- **B5 → 合併 Phase 2**：`bash scripts/gate_decision_delta.sh` rc=0 且報表內「非預期」項數 == 0。
- **B6 → B7**：`pytest tests/governance/test_atomic_publish.py -q` rc=0，含 `TEST-3.2-LOCK-⑨`～`⑫` 四條並發斷言。
- **B7 → 完工**：`pytest tests/governance -q` 總數 ≥701 且無既有測試轉紅。

**每 Batch 派工 prompt 骨架**（可直接複製，`<>` 內替換）：

```
前置狀態：<列出已完成 Batch 與其 Gate 命令 rc>
本批 Task：<Task 編號與名稱>
必讀：docs/GOVB0_FRICTION_TODO.md §0 全文 ＋ 本批各 Task 段落。
驗證命令：<Gate 命令，rc 直接取，禁經 pipe>
禁止：不得修改既有測試斷言；不得改檢查器換綠燈；不得 git checkout/restore 任何 tracked 檔。
收尾：貼每個 mutation 的實跑 rc；跑 bash scripts/restore_golden_inventory.sh 後貼 git status --short tests/golden/。
```

---

## Phase 0 — 可觀測性前置（依賴：無）

> 完成後系統狀態：每次 `gate_deny` 都留下「被擋的指令」與「命中哪條規則」，誤擋率可事後量測。
> 🔴 **這是 Phase 2 驗收的資料來源，也是 `票 B-37`（撞擊次數統計）與 R7 殘留 `H-1`（允許清單收斂）的硬前置。**

### Task 0.1 — `gate_deny` 記錄被擋指令與命中規則

- **SPEC ref**：Task 0.1　**目標**：`gate_deny` 事件新增指令與命中規則兩欄，使誤擋率可事後量測。
- **輸入 / 輸出**：
  - 輸入：現行 `scripts/gate_check.sh`、`scripts/audit_events.json`。
  - 輸出：①改動後的 `gate_check.sh` ②`audit_events.json` 新增條目
    ③`tests/governance/fixtures/gate_invariance_corpus.txt`（**語料 A**，進版控）
    ④`tests/governance/test_gate_deny_fields.py`。
- **實作要點**：
  1. **先判定、後記錄**（順序不可逆）：
     ```
     _gate_decide()      # 既有判定邏輯，原封不動 → 回傳 (rc, kind)
     if rc != 0:
         frag=$(printf '%s' "$cmd" | LC_ALL=C grep -Eo "$matched_pattern" | head -1)
         _append_gate_deny_audit "$cmd" "$frag" "$match_rule"
     ```
     🔴 **`grep -Eo` 的結果不得回饋進判定**（`D-12`：`grep` 失敗或效能變化會改 rc）。
  2. **命令欄截斷**：`cmd_sha256`＝全文 sha256；`cmd_head`＝前 512 位元組。
     函式簽名：`_gate_deny_cmd_fields() { # $1=cmd → stdout: <sha256>\t<head512> }`
     理由：委員 prompt 可達數十 KB；sha256 使同一指令可被歸併計數（接 `票 B-37`）。
  3. **enum 與 required_fields 寫入 `scripts/audit_events.json`**，`gate_check.sh` **只引用不自列**。
     待新增 key（逐一列出，實作者不必猜）：
     - `required_fields_per_event.gate_deny` ← `["event","ts","reason","match_rule","cmd_sha256","cmd_head"]`
     - `match_rule` 封閉值集合 ← `["family_cli","claude_agent","outer_script","token_expired","open_debt","role_gate","unknown"]`
     - `event_object_allowed_keys.gate_deny` ← 同 `required_fields_per_event.gate_deny`
     未知值依該檔既有 `unknown_event_policy` 處理。
  4. **不變式（`D-3` 收窄＋`E-7`／`E-8` 分離 baseline）**：對**語料 A**，改前與改後的 `(rc, kind)` 序列**逐項相等**。
     🔴 **audit 內容本來就會增加欄位，不在本不變式範圍內。**
     🔴 **兩份語料與兩份 snapshot 各自獨立、不得共用**：
     - 語料 A `tests/governance/fixtures/gate_invariance_corpus.txt` — 判定**應完全相同**，基準＝Phase 0 改動前。
     - 語料 B `tests/governance/fixtures/gate_decision_corpus.txt` — 判定**應該改變**，基準＝Phase 2 動工前的 `gate_check.sh` 固定 sha snapshot（見 Task 2.5）。
     測試須斷言兩份語料檔 sha256 **不相等**且各自入版控。
- **修改檔案**（精確到函式名）：
  - `scripts/gate_check.sh` → `_append_gate_deny_audit()`（`:21-30`）新增三參數；`:86` 判定段後插入取片段步驟。
  - `scripts/audit_events.json` → 上述三個 key。
  - **既有 caller**：`gate_check.sh:117`、`gate_check.sh:128`（兩處呼叫 `_append_gate_deny_audit`，須同步改簽名）。
- **不可做**：**不得把 `grep -Eo` 放進判定前主路徑**；不建新 log 檔；不改 hook 順序；不動 `scripts/ts_stamp.sh`。
- **邊界**（≥2）：
  1. 指令含換行與控制字元 → 欄位須為合法 JSON 字串（`jq -e . < line` rc=0），不破壞 audit 逐行 JSON 結構。
  2. `tool_input.command` 缺失 → 欄位寫**空字串**而非缺欄，且不得例外中止（rc 與缺欄前相同）。
  3. 4 MB 巨量 prompt → 截斷後 audit 單行 ≤1 KB（`awk 'length($0)>1024' audit.log | wc -l` == 0）。
- **風險緩解**：`RISK-b`（跨模組共用路徑）— Phase 0 為純觀測，判定行為不變，可最先獨立 merge 並單獨 revert。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言）：
  - `TEST-0.1-RC-BLOCK`：`ASSERT bash scripts/gate_check.sh WHEN input=blocked_cmd THEN rc!=0`
  - `TEST-0.1-RC-ALLOW`：`ASSERT bash scripts/gate_check.sh WHEN input=allowed_cmd THEN rc=0`
  - `TEST-0.1-INVARIANCE`（狀態）：對語料 A，改前／改後的 **decision trace**（只含 `(rc, kind)` 兩欄，
    由測試 harness 另行輸出，**與 audit 事件是兩份不同產物**）**逐項相等、diff 行數 == 0**。
    🔴 **不得要求「兩份 audit JSON diff 為空」**——本 Task 的目的就是新增欄位，audit 必然不同。
  - `TEST-0.1-FIELDS`（狀態，與上條**分開驗**）：新 `gate_deny` 事件的欄位集合 **==**
    `jq -r '.required_fields_per_event.gate_deny[]' scripts/audit_events.json` 所得集合（**以該檔為斷言來源，非硬編**）。
  - `TEST-0.1-ENUM`（狀態）：`jq -r '.match_rule' <event>` 的值 ∈ `audit_events.json` 所定集合；`cmd_head` 非空。
  - `TEST-0.1-CORPUS-DISTINCT`（狀態）：兩份語料檔 sha256 **不相等**，且 `git ls-files` 兩者皆已追蹤。
  - `TEST-0.1-MUT`（mutation）：移除欄位寫入 → `TEST-0.1-FIELDS` 轉紅（貼實跑 rc）。
- **存活至**：永久（`票 B-29` 差集工具與 `票 B-37` 統計的資料來源）。
- **覆蓋風險**：無。

### Phase 0 測試 ＋ Gate

- 單元：`TEST-0.1-FIELDS`／`TEST-0.1-ENUM`　邊界：三條邊界各一測　效能：判定段不新增 subprocess。
- **Phase 0 Gate**：`pytest tests/governance/test_gate_deny_fields.py -q` rc=0 且 `TEST-0.1-INVARIANCE` 通過。

---

## Phase 1 — `B-32` stamp prompt 條件化（依賴：無）

> 完成後系統狀態：只有需要戳記的輪次才在 prompt 提及 RECONCILE-STAMP，系統不再自己誘發委員交件失敗。

### Task 1.1 — `cx_run.sh` prompt 依 `brief-kind` 分支

- **SPEC ref**：Task 1.1　**目標**：只有需要戳記的輪次才在 prompt 中提及 RECONCILE-STAMP。
- **輸入 / 輸出**：輸入＝**既有變數 `${_bk}`**（`cx_run.sh:46`，見下）；輸出＝分支後的 prompt 字串 ＋ `tests/governance/test_cxrun_stamp_prompt.py`。
- **實作要點**：
  1. **沿用既有 parser，禁再寫一份**（出生事故：`committee_run.sh` 曾有第二份 parser，造成孤兒債）。
     🔴 **既有機制的實際樣貌（`CODEX-TODO-P0-02` 修正；主委初版誤把 `_bc_kv` 當成 helper 函式，
     實測 `grep -n '_bc_kv' scripts/cx_run.sh` 顯示它是 `mktemp` 的暫存檔路徑變數，非函式）**：
     ```
     # cx_run.sh:39  _bc_kv="$(mktemp)"                         ← 暫存檔路徑
     # cx_run.sh:45  bash brief_conformance_check.sh "$brief" --emit "${_bc_kv}" || exit $?
     # cx_run.sh:46  _bk="$(sed -n '1p' "${_bc_kv}")"           ← brief-kind 已在此可用
     # cx_run.sh:47  stamp_target="$(sed -n '2p' "${_bc_kv}")"
     ```
     ⇒ **本 Task 直接使用既有的 `${_bk}`，不新增任何解析步驟。**
     ```
     case "${_bk}" in
       stamp|closure) prompt="${prompt}${_STAMP_INSTRUCTION}" ;;
       consult|review|impl|dext) : ;;                 # 完全不提 RECONCILE-STAMP
       *) echo "ERROR: unknown brief-kind=$kind（fail-closed）" >&2; exit 1 ;;
     esac
     ```
  2. `stamp`／`closure` 分支的注入句須**補格式說明**：戳記為單獨一行
     `RECONCILE-STAMP: <family> APPROVED <date> sha256:<hash> task:<id>`，**非 `## ` 標題**。
     🔴 **格式的單一真相源＝`cx_run.sh:345` 的正則**；測試須斷言 prompt 說明與該正則機械一致
     （同一個合法戳記樣本同時通過兩者）。
  3. **unknown `brief-kind` → fail-closed 拒派**（`D-5`：R1 原文「視同不需戳記＋audit 警示」與 fail-closed 互斥，已改為單一行為）。
- **修改檔案**：`scripts/cx_run.sh` 的 **`_prepare_and_run()`（`:501-513`，prompt 組裝在此）**。
  🔴 **`CODEX-TODO-P0-02` 修正**：主委初版誤寫「caller ＝ `_run_cli_and_emit`」，方向相反——
  實測 `grep -n '_prepare_and_run\|_run_cli_and_emit' scripts/cx_run.sh` 顯示
  `_prepare_and_run`（`:501`）**呼叫** `_run_cli_and_emit`（`:513`），非被它呼叫。
  **既有 caller**：`cx_run.sh:518`／`:521`／`:524` **三處**呼叫 `_prepare_and_run`（分支入口，不需改）。
- **不可做**：不改 `completeness_check.sh` 的 ID schema（`票 B-32` 修法③，本批不做）；不改既有戳記格式。
- **邊界**（≥2）：
  1. `brief-kind` 解析失敗／缺欄 → fail-closed，維持現行拒派行為（rc≠0）。
  2. `brief-kind` 為未知值 → fail-closed（同上，**不再有第三種行為**）。
- **風險緩解**：`RISK-b` — Phase 1 與 Phase 0 完全獨立，可單獨 revert。
- **🔴 誠實邊界**（`D-11`）：本 Task 只保證 **harness 端不再誘導**；**無法保證委員不自行寫出 `## RECONCILE-STAMP` 標題**。
  後者屬 `票 B-31` 範疇。**驗收不得以「委員這次沒寫」為斷言**（不可重現）。
  📌 佐證：2026-08-05 主委在 brief 明文警告格式規則後，composer **仍同型違規第二次** ⇒ prompt 層警告無效已實證。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-1.1-CONSULT`：`ASSERT bash scripts/cx_run.sh WHEN brief_kind=consult THEN rc=0`
    且生成的 prompt 中 `RECONCILE-STAMP` 出現次數 == 0。
  - `TEST-1.1-STAMP`：`ASSERT … WHEN brief_kind=stamp THEN rc=0` 且 prompt 含該字串與格式說明。
  - `TEST-1.1-UNKNOWN`：`ASSERT … WHEN brief_kind=unknown THEN rc!=0`
  - `TEST-1.1-UNKNOWN-NOSIDEEFFECT`（狀態，`E-2`：R2 只有 rc、缺無副作用證明）：
    被拒後 ①`.claude/gate/` 內**無新 token 檔且 mtime 未更新** ②`.claude/gate/audit.log` 行數**前後相等**
    ③`bash scripts/debt_ledger.sh --has-open` 的 rc 與呼叫前**相同** ④`handoffs/` 下**未產生任何新檔**。
  - `TEST-1.1-FORMAT-SSOT`（狀態）：一個合法戳記樣本**同時**通過 prompt 說明所述格式與 `cx_run.sh:345` 正則。
  - `TEST-1.1-MUT`（mutation）：還原無條件注入 → `TEST-1.1-CONSULT` 轉紅；
    移除 unknown 分支 → `TEST-1.1-UNKNOWN` 與四項無副作用斷言轉紅（貼實跑 rc）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Phase 1 測試 ＋ Gate

- 單元：prompt 生成分支　邊界：兩條 fail-closed　整合：一次真實 `consult` 派工 prompt 不含該字串。
- **Phase 1 Gate**：`pytest tests/governance/test_cxrun_stamp_prompt.py -q` rc=0。

---

## Phase 2 — `B-15` gate 判定修正（依賴：Phase 0）

> 完成後系統狀態：唯讀查詢不再被誤判為派工；六種既有 fail-open 全部關閉；判定變更有差集報表佐證。

### Task 2.0 — 詞法契約（lexical contract）先定義，後實作

- **SPEC ref**：Task 2.0　**目標**：先把「什麼算命令位置／什麼算引號 span」定死成可機械驗收的契約，再實作。
- **輸入 / 輸出**：輸入＝SPEC Task 2.0 契約 **11 項**（`1`／`1b`／`2`–`10`）；
  輸出＝`tests/governance/fixtures/gate_decision_corpus.txt` 語料 B ＋ `tests/governance/test_gate_lexical_contract.py`。
- **實作要點**：
  1. **契約 11 項逐項實作**，每項各 ≥1 TP ＋ ≥1 TN，**共 ≥22 條**，全部進語料 B。
  2. **參考實作＝原型③** `handoffs/govb0_probes/b15probe5.sh`（主委實跑 26/26）。
     🔴 它**只涵蓋第 2、3 項**；第 **4、5、7、8、9、10** 項**尚未在原型中實作**，實作者須補齊並補測試。
     **禁止照抄原型即宣稱完成**（`COMPOSER-R2-P1-01`：原型與契約有落差）。
  3. **契約 1b（剝引號）必須跨行有狀態**：用 `awk` 狀態機，
     **禁 `sed 's/"[^"]*"//g'` 行內替換**、**禁正規化為單行**（會使真多行指令第 2 行漏網）。
     參考原型＝`handoffs/govb0_probes/b15probe6.sh`（4/4）。
  4. **heredoc（契約第 10 項）七條機械規則**——實作者逐條落地：
     ```
     ① 起點 = 匹配 <<[-]?[[:space:]]* 後接 (a)|(b)|(c) 之一，取其後的下一個換行
        (a) '([^']*)'   (b) "([^"]*)"   (c) ([A-Za-z0-9_.:+=,%@^~{}\[\]!*?-]+)   ← 允許清單
        (c) 必須完整 token：其後緊接 [[:space:]]／換行／字串結尾（禁前綴匹配）
     ② delimiter = 捕捉群去引號後的字面值
     ③ 終點 = 行首恰為 delimiter 的那一行（<<- 允許行首 tab，其餘不允許任何前導空白）
     ④ 多 heredoc 併存 → 依出現順序依序消耗
     ⑤ delimiter 未出現到字串結尾 → fail-closed
     ⑥ 允許清單語意見①(c)
     ⑦ 無法依⑥解析 → 整個掃描 fail-closed（BLOCK），不得略過該 << 繼續掃描
     ```
     🔴 **⑥與⑦互補且不重疊**：凡不落在 (a)(b)(c) 三形式者一律走⑦，**不得有「⑥接受但⑦說要拒絕」的重疊區**。
     🔴 **允許清單為何不必列完**（使用者 2026-08-05 定框架，見 SPEC §N）：
     漏項的後果是 **fail-closed／誤擋**（可見、會被抱怨、可補），不是 fail-open／漏放（不可見）。
     ⇒ 允許清單**可收斂**，補一次少一次。**收斂循環的前提是誤擋看得見 ⇒ Phase 0 為硬前置。**
- **修改檔案**：新增 `tests/governance/test_gate_lexical_contract.py`；新增語料 B `tests/governance/fixtures/gate_decision_corpus.txt`。
  **既有 caller**：無（本 Task 只產契約與語料，實作點在 2.1–2.4）。
- **不可做**：**不得在四個 Task 中各寫一份剝引號邏輯**（須單一實作供 2.1–2.4 共用）。
- **邊界**（≥2）：見契約第 6、8、9、10 項——未閉合引號／遞迴逾 3 層／跳脫字元邊界不明／heredoc 未閉合，
  **四者皆 fail-closed**，各自即為邊界情境並已要求測試。
- **風險緩解**：`RISK-b`＋`RISK-c` — Phase 2 為最高風險；逃生口＝環境變數一鍵回舊判定（**僅供緊急回退，非預設關閉**）。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-2.0-CONTRACT-22`（狀態）：契約 **11 項**各 ≥1 TP＋1 TN，**測試條數 ≥22**，全部進語料 B。
  - `TEST-2.0-PROTO-PARITY`（狀態）：對 `b15probe5.sh` 的 **26 條**既有語料，新實作判定與原型③**逐條相同**；差異須具名說明。
  - `TEST-2.0-HEREDOC-FC`（狀態）：`<<E'O'F`／`<<E"O"F`／`<<$'EOF'`／`<<E\ F`／`<<EOF$(` **五向量全部 BLOCK**（走⑦）。
  - `TEST-2.0-HEREDOC-OK`（狀態）：`<<EOF-1`／`<<'EOF-1'`／`<<EOF~1` 等允許清單內字元**正確開 span**（body 不掃描）。
  - `TEST-2.0-HEREDOC-NEST`（狀態）：**body 內含假 marker 且 delimiter 後接真派工** → **BLOCK**（即 `CODEX-R5-P0-01` 攻擊鏈）。
  - `TEST-2.0-MUT-ALLOWLIST`（mutation）：把⑥(c) 改回排除清單 `([^[:space:]|&;()<>]+)` **或**移除完整 token 邊界
    ⇒ `TEST-2.0-HEREDOC-FC` **至少一條轉為 ALLOW**（斷言轉紅，貼實跑 rc）。
  - `TEST-2.0-MUT-11`（mutation）：契約每一項各自 revert → 對應語料轉為錯誤方向（**11 項各一個 mutation**）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.1 — 引號感知 ＋ `-c` 遞迴（洞 A ＋ `D-1` 的 fail-open）

- **SPEC ref**：Task 2.1　**目標**：引號**內**的分隔符不生效；但 `(bash|sh|zsh) -c` 的引數仍受檢。
- **輸入 / 輸出**：輸入＝Task 2.0 契約；輸出＝改動後的 `gate_check.sh:86` 判定段前處理 ＋ 對應測試。
- **實作要點**：
  1. 依 Task 2.0 契約實作剝引號前處理，**純 shell／`sed`／`awk`，禁 subprocess 呼叫 python**（熱路徑）。
     🔴 **R4 放寬至含 `awk`**：契約 1b 要求跨行狀態機，`sed` 的 `s///` 做不到；`awk` 與 `sed`／`grep` 同級（POSIX，單次 fork）。
     **FACT-RECEIPT**：實測每次工具呼叫 **+5 ms**（正常呼叫約 80 ms、權限分類器 2300–3000 ms）⇒ 約 6% 開銷，可接受。**維持禁 python。**
  2. 剝引號後再套命令位置判定；命令位置定義含 `^ ; & | ( \` $( && || eval後 xargs後`（契約第 2 項）。
  3. `(bash|sh|zsh) -c` 與 `eval` 的引號引數**遞迴掃描**，上限 3 層，逾限 fail-closed。
- **修改檔案**：`scripts/gate_check.sh:86` 判定段（新增前處理）。**既有 caller**：`gate_check.sh:117`、`:128`。
- **不可做**：不得在別處複製一份剝引號邏輯；不得改用 python。
- **邊界**（≥2）：①未閉合引號 → fail-closed（視為未剝除）②遞迴逾 3 層 → fail-closed ③跳脫字元不終止 span，邊界不明 → fail-closed。
- **風險緩解**：`RISK-c` — 差集報表（Task 2.5）出現「非預期」項 → **不 merge**。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-2.1-FP`（狀態）：`pgrep -fl 'codex exec|cursor-agent|grok '`、
    `git commit -m "…; codex closure review…"` **由 BLOCK 轉 ALLOW**。
  - `TEST-2.1-E3`（狀態，**`E-3`：現行 gate 即已 fail-open，本 Task 一併修**）：
    `eval "codex exec x"`、`out=$(codex exec x)`、`` out=`codex exec x` ``、`(codex exec x)`、`eval 'grok -m grok-4.5 -p x'`
    **五條全部由 ALLOW 轉 BLOCK**。
  - `TEST-2.1-RECURSE`（狀態）：`bash -c "codex exec x"`、`sh -c 'grok -m grok-4.5 -p x'`、`bash -c "claude -p x"`、
    `true && codex exec x`、`false || grok -m x -p y`、`echo x | xargs codex exec` **六條皆 BLOCK**。
  - `TEST-2.1-OUTSIDE`（狀態）：`echo start; grok -m grok-4.5 -p "x"`（引號**外**的分號）維持 BLOCK。
  - `TEST-2.1-1B`（狀態，`F-6` 具名語料，來源 `handoffs/govb0_probes/b15probe6.sh`）：跨行剝引號 4/4 通過。
  - `TEST-2.1-MUT`（mutation）：移除 `-c`／`eval` 遞迴 → `TEST-2.1-RECURSE` 轉 ALLOW；
    縮回 R2 的命令位置定義（僅 `^ ; & |`）→ `TEST-2.1-E3` 五條轉回 ALLOW（貼實跑 rc）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.2 — `claude` 段收窄（洞 B，含一條 fail-open）

- **SPEC ref**：Task 2.2　**目標**：`claude` 不再子字串比對；`-p`／`--print` 須為獨立引數。
- **輸入 / 輸出**：輸入＝Task 2.0 契約第 2、3 項；輸出＝`gate_check.sh:86` 第二段 alternation ＋ 測試。
- **實作要點**：
  1. `claude` 比照家族名**限定命令位置**並允許路徑前綴。
  2. `-p`／`--print` 須有**詞界**（`(^|[[:space:]])(-p|--print)([[:space:]]|$)`）。
  3. **移除 `[^|]*` 跨字元貪吃**（現行 `claude[^|]*(-p|--print)` 是子字串比對的根源）。
- **修改檔案**：`scripts/gate_check.sh:86` 第二段 alternation。**既有 caller**：`gate_check.sh:117`、`:128`。
- **不可做**：**不得整段刪除 `claude` 判定**（會失去子代理攔截）。
- **邊界**（≥2）：①`claude` 在檔名中段（`my-claude-notes.md`）→ ALLOW ②絕對路徑（`/usr/local/bin/claude -p x`）→ BLOCK ③`-p` 為他人旗標（`grep -p`）且無 `claude` → ALLOW。
- **風險緩解**：`RISK-c` — 同 Task 2.1。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-2.2-FP4`（狀態）：`head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD`、
    `cat .claude/tmp/x.txt; git rev-parse HEAD`、`ls /private/tmp/claude-501/; git status --porcelain`、
    `find .claude/tmp -name "*.md" -print` **四條全由 BLOCK 轉 ALLOW**。
  - `TEST-2.2-TP`（狀態）：`claude -p "x"`、`claude --print "x"` **維持 BLOCK**。
  - `TEST-2.2-PIPE`（狀態，**修 fail-open**）：`cat x | claude -p "y"` **由 ALLOW 轉 BLOCK**。
  - `TEST-2.2-REGRESS`（狀態，🔴 **防 R2 設計造成的回歸**）：`v=$(claude -p "hi")` 與
    `/usr/local/bin/claude --print "x"` **兩條須 BLOCK**。
    R2 把 `claude` 收窄到命令位置後，命令替換形態**由 BLOCK 退化為 ALLOW**（現行 gate 靠子字串偶然擋住）——
    此為 `E-3` 實測發現，由 Task 2.0 契約第 2 項（命令位置含 `$(`）承接。
  - `TEST-2.2-MUT`（mutation）：還原子字串比對 → `TEST-2.2-FP4` 轉回 BLOCK、`TEST-2.2-PIPE` 轉回 ALLOW；
    自命令位置定義中移除 `$(` → `TEST-2.2-REGRESS` 轉為 ALLOW（貼實跑 rc）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.3 — 家族名 basename 化（fail-open ①）

- **SPEC ref**：Task 2.3　**目標**：帶路徑前綴的家族 CLI 須被擋。
- **輸入 / 輸出**：輸入＝Task 2.0 契約第 3 項；輸出＝`gate_check.sh:86` 第一段 alternation ＋ 測試。
- **實作要點**：
  1. 命令位置比對**允許可選路徑前綴**，含帶引號路徑（`"/my dir/codex" exec`）。
  2. 家族清單維持既有 SoT 語意（`gate_check.sh:79-80` 註解已載明「熱路徑寫死＋測試釘死 == SoT」）。
  3. 比對以 **basename 相等**為準，非子字串（`mycodex` 不得命中）。
- **修改檔案**：`scripts/gate_check.sh:86` 第一段 alternation。**既有 caller**：`gate_check.sh:117`、`:128`。
- **不可做**：**不得把家族清單複製一份到別處**（會產生第二個 SoT）。
- **邊界**（≥2）：①檔名為 `mycodex`（非 basename 相等）→ ALLOW ②`grok` 為目錄名（`/tmp/grok/notes.md`）→ ALLOW ③路徑含空白且未加引號 → 依 Task 2.0 契約定義。
- **風險緩解**：`RISK-c` — 同 Task 2.1。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-2.3-PREFIX5`（狀態）：`/opt/homebrew/bin/codex exec hi`、`/Users/…/.grok/bin/grok -m x -p y`、
    `venv/bin/codex exec hi`、`./scripts/../codex exec hi`、`"/my dir/codex" exec hi` **五條全由 ALLOW 轉 BLOCK**。
  - `TEST-2.3-FN`（狀態）：`cat sp_codex.txt` **維持 ALLOW**。
  - `TEST-2.3-MUT`（mutation）：還原無前綴版 → `TEST-2.3-PREFIX5` 五條轉回 ALLOW（貼實跑 rc）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.4 — 官方外層腳本呼叫點（fail-open ②）

- **SPEC ref**：Task 2.4　**目標**：直接執行 `cx_run.sh`／`committee_run.sh` 亦須有 gate token。
- **輸入 / 輸出**：輸入＝Task 2.0 契約第 4 項（路徑正規化）；輸出＝`gate_check.sh:86-90` ＋ 測試。
- **實作要點**：
  1. 命令位置出現 `cx_run.sh` 或 `committee_run.sh`（含路徑正規化變形 `./scripts/`、`scripts//`、`scripts/../scripts/`）→ `kind=dispatch`。
  2. `scripts/gate.sh` **維持排除**（否則無法 bootstrap 取 token）。
  3. 判定須在**命令位置**，字串引數中出現腳本名不得命中。
- **修改檔案**：`scripts/gate_check.sh:86-90`。**既有 caller**：`gate_check.sh:117`、`:128`。
- **不可做**：**不得把 `gate.sh` 納入**（會鎖死取 token 的唯一路徑）。
- **邊界**（≥2）：①相對路徑變形 → BLOCK ②唯讀查看該腳本 → ALLOW ③腳本名出現在字串引數中（`echo "run cx_run.sh later"`）→ ALLOW。
- **風險緩解**：`RISK-c` — 端到端回歸護欄 `TEST-2.4-E2E`（`pytest` 斷言 `result_state=success` 出現在 audit）確保取 token 後的正常流程未被鎖死。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-2.4-DIRECT`（狀態）：`ROUND_ID=x bash scripts/cx_run.sh composer b.md o.md`、`bash ./scripts/cx_run.sh …`、
    `bash scripts//cx_run.sh …` **三條由 ALLOW 轉 BLOCK**（無 token 時）。
  - `TEST-2.4-COMMITTEE`（狀態）：`bash scripts/committee_run.sh --session s b.md o codex -- --task-id T`
    **由 ALLOW 轉 BLOCK**（無 token 時）。
  - `TEST-2.4-GATE-OK`（狀態）：`bash scripts/gate.sh dispatch --intent x …` **維持 ALLOW**。
  - `TEST-2.4-E2E`（**回歸護欄，端到端**）：`committee_run.sh` 取得 token 後呼叫 `cx_run.sh` 的既有流程
    **須仍能完成一次真實派工**（`result_state=success` 出現在 audit）。
  - `TEST-2.4-NOFP`（狀態，**不得製造新誤擋**）：`sed -n '1,40p' scripts/cx_run.sh`、
    `grep -n timeout scripts/cx_run.sh`、`wc -l scripts/committee_run.sh` **三條唯讀查看維持 ALLOW**。
  - `TEST-2.4-MUT`（mutation）：移除呼叫點判定 → `TEST-2.4-DIRECT` 與 `TEST-2.4-COMMITTEE` 轉回 ALLOW（貼實跑 rc）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.5 — 行為差集報表（`票 B-29` 手動版）＋ immutable corpus

- **SPEC ref**：Task 2.5　**目標**：對**固定**語料，列出「本來擋現在放行」「本來放行現在擋」「未變」三堆。
- **輸入 / 輸出**：輸入＝語料 B ＋ Phase 2 動工前的 `gate_check.sh` 固定 sha snapshot；
  輸出＝`scripts/gate_decision_delta.sh`（一次性可重跑，**非 hook**）＋報表。
- **實作要點**：
  1. **immutable corpus**：語料檔 `tests/governance/fixtures/gate_decision_corpus.txt` 進版控，
     其 `sha256` 寫入報表標頭；差集結果綁該 sha。
     語料變更須另行 commit 並重跑，**不得在同一次驗收中修改語料**。
  2. **舊版判定來源＝Phase 2 動工前的 `gate_check.sh` 副本**，以固定 sha 存於 `tests/governance/fixtures/`，
     **非 `HEAD`**（`D-13`：舊版 snapshot 為 forward dependency，用 `HEAD` 會隨改動漂移）。
     🔴 **此 snapshot 由 B0 產出並 commit，必須在 B3 動工前完成**（`CODEX-TODO-P0-03`）。
     本 Task 只**消費**該 snapshot，不負責產生；若檔案缺失或 sha256 與 `.sha256` 檔不符 ⇒ **fail-closed（rc≠0）**。
  3. 每條語料**標明出處**（哪次事故／哪個 Task 的驗證項），**禁憑空造**。
- **修改檔案**：新增 `scripts/gate_decision_delta.sh`。
  🔴 **本 Task 不產生任何 fixture**（`CODEX-R8-P1-02` 修正：主委初版把 snapshot 同時列為 B0 產出與本 Task 產出，
  實作者可能在 B5 重產 ⇒ 差集 oracle 會含 Phase 2 改動）。
  **唯讀輸入**（由 **B0** 產出並持有 sha ownership，本 Task 只讀不寫）：
  `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` ＋ 其 `.sha256` sidecar；
  `tests/governance/fixtures/gate_decision_corpus.txt`（語料 B，由 Task 2.0 產出）＋ 其 `.sha256` sidecar。
  **既有 caller**：無（一次性腳本）。
- **不可做**：**不掛 hook、不進 CI**（一次性驗收工具）。
- **邊界**（≥2）：
  1. 語料為空 → **rc≠0 並明確報錯**，**不得靜默輸出「無差異」**。
     出生事故：2026-08-04 zsh 斷詞使 2559 條路徑變成一個檔名，報表印「前 0 後 0、無差異」。
  2. 語料含 Phase 0 記錄的真實被擋指令 → 須能吃（含換行、控制字元）。
  3. 舊版 snapshot 檔缺失 → **fail-closed**（rc≠0）。
- **風險緩解**：`RISK-c` — 本 Task 即 Phase 2 的 merge gate。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-2.5-SUBSET-BLOCK`（狀態）：「本來放行現在擋」欄 **⊇** Task 2.2／2.3／2.4 列舉的 fail-open 修復項（**必要子集**）。
  - `TEST-2.5-SUBSET-ALLOW`（狀態）：「本來擋現在放行」欄 **⊇** Task 2.1／2.2 列舉的誤擋修復項（**必要子集**）。
  - `TEST-2.5-EXTRA`（狀態）：兩欄中**不屬於 SPEC 列舉的附加項**須**逐項人工標註**為「預期」或「非預期」，
    標註結果寫入報表；**存在任一「非預期」⇒ rc≠0**。
    🔴 R1 原文要求「每一項都須在 SPEC 中被預期」，`COMPOSER-R1-P1-01` 指出 Phase 0 真實語料上線後必然產生 SPEC 未列舉項
    ⇒ 永遠 FAIL 或被悄悄放寬。**已改為「列舉項為必要子集 ＋ 附加項須人工標註」。**
  - `TEST-2.5-CORPUS-SHA`（狀態，**`CODEX-R8-P1-03` 修正**）：報表標頭的 sha256
    須同時等於 ①**當前語料檔實算的 sha256** ②**已 commit 的 `.sha256` sidecar 內容**。
    🔴 **兩者缺一不可**。主委初版只比對①⇒ 改了語料重跑後標頭會**跟著重算並相等**，
    「同一次驗收不得修改語料」根本無法證偽（假綠）。sidecar 是**獨立 SoT**，
    改語料**必須另行 commit 更新 sidecar**，該 commit 即為稽核痕跡。
  - `TEST-2.5-EMPTY`（邊界）：空語料 → rc≠0 且 stderr 含明確錯誤訊息（非「無差異」）。
  - `TEST-2.5-MUT`（mutation，**`COMPOSER-TODO-P2-01` 指出主委初版漏列，違反 SPEC §V「全部 11 Task 皆須 mutation」**）：
    ①移除「與已 commit 的 `.sha256` sidecar 比對」這一半守衛 ⇒ **改語料並重跑後仍 rc=0**
      （`TEST-2.5-CORPUS-SHA` 轉紅）。🔴 **只移除「與當前語料實算值比對」那一半不算數**——
      那一半本來就擋不住改語料，mutation 必須針對 sidecar 那一半；
    ②移除「附加項須人工標註」的守衛 ⇒ 注入一個未標註的附加項時仍 rc=0（`TEST-2.5-EXTRA` 轉紅）；
    ③把空語料的 fail-closed 改為靜默輸出「無差異」⇒ `TEST-2.5-EMPTY` 轉紅。
    **三個 mutation 各須貼實跑 rc。**
- **存活至**：永久（`票 B-29` 實作時取代）。
- **覆蓋風險**：`票 B-29`（第 1 批）可能以更通用機制取代 ⇒ **屆時應取代而非並存**，理由已註記於本行。

### Phase 2 測試 ＋ Gate

- 單元：契約 11 項 ≥22 條　邊界：四類 fail-closed　整合：`TEST-2.4-E2E` 一次真實派工。
- **Phase 2 Gate**：`pytest tests/governance/test_gate_lexical_contract.py tests/governance/test_gate_decision.py -q` rc=0
  **且** `bash scripts/gate_decision_delta.sh` rc=0 **且**報表「非預期」項數 == 0。
  🔴 **差集報表出現「非預期」項 → 不 merge。**

---

## Phase 3 — `B-14` ＋ `B-30` 委員產出生命週期（依賴：Phase 1）

> 完成後系統狀態：委員寫入中的產出對外不可見；publish 本身即 terminal marker；委員掛住會自動收斂且不誤判成功。

### Task 3.1 — per-family 耗時紀錄

- **SPEC ref**：Task 3.1　**目標**：先有資料，才有 timeout 值的依據。**Task 3.3 的定稿依賴本 Task。**
- **輸入 / 輸出**：輸入＝現行 `committee_family_result` 事件；輸出＝該事件新增 `started_at`／`ended_at`／`duration_sec` 三欄 ＋ `audit_events.json` schema ＋ 測試。
- **實作要點**：
  1. 記錄 CLI 呼叫的起、訖與時長，**寫入既有 `committee_family_result` 事件**（**沿用既有事件，不新增事件型別**）。
  2. 時間源須為**單調時鐘或 UTC epoch**，**禁本地時間字串相減**。
     ```
     _t0=$(date -u +%s)          # UTC epoch
     ... CLI ...
     _t1=$(date -u +%s); _dur=$(( _t1 - _t0 ))
     ```
  3. 欄位加入 `scripts/audit_events.json` 的 `required_fields_per_event.committee_family_result`。
  4. 🔴 **duration manifest 定義（`CODEX-TODO-P1-04` 修正；主委初版只說「manifest」未定路徑與 schema ⇒ 不可解析）**：
     - **產出路徑**：`handoffs/duration_manifest.json`（進版控）。
     - **producer**：新增 `scripts/duration_manifest.sh`，由 `audit.log` 的 `committee_family_result` 事件導出，**不另存狀態**。
     - **schema**（逐 key 列出，實作者不必猜）：
       ```
       {
         "generated_at": "<UTC ISO8601>",
         "source_event_count": <int>,          # 納入統計的事件總數
         "families": {
           "<family>": {
             "sample_count": <int>,            # 該家族 result_state=success 且含三欄的筆數
             "distinct_sessions": <int>,       # 跨幾個不同 session / UTC 日期
             "max_duration_sec": <int>,
             "p99_duration_sec": <int>,
             "timeout_sec": <int>,
             "status": "PROVISIONAL" | "FINAL"  # sample_count>=50 且 distinct_sessions>=3 才可為 FINAL
           }
         },
         "outer_timeout_sec": <int>,
         "status": "PROVISIONAL" | "FINAL"     # 任一家族為 PROVISIONAL 則整體 PROVISIONAL
       }
       ```
     - **`status` 的判定為純函式**（由 `sample_count` 與 `distinct_sessions` 導出），**不得手填**。
- **修改檔案**：`scripts/cx_run.sh` 的 `_run_cli_and_emit` 與 `_emit_family_result`（`:250-288`）。
  **既有 caller**：`committee_run.sh` 呼叫 `cx_run.sh`（不需改，欄位為附加）。
- **不可做**：**不新增 audit 事件型別**。
- **邊界**（≥2）：①CLI 未執行即失敗（binary 不存在）→ 時長欄為 **0 或缺，不得為負** ②跨日／時區 → 用單調時間或 UTC epoch。
- **風險緩解**：`RISK-b` — 純附加欄位，不改判定。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-3.1-FIELDS`（狀態）：一次真實派工後，`committee_family_result` 含起訖與時長三欄，
    且 `duration_sec == ended_at - started_at`（**自洽檢查**）。
  - `TEST-3.1-SCHEMA`（狀態）：欄位名與 `jq -r '.required_fields_per_event.committee_family_result[]' scripts/audit_events.json`
    **一致**（以該檔為斷言來源）。
  - `TEST-3.1-NONNEG`（邊界）：binary 不存在時 `duration_sec >= 0`。
  - `TEST-3.1-MANIFEST`（狀態，`CODEX-TODO-P1-04`）：`bash scripts/duration_manifest.sh` 產出的
    `handoffs/duration_manifest.json` 可被 `jq -e .` 解析；其
    `.families[].status` **由 `sample_count>=50 and distinct_sessions>=3` 純函式導出**
    （測試以構造資料驗兩個方向：49 筆 → `PROVISIONAL`；50 筆跨 3 session → `FINAL`）。
  - `TEST-3.1-MANIFEST-MUT`（mutation）：把 `status` 改成手填常數 `FINAL` ⇒ 上條的 49 筆案例**必須 FAIL**。
  - `TEST-3.1-MUT`（mutation）：移除欄位 → `TEST-3.1-FIELDS` 轉紅（貼實跑 rc）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 3.2 — attempt-scoped atomic publish（同時解 `B-30` 與 `B-14` 的 terminal marker）

- **SPEC ref**：Task 3.2　**目標**：委員寫入中的產出對外不可見；**publish 動作本身**即 terminal marker。
- **輸入 / 輸出**：輸入＝Task 1.1 對齊後的 prompt 路徑；輸出＝attempt-scoped 寫入＋原子 publish＋lock 協定 ＋ 測試。
- **實作要點**：
  1. **attempt identity**：每次派工產生唯一 attempt id，產出寫入 **attempt 專屬 temp namespace**
     （`<out>.<attempt-id>.part`），**非共用的 `<out>.part`**。
  2. **prompt 對齊（`D-2` 核心）**：`cx_run.sh:512` 的「產出寫到 `${out}`」**必須同步改為 attempt 路徑**。
     🔴 **prompt-only 或 wrapper-only 皆不成立**：只改 prompt → 委員可忽略；只改 wrapper → 委員仍寫 `<out>`。
     **兩者必須同時改，且測試須同時覆蓋。**
  3. **啟動前檢查**：確認 final path 的 marker 不存在；若存在 stale `<out>` → **拒絕啟動或明確標記為 stale**，不得沿用。
  4. **publish 條件**：CLI 返回 rc=0 → **先 flush/fsync** → 跑格式檢查 → 通過才**原子 publish（rename）**。
     **不通過則保留 attempt 檔並記 `format-failed`**（產出不消失，供人工檢視）。
  5. **terminal marker ≠ 檔案存在**：marker 為「本 attempt 的 publish 已完成」，須可由 audit 與檔案系統**雙向確認**（attempt id 綁定）。
     🔴 **明確不受理（`E-SCOPE`）**：本 marker **不保證內容完整**——中途截斷但最後一條 finding 恰好格式完整者仍會通過。
     已開 `票 B-35`。本 Task 解掉的是 **stale `<out>` 誤判／委員覆蓋自產（`B-30`）／未完成即上架** 三種失效模式；**截斷是第四種，本批不解**。
  6. **`B-30` 回歸**：委員若誤寫 attempt 檔，最終以 publish 為準；另加**大小回歸偵測**（曾非空後歸零 → 記警示）。
  7. **lock 協定（acquire 必須原子）**：
     ```
     # 取得：單一原子操作，二選一
     mkdir "<out>.lockdir"            # POSIX 保證同名目錄僅一個建立者成功
     # 或 set -o noclobber; > "<out>.lock"     # O_CREAT|O_EXCL 等價
     # 成功 → 寫 attempt id / pid / UTC epoch → 啟動 CLI
     # 失敗 → 重讀 lock 判 stale：
     #   非 stale → 拒絕啟動（不寫 result_state，只記拒絕事件）
     #   stale    → 走下方 takeover 協定（禁裸刪重建）
     # lock-create 或 process-discovery 任一錯誤 → fail-closed（拒絕啟動）
     ```
  8. **stale takeover 協定（禁裸刪重建）**：
     ```
     ① mkdir "<out>.reclaim.lockdir"   # 原子取得回收權；EEXIST → 直接拒絕，不得碰主 lock
     ② 重讀主 lock，確認 attempt id 仍 == 先前觀察到的 stale owner
        不相等 → 已被他人接管，不得刪除，直接拒絕
     ③ 相等才刪除主 lock，並以①同款原子操作建立新 lock
        建立失敗 EEXIST → 拒絕，不得再刪
     ④ 無論成敗，最後釋放回收權（rmdir），釋放前確認回收權仍為自己所有
     ```
     🔴 **已知殘留（見 §0 第 2 條）**：③與④之間 crash ⇒ reclaim 孤兒 ⇒ 該 `<out>` 鎖死待人工清理。
     **本批修法三擇一，實作者定**：(a) 清 orphan 的運維腳本 (b) reclaim lock 加 TTL／lease（owner token＋pid＋時間戳）＋受保護的 stale-reclaim CAS (c) 改用 crash 自動釋放的 `flock`（⚠️ macOS 無 `flock`，選此須另附相容方案）。
     **不論選哪個，§0 第 2 條的宣告不得移除。**
  9. **release**：`_emit_family_result` 寫入後**必定釋放**（無論 `success`／`failed`／`format-failed`），
     **不依賴 publish 是否成功**；釋放前**必須比對 lock 內的 attempt id 與自己相同**，不同即**不得釋放**。
  10. **存活判準**：「lock 檔存在 **且** 其 pid 存活」**或**「該 `<out>` 的 attempt 進程存活」**二者取聯集**；
      任一為真即拒絕啟動。⇒ **刪 lock 檔不足以繞過序列化。**
- **修改檔案**：`scripts/cx_run.sh`（產出路徑處理、`_emit_family_result`、`:512` prompt）；
  `scripts/new_brief.sh`／`scripts/brief_conformance_check.sh` 的骨架文字（產出路徑說明）。
  **既有 caller**：`committee_run.sh` 呼叫 `cx_run.sh`（產出路徑由 wrapper 管理，caller 不需改）。
- **不可做**：不得繞過 terminal marker 自行判定完整性；不得以「檔案存在」當 marker。
- **邊界**（≥2）：①同 `<out>` 兩次派工並發 → 恰一個啟動 ②CLI 被 SIGKILL（wrapper 存活）→ 依 stale 回收 ③跨裝置 rename 失敗 → 仍走 `_emit_family_result` 記 `failed` 並 owner-safe 釋放 ④外部刪 lock 但進程存活 → 仍拒絕。
- **風險緩解**：`RISK-b`＋`RISK-c` — Phase 3 獨立 commit 可單獨 revert；lock 相關全部 fail-closed。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-3.2-INVISIBLE`（狀態）：CLI 執行期間 `<out>` **不存在**、attempt 檔存在；正常結束後 `<out>` 存在且 attempt 檔已清除。
  - `TEST-3.2-FORMATFAIL`（狀態）：格式不合格時 attempt 檔**仍存在**且 `<out>` 不存在，`result_state=format-failed`。
  - `TEST-3.2-STALE`（狀態）：預先放置舊 `<out>`，CLI 逾時未 publish ⇒ **不得判 `success`**；audit 須顯示該 `<out>` 非本 attempt。
  - `TEST-3.2-B30`（狀態）：以「寫入 → 清空 → 重寫」序列模擬 codex 事故，最終 `<out>` **等於最後一次寫入**，且警示已記入 audit。
  - `TEST-3.2-PROMPT-ALIGN`（狀態）：`cx_run.sh` 產生的 prompt 內產出路徑 **==** wrapper 實際期待的 attempt 路徑
    （**同一來源，測試比對兩者字串相等**）。
  - `TEST-3.2-LOCK-①`～`⑧`（狀態，逐路徑）：①`failed` 後同 `<out>` 重派放行 ②pid 已死的 stale lock 重派放行且 audit 有接管紀錄
    ③被拒 attempt 在 audit **無 `committee_family_result`** 且 Task 3.1 duration 統計筆數**不增加**
    ④owner-safe release：舊 attempt 走 `_emit_family_result` → **lock 不得被釋放** ⑤wrapper SIGKILL 後經 stale 判定重派放行
    ⑥外層 timeout 殺 `cx_run.sh` → lock 由 stale 回收，**外層不直接刪 lock** ⑦外部刪 lock 但進程存活 → 第二次派工仍**拒絕**
    ⑧跨裝置 rename 失敗 → `result_state=failed` 且 lock 已 owner-safe 釋放。
  - `TEST-3.2-LOCK-⑨`（狀態，**原子取得 barrier race**）：兩 dispatcher 對同一 `<out>` 在 precheck 後以 **barrier 同步**
    （**不得用 `sleep` 競速，須 deterministic**），**恰有一個** CLI 啟動、另一個 rc≠0；loser **不寫 `result_state`**。
    **反向 mutation**：換回「先檢查再建立」兩步 ⇒ 本斷言**必須 FAIL**（出現兩個 `START`）。
  - `TEST-3.2-LOCK-⑩`（狀態）：`mkdir`／`O_EXCL` 因權限或 I/O 失敗（非 EEXIST）⇒ **拒絕啟動**，不得視為「無鎖」放行。
  - `TEST-3.2-LOCK-⑪`（狀態）：注入 process-discovery `EIO`／權限錯誤 ⇒ **rc≠0、CLI 不啟動、不寫 `result_state`、只記拒絕 audit**。
    **反向 mutation**：改為「當作無存活進程」放行 ⇒ 本斷言**必須 FAIL**。
  - `TEST-3.2-E9-ORDER`（狀態，**publish 與 timeout 的順序契約**；`E-9`／`CODEX-R2-P1-08`；
    `COMPOSER-TODO-P1-02` 指出主委初版完全漏列此 Test ID）：
    ①**先 CLI wait 返回，才做格式檢查與 publish**（不得在 CLI 仍執行時 publish）；
    ②audit 中該 **attempt id** 的 `committee_family_result` **計數 == 1**（`grep -c` 導出，**恰一筆，不多不少**）；
    ③timeout 觸發與正常返回**競態時**仍維持②（邊界①的同一情境）。
    **反向 mutation**：把 publish 移到 CLI wait 之前 ⇒ ①轉紅；移除「每 attempt 恰一筆」的守衛 ⇒ ②轉紅。
  - `TEST-3.2-LOCK-⑬`（狀態，**③→④ crash 的 reclaim 孤兒**；`CODEX-TODO-P1-04` 要求補）：
    以 deterministic probe 在協定步驟③完成後、④之前 **SIGKILL** 持有者 ⇒ 斷言
    ①`<out>.reclaim.lockdir` **仍存在**（孤兒）②主 lock **存在且屬新 attempt**
    ③後續第三個 dispatcher 於步驟① **EEXIST 拒絕**（rc≠0、CLI 未啟動、不寫 `result_state`）。
    🔴 **本測試的目的是「把已知殘留釘成可重現的既定行為」，不是宣稱已修**——
    §0 第 2 條的「需人工清理」宣告即以本測試為證據。**實作者若選了修法 (a)/(b)/(c) 其中之一，
    須把本測試的斷言③改為「可自動回收」並附對應 mutation；未改則 §0 宣告不得移除。**
  - `TEST-3.2-LOCK-⑫`（狀態，**stale takeover 序列化**）：A、B 皆判同一 lock 為 stale，以 deterministic barrier 同步後各自嘗試接管
    ⇒ **`STALE_TAKEOVER_STARTS == 1`**，且 audit 中該 `<out>` 的 lock attempt id 序列**恰 1 次**變更。
    **反向 mutation**：移除 `<out>.reclaim.lockdir` 回收權**或**移除「重讀比對 observed owner」⇒ 本斷言**必須 FAIL**（2 個 `START`）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 3.3 — per-family timeout 與逾時後的 `result_state`

- **SPEC ref**：Task 3.3　**目標**：委員掛住時自動收斂，且不誤判成功。**值的定稿依賴 Task 3.1。**
TASK-STATUS: INCOMPLETE

- **🔴 本 Task 未完工**（依 §0 第 3 條，Task 3.1 尚未上線、三家族累積筆數為 0）。
  狀態以上方**機器標記行**為準，**不以散文敘述為準**（見下方驗證段的三次出生事故）。
- **輸入 / 輸出**：輸入＝Task 3.1 的 duration manifest；輸出＝`cx_run.sh` 主 timeout ＋ `committee_run.sh:280` 外層安全閥 ＋ 測試。
- **實作要點**：
  1. **主 timeout 在 `cx_run.sh`**：涵蓋區間＝**CLI process-group launch → return/kill**，逾時終止該**進程群組**（避免孤兒）。
  2. **外層安全閥在 `committee_run.sh:280`**：上限**略大於**主 timeout；只在主 timeout 失效時作用。
  3. **逾時後判定**：本 attempt 已 publish → 依格式檢查落 `success`／`format-failed`；未 publish → **`failed`**。
     **不新增第四個 `result_state` 值**（SoT 見 `scripts/audit_events.json`）。
  4. **值與定稿門檻（`E-10`）**：
     ```
     暫定值（PROVISIONAL）：codex 50m / grok 70m / composer 75m / 外層 90m
     定稿門檻：每家族累積 ≥50 筆 committee_family_result（result_state=success、含 duration 三欄）
               且該 50 筆跨 ≥3 個不同 session / UTC 日期
     計算：timeout_family = ceil(max(max(duration), P99(duration) × 1.25))
           外層 = max(family_timeouts) + 15m
     未達門檻：機制照常上線並以暫定值運作，值逐行標 PROVISIONAL，
               Task 3.3 不得宣稱完工，票 B-14 保持「未定稿」
     ```
     🔴 **只有「達標／未達標」兩種狀態，無中間灰區**（含 10–19 區間）。
     🔴 與 codex 原主張「未達門檻不得用暫定值」的差異理由：**無 timeout 正是 `B-14` 事故成因**（空等 2h20m），
     「有暫定 timeout」嚴格優於「無 timeout」。此取捨經 R2 收斂 `E-10` 明示並獲三家戳記 APPROVED。
     ⑤歷史 runlog proxy（n=462）僅作 sanity check，**不可替代** Task 3.1 欄位。
  5. 值須**可由環境變數覆寫**以利測試。
- **修改檔案**：`scripts/cx_run.sh`（主 timeout 包裹 CLI 呼叫）；`scripts/committee_run.sh:280`（外層安全閥）。
  **既有 caller**：`committee_run.sh` 呼叫 `cx_run.sh`。
- **不可做**：**不得只加 timeout 就殺**（`票 B-14` 明載：會把已完成的審查誤判為失敗）；
  **不得繞過 Task 3.2 的 terminal marker 自行判定完整性**。
- **邊界**（≥2）：①CLI 在 timeout 邊界正常結束（競態）→ **不得寫兩筆 `result_state`** ②timeout 值為 0 或負 → **拒絕啟動並報錯** ③三家並行時其中一家逾時 → **其餘兩家不受影響**。
- **風險緩解**：`RISK-c` — 環境變數可覆寫，緊急時可調大。
- **驗證**（Test ID ＋ 可證偽通過條件；每條落為 `pytest tests/governance/` 斷言，rc 直接取）：
  - `TEST-3.3-HANG`：`ASSERT bash scripts/cx_run.sh WHEN cli=hang timeout_sec=1 THEN rc!=0`
  - `TEST-3.3-FAILED`（狀態）：上述情境 audit 的 `result_state` 為 **`failed`**，且 `<out>` **不存在**、attempt 檔**存在**。
  - `TEST-3.3-SUCCESS`（狀態）：CLI 在 timeout 內正常結束且格式合格 → `result_state=success`、`<out>` 存在。
  - `TEST-3.3-ORPHAN`（狀態）：逾時後查不到該 CLI 的殘留子進程（**以 process group 為單位斷言**，`pgrep -g <pgid>` 無輸出）。
  - `TEST-3.3-VALUE-SRC`（狀態）：TODO 中的 timeout 值與 Task 3.1 產出的 duration manifest **一致**
    （**禁硬編未經重算的暫定值**）。
  - `TEST-3.3-PROVISIONAL`（狀態，**`E-10` 取捨的可證偽化**；`CODEX-TODO-P1-04` 修正為**可解析來源**）：
    未達定稿門檻（`handoffs/duration_manifest.json` 的 `.status == "PROVISIONAL"`）時，三條件**任一缺失即 FAIL**——
    ①`jq -r .status handoffs/duration_manifest.json` **== `PROVISIONAL`**；
    ②本 TODO 的 Task 3.3 段落**含機器標記行** `TASK-STATUS: INCOMPLETE`（見本 Task 標頭，`grep -c '^TASK-STATUS: INCOMPLETE'` **== 1**）；
    ③`票 B-14` 的 bounded section（`^## B-14 ` 起至下一個 `^## B-` 前）**含且僅含一行** `TICKET-STATUS: PROVISIONAL`。
    🔴 **本條的三次出生事故（同型錯誤，記為 `票 B-16`／`B-17` 佐證）**：
    **(i)** 主委初版寫「`票 B-14` 票面含『未定稿』」，實測 `grep -c` **== 0** ⇒ 條件恆為 FAIL（`CODEX-TODO-P1-04`）。
    **(ii)** 主委補寫狀態段後，條件②的 `grep -c '…未完工…' == 1` **實測為 2**——
    **測試定義本身就含該字串，自我引用**（`CODEX-R8`／`COMPOSER-R8` 兩家獨立指出）。
    **(iii)** 主委為 `票 B-24` 補狀態段時，在否定敘述中提到被禁的關鍵字，
    使該詞 `grep -c` 由 0 變 4，**又把自己的測試弄壞**。
    ⇒ **結論：散文關鍵字比對本質脆弱**（任何討論該詞的句子都污染計數，且無法區分「宣稱」與「否定宣稱」）。
    **本批全面改用單一機器標記行**（`TICKET-STATUS:` ／ `TASK-STATUS:`），語意明確、不受行文影響。
  - `TEST-3.3-B24-PARTIAL`（狀態）：`票 B-24` 的 bounded section 內
    **含且僅含一行** `TICKET-STATUS: PARTIAL`（`grep -c '^TICKET-STATUS: PARTIAL'` **== 1**），
    且**不得**出現 `TICKET-STATUS: DONE`（`grep -c` **== 0**）。
  - `TEST-3.3-H2-RESIDUAL`（狀態）：本 TODO §0 第 2 條含**行首錨定**的機器標記——
    `grep -c '^RESIDUAL: reclaim-orphan-manual-cleanup' docs/GOVB0_FRICTION_TODO.md` **== 1**；
    且實作產出文件中 `grep -c '^LOCK-STATUS: COMPLETE'` **== 0**。
    🔴 **所有標記斷言一律行首錨定 `^`**——這是本日同型陷阱第五次的通解：
    未錨定時，**測試定義自身提到該標記就會被計進去**（實測 `RESIDUAL` 未錨定為 2、錨定後為 1）。
    ⇒ **機器標記必須寫在行首、斷言必須帶 `^`**，兩者缺一即自我污染。
  - `TEST-3.3-MUT`（mutation）：移除 timeout → 掛住情境測試逾時失敗（**測試自身須有上限**，避免測試本身掛住）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Phase 3 測試 ＋ Gate

- 單元：lock 協定各分支　邊界：並發／SIGKILL／跨裝置／timeout 邊界　整合：一次真實三家派工。
- **Phase 3 Gate**：`pytest tests/governance/test_atomic_publish.py tests/governance/test_family_timeout.py -q` rc=0，
  含 `TEST-3.2-LOCK-⑨`～`⑫` 四條並發斷言與其反向 mutation。

---

## §T 追溯表（**本批 in-scope Task 覆蓋 ＋ 明列排除清單**）

🔴 **標題已由「100% 覆蓋」改為現名**（`CODEX-R8-P1-04`）：主委初版宣稱 100% 覆蓋，
但 SPEC 的具名殘留 `F-7`／`票 B-36`（ID 錯位無機械防線）**沒有任何 TODO 落點**——
下游若把 §T 當完整追溯索引就會漏掉。**本表現在明確區分「有落點」與「具名排除」兩類。**

### 具名排除（**不在本批施工範圍，但必須被看見**）

| SPEC 具名項 | 為何排除 | 後續落點 |
|---|---|---|
| `F-7`／`票 B-36` **ID 錯位無機械防線** | 產出端修法只能擋「漏」不能擋「錯位」；本批無機械解 | 已裁定併入 `票 B-13`（第 3 批） |
| `E-SCOPE` 四項 | R2 起三家＋使用者雙重核可 | `B-35`／`B-34`／`B-24` 機械強制面／`B-15` FP-2 |
| `H-1` 允許清單枚舉不完整 | 方向為 fail-closed（誤擋），可隨 Phase 0 資料收斂 | 補查條件同 `B-15` FP-2 |
| `H-2` reclaim 孤兒 | 已具名接受，修法落 TODO 運維項 | §0.1 第 2 條 ＋ Task 3.2 要點 8 |
| `OPEN-2`／`D-8` locale 守衛 | 與本批無關聯，硬塞會撐爆範圍 | `票 B-33`（第 1.5 批） |

### In-scope 覆蓋表

| SPEC ID | TODO 位置 | SPEC ID | TODO 位置 |
|---|---|---|---|
| Task 0.1 | Phase 0 / Task 0.1 | Task 3.1 | Phase 3 / Task 3.1 |
| Task 1.1 | Phase 1 / Task 1.1 | Task 3.2 | Phase 3 / Task 3.2 |
| Task 2.0 | Phase 2 / Task 2.0 | Task 3.3 | Phase 3 / Task 3.3 |
| Task 2.1 | Phase 2 / Task 2.1 | `E-SCOPE` 四項 | §0.2 ＋ Task 3.2 要點 5 |
| Task 2.2 | Phase 2 / Task 2.2 | `H-1` 允許清單殘留 | Task 2.0 要點 4 |
| Task 2.3 | Phase 2 / Task 2.3 | `H-2` reclaim 孤兒 | §0.1 第 2 條 ＋ Task 3.2 要點 8 |
| Task 2.4 | Phase 2 / Task 2.4 | `B-24` 紀律面 | §0.1 第 1 條 ＋ §0.5 |
| Task 2.5 | Phase 2 / Task 2.5 | `E-10` PROVISIONAL | §0.1 第 3 條 ＋ Task 3.3 |

**SPEC Task 總數 11**（導出命令 `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md`）
**== 本 TODO Task 總數 11**（導出命令 `grep -c '^### Task ' docs/GOVB0_FRICTION_TODO.md`）。
🔴 **code review 須機械核對此兩數相等**（`票 B-17` 病型：本 SPEC 制定過程中同型計數已漂 8 次）。

## §R 回退

- **每 Phase 獨立 commit，可單獨 revert。**
- 依賴：Phase 0 → Phase 2；Phase 1 → Phase 3。**Phase 0 與 Phase 1 彼此獨立，可並行。**
- **Phase 2 為最高風險**（改判定放行／擋下）：逃生口＝環境變數一鍵回舊判定
  （**僅供緊急回退，非預設關閉**——依使用者定死「驗過就別預設關閉」，Task 2.5 報表 rc=0 後新判定即為預設）。
- 差集報表出現「非預期」項 → **不 merge**。
- Phase 0 為純觀測（判定行為不變），**可最先 merge**。
- 任一 Phase 使既有測試轉紅且無具名理由 → **不 merge**。

---

`SPEC=docs/GOVB0_FRICTION_SPEC.md TODO=docs/GOVB0_FRICTION_TODO.md FOCUS=完整審查（重點：追溯完整性、深度紅線、§0 三項狀態宣告是否可機械驗證）`
