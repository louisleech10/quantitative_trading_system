# G-7FIX：G-7 context 切分與便宜閘假閘修復 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260905-g7perf-x-consult-r2/synth.md`（處置方向）、`handoffs/reconcile/20260905-g7fix-x-consult-r1/synth.md`（群集 A–K）、`handoffs/reconcile/20260905-g7fix-x-consult-r2/synth.md`（群集 α–ι，本 SPEC 之直接輸入）　|　日期：2026-09-05　|　對應 TODO：`docs/G7FIX_TODO.md`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。
- **命中高風險原則**：(b) 跨模組/共用路徑——`govb1_final_gate.sh`／`g7_trailer_precheck.sh`／`gov_check.sh` 為每次 commit 與 push 皆經過之共用治理控制流；(c) 多 phase/難回退——引入 `epic_state` 狀態機，錯誤的預設方向或轉態謂詞會靜默關閉既有保護。
RISK-HIT: b,c
- 未命中 (a)／(d) ⇒ §G 移 §N 標 N/A。

## §A 假設與待使用者確認（事故：拿推論代替問人）

**已驗證事實（FACT-RECEIPT ×11，逐條附實跑輸出）**
- FACT-RECEIPT: `grep -n "fast\|govb1_final_gate" scripts/gov_check.sh` → 印出 `:266-267` `--fast` 早退、G-7 段在 `:343-350`；`sed -n '46p' scripts/git_hooks/pre-push` → `_GC_MODE="--fast"`（Claude 實跑 2026-09-05）
- FACT-RECEIPT: `bash scripts/govb1_final_gate.sh --print-scope | wc -l` → 印出 `51`（Claude 實跑 2026-09-05）
- FACT-RECEIPT: `grep -n "_G7_OOE_VALUE_RE" scripts/govb1_final_gate.sh` → 印出僅 `427`（定義）與 `462`（消費）兩行，`g7_trailer_precheck.sh` 未取用（Claude 實跑 2026-09-05）
- FACT-RECEIPT: `rg -n "_FROZEN_CLOSED_KEYS" .` → 印出唯一定義 `tests/governance/test_govb1_contract_matrix.py:180`，無第二副本（grok 實跑 2026-09-05）
- FACT-RECEIPT: `rg -n "epic_state|dormant|active" scripts/govb1_final_gate.sh scripts/gov_check.sh scripts/g7_trailer_precheck.sh` → 印出零命中（codex 實跑 2026-09-05）
- FACT-RECEIPT: `git show HEAD:scripts/govb1_frozen_hashes.txt | grep -c '^epic_state:'` → 印出 `0`（codex 實跑 2026-09-05）
- FACT-RECEIPT: `git config --get core.hooksPath` → 印出 `scripts/git_hooks`；`bash scripts/verify_hooks_health.sh` → `HEALTH OK` rc=0（codex 實跑 2026-09-05）
- FACT-RECEIPT: `git diff --name-only --diff-filter=ACMRD $(_base) HEAD` → 印出含 `docs/GOVB1_INPUT_QUALITY_TODO.md`、`scripts/govb1_frozen_hashes.txt`、`scripts/govb1_scope.manifest` 三條硬保護路徑（grok 實跑 2026-09-05）
- FACT-RECEIPT: `rg -n --glob '!tests/**' --glob '!docs/site/**' --glob '!handoffs/**' -- '--no-probe|--only g7|pre-push.*全套|pre-push.*G-7|G-7.*pre-push' scripts docs | wc -l` → 印出 `62`（codex 實跑 2026-09-05）
- FACT-RECEIPT: `jq -c '.["governance-enforcement"].target' scripts/fact_keys.json` → 印出 `['docs/GOV_ENFORCEMENT_REGISTRY.md','docs/GOV_TICKET_SOT.md']`（codex 實跑 2026-09-05）
- FACT-RECEIPT: `rg -n 'line_count|整檔|govb1_frozen_hashes.*sha' tests/governance --glob '*.py'` → 印出零命中（composer 實跑 2026-09-05）

**未實證、施工後必補之查核**（來自 R2 synth 末段；不得當已驗）
- U-1：擴 `_FROZEN_CLOSED_KEYS` 的連鎖影響——三家皆未跑全套 `pytest tests/governance`（十分鐘級，前景必逾時）。收案條件見 §V。
- U-2：缺鍵預設方向——僅以 reader 模擬驗證，未真跑 `bash scripts/govb1_final_gate.sh --only g7` 前後對照。驗收須含一次真跑。

**待確認：無**
**已確認結果**：`2026-09-05 使用者裁定「四步一起做完，不掛到 B-D4 之後」`；`2026-09-05 使用者選定「先跑 consult R2 確認修補案」，R2 已收斂`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條：本票只動 `scripts/`／`docs/`／`tests/governance/`，不觸 `momentum/`／`api/`／`frontend/`，7 條不受影響。
- 本任務特別注意：
  - `scripts/govb1_frozen_hashes.txt` 為 `_G7_OOE_HARD_PROTECTED` 成員（`govb1_final_gate.sh:379-382`），同時在 `scripts/govb1_scope.manifest:32` 為 `allow`——**兩個身分並存**是群集 β 的根因，改動時不得只看其中一邊。
  - 既有 caller：`scripts/git_hooks/commit-msg:18-22` → `g7_trailer_precheck.sh`；`scripts/git_hooks/pre-push:46` → `gov_check.sh --fast`；`gov_check.sh:343-350` → `govb1_final_gate.sh --only g7`。
  - `tests/governance/test_g7_trailer_precheck.py:104-107` 釘死「active＋in-scope 無 trailer 可過」，為群集 ε 之 active 基線，**不得為求綠燈修改該斷言**。
