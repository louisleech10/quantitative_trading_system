# 規則提案詰問 — Composer 委員回覆

**審查標的**：`handoffs/RULE-PROPOSAL-ORCH-SELF-ARTIFACT.md`（編排端自產 Golden/baseline/oracle「先審後跑」）  
**方法**：獨立讀提案 + `templates/SPEC_TEMPLATE.md` §G + `scripts/gate_check.sh` / `scripts/gate.sh` artifact 分支 + `scripts/template_check.sh` + `scripts/reconcile_stamps_check.sh`（戳記模式參照）+ IC1EB 出生事故鏈。  
**誠實邊界**：本回覆為制度設計審查，未改 gate 程式；機械化可行性依現行腳本靜態閱讀。

---

## 任務 A — 逐條詰問

### 條文 1：先審後跑

**立場**：**CHALLENGE**（方向正確，現文邊界與執行掛鉤不足，易留新縫）

#### 可鑽縫（「驗證性產物」灰帶）

| # | 逃脫路徑 | 為何現文攔不住 |
|---|---|---|
| E1 | **改名降級**：不叫 baseline，改稱「preflight 探針」「receipt 快照」「mutation fixture 種子」 | 「驗證性產物」無機械定義；只靠自然語言 |
| E2 | **設計檔薄化**：`handoffs/foo-receipt.md` 三行 hash，無 run 矩陣/排除清單 | 「設計檔」未綁範本錨點或 `BASELINE-DESIGN-STAMP` |
| E3 | **分拆顆數**：先跑 1 顆「冒煙」再補審擴成 13 顆 | 「動工」未界定為「任一產生程序執行」vs「首次寫入 canonical 路徑」 |
| E4 | **執行通道繞過**：編排端 `python scripts/capture_*` 走 Claude 本體 Bash，**不經** dispatch gate | 提案只要求委員審，未掛 PreToolUse；與逃脫點分析 #1 同源 |
| E5 | **消費端自產**：SPEC §G 寫「編排端產 baseline」，執行端 Task 5.1 自跑小 golden | 條文只點編排端，未禁執行端在允許檔內自產 oracle |
| E6 | **先跑再補審**：事後 `IC1EB-BASELINE-REVIEW-*`（本次事故實際路徑） | 無機械「capture 前缺戳記 → Bash DENY」 |
| E7 | **≥2 家模糊**：未指定家族、戳記格式、body-hash、與 `RECONCILE-STAMP` 是否同構 | 可自寫兩行「composer 已看」無 task-id |

#### 邊界建議（去灰帶）

**納入（須先審後跑）** — 同時滿足：

1. 產物將被 **SPEC §G / TODO / B5 測試 / gate `--manifest`** 引用為改前改後對照或驗收尺；且  
2. 程序會讀 **真實 `data_cache`** 或寫入 **`handoffs/*baseline*` / `tests/**/*golden*`** 路徑；且  
3. 輸出含 **可證偽數值指紋**（hash / atol / byte digest / manifest run 矩陣）。

**明確排除（不觸發先審後跑）**：

- 單元測試內 **hermetic / synthetic** fixture（SPEC §G 已禁用於 feature/kline 真資料刀，但允許 M-B/T-* 契約測試）；  
- **唯讀** `grep` / `pytest -k` 對既有 baseline 的複驗（不寫新 canonical）；  
- 委員會 **read-only** 設計審查派工本身（`--risk low --template n/a:`）。

#### 修文（替代條文 1）

