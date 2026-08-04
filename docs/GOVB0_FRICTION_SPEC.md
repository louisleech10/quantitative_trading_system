# 治理 backlog 第 0 批（摩擦止血）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/govb0-recon-r1/synth.md`（R1 偵察，21 findings，rc=0）　|　日期：2026-08-04　|　對應 TODO：`docs/GOVB0_FRICTION_TODO.md`（待生成）

**版本 R2**（依 `handoffs/reconcile/20260804-govb0-spec-r1/synth.md` 的 D-1～D-13 全數修訂；R1 兩家皆判「需修補後派工」）。

**涵蓋票**：`B-15`（gate 判定：2 個誤擋機制 ＋ 2 個 fail-open）／`B-14`（委員不退出）／`B-30`（委員覆蓋自己產出）／`B-32`（stamp prompt 無條件注入）／`B-24`**僅紀律面**。
**唯一票登記處**：`handoffs/20260801-GOV-AMEND-BACKLOG.md`。

🔴 **R2 相對 R1 的範圍變更**：**刪除原 Phase 4**（`B-24` 機械強制面）。
依 `D-6` 裁決 SPLIT：`B-24` 紀律面（驗收欄一律寫狀態斷言，零新增元件）留本批並落實於 §V；
機械強制面（`acceptance_state_check.sh`＋grandfather SoT＋owner／UTC 到期／到期後 fail-closed）移出獨立排期，
理由與 grandfather 三要件已記於 backlog「`票 B-24` 的拆分裁決」節。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大。
- **命中高風險原則**：
  - **(b) 跨模組／共用路徑** — `scripts/gate_check.sh` 是**每一次** `Task|Bash|Write` 工具呼叫的 PreToolUse 攔截點；`scripts/cx_run.sh`／`committee_run.sh` 是**所有**委員派工的唯一通道。
  - **(c) 多 phase／難回退** — 4 Phase；Phase 2 改判定放行/擋下，錯誤方向為 fail-open。
- RISK-HIT: b,c
- 未命中 (a)／(d)：不碰數值、特徵、ML、回測路徑 → §G 於 §N 標 N/A。
- **adversarial review 必跑**；**code review 兩個非實作者家族**（角色 SoT `scripts/governance_roles.json`：implementer=grok ⇒ 審查為 codex＋composer）。

## §A 假設與待使用者確認（事故：拿推論代替問人）

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

**已驗證事實（9 條，每條附實跑 stdout 摘要）**：