- **本 SPEC 不定義新資料結構檔**：`epic_state` 為既有 `scripts/govb1_frozen_hashes.txt` 之新增鍵，值域枚舉之唯一真相源＝Phase 1 之 production parser（`_FROZEN_ENUM_KEYS`），SPEC 只 pointer，不在散文中重列值。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 1 — `epic_state` 契約與 production parser（依賴：無）

**Task 1.1 — production parser 落點與共用**
- 目標：建立**唯一**的 production `epic_state` 讀取實作，供三支腳本共用。
- 檔案：`scripts/govb1_final_gate.sh`（新增 `_epic_state()` 與 CLI 出口 `--print-epic-state`）；`scripts/gov_check.sh`、`scripts/g7_trailer_precheck.sh` 透過該出口取用。
- 既有 caller/影響面：`gov_check.sh:343-350`、`g7_trailer_precheck.sh:66-68`（現行已用 `--print-scope` 同模式取 gate 輸出）。
- 改法：
  - **單一 helper**〔`CODEX-R1-P1-07`〕：`_parse_epic_state_from_text()` **吃文字、不吃路徑**，為全票唯一之 state 判準實作。
    `_epic_state()` 讀宿主檔後呼叫它；轉態（Task 2.1）把兩個 blob 餵**同一個** helper。禁任何「同構的第二份 parser」。
  - 🔴 **禁 env 覆寫**〔`CODEX-R1-P0-02`／`GROK-R1-P0-01`／`COMPOSER-R1-P1-02`〕：`_epic_state()` 一律讀 repo root 下**固定相對路徑** `scripts/govb1_frozen_hashes.txt`，**不得**引入 `GOVB1_FROZEN_HASHES` 或任何 caller-controlled path override。
    `gov_check.sh` 與 `g7_trailer_precheck.sh` 呼叫本出口前一律 `env -u GOVB1_FROZEN_HASHES`（與 `gov_check.sh:305-314` 對 `GOVB1_FACTKEY_ROOT` 同形；理由逐字相同：強制點必須自己決定檢查對象）。
    測試以**隔離 repo 之真實相對路徑**建 fixture，不給 production reader 覆寫鉤子。
  - 語意分岔（寫死，不得由呼叫端覆寫）：鍵**缺席** ⇒ stdout `active`、rc=0；鍵存在但**重複**／**格式不符**／**值不在枚舉** ⇒ rc≠0（fail-closed），stderr 具名原因。
  - CLI 出口（`--print-epic-state`；另 `--parse-epic-state-stdin` 供 Task 2.1 餵 blob）置於 `_plan` 之前 exit（同 `:780-786` 之 `--print-scope` 模式），避免進入 G-2 `_CHECKS` 函式存在性檢查〔`COMPOSER-R1-P2-02`〕。
- **驗證（可證偽）**：新增 `tests/governance/test_govb1_epic_state.py`，含下列 4 條 ASSERT；`pytest` 全綠
  - `ASSERT bash scripts/govb1_final_gate.sh --print-epic-state WHEN frozen_key=absent THEN rc=0`（且 stdout 恰為 `active`）
  - `ASSERT bash scripts/govb1_final_gate.sh --print-epic-state WHEN frozen_key=dormant THEN rc=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --print-epic-state WHEN frozen_key=duplicate THEN rc!=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --print-epic-state WHEN frozen_key=bad_value THEN rc!=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --print-epic-state WHEN env_override=fake_dormant_file THEN rc=0`（且 stdout 恰為宿主檔之值，證明 env 無效）
  - `bash scripts/govb1_final_gate.sh --print-plan` rc=0 且輸出無 `UNRESOLVED`
  - mutation：把固定路徑改回 `${GOVB1_FROZEN_HASHES:-...}` ⇒ `env_override=fake_dormant_file` 那條須轉紅。
  - mutation：對 `_parse_epic_state_from_text()` 做一個 enum／空白處理之改動 ⇒ 本 Task 與 Task 2.1／2.2 之測試須**同時**轉紅（證明確為同一 helper，非同構第二份）。
- **邊界（≥2）**：① 凍結檔不存在 ⇒ rc≠0，不得回退成 `active`（否則刪檔即關閘）；② 凍結檔可讀但為空 ⇒ rc≠0。
- **存活至**：Phase 6 完工後仍保留（為 Phase 2–4 之唯一 state 來源）。
- **覆蓋風險**：無。
- 不可做：不得在 `gov_check.sh` 或 `g7_trailer_precheck.sh` 內各自 `grep '^epic_state:'`（群集 α 之根因即為此類複寫）。

