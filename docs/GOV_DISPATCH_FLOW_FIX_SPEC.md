# 派工控制流缺陷修補 — SPEC **rev6**

> 來源診斷：`handoffs/reconcile/20260803-frozen-proc-v2-r{1..5}/synth.md` 實戰事故
> ｜R1 對抗審：`handoffs/reconcile/20260803-govflow-fix-r1/synth.md`（29 findings）
> ｜**R2 對抗審**：`handoffs/reconcile/20260803-govflow-fix-r2/synth.md`（13 findings，
> **三家 `RECONCILE-STAMP` 全數 APPROVED**，`reconcile_stamps_check` **rc=0**，body sha256 `95a79051…`）
> ｜日期：2026-08-03　|　對應 TODO：待生成（R3 通過後）
>
> **findings 收斂曲線：R1 29 → R2 13。**

**一句話**：v2.0 epic 五輪派工中，**三個治理機制在正當工作上誤擋或誤放**，各造成一整輪損失；
第四個機制使治理稽核軌跡永遠無法進版控。本 SPEC 修這四項。**全部是 fail-wrong，不是缺功能。**

> 🔴 **rev1 的三個根本錯誤（R1 三家一致抓出，寫在最前面防止重犯）**
> 1. **Phase 1 的收窄會放過 `## RECONCILE-STAMP`**——那正是 T5 剛堵上的事故形態。修一個誤報卻打開一個
>    **已實測發生過**的真陽性，違反本 SPEC §C 自己的禁令。
> 2. **Phase 2 只改判準無效**——`_emit_family_result`（`cx_run.sh:445`）跑在格式檢查（`:475`）**之前**，
>    audit 是 append-only，`success` 已不可變。
> 3. **我寫了兩處假事實**：邊界①宣稱 `## R2-P0-01` 現行會被擋（實測 rc=0）；(B) 案成本被誇大
>    （`register-output` 無路徑唯一性檢查）。**用假事實支撐裁定，即使結論對也是壞的推理。**

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：**大**。
- **命中高風險原則**：**(b) 跨模組/共用路徑**——四項全部改 `cx_run.sh`／`committee_run.sh`／
  `completeness_check.sh`／`verification_claim_check.py`，是**所有**委員派工與 commit 的必經路徑。
  未命中 (a)（不碰數值/資料品質）、(c)（每 Phase 獨立可 revert，見 §R）、(d)（不碰 ML/回測）。
- 未命中 (a)/(d) ⇒ §G Golden 移 §N；**但 adversarial review 仍必跑**（大任務鐵律）。

RISK-HIT: b

## §A 假設與待使用者確認

### 已驗證事實（本 session 實跑；R1 三家覆核並補充）

- **FACT-RECEIPT**: `bash scripts/completeness_check.sh --single <含 "### E-1～E-7 逐條 Verdict" 之檔> --family codex`
  → 印出 `COMPLETENESS FAIL: invalid finding ID (schema/trailing): E-1～E-7 逐條 Verdict`，rc=1（Claude 實跑 2026-08-03）
- **FACT-RECEIPT**: `printf '## RECONCILE-STAMP\n' > <隔離副本> && bash scripts/completeness_check.sh --single <該檔> --family grok`
  → rc=1，stderr 含 `invalid finding ID … RECONCILE-STAMP`（grok 實跑 2026-08-03）
- **FACT-RECEIPT**: `printf '## R2-P0-01\n' > <隔離副本> && bash scripts/completeness_check.sh --single <該檔> --family composer`
  → `COMPLETENESS PASS … 0 個 canonical ID`，**rc=0**（composer 實跑 2026-08-03）
  ——**現行即放行**，rev1 邊界①宣稱「仍須 rc≠0」為**假事實**，已刪除
- **FACT-RECEIPT**: `nl -ba scripts/cx_run.sh | sed -n '445,488p'`
  → `_emit_family_result` 在 L445、`completeness_check --single` 在 L475；L461-468 註解自承
  「此處刻意不改 result_state」且格式失敗只 `exit 3` 不回滾（grok 實跑 2026-08-03）
- **FACT-RECEIPT**: `ROUND_ID=7268d4ff… bash scripts/cx_run.sh codex …`
  → `ERROR: 家族 'codex' 在 round … 最新結果已是 success，拒重派`（Claude 實跑 2026-08-03）
- **FACT-RECEIPT**: `bash scripts/committee_run.sh …`（brief-kind=review ＋ grok）
  → `ERROR: 角色不符 — 'grok' 是現行 implementer`，**且出現在 codex/composer 已跑完之後**（Claude 實跑 2026-08-03）
- **FACT-RECEIPT**: `ls tests/governance/test_completeness_idlike_fp.py …` → 四個新測試檔**皆不存在**
  （composer 實跑 2026-08-03）——屬規劃，非既有事實

### 事故成本（實測）

| 缺陷 | 實際損失 |
|---|---|
| D-1 heading 誤報 | codex 自修 2 輪未過 ＋ 無法重派 ⇒ **R4 整輪 abandon** |
| D-2 `result_state` 過寬 | **是 D-1 無法補救的直接原因**（守衛⑥ 只擋 `success`） |
| D-3 角色檢查太晚 | grok 不可派 ⇒ **R1 整輪 abandon**（另兩家已跑完才發現） |
| D-4 claim checker vs 逐字保留 | **69 份收斂檔 0 份進 git** |

### 待使用者確認

**待確認：無**

### 已確認結果

`2026-08-03 使用者：「Ok，先做B。完成後再進行A」`——B＝本 SPEC 四項；A＝v2.0 階段 1 工具實作。

