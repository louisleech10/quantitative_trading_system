# RULEIMPL SPEC 初稿審查 — Grok 委員（非作者）

**標的**：`handoffs/RULEIMPL-SPEC-DRAFT.md`（Composer 起草）  
**對照**：`handoffs/RULE-PROPOSAL-RECONCILE.md`（v2 四條 + R2）+ `handoffs/RULE-PROPOSAL-REVIEW-{codex,composer,grok}.md`  
**現碼抽驗**：`scripts/gate.sh` / `gate_check.sh` / `template_check.sh` / `run_with_receipt.py` / `verification_claim_check.py` / `reconcile_stamps_check.sh` + `tests/governance/test_dispatch_wrapper.py`（2026-07-11 本機靜態 + 實跑）  
**範圍**：只產出本檔；未改其他檔。

---

## (1) 四條是否全數落進 SPEC/TODO（含 R2 觸發 / receipt 綁定）

### 條文 1 先審後跑 — **AGREE（機械子集） / CHALLENGE（程序邊界）**

| 要求（v2 + R2） | 初稿落點 | 判定 |
|---|---|---|
| 功能定義驗收尺、委外不豁免、邊界不明從嚴 | §C + Phase 2 三態；非散文重述全文 | **AGREE**（本票為機械兜底，可接受） |
| 輸入身分 = content-hash | §C「禁止僅路徑」；V-G8 path-invariant | **AGREE** |
| disposable 機械標記 + 禁止 mv 洗白 | §C `handoffs/_disposable/` / `disposable:true`；升級=new-or-changed；3.1 拒 disposable manifest | **AGREE（政策級）**；**CHALLENGE**：無磁碟級禁搬，仍可靠編排端 `cp` 進 canonical 後手寫 manifest（靠消費端，見 §3） |
| stamp ≠ 輸出正確性 | §C 誠實邊界 | **AGREE** |
| 首次產生前 ≥2 非作者同 body-hash | Task 2.1 `new-or-changed` + stamps 同構 | **AGREE** |

**修文**：在 §C 明示「條文 1 程序面（誰審 envelope）由 VALIDATION-REVIEW 戳記強制；本票不實作 read-only 審查產物排除句的機檢，由人工/adversary」。

### 條文 2 機械兜底（R2 主力）— **AGREE 方向 / CHALLENGE 閉合度**

