# Template / 機檢管線獨立審查 — Composer 2.5（2026-07-04）

審查範圍：`templates/SPEC_TEMPLATE.md`、`TODO_GENERATION_PROMPT.md`、`SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`RESULT_TEMPLATE.md`；`scripts/template_check.sh`、`scripts/coverage_check.sh`；制度背景 `CLAUDE.md`（Multi-Agent / 驗證保真度 / 三方數據簽核）。  
方法：全文通讀 + 機檢實跑（含反例 fixture）+ 與現役 SPEC（`docs/IC_PHASE0_SPEC.md`）交叉對照。**未讀其他委員 review 檔。**

---

## 三題總答

### 1. 合適性

**方向正確，分層合理，但機檢與範本、制度之間有多處「聲稱擋得住 vs 實際可繞過」的裂縫。**

V13 把 V12 的 rigor 收成 gate 錨點 + adversarial 分層，對「扁平 checklist」「漏 Golden」「沒問使用者就寫完 SPEC」等真實事故有對症設計。§A / §G / per-Task 驗證·邊界·不可做、反空殼、manifest ID 覆蓋，在結構層面比純靠 Claude 記性可靠。

然而實測顯示：**高風險 (d) 可在 §N 寫 `§G：N/A` 過 gate**；**§A「已驗證事實」可承載未實測的資料結構宣稱而完全避開 FACT-RECEIPT**；**TODO 只需全域出現一次「驗證/邊界/不可做」即可過機檢，末段 Task 可全空**。這三條直接對應第三次 timestamp 事故與「精緻空殼」類失敗，使「錨點+adversarial 分層」在關鍵路徑上**未達文件聲稱的 fail-closed**。

### 2. 冗長度

**範本本體（4 檔合計 ~250 行）不算冗長，是合理熱點。真正 token 黑洞在 TODO 生成 Prompt 強制「憲法三讀」：**

| 每次付費項 | 約行數 | 判定 |
|---|---|---|
| `docs/ARCHITECTURE.md` | ~1989 | 多數中型任務可改為「按需 grep + SPEC §C 引用」 |
| `docs/DEVELOPMENT_GUIDE.md` | ~2407 | 同上；§0 已從 SPEC+憲法摘 5–10 條即可 |
| `.github/copilot-instructions.md` | ~739 | 與 `AGENTS.md`/`.cursorrules` 重疊，執行端不讀此檔 |
| Adversarial 10 類必查 | ~40 行 | **不可砍** — 失敗模式清單是 adversarial 價值核心 |
| SPEC V13 各 § 錨點 | ~60 行 | **不可砍** — 直接對應 gate |
| IC_PHASE0 級優質 SPEC 全文複製進 TODO §0 | 常見 | 重複搬運；應引用 SPEC + manifest ID |

**值得付**：§RISK/§A/§G/§P 錨點、反空殼 grep、adversarial §0 挑戰前提、RESULT 枚舉欄位。  
**可省（不砍防線）**：TODO 階段 0 無條件全讀 5135 行憲法；改為「缺什麼讀什麼 + 機檢已擋的錨點不重述」。

### 3. 遺漏 / 瑕疵

見下方 Findings。最嚴重缺口：

1. **template↔機檢漂移**（FACT-RECEIPT、§G 與 §RISK 脫鉤、TODO per-Task 欄位、§1.0/§1.4 殘留引用）
2. **制度鐵律未下沉範本**（三方真實 kline、驗證保真度三條僅在 CLAUDE.md）
3. **執行收尾雙軌**（`ASSUMPTIONS_VERIFIED` 合約 vs `RESULT_TEMPLATE` 枚舉欄位未在範本層統一）
4. **adversarial 與 gate 只驗「檔案存在/錨點在」**，不驗 reconcile 品質、findings 是否處理、真實路徑測試是否落地

---

## 挑戰前提（設計層）

**前提 A：「錨點機檢 + 不同模型 adversarial」能擋住邏輯空殼與錯前提 SPEC。**  
**反證**：機檢多為 substring presence；adversarial 輸出 gate 只查檔案存在與 provenance（`gate.sh` L190–226），**不 parse Verdict 或 BLOCKING 數量**。作者可用 `§G：N/A`、把未驗證事實寫進「已驗證事實」、TODO 末 Task 省略三欄，仍拿到 dispatch token（若 adversarial 檔路徑合規）。

**前提 B：「coverage_check 防掉項 churn」等於任務完整。**  
**反證**：只驗 `[A-1]` 字串出現（`coverage_check.sh` L30），不驗 Task 深度、不驗 manifest ID 與 §P Task 編號一致；ID 可出現在 §0 一句話而無對應 Task。

**前提 C：「V13 緊湊 SPEC 能被 follow」。**  
**部分成立**：結構可 follow，但 **SPEC_TEMPLATE 未教 FACT-RECEIPT、未統一「已驗證事實 vs 已確認」語彙**，作者照範本填反而易與機檢/CLAUDE.md 驗證保真度鐵律衝突或繞過。

**整類未覆蓋風險**：執行期 token 燒盡（無 SPEC 級成本預算）、跨 agent handoff 提示注入（範本有提、機檢不查）、**mutation/oracle 自指**（僅 VERIFY_GATE 域，未進 SPEC/TODO 範本）、**委員會 reconcile 形式過關**（戳記存在即可）。

---

## Findings

### Template ↔ 機檢漂移

**[C-1] [BLOCKING] SPEC 範本未記載 FACT-RECEIPT，機檢卻強制**  
證據：`template_check.sh` L42–73（`已確認` + 資料結構詞須鄰行 `FACT-RECEIPT:`）；`SPEC_TEMPLATE.md` §A 僅寫「附驗證方式」，全文無 `FACT-RECEIPT`；`CLAUDE.md` 驗證保真度鐵律 L143 要求實測 transcript。  
失敗：作者照範本填 `已確認: raw_data.index 是 DatetimeIndex` → gate FAIL，不知要加 `FACT-RECEIPT:`。  
修法：§A 增固定格式 + 範例一行；與 VERIFY_GATE_SPEC §P5-3 對齊。

**[C-2] [BLOCKING] 「已驗證事實」可完全繞過 FACT-RECEIPT（第三次事故同款）**  
證據：實跑 `/tmp/spec_verified_bypass.md`（§A 用「已驗證事實」寫 DatetimeIndex/int64 宣稱 + `待確認：無` + `已確認結果`）→ `template_check.sh spec` **PASS**；機檢僅在含字面 `已確認` 的行觸發 FACT-RECEIPT（L55–56）。`docs/IC_PHASE0_SPEC.md` 用「已驗證事實」承載 DatetimeIndex/int64 敘述且 gate PASS。  
失敗：未實跑 `_layer0` 仍可在 §A 寫「已驗證」資料結構，機檢綠燈 → 錯前提 SPEC 進入 TODO/派工。  
修法：FACT-RECEIPT 觸發改為「§A 內任一資料結構關鍵詞行」或強制「已驗證事實」每條須 `fact-verified` + `FACT-RECEIPT:`；禁止無 receipt 的型別/單位斷言。

**[C-3] [BLOCKING] 高風險 (a/d) 不要求 §G — §RISK 與 §G 機檢脫鉤**  
證據：`SPEC_TEMPLATE.md` L9–10、L20（命中 a/d → §G 必填）；`template_check.sh` L30–33 僅查 `## §G` 或 `§N` 內 `§G.*N/A`；實跑 `/tmp/spec_highrisk_no_g.md`（§RISK 標大+(d)，§N 寫 `§G：N/A`）→ **PASS**。`gate.sh` 無 §RISK 解析。  
失敗：數值/ML 任務無 golden 仍可 freeze/派工，驗收退回口說。  
修法：機檢解析 §RISK 若含 `(a)`/`(d)`/`高風險` 則拒絕 §N 對 §G 的 N/A，強制 `## §G` 且含 `atol|rtol|sha256` 等 token。