## §C 約束

- 本任務**不碰** `momentum/`／`api/`／`frontend/`，僅動 `scripts/`＋`tests/governance/`。
- 🔴 **禁止以放寬判準換綠燈**：四項全是「修誤報」，最大風險就是順手把真陽性也放過
  （rev1 就犯了）。每項修補**必須**附「原本能擋的仍然擋得住」的迴歸測試與 mutation。
- 🔴 **禁止第二份 parser**：`committee_run.sh:100-109` 已文件化禁令（不得自行 parse brief，
  須呼叫同一 `brief_conformance_check.sh`）。Phase 3 若新增 brief 解析即違規。
- 🔴 **攻擊面矩陣見 §M**（rev1 缺席，違反 CLAUDE.md 對機檢腳本改動的前置要求）。

## §P Phase 與依賴

### Phase 1 — `completeness_check` heading 判準（依賴：無）

**Task 1.1 — ID-like 誤報收窄，且不得放過既有真陽性**
- 目標：讓一般小節標題不再被判成畸形 finding ID，**同時**保住所有現行真陽性。
  檔案：`scripts/completeness_check.sh` 的 `extract_heading_ids()`（awk 區塊，現行判準約 L163-169）。
  既有 caller：見 §M。
- 改法：**本 Task 的契約是下方行為表，不是特定正則**。實作須滿足**全部**列；
  若證明無單一規則可同時滿足，須回報為 finding 而**不是**私自刪列。

  🔴 **rev2 曾列三條「已知可行方向」，經 R2 實測證明有害，已整段刪除**
  〔`COMPOSER-R2-P0-01`：方向②「含 `-P[0-3]-` 但缺 `-R[0-9]+-` 仍判畸形」與行為表第 10 列
  `## R2-P0-01` 必須 rc==0 **字面互斥**（該 token 含 `-P0-` 且無 `-R<數字>-`）；
  `COMPOSER-R2-P0-02`：方向①③ 不足以擋 `ADV-CODEX-1`／`UNION-01`〕。

  **已驗可行的一組解（`GROK-R2-P1-01` 推導並實跑驗證；非唯一解，契約仍是行為表）**：

  ```
  (1) 整行命中 canonical              → 走 family-binding（NOTAFAMILY-… 仍紅）
  (2) 【完整 heading 文字】在放行 allowlist 內 → 放行  （見下；修 E-1 誤報）
  (3) 其餘仍命中 ^[A-Z]+(-[A-Z0-9]+)+$ → 畸形  （RECONCILE-STAMP／ADV-CODEX-1／UNION-01／
                                                A-1／U-01／Z-999／CODEX-BAD／位數錯／尾綴）
  (4) 不命中 id-like                   → 放行  （R2-P0-01、中文標題）
  ```

  🔴 **rev4 曾有第 (3) 步「家族前綴＋全字母段 ⇒ 放行」，rev5 整條刪除**
  〔`CODEX-R4-P0-01` [BLOCKING]＋`COMPOSER-R4-P1-01`，兩家獨立實測：
  該步會讓 `CODEX-BAD`／`CODEX-SECURITY`／`GROK-ISSUE`／`COMPOSER-FOO` 等
  **共 17 個現行 rc=1 的 token 變成 rc=0**——修一個誤報卻放掉一整類真陽性。〕

  **根因是主委的 scope 蔓延**：R4 的**原始事故只有 `E-1～E-7`**；
  `CODEX-NOTES` 是 R2 grok 順帶提的 MINOR（明標「非 R4 主事故」），
  我把它收進行為表當成要修的誤報，於是被迫寫出第 (3) 步——
  而該步的放行條件**無法只涵蓋 `CODEX-NOTES` 一個詞**。
  ⇒ **刪除第 (3) 步、把 scope 收回原始事故**；家族前綴型誤報**不在本 SPEC 範圍**，另立票
  `GOV-COMPLETENESS-FAMILYPREFIX-FP`（見 §N）。

  🔴 **放行 allowlist（逐字，唯一集合）**：

  ```
  ALLOWLIST = { "E-1～E-7 逐條 Verdict" }        ← ATX 標記剝除後的【完整 heading 文字】
  ```

  **鍵值必須是完整 heading，不是首 token**
  〔`CODEX-R5-P0-01` [BLOCKING] 實跑：若鍵在首 token，裸標題 `## E-1` 的首 token 亦為 `E-1`
  ⇒ **被放行**，但現行 `completeness_check` 對它是 **rc=1**（`e-1|current_rc=1|rev5_literal_rc=0`）。
  同一掃描確認 A/U/Z、ADV/UNION、家族前綴、`CODEX-NOTES` **均 current=1／new=1**，
  ⇒ **`## E-1` 是唯一剩餘漏網，成因是鍵值粒度**〕。
  新增放行項須先進行為表並經委員審。

  🔴 **不得用 `^[A-Z]-[0-9]+$` 這種寬 regex**
  〔`CODEX-R3-P0-02` [BLOCKING]：codex **實作五步程序並實跑**——十列全過
  （`FIVE_STEP_MATRIX: 10/10 expected rows matched; rc=0`），
  **但**對未列入行為表的 `A-1`／`U-01`／`Z-999` 也一併放行，而現行 `completeness_check`
  對三者皆 **rc=1** ⇒ 一整類真陽性靜默變綠。
  **十列全過 ≠ 真陽性邊界閉合。**〕
  ⇒ allowlist 只放行**本 SPEC 行為表明列**的誤報形態；新增放行項須先進行為表並經委員審。