- FACT-RECEIPT: `grep -o '"reason":"[^"]*"' .claude/gate/audit.log | sort | uniq -c` → 印出 `493 token_expired` / `106 open_debt`，全檔 599 筆僅此兩值，**無指令欄位**（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `LC_ALL=C grep -ac 'closure review' .claude/gate/ts_stamp.log` → 印出 `0`；`LC_ALL=C grep -ac 'hmsg.txt'` → 印出 `2`（Claude 實跑 2026-08-04）⇒ 被擋指令零紀錄、成功重試有紀錄
- FACT-RECEIPT: `bash .claude/tmp/b15probe.sh` → `pgrep -fl 'codex exec|cursor-agent|grok '` 與 `git commit -m "…; codex closure review…"` 皆 BLOCK；7 條真派工全 BLOCK（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/b15probe2.sh` → `head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD` BLOCK（命中 `claude-501/x.output; git rev-p`）；拆解對照組兩條皆 ALLOW（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/b15probe3.sh` → 原型①（單純剝引號）對 `bash -c "codex exec x"` 與 `sh -c 'grok … -p x'` 皆 **ALLOW（fail-open）**；原型②（剝引號＋對 `(bash|sh|zsh) -c` 引數遞迴）9/9 全對（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `grep -c 'token' scripts/cx_run.sh` → 印出 `0`；`grep -c 'token' scripts/_role_gate.sh` → 印出 `0`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `grep -c 'timeout' scripts/cx_run.sh` → 印出 `0`；`scripts/committee_run.sh:280` 為裸 `wait "${pid}"`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `sed -n '512p' scripts/cx_run.sh` → 印出含 `RECONCILE-STAMP 的 task: 欄位須逐字使用此值` 的 prompt 賦值，**無 brief-kind 分支**，且該行同時寫著「產出寫到 ${out}」（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/runlog_dur.sh` → 印出 `TOTAL_RUNLOGS=462`；`codex n=166 max=45.1m`／`composer n=153 max=146.7m`／`grok n=143 max=64.6m`；於 codex 50m／grok 65m／composer 75m 下誤殺各為 `0/166`、`0/143`、`0/152`（Claude 實跑 2026-08-04，獨立於委員報告）

**待使用者確認**：**待確認：無**

**已確認結果**：`2026-08-04 使用者指示「有疑慮和問題就跟委員討論，有撞到問題需開票或合併的也就跟委員討論寫到 backlog」——技術取捨交委員裁決，不阻塞等使用者。`

**未決技術項（已由 R1 審查裁定，非使用者事項）**：

- **OPEN-1（已裁定，值為暫定）**：timeout 涵蓋區間＝**CLI process-group launch → return/kill**（兩家一致；明文否決 output-mtime proxy，因其無法覆蓋「產出已寫完但 CLI 不退出」的 `B-14` 掛死型態）。
  暫定值（取兩家保守聯集）：**codex 50m／grok 70m／composer 75m**，`committee_run.sh` 外層安全閥 **90m**。
  🔴 **暫定理由**：現有數據皆為 runlog `birth→mtime` proxy，非 CLI wall-clock。**Task 3.1 上線取得真實 duration 後須重算並在 TODO 定稿**（`CODEX-R1-P0-07` 條件，已接受）。
- **OPEN-2（已裁定，移出本批）**：locale 相依守衛 → 已開 `票 B-33 GOV-LOCALE-GUARD-DRIFT`，嚴重度 MAJOR，排第 1 批之後。**本批不併入**（兩家一致），但須寫入本批 TODO §0 已知債。
- **OPEN-3（已裁定，不除役）**：`B-15` FP-2（`for` 迴圈形態）以「Phase 0 上線後補查」結案。
  **補查條件（`CODEX-R1-P1-08` 要求，本 R2 補上）**：Phase 0 上線後累積 **≥200 筆 `gate_deny` 紀錄**或 **≥30 個日曆日**（先到者為準）後，以 `match_rule` 反查；
  若期間零命中 `for` 迴圈形態 ⇒ 從 `票 B-15` 除役並在票面記「觀測期無再現」；若命中 ⇒ 依實際 `match_rule` 另立修法。**除役須有紀錄支撐，不得因「現在重現不出來」而除役。**

## §C 約束（不重抄，引用 + 只列本任務相關）

- 解耦 7 條不適用（本批不動 `momentum/`／`api/`／`frontend/`）。
- **共用路徑與既有 caller**：
  - `scripts/gate_check.sh` — PreToolUse 第 1 個 hook（`.claude/settings.json:99-135`；`ts_stamp.sh IN` 為第 4 個）。**熱路徑，禁引入 subprocess**。
  - `scripts/cx_run.sh` — 唯一委員 CLI 呼叫點（`:443` codex／`:452` grok／`:461` composer）；`_emit_family_result`（`:250-288`）為 `result_state` 唯一寫入點；`:512` 為 prompt 賦值。
  - `scripts/committee_run.sh:268` 呼叫 `cx_run.sh`、`:280` 裸 `wait`。
  - `scripts/completeness_check.sh:179` 為 finding ID schema 拒收點；`:1459-1472` 為 `--single`。
  - `scripts/governance_families.json`（家族 SoT）／`scripts/governance_roles.json`（角色 SoT）／`scripts/audit_events.json`（事件與枚舉 SoT）。**禁在他處再寫一份。**
- **禁止**：改檢查器或加排除清單使測試變綠；恆真斷言；弱化既有斷言；空 monkeypatch 騙靜態檢查。
- **禁止**：`git checkout`／`git restore` 任何 tracked 檔。探針一律隔離副本。

> **新資料結構檢查點**：本 SPEC 新增枚舉 `gate_deny.match_rule`。
> 依範本規定，其**封閉值集合與事件契約寫入 `scripts/audit_events.json`**（既有 SoT，已有 `registry_version`／`schema_version`／`unknown_event_policy`／`required_fields_per_event`），
> **SPEC 不在散文中列舉任何值**。`result_state` 三值為既有定義，同樣只 pointer。

## §P Phase 與依賴

**依賴圖（`D-13` 要求，全部宣告，含 R1 未宣告者）**：

```
Phase 0 ──────────────► Phase 2        （驗收依賴：無 deny 紀錄則差集不可驗）
Phase 0 ──registry enum─► Phase 2       （match_rule 契約須先存在）
Phase 1 ──prompt 路徑──► Task 3.2       （prompt 仍寫 <out> 則 .part 方案失效）
Task 3.1 ──duration───► Task 3.3        （timeout 值定稿依賴真實 duration）
OPEN-1 裁決 ──────────► Task 3.3 TODO   （值填入 TODO 前須完成 Task 3.1 重算）
immutable corpus ─────► Task 2.5        （語料檔須先進版控並記 sha256）
舊版 gate snapshot ───► Task 2.5        （差集的「舊版」須為固定 sha 的副本，非 HEAD）
```

**無其他 forward dependency。** Phase 3 不影響 Phase 0 的紀錄內容，亦不影響 Phase 2 的判定。

### Phase 0 — 可觀測性前置（依賴：無）

> 目標：讓「被 gate 擋下」留下可機械分析的紀錄。**Phase 2 的驗收完全依賴本 Phase。**

**Task 0.1 — `gate_deny` 記錄被擋指令與命中規則**

- 目標：`gate_deny` 事件新增指令與命中規則兩欄，使誤擋率可事後量測。
  檔案：`scripts/gate_check.sh` 的 `_append_gate_deny_audit()`（`:21-30`）與 `:86` 判定段；枚舉與事件契約寫入 `scripts/audit_events.json`。
  既有 caller：`gate_check.sh:117`、`:128`。
- 改法：
  1. **先判定、後記錄**：命中後才以 `grep -Eo` 取命中片段。**取片段的結果不得回饋進判定**。
  2. `match_rule` 的封閉 enum 與 `gate_deny` 的 `required_fields` 寫入 `scripts/audit_events.json`；`gate_check.sh` 只引用，不自列。未知值依該檔既有 `unknown_event_policy` 處理。
  3. **命令欄截斷規則**：存全文 `sha256` ＋ 前 512 位元組。理由：委員 prompt 可達數十 KB；`sha256` 使同一指令可被歸併計數。
  4. **不變式（`D-3` 收窄後的精確定義）**：**判定行為不變** ＝ 對同一批輸入，改前與改後的 `(rc, kind)` 序列**逐項相等**。
     🔴 **audit 內容本來就會增加欄位，不在本不變式範圍內**（R1 原文「行為逐位元組不變」有歧義，已修正）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/gate_check.sh WHEN input=blocked_cmd THEN rc!=0`
  - `ASSERT bash scripts/gate_check.sh WHEN input=allowed_cmd THEN rc=0`
  - 狀態斷言：固定輸入語料（≥20 條，含全部 Phase 2 語料）的 `(rc, kind)` 序列改前 == 改後，**逐項比對輸出兩份 JSON 並 diff 為空**。
  - 狀態斷言：新 `gate_deny` 事件經 `jq` 取出後，命令欄非空、`match_rule` 值屬 `scripts/audit_events.json` 所定集合（**以該檔為斷言來源，非硬編**）。
  - mutation：移除欄位寫入 → 對應測試轉紅。