**Task 1.2 — 測試端契約擴充（封閉集 ＋ 枚舉分支）**
- 目標：使測試契約接受 `epic_state`，且值域走枚舉分支而非 12-hex 分支。
- 檔案：`tests/governance/test_govb1_contract_matrix.py`（`_FROZEN_CLOSED_KEYS` `:180`、`_parse_frozen_hashes` 值域分支 `:205-212`）。
- 改法：`_FROZEN_CLOSED_KEYS` 加入 `epic_state`；新增 `_FROZEN_ENUM_KEYS = {"epic_state"}` 與其允許值集合，於 `_parse_frozen_hashes` 中**先於** 12-hex else 分支判定。測試須呼叫 Task 1.1 之 production 出口作交叉驗證，不得只驗 test-local parser。
- **驗證（可證偽）**：`venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q` 全綠；且新增一條斷言：production `--print-epic-state` 與 test-local parser 對同一 fixture 給出相同結果。
  - mutation〔R2 群集 α⑤〕：刪除 `_FROZEN_ENUM_KEYS` 分支、讓 `epic_state` 掉回 12-hex else ⇒ 「`epic_state: dormant` 可解析」之斷言須轉紅。
  - mutation：把 `_FROZEN_CLOSED_KEYS` 改成開放集 ⇒ 「未知 third key 須 FAIL」之既有斷言須轉紅。
- **邊界（≥2）**：① `epic_state` 值為 12-hex 字串（如 `deadbeef0000`）⇒ 須 FAIL（證明沒有掉回 hex 分支）；② 同時出現兩行 `epic_state:` ⇒ 須 FAIL。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得為求綠燈放寬 `_FROZEN_CLOSED_KEYS` 成開放集（會打開「任意 third key」後門〔`GROK-R1-P0-01`〕）。

### Phase 2 — 轉態謂詞（依賴：Phase 1）

**Task 2.1 — old/new state 讀取**
- 目標：在 commit-msg 階段取得轉態前後之 state，來源明確不可由實作者發明。
- 檔案：`scripts/g7_trailer_precheck.sh`（新增 `_transition_states()`）。
- 改法（偽碼逐字採 R2 群集 γ 之三家實構結果）：
  ```
  old_blob="$(git show HEAD:<path>)"   # rc≠0（初始 commit／無 HEAD）⇒ 拒轉態，fail-closed
  new_blob="$(git show :<path>)"       # index blob；**不得**讀工作樹
  old/new 兩個 blob 皆餵 Task 1.1 之 `_parse_epic_state_from_text()`（經 `--parse-epic-state-stdin`）；解析失敗 ⇒ fail-closed
  ```
  🔴 **同一 helper，非同構**〔`CODEX-R1-P1-07`〕：不得為 blob 另寫一份 parser。