```markdown
1. **先審後跑（驗收尺產物）**：凡編排端將執行、且產物可能被 SPEC §G / TODO / B5 / gate manifest 引用為數值或行為對照尺的程序（含 Golden、baseline、oracle、capture 腳本首次跑出的 canonical 快照），**在首次執行該程序前**，其設計檔須滿足：
   - 路徑固定為 `handoffs/*-BASELINE-DESIGN.md` 或 SPEC §G 內嵌等價段落；
   - 含 run 矩陣、落地參數、hash/canonical 政策、**明知排除清單與理由**；
   - 獲 **≥2 家**委員（預設 codex+composer；高賭注可加 grok）於設計檔 `## 戳記` 區 append  
     `BASELINE-DESIGN-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`（格式對齊 RECONCILE-STAMP）。
   **機械兜底**：`scripts/gate_check.sh` 對匹配 `python scripts/capture_*baseline*.py` / `generate_baseline` 的 Bash 無 fresh `baseline-design` token → exit 2（與 dispatch 分 token）。
   BLOCKING findings 依 Finding 閉合鐵律由原提出方複驗；**禁止**先寫入 canonical 路徑再補設計審。
```

---

### 條文 2：SPEC 範本義務 + gate artifact 機械化

**立場**：**CHALLENGE**（§G 增欄必要，但「gate artifact 檢查不過」與現行實作**不符**；須改掛點）

#### 現況（實測靜態閱讀）

| 元件 | 實際行為 | 與提案落差 |
|---|---|---|
| `gate_check.sh` Write→artifact | 僅攔 **新建** `docs/*{SPEC,TODO,PLAN}*.md` | 不攔 `handoffs/` 設計檔、不攔 `scripts/capture_*.py` |
| `gate.sh artifact` | 只驗 `--file` / `--template-opened` 存在 + `--sections` 非空 | **未**對 `--file` 跑 `template_check.sh` |
| `template_check.sh` §G | RISK-HIT 含 a/d 時查 `atol|rtol|sha256` | **無** baseline 產生程序審查戳記欄 |
| `gate.sh dispatch --spec` | 會跑 `template_check.sh spec` | 只擋「派實作」，不擋編排端自己 Bash 跑 capture |

**結論**：條文 2 若只改 `SPEC_TEMPLATE` + 指望現有 `artifact` gate，**防不住本次事故**（capture 在 `scripts/` + `handoffs/`，且 artifact 分支不機檢 SPEC 內容）。

#### 可行機械化方案（按成本排序）

1. **§G 增欄 + `template_check.sh`（低）**  
   - RISK-HIT 含 a/d 且 §G 未在 §N 標 N/A 時，要求 §G 含：  
     `BASELINE-PRODUCER: orchestrator|executor|waived:<reason>`  
     `BASELINE-DESIGN-REVIEW: handoffs/<file>.md sha256:<hash> stamps:codex+composer`  
   - 在 `gate.sh dispatch`（`--spec` 存在）與 **`gate.sh artifact` 新增**：`template_check.sh spec "${file}"`。

2. **設計檔戳記腳本（中，推薦）**  
   - 複用 `reconcile_stamps_check.sh` 模式 → `baseline_design_stamps_check.sh handoffs/*-BASELINE-DESIGN.md`  
   - `gate.sh` 新 kind `baseline-design` 或擴展 dispatch：附 `--baseline-design` 時跑戳記檢查。

3. **Bash 執行掛鉤（中，補洞關鍵）**  
   - `gate_check.sh` Bash 分支：若命令匹配 baseline capture 模式且無 `baseline-design.token` → DENY。  
   - 這才是堵逃脫點 #1 的最低成本等效點。

#### 修文（替代條文 2）

```markdown
2. **SPEC §G 與機械兜底（分兩層）**：
   - **範本**：`SPEC_TEMPLATE` §G 增（RISK-HIT 含 a/d 時必填）：  
     `- **baseline 產生程序審查**：設計檔路徑；審查方；`BASELINE-DESIGN-STAMP` 摘要（誰/日期/body-sha256/task-id）；執行者（orchestrator|executor|waived:理由）。`  
   - **機檢**：`template_check.sh` 在 RISK-HIT a/d 時驗上述欄非空且含 `BASELINE-DESIGN` 或 `waived:`；  
     `gate.sh dispatch --spec` **與** `gate.sh artifact --file` 均須呼叫 `template_check.sh`（artifact 現況缺口須補）。  
   - **執行閘**：capture 類 Bash 須 fresh `baseline-design` token（見條文 1），否則 `gate_check.sh` DENY。  
   §G 欄未填 alone **不足以**防再犯；三層缺任一則誠實標「部分機械化」。
```

---

### 條文 3：裁量 = 決策

**立場**：**CHALLENGE**（原則對，**全量委員會會癱瘓**；須分級 + 預先凍結）

#### 癱瘓風險

若「凍結文字未覆蓋之參數」**一律**走技術決策委員會：

- 每次選 staging 目錄名、log 檔名、pytest `-k` 子集、單一 symbol 冒煙、timeout 秒數 → 皆觸發委員會 → **吞吐崩潰**；  
- 編排端會反向激勵：把裁量寫進 SPEC 空殼句（「依實務選擇」）→ **假凍結**。

#### 切分判準（建議四級）

| 級別 | 觸發條件 | 流程 | 例（IC1EB） |
|---|---|---|---|
| **L0 已凍結** | SPEC/TODO/§G 明文寫死 | 照做，**不**算裁量 | symbol 列表、§G 資料集、atol/rtol |
| **L1 實施細節** | 不改 oracle 語意、不增刪 run 維度、不碰排除政策 | 設計檔 **記錄即可**，無委員會 | `generated_at_utc` 格式、staging 子目錄名 |
| **L2 矩陣內選擇** | 在已審 design 宣告的候選空間內取值 | **單一 adversary** 非作者複核（`--risk low`） | 在「9 縱向 + 1 xsec」框架內增第 10 顆（若 design 已列候選） |
| **L3 驗收尺裁量** | 影響 **run 矩陣維度、選樣政策、hash 定義、排除/納入理由、資料來源** | **≥2 家** + `BASELINE-DESIGN-STAMP`（條文 1） | N=500、sha256 選欄、event 排除→後改納入、passed 重建公式 |

**快判一句**：若改動會讓 B5「改後仍綠」的**可證偽性**變弱或改變比較母體 → L3；否則 L0–L2。

#### 修文（替代條文 3）

```markdown
3. **裁量分級（非全量委員會）**：
   - **L0**：SPEC/TODO/§G 已凍結參數 → 不算裁量，禁假借「執行」吸收未寫明變更。  
   - **L1**：不改 oracle 語意/run 維度/排除政策之實施細節 → 設計檔記錄，無委員會。  
   - **L2**：在已審 design 候選空間內的取值 → 單一 adversary 複核（低風險派工）。  
   - **L3（技術決策）**：run 矩陣增刪、選樣/截斷政策、hash/canonical 規則、明知排除清單、真資料來源選擇 → 適用委員會先審後跑（條文 1）+ 雙戳記；**不得**以「照 SPEC 執行」涵蓋 L3。  
   爭議時 **就高不就低**（L3）。
```

---

### 條文 4：SCAR 登記

**立場**：**AGREE**

- 出生事故與逃脫點分析與 `docs/SCAR_LEDGER.md` 既有格式一致；  
- 應登記兩實害（xsec 截斷靜默無效、passed 假快照）+ 「編排端 Bash 無 hook」+ 「SPEC §G 指派單人無審查義務」；  
- 建議 SCAR 表增一列 **觸發詞**：`capture_*baseline` / `generate_baseline` / `handoffs/*baseline*` → 強制 baseline-design 流程。

#### 修文（替代條文 4）

```markdown
4. **SCAR 登記**：於 `docs/SCAR_LEDGER.md` 新增列「編排端自產驗收尺先跑後審」：  
   實害=xsec `max_features` 靜默無效、passed_set 假快照；  
   制度洞=gate 不攔編排端 Bash capture、§G 只約束消費端；  
   對策=條文 1–3 + baseline-design token + `BASELINE-DESIGN-STAMP`；  
   出處=handoffs/IC1EB-BASELINE-RECONCILE.md + RULE-PROPOSAL-ORCH-SELF-ARTIFACT.md。
```

---

## 任務 A — 成本效益：更便宜等效方案？

| 方案 | 成本 | 覆蓋逃脫點 | 評價 |
|---|---|---|---|
| **A. 僅條文 1–4 散文** | 最低 | 低（靠記性，重演 SCAR 模式） | 不足 |
| **B. 僅 §G 增欄 + template_check** | 低 | 中（只擋 SPEC 創建/派實作） | **不足**，漏 capture Bash |
| **C. baseline-design Bash hook + 設計檔雙戳記** | 中 | **高**（對齊本次根因） | **推薦主方案** |
| **D. 全量禁止編排端跑任何 `scripts/`** | 低程式 | 過度（小腳本亦癱瘓） | 拒絕 |
| **E. 事後三方複驗（本次 IC1EB 路徑）** | 高 token/時間 | 高但**事後** | 保留為兜底，不能替代 C |

**建議採用 C + B + 條文 4**；E 作為既有 Finding 閉合鐵律，不刪。

---

## 任務 B — DELTA-ACK（v2 PASS → v3/v4 增量）

**本人 R1 複驗**：`handoffs/IC1EB-BASELINE-REVERIFY-composer.md`，**VERDICT: PASS**（基於 v2 產物 `handoffs/ic1eb_baseline/`）。

**v3/v4 增量**（依 `IC1EB-BASELINE-RECONCILE.md` R2 節 + Codex R3/R4）：content-hash 指紋、q95 low-confidence 顆、inputs_integrity、逐列 schema hash（`summary_row_keysets_sha256`）、NaN canonical、±inf gate、manifest subsets（`selected_names`/family）。

| 增量 | 與 R1 PASS 關係 | 判定 |
|---|---|---|
| content-hash 指紋 (F6b) | 加強防偽，不改 G-1 五 hash 語意 | **不動搖 PASS** |
| inputs_integrity 逐檔 sha (F7b) | 加強 inputs 防篡改；R1 未驗此欄但不衝突 | **不動搖 PASS** |
| ±inf gate (F5b) | 加嚴；與 R1 F5 coerce 測試同向 | **不動搖 PASS** |
| NaN quiet 位元 (F8b) | 修 dtypes 假陽性；強化 R1 M2 結論 | **不動搖 PASS** |
| summary_keys_union / row_keysets (F4b/F4c) | 補 R1 未覆蓋的綱要盲區；**嚴化**非放寬 | **不動搖 PASS** |
| q95 low-confidence 事件顆 (F13b) | 新增 run，補 α 變更面；R1 曾 PASS event sufficient 顆 | **不動搖 PASS**（矩陣超集） |
| manifest subsets / F10b | 解決本人 R1 **PARTIAL**（family 直方未入 manifest） | **強化原 PASS** |
| run 數 12→14 | 超 R1 要求的 10 顆 | **不動搖 PASS** |

**DELTA-ACK: 維持 PASS**

**保留說明（非異議）**：

- 本人 R1 未獨立重跑 v4 全量 harness，delta 判定依 reconcile 文字 + Codex R4 PASS + 增量與 R1 反例方向一致性；  
- F14 labels_path MultiIndex 仍為 expected-raise（R2 已修正裁決文字），與本人 R1 F14 CLOSED 一致；  
- 若 B5 消費端改讀 v4 新增欄位為**硬性**斷言，屬下游契約，不推翻 baseline 設計審 PASS。

---

## 彙總表

| 條文 | 立場 | 一句摘要 |
|---|---|---|
| 1 先審後跑 | CHALLENGE | 方向對；須機械定義 + Bash hook，否則仍先跑後審 |
| 2 §G + artifact | CHALLENGE | §G 欄必要；現 artifact gate 不跑 template_check，須補 |
| 3 裁量=決策 | CHALLENGE | 須 L0–L3 分級，否則委員會癱瘓 |
| 4 SCAR | AGREE | 應登，建議加觸發詞列 |

---

ASSUMPTIONS_VERIFIED: gate.sh artifact 分支未呼叫 template_check（靜態閱讀 L369-L376）；gate_check Bash 不攔 python capture（L40-L51）；template_check §G 無審查戳記欄（L105-L112）；本人 R1 複驗報告 VERDICT PASS（handoffs/IC1EB-BASELINE-REVERIFY-composer.md）
TESTS_RUN: 靜態閱讀 scripts/gate_check.sh, scripts/gate.sh, scripts/template_check.sh, templates/SPEC_TEMPLATE.md；未跑 pytest
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅產出本檔）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: 使用者限 scope 僅本檔

VERDICT: ADOPT-WITH-CHANGES