- **行為表（＝驗收契約；每列一個 pytest 參數化用例）**：

  | heading | 現行 | 修後**必須** | 理由 |
  |---|---|---|---|
  | `### E-1～E-7 逐條 Verdict` | rc==1 | **rc==0** | 本票要修的誤報（R4 事故） |
  | `## RECONCILE-STAMP` | rc==1 | **rc==1** | T5 已實測事故形態，**不得放過** |
  | `## ADV-CODEX-1` | rc==1 | **rc==1** | 同上類 |
  | `## UNION-01` | rc==1 | **rc==1** | 同上類 |
  | `## CODEX-R4-P0-1` | rc==1 | **rc==1** | 位數錯 |
  | `## CODEX-R4-P0-01 附加標題` | rc==1 | **rc==1** | 尾綴 |
  | `## NOTAFAMILY-R1-P0-01` | rc==1 | **rc==1** | invalid family（既有行為不變） |
  | `## CODEX-NOTES` | rc==1 | **rc==1** | 🔴 rev5 更正——**不再視為本 SPEC 要修的誤報**（見上刪除說明），另立票 |
  | `## CODEX-BAD` | rc==1 | **rc==1** | 🔴 rev5 新增（`CODEX-R4-P0-01` 實測） |
  | `## CODEX-SECURITY` | rc==1 | **rc==1** | 🔴 同上 |
  | `## GROK-ISSUE` | rc==1 | **rc==1** | 🔴 同上 |
  | `## COMPOSER-FOO` | rc==1 | **rc==1** | 🔴 同上（composer 實測共 17 個同型） |
  | `## E-1` | rc==1 | **rc==1** | 🔴 rev6 新增（`CODEX-R5-P0-01` 實測）——**裸標題**，與 `### E-1～E-7 逐條 Verdict` 必須分開判定 |
  | `### 實測摘要` | rc==0 | **rc==0** | 中文標題不得回歸 |
  | `## R2-P0-01` | **rc==0** | **rc==0** | ⚠️ 現行即放行；rev1 誤稱會擋，已更正 |
  | `## A-1` | **rc==1** | **rc==1** | 🔴 rev4 新增（`CODEX-R3-P0-02` 實跑）——五步程序第 (2) 步會誤放 |
  | `## U-01` | **rc==1** | **rc==1** | 🔴 同上 |
  | `## Z-999` | **rc==1** | **rc==1** | 🔴 同上 |

- **驗證（可證偽；`pytest tests/governance/test_completeness_idlike_fp.py` 須 **19 passed**，rc==0）**：
  上表每列一個用例（**18 列**，機械計數），逐列比對 rc；**另加第 19 個 mutation 用例**（下）。

  🔴 **數字須與表機械同步，不得手寫**〔`CODEX-R5-P1-02`＋`GROK-R5-P1-01`＋`COMPOSER-R5-P1-01`
  **三家同時抓到**：rev5 表已 17 列，驗證段仍寫「13 列／14 passed」
  ⇒ 照 14 passed 當 gate 會**正好漏測 R4／R5 新增的四列否定例**——那四列正是前兩輪的漏網〕。
  **這是主委本 session 第四次數量寫錯**（前三次：consumer 閉包 12/13/15、戳記檔數 2/31/0、§M 列數）。
  ⇒ **TODO 階段一律以機械計數產生 node 清單與總數，禁止手寫數字。不得刪列湊數。**

- 🔴 **第 19 個用例＝mutation，須附機械突變食譜**
  〔`GROK-R3-P1-02`：rev3 未重述已刪方向 ⇒ 實作者無從得知 mutate 成什麼；
  `COMPOSER-R3-P1-01`：缺機械食譜 ⇒ 會做成空心探針〕：

  **突變目標（rev2 已刪的三條方向，逐字重述，僅供 mutation 使用，不得回到正文）**：
  ```
  ① 家族前綴候選額外要求含 -R[0-9]+-
  ② 含 -P[0-3]- 但缺 -R[0-9]+- 仍判畸形
  ③ 治理關鍵字（含 STAMP／RECONCILE）明列必擋
  ```
  **機械食譜**：把 `extract_heading_ids()` **複製到隔離副本**（禁改 repo 內腳本），
  🔴 **以①②③ 完全「取代」本 Task 的決策程序——不是在第 (3) 步之上「疊加」**
  〔`GROK-R4-P1-02`：若讀成疊加，`ADV-CODEX-1` 會維持 `rc=1`
  ⇒ **mutation oracle 永不轉紅＝空心探針**〕；`extract_heading_ids()` 其餘邏輯不動。
  對該副本跑本測試檔的全部行為表列。
  **TODO 須具名**：mutation patch 的行範圍、pytest node ID、以及
  「轉紅 → 恢復修法 → 再轉綠」的**兩段 receipt**〔`CODEX-R4-P1-01`〕。
  **預期**：`## ADV-CODEX-1` 由 `rc==1` **轉為 `rc==0`**（三方向抓不到它），該用例**轉紅**。
  ⇒ 以測試釘死「三方向不足」，防止日後被當充分條件重新引入。
- **邊界（≥2）**：① heading 含全形字元或 `～` 分隔（截斷點行為）② heading 為空或僅 `##`
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得**改動 canonical ID 正則 `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`；**不得**放寬 family-binding。

### Phase 2 — `result_state` 收窄（依賴：Phase 1 —— **語意耦合，見 §R**）