**[C-4] [MAJOR] TODO「每 Task 三欄」僅全域 grep 一次**  
證據：`template_check.sh` L105–108 用 `need "驗證"` 等全檔一次；實跑 `/tmp/todo_bad.md`（Task 1.2 無三欄）→ **PASS**。`TODO_GENERATION_PROMPT.md` L66、L70 聲稱每 Task 必含。  
失敗：批次末 Task 可無驗證/邊界，執行端猜測實作，adversarial 若漏掃則直接派工。  
修法：awk 按 `### Task` 分段，每段獨立檢查三關鍵字 + 反空殼。

**[C-5] [MAJOR] 治理文件仍引用不存在的 §1.0 / §1.4**  
證據：`CLAUDE.md` L41「SPEC §1.0 可測性準則」；`gate.sh` L254、`MULTI_AGENT_ORCHESTRATION.md` L69/L101「§1.4 Golden」；V13 `SPEC_TEMPLATE.md` 無 §1.0/§1.4（改為 §RISK/§G/§V）。  
失敗：artifact gate 的 `--sections` 陳述與實際範本錨點不一致，稽核/新 agent 找錯章節。  
修法：全庫替換為 V13 錨點名；`gate.sh --sections` 範例改 `§G Golden=...; §N=...`。

**[C-6] [MAJOR] 執行收尾雙軌：RESULT_TEMPLATE vs AGENTS 合約**  
證據：`RESULT_TEMPLATE.md` 要求 `STATIC_CHECK`/`RUNTIME_CHECK`/`MUTATION_CHECK`；`AGENTS.md` L29、`.cursorrules` L20 要求 `ASSUMPTIONS_VERIFIED/TESTS_RUN/...`；`check_agent_contract_sync.sh` 只查後者，不查 RESULT 欄位。  
失敗：執行端只寫 ASSUMPTIONS 塊 → `verification_claim_check.py` 可能擋 operational 宣稱，但 `template_check.sh result` 未跑；或寫 RESULT 欄位卻缺 ASSUMPTIONS → 合約 sync 仍綠。  
修法：在 `RESULT_TEMPLATE` 或合約中明訂映射（例：`TESTS_RUN` ⊆ RECEIPTS）；四源 sync 腳本加入 RESULT 錨點。