- **驗證（可證偽）**：新增 `tests/governance/test_g7_transition.py`，含下列 2 條 ASSERT ＋ 1 種 mutation；`pytest` 全綠
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN head=absent staged=transition THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN head=present staged=transition_legal trailer=epic_state THEN rc=0`
  - mutation：把 `HEAD:` 改成 `HEAD~1:` ⇒ 上列第二條須轉紅。
- **邊界（≥2）**：① detached HEAD ⇒ 行為與 `head=present` 相同（不得因 symbolic ref 缺失而誤拒）；② `git commit --amend` ⇒ 判定對象為 amend 後之最終 staged 集合。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得以 `cat <path>`／工作樹內容替代 index blob。

**Task 2.2 — 轉態謂詞（map 相等，雙向封閉）**
- 目標：轉態只在「恰好且只有 `epic_state` 值改變」時成立，且**升級與降級套用同一組條件**。
- 檔案：`scripts/g7_trailer_precheck.sh`（`_is_legal_transition()`）。
- 改法：
  - **map 相等**（非行 diff）：`old \ {epic_state} == new \ {epic_state}` 作為集合相等；拒缺鍵／重複鍵／未知鍵。
  - **共同條件**（兩個方向皆須滿足）：staged 路徑恰一條且為 `scripts/govb1_frozen_hashes.txt`、git status 恰為 `M`（拒 `T`/`R`/`C`）、目標為 regular file（非 symlink）、commit 訊息末段之 `Governance-Scope` key **恰出現一次**。
  - **方向不對稱**〔`CODEX-R1-P0-01`〕——降級須有可驗證之授權來源，升級不須：
    - `dormant→active`（**提高**保護）：trailer 值恰為 `govb1-epic-state active[<空白><理由>]`。
    - `active→dormant`（**降低**保護）：trailer 值恰為 `govb1-epic-state dormant ruling:<ID>`，且 `<ID>` 須在 **`docs/GOV_ENFORCEMENT_REGISTRY.md`**（tracked）中字面存在（一次 `grep -qF`，不增子行程）。該登記列由 Phase 5 先行寫入。
    - 🔴 授權來源**不得**取自 `handoffs/`（gitignored，不可當授權），亦不得由 commit 自行宣稱。
  - 其餘任何情形一律非轉態，退回一般判定流程。
- **驗證（可證偽）**：`tests/governance/test_g7_transition.py` 含下列 7 條 ASSERT；`pytest` 全綠
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=legal_upgrade THEN rc=0`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=legal_downgrade THEN rc=0`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=other_key_changed THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=typechange_symlink THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=duplicate_scope_trailer THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=extra_staged_file THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=key_reordered THEN rc=0`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=downgrade_no_ruling THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN transition=downgrade_ruling_absent_in_registry THEN rc=1`
  - mutation：移除 ruling 檢查 ⇒ `transition=downgrade_no_ruling` 須轉紅。
  - mutation〔R2 群集 β〕：刪除 downgrade 分支（使降級落回一般流程）⇒ `transition=legal_downgrade` 須轉紅。
  - mutation〔R2 群集 δ〕：把 map 相等改成「`diff -u` 無其他 +/- 行」⇒ `transition=key_reordered` 須轉紅。
- **邊界（≥2）**：① 凍結檔鍵重排但值全同（`key_reordered`）⇒ 須成立（行 diff 會誤判，map 不會）；② `epic_state` 值尾帶空白 ⇒ 須拒（不得以 strip 吞掉後放行）。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：🔴 **不得**以「`diff -u` 無其他 `+`/`-` 行」實作 map 相等——R2 群集 δ 已明訂此為「本條未修」之判準。
- 不可做：不得只封單向（群集 β 為本 SPEC 新引入之 P0，降級路徑同樣關閉整個閘）。

### Phase 3 — 便宜閘：三洞修復與分模式控制流（依賴：Phase 1、Phase 2）

🔴 **本 Phase 實作序寫死＝Task 3.4 → 3.1 → 3.2 → 3.3**〔`GROK-R1-P2-01`〕。
理由：3.3 之控制流呼叫 3.4 提供的 `_staged_paths_nul`；若按 Task 號順序施工，實作者會先內聯一份路徑收集再抽函式，正是 Task 3.4 要禁的漂移。Task 號僅為編號，不是施工序。

**Task 3.1 — gate 端新增兩個單一來源出口**
- 目標：讓便宜閘不自寫判準。
- 檔案：`scripts/govb1_final_gate.sh`（`--print-ooe-value-re` 印 `_G7_OOE_VALUE_RE`；`--print-protected` 印 `_G7_OOE_HARD_PROTECTED`），兩者皆置於 `_plan` 之前 exit。
- **驗證（可證偽）**：兩出口 rc=0 且 stdout 非空；`--print-plan` 仍 rc=0 且無 `UNRESOLVED`。
  - mutation：使 `--print-ooe-value-re` 回傳空字串 ⇒ Task 3.2 之 `exporter=missing THEN rc=1` 須仍為綠、而 `trailer_value=out-of-epic THEN rc=0` 須轉紅（證明便宜閘真的依賴該出口而非自寫）。
- **邊界（≥2）**：① 出口不存在或 rc≠0 ⇒ 便宜閘 fail-closed 擋（見 Task 3.2）；② 出口輸出為空 ⇒ 同樣 fail-closed。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得在便宜閘複寫 regex 或硬保護清單字面。

**Task 3.2 — 洞 A／洞 B：trailer 值域改向消費端取**
- 目標：便宜閘之 trailer 判準與昂貴閘一致。
- 檔案：`scripts/g7_trailer_precheck.sh:97-107`。
- 改法：以 `--print-ooe-value-re` 取得 regex 後 `grep -qE "${re}"` 判**值**；取不到（rc≠0 或空）⇒ **fail-closed 擋**。
  🔴 與 scope 導出失敗（`:63-75`）之處置**刻意不同**：scope 導不出來仍可要求 trailer 而不死鎖；但值的合法形態取不到即無從判定，放行等於無閘。
- **驗證（可證偽）**：`tests/governance/test_g7_trailer_precheck.py` 含下列 4 條 ASSERT ＋ 1 種 mutation；`pytest` 全綠
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN staged=uncovered_nonhard trailer_value=out-of-epic THEN rc=0`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN staged=uncovered_nonhard trailer_value=in-epic THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN staged=uncovered_nonhard trailer_value=out-of-epic-extra THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN staged=uncovered_nonhard exporter=missing THEN rc=1`
  - mutation：還原成「只驗非空」⇒ `trailer_value=in-epic` 那條須轉紅。
- **邊界（≥2）**：① `out-of-epic <理由>` 須放行（`<理由>` 為自由文字）；② `scope 導出失敗 ＋ trailer_value=in-epic` ⇒ rc=1（證明洞 B 隨洞 A 一併收斂）。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得因取不到出口而放行。

**Task 3.3 — 洞 C：硬保護集納入便宜閘，並寫死判定順序**
- 目標：修好洞 C 且不新增死鎖（群集 E／ε）。
- 檔案：`scripts/g7_trailer_precheck.sh`（主控制流）。
- 改法——**分模式**寫死，不得寫成單一流程再加分支旗標：
  - **`epic_state=active`**：① `_is_legal_transition` → 成立即放行；② covered 短電路（covered 全部 ⇒ 放行，維持 `test_g7_trailer_precheck.py:104-107` 之基線）；③ 對 `uncovered ∩ hard` 拒（trailer 不救）；④ 其餘 uncovered 走 OOE 值域（Task 3.2）。
  - **`epic_state=dormant`**：① `_is_legal_transition` → 成立即放行；② 硬保護字串比對（`--print-protected` ＋ **呼叫** `_staged_paths_nul`，由 Task 3.4 提供；**本 Task 不得內聯第二份路徑收集**）→ 命中即拒；③ 否則放行，**不呼叫** `--print-scope`。
  - **OOE candidate 封閉定義**（供 ③ 使用）＝「非合法 state transition **∧** scope 判定為 uncovered **∧** trailer 經 `--print-ooe-value-re` 判為合法 OOE 值」；缺 exporter／輸出空／malformed 皆 fail-closed。
- **驗證（可證偽；四情境矩陣）**：`tests/governance/test_g7_trailer_precheck.py` 含下列 4 條 ASSERT ＋ 1 種 mutation；`pytest` 全綠
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN epic_state=active staged=covered_manifest trailer=absent THEN rc=0`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN epic_state=active staged=hard_uncovered trailer_value=out-of-epic THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN epic_state=dormant staged=ordinary trailer=absent THEN rc=0`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN epic_state=dormant staged=hard trailer_value=out-of-epic THEN rc=1`
  - `ASSERT bash scripts/g7_trailer_precheck.sh <msg> WHEN epic_state=active staged=uncovered_hard trailer_value=out-of-epic THEN rc=1`（與 Task 3.2 之 `uncovered_nonhard` 成對；證明 hard 不被 OOE trailer 救〔`GROK-R1-P1-02`〕）
  - **子行程數上界**〔`CODEX-R1-P2-08`〕：`ASSERT <precheck 對 gate 之子行程呼叫數> WHEN epic_state=dormant staged=ordinary THEN rc=1`（恰 1 次：只取 state，不取 scope）；`ASSERT <同上> WHEN epic_state=active staged=uncovered_nonhard THEN rc=3`（state＋scope＋ooe-value-re）。以 stub 計數，見 §V。
  - mutation（答群集 ε 之 5b）：把硬保護拒絕**前移到 covered 判定之前** ⇒ 第一條（`active`＋`covered_manifest`）須轉紅。