- **邊界（≥2）**：①指令含換行與控制字元 → 欄位須為合法 JSON 字串，不破壞 audit 逐行 JSON 結構 ②`tool_input.command` 缺失 → 欄位寫空字串而非缺欄，且不得例外中止 ③4 MB 巨量 prompt → 截斷後 audit 單行 ≤1 KB。
- **存活至**：永久（`票 B-29` 差集工具的資料來源）。
- **覆蓋風險**：無。
- 不可做：**不得把 `grep -Eo` 放進判定前主路徑**（`D-12`／`COMPOSER-R1-P2-01`：`grep` 失敗或效能變化會改 rc）；不建新 log 檔；不改 hook 順序；不動 `ts_stamp.sh`。

### Phase 1 — `B-32` stamp prompt 條件化（依賴：無）

> 目標：停止讓系統自己誘發委員交件失敗。**Task 3.2 依賴本 Phase 的 prompt 路徑對齊。**

**Task 1.1 — `cx_run.sh` prompt 依 `brief-kind` 分支**

- 目標：只有需要戳記的輪次才在 prompt 中提及 RECONCILE-STAMP。
  檔案：`scripts/cx_run.sh:512`。既有 caller：`_run_cli_and_emit`（同檔 `:513`）。
- 改法：
  1. `brief-kind` 沿用 `brief_conformance_check.sh` 經 `_bc_kv` 回傳的既有解析結果，**禁再寫一份 parser**（出生事故：`committee_run.sh` 第二份 parser 造成孤兒債）。
  2. `brief-kind ∈ {stamp, closure}` → 保留注入句並**補充格式說明**：戳記為單獨一行 `RECONCILE-STAMP: <family> APPROVED <date> sha256:<hash> task:<id>`，**非 `## ` 標題**。格式的單一真相源＝`cx_run.sh:345` 的正則，測試須斷言 prompt 說明與該正則機械一致。
  3. 其餘 `brief-kind` → **完全不提** RECONCILE-STAMP，只注入 task-id。
  4. **unknown `brief-kind` → fail-closed，拒派**（`D-5`／`CODEX-R1-P1-09`：R1 原文「視同不需戳記＋audit 警示」與 fail-closed 互斥，已改為單一行為）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=consult THEN rc=0`（且 prompt 不含字串 `RECONCILE-STAMP`）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=stamp THEN rc=0`（且 prompt 含該字串與格式說明）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=unknown THEN rc!=0`
  - 狀態斷言：prompt 中的格式說明字串與 `cx_run.sh:345` 正則所接受的樣本**互為可解析**（以一個合法戳記樣本同時通過兩者）。
  - mutation：還原無條件注入 → `brief_kind=consult` 斷言轉紅；移除 unknown 分支 → 第三條轉紅。
- **邊界（≥2）**：①`brief-kind` 解析失敗／缺欄 → fail-closed，維持現行拒派行為 ②`brief-kind` 為未知值 → fail-closed（同上，**不再有第三種行為**）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 🔴 **誠實邊界（`D-11`／`COMPOSER-R1-P2-02`）**：本 Task 只保證 **harness 端不再誘導**；**無法保證委員不自行寫出 `## RECONCILE-STAMP` 標題**。後者若再發生，屬 `票 B-31`（format-failed 無便宜修正路徑）範疇，不由本 Task 承擔。驗收**不得**以「委員這次沒寫」為斷言（不可重現）。
- 不可做：不改 `completeness_check.sh` 的 ID schema（`票 B-32` 修法③，本批不做）；不改既有戳記格式。

