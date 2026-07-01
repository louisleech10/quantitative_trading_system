# VERIFY_GATE_SPEC — Adversarial Review（Composer 2.5，獨立稽核）

**審查對象**：`docs/VERIFY_GATE_SPEC.md`（作者 Claude，不自審）  
**對照**：`docs/VERIFY_GATE_BRIEF.md`、`handoffs/20260701-FF-FORENSICS-RECONCILE.md` §3、既有 `scripts/gate_check.sh` / `gate.sh` / `mutation_probe_check.sh`  
**方法**：以「攻破 SPEC」為目標；下列每條附可執行反例或事故重現路徑。

---

## 總評

SPEC 方向正確（receipt + claim checker + hook），但**未閉合本次事故的核心破口**——「機制在、人跳過」與「不 commit 也能污染 HANDOFF」。多處關鍵語義未定義（同段、驗收語境、pending 偵測），`runtime_class` 自填、`VERIFY-EXEMPT` 無審批、詞表可同義詞繞過，使 v1 實作後仍可能假綠。§V 僅 2 項 mutation 探針，未覆蓋繞過面。

**VERDICT: CHANGES-REQUESTED** — 須補 BLOCK 級缺口後再派實作；否則高概率重演「有閘、但從旁路走」。

---

## ① Claim checker 繞過手法

### [BLOCK] 詞表不全／同義詞規避

SPEC P2-1 詞表為閉集，但 reconcile §2 與真實事故文案已用未列詞：

| 反例（真實或高概率） | 為何繞過 |
|---|---|
| `也正確紅`（`METAFIX-PROMPT` L6） | 非 `真紅` 子字串；若實作只做精確詞表 |
| `驗收通過`、`驗證完成`、`全綠`、`mutation 探針綠` | 語意等同「已驗」但未列 |
| `STATUS: DONE`（METAFIX L17、執行合約收尾） | pending 規則提 DONE，CLAIM 詞表未列 DONE |
| `無洩漏`、`no look-ahead`、`look-ahead free` | 英文／簡寫變體 |
| `PASS`（reconcile §3 有列）vs SPEC `runtime PASS` | SPEC 與 reconcile 不一致；bare `PASS` 是否觸發未定 |
| `綠燈`、`可 merge`、`P0 已閉` | 編排常用收尾，零 receipt 要求 |

**要求**：詞表須含事故原文 regression fixture（`7e71fd1` HANDOFF、`9f9839d` body、`METAFIX` L6），或改為「驗收極性模式」（已驗/通過/DONE/紅綠燈/無洩漏 look-ahead 等）+ 明確 normalization（NFKC、全半形）。

### [BLOCK] 「同段」未定義 → 拆段繞過

P2-1：「含 CLAIM 的**段落/行**須同段含 `VERIFY:`」——無演算法。

反例：

```markdown
## 驗收
對齊 mutation 已驗 ✅，無 look-ahead。

## 證據
（空）

<!-- 文末 -->
VERIFY:20260701-smoke-receipt-id
```

若 checker 以 blank-line 分段，CLAIM 段無 VERIFY → 應擋；若以「同檔案任意位置」→ 假綠。SPEC 未規定 → 實作者任選 → 可攻破。

### [MAJOR] VERIFY 與 CLAIM 語義脫鉤

反例：`已驗 mutation 真紅 VERIFY:<指向 columns-gate smoke 的 receipt_id>`。  
sha 校驗通過、exit=0，但若 claim 未含 `mutation|runtime|慢測|真跑`（只寫「已驗」），規則④可能不觸發；規則⑤「若 claim 引用 node-id」為條件式，純「已驗」無範圍 → **快測 receipt 撐泛化已驗**（本次事故類型）。

### [MAJOR] 偽造 receipt sha — 部分可擋、標籤可騙

規則②校 sha 是對的。但攻擊面在**產生端**：

```bash
run_with_receipt.py --claim-id fake --runtime-class mutation_runtime -- \
  python -c "import sys; sys.exit(0)"
```

JSON 內 sha 與 log 一致、exit=0、class=mutation_runtime，但 command 非 pytest。規則⑤僅在 claim **引用** node-id/marker 時才交集檢查 → **空殼 mutation receipt 可支撐「已驗」**。