**[C-7] [MAJOR] Adversarial prompt 未要求查 FACT-RECEIPT / §G 與 §RISK 一致**  
證據：`SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §2 L39 查 §G 口號，但未列 FACT-RECEIPT、未要求「§RISK 命中 a/d 時 §N 不得 N/A §G」；§0 提「已驗證事實」但未與機檢關鍵詞對齊。  
失敗：adversarial 與機檢各擋一半，中間縫隙（C-2/C-3）兩邊都可能標「無」。  
修法：§2 增兩條必查並引用 `template_check.sh` 規則原文。

### 範本內容 / 制度缺口

**[C-8] [MAJOR] 三方數據正確性簽核未進 SPEC/TODO 範本**  
證據：`CLAUDE.md` L149–156 強制真實 `kline_cache.h5`、三方簽核；`templates/*` grep 無 `kline_cache`/`三方`/`feature_klines`。  
失敗：Feature Factory 類 SPEC 的 §G 可寫合成 fixture golden，不觸發範本層提醒，與制度衝突。  
修法：§G 增「命中 (a) 且涉 feature/kline」子條款，引用固定路徑 + 禁合成；或 §RISK 勾 (a) 時自動插入 checklist。

**[C-9] [MAJOR] TODO 階段 0 憲法來源與執行端合約不一致**  
證據：`TODO_GENERATION_PROMPT.md` L23 無條件讀 `copilot-instructions.md`；Codex/Cursor 執行讀 `AGENTS.md`/`.cursorrules`（不含 copilot 檔）。  
失敗：TODO §0 與執行端實際遵守的規則可能分叉；且每次 TODO 生成固定 ~5k 行 token。  
修法：憲法清單改 `AGENTS.md` + `CLAUDE.md` 摘要 + 按需 `ARCHITECTURE` 章節引用。

**[C-10] [MINOR] SPEC §A 三段子標題與機檢用字不一致**  
證據：範本 L24–26「已驗證事實 / 待使用者確認 / 已確認結果」；機檢 L38–39 搜 `已確認` 或 `待確認：無`；facts-resolved 可被空泛「已確認結果」標題滿足（見 C-2 反例）。  
失敗：語彙誤導作者以為「已驗證事實」= 已機檢的 fact。  
修法：統一為「已確認（須 FACT-RECEIPT）」「已驗證（code/grep）」「待確認」三類，機檢與範本同詞。

**[C-11] [MINOR] 反空殼「驗證」規則過寬且誤傷範例**  
證據：`template_check.sh` L132–137 任一 bullet 含「驗證」即需 token；`SPEC_TEMPLATE.md` L47 範例「驗證（可證偽…）」若照抄無 pytest 數字會 FAIL；範本自身跑機檢 FAIL（樣板 `{{}}` + 驗證 bullet）。  
失敗：作者複製範例段落觸發 hollow；或規則只掃 bullet 不掃「**驗證**：」表格行。  
修法：hollow 改為僅匹配 `- 驗證：` / `驗證：` 欄位值；範例改含 `pytest` token。

**[C-12] [MINOR] coverage_check 不驗 ID 語義**   〔REF:handoffs/2026-07-04-template-review-RECONCILE.md〕 〔SUPERSEDED:早期紅燈紀錄已由 TGF epic 修復+stamped reconcile 取代〕
證據：`coverage_check.sh` L30 `grep -qF "[${id}]"`；ID 可僅出現在 §0 一句話。  
失敗：manifest 全綠但 Phase/Task 漏項。  
修法：可選模式 `--require-task`：每 ID 須出現在 `### Task` 或 `**Task` 區塊內（SUGGESTION 級實作複雜度）。

**[C-13] [SUGGESTION] gate 不驗 adversarial 結論品質**  
證據：`gate.sh` L195 只 `[ -f "${adversarial}" ]` + provenance；不要求 `Verdict`、BLOCKING 清零或 reconcile APPROVED 內容審查。  
失敗：空 findings 或未修補的 BLOCKING 仍可派工（若路徑/戳記形式合規）。  
修法：輕量 grep `Verdict：可派工` + 無未處理 `[BLOCKING]`（誠實邊界：仍可偽造，但提高成本）。

**[C-14] [SUGGESTION] RESULT_TEMPLATE 未納入 BRIEF 必讀的 adversarial 鏈**  
證據：BRIEF 列 4 templates；adversarial prompt 不提 RESULT；VERIFY_GATE 域已用 RESULT 枚舉。  
失敗：高風險任務執行收尾標準因任務類型分裂。  
修法：在 `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT` 或 TODO §0 增「收尾用 RESULT_TEMPLATE」交叉引用。

### Token 經濟（補充）

**[C-15] [MAJOR] TODO 生成強制全量憲法讀取 — 每次中/大任務固定 ~5k+ 行**  
證據：`TODO_GENERATION_PROMPT.md` L23；`wc -l` ARCHITECTURE 1989 + DEVELOPMENT_GUIDE 2407 + copilot 739。  
失敗：規劃階段 token 成本主導，擠壓真正該花的 adversarial / golden 設計預算。  
修法：改為 manifest-driven 按需讀取 + SPEC §C 已列約束不重複展開。

**[C-16] [MINOR] 優質實務把整份 §A 複製進 TODO §0（IC_PHASE0）**  
證據：`docs/IC_PHASE0_TODO.md` L11–12 六項事實長摘要。  
失敗：SPEC→TODO 雙份維護，更新 SPEC 易漏 sync TODO。  
修法：TODO §0 只保留規則 + `SPEC §A 見 [M-2]` 索引，細節不複製。

---

## 機檢實跑摘要

| 探針 | 結果 |
|---|---|
| `template_check.sh spec templates/SPEC_TEMPLATE.md` | FAIL（預期：樣板 `{{}}`） |
| `template_check.sh result templates/RESULT_TEMPLATE.md` | PASS |
| `template_check.sh spec docs/IC_PHASE0_SPEC.md` | PASS（含未附 FACT-RECEIPT 的已驗證事實） | 〔REF:handoffs/2026-07-04-template-review-RECONCILE.md〕 〔SUPERSEDED:早期紅燈紀錄已由 TGF epic 修復+stamped reconcile 取代〕
| 高風險 + §G N/A only（`/tmp/spec_highrisk_no_g.md`） | **PASS（不應）** |
| 已驗證事實繞過 FACT-RECEIPT（`/tmp/spec_verified_bypass.md`） | **PASS（不應）** | 〔REF:handoffs/2026-07-04-template-review-RECONCILE.md〕 〔SUPERSEDED:早期紅燈紀錄已由 TGF epic 修復+stamped reconcile 取代〕
| TODO 末 Task 缺三欄（`/tmp/todo_bad.md`） | **PASS（不應）** |
| §A 未解待確認（`/tmp/spec_pending_unresolved.md`） | FAIL（正確） |

---

## 明確不建議改的地方（勿為省 token 砍掉）

1. **§RISK / §A / §C / §P / §V / §R / §N 錨點全集** — 對應真實事故，機檢成本低、收益高。  
2. **§A facts-resolved（已確認 或 待確認：無）** — C3 反制有效（未解 pending 實測 FAIL）；應強化而非削弱。  
3. **反空殼三件套（`{{}}` / 空表 / 驗證無 token）** — 擋「只寫表頭」；修 C-11 精準度即可，勿刪。  
4. **Adversarial §0 挑戰前提 + 10 類必查** — 機檢無法取代語義審查；這是第二道防線核心。  
5. **§G golden 細項（value hash / NaN mask / atol·rtol 分尺度）** — 直接來自值重排/局部漂移事故。  
6. **TODO 深度紅線（偽碼≥3、函式名、邊界≥2）** — 應下沉到機檢（C-4），不是刪除要求。  
7. **manifest `coverage_check`** — 防 V1–V6 churn；可加深語義（C-12）不可移除。  
8. **FACT-RECEIPT 概念本身** — 應寫進範本並擴大觸發（C-1/C-2），不是刪機檢。  
9. **RESULT 枚舉欄位 + RUNTIME PASS 須 RECEIPTS** — VERIFY_GATE 執行期誠實邊界，與 ASSUMPTIONS 合併而非二選一廢除。  
10. **雙家族 adversarial + provenance（gate W3/R7）** — 形式門檻有價值；缺的是結論品質機檢（C-13），不是回退單模型自審。

---

## 優先修補順序（建議）

1. **C-2 + C-1** — 堵 §A 錯前提（最高優先，直接對應第三次事故）  
2. **C-3** — §RISK ↔ §G 機檢聯動  
3. **C-4** — TODO per-Task 分段機檢  
4. **C-5 + C-6** — 治理文件錨點與收尾雙軌統一  
5. **C-8 + C-9** — 制度鐵律下沉範本 + 憲法讀取瘦身  

---

## 審查者說明

本報告僅審查管線文件與機檢腳本，未改動任何 template/script。`HANDOFF.md` 為 Claude 維護索引，執行端依合約不覆寫 → `HANDOFF_NOT_UPDATED: read-only 委員會審查任務`。

STATUS: DONE