### Phase 2 — `B-15` gate 判定修正（依賴：Phase 0）

> **設計約束（`CLAUDE-R1-P1-03`）**：現行正則 TP 面 7/7 完好，**本 Phase 不得使任何既有 TP 轉為放行**。

**Task 2.0 — 詞法契約（lexical contract）先定義，後實作**

- 目標：`D-1`／`CODEX-R1-P0-02` 指出「前處理語義與命令遞迴語義衝突」，故四項修法**共用一份詞法契約**，不得各自為政。
  檔案：`scripts/gate_check.sh`（契約以註解形式寫在判定段上方，並由測試釘死）。
- 改法：契約須明確定義下列每一項的判定結果，**且每一項都要有對應測試**：
  1. 引號內的 `;` `&` `|` **不作分隔符**；
  2. `(bash|sh|zsh) -c <引號引數>` 的**引數內容須遞迴套用同一判定**（不得因剝引號而消失）；
  3. 帶引號的路徑（`"/my dir/codex" exec`）；
  4. 路徑正規化（`./scripts/cx_run.sh`、`scripts//cx_run.sh`、`scripts/../scripts/cx_run.sh`）；
  5. 未閉合引號 → **fail-closed**（視為未剝除）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：契約 5 項各至少 1 條 TP 與 1 條 TN，**共 ≥10 條**，全部進入 Task 2.5 的 immutable corpus。
- **邊界（≥2）**：①巢狀 `bash -c "bash -c 'codex exec x'"` → 遞迴深度須有上限且逾限 fail-closed ②跳脫引號（`"a\"b"`）→ 不得因剝除錯誤而放行。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得在四個 Task 中各寫一份剝引號邏輯。

**Task 2.1 — 引號感知 ＋ `-c` 遞迴（洞 A ＋ `D-1` 的 fail-open）**

- 目標：引號**內**的分隔符不生效；但 `(bash|sh|zsh) -c` 的引數仍受檢。
  檔案：`scripts/gate_check.sh:86` 判定段（新增前處理）。
- 改法：依 Task 2.0 契約實作。**純 shell/`sed`，禁 subprocess 呼叫 python**（熱路徑）。
  參考原型＝`.claude/tmp/b15probe3.sh` 的原型②（主委實跑 9/9 全對）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`pgrep -fl 'codex exec|cursor-agent|grok '`、`git commit -m "…; codex closure review…"` 由 BLOCK 轉 ALLOW。
  - 狀態斷言：`bash -c "codex exec x"`、`sh -c 'grok -m grok-4.5 -p x'`、`bash -c "claude -p x"` **三條皆維持/轉為 BLOCK**。
  - 狀態斷言：`echo start; grok -m grok-4.5 -p "x"`（引號**外**的分號）維持 BLOCK。
  - mutation：移除 `-c` 遞迴 → 上述三條 `-c` 語料轉為 ALLOW（**這是 `D-1` 的守護測試**）。
- **邊界（≥2）**：①未閉合引號 → fail-closed ②巢狀／跳脫引號 → 依 Task 2.0 契約 ③`bash -c` 引數不加引號（`bash -c codex`）→ 依契約定義並測試。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得白名單化「唯讀動詞」（R1 偵察已否決：清單列不完，且與 `票 B-23` 方向矛盾）。