另：`handoffs/run_receipts/` **未在 `.gitignore`**（SPEC 只禁二進位 commit）。攻擊者可 commit 自製 receipt+log（sha 自洽）+ handoff VERIFY 指向它 → 歷史永久假證據。

### [BLOCK] VERIFY-EXEMPT 濫用

豁免兩條皆無審批、無 rate limit：

```markdown
# VERIFY-EXEMPT: wip
已驗 ✅ 對齊 mutation 真紅
```

```markdown
<!-- claim-context: discussion -->
已驗 ✅ 慢測全過
```

反例：整段 HANDOFF 包在 HTML comment；或每行 claim 前加 `# VERIFY-EXEMPT: temp`。V7 只測「附 EXEMPT 理由 → 通過」，**未測濫用應擋**。

### [MAJOR] Unicode／零寬字元

未要求 NFKC／strip ZWSP。反例：`已​驗`（U+200B）、全形 `已驗`、`已 驗`（空格拆分）可能逃 substring 匹配。

### [MINOR] `passed`「限 handoff/commit 敘事」

未機械定義。反例：引用 pytest 輸出 `` `42 passed` `` 在討論段 vs 宣稱段 — 誤擋或誤放取決於實作，SPEC 無判準。

---

## ② runtime_class 偽造或誤標

### [BLOCK] 完全自宣告、無交叉驗證

`run_with_receipt.py` 的 `--runtime-class` 由呼叫者傳入；SPEC **無**根據 command argv 推導或拒絕矛盾標籤。

反例：

| 實際命令 | 標籤 | claim |
|---|---|---|
| `pytest -k test_mutation_`（真 mutation） | `helper_smoke` | 若 claim 只寫「已驗」→ ④不觸發 |
| `python -c pass` | `mutation_runtime` | 「已驗」+ 合法 sha → 可能放行 |
| `mutation_probe_check.sh` 只跑 `-k test_mutation_` | `requires_kline_runtime` | reconcile 要的 kline 慢測與 mutation 未分級約束 |

### [MAJOR] 耗時僅 WARN

P2-1 明訂 `duration < 5s` + `requires_kline_runtime` → WARN 非擋。反例：0.38s smoke 標 `requires_kline_runtime`，宣稱「kline 慢測已驗」——與本次 0.38s 誤讀同型；依 SPEC 可 WARN 後仍 commit。

### [MAJOR] pytest 解析失敗 → 規則⑤失效

P1：`pytest_summary/... 無法解析→null+不阻斷`。反例：刻意用非 pytest 包裝或破壞輸出格式 → `selected_node_ids=[]` → 範圍匹配永遠跳過。

### [MINOR] 極性詞與詞表脫節

規則③要辨識「真紅/FAIL claim」，但 CLAIM 詞表已含 `真紅`；若寫「正確紅」「探針紅」→ 極性檢查可能不觸發卻語意宣稱失敗狀態（METAFIX 語境）。

---

## ③ Pending ledger race／可繞

### [BLOCK] 偵測機制空殼

P2-2：`run_with_receipt.py` 或 **RESULT 模板偵測**「留 X 驗 / RUNTIME_*: NOT_RUN」——**無格式、無 regex、無誰負責寫 open**。實作可永遠不 append → ledger 空 → pending fail-closed 永不觸發。

### [BLOCK] 完全繞過 ledger

攻擊：執行端**不寫**「留 Claude 驗」、不寫 `NOT_RUN`，直接 HANDOFF「已驗」+ 假 receipt。本次 babu8o07p RESULT 其實誠實分列，但**惡意或疏忽的編排端可省略** → ledger 無 entry → 無擋。

### [MAJOR] TOCTOU / 無鎖 append-only

`pending_verifications.jsonl` append-only **無 file lock**。反例：進程 A 寫 open、B 同時寫 closed；或 commit hook 讀 ledger 時尚未 flush open → 「已驗 DONE」先 commit。

### [MAJOR] task_id 綁定未定

「同 task_id 有 open」——task_id 從哪來（檔名 prefix？YAML？手寫？）未規定。反例：pending 開在 `P0-FF-3`，claim 寫在 `P0FF3` / 不同 slug → 不匹配 → 放行。

### [MINOR] open 永不過期

無 TTL／supersede。陳舊 open 要麼永久擋錯 task，要麼被新 task_id 繞過。

---

## ④ Hook 安裝／停用靜默跳過（本次事故核心）