**Task 2.1 — 格式檢查必須跑在 audit append 之前**
- 目標：格式不合規的產出不得記為 `success`，使守衛⑥ 允許同輪重派。
  檔案：`scripts/cx_run.sh`（`_emit_family_result` 與其呼叫點的**順序**）。
- 🔴 **改法（順序是規則本身）**：

  ```
  brief-kind ∈ {review, consult, closure} 且 cli_rc==0 且產出非空：
      先跑 completeness_check --single  →  再 _emit_family_result（或 emit 內原子分支）
        格式 rc==0  → result_state=success        + 非空 output_sha256
        格式 rc!=0  → result_state=format-failed  + 非空 output_sha256（檔在；利於偵測重派是否改檔）
      其餘（cli_rc!=0 或產出空）        → result_state=failed + 空 sha（維持現行 audit_append 例外）
      格式 checker 本身無法執行         → fail-closed，**不得**記 success
  brief-kind ∈ {impl, stamp}：判準不變、行為不變
  ```
  `format-failed` 須先加進 `scripts/audit_events.json` 的 `enums.result_state`
  （**新枚舉值建檔為單一真相源，不得散文列舉**）。
- **驗證（可證偽；`pytest tests/governance/test_result_state_format_failed.py` 須 6 passed，rc==0）**：
  - 格式不合規產出 ⇒ 最新 `committee_family_result.result_state` == `format-failed`
  - **orphan-success 否定 oracle**：格式紅時 audit 最新 `result_state` **不得**為 `success`
  - `format-failed` 後同輪重派同家族 ⇒ **允許**（現行被拒）
  - 格式合規 ⇒ `result_state` == `success`，重派仍**被拒**（既有保護不弱化）
  - `debt_clear` 對 `format-failed` ⇒ **仍拒銷帳**（守衛⑤ 不放寬）
  - `brief-kind=impl` ⇒ 判準與行為皆不變
- **process exit code 契約**〔`GROK-R2-P2-02`〕：`format-failed` 時**維持現行 `exit 3`**
  （主委現形）＋ audit 記 `format-failed`（可重派）**雙軌**。
  🔴 **不得**為求「整輪看似全綠」把 rc 改成 0——`committee_run.sh` 依 `wait` rc 標記家族失敗。
- 🔴 **harness 遷移面（rev3 新增；rev2 未具名，R2 兩家指出）**
  〔`GROK-R2-P1-02`／`COMPOSER-R2-P1-01`〕：
  - `cx_run.sh:393-395` 的 `CX_STUB_MODE=success` 只寫 `stub-ok family=…`，**無 canonical finding**
    ⇒ 格式檢查前移後，該 stub 在 `review|consult|closure` 下**必觸 `format-failed`**
    ⇒ `test_debt_emit.py`／`test_stamp_taskid_inject.py` 中綁 `result_state == "success"` 的斷言會轉紅
      （**實際數量以 TODO 階段實跑清單為準**——見下方更正）
  - `cx_run.sh:404-411` 的 `CX_STUB_MODE` **未知值**分支先 emit 再 exit，是**另一條旁路**
  - 🔴 **處置：裁定採①**——`CX_STUB_MODE=success` 在 findings-kind 下改寫**最小合法**四欄 finding
    〔`GROK-R3-P2-01` 實測：硬約束「禁止 harness 跳過格式檢查」與裁定① **相容**，
    既有 stamp 主路徑測試**可在不跳過檢查的前提下收斂**〕
    ＋ 🔴 **硬約束**：**禁止** `GOVERNANCE_TEST_HARNESS=1` 時跳過格式檢查（那是弱化 production 路徑）；
    **所有**呼叫 `_emit_family_result` 的入口（含 stub 未知值分支）須遵守同一順序表
  - **預期轉紅的既有檔**：`test_debt_emit.py`、`test_stamp_taskid_inject.py`
    ⚠️ **rev3 曾寫「大量」，經 `GROK-R3-P1-04` 實測兩檔主路徑推翻**——**不是**大量。
    TODO 須以**實跑得到的具名 node 清單與數量**取代形容詞，不得再用「大量」這類無法驗證的量詞。
- **邊界（≥2）**：① `output_sha256` 為空時 `audit_append` 只對 `failed` 放行 ⇒ `format-failed` 用非空 sha
  ② 格式 checker 不存在／不可執行 ⇒ fail-closed
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得**放寬 `debt_clear` 守衛⑤（放寬會讓空殼／畸形 findings 進收斂檔）；
  **不得**讓 `format-failed` 自動觸發重派（仍須主委顯式發起）。

**Task 2.2 — P16 凍結契約同步（依賴：Task 2.1）**
- 目標：`result_state` 的擴張同步到凍結契約，避免三方漂移。
  檔案：`docs/P16_COMMITTEE_DEBT_SPEC.md`（`enums.result_state` 相關 heading）。
  🔴 **2026-08-04 狀態更新**：本 Task 已執行，P16 走 **R 重開 → v3.0**，該檔現為**三值**；
  D-001 已標 `SUPERSEDED-BY-R` 並將內容併回本體。本行原寫「現寫二值」為**執行前的現況描述**，
  已過時〔`COMPOSER-R8-P2-03`＋`GROK-R8-P2-03`：交叉引用殘留〕。