**Task 2.2 — `claude` 段收窄（洞 B，含一條 fail-open）**

- 目標：`claude` 不再子字串比對；`-p`／`--print` 須為獨立引數。
  檔案：`scripts/gate_check.sh:86` 第二段 alternation。
- 改法：`claude` 比照家族名限定命令位置並允許路徑前綴；`-p`／`--print` 須有詞界；移除 `[^|]*` 跨字元貪吃。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD`、`cat .claude/tmp/x.txt; git rev-parse HEAD`、`ls /private/tmp/claude-501/; git status --porcelain`、`find .claude/tmp -name "*.md" -print` **四條全由 BLOCK 轉 ALLOW**。
  - 狀態斷言：`claude -p "x"`、`claude --print "x"` 維持 BLOCK。
  - 狀態斷言（**修 fail-open**）：`cat x | claude -p "y"` 由 **ALLOW 轉 BLOCK**。
  - mutation：還原子字串比對 → 前四條轉回 BLOCK、fail-open 條轉回 ALLOW。
- **邊界（≥2）**：①`claude` 在檔名中段（`my-claude-notes.md`）→ ALLOW ②絕對路徑（`/usr/local/bin/claude -p x`）→ BLOCK ③`-p` 為他人旗標（`grep -p`）且無 `claude` → ALLOW。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得整段刪除 `claude` 判定（會失去子代理攔截）。

**Task 2.3 — 家族名 basename 化（fail-open ①）**

- 目標：帶路徑前綴的家族 CLI 須被擋。
  檔案：`scripts/gate_check.sh:86` 第一段 alternation。
- 改法：命令位置比對允許可選路徑前綴，含帶引號路徑（依 Task 2.0 契約第 3 項）。家族清單維持既有 SoT 語意（`:79-80` 註解已載明熱路徑寫死＋測試釘死 == SoT）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`/opt/homebrew/bin/codex exec hi`、`/Users/…/.grok/bin/grok -m x -p y`、`venv/bin/codex exec hi`、`./scripts/../codex exec hi`、`"/my dir/codex" exec hi` **五條全由 ALLOW 轉 BLOCK**。
  - 狀態斷言：`cat sp_codex.txt` 維持 ALLOW。
  - mutation：還原無前綴版 → 五條轉回 ALLOW。
- **邊界（≥2）**：①檔名為 `mycodex`（非 basename 相等）→ ALLOW ②`grok` 為目錄名（`/tmp/grok/notes.md`）→ ALLOW ③路徑含空白且未加引號 → 依契約定義。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得把家族清單複製一份到別處。

**Task 2.4 — 官方外層腳本呼叫點（fail-open ②）**

- 目標：直接執行 `cx_run.sh`／`committee_run.sh` 亦須有 gate token。
  檔案：`scripts/gate_check.sh:86-90`。
- 改法：命令位置出現 `cx_run.sh` 或 `committee_run.sh`（含 Task 2.0 契約第 4 項的路徑正規化變形）→ `kind=dispatch`；`scripts/gate.sh` 維持排除（否則無法 bootstrap）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`ROUND_ID=x bash scripts/cx_run.sh composer b.md o.md`、`bash ./scripts/cx_run.sh …`、`bash scripts//cx_run.sh …` 三條由 ALLOW 轉 BLOCK（無 token 時）。
  - 狀態斷言：`bash scripts/committee_run.sh --session s b.md o codex -- --task-id T` 由 ALLOW 轉 BLOCK（無 token 時）。
  - 狀態斷言：`bash scripts/gate.sh dispatch --intent x …` 維持 ALLOW。
  - **回歸護欄（端到端）**：`committee_run.sh` 取得 token 後呼叫 `cx_run.sh` 的既有流程須仍能完成一次真實派工。
  - 狀態斷言（**不得製造新誤擋**）：`sed -n '1,40p' scripts/cx_run.sh`、`grep -n timeout scripts/cx_run.sh`、`wc -l scripts/committee_run.sh` **三條唯讀查看維持 ALLOW**。
  - mutation：移除呼叫點判定 → 前四條轉回 ALLOW。
- **邊界（≥2）**：①相對路徑變形 → BLOCK ②唯讀查看該腳本 → ALLOW ③腳本名出現在字串引數中（`echo "run cx_run.sh later"`）→ ALLOW。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得把 `gate.sh` 納入（會鎖死取 token 的唯一路徑）。

**Task 2.5 — 行為差集報表（`票 B-29` 手動版）＋ immutable corpus**