### [BLOCK] 與 `mutation_probe_check` 同型：opt-in hook，無強制安裝

§A 已確認 **git hooks 目錄無自訂 hook**。P3-3 `install_verify_hooks.sh` 為**手動**；SPEC 無：clone 後強制、CI 檢查 `core.hooksPath`、SessionStart 提醒。  
**反例**：新機器 / 忘記 install → 與「不跑 mutation_probe_check」完全同構。

### [BLOCK] `git commit --no-verify` 未處理

SPEC 全文未提 `--no-verify`。pre-commit/commit-msg **可被標準 git 旗標跳過**。  
反例：本次若只有 hook，編排端仍可用 `--no-verify` 提交 `9f9839d` 級假 claim。§R 還把 `unset core.hooksPath` 列為正當回退 → **制度化旁路**。

### [BLOCK] 不 commit 即可污染 HANDOFF（編排主路徑）

`gate_check.sh` 只守 Task/Bash/Write(新 SPEC)；**不掃 HANDOFF 內容**。  
Verify hook 只在 commit 時跑。反例：Claude `Edit` `HANDOFF.md` 寫「已驗真紅」→ **不 commit** → SessionStart 注入下一 agent → **零 hook 觸發**。本次事故編排期即存在 HANDOFF 污染，未必等 commit。

### [MAJOR] 掃描範圍漏 P5 破口

P3-1：`HANDOFF.md`、`handoffs/*.md`、`docs/*.md`、commit-msg。  
**未含**：`specs/*_SPEC.md`、`METAFIX-PROMPT` 若在 `handoffs/` 有涵蓋，但 `handoffs/20260630-FF-P0FF3-METAFIX-PROMPT.md` 在 handoffs → OK；然而 **派工 prompt 放 `docs/` 以外**、根目錄 `AGENTS.md`/`CLAUDE.md`、commit **subject only 已驗** 若 hook 實作漏 body…  
reconcile P5 明確：METAFIX 前提污染 — 僅靠 handoffs glob 不足（未來 prompt 路徑不穩定）。

### [MAJOR] §R 停用說明與「防再犯」目標衝突

「停用 = unset hooksPath」對開發合理，但與 BRIEF「機器擋不靠人記得」矛盾；無 **audit log 記錄停用事件**、無 CI fail if hooks missing。

### [MINOR] `core.hooksPath` vs symlink 二選一

P3-3「或 symlink」未規定團隊標準；部分人 `.git/hooks` 部分人 `scripts/git_hooks` → 支援與測試分裂。

---

## ⑤ §V 測試是否真能證偽

### [BLOCK] mutation 覆蓋過窄

僅 V2、V4 要求 mutation（移除擋板邏輯）。**未要求 mutation** 於：

- 同段定義繞過（V2 只測無 VERIFY）
- `--no-verify`（V7 無）
- VERIFY-EXEMPT 濫用（V7 只測合法豁免）
- 同義詞 `也正確紅`（無）
- 自填 `runtime_class` 空殼 receipt（無）
- pending TOCTOU（V6 僅靜態 jsonl）
- 不 commit 的 HANDOFF 污染（無）
- 事故原文 regression `7e71fd1`/`9f9839d` byte 級（無）

### [MAJOR] V7 temp repo 不等於真實 bypass 面

測 install hook + 假 claim commit，不測：hooks 未裝、no-verify、unstaged HANDOFF、agent Write 路徑。

### [MAJOR] V3「真 claim 放行」可假綠實作

若實作只對「含 VERIFY: 且 receipt exit=0」放行，不驗 class/command → V3 綠、V4 有 mutation 但 **V3 不擋 helper_smoke + 泛化已驗**。

### [MINOR] V8 只驗 `mutation_probe_check` exit 訊息

不驗 receipt 內容正確、不驗 audit.log 格式；P4 可寫空 receipt 仍 V8 綠。

### [MINOR] 無 CI 整合測試

§V 全在 `tests/governance/` 本地 pytest；PR 不跑 hook = 主幹仍可由 no-verify 進入。

---

## ⑥ 空殼／邏輯空但貌似合理段落

