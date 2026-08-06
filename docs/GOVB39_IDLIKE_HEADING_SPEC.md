# B-39 — id-like heading 誤判修正 SPEC（rev2，三家裁定後重寫）

**狀態**：**READY-FOR-IMPL** — 規格已對齊既有契約，待實作
**票**：`票 B-39 GOV-IDLIKE-HEADING-FALSE-POSITIVE`（`handoffs/20260801-GOV-AMEND-BACKLOG.md`）
**裁定來源**：`handoffs/reconcile/20260806-govb39-b1-consult-r2/synth.md`
（三家零分歧採第五案 E2b；body hash `cc3949c0d21e87a9662b9cc2234c1ea0001b40e08bdbfc7c98a801a41cb09fda`）

🔴 **權威行為表＝`docs/GOV_DISPATCH_FLOW_FIX_SPEC.md:139-158` 的 18 列**，
由 `tests/governance/test_completeness_idlike_fp.py` 機械抽取比對。
**本 SPEC 不得與之衝突；既有 18 列一列不改，只增放行列。**

## 🔴 rev1 的三處錯誤（主委原稿，具名保留供追溯）

| # | rev1 寫 | 實況 | 發現方式 |
|---|---|---|---|
| 1 | Task 1.1＝「新增結構標題 allowlist」 | allowlist 早已存在（`completeness_check.sh:135-140`，唯一元素 `"E-1～E-7 逐條 Verdict"`）；根因在第 178 行的形狀猜測 | 動工前讀碼 |
| 2 | §V 用中文標題當驗證項 | 恆真斷言——中文不匹配舊 regex，修法前後都放行 | mutation 實跑：`### 逐項核對表` 突變後 rc 仍 **0** |
| 3 | **全篇未引用既有行為契約**（`grep -c` → **0**） | 導致 rev1 方案與 18 列契約全面衝突 | 實作後 `pytest tests/governance -q` → **10 failed, 768 passed** |
| 4 | 開票依據寫「作廢 4 輪」 | audit 只能定位 **3 輪** | `CODEX-R1-P1-03` 查 audit |

⇒ rev1 的 (3a)/(3b) 具名特徵方案**已完整還原**（`git diff -- scripts/completeness_check.sh` 零輸出），**不得再落地**。

## §0 全域規則與約束

### §0.A 數值影響

N/A — 純字串／標題判定，不涉數值計算、不動 `data_cache/`、不影響 ML 或回測路徑。

### §0.B 不變式（違反即 BLOCKING）

1. **既有 18 列行為契約零推翻**——`GOV_DISPATCH_FLOW_FIX_SPEC.md:139-158` 每列 rc 期望值逐字不動。
2. **不得以「禁用 `###`」作為修法**——那是把摩擦轉嫁給每位委員與每份 brief，不修根因。
3. 既有收斂檔**一律不改**（forward-only）。
4. **禁改測試斷言以取得綠燈**；**禁恆真斷言**（rev1 已犯，見上表第 2 列）。
5. **STRUCT_TOKEN_ALLOWLIST 初始集合須由全量掃描導出**，不得憑想像列舉（`票 B-23` 紀律）。

## §C 約束

| # | 約束 | 來源 |
|---|---|---|
| C-1 | bash 3.2 相容；`completeness_check.sh` 為熱路徑，**禁新增 subprocess 呼叫** | 既有檔頭約束 |
| C-2 | **不得改 canonical schema**（`^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`）——本票只改「誰進通道」 | §0.B-1 |
| C-3 | **不得動 body-hash 範圍**（`H2_LINE_RE` 用 `##(?!#)`）——那是另一個 Oracle | 既有邊界 |
| C-4 | forward-only：既有收斂檔一律不改 | 使用者 2026-08-06「釘死不動」 |
| C-5 | **淨摩擦須為負**（非「增量為零」） | 使用者 2026-08-06 更正 |
| C-6 | **`票 B-23` 與 `票 B-39` 適用不同域**：B-23＝標記／符號層（變體空間無界 ⇒ 白名單）；B-39＝heading 路由層（有限錨點＋arity 可表達）。二者不矛盾 | `COMPOSER-R2-P1-02`＋`GROK-R2-P0-03` |

## §RISK 風險分級

RISK-HIT: b

- **(b) 跨模組／共用路徑**：`completeness_check.sh` 由 `reconcile_build.sh`／`debt_clear.sh`／
  `gate.sh` 共用，且 `cx_run.sh` 於交件當下呼叫 `--single`。改動面波及**每一輪委員派工**。