- 目標：對**固定**語料，列出「本來擋現在放行」「本來放行現在擋」「未變」三堆。
  檔案：新增 `scripts/gate_decision_delta.sh`（一次性可重跑，非 hook）＋語料檔 `tests/governance/fixtures/gate_decision_corpus.txt`（**進版控**）。
- 改法（依 `D-4` 修訂）：
  1. **immutable corpus**：語料檔進版控，其 `sha256` 寫入報表標頭；差集結果綁該 sha。語料變更須另行 commit 並重跑，**不得在同一次驗收中修改語料**。
  2. **舊版判定來源**＝Phase 2 動工前的 `gate_check.sh` 副本，**以固定 sha 存於 `tests/governance/fixtures/`**，非 `HEAD`（`D-13`：舊版 snapshot 為 forward dependency）。
  3. 每條語料標明出處，禁憑空造。
- **驗證（可證偽，`D-4` 改寫後）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：「本來放行現在擋」欄 ⊇ Task 2.2／2.3／2.4 列舉的 fail-open 修復項（**必要子集**）。
  - 狀態斷言：「本來擋現在放行」欄 ⊇ Task 2.1／2.2 列舉的誤擋修復項（**必要子集**）。
  - 狀態斷言：兩欄中**不屬於 SPEC 列舉的項目**（附加項）**逐項人工標註**為「預期」或「非預期」，標註結果寫入報表；**存在任一「非預期」⇒ rc≠0**。
  - 🔴 R1 原文要求「每一項都須在 SPEC 中被預期」，`COMPOSER-R1-P1-01` 指出 Phase 0 真實語料上線後必然產生 SPEC 未列舉項 ⇒ 永遠 FAIL 或被悄悄放寬。**已改為「列舉項為必要子集 ＋ 附加項須人工標註」。**
  - 狀態斷言：語料檔 sha256 與報表標頭一致（**防止「改語料換綠燈」**）。
- **邊界（≥2）**：①語料為空 → rc≠0 並明確報錯，**不得靜默輸出「無差異」**（出生事故：2026-08-04 zsh 斷詞使 2559 條路徑變成一個檔名，報表印「前 0 後 0、無差異」）②語料含 Phase 0 記錄的真實被擋指令 → 須能吃 ③舊版 snapshot 檔缺失 → fail-closed。
- **存活至**：永久（`票 B-29` 實作時取代）。
- **覆蓋風險**：`票 B-29`（第 1 批）可能以更通用機制取代 ⇒ **屆時應取代而非並存**，理由已註記。
- 不可做：不掛 hook、不進 CI。

### Phase 3 — `B-14` ＋ `B-30` 委員產出生命週期（依賴：Phase 1）

> 兩票共用同一機制（attempt-scoped atomic publish），故同 Phase。

**Task 3.1 — per-family 耗時紀錄**

- 目標：先有資料，才有 timeout 值的依據。**Task 3.3 的定稿依賴本 Task。**
  檔案：`scripts/cx_run.sh` 的 `_run_cli_and_emit` 與 `_emit_family_result`（`:250-288`）。
- 改法：記錄 CLI 呼叫的起、訖與時長，寫入既有 `committee_family_result` 事件（**沿用既有事件，不新增事件型別**；欄位加入 `scripts/audit_events.json`）。時間源須為單調時鐘或 UTC epoch。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：一次真實派工後，`committee_family_result` 含起訖與時長三欄，且時長 == 訖 − 起（自洽檢查）。
  - 狀態斷言：欄位名與 `scripts/audit_events.json` 所定 schema 一致（以該檔為斷言來源）。
  - mutation：移除欄位 → 測試轉紅。
- **邊界（≥2）**：①CLI 未執行即失敗（binary 不存在）→ 時長欄為 0 或缺，不得為負 ②跨日／時區 → 用單調時間或 UTC epoch，禁本地時間字串相減。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不新增 audit 事件型別。

**Task 3.2 — attempt-scoped atomic publish（同時解 `B-30` 與 `B-14` 的 terminal marker）**

- 目標：委員寫入中的產出對外不可見；**publish 動作本身**即 terminal marker。
  檔案：`scripts/cx_run.sh`（產出路徑處理 ＋ `:512` prompt）；`scripts/new_brief.sh`／`brief_conformance_check.sh` 的骨架文字。