- 🔴 **改法：預設 R**（rev2 寫「合併為單一 D 延伸」，R2 兩家皆判**不可默認**）
  〔`GROK-R2-P1-03`：`success` 語意被 R4 事故**證偽**並收窄，不是錯字級補充，
  依 v2.0 §2.1「爭議一律預設 R」；`COMPOSER-R2-P1-04`：建議 D 但**不可無裁定默認 D**〕：

  > **本 Task 預設走 R**（原檔重跑完整對抗審）。
  > **僅在使用者明示裁 D**、且觸及面與 `D-002` 合併後確認無互斥時才走 D 延伸，
  > 且該裁定**須寫進本 SPEC §A「已確認結果」**（含日期與使用者原話）。
  > **實作者不得自行選較輕路徑。**

  ⚠️ 這是**新生效的 v2.0 條文首次被實際適用**——委員援引 §2.1 推翻主委的較輕分類。
- **驗證（可證偽；`bash scripts/template_check.sh dext <延伸檔>` rc==0 且三家戳記機檢 rc==0）**：
  `pytest tests/governance/test_registry_v2_shape.py` 更新為三值後全綠。
- **邊界（≥2）**：① 若委員裁定此為 R 而非 D ⇒ 走完整重審，不得自判較輕類別
  ② `test_registry_v2_shape.py:58` 硬編二值 ⇒ 更新時**須在報告標明「契約擴張」**，禁默默刪 assert
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得**只改腳本不改凍結契約（歷史 D-003 審查已抓過此漂移）。

### Phase 3 — 角色 preflight 前移（依賴：無）

**Task 3.1 — 角色檢查移到 `gate.sh dispatch` 之前，並共用既有解析**
- 目標：`brief-kind` 與角色 SoT 不相容時，**在 gate、開債、派工全部之前**擋下，零副作用。
  檔案：`scripts/committee_run.sh`（`gate.sh dispatch` **之前**）；抽出共用角色閘供 `cx_run.sh` 復用。
- 改法：
  - 🔴 **禁止新增 brief parser**——**reuse** `brief_conformance_check.sh`（或其 `--emit <kv>` 輸出）取 `brief-kind`。
  - 抽 `_role_gate.sh`（或等效共用函式），`committee_run.sh` 與 `cx_run.sh` **呼叫同一份**。
  - 對傳入的**每一個**家族比對 `scripts/governance_roles.json` 的 `_rules`；
    任一不相容 ⇒ 印**完整不相容清單**（非只第一個）並非零離開。
  - 🔴 `claude`／`agy` 被傳入 ⇒ **fail-closed**。
    〔`COMPOSER-R2-P1-02`：`committee_run.sh:136-138` 現行對 `advisory_only` **只 `echo ⚠️` 不拒絕**
    ⇒ 主委 CSV 誤帶 `agy` 時會過家族驗證、開債後才在 `cx_run` 失敗＝R1 同型半失敗輪〕
    🔴 **判準不得對 `review_families` 與 `executor_clis` 做 raw set intersection**
    〔`CODEX-R3-P0-01` [BLOCKING]，實跑 `governance_families.json`：
    `review_families=['codex','composer','grok']`、`executor_clis=['agy','codex','cursor-agent','grok']`、
    `intersection=['codex','grok']` ⇒ **合法的 `composer` 會被拒**（它由 `cursor-agent` 執行，
    見 `cx_run.sh:434-440`）。兩欄位是**異質命名空間**（家族名 vs CLI 名）〕。
    **正確判準**：
    ```
    先建 family → CLI 正規化映射（寫死於 SoT 或共用函式）：
        codex → codex ；grok → grok ；composer → cursor-agent
    再以映射後的集合判定：家族須同時在 review_families 內、且其映射 CLI 在 executor_clis 內
    映射查無此家族（claude／agy 等）⇒ fail-closed 拒絕
    ```
    並明定 `consult` 的處理（不受 implementer 限制，但仍須通過上述映射檢查）。
  - 🔴 **暫存檔契約**〔`COMPOSER-R2-P2-01`〕：`brief_conformance_check --emit` 需暫存檔；
    **由 `_role_gate.sh` 內部自行 `mktemp` ＋ `trap` 清理**，`committee_run.sh` 只 source／呼叫
    ——避免與 `cx_run.sh:39-44` 的「單一 EXIT trap」約束衝突（trap 是覆寫非疊加）。
- **驗證（可證偽；`pytest tests/governance/test_rolegate_predispatch.py` 須 8 passed，rc==0）**：
  - 🔴 **`composer` 正例**：`brief-kind=consult` ＋ `codex,composer,grok` ⇒ **正常進行**
    （防 `CODEX-R3-P0-01` 的誤拒回歸）
  - 🔴 **傳入 `claude` ⇒ rc!=0**〔`COMPOSER-R3-P2-02`：rev3 改法要求 `claude` fail-closed，
    驗收表卻只列 `agy`，與數量宣稱不一致〕
  - `brief-kind=review` ＋ 家族含 implementer ⇒ rc!=0，且 **`.claude/gate/audit.log` 無新 `committee_dispatch`**、
    `debt_ledger --list` 無新 round、無 gate token 產生
  - `brief-kind=consult` ＋ 同樣家族 ⇒ 正常進行（不受限，語意不變）
  - `brief-kind=impl` ＋ 非 implementer ⇒ rc!=0、無副作用
  - 三家中僅一家不相容 ⇒ **整批拒絕**且訊息列出該家族
  - 傳入 `agy` ⇒ rc!=0
  - `governance_roles.json` 讀取失敗 ⇒ rc!=0（fail-closed）
- **邊界（≥2）**：① SoT 檔存在但 JSON 壞 ⇒ fail-closed
  ② `cx_run.sh` 的既有角色閘**仍須通過**同一組用例（共用後不得行為漂移）