- **邊界（≥2）**：① `active` 且 staged 為 `scripts/govb1_scope.manifest`（covered 且 hard）之合法更新 ⇒ rc=0（不得因 hard 而誤擋）；② `dormant` 且 staged 同時含硬保護與一般路徑 ⇒ rc=1。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把硬保護判定寫成無條件前置（會弄死 active 之合法 manifest 更新〔`CODEX-R1-P1-04`〕）。

**Task 3.4 — 路徑收集抽成單一函式**
- 目標：消除 active／dormant／轉態三條路徑各自收集 staged 路徑而漂移之可能。
- 檔案：`scripts/g7_trailer_precheck.sh`（抽出 `_staged_paths_nul()`，取代現行 `:38-59` 內聯段）。
- 改法：單一實作，寫死 NUL-safe（`-z` ＋ `read -r -d ''`）＋ `--name-status` ＋ `--diff-filter=ACMRDT` ＋ R/C 之舊名與新名皆納；git rc 落變數後判，不經 pipe。三條路徑一律呼叫本函式。
- **驗證（可證偽）**：`tests/governance/test_g7_trailer_precheck.py` 含下列 2 種 mutation；`pytest` 全綠
  - mutation：把本函式改回 `--name-only` ⇒ 「`git mv` 硬保護檔出前綴」之測試須轉紅。
  - mutation：filter 去掉 `T` ⇒ 「凍結檔改為 symlink」之測試須轉紅。
- **邊界（≥2）**：① 路徑含換行 ⇒ 不得被切成兩筆；② `git diff --cached` 失敗（如 `GIT_INDEX_FILE` 指向不存在檔）⇒ rc≠0 fail-closed，不得放行。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：禁止第二份 path 收集實作（含複製後微調）。

### Phase 4 — dormant 接線與昂貴閘分支（依賴：Phase 1、Phase 3）

**Task 4.1 — `_g7()` 與 `gov_check.sh` 依 state 分支**
- 目標：`dormant` 時昂貴閘不做歷史 endpoint 掃描，否則現況立即恆紅〔`GROK-R1-P0-02`〕。
- 檔案：`scripts/govb1_final_gate.sh::_g7`（`:489-552`）；`scripts/gov_check.sh:341-350`。
- 既有 caller/影響面：`gov_check.sh` 第 4 段之 `if [ -f scripts/govb1_scope.manifest ]` 條件無 state 分支〔`COMPOSER-R1-P1-01`〕，只改 gate 內部不足。
- 改法：兩處皆先取 Task 1.1 之 state；`active` ⇒ 行為與現行**完全相同**。`dormant` ⇒ 依下列**決策表**（〔`CODEX-R1-P1-03`／`COMPOSER-R1-P1-01`／`GROK-R1-P1-01`〕，定義本體寫死於此，不留白）：
  - **仍執行**：`_g7()` 開頭之交付形態守衛（`govb1_final_gate.sh:489-530`），語意與 `active` **完全相同**——covered 之未 commit `??`／`A*` ⇒ rc=1；批次標的之 `M`/`MM` ⇒ rc=1；非標的 ambient `M` 不觸發。
  - **跳過**：`base..HEAD` endpoint loop（`:532-545`）與 `_g7_path_only_ooe`。硬保護改由 Phase 3 之便宜閘承擔**當次 staged**。
  - **不變**：state 讀取失敗仍 rc≠0，不得回退成任一模式。