- **(a) 數值** 不命中；**(c) 多 phase／難回退** 不命中（單函式、單 commit 可回退）；
  **(d) ML／回測** 不命中。

## §A 問題陳述

`completeness_check.sh:174-183` 以**形狀猜測** `^[A-Z]+(-[A-Z0-9]+)+$` 判定首 token 是否為 finding ID。
命中者送入 finding 通道，不符 canonical schema 即 hard-fail。

**該判準對結構標題誤擋**——實證 **3 輪**委員派工作廢（2026-08-06，audit 可定位）：
`GOVB35-SPEC-REVIEW`（`## OUT-OF-SCOPE`）／`GOVB35-SPEC-REVIEW2`（`### OUT-OF-SCOPE`，
**委員照主委 brief 指示所寫**）／`GATELEX-REDESIGN`（三家皆把 brief 小節代號寫成 `##`）。

**第 4 次發作發生在裁定本票的那一輪**：`grok` 因在報告中引用受影響字串分析問題而交件失敗
⇒ **本 bug 會阻止自己被討論**（`handoffs/20260806-govb39-conflict-grok.md` 為 format-failed 實例）。

### 語料規模（2026-08-06 全量掃描，`.claude/tmp/b39/scan_struct_tokens.sh`）

| 量 | 值 |
|---|---|
| `handoffs/`＋`templates/`＋`docs/` heading 總數 | **18,574** |
| 舊判準會送進 finding 通道（id-like） | **6,291** |
| 其中非 canonical（即會 hard-fail） | **1,236** |
| E2b 之後放行（多 token） | **944** |
| E2b 之後仍擋（單 token） | **292** |

⇒ **誤擋面下降 76.4%**（944/1236），且 292 個單 token 全數維持既有契約行為。

### §A 未解事實

已確認：本任務無需使用者提供的事實，待確認：無（使用者 2026-08-06 於裁定審閱閘選「走完 B-39」）。
全部事實可由 repo 程式碼、測試、audit log 與全量掃描導出：
①既有 18 列契約＝`GOV_DISPATCH_FLOW_FIX_SPEC.md:139-158`（測試機械抽取）；
②作廢輪數＝audit 可定位 **3** 輪；
③allowlist 初始集合＝全量掃描 18,574 個 heading 導出；
④`RECONCILE-STAMP` 為誤用形態＝實測 47 個 synth 全用 `## 戳記`、**0** 個用該形式。

## §P Phase 與依賴

**Task 1.1 — E2b 四層路由**

- 產出：`completeness_check.sh` 的 `extract_heading_ids()` 內，把單層形狀猜測改為四層：

```
① 整行命中 canonical                     → 既有 family-binding 路徑（逐字不動）
② 首 token 命中 ^[A-Z]+-R[0-9]+-P        → rc==1（near-canonical 守衛，堵尾綴）
③ 首 token ∈ STRUCT_TOKEN_ALLOWLIST      → 放行
④ 其餘 id-like：n==1 → rc==1 ；n>1 → 放行（arity 規則）
```

- 🔴 **②為必要層**：純 arity 會漏收 `## CODEX-R4-P0-01 附加標題`（多 token 但仍是 finding ID），
  該列為既有契約第 146 列，要求 rc==1。〔`COMPOSER-R2-P1-03`〕
- **STRUCT_TOKEN_ALLOWLIST 初始集合**（全量掃描導出，只收**跨 brief 固定段名**）：

| token | 語料次數 | 判定 |
|---|---|---|
| `FACT-RECEIPT` | 10 | 收錄 |
| `NON-BLOCKING` | 4 | 收錄 |
| `OUT-OF-SCOPE` | 3 | 收錄 |
| `RECONCILE-STAMP` | 8 | **不收**——既有契約第 142 列要求 rc==1；實測 47 個 synth 全用 `## 戳記`、**0 個**用本形式，戳記本體為行內格式 `RECONCILE-STAMP: <family> APPROVED`，故語料中的 8 處為**委員誤用** |
| `ID-A`／`ID-B`／`FIND-1`／`C-1`／`B-3` 等 | 2–3 | **不收**——臨時代號非固定段名；帶尾綴者由④放行 |

- **既有 allowlist 分支保留不動**（forward-only）：其唯一元素 `"E-1～E-7 逐條 Verdict"`
  為**全行**比對，與③的**首 token**比對不同層，二者並存。