- **存活至**：永久。
- **覆蓋風險**：無——`cx_run.sh` 的既有檢查**刻意保留**（前移是早退，不是取代）。
- 不可做：**不得**移除 `cx_run.sh` 內的角色閘；**不得**用第三份 inline awk/sed 抽 `brief-kind`。

### Phase 4 — claim checker 對逐字治理產物的豁免（依賴：無）

**Task 4.1 — `sources/` 副本的註冊路徑正規化（採 (A)）**
- 目標：`handoffs/reconcile/<session>/sources/<name>.md` 可豁免 prose claim，且**不放寬**其他任何路徑。
  檔案：`scripts/verification_claim_check.py` 的 `_committee_output_rel`／`_is_committee_process_exempt`。
- 改法：對該精確形態的路徑，回退比對 `handoffs/<name>.md` 的已註冊 hash；
  **限定**：路徑須為 `handoffs/reconcile/<session>/sources/<name>.md`、
  綁定同 session 的 `sources.lock`、且 **raw-byte hash 與原註冊值相符**才豁免。
  🔴 **修正 staged／worktree 不一致**：checker 從 staged blob 取內容掃描，
  但現行豁免對 working-tree 重算 hash ⇒ **兩者須取同一份 bytes**。
- **驗證（可證偽；`pytest tests/governance/test_claimcheck_verbatim_exempt.py` 須 6 passed，rc==0）**：
  - `git add -f` 一份 reconcile `sources/` ＋ commit ⇒ rc==0
  - 副本被竄改（hash 不符原註冊）⇒ **不豁免**，rc!=0
  - session 外路徑／duplicate basename／symlink ⇒ **不豁免**
  - **staged 與 worktree 內容不同** ⇒ 豁免判定與掃描內容取同一份 bytes（具名斷言）
  - `docs/` 內一般文件無 backing 的 claim ⇒ **仍 FAIL**
- **邊界（≥2）**：① 原註冊檔已被刪除 ⇒ 不豁免 ② `sources.lock` 缺失 ⇒ 不豁免
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得**改 `gate.sh register-output` 的全域語意。
  （附記：rev1 稱 (B) 需改 `register-output` 接受第二 path 為**誤述**——`gate.sh:156-177` 無路徑唯一性檢查。
  結論仍採 (A)，但理由改為「不擴 audit 表面」，非「(B) 改動量大」。）

**Task 4.2 — `synth.md` 的 unit 級附錄豁免**
- 目標：`## 附錄…` 區段豁免、`## 群集 / 處置` **永不**豁免。
  檔案：`scripts/verification_claim_check.py`——現行 `committee_process_exempt` 是
  **整檔 bool**（`:1387` 一次算完、`:1394-1400` 對所有 unit 傳同一 flag），**無法**表達區段邊界。
- 改法：改為 **unit/line 級**判定——自匹配 `^## 附錄` 的標題起，至下一個 `^## `（H2）前或 EOF 為豁免區；
  其餘區段不豁免。⚠️ 實際標題為 `## 附錄：findings 逐字保留（byte-faithful；…）`，
  **須以 `^## 附錄` 前綴匹配**，不得要求精準等於 `## 附錄`。
- **驗證（可證偽；同上測試檔，另計 5 passed）**：
  - 附錄段內無 backing 的 claim ⇒ **PASS**
  - `## 群集 / 處置` 段內同樣文字 ⇒ **FAIL**
  - 群集段下的 nested H3/H4 內 claim ⇒ **FAIL**（豁免不得外溢）
  - 一般 handoff 檔偽造 `## 附錄` 標題 ⇒ **仍 FAIL**（非 synth 路徑不適用）
  - 檔內有兩個 `## 附錄` ⇒ 行為須具名（建議：皆豁免，但須測）
- **邊界（≥2）**：① 附錄後又出現 `## 群集`（順序顛倒）⇒ 群集段仍不豁免
  ② 附錄區被插入非委員文字 ⇒ **屬已知殘留，不在本 Task 範圍**（§N 具名）
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得**用 `VERIFY-EXEMPT` 檔頭豁免整份收斂檔（會連主委撰寫段一起豁免）。
  **不得**改動 claim ledger 的 fingerprint 衝突判定（另一票，見 §N）。

## §M 攻擊面矩陣（rev2 新增；R1 三家 grep 聯集）