- **驗證（可證偽）**：新增 `tests/governance/test_g7_epic_state_wiring.py`，含下列 6 條 ASSERT ＋ 1 種 mutation；`pytest` 全綠
  - `ASSERT bash scripts/govb1_final_gate.sh --only g7 WHEN frozen_key=absent THEN rc=0`（U-2 之真跑對照；**改前與改後 rc 及 stdout 須完全相同**——本條是預設方向的唯一閘門）
  - `ASSERT bash scripts/govb1_final_gate.sh --only g7 WHEN frozen_key=active THEN rc=0`（只驗顯式 enum，不涉預設）
  - `ASSERT bash scripts/govb1_final_gate.sh --only g7 WHEN frozen_key=dormant worktree=clean THEN rc=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --only g7 WHEN frozen_key=dormant worktree=covered_untracked THEN rc=1`（stderr 須含 `UNSUPPORTED-DELIVERY-SHAPE`）
  - `ASSERT bash scripts/govb1_final_gate.sh --only g7 WHEN frozen_key=dormant worktree=ambient_modified THEN rc=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --only g7 WHEN frozen_key=bad_value THEN rc!=0`
  - mutation〔`CODEX-R1-P1-05`／`GROK-R1-P1-03`〕：**只改缺鍵 fallback** 為 `dormant` ⇒ `frozen_key=absent` 那條須轉紅；`frozen_key=active` 那條須**維持綠**（若 active 那條也紅，代表 fixture 寫錯，mutation 無效）。
- **邊界（≥2）**：① `dormant` 且 staged 含硬保護但未 commit ⇒ 交付形態守衛先於 state 分支生效，rc=1；② `gov_check.sh` 第 4 段在 manifest 存在但 state 為 `dormant` 時，不得再呼叫 `--only g7` 之歷史掃描路徑。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得在 `gov_check.sh` 內自行判 state（一律呼叫 Task 1.1 出口）。

### Phase 5 — 文件與登記對齊（依賴：Phase 3、Phase 4）

**Task 5.1 — fact-key SoT 與投影**
- 目標：消除「pre-push 跑全套／跑 `--only g7`」之過期敘述，且不造成 fact-key 投影漂移。
- 檔案：`scripts/fact_keys.json`（governance-enforcement 之 E-005 列）→ `bash scripts/gen_fact_key_blocks.sh --write` 投影 `docs/GOV_ENFORCEMENT_REGISTRY.md` 與 `docs/GOV_TICKET_SOT.md`；再人工處理 `docs/GOV_ACTIVE_MECHANISMS.md:127`、`docs/GOV_GATECHAIN_SPEC.md:41`（皆不在任何 fact-key target，須人工；凍結者走 extension/pointer，不得回改）。
- 改法：順序寫死＝先改 SoT → `--write` → 人寫段落。
- **驗證（可證偽）**：`bash scripts/gen_fact_key_blocks.sh --check` rc=0；stale-pattern grep 之命中集合**等於** Task 5.2 所定義之 allowlist（差集為空）。
- **邊界（≥2）**：① 凍結文件命中 ⇒ 只得新增 extension/pointer，原檔 byte 不變（以 `git diff --stat` 斷言）；② `--write` 後兩份投影表之 diff 僅限 E-005 列。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得手改 `GOV_ENFORCEMENT_REGISTRY.md` 或 `GOV_TICKET_SOT.md`（兩者為投影產物）。

**Task 5.2 — stale-pattern allowlist 與預期殘留集**
- 目標：使 stale grep 成為可證偽之驗收，而非恆失敗或被任意排除。
- 檔案：**不新增** `scripts/` 檔〔`GROK-R1-P2-02`：避免與 `CLAUDE.md:138`「治理不再擴建」衝突〕。預期殘留集寫成 `tests/governance/test_g7fix_stale_docs.py` 內之 `EXPECTED_STALE` 常數；該 pytest 檔即唯一收案命令〔`COMPOSER-R1-P2-01`〕。
- 改法：定義 ① exact stale pattern ② 掃描範圍（含 glob 排除） ③ 凍結文件允許之 extension/pointer 形態 ④ 預期殘留集合。
  🔴 **key 粒度封閉到 `(path, 命中行內容之 sha256 前 12 碼)`，禁 path-only 條目**〔`CODEX-R1-P1-04`：path 級條目會讓同檔新增 stale 敘述被整體放行，雙向差集不會變紅〕。
  現況命中 62 筆須逐筆分類為「待改／正確註解／凍結留存」三類，前者清空、後兩者入 `EXPECTED_STALE`。
- **驗證（可證偽）**：`venv/bin/python -m pytest tests/governance/test_g7fix_stale_docs.py -q` 全綠，其斷言為 `命中集合 − EXPECTED_STALE == ∅` 且 `EXPECTED_STALE − 命中集合 == ∅`（雙向，防腐爛）。
  - mutation：於**已列入** `EXPECTED_STALE` 的同一檔案新增一條 stale 行 ⇒ 須轉紅（證明不是 path-only 吞掉）。
  - mutation：從 `EXPECTED_STALE` 刪掉一筆仍實際存在之命中 ⇒ 須轉紅。