- 依賴：無。
- **存活至**：長期（本票唯一交付物）。
- **覆蓋風險**：`票 B-38` 若採「`FINDINGS_COUNT: 0` 明示欄」修法會動到相鄰分支；本 Task 須讓兩者可各自獨立測試（`pytest -k` 分別選中），不得共用同一旗標。
- **驗證**：`pytest tests/governance/test_completeness_idlike_fp.py -q` → **30 passed**（23 列行為表＋7 其他用例；擴表前為 25 passed／18 列）；
  新測試 `pytest tests/governance/test_completeness_idlike_heading.py -q` 全過；
  `pytest tests/governance -q` rc **== 0** 且總數**不減少**（基線 766）。
- **邊界**：只改「哪些標題進 finding 通道」；**不改** canonical schema、family-binding、body-hash 範圍、`_validate_finding_body`。
- **不可做**：不得停用 `HEADING_LINE_RE`；不得全面放行 `###`；不得改既有收斂檔或既有 18 列。

**Task 1.2 — 反向 mutation 測試**

- 產出：對④arity 層與②near-canonical 層**各一支** mutation（共 2 支，寫入 `tests/governance/test_completeness_idlike_heading.py`），證明移除該層後對應項 rc 由 **0** 轉 **1**（或反向）。
- 依賴：Task 1.1。
- **存活至**：長期（回歸保護）。
- **覆蓋風險**：若 `票 B-38` 改動同函式，本測試須仍為紅／綠可鑑別。
- **驗證**：移除④ ⇒ `## OUT-OF-SCOPE`／`### G-1 extra` 由 rc **== 0** 轉 **1**；
  移除② ⇒ `## CODEX-R4-P0-01 附加標題` 由 rc **== 1** 轉 **0**；兩者輸出都要貼出。
- **邊界**：只針對本票修法做 mutation，不擴及其他 Oracle。
- **不可做**：不得用「刪掉斷言」當 mutation；不得用中文標題當驗證項（rev1 已犯，恆真）。

## §V 驗證策略與邊界

**A 組 — 行為契約（零回歸，逐列比對）**：由 `test_completeness_idlike_fp.py` 機械抽取。
擴表後為 **23 列**（既有 18 ＋ B-39 新增 5），整檔 **30 passed**。
本 SPEC **不列舉其內容**，避免手抄漂移〔`票 B-25` 紀律〕。
🔴 **數字須與表機械同步**：`grep -cE '^  \| \`#\{2,6\} ' docs/GOV_DISPATCH_FLOW_FIX_SPEC.md` 為權威計數，
本行任一數字與實跑不符即為漂移（`CODEX-R1-P1-02` 抓過一次：本 SPEC 曾殘留 `25 passed` 的舊值）。

**B 組 — B-39 新增放行列（須擴進權威行為表）**：

| # | heading | 期望 | 由哪層放行 | 鑑別力 |
|---|---|---|---|---|
| V-1 | `## OUT-OF-SCOPE` | rc **== 0** | ③ allowlist | 移除③轉紅 |
| V-2 | `## NON-BLOCKING` | rc **== 0** | ③ allowlist | 同上 |
| V-3 | `## FACT-RECEIPT` | rc **== 0** | ③ allowlist | 同上 |
| V-4 | `### G-1 extra` | rc **== 0** | ④ arity（n>1） | 移除④轉紅 |
| V-5 | `### E-1 換行繞道` | rc **== 0** | ④ arity（n>1） | 同上 |

**C 組 — 放寬不得漏收（守衛層）**：

| # | heading | 期望 | 理由 |
|---|---|---|---|
| V-6 | `## CODEX-R4-P0-01 附加標題` | rc **== 1** | ② near-canonical 守衛；**純 arity 在此漏收** |
| V-7 | `## A-1`／`## U-01`／`## Z-999`／`## E-1` | rc **== 1** | ④ n==1；既有契約第 156-158、153 列 |
| V-8 | `## RECONCILE-STAMP`／`## ADV-CODEX-1`／`## UNION-01` | rc **== 1** | ④ n==1；既有契約第 142-144 列 |
| V-9 | `## GROK-R1-P0-01`（檔名為 codex） | rc **== 1** | family-binding 未被削弱 |

**誠實邊界（不得宣稱本修法已全解）**：

- ~~具名殘留：`## CODEX-NOTES 討論` 會被④放行~~ ⇒ 🔴 **已於 code review 後關閉**
  〔`CODEX-R1-P1-01` 指出純 arity 讓 `## ADV-CODEX-1 討論`／`## CODEX-BAD 追加說明` 逃脫〕：
  新增 **(3a2) 層——首 token 內含合法家族名 ⇒ 判畸形，不論 arity**。
  有界性：家族名取自既有 `fam` SoT，非逐字打地鼠。
  誤擋率實測：全量掃描 **334** 個命中者**全為 `ADV-<FAMILY>-<n>` 舊格式 finding ID**，
  結構標題命中數 **0** ⇒ 本層不誤擋。放行面零損傷（`### G-1 extra`／`## OUT-OF-SCOPE`／
  `### E-1 換行繞道` 實跑仍 rc==0）。