- 改法（依 `D-2` 全面改寫；R1 版本被兩家判 BLOCKING）：
  1. **attempt identity**：每次派工產生唯一 attempt id，產出寫入 **attempt 專屬 temp namespace**（例：`<out>.<attempt-id>.part`），**非共用的 `<out>.part`**。
  2. **prompt 對齊（`D-2` 核心）**：`cx_run.sh:512` 的「產出寫到 `${out}`」**必須同步改為 attempt 路徑**。
     🔴 **prompt-only 或 wrapper-only 皆不成立**：只改 prompt → 委員可忽略；只改 wrapper → 委員仍寫 `<out>`。**兩者必須同時改，且測試須同時覆蓋。**
  3. **啟動前檢查**：確認 final path 的 marker 不存在；若存在 stale `<out>` → **拒絕啟動或明確標記為 stale**，不得沿用（`CODEX-R1-P0-03`：舊 `<out>` 會被誤當本輪 terminal marker）。
  4. **publish 條件**：CLI 返回 rc=0 → 先 flush/fsync → 跑格式檢查 → 通過才原子 publish（rename）。**不通過則保留 attempt 檔並記 `format-failed`**（產出不消失，供人工檢視）。
  5. **terminal marker ≠ 檔案存在**：marker 為「本 attempt 的 publish 已完成」，須可由 audit 與檔案系統雙向確認（attempt id 綁定）。
  6. **`B-30` 回歸**：委員若誤寫 attempt 檔，最終以 publish 為準；另加**大小回歸偵測**（曾非空後歸零 → 記警示）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：CLI 執行期間 `<out>` **不存在**、attempt 檔存在；正常結束後 `<out>` 存在且 attempt 檔已清除。
  - 狀態斷言：格式不合格時 attempt 檔**仍存在**且 `<out>` 不存在，`result_state=format-failed`。
  - 狀態斷言（**stale 防護**）：預先放置一個舊 `<out>`，CLI 逾時未 publish ⇒ **不得**判 `success`；audit 須顯示該 `<out>` 非本 attempt。
  - 狀態斷言（**`B-30` 回歸**）：以「寫入 → 清空 → 重寫」序列模擬 codex 事故，最終 `<out>` 等於最後一次寫入，且警示已記入 audit。
  - 狀態斷言（**prompt 對齊**）：`cx_run.sh` 產生的 prompt 內產出路徑 == wrapper 實際期待的 attempt 路徑（**同一來源，測試比對兩者字串相等**）。
  - 狀態斷言（**並發**）：同一 `<out>` 併發兩次派工 ⇒ 兩個 attempt 各自獨立，**成功產出不得遺失**；audit 兩筆皆在。
    🔴 R1 原文以「後者覆蓋前者」為通過條件，`CODEX-R1-P0-03` 指出會丟失成功產出 ⇒ **已改為兩者皆須保留可追溯**。
  - mutation：移除 publish 改為直接寫 `<out>` → 前三條轉紅；移除 prompt 對齊 → prompt 對齊斷言轉紅。
- **邊界（≥2）**：①CLI 被 SIGKILL → attempt 檔殘留、`<out>` 不存在 ⇒ 判 `failed`，**不得因 attempt 檔格式合格而 publish** ②跨裝置 rename 失敗 → fail-closed 並明確報錯 ③attempt 檔在 publish 瞬間被外部刪除 → fail-closed。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得只改 prompt 要求委員自己做 atomic write**（不可靠，違反「工具必須自帶強制機制」）；**不得只改 wrapper 而不動 prompt**（`D-2`）。

**Task 3.3 — per-family timeout 與逾時後的 `result_state`**

- 目標：委員掛住時自動收斂，且不誤判成功。**值的定稿依賴 Task 3.1。**
  檔案：`scripts/cx_run.sh`（主 timeout）＋ `scripts/committee_run.sh:280`（外層安全閥）。