- **邊界（≥2）**：① 命中行內容變動但路徑不變 ⇒ sha 改變，須轉紅（迫使重新分類）；② 掃描範圍之 glob 排除清單本身被改動 ⇒ 命中集合改變，雙向差集須反映。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得以 `--glob` 排除整個 `docs/` 求綠。

**Task 5.3 — `--no-verify` 誠實邊界登記 ＋ 降級授權 ID 登記**
- 目標：① 不得宣稱 dormant 硬保護「無條件恆開」〔`CODEX-R2-P1-03`、`COMPOSER-R2-P1-03`〕 ② 提供 Task 2.2 之 `active→dormant` 授權來源〔`CODEX-R1-P0-01`〕。
- 檔案：`scripts/fact_keys.json` 之 E-005 列（經投影落到兩份登記表）。
- 🔴 **本 Task 必須先於任何實際降級 commit 完成**（否則 Task 2.2 之 `ruling:<ID>` 查無此 ID，降級無法執行）。
- 改法：
  - 邊界具名：dormant 之硬保護僅在 commit-msg 生效，`git commit --no-verify` 與 hook 未安裝時不保護；與 `E-005` 既有邊界同界。附 receipt（`core.hooksPath` 與 `verify_hooks_health.sh` 之輸出）。
  - 授權登記：新增一個字面 ID（形如 `R-GOVB1-DORMANT-2026-09-05`）與其裁決依據，供 Task 2.2 之 `grep -qF` 比對。
- **驗證（可證偽）**：登記表投影後含該邊界字串與該授權 ID；`gen_fact_key_blocks.sh --check` rc=0；Task 2.2 之 `transition=legal_downgrade` 以該 ID 通過、以任一未登記 ID 則 rc=1。
- **邊界（≥2）**：① 未安裝 hook ⇒ 邊界敘述須涵蓋；② 敘述不得出現「取代 B3／B4／B5 窗守衛」之宣稱（以 grep 斷言零命中）。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把 dormant 硬保護搬回 pre-push（違背使用者 2026-08-14「commit 和 push 是幾秒鐘內的事情」）。

### Phase 6 — TODO「修改檔案」欄機械化（依賴：無）

**Task 6.1 — 新增 `- 路徑：` 區塊（加欄不換欄，前向適用）**
- 目標：使 TODO 之修改標的可被實作 agent 精確讀取。
- 檔案：`templates/TODO_GENERATION_PROMPT.md`（產生規則）。
- 改法：每個 Task 於現行「修改檔案：」散文欄**之外**新增 `- 路徑：` 區塊，一行一條、允許 glob、禁散文。散文欄**保留**（承載 `::函式` 與「既有 caller ⇒ 為何不用改」之推理）。**前向適用**：`docs/GAP3_EVENT_UX_TODO.D-006.md:245` 已 `v2 FROZEN 2026-09-04`，不回頭改。
- **驗證（可證偽）**：本 SPEC 對應之 `docs/G7FIX_TODO.md` 每個 Task 皆含 `- 路徑：` 區塊（`grep -c` 等於 Task 數）。
- **邊界（≥2）**：① Task 新建檔案且尚不存在 ⇒ 路徑仍須列出（不得因不存在而略）；② 一次建多檔 ⇒ 允許 glob，不強制逐檔展開。
- **存活至**：Phase 6 完工後仍保留（長期 TODO metadata）。
- **覆蓋風險**：無。
- 不可做：🔴 **不得**把本欄接成 G-7 之 scope 來源（R2-perf 群集 B 已三方實算證明更差：只用 D-006 欄 ⇒ uncovered 1706–1734/1754，劣於現行 1660–1706）。
- 不可做：本票**不加** `scripts/template_check.sh` 格式閘（見 §N 殘留 R-G7FIX-1）。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT 為 `b,c`，未含 a/d；惟本票多數 Task 宣稱修復假閘（＝宣稱驗正確性），故**逐 Task 附 mutation**，設計引 `docs/TEST_DESIGN_CHARTER.md`。
  具名 mutation **實數 16 種**，分佈：Task 1.1×2、1.2×2、2.1×1、2.2×3、3.1×1、3.2×1、3.3×1、3.4×2、4.1×1、5.2×2。
  🔴 本行為**實際計數**，非「不少於」之空頭宣稱〔`COMPOSER-R1-P1-03`／`GROK-R1-P1-03` 已抓過一次：前版稱 ≥8 而實為 6〕。改動 SPEC 時須同步重數。
- 測試層級：
  - 單元：`tests/governance/test_govb1_contract_matrix.py`（Phase 1）
  - 整合：`tests/governance/test_g7_trailer_precheck.py`（Phase 2–3；須新增 `test_g7_transition_*` 與四情境矩陣）
  - 子行程呼叫計數：dormant＋一般路徑須斷言**未呼叫** gate（現行 `_stub_gate` `:35-50` 不計數，須擴充〔`COMPOSER-R2-P2-03`〕）
  - 真跑對照：`bash scripts/govb1_final_gate.sh --only g7`（U-2；秒級，可前景）