- **仍存在的具名殘留**：非家族關鍵字 ＋ 尾綴（例 `## UNION-01 討論`）仍會被④放行，
  而其單 token 形式為契約第 144 列要求 rc==1。**本票接受此殘留**——收窄它需枚舉治理關鍵字，
  即 `票 B-23` 已否決的打地鼠。**不得宣稱所有畸形 ID 皆被攔下。**
- **中文結構標題**（`### 另外要回答的`）在修法前後都放行，rc 皆 **== 0**，**不列為驗證項**——恆真。
- ③的 allowlist 為**有限集合**，新增固定段名時須同步擴表並附誤擋率 receipt（`票 B-23` 紀律）。
- 🔴 **實作時發現（2026-08-06，本 SPEC 撰寫時未知）**：`_validate_finding_body()` 有**自己一套**
  finding ID 判定，與 `extract_heading_ids()` **不共用**。實測：移除②守衛後，
  `## CODEX-R4-P0-01 附加標題` 在 heading 層被放行，但 `_validate_finding_body()` 仍以
  `empty-shell finding` 擋下 ⇒ **rc 相同、理由不同**。
  **後果**：只看 rc 的 mutation 測不到②這一層（本票測試已改為斷言 stderr 含 `invalid finding ID`）。
  **這是「同一概念兩處定義不一致」的第二個實例**（第一個：`completeness_check.sh:60` vs `:913`）。
  **不在本票 scope**，具名留待 `票 B-25`（fact-key 單一來源）或另立票。

  🔴 **主委錯誤歸因更正（2026-08-06，第 16 次同型）**：主委曾把
  「`reconcile_build.sh` 與 `completeness_check.sh` 的 body 邊界定義不一致」
  列為本族第二個實例，並據此 `abandon` 一整輪委員債。
  **該歸因不成立**——實測真因是主委自己在 append `## 戳記` 區時多寫了一條 `---` 分隔線，
  它落進最後一個 finding 的 body 範圍而使 hash 不符；**移除該行後 `--lock` 檢查即 rc=0**。
  ⇒ **把自己造成的問題歸因給工具**。ledger 中該輪的 abandon 理由已成歷史記錄（forward-only 不改），
  本段為權威更正。

## §R 回退

單一 commit、單一函式 ⇒ `git revert <commit>` 即可。
回退代價＝恢復 3 輪作廢的風險，**不會**造成資料或既有產出損壞。

## §N N/A 登記

| 項目 | 判定 | 理由 |
|---|---|---|
| §0.A 數值影響 | **N/A** | 純字串判定 |
| ML／回測正確性 | **N/A** | 不觸 `momentum/`、`data_cache/` |
| 前端／API | **N/A** | 不動 `api/`、`frontend/` |
| 資料遷移 | **N/A** | 無持久化格式變更 |
| 效能 | **N/A** | 判定在既有 awk 迴圈內，無新增 I/O 或 subprocess（C-1）。microbench：1M headings 舊 **1.21s**、新增檢查 **1.38s**，Δ **+0.17s/M**〔`CODEX-R1-P1-03`〕 |

## §G Golden 狀態

**filled** — golden ＝ §V 三組的期望 rc 表；A 組由既有測試機械保護，B／C 組為新增。
其中 V-6～V-9 為**防退化樁**，任一轉綠即代表放寬過頭。既有 golden 檔一律不動。

## §淨摩擦

| 項 | 值 |
|---|---|
| 新增每次成本 | 3 次字串判定（allowlist lookup、near-canonical 檢查、`n=split`），既有 awk 迴圈內，**無 subprocess** |
| 發生次數 | 每次 `--single`（委員交件）與每次收斂 |
| 省下重工 | 1 輪作廢 ≈ 45–90 分鐘（2–3 家重跑＋主委重派） |
| 已避免次數 | **3**（2026-08-06，audit 可定位；**不得寫 4**——見 rev1 錯誤表第 4 列） |
| allowlist 維護 | ≈1 次/季 × 15 分鐘 |

⇒ **淨摩擦顯著為負**〔`CODEX-R1-P1-03` microbench：3 rounds × 1M headings → **−10472.49s**〕。