| 元件 | 讀/寫 | 受影響 Phase | 必跑測試 |
|---|---|---|---|
| `completeness_check.sh` | 判準本體 | 1, 2 | `test_completeness_idlike_fp.py` |
| `cx_run.sh` | emit 順序、守衛⑥、角色閘 | 2, 3 | `test_result_state_format_failed.py`、`test_rolegate_predispatch.py` |
| `committee_run.sh` | 角色 preflight | 3 | `test_rolegate_predispatch.py` |
| `brief_conformance_check.sh` | brief-kind 來源（**唯一**） | 3 | 同上 |
| `governance_roles.json`／`governance_families.json` | 角色 SoT | 3 | 同上 |
| `audit_events.json` | `enums.result_state` | 2 | `test_registry_v2_shape.py` |
| `audit_append.sh` | 枚舉驗證、空 sha 例外 | 2 | `test_debt_emit.py` |
| `debt_clear.sh` | 守衛④ roster／守衛⑤ success | 2 | `test_debt_clear.py` |
| `_debt_ledger_core.py` | 原樣輸出 `result_state` | 2 | `test_debt_clear.py` |
| `verification_claim_check.py` | 豁免判定、staged blob | 4 | `test_claimcheck_verbatim_exempt.py` |
| `scripts/git_hooks/pre-commit` | 呼叫 claim checker | 4 | 同上 |
| `verify_pretooluse.sh`／`verify_hooks_health.sh` | 掛載健檢 | 4 | 既有測試 |
| `gate.sh` | register-output、completeness 提示 | 1, 4 | 既有測試 |
| `reconcile_build.sh` | cp + lock + completeness | 1, 4 | 既有測試 |
| `reconcile_add_stamp_section.sh`／`reconcile_clear_stamps.sh` | completeness | 1 | 既有測試 |
| `gov_check.sh`／`doc_format_precheck.sh`／`draft_selfcheck.sh` | completeness／claim | 1, 4 | 既有測試 |
| `verify_task_provenance.py` | stamp provenance | 4 | `test_stamp_taskid_inject.py` |
| `docs/P16_COMMITTEE_DEBT_SPEC.md` | 凍結契約（**v3.0 三值**，R 重開後） | 2 | Task 2.2 的戳記機檢 |
| `scripts/debt_ledger.sh` | 包裝 ledger／clear 路徑 | 2 | `test_debt_clear.py` |
| `scripts/set_roles.sh` | 寫角色 SoT | 3 | `test_rolegate_predispatch.py` |
| `scripts/verify_role_gate.sh` | 角色閘 oracle | 3 | 同上 |
| `tests/governance/test_completeness_oracles.py` | completeness oracle 套件 | 1 | 本身 |
| `tests/governance/test_completeness_semantic.py` | 同上 | 1 | 本身 |
| `tests/governance/test_completeness_id.py` | ID 正則斷言 | 1 | 本身 |
| `tests/governance/test_reconcile_completeness_enforced.py` | 強制面 | 1 | 本身 |
| `tests/governance/mutation_red/test_completeness_mutations.py` | mutation 紅燈套件 | 1 | 本身 |
| `tests/governance/test_brief_conformance.py` | 釘 completeness ID 正則 | 1, 3 | 本身 |
| `scripts/governance_tools.json` | **repo 內無引用** | — | **N/A**（兩家確認） |

**每個 mutation 須明定**：改哪一行／隔離副本、預期哪個 pytest node 由 pass 轉 fail、rc 與關鍵 stdout。

🔴 **本表改為腳本生成，禁止手寫列舉**〔`COMPOSER-R3-P2-01`：`rg -l 'completeness_check|result_state'`
的 **32 命中**中仍有 **6 項**未入表；`GROK-R3-P1-03`：另有多個呼叫／釘選 `completeness_check` 的測試檔未入表〕：

```
manifest = grep -rlE 'completeness_check|result_state|committee_process_exempt|STAMP-MODE' scripts tests/governance
         ∪ 產出端 hook 表（doc_format_precheck / brief_conformance_check / verdict_filled_check / gov_check）
         ∪ 本 SPEC 新增元件（_role_gate.sh / 四個新測試檔）
```

🔴 **命令用 `grep -rlE` 不用 `rg`**——理由是**可攜性，不是「rg 不存在」**：

| 環境 | `command -v rg` | 來源 |
|---|---|---|
| grok 執行端 | **空**（未安裝） | `GROK-R4-P1-01` 實跑 |
| codex 執行端 | 非空，`ripgrep 15.2.0` | `CODEX-R5-P1-03` 實跑 |

⇒ **`rg` 不保證存在於所有執行端**，故 DoD 命令採可攜的 `grep -rlE`（兩家實測皆得 **33 命中**）。

⚠️ **rev4／rev5 曾把「`rg` 不在 PATH」寫成 `fact-verified`，那是錯的**
——那是**單一執行端**的觀察，不是跨環境事實。**結論（改用 grep）仍成立，錯的是 receipt。**
🔴 **凡涉環境的 receipt，日後一律註明來源環境**，不得升格為全域事實。

**DoD**：manifest 列數 **== 生成結果**（機械相等）；未知分類或缺 nodeid ⇒ FAIL。
🔴 **生成器本身是 TODO 的 Phase 0 交付物**（`scripts/gen_govflow_manifest.sh` 或等效），
須附 schema 與 fail oracle。**SPEC 只定契約、不實作**（範本規定 SPEC 階段禁寫實作）
〔`CODEX-R4-P1-02`／`COMPOSER-R4-P2-01`：目前只有非執行的 union 描述，實作前無法 CI 驗收〕。
⚠️ **已連續三輪因手寫而漏**（R1 漏、R2 漏九項、R3 仍漏六項）——**這是手寫必錯的第三次實證**。
上方表格自 rev4 起僅作**人類可讀快照**，**驗收以生成結果為準**。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：四項皆宣稱「修誤報而不弱化真陽性」⇒ **mutation 必附**。
  每 Task 的「真陽性仍被擋」用例即 mutation 錨點：把修補後的判準改回寬鬆版，該用例**必須轉紅**。
  **具名 mutation 錨點**：Phase 1＝`## RECONCILE-STAMP` 必紅；Phase 2＝orphan-success 否定 oracle；
  Phase 3＝三家中一家不相容仍整批拒；Phase 4＝竄改副本不豁免。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級：全部為 `tests/governance/` 整合測試（呼叫實際腳本），可獨立 `pytest` 跑。