- **防假綠**：
  - 🔴 既有 `tests/governance/test_g7_trailer_precheck.py:104-107`（active＋in-scope 無 trailer 可過）**不得修改或刪除**；它是 Phase 3 之 active 基線。
  - 既有 22 條／9 條通過**不構成**洞 A／B／C 之覆蓋證據（codex 已於前輪實證），新斷言須對應新行為。
  - 收案前 `bash scripts/gov_check.sh --no-probe`（**丟背景**，十分鐘級）——此為 U-1 之唯一結案方式，不得以 targeted pytest 代替。
  - 跑完測試須 `bash scripts/restore_golden_inventory.sh`。
- **邊界目錄**（本任務適用者）：空輸入（凍結檔為空）／重複鍵／未知鍵／路徑含換行／type change（symlink）／rename 舊名／初始 commit 無 HEAD／detached HEAD／`--amend`／dirty worktree 三態（clean／covered untracked／ambient modified）。
  🔴 **`touched-then-reverted` 已移出本票適用邊界**〔`CODEX-R1-P1-06`〕：dormant 只保護**本次 staged**，planned collector 在定義上不可能觀察到「前一 commit 觸及、現已回復」之路徑；把它列為適用等於假完整性。殘留登記見 §N 之 R-G7FIX-3。
  不適用：全NaN、Inf、std=0、OOM降載、並發寫、大尺度浮點 reduction（本票不涉數值）。

## §R 回退
- 每 Phase 獨立 commit，可單獨 revert。
- **狀態機本身即回退機制**：`epic_state` 未寫入凍結檔時預設 `active` ⇒ Phase 1–4 全數落地後，若不寫入該鍵，行為與現行完全相同；欲回退只需 revert 對應 commit 或移除該鍵。
- Phase 5（文件）與 Phase 6（TODO 欄）無行為面影響，revert 無副作用。
- 任一 Task 之 mutation 未能轉紅 ⇒ 該 Task 不得標完成，不 merge。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- **§G**：N/A — 本票只改治理腳本與文件，不觸 `momentum/`／`api/` 之數值、特徵計算、merge/split 或 ML 路徑；`RISK-HIT: b,c` 未含 (a)／(d)，依範本規則移此登記。

**殘留**
- **R-G7FIX-1**：TODO `- 路徑：` 欄**不加** `scripts/template_check.sh` 格式閘。
  `為何現在不做: needs-research:「TODO 路徑欄之封閉 grammar」——區塊終止錨點、glob 方言（shell vs POSIX）、註解與空白規則、特殊字元處理皆未定義；現行 G-7 matcher（`govb1_final_gate.sh:183-194`）只支援精確路徑或尾斜線前綴，不能充當此欄之 glob 語法。三家 R1 一致選不加。`
  **具名代價**：漏欄、錯 glob、特殊字元與散文混入只能靠 review 發現；D3.1 型「同一值漏改多處」事故仍可能重演。
  **觸發條件**：出現第二次「因 TODO 路徑欄不精確而漏改呼叫點」之實例，或封閉 grammar 完成研究。
  **登記處**：`docs/GOV_ENFORCEMENT_REGISTRY.md`（隨 Task 5.1 之投影一併登記）。
- **R-G7FIX-2**：dormant 之硬保護僅在 commit-msg 生效，`git commit --no-verify` 可繞。
  `為何現在不做: user-ruling:2026-08-14 使用者「我只要 commit 和 push 是幾秒鐘內的事情」，`pre-push` 已改 `--fast`；把 dormant 硬保護搬回 push 等於回退該裁定。`
  **具名代價**：刻意繞過者不受本機制約束；本機制只防**未使用 `--no-verify` 的意外提交**。與 `E-005` 既有邊界同界，非本票新增。
  **觸發條件**：出現一次因 `--no-verify` 而使硬保護檔被實際破壞之事件。
  **登記處**：`docs/GOV_ENFORCEMENT_REGISTRY.md`（Task 5.3）。
- **R-G7FIX-3**：`dormant` 下不偵測 `touched-then-reverted`（前一 commit 觸及硬保護、現已回復）。
  `為何現在不做: user-ruling:2026-09-05 採 R1 群集 B 之裁定「dormant 之昂貴 _g7 不做歷史 endpoint 掃描」——要偵測它就得逐 commit 掃 base..HEAD，而 grok 已實證那會使現況立即恆紅（三個硬保護路徑已在 range 內）。`
  **具名代價**：於 dormant 期間，一筆「改壞硬保護檔、下一筆再改回」的成對 commit 不會被 G-7 記錄；便宜閘只在**每筆 commit 當下**擋，故第一筆仍會被擋——真正漏掉的只有「第一筆用 `--no-verify` 繞過」之組合，與 R-G7FIX-2 同界。
  **觸發條件**：`epic_state` 轉回 `active`（屆時歷史掃描恢復），或出現一次實際的成對繞過事件。
  **登記處**：`docs/GOV_ENFORCEMENT_REGISTRY.md`（隨 Task 5.1 之投影一併登記）。