| 段落 | 問題 |
|---|---|
| P2-1「通過（限驗收語境）」「passed（限 handoff/commit 敘事）」 | 無判定算法 → 實作自由裁量 → 假綠口 |
| P2-1 規則⑤「若 claim 引用…」 | 條件式使核心範圍檢查可選 |
| P2-2 pending「偵測」 | 無 schema、無觸發器、無與 RESULT 模板對齊 |
| P1 pytest 解析失敗不阻斷 | 與「範圍匹配」主軸自相矛盾 |
| §C「不得弱化 gate_check.sh」 | 正確但未要求 verify 接入 PreToolUse／Edit HANDOFF |
| P4 audit.log append | 無格式、無與 `gate.sh` audit 關聯 |
| §G N/A + §V 行為測試 | 合理，但未綁定 reconcile §3 七項閉環 |

---

## ⑦ v1 範圍致命遺漏（相對 reconcile §3）

reconcile §3 七項 vs v1（BRIEF 暫緩 #6）：

| reconcile §3 項 | v1 SPEC | 缺口嚴重度 |
|---|---|---|
| 1 Run receipt | ✅ P1 | — |
| 2 mutation_probe 寫 receipt | ✅ P4 | — |
| 3 Claim checker | ✅ P2 | 語義漏洞見上 |
| 4 pre-commit + commit-msg | ✅ P3 | 無 no-verify／無強制安裝 |
| 5 Pending ledger | ⚠️ P2-2 | 偵測空殼 |
| **6 根 HANDOFF 生成索引** | ❌ 暫緩 | **[BLOCK]** P7「過期 claim 可復活」未修；與本次 HANDOFF 紅燈+舊已驗並存同型 |
| **7 RESULT 硬欄位 `MUTATION_*`** | ❌ 全缺 | **[BLOCK]** reconcile §2 P3 次責根因仍在；pending 無可靠輸入 |

額外遺漏（三方 forensics 已列，SPEC 未收）：

- **[BLOCK]** `git commit --no-verify` / hooks 未裝備
- **[BLOCK]** Agent `Edit` HANDOFF 不經 commit（`gate_check` 不管內容）
- **[MAJOR]** 無 CI `verification_claim_check` on PR diff
- **[MAJOR]** reconcile §3 目標含 **merge**；SPEC 只到 commit
- **[MAJOR]** P6 讀碼 signoff vs runtime 信任階梯 — 無 `READONLY_SIGNOFF` vs `RUNTIME_VERIFIED` 分級
- **[MAJOR]** `run_receipts` 可進 git 歷史（無 ignore + 無 checker 拒絕 staged receipt 造假）

---

## 必修項（派實作前）

1. **BLOCK**：定義「驗收 claim」機械判準（含事故原文 + DONE/正確紅/同義詞 + NFKC）；定義「同段」算法（建議：同 markdown block / 同標題下 / VERIFY 須在 CLAIM 同行或上一行）。
2. **BLOCK**：`runtime_class` 由 command 推導或校驗（含 `mutation_probe_check` → 強制 `mutation_runtime`；裸 `python -c` 不可標 mutation）。
3. **BLOCK**：`--no-verify` 對策（CI 必跑 checker；或 document 明示不可接受 + `scripts/check_verify_hooks.sh` in CI）；hook 安裝納入 onboarding/CI gate。
4. **BLOCK**：HANDOFF 內容檢查接入 **PreToolUse Edit/Write**（至少 `HANDOFF.md`）或禁止未驗 claim 的 SessionStart 注入源。
5. **BLOCK**：pending ledger schema + RESULT 硬欄位（reconcile #7）或明確刪除並承認 P3 未閉合。
6. **MAJOR**：VERIFY-EXEMPT 限討論檔白名單 + 禁止與新驗收 claim 同段；濫用測試。
7. **MAJOR**：§V 增：事故 regression、no-verify、同義詞、空殼 receipt、EXEMPT 濫用、hook 未裝備 fail。
8. **MAJOR**：`handoffs/run_receipts/` gitignore + checker 驗 receipt 非 staged 偽造路徑。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: gate_check.sh 僅 Task/Bash/Write(新檔); .git/hooks 無自訂; run_receipts 未 gitignore; METAFIX L6 用「也正確紅」; 事故 commit 9f9839d body 含「已驗」
TESTS_RUN: 讀碼靜態（gate_check.sh, mutation_probe_check.sh, gate.sh, reconcile_stamps_check.sh, .gitignore, METAFIX-PROMPT, RECONCILE §3）
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none（僅審查產物）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**VERDICT: CHANGES-REQUESTED**