- **四個測試檔目前皆不存在**（實跑確認）⇒ TODO 須列為 Phase gate，不得假設已存在。
- **防假綠**：
  - 🔴 **禁止**修改既有 `tests/governance/` 斷言換綠燈。既有測試因本次改動轉紅時，
    須逐條說明「該斷言原本鎖的是舊契約」並由委員裁定；`test_registry_v2_shape.py` 的二值 assert
    更新須**明標契約擴張**。
  - 探針一律用**隔離副本**，禁直接變異 repo 內 `scripts/*.sh`。
  - 新增測試須自證：revert 修法 → 轉紅（實跑貼 rc）。
  - **不得**以「3/4 passed」當充分證明；須先跑 production-path integration，再跑 full governance suite。
- **邊界目錄**：空輸入、SoT 讀取失敗、部分成功（三家中一家不相容）、重入（同輪重派）、
  staged/worktree 分歧。不適用：全NaN／Inf／std=0／OOM／大尺度浮點。

## §R 回退

- **三個獨立 rollback 邊界**（codex 建議拆三批次；grok／composer 同意合 epic ⇒ 折衷）：
  ① Phase 1＋2（ID 判準與結果狀態）② Phase 3（角色 preflight）③ Phase 4（claim provenance）
- 🔴 **Phase 1 與 Phase 2 是語意耦合，不是無耦合**（rev1 宣稱有誤）：
  Phase 2 直接呼叫 Phase 1 所改的 `completeness_check --single`；revert Phase 1 會改變 `format-failed` 判定。
  ⇒ **revert 順序須 Phase 2 先**，或 Phase 1 改動後**重跑 Phase 2 全部測試**。
- **Phase 4 獨立 commit ＋ 隔離 clone 驗證**（三家一致）：改 pre-commit 風險最高，
  須先在隔離 clone 確認 commit 仍可進行，再進 repo。
- 任一 Phase 造成 `pytest tests/governance` 轉紅或 pre-commit 全面失效 ⇒ 立即 revert 該 Phase。

## §N N/A 登記

- **§G Golden / Baseline：N/A** — 不碰數值計算、特徵生成、ML 或回測路徑，無 baseline 可凍結；
  驗收改以「行為表 ＋ mutation 轉紅」達成（§P Task 1.1 的行為表即為此設計）。
- **本 SPEC 範圍的更正（rev1 §N 有自相矛盾，已修）**：
  - 🔴 **`D-003`（`result_state` 收窄）＝本 SPEC Phase 2 的載體**，**不是** out-of-scope。
    rev1 誤標為「歸 T3」，與 Phase 2 直接矛盾。凍結契約同步見 Task 2.2。
  - 🔴 **`D-002` 的處理（rev4 更正；rev3 此處與 Task 2.2 主文字面互斥）**
    〔`GROK-R3-P1-01`：主文已改「預設 R」，此處仍寫「合併為單一 D 延伸」⇒ 實作者可依本節直接開 D 檔〕：
    > **本 Task 預設 R**（見 Task 2.2）。`D-002` 與本 Task 的合併**僅在使用者明示裁 D 之後**才適用；
    > 未裁定前，`D-002` 與本 Task **各自依 v2.0 §2 獨立處理**，不得預先合併。

    ⚠️ **這是主委本 session 第三次「改了裁決卻沒同步所有引用」**
    （前兩次：v2.0 rev5 的詞界舊定義殘留、本 SPEC rev1 的 §N 把 D-003 標 OOS）。
    **rev4 已用 `grep -n '單一 D 延伸\|合併為單一'` 機械複查**，不靠眼睛。
- 🔴 **本 session 新發現的同型缺陷（rev3 記錄，另開票，不在本 SPEC 範圍）**：
  **`GOV-GATECHECK-DEBTCLEAR-DEADLOCK`**——`gate_check.sh` 的 dispatch 分類器會因
  `debt_clear.sh --reason` 內含中文治理關鍵字而把**清債指令本身**誤判為 dispatch；
  在「有 fresh dispatch token ＋ 有開債」時，該 hook 以「債務帳本重查未通過」拒絕執行
  ⇒ **清債的指令被「因為有債」擋住＝死鎖**。
  **實測**（Claude 2026-08-03）：同一 `debt_clear --abandon` 指令，`--reason` 為中文時被 hook 拒絕；
  改為英文短句後 **rc=0 成功**。
  ⇒ 與本 SPEC 四項同族（治理檢查在正當工作上 fail-wrong），但**觸及 `gate_check.sh`／hook 層**，
  範圍不同，另開票避免本 SPEC 再膨脹。
- 🔴 **`GOV-COMPLETENESS-FAMILYPREFIX-FP`（rev5 新開票）**：
  `## CODEX-NOTES`／`## CODEX-BAD`／`## GROK-ISSUE` 這類「家族前綴＋非 finding ID」的 heading
  現行皆被判畸形（實測 17 個）。其中部分**確為誤報**（`CODEX-NOTES` 顯然是小節標題），
  但**無法只放行其中一個詞而不放行其餘**——rev4 曾嘗試（第 (3) 步），被兩家實測證明會放掉一整類。
  ⇒ **本 SPEC 不處理**；要修須先定義「哪些家族前綴 heading 是合法小節標題」的可判定契約，
  屬獨立議題。**現況維持全部擋下（不弱化）。**
- **不在本 SPEC 範圍（具名，非遺漏）**：
  - `claim ledger 的 fingerprint 衝突`（「曾有 FAIL 紀錄，舊綠 claim 未標 SUPERSEDED」）——另開票。
  - `.git/info/exclude` 排除 `handoffs/*` —— 屬 v2.0 §6.3 輔案，歸 v2.0 階段 1。
  - 收斂檔附錄區被插入非委員文字 —— 已知殘留（Task 4.2 邊界②）。