- 改法：
  1. **主 timeout 在 `cx_run.sh`**：涵蓋區間＝**CLI process-group launch → return/kill**（兩家一致），逾時終止該進程群組（避免孤兒）。
  2. **外層安全閥在 `committee_run.sh`**：上限略大於主 timeout；只在主 timeout 失效時作用。
  3. **逾時後判定**：本 attempt 已 publish → 依格式檢查落 `success`／`format-failed`；未 publish → **`failed`**。**不新增第四個 `result_state` 值**（SoT 見 `scripts/audit_events.json`）。
  4. **值**：暫定 codex 50m／grok 70m／composer 75m、外層 90m（§A `OPEN-1`）。**TODO 生成前須以 Task 3.1 的真實 duration 重算並定稿**；須可由環境變數覆寫以利測試。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/cx_run.sh WHEN cli=hang timeout_sec=1 THEN rc!=0`
  - 狀態斷言：上述情境 audit 的 `result_state` 為 `failed`，且 `<out>` 不存在、attempt 檔存在。
  - 狀態斷言：CLI 在 timeout 內正常結束且格式合格 → `result_state=success`、`<out>` 存在。
  - 狀態斷言（**孤兒檢查**）：逾時後查不到該 CLI 的殘留子進程（以 process group 為單位斷言）。
  - 狀態斷言（**值來源**）：TODO 中的 timeout 值與 Task 3.1 產出的 duration manifest 一致（**禁硬編未經重算的暫定值**）。
  - mutation：移除 timeout → 掛住情境測試逾時失敗（測試自身須有上限）。
- **邊界（≥2）**：①CLI 在 timeout 邊界正常結束（競態）→ 不得寫兩筆 `result_state` ②timeout 值為 0 或負 → 拒絕啟動並報錯 ③三家並行時其中一家逾時 → 其餘兩家不受影響。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得只加 timeout 就殺（`票 B-14` 明載：會把已完成的審查誤判為失敗）；不得繞過 Task 3.2 的 terminal marker 自行判定完整性。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 為 `b,c`；全部 10 個 Task 皆宣稱「驗證判定正確性」 ⇒ **mutation 必附**，逐 Task 已列出，全部落為 `pytest tests/governance/` 斷言。設計依 `docs/TEST_DESIGN_CHARTER.md`。
- **測試層級**：單元（正則判定／prompt 生成）＋整合（`cx_run.sh` 端到端一次真實派工）＋邊界。全部可 `pytest tests/governance/...` 獨立跑，不需 `run_api.py`。
- **`票 B-24` 紀律面（本批交付物之一，零新增元件）**：
  **本 SPEC 每個 Task 的「驗證」欄皆已寫成狀態斷言**（斷言的是**執行後的狀態**：檔案存在/不存在、序列相等、集合包含、欄位值屬 SoT 集合、sha256 一致），**而非「某腳本 rc=0」**。
  本批 TODO 須逐條沿用；code review 須逐條檢查是否有退化為 rc 斷言者。
- **防假綠**：
  - 禁改檢查器或加排除清單換綠；禁恆真斷言；禁弱化既有斷言。
  - **每個新測試須 mutation 自證**：revert 修法 → 該測試轉紅，並貼實跑 rc。
  - **既有 701 passed 為下限**；本批完工後總數只增不減；任何既有測試轉紅須具名說明。
  - 跑完測試須 `bash scripts/restore_golden_inventory.sh`，**驗收以 `git status --short tests/golden/` 輸出為空為準，不得以該腳本 rc 為證**。
- **行為差集**：Phase 2 完工須附 Task 2.5 報表；**列舉項為必要子集，附加項須逐項人工標註**，存在「非預期」即 FAIL。
- **邊界目錄**：空輸入（空語料／空指令）／並發寫（同 `<out>` 兩次派工）／API 重啟（CLI 被 SIGKILL）／大尺度輸入（4 MB prompt）。不適用：全 NaN 列、Inf、std=0、大尺度浮點 reduction。

## §R 回退

- **每 Phase 獨立 commit，可單獨 revert。** Phase 1 → Phase 3 有依賴（prompt 路徑）；Phase 0 → Phase 2 有依賴。Phase 0 與 Phase 1 彼此獨立。
- **Phase 2 為最高風險**（改判定放行/擋下）：
  - 逃生口＝環境變數一鍵回到舊判定（**僅供緊急回退，非預設關閉**——依使用者定死「驗過就別預設關閉」，Task 2.5 差集報表 rc=0 後新判定即為預設）。
  - 差集報表出現「非預期」項 → **不 merge**。
- Phase 0 為純觀測（判定行為不變），可最先 merge。
- 任一 Phase 使既有測試轉紅且無具名理由 → 不 merge。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）

- **§G Golden / Baseline：N/A** — 本批不碰數值正確性、特徵計算、ML 或回測路徑。RISK-HIT 為 `b,c`，不含 (a)／(d)。
  **替代保證**＝Phase 0 的判定行為不變證明（`(rc, kind)` 序列逐項相等）＋ Task 2.5 綁 sha256 的 immutable corpus 差集報表——兩者共同扮演本批的 baseline。
- **§A 待使用者確認：無** — 使用者 2026-08-04 明示技術取捨交委員裁決。三項 `OPEN` 已由 R1 審查裁定，裁定內容與條件已寫入 §A。
- **原 Phase 4（`B-24` 機械強制面）：移出本批** — 依 `D-6` SPLIT 裁決，理由與 grandfather 三要件（具名 owner／UTC 到期日／到期後 fail-closed 行為）已記於 `handoffs/20260801-GOV-AMEND-BACKLOG.md` 的「`票 B-24` 的拆分裁決」節，不隨拆分遺失。