| R2 / v2 要點 | 初稿 | 判定 |
|---|---|---|
| §G 三機讀欄 | Phase 1 + TODO 1.1 | **AGREE** |
| 觸發 ≠ 僅 a/d：a\|d **或** 驗收尺語言 **或** 已有欄位 | Task 1.2 / 2.1(1) 聯集 | **AGREE（核心 R2 有吸收）** |
| R2「§G/**TODO** 出現產生/引用」 | 明確「本票僅 spec；todo 留 Phase 4 可選」 | **CHALLENGE**：TODO 單寫 capture、SPEC 標 none 仍可紙面合法（出生「當小任務」變體） |
| R2「將執行 validation-run/capture」作觸發 | runner 端拒 `none`；**無** Bash capture 攔 | **AGREE（與 v2 不靠 regex 主力一致）**；閉合力見 §3 |
| `none` 矛盾 / `existing-approved` 未漂 | 2.1 + V-T4/V-T6 | **AGREE**；**CHALLENGE**：existing 的 outputs hash 標「可選」→ 弱於 Grok R2「綁定 hash 未漂」 |
| 唯 runner 寫 receipt + 綁定欄 | 3.1 schema + V-G5/G6 | **AGREE**（對齊 R2） |
| 消費端拒收 | Phase 4 + V-C* | **CHALLENGE → 近 BLOCKING**：D3 預設 A + V-C4 無鍵 skip + 4.2 可整項 waive → **fail-closed 主力可整票不落地** |
| PARTIAL-MECH | §R 僅「回退 3–4 後」 | **CHALLENGE**：D3=A 完工仍應標 PARTIAL-MECH，禁止宣稱逃脫點已關 |
| `gate.sh artifact` 不驗內容 | 不改 artifact 語義 | **AGREE**（對現碼正確） |

**修文（條文 2 必補）**：〔REF:handoffs/RULEIMPL-REVIEW-R3-grok.md〕 〔SUPERSEDED:該輪 FAIL/紅燈紀錄已由後續修復輪與 ic1eb-epic-final-gate 綠收據取代;審計軌跡保留〕
1. 完工定義拆兩級：`MECH-HELPER-DONE`（governance 自測全綠）vs `MECH-FAILCLOSED-DONE`（≥1 真實 harness 強制 `require_validation_receipt`，或 SCAR 對策欄明列仍 PARTIAL）。  
2. `existing-approved`：`outputs_content_sha256`（manifest 已列之 canonical 檔）**必**重算比對，不得「可選」。  
3. TODO 觸發：至少 Phase 2 對 **同 task 的 --todo 檔** 若含 capture/baseline 語言 → WARN 或 FAIL（二選一寫死；建議 FAIL 與 SPEC 聯集）。

### 條文 3 裁量切分 — **AGREE（本票可不機械化全文）**

- v3 原則：1/3/4 依 v2 文；本票主改條文 2。  
- 初稿有 content-hash / V-G8，**無** G1 執行緒 determinism、G3 compare-schema vs sidecar 機檢 → **可接受**，但須在 §N 登記「條文 3 灰帶仍靠 envelope 人工 + adversary，本票不宣稱已機械化」。  
- **修文**：§N 增一行上述 N/A；避免讀者以為反事實測試已進 template_check。

### 條文 4 SCAR — **AGREE（另票）**

- §N / 不做：SCAR 正文另票 — **AGREE**。  
- **修文**：派工提示補「RULEIMPL 合入後 SCAR 對策欄須鏈到 validation-run + consumer；未達 MECH-FAILCLOSED-DONE 不得寫『逃脫點已關閉』」。

### 四條 ↔ Phase/TODO 覆蓋總表

| 條文 | SPEC | TODO | 缺口 |
|------|------|------|------|
| 1 | §C + 戳記前置 | 2.x stamps | disposable 僅政策 |
| 2 | Phase 1–4 | 1–4 全 | 消費端可 waive；TODO 觸發弱；existing hash 可選 |
| 3 | 幾乎無 | 無 | 須 §N 誠實 |
| 4 | §N 另票 | 無 | 另票 + 完工措辭 |

---

## (2) §G/§V 可證偽性（「改壞 gate 應紅」）

### 行為測試矩陣（V-T / V-G / V-C）— **AGREE 主體 / CHALLENGE 數項**

**AGREE**：多數案例是「壞輸入 / 缺件 / 竄改 → 期望 FAIL」與「happy path → 有 receipt+audit」，屬真可證偽；實作漏檢查時對應 pytest 應紅（TDD 向）。

| ID | 判定 | 問題 |
|----|------|------|
| V-T1–T4, T6 | **AGREE** | 缺欄/缺檔/戳記錯/none 矛盾/existing 漂移 — 可證偽 |
| **V-T5** | **CHALLENGE（BLOCKING 級）** | 宣稱 `template_check.sh spec docs/VERIFY_GATE_SPEC.md` → exit 0。**本機實跑現為 exit 1**（缺 `RISK-HIT:`、FACT-RECEIPT 格式）。且該檔本就非 validation 欄問題。用錯 grandfather 錨點 → 驗收句**今日已假**。 |
| V-G1–G4, G7 | **AGREE** | 缺參/不一致/未戳/none 拒跑 — 可證偽 |
| V-G5/G6 | **AGREE** | 對齊 `run_with_receipt` 手寫無 audit 模式；**修文**：參照名應為 `test_v6_handwritten_receipt_without_audit_blocked`（`tests/governance/test_verify_gate.py:450`），初稿寫的 `test_manual_receipt_without_audit_fails` **不存在** |
| V-G8 | **AGREE** | 釘 R2 G2 content-hash |
| V-C1–C3, C5 | **AGREE** | 消費端 fail-closed（含禁 skip） |
| V-C4 | **CHALLENGE** | grandfather「無鍵就 skip」永久旁路，除非 deadline + 預設 enforce 路徑 |

### F5「改壞 validation-run 後既有 gate 仍全綠 = 假綠」— **CHALLENGE（不可當可證偽項）**

- 現有 `test_dispatch_wrapper` / `test_verify_gate*` **本來就不覆蓋**尚未存在的 `validation-run`；改壞新子命令後「既有全綠」是**預期**，不是假綠。  
- `test_gate_bad_kind`（`test_dispatch_wrapper.py:30-41`）只 assert exit 1 且 stdout 含 `register-output`；加第四 kind **不必**改此測試也會過。  
- **「改壞 gate 應紅」真來源**應是 `test_ruleimpl_validation_gate.py` 自身，不是既有套件。

**修文 F5 / 防假綠**：
```text
F5'：故意 no-op 掉 template_check 的 validation 分支或 consumer 的 audit 比對後，
     V-T1–T4 / V-G5–G6 / V-C1 至少一條必須紅（meta 或註解強制的 sabotage 清單）。
F6：既有 governance 套件回歸全綠（與新功能正交；破則 BLOCKED 修回歸）。
```

### 觸發 regex 與既有 a/d SPEC — **CHALLENGE（向後相容假敘事）**

- 觸發含「RISK-HIT a|d 且 §G 非 N/A」→ 現況 **至少 8 份已 PASS 的 docs/*SPEC***（如 `IC_PHASE0`、`IC_PHASE1_1E1B_SIGNIF`、CUT* 等）**沒有** VALIDATION-* 三欄。  
- Phase 2 落地後，`gate.sh dispatch --spec`（`gate.sh:351-353` 已會跑 `template_check`）會對這些歷史 SPEC **新紅**，除非：遷移填三欄、或日期 grandfather、或只對「新建/變更 §G」生效。  
- 初稿 §C 只保證「**未觸發**的既有 SPEC 不因新欄失敗」，**未**處理「**會觸發**的歷史 a/d SPEC」。  
- 另：IC_PHASE0 §G 大量 baseline 語言 → 即使標 `none` 也會撞 V-T4 類矛盾。

**修文（二選一，須鎖死）**：
- **A（推薦）**：`VALIDATION_ENFORCE_AFTER=<date>` 或 manifest 白名單；日期前 a/d SPEC 缺三欄 → WARN 不 FAIL；新 SPEC / 新 commit 觸碰 §G → FAIL。  
- **B**：Phase 0 遷移票，允許改 `docs/IC_*_SPEC.md` 批量補 `existing-approved`/`none`+理由（**擴大 scope，須編排端核准**）。

---

## (3) fail-closed 完整性（缺件 / 未知值 / 繞過）

| 路徑 | 初稿 | 判定 |
|------|------|------|
| 缺三欄（已觸發） | FAIL | **AGREE** |
| `new-or-changed` 缺 manifest/戳記 | FAIL | **AGREE** |
| 手寫 receipt 無 audit | 消費端 FAIL | **AGREE**（同 verify 哲學） |
| `VALIDATION-ARTIFACT` 未知/typo | 僅提 case 正規化 | **CHALLENGE**：須 **顯式 FAIL**（非默認當 none） |
| `none` + 產生尺語言 | FAIL | **AGREE**；regex 有限 → 改名「preflight 探針」可逃（composer E1；可接受為 PARTIAL，須寫進誠實邊界） |
| 編排端直跑 `python scripts/capture_*` | 不攔（§C 不做 regex 主力） | **AGREE 與 v2**；**閉合依賴消費端** |
| 消費端未接入真實 harness | D3=A / 4.2 waive | **CHALLENGE BLOCKING**：與條文 2「下游拒收為 fail-closed 主力」衝突 |
| `VALIDATION_CONSUMER_ENFORCE=0` | 限 governance 測試 | **AGREE**；須防文件教生產關閉 |
| disposable 升級洗白 | 政策禁止 | **CHALLENGE**：無機械禁 `cp` |
| `gate_check.sh` 不認 `validation-run` | 白名單無 `gate_check.sh`；token 不進 PreToolUse | **AGREE 現碼**（`gate_check.sh:35-62` 僅 dispatch/artifact）；初稿把 validation-run 當 **canonical runner 入口** 而非 PreToolUse kind — 須在 §C 一句寫清，避免「有 token 就進 hook」誤解 |

**修文 §C 誠實邊界（建議整段替換）**：
> 本票 fail-closed = template_check（派工/規格）+ validation-run（產尺）+ consumer（讀尺）。  
> 未完成真實 harness 接入前狀態 = **PARTIAL-MECH**。  
> 不阻擋編排端任意 Bash；不擴充 `gate_check` capture 關鍵字。  
> 未知 `VALIDATION-ARTIFACT` 值 = FAIL。

---

## (4) 與現碼整合點（抽驗行號）

### 初稿 §A FACT-RECEIPT — **AGREE（結論對）**

| 主張 | 抽驗 | 判定 |
|------|------|------|
| 無 `VALIDATION-ARTIFACT` in template | `grep -c` → 0 | **AGREE** |
| 無 `validation-run` in gate.sh | → 0 | **AGREE** |
| `run_with_receipt.py` shebang python3 | L1 | **AGREE** |
| 三種 kind | `gate.sh:39-40` `dispatch\|artifact\|register-output` | **AGREE** |
| TTL 900s | `gate.sh:395`；`gate_check.sh:14` | **AGREE** |
| artifact 不跑 template_check | `gate.sh:369-376` 只驗 path/sections 非空 | **AGREE**（對齊 codex/composer） |
| dispatch 跑 template_check | `gate.sh:351-353` | **AGREE** |
| RISK-HIT a/d → §G atol\|rtol\|sha256 | `template_check.sh:102-112` | **AGREE** |
| stamp 格式同構 | `reconcile_stamps_check.sh:10-13,46-57` body=`## 戳記` 前 | **AGREE**；D1 選 A 與現碼一致 |

### 整合設計讀碼 — **CHALLENGE 數處**

1. **`validation-run` token 與 `gate_check`**：`gate_check` 不讀第四 kind（L39 只允許三 kind）。Runner 自管 token 可，但**不是** PreToolUse 門；初稿 Task 3.1「mint token」易被誤解成 hook 閘。**修文**：改稱「run lease / 內部互斥檔」或明寫「不進入 gate_check」。  

2. **`run_with_receipt` 重用**：`append_audit_event`（`run_with_receipt.py:361-392`）固定 `event:receipt` + `emitter:run_with_receipt.py`。validation schema 分離正確；若 D2=B 併入 `verify_audit.log`，consumer **必須**濾 `event:validation_run` + emitter，禁與 VERIFY receipt 混判。  

3. **`verification_claim_check.py`**：**初稿零整合**。該檔認 VERIFY/`run_with_receipt` provenance（如 L958+ audit 比對）。validation_run receipt **不可**被當成 VERIFY claim 後盾，除非另開契約。  
   **修文 §C**：`validation_run` ≠ `VERIFY:` claim receipt；正確性主張仍走既有 verification_claim_check。  

4. **`ic1eb_b5_replay.load_manifest`**（`scripts/ic1eb_b5_replay.py:56-60`）僅 `json.loads`，無 receipt。D3=A 則出生路徑消費者仍裸讀 — 與 R2「消費端主力」缺口同 §3。  

5. **參照測試名錯誤**：見上 `test_v6_handwritten_receipt_without_audit_blocked`。  

6. **V-T5 錨點錯誤**：grandfather 應用**今日已 PASS** 檔，例如 `docs/TEMPLATE_GATE_FIX_SPEC.md` 或 `docs/INSTREV_PHASEB_SPEC.md`（本機 `template_check` exit 0），**不要**用 `VERIFY_GATE_SPEC.md`。  

7. **`test_gate_bad_kind`**：更新 usage 字串時保持 `register-output` 子字串即可；不必為 F5 綁死。

---

## (5) scope 膨脹 — **AGREE 主體 / CHALLENGE 邊界**

| 約束 | 初稿 | 判定 |
|------|------|------|
| 不碰 `momentum/` `api/` | 白名單 + §N | **AGREE** |
| 核心 scripts + governance 測試 | 是 | **AGREE** |
| 可選 `ic1eb_b5_replay.py` | scripts，非生產引擎 | **AGREE**（控 scope 選 A 合理） |
| 不改 SCAR 正文 | §N | **AGREE** |
| 不改 `gate_check` capture hook | 明示不做 | **AGREE**（與 v2；非膨脹） |
| 歷史 `docs/*_SPEC.md` 批量補欄 | **未寫入白名單卻會被 Phase 2 間接強迫** | **CHALLENGE**：要嘛 enforcement 日期 grandfather，要嘛另開遷移 scope — **不可 silently 紅掉 8+ 現役 SPEC** |
| 開決策 D1–D3 | 有 | **AGREE**；D3 與完工分級綁定（見 §1 修文） |

**不做清單守住**：無生產數值容差、無 fake data、無弱化既有斷言 — **AGREE**。

---

## 彙總裁決表

| # | 審項 | 總判 | 一句 |
|---|------|------|------|
| 1 | 四條 + R2 落入 | **CHALLENGE** | 條文 2 骨架與 R2 觸發/ receipt 綁定有吸收；消費端可 waive + TODO 觸發弱 + existing hash 可選 → 閉合不足 |
| 2 | §G/§V 可證偽 | **CHALLENGE** | V-T/G/C 主體可證偽；**V-T5 現況假**；F5 定義錯；缺「破壞檢查器應紅」 |
| 3 | fail-closed | **CHALLENGE** | 缺件路徑好；未知 enum 未釘；**主力消費端可整票不接**；Bash 旁路靠 PARTIAL 誠實 |
| 4 | 現碼整合 | **CHALLENGE** | kind/TTL/template_check/artifact 讀對；**誤引用測試名**；**verification_claim_check 未劃界**；validation token≠gate_check |
| 5 | scope | **AGREE*** | 生產碼邊界守住；\*歷史 a/d SPEC 相容未設計會變成隱性 scope 炸彈 |

---

## 必須修文清單（吸收前不建議 stamp / 派實作）

1. **V-T5** 改錨今日 PASS 的 SPEC；並定義 a/d 歷史 SPEC 的 WARN/日期 grandfather 或遷移票。  
2. **完工分級** + D3=A 時強制 **PARTIAL-MECH** 終態措辭。  
3. **未知 VALIDATION-ARTIFACT → FAIL**；existing outputs hash **必查**。  
4. **刪/改 F5**；改為新套件 sabotage 可證偽 + 既有套件回歸正交。  
5. 修正 `test_manual_receipt_*` → `test_v6_handwritten_receipt_without_audit_blocked`；§C 劃清 validation_run vs VERIFY claim。  
6. Task 3.1 token 語意對齊 `gate_check` 現況（非 PreToolUse kind）。  
7. §N 登記條文 3 未機械化；TODO 觸發縫至少 WARN/FAIL 之一寫死。

---

## 非阻塞讚同（可保留）

- 不以 Bash 檔名 regex 當主力（v2 + 三家共識）— **AGREE**。  
- receipt schema 與 `run_with_receipt` 分離、audit 防手寫 — **AGREE**。  
- 白名單不碰 momentum/api/data_cache — **AGREE**。  
- D1 戳記附著 manifest / D2 併 audit log 建議合理 — **AGREE**。

---

ASSUMPTIONS_VERIFIED: RULEIMPL 初稿全文；RECONCILE v2+R2；三家 REVIEW；gate.sh:39-40,351-353,369-376,395；gate_check.sh:14,35-62；template_check.sh:102-112；run_with_receipt.py:361-398；reconcile_stamps_check.sh:10-57；test_dispatch_wrapper.py:30-41；ic1eb_b5_replay.py:56-60；實跑 `template_check.sh spec docs/VERIFY_GATE_SPEC.md` → exit 1；多份 IC_* SPEC 現況 PASS 且 RISK-HIT 含 a/d  
TESTS_RUN: `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` → FAIL（缺 RISK-HIT/FACT-RECEIPT）；對 `docs/*SPEC*.md` 掃描 PASS 集合含 IC_PHASE0 等 a/d 檔  
FAILURES_SEEN: none（審查過程）  
SCOPE_CHANGES: none（僅本審查檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: BLOCK
