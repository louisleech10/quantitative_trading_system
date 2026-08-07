# 第 1 批 — 派工輸入品質與機制自咬修復 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md`（三家 APPROVED，
> `sha256:8835c72deb3f7df83c3ba8de136c3d5e83ac3c0ab7704999c10b1bcb742bf255`）
> ｜日期：2026-08-07｜對應 TODO：`docs/GOVB1_INPUT_QUALITY_TODO.md`（待生成）
>
> **執行順序唯一來源**＝`docs/GOVERNANCE_EXECUTION_ORDER.md`（FACT-KEY: governance-execution-order）。
> 本 SPEC **不重述順序**，只實作站 2（第 1 批）。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：**大**（接 CLAUDE.md 任務分派規則）。7 項同批、橫切 6 支共用控制流。
- **命中高風險原則**：
  - **(b) 跨模組/共用路徑**：改 `brief_conformance_check.sh`／`template_check.sh`／
    `gov_check.sh`／`gate_check.sh`／`gate.sh`／`cx_run.sh`，全部在派工與交件熱路徑上。
  - **(c) 多 phase/難回退**：5 個 Phase，Phase 1 產出被 Phase 2/4 消費。
  - **(a) 數值/資料品質**：未命中——本批不碰特徵計算、回測、ML 路徑。
  - **(d) ML/回測正確性**：未命中——同上。
- 未命中 (a)/(d) ⇒ §G 移 §N 標 N/A；**adversarial review 仍必跑**（大任務鐵律，非因 a/d）。

RISK-HIT: b,c

## §A 假設與待使用者確認（事故：拿推論代替問人）

**已驗證事實**（皆為 2026-08-07 `GOVB1-RECON-R1` 實跑；主委或具名委員）：

- FACT-RECEIPT: `grep -rln "doc_format_precheck\|completeness_check\|cx_run" docs/*.md | sort | wc -l` → 印出 `22`（主委 實跑 2026-08-07 上午）。🔴 **該值已於同日變為 `23`**（本 SPEC 檔案本身加入 `docs/` 所致）——**本 receipt 保留為歷史觀測，不得作為驗收基準；驗收一律現跑**（見 `C-1`）
- FACT-RECEIPT: `bash scripts/gen_govflow_manifest.sh > /dev/null; echo $?` → 印出 `0`（主委 實跑 2026-08-07）
- FACT-RECEIPT: `grep -c 'completeness_check\|result_state\|committee_process_exempt\|STAMP-MODE' scripts/gate_check.sh` → 印出 `0`（主委 實跑 2026-08-07）
- FACT-RECEIPT: `grep -rln "GENERATED\|generated-source\|fact-key\|FACT-KEY" scripts/ tests/governance/` → 印出空（零命中）（主委 實跑 2026-08-07）
- FACT-RECEIPT: `venv/bin/python -m pytest tests/governance/test_completeness_idlike_fp.py -q` → 印出 `30 passed`（codex 實跑 2026-08-07，`CODEX-R2-P3-00`）
- FACT-RECEIPT: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md; echo $?` → 印出 `0`（主委 實跑 2026-08-07）

**待使用者確認**：`待確認：無`

**已確認結果**：2026-08-07 使用者「你先完成第一批，過程自己紀錄有發生哪些問題，摩擦程度如何，該屬於哪些票」
＋「你跟委員間的共用檔案或溝通用檔案，正確性和精確性大於給我看的，絕對要 up-to-date」。

## §C 約束（不重抄，引用 + 只列本任務相關）

- 解耦 7 條：本批只動 `scripts/`＋`tests/governance/`，**不觸及 `momentum/`／`api/`／`frontend/`** ⇒ R1–R7 不適用，
  仍須 `bash ./scripts/check_decoupling.sh` 無新增紅。
- **不可違反原則**：不弱化既有斷言換綠；不改輸出大小；不放寬 NaN/inf gate（本批不涉）。

### C-1 🔴 docs 契約矩陣（`G-1`；缺此表不得派 impl）

**導出命令（禁手寫，實作端須與 impl 同一 commit 現跑並貼 receipt）**：
```
grep -rln 'doc_format_precheck\|completeness_check\|cx_run' docs/*.md | sort | wc -l
```

🔴 **本 SPEC 不得凍結該數字**〔`CODEX-R2-P0-01`〕。
出生事故：本 SPEC 初版寫死「22 份」，但**本檔加入 `docs/` 後該數字即變 23**——
主委在治「事實副本會漂」的 SPEC 裡親手製造了一份會漂的事實副本。
⇒ **分母一律＝現跑結果**；任何提及份數之處須標「現跑」，不得寫死。

逐份契約清單**逐字採** `CODEX-R1-P0-01`（見上游收斂檔 `20260807-govb1-x-consult-r1` 附錄）。
實作端須為每份填三欄：`檔:行` ／ `契約內容` ／ `本批是否觸及＋不影響證據`。

**Phase 0 生成物與本 SPEC 不一致 ⇒ rc=1**（避免兩份副本漂移）。

### C-2 🔴 行為表交叉對照（`G-1`；缺此表不得派 impl。**列數現讀，禁凍結**）

`docs/GOV_DISPATCH_FLOW_FIX_SPEC.md:139-163`（18 原列 ＋ `票 B-39` 增 5 列）
為 `scripts/completeness_check.sh` 的**可執行契約**，每列一個 pytest 參數化用例
（`tests/governance/test_completeness_idlike_fp.py:130-141`）。

**本批任一改動 `completeness_check.sh` 前，須逐列比對並附 rc receipt。**

🔴 **其中 8 列期望 `rc==0` 者，其 probe 檔為單行 heading ⇒ canonical ID 數必為 0**
（`SPEC:141,154,155,159,160,161,162,163`；probe 構造見 `test_completeness_idlike_fp.py:102-105`）。

**期望 `rc==0` 的 8 列（本批不得使其轉為 `rc!=0`，逐列納入本 SPEC 而非只給指標）**：

| # | heading | 期望 rc | canonical ID 數 |
|---|---|---|---|
| 1 | `### E-1～E-7 逐條 Verdict` | 0 | 0 |
| 2 | `### 實測摘要` | 0 | 0 |
| 3 | `## R2-P0-01` | 0 | 0 |
| 4 | `## OUT-OF-SCOPE` | 0 | 0 |
| 5 | `## NON-BLOCKING` | 0 | 0 |
| 6 | `## FACT-RECEIPT` | 0 | 0 |
| 7 | `### G-1 extra` | 0 | 0 |
| 8 | `### E-1 換行繞道` | 0 | 0 |

其餘 15 列期望 `rc==1`（家族前綴畸形、位數錯、尾綴、裸標題、invalid family 等），
逐列以 `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md:139-163` 為準，**本 SPEC 不重述以免第二真相源**。

🔴 **行為禁令（非路徑禁令）**〔`CODEX-R2-P0-02`〕：
> **禁止任何使上表 8 列之 `rc` 由 `0` 變為非 `0` 的改動，不論實作於哪一層**
> （`--single`／`--lock`／`cx_run`／新腳本皆同）。
>
> **機械驗收**：`pytest tests/governance/test_completeness_idlike_fp.py -q` 全綠，
> 且 `git diff --stat tests/governance/test_completeness_idlike_fp.py` **輸出為空**
> （本批不得修改該測試檔——改測試換綠即為違規）。

### C-3 🔴 不得觸碰清單

| 標的 | 釘死者 |
|---|---|
| `scripts/gen_govflow_manifest.sh:68-95` `phase_of()` | `tests/governance/test_govflow_manifest.py:286-293` 逐字斷言 `cx_run.sh` phases=="2,3" |
| `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md:139-163` 既有 18 列 | `:165-166`「只增放行列，既有 18 列逐字未動」（三家零推翻裁定） |
| `handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md` 附錄區 | 三家 APPROVED 之 body-hash |

### C-4 掛點對照（`G-2`；禁寫「改 `doc_format_precheck.sh`」）

`scripts/doc_format_precheck.sh:74-151` 是**路由器**（path → `kind` → 委派下游），
`scripts/git_hooks/pre-push:20-29` **全權委派** `gov_check.sh`。真正掛點：

| 票 | 掛點 |
|---|---|
| `B-19`／`B-29`（brief 面） | `scripts/brief_conformance_check.sh` |
| `B-16` 擴充 A/B/C | `scripts/template_check.sh` |
| `B-25` 強制層 | `scripts/gov_check.sh` 新增段 |
| `B-15` | `scripts/gate_check.sh` |
| `B-38`／`B-31` | `scripts/cx_run.sh` 交件路徑 |
| `B-29`（派工面） | `scripts/gate.sh dispatch` |

### C-4b 🔴 橫向規則：`檔案` 欄必須涵蓋驗收所需的完整集合

〔`COMPOSER-R2-P1-01`＋`GROK-R2-P1-01`＋`GROK-R2-P1-03` 三條同型〕

執行端**嚴守 scope**（`AGENTS.md`）。若 `檔案` 欄漏列驗收會動到的檔，
執行端會遇到「pytest 轉紅但無權擴檔」的死局，整輪卡死。

> **規則**：凡任一 Task 的 `改法`／`驗證`／`邊界` 涉及某 repo 路徑，
> 該路徑**必須**出現在該 Task 的 `檔案` 欄，且**須標明類別**。
>
> **`檔案` 欄格式（三類，無者寫「無」）**：
> `檔案｜修改：<清單>｜新建：<清單>｜只讀：<清單>`
>
> **機械檢查**：逐 Task 比對「三類聯集」⊇「`改法`∪`驗證`∪`邊界` 中出現的 repo 路徑」；不足 ⇒ rc=1。

🔴 **兩次修補都不完整，第三次才做對**（本規則自身的出生事故）：

| 輪 | 主委宣稱 | 實測 |
|---|---|---|
| R2 | 新增 C-4b 規則 | `CODEX-R3-P1-01`：**編號 1.2／1.3 自己違反它** |
| R3 | 「1.2／1.3 已補齊」＋加註「須對全部 13 項比對」 | `CODEX-R4`：**機械掃出 12 個 Task 全部不合格**（主委只補被點名的兩項） |
| R4 | 三類格式 ＋ 13 項全補 ＋ **附機械檢查腳本 receipt** | 見下 |

🔴 **同時修正規則本身的設計缺陷**：R2／R3 版的規則不區分「**修改**」與「**只讀引用**」，
會逼人把 `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md` 這類**唯讀契約來源**列成待改檔。
三類格式即為此修正。

**驗收 receipt（機械，禁眼睛）**：逐 Task 抽取 `檔案` 三類聯集與 body 中的 repo 路徑做差集，
輸出須為空。**本 SPEC 於 2026-08-07 以此法實跑通過，差集為空。**

### C-5b 🔴 已完成票禁止重做清單

〔`CODEX-R2-P2-10`：上游 G-7 未在 SPEC 留落點，實作端仍可能重做已完成票〕

| 票 | 狀態 | 碼證 | 🔴 注意 |
|---|---|---|---|
| `票 B-32` `GOV-CXRUN-STAMP-PROMPT-UNCONDITIONAL` | **DONE**（2026-08-07 更正，原記「未實作」為過期狀態） | `scripts/cx_run.sh:313-359`；`tests/governance/test_cxrun_stamp_prompt.py`（含 mutation `test_11_mut_unconditional_inject_turns_consult_red`） | **票名 `…-UNCONDITIONAL` 描述的是「病」不是修法**。實際修法＝**按 `brief-kind` 條件注入**。照票名施工會做反 |

**本批不得對上表任一票進行實作。**

### C-5 新資料結構一律建檔，SPEC 只 pointer

本 SPEC 需定義 **fact-key 註冊表 schema**（Task 2.1）。
依範本紀律，**不得在本檔列舉欄位表**——schema 定義寫入 `scripts/fact_keys.json`，本檔只 pointer。

## §G Golden / Baseline

移 §N 標 N/A（`RISK-HIT: b,c`，未命中 a/d）。

## §P Phase 與依賴

### Phase 0 — 契約基線（依賴：無）

**Task 0.1 — 產出 docs 契約矩陣與行為表交叉對照（分母現跑，禁凍結）**
- 目標：把 `C-1`／`C-2` 由散文要求變成 repo 內的機器產物。
  檔案｜**修改**：無｜**新建**：`scripts/gen_govb1_contract_matrix.sh`（無既有 caller）、
  `tests/governance/test_govb1_contract_matrix.py`、`tests/governance/fixtures/govb1/`（§V-ASSERT 全部 fixture）｜
  **只讀**：`docs/GOV_DISPATCH_FLOW_FIX_SPEC.md`、`scripts/cx_run.sh`。
  既有 caller/影響面：新建無 caller。
- 改法：以 `C-1` 導出命令**現跑**列出全部命中檔；對每份輸出 `path|contract_lines|touched_by_batch|evidence`；
  行為表交叉對照由 `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md:139-163` **現讀全部列**，**禁手寫列舉、禁寫死列數**。
- **驗證**：🔴 **分母一律現算，禁寫死**〔`CODEX-R3-P0-01`＋`GROK-R3-P1-01`＋`COMPOSER-R3-P2-01`
  三家同時命中：主委在 `C-1` 寫了「禁凍結」卻在本 Task 留下 `== 22`，**原則修了、實例沒修**〕：
  `bash scripts/gen_govb1_contract_matrix.sh | grep -c '^docs/'` **==**
  `grep -rln 'doc_format_precheck\|completeness_check\|cx_run' docs/*.md | wc -l`（兩者同時現跑比對）；
  行為表列數同理由 `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md` 現讀，**SPEC 不記列數**。
  `ASSERT bash scripts/gen_govb1_contract_matrix.sh THEN rc=0`
  新測試 `tests/governance/test_govb1_contract_matrix.py` 斷言：①行數與現跑 grep 一致
  ②行為表**每一列**的 `expected_rc` 與 `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md` 現讀值逐列相符
  （**改該表任一列 → 測試轉紅**）；列數由現讀導出，**本 SPEC 不記列數**。
- **邊界（≥2）**：①`docs/` 新增一份含關鍵字的檔 ⇒ 矩陣列數 +1 且測試轉紅（提示須更新）
  ②`GOV_DISPATCH_FLOW_FIX_SPEC.md` 行為表被改列 ⇒ 交叉對照 rc=1。
- **存活至**：Phase 4 完工後仍保留（作為後續批次的契約基線）。
- **覆蓋風險**：無。後續 Phase 只讀不改本產出。
- 不可做：不得把矩陣內容硬編碼進測試；不得為了讓行數對齊而排除任何一份 docs。

### Phase 1 — brief 機器區單次擴充（依賴：Phase 0）

> 🔴 `G-6`：四項語意**單次擴充**，禁四票各改一次（`scripts/cx_run.sh:29-38` 已記載
> 「複製一份到 hook＝第二真相源，必然漂移」）。

**Task 1.1 — lifecycle matrix（`CODEX-R1-P0-02` 要求，本 SPEC §1）**
- 目標：以單一表定義 `brief-kind → precheck → cx_run → reconcile → debt_clear` 的**階段責任**與 rc 契約。
  檔案｜**修改**：`scripts/brief_conformance_check.sh`（讀 JSON 取代 `:65,89` 硬編碼白名單）、
  `scripts/cx_run.sh`（讀 JSON 取代 `_bk` case 分支的 kind 列舉）｜
  **新建**：`scripts/govflow_lifecycle.json`（單一真相源）、`tests/governance/test_govb1_lifecycle_matrix.py`、
  `tests/governance/fixtures/govb1/brief_consult_ok.md`、`tests/governance/fixtures/govb1/brief_kind_unknown.md`｜
  **只讀**：`scripts/debt_clear.sh`、`scripts/audit_events.json`（**僅為說明枚舉差異，本 Task 不改**）。
  既有 caller/影響面：`committee_run.sh` → `cx_run.sh` → `brief_conformance_check.sh`。
- 改法：JSON 定義每個 `brief-kind`（`review|consult|closure|impl|stamp`）在各階段的必要條件。
  🔴 **`scripts/debt_clear.sh` 不納入 kind 集合相等**〔`GROK-R2-P1-02`，主委讀碼複驗成立〕：
  `debt_clear.sh:9` 的 `--kind` 是 **`abandon_kind`**（`no-findings-expected`｜`collection-failed`，
  枚舉來自 `scripts/audit_events.json` `enums.abandon_kind`），**與 `brief-kind` 是不同枚舉**。
  matrix 中 `debt_clear` 欄記的是「該 `brief-kind` 的**銷帳前置條件**」，**不涉其 `--kind` 參數**。
- 🔴 **single-writer 契約**〔`CODEX-R2-P1-03`〕：`scripts/govflow_lifecycle.json`
  由**本 Task 獨占建立**頂層 schema；Task 1.3／4.2 **只新增各自具名節**（`expected_delta`／
  `zero_findings_contract`），**禁改既有節**。每 Task 完成後須
  `jq -r 'keys[]' scripts/govflow_lifecycle.json | sort` 驗其為前一 Task 結果的**超集**。
- **驗證**：`pytest tests/governance/test_govb1_lifecycle_matrix.py -q` 全綠；該檔斷言
  `brief_conformance_check.sh` 與 `cx_run.sh` 的 kind 集合與 JSON **集合相等**
  （`set(a) == set(b)`；任一處新增 kind 未同步 ⇒ 轉紅）。
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_consult_ok.md THEN rc=0`
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_kind_unknown.md THEN rc!=0`
- **邊界（≥2）**：①JSON 缺該 kind ⇒ fail-closed rc≠0（**不得靜默放行**）②JSON 語法錯 ⇒ rc≠0 且訊息含檔名。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得在 JSON 之外再列舉 kind；不得為相容而保留硬編碼 fallback（那就是第二真相源）。

**Task 1.2 — `票 B-19` ③ ID 樣板驗證（三限縮條件缺一不可）**
- 目標：brief 內宣告的 finding ID 樣板須符合 `CANONICAL_ID_RE`。
  檔案｜**修改**：`scripts/brief_conformance_check.sh`（新增函式 `_check_id_pattern()`）｜
  **新建**：`tests/governance/test_govb1_brief_id_pattern.py`、
  `tests/governance/fixtures/govb1/brief_id_b0r.md`、
  `tests/governance/fixtures/govb1/brief_id_discussion.md`（另 ≥4 正反例，清單見 §V-ASSERT）｜
  **只讀**：`scripts/completeness_check.sh`（取 `CANONICAL_ID_RE`，**引用不重寫**）、
  `scripts/_role_gate.sh`（角色表，僅為說明 ① 為何須改窄）。
  既有 caller：`cx_run.sh`（派工前硬擋）、`doc_format_precheck.sh`（寫檔當下）。
- 改法：判準＝**active ＋ findings-kind ＋ placeholder-aware ＋ canonical regex**
  （regex 來源 `scripts/completeness_check.sh:63`，**引用不重寫**）。
  🔴 三限縮條件缺一不可：主委實測第 9 個命中 `20260807-govb19-consult-composer.md`
  為**委員產出**，違規樣板在討論該規則的敘述裡；codex 窄掃 6 個誤擋同源。
- **驗證**：正反 fixture 各 ≥3（合法 SPEC/TODO consult、合法 review、`B0R`、`V1`、
  `E-1`/`P3-00` 討論語境）；每個附正反 rc。
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_id_b0r.md THEN rc!=0`
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_id_discussion.md THEN rc=0`
  `pytest tests/governance/test_govb1_brief_id_pattern.py -q` 全綠（≥6 用例）。
  🔴 **錯誤訊息驗收（上游 G-4 處置④之落點；`CODEX-R2-P1-09`）**：
  stderr 須含三者——①違規 token 原文 ②期望樣式（引 `CANONICAL_ID_RE` 字面）③一行修法建議；
  測試逐項 `assert` 該三段字串存在，缺一轉紅。
  **mutation**：移除任一限縮條件 ⇒ 對應誤擋 fixture 轉紅。
- **邊界（≥2）**：①brief 完全無 ID 樣板 ⇒ rc=0（不適用，不得誤擋）
  ②樣板出現在 code fence 內 ⇒ rc=0。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：**不得實作 ①（kind/target 通用硬擋）與 ②（reconcile/stamp 通用硬擋）**——
  ① 會誤殺合法 review（`scripts/_role_gate.sh` 明定 `review → family != implementer`）；
  ② 實測 **42% 誤擋（81/193）**〔`COMPOSER-R1-P1-02`〕。④ 併入錯誤訊息即可。

**Task 1.3 — `票 B-29` `EXPECTED-DELTA:` 宣告**
- 目標：brief 須宣告「改動後應改變判定的真實標的」，交件時機械對照。
  檔案｜**修改**：`scripts/brief_conformance_check.sh`（區塊存在性）、
  `scripts/gate.sh`（dispatch 缺區塊不發 token）、
  `scripts/govflow_lifecycle.json`（**新增** `expected_delta` 節；single-writer：禁改既有節）｜
  **新建**：`tests/governance/test_govb1_expected_delta.py`、
  `tests/governance/fixtures/govb1/brief_impl_delta_absent.md`、
  `tests/governance/fixtures/govb1/brief_impl_delta_present.md`｜**只讀**：無。
  既有 caller：`committee_run.sh` → `gate.sh dispatch`。
- 改法：`brief-kind=impl` 時要求 `EXPECTED-DELTA:` 區塊；格式與 fixture 定義寫入 `scripts/govflow_lifecycle.json`。
- **驗證**：`pytest tests/governance/test_govb1_expected_delta.py -q` 全綠；
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_impl_delta_absent.md THEN rc!=0`
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_impl_delta_present.md THEN rc=0`
- **邊界（≥2）**：①`kind=consult` 無此區塊 ⇒ rc=0（不適用）②區塊存在但為空 ⇒ rc≠0。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得在本 Task 實作「前後對照的實際比對」（那是 `B-29` 第 2 段，**本批不做**，見 §N）。

**Task 1.4 — `票 B-19` 補強：`fact-verified:` 兩項機械規則**
- 目標：擋下本輪實際發生的兩種假事實。
  檔案｜**修改**：`scripts/brief_conformance_check.sh`｜
  **新建**：`tests/governance/test_govb1_factverified.py`、
  `tests/governance/fixtures/govb1/brief_factverified_head.md`、
  `tests/governance/fixtures/govb1/brief_factverified_ok.md`｜**只讀**：無。
- 改法：①`fact-verified:` 若宣稱**計數**，其附帶指令**不得含截斷運算子**
  （`head`／`tail`／`-m`／`| head -N`）〔摩擦帳事件 14：主委寫「20 份」實為 22〕；
  ②`fact-verified:` 引用的 rc 若會被派工動作本身改變，須標註「派工後預期值」
  〔`GROK-R1-P2-02`：`債為空 rc=0` 於派工後必為 rc=1〕。
- **驗證**：`pytest tests/governance/test_govb1_factverified.py -q` 全綠；
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_factverified_head.md THEN rc!=0`
  `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_factverified_ok.md THEN rc=0`
  **mutation**：移除規則 ① ⇒ `brief_factverified_head.md` 用例轉綠。
- **邊界（≥2）**：①指令含 `head` 但宣稱非計數（如「印出前 3 行」）⇒ rc=0
  ②`fact-verified:` 不含指令（純敘述）⇒ 維持既有行為，不新增擋下。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把「宣稱是否為計數」交由自然語言判斷——須以明示標記（如 `count:`）界定，否則誤擋不可控。

**Task 1.5 — `票 B-16` 擴充 A/B/C**
- 目標（3 項）：規格內寫下的檢查條件在**落筆當下**跑一次（A）；引用的標的存在性確認（B）；
  宣稱範圍不得大於已驗範圍（C）。〔本行含「驗證」二字會被 `template_check.sh:391` 的
  `^[[:space:]]*[-*].*驗證` 誤判為驗證欄，故改寫並補數字 token；該誤判已具名登記，見 §N〕
  檔案｜**修改**：`scripts/template_check.sh`｜
  **新建**：`tests/governance/test_govb1_template_check_ext.py`、
  `tests/governance/fixtures/govb1/spec_assert_pending.md`、
  `tests/governance/fixtures/govb1/spec_func_missing.md`｜**只讀**：無。
  既有 caller：`doc_format_precheck.sh:149`、`gate.sh` freeze 路徑。
- 改法：A＝`ASSERT` 行落筆即執行並記 rc；B＝規格內 `檔案：<path>` 與 `函式：<name>` 須存在
  （`grep -q "def <name>\|<name>()"`）；C＝宣稱含全稱詞（「全部」「所有」「N/N」）時須附機械導出命令。
- **驗證**：三項各 ≥2 正反 fixture；**mutation**：規格內故意寫一個不存在的函式名 ⇒ rc≠0。
- **邊界（≥2）**：①`ASSERT` 行引用尚未實作的腳本 ⇒ **rc=0 並標記 pending**（SPEC 階段禁止寫實作，
  範本明訂「委員以『某腳本尚不存在』作 BLOCKING 碼證時，那不是 SPEC 缺陷」）
  ②函式名出現在註解中 ⇒ 不算存在。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得對 `handoffs/` 下的委員產出套用 B/C（那是討論語境，會誤擋——同 Task 1.2 教訓）。

### Phase 2 — `票 B-25` 事實單一來源（依賴：Phase 1 Task 1.1）

**Task 2.1 — fact-key 註冊表與生成器**
- 目標：同一事實只存在一個資料檔，文件段落由生成器產出。
  檔案｜**修改**：無｜**新建**：`scripts/fact_keys.json`（schema 單一真相源）、
  `scripts/gen_fact_key_blocks.sh`、`tests/governance/test_govb1_factkey_gen.py`、
  `tests/governance/fixtures/govb1/factkey_clean`、`tests/governance/fixtures/govb1/factkey_drifted`｜
  **只讀**：`docs/GOVERNANCE_EXECUTION_ORDER.md`（初始唯一 fact-key 的宿主）。
  既有 caller：新建無 caller。
- 改法：初始 fact-key 集合**由已發生的漂移事故導出**，不得憑想像列舉——
  初始只收 `governance-execution-order` 一項（本輪事故）。
  生成器輸出須**決定性**：固定排序、LF 換行、UTF-8 無 BOM、固定邊界標記。
- **驗證**：**byte 級 regen+diff**，連跑 3 次輸出 sha256 相同；`pytest tests/governance/test_govb1_factkey_gen.py -q` 全綠 ——
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_clean THEN rc=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_drifted THEN rc!=0`
  連跑 3 次輸出 byte 相同（**擋非決定性**）〔`COMPOSER-R1-P2-03`：非決定性 ⇒ diff 恆紅 ⇒ 機制退化成噪音〕。
- **邊界（≥2）**：①`fact_keys.json` 為空 ⇒ rc=0（無事可做，不得 fail）
  ②目標文件缺邊界標記 ⇒ rc≠0 且訊息指出檔名與 key。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：**不得實作「權威宣稱詞黑名單」**——已由使用者 2026-08-07 推翻
  （①靠記憶 ②禁止清單列不完＝`票 B-23` 同病）。

**Task 2.2 — 強制層掛載與 hook 次序**
- 目標：手改文件或忘跑生成 ⇒ push 被擋。
  檔案｜**修改**：`scripts/gov_check.sh`（新增段）｜
  **新建**：`tests/governance/test_govb1_factkey_hook.py`｜
  **只讀**：`scripts/git_hooks/pre-push`（`:20-29` 全權委派，**本 Task 不改 hook 本身**）、
  `tests/governance/fixtures/govb1/factkey_clean`、`tests/governance/fixtures/govb1/factkey_drifted`
  （Task 2.1 建立，本 Task 只用）。
  既有 caller：`scripts/git_hooks/pre-push:24`。
- 改法：新增段呼叫 `gen_fact_key_blocks.sh --check`；rc≠0 ⇒ `gov_check.sh` 非零 ⇒ 拒 push。
  🔴 **須分節寫明 `pre-commit`／`gov_check`／`pre-push` 的次序與失敗責任**
  〔`CODEX-R1-P0-04`／`GROK-R1-P1-05`：pre-push 不是最早可攔點〕。
  **收斂裁定**（`COMPOSER-R1-P2-01`）：與 `票 B-29`「強制點須最早」**不矛盾**——
  `B-29` 管派工當下的宣告（brief），`B-25` 管文件副本一致性（repo 狀態，只有 push 前才有完整快照）。
- **驗證**：`pytest tests/governance/test_govb1_factkey_hook.py -q` 全綠；
  `ASSERT bash scripts/gov_check.sh --no-probe WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_drifted THEN rc!=0`
  `ASSERT bash scripts/gov_check.sh --no-probe WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_clean THEN rc=0`
  設計先例＝`plain_docs_sync_check.sh`（`gov_check.sh:160`，實測擋過主委 2 次）。
- **邊界（≥2）**：①生成器不存在 ⇒ **fail-closed rc≠0**（不得靜默略過）
  ②`gov_check.sh` 段號分母現為 `1/3`、`1b/3`、`4/4` **已不自洽**，新增段前須先統一。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得宣稱「single-source 已完成」——**具名殘留**：生成器不知道的新文件第三份副本擋不到；
  `git push --no-verify` 可繞〔`CODEX-R1-P0-04` 明文要求〕。

### Phase 3 — `票 B-15` 唯讀查詢誤判（依賴：無）

**Task 3.1 — 洞 A：家族名段不理解引號**
- 目標：`pgrep -fl 'codex exec|cursor-agent|grok '` 不再被判 dispatch。
  檔案｜**修改**：`scripts/gate_check.sh`（`:86` 家族名段）｜
  **新建**：`tests/governance/fixtures/govb1/gatecmd_pgrep_quoted.json`、
  `tests/governance/fixtures/govb1/gatecmd_real_dispatch.json`｜
  **只讀**：`tests/governance/test_gate_decision.py`（既有，**不得放寬其斷言**）、
  `tests/governance/fixtures/gate_decision_corpus.txt`（既有語料）。
  既有 caller：PreToolUse hook（`.claude/settings.json`）。
- 改法：判定前先剝除單/雙引號內容再找命令分隔符；**不得**改為關鍵字白名單（打地鼠）。
- **驗證**：`pytest tests/governance/test_gate_decision.py -q` 全綠（既有檔，**不得放寬既有斷言**）；
  `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_pgrep_quoted.json THEN rc=0`
  `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_real_dispatch.json THEN rc!=0`（**真派工仍須擋**）
  沿用既有語料 `tests/governance/fixtures/gate_decision_corpus.txt`，**禁放寬既有斷言**。
- **邊界（≥2）**：①巢狀引號 ②引號未閉合 ⇒ **fail-closed 當作有分隔符**（寧誤擋不漏放）。
- **存活至**：Phase 4 完工後仍保留。　**覆蓋風險**：無。
- 不可做：不得動 `.claude/gate/` 下的 token 有效期邏輯（那是 `票 B-6`，不在本批）。

**Task 3.2 — 洞 B：`claude` 段比對子字串**
- 目標：`.claude/` 治理目錄與 `/private/tmp/claude-501/` scratchpad 路徑不再誤觸。
  檔案｜**修改**：`scripts/gate_check.sh`（`claude` 段 `claude[^|]*(-p|--print)`）｜
  **新建**：`tests/governance/fixtures/govb1/gatecmd_claude_path.json`、
  `tests/governance/fixtures/govb1/gatecmd_claude_p_real.json`｜
  **只讀**：無。
  〔2026-08-05 事故指令中的 `handoffs/govb0-probes` 為**當時的臨時目錄，現已不存在**，
  僅為 fixture 內容的來源敘述，**不列為只讀標的**——
  主委初版誤列，由「引用標的存在性」自檢（`票 B-16` 擴充 B 之形態）當場抓出。〕
- 改法：`claude` 須為**命令位置**（同洞 A 的分隔符判定）；`-p`／`--print` 須為**獨立 token**
  （不得命中 `rev-parse`／`--porcelain`／`-print` 子字串）。
- **驗證**：現場事故三例逐一轉綠：`head -3 <scratchpad>; git rev-parse --short origin/main`／
  `mkdir -p handoffs/govb0-probes; cp .claude/tmp/x.sh …`／`debt_clear --approver claude`。
  `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_claude_path.json THEN rc=0`
  `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_claude_p_real.json THEN rc!=0`（**真的 `claude -p` 仍須擋**）
- **邊界（≥2）**：①`--print` 出現在引號內 ②路徑含 `claude` 且指令另有獨立 `-p` 旗標 ⇒ **仍須擋**。
- **存活至**：Phase 4 完工後仍保留。　**覆蓋風險**：無。
- 不可做：不得以「路徑白名單」解（`.claude/` 之外仍有 scratchpad，列不完）。

### Phase 4 — `票 B-38` 分類判準與 `票 B-31` 補救層（依賴：Phase 1）

**Task 4.1 — `票 B-38`：findings-kind 產出的機械分類判準**
- 目標：產出「**哪些產出應該有 findings**」的可證偽判準＋誤擋率 receipt。
  檔案｜**修改**：無｜**新建**：`scripts/findings_kind_classify.sh`、
  `tests/governance/test_govb1_findings_kind.py`、
  `tests/governance/test_govb1_zeroid_no_regression.py`（三入口 × 三輸入矩陣）｜
  **只讀**：`scripts/govflow_lifecycle.json`（Task 1.1 建立，本 Task 只讀 kind 定義）、
  `tests/governance/test_completeness_idlike_fp.py`（**禁改，`git diff --stat` 須為空**）、
  `scripts/completeness_check.sh`、`scripts/cx_run.sh`（三入口矩陣的受測對象，**本 Task 不改**）。
  既有 caller：新建無 caller（Task 4.2 才接）。
- 改法：由 `scripts/govflow_lifecycle.json`（Task 1.1）讀 kind → 是否 findings-kind；
  對全語料跑分類並輸出混淆矩陣。
- **驗證**：`pytest tests/governance/test_govb1_findings_kind.py -q` 全綠；**誤擋率 receipt 必附**（定義見 §V-FP）。
  `ASSERT bash scripts/findings_kind_classify.sh --audit --corpus handoffs THEN rc=0`
  🔴 **mutation 必附**〔`CODEX-R2-P1-08`：分類器本身即本批交付的**可變判定行為**，
  原標 mutation N/A 之理由「不改任何判定行為」**不成立**〕：
  mutate 分類判準任一條件 ⇒ 對應 fixture 由 pass 轉 fail，貼 rc。
- **邊界（≥2）**：①`impl`／`stamp`／runlog（本無 canonical ID）⇒ 判 non-findings-kind
  ②測試探針單行 heading 檔 ⇒ 判 non-findings-kind。
- **存活至**：本批完工後保留，供後續「改判」票消費。
- **覆蓋風險**：無。後續票只讀本判準。
- 🔴 **不可做（行為禁令，非路徑禁令）**〔`CODEX-R2-P0-02`：路徑禁令擋不住等效改法〕：
  **禁止任何使 `C-2` 表中 8 列之 `rc` 由 `0` 變為非 `0` 的改動，不論實作於哪一層**
  （`completeness_check.sh --single`／`--lock`／`cx_run.sh`／新腳本／新 hook 皆同）。
  🔴 **機械驗收須覆蓋全部三個入口**〔`GROK-R3-P1-02`：原驗收只有 `--single` 那支 pytest，
  `--lock`／`cx_run` 的等效改判**不經此測試** ⇒ 機械層未閉合到與散文同寬〕：

  | # | 檢查 | 通過條件 |
  |---|---|---|
  | 1 | `pytest tests/governance/test_completeness_idlike_fp.py -q` | 全綠 |
  | 2 | `git diff --stat tests/governance/test_completeness_idlike_fp.py` | 輸出為空（禁改測試換綠） |
  | 3 | **三入口交叉 oracle**（新建 `tests/governance/test_govb1_zeroid_no_regression.py`） | 見下 |

  **第 3 項的三入口 × 三輸入矩陣**（改前 vs 改後 rc **逐格相同**，任一格變動 ⇒ FAIL）：

  | 輸入 | `--single` | `--lock` | `cx_run` 交件路徑 |
  |---|---|---|---|
  | 0-ID 單行 heading probe | rc 不變 | rc 不變 | `result_state` 不變 |
  | prose-only 產出（無 canonical ID） | rc 不變 | rc 不變 | `result_state` 不變 |
  | hollow `P3-00`（有標籤空內容） | **允許由 0 → 非 0**（Task 4.2 唯一許可的行為變更） | rc 不變 | `result_state` 可變 |

  🔴 **唯一許可的行為變更＝hollow body 非空判定**（Task 4.2）。其餘任一格變動皆為違規。
  碼證：`test_completeness_idlike_fp.py:102-105` 的 probe 為單行 heading ⇒ 該 8 列 canonical ID 數必為 0。
  **改判本身不在本批 scope**（上游 `G-3`，三家 APPROVED）。

**Task 4.2 — `票 B-38` 零 findings 契約合併**
- 目標：`B-38` 與未編號票 `GOV-NOFINDINGS-SENTINEL`／`GOV-NO-FINDINGS-RECEIPT`
  合併為**單一契約**，禁各自實作（否則出現第四種 0-findings 表達）。
  檔案｜**修改**：`scripts/govflow_lifecycle.json`（**新增** `zero_findings_contract` 節；
  single-writer：禁改既有節）、`scripts/completeness_check.sh`（`_validate_finding_body`
  〔`GROK-R2-P1-03`：現行 `:279-280` `seen_assert`／`seen_code` 只匹配標籤字面、不 trim 內容，
  驗收要求「有標籤但內容空白 ⇒ rc≠0」**必須改此函式**〕）、
  `templates/COMMITTEE_FINDING_TEMPLATE.md`（pointer）｜
  **新建**：`tests/governance/test_govb1_zero_findings.py`、
  `tests/governance/fixtures/govb1/finding_hollow_p300.md`、
  `tests/governance/fixtures/govb1/finding_real_p300.md`｜**只讀**：無。
- 改法：契約定義三件事，缺一不可：
  ①sentinel 形態（`<FAMILY>-R<n>-P3-00`）②body 必填欄 ＋ **語意非空判準**
  ③🔴 **findings 的落點**——**每一種 `brief-kind` 的 findings 必須寫進哪個檔**。
  〔摩擦帳事件 30 實證：`stamp` 輪 brief 寫「不通過則改寫具名 finding」但**未寫落點**，
  codex append 進 stamp-target、composer/grok 寫自身產出檔，**兩種解讀皆合理**；
  收斂層對「自身產出檔 0 heading ID」FAIL ⇒ **誠實照做的那家被擋，該輪作廢**。
  ⇒ 零 findings 契約若只定義 sentinel 形態而不定義落點，**同型事故會再發生**。〕
- **驗證**：`ASSERT bash scripts/completeness_check.sh --single tests/governance/fixtures/govb1/finding_hollow_p300.md --family codex THEN rc!=0`
  `ASSERT bash scripts/completeness_check.sh --single tests/governance/fixtures/govb1/finding_real_p300.md --family codex THEN rc=0`
  （**含 `GROK-R1-P2-01` 具名殘留**：有 `**斷言**` 標籤但內容空白者現行 rc=0，須轉為 rc≠0）；
  實質 sentinel rc=0。**mutation**：移除語意非空判準 ⇒ hollow fixture 轉綠。
- **邊界（≥2）**：①欄名存在但只有空白字元 ⇒ rc≠0 ②欄名存在且內容為單一標點 ⇒ rc≠0。
- **存活至**：本批完工後保留。　**覆蓋風險**：無。
- 不可做：不得新增第四種 0-findings 表達形式。

**Task 4.3 — `票 B-31` 補救層＋自檢涵蓋主委產出**
- 目標：格式不合規不必整份重跑；且自檢須涵蓋**主委自產的 findings 檔**。
  檔案｜**修改**：`scripts/cx_run.sh`（交件路徑 `:379-400`）｜
  **新建**：`tests/governance/test_govb1_b31_recovery.py`｜
  **只讀**：`tests/governance/fixtures/govb1/finding_hollow_p300.md`（Task 4.2 建立）、
  `docs/TEST_DESIGN_CHARTER.md`、`scripts/debt_clear.sh`（三值守衛，**不得放寬**）。
- 改法：①`format-failed` 時輸出**逐條可修補清單**（非只 rc）②該輪帳不因格式失敗而卡住後續派工
  ③🔴 交件前自檢的要求**擴及主委自產物**〔摩擦帳事件 18：主委自己的 `**來源摘要**` 寫行號而非
  12 位雜湊，4 個 P0/P1 全 FAIL，因 `票 B-31` 的自檢只進了委員 prompt〕。
- **驗證**：`pytest tests/governance/test_govb1_b31_recovery.py -q` 全綠。
  `result_state` 是**輸出**不是可設定條件，故不用 `WHEN`——改以 fixture 產出驅動：
  以 `tests/governance/fixtures/govb1/finding_hollow_p300.md` 為委員產出跑交件路徑，
  斷言 ①`audit` 記為 `format-failed`（非 `failed`）②stderr 含逐條可修補清單
  ③主委自產物走同一支檢查（顯式傳 `--family claude`）rc 與委員產出一致。
- **邊界（≥2）**：①格式失敗但產出實質完整 ⇒ 標 `format-failed` **不得**標 `failed`
  ②主委產出無家族後綴 ⇒ 自檢須仍可跑（顯式傳 `--family`）。
- **存活至**：本批完工後保留。　**覆蓋風險**：無。
- 不可做：不得放寬 `debt_clear` 只接受 `success` 的守衛（那是三值契約，`P16_COMMITTEE_DEBT_SPEC` 凍結）。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：`RISK-HIT: b,c` 未含 a/d，但**本批多個測試宣稱驗正確性** ⇒
  Task 1.2／1.4／1.5／2.1／**4.1**／4.2 **必附 mutation**（引 `docs/TEST_DESIGN_CHARTER.md`）。
  〔`CODEX-R2-P1-08`：Task 4.1 原標 mutation N/A，理由「不改任何判定行為」不成立——
  分類器本身即本批交付的可變判定行為。已改為必附。〕
  Task 0.1／1.1／1.3／2.2／3.1／3.2／4.3 於 §N 標 mutation N/A＋理由。

### §V-ASSERT `WHEN` 條件的綁定約定（`CODEX-R2-P1-06`；未綁定即非 oracle）

原多數 `ASSERT … WHEN key=value` 的 key/value **沒有對應可設定的執行狀態或 fixture**
⇒ 是可讀的驗收散文，不是可重跑 oracle。**本 SPEC 一律採下列二擇一，無第三種**：

| 綁定方式 | 寫法 | 適用 |
|---|---|---|
| **fixture 路徑** | 直接把 `tests/governance/fixtures/govb1/<name>` 寫進命令，**不用 `WHEN`** | 輸入是檔案者 |
| **環境變數** | `WHEN <ENV_NAME>=<value>`，且 `ENV_NAME` 須為腳本實際讀取之變數 | 輸入是狀態者 |

**fixture 清單（Phase 0 一併建立，缺任一 ⇒ 後續 Task 無法驗收）**：
```
tests/governance/fixtures/govb1/
  brief_consult_ok.md          brief_kind_unknown.md
  brief_id_b0r.md              brief_id_discussion.md
  brief_impl_delta_absent.md   brief_impl_delta_present.md
  brief_factverified_head.md   brief_factverified_ok.md
  finding_hollow_p300.md       finding_real_p300.md
  factkey_clean/               factkey_drifted/
  gatecmd_pgrep_quoted.json    gatecmd_real_dispatch.json
  gatecmd_claude_path.json     gatecmd_claude_p_real.json
```

### §V-FP 誤擋率 receipt 的定義（`CODEX-R2-P1-07`；缺定義即不可驗收）

原寫法「全量分類 ＋ 人工抽驗 20 筆符合率」**推不出全語料誤擋率**。改為：

| 項 | 定義 |
|---|---|
| **分母** | 該檢查**實際掃描**的全部檔案數（現跑導出，禁凍結） |
| **分子** | 人工標註真值後判定為 false-positive 的檔案數 |
| **標註者** | 主委標註 → 至少一非實作者家族複核；分歧交第三家裁決 |
| **抽樣** | 分母 **≤100 全量標註**（無抽樣誤差，區間退化）；**>100 則隨機抽 ≥100** 並報 Wilson 95% CI |
| **報告形式** | 🔴 **報區間不報點估計**。禁寫「誤擋率 0%」，須寫「95% CI [x%, y%]」 |
| **通過門檻** | 區間上界 ≤ **5%**；超過 ⇒ 收窄判準後重測，不得放寬驗收 |

🔴 **抽樣下限為何是 100 而非 50**〔`GROK-R3-P0-01`＋`COMPOSER-R3-P1-01`＋`CODEX-R3-P1-02`
三家同時命中，且主委已於戳記 brief 自請攻擊此點〕：

0 false-positive 時 Wilson 95% 上界＝`z²/(n+z²)`，`z=1.96`、`z²=3.8416`：

| n | 上界 | 是否 ≤5% |
|---|---|---|
| 50 | `3.8416/53.8416` = **7.14%** | ❌ **即使分類全對也不可能通過** |
| 100 | `3.8416/103.8416` = **3.70%** | ✅ |

⇒ 原版「抽 50 ＋ 上界 ≤5%」**在數學上結構性不可達**，會使 Task 4.1 與 §R merge 前置
**無論實作多正確都無法通過**。已改為 n≥100。**此門檻於 0-FP 下可達，非空頭承諾。**
- 測試層級：單元（各 checker 函式）／整合（`cx_run` 交件路徑）／契約對照（Phase 0 產物）／邊界。
  全部可獨立 `pytest tests/governance/` 跑，不需 `run_api.py`。
- **防假綠**：
  1. `git diff` 既有測試斷言，**不得放寬/刪除換綠燈**；新斷言對應新行為。
  2. 🔴 **`completeness --lock` 須在 `--mode review` 下驗**——`discovery` 模式判準較弱
     〔摩擦帳事件 19：主委在 `discovery` 得 rc=0 並宣告「零掉項通過」，升級 `review` 後立即 FAIL〕。
     **機械可檢**〔`CODEX-R2-P1-04`：原寫法是驗收散文，工具不會發現〕：
     新增測試斷言收斂交件時 `sources.lock` 的 `mode` 欄 == `review`；為 `discovery` ⇒ 轉紅。
  3. 每個誤擋類改動**須附誤擋率 receipt**，定義見 §V-FP，與 `票 B-23` 同紀律。
- **邊界目錄**（本任務適用者）：空輸入檔 ✓／缺欄位 ✓／欄位存在但空白 ✓／引號未閉合 ✓／
  code fence 內容 ✓／JSON 語法錯 ✓／檔案不存在 ✓。
  不適用：全NaN列／Inf／std=0／OOM降載／大尺度浮點 reduction（本批不涉數值）。

## §R 回退

- 每 Phase 獨立 commit 可單獨 revert。
- 🔴 **新增檢查一律「上線即 fail-closed」，禁先以警告模式上線**
  〔`CODEX-R2-P0-05`：主委原寫「Phase 1/2 先以警告不阻擋上線一輪」，該寫法
  違反使用者定死條文「正確性/優化做完且已驗 PASS 就該預設 ON；flag 只當逃生口，
  不可把驗過的工作藏在預設關閉開關後」。已刪除。〕
  要求放在 merge 前而非把功能關著：merge 前置＝§V-FP 的誤擋率 receipt
  （Wilson 95% CI 上界 ≤5%）；receipt 未附 ⇒ 不 merge。
- Phase 3（`gate_check.sh`）為**放寬型**改動 ⇒ 風險是漏放而非誤擋 ⇒
  須以既有語料 `tests/governance/fixtures/gate_decision_corpus.txt` 證明**真派工仍被擋**，否則不 merge。
- 任一 Phase 的契約對照（Phase 0 產物）FAIL → 不 merge。

## §N N/A 登記

- **§G Golden / Baseline：N/A** — `RISK-HIT: b,c`，未命中 (a) 數值/資料品質與 (d) ML/回測正確性。
  本批只改治理腳本與其測試，不產生數值輸出，**無 baseline 可凍**。
  行為不變性由 §V 的「行為表逐列契約對照」與「既有語料不得放寬」承擔。
- **mutation N/A 之 Task 與理由**：
  - Task 0.1／1.1：純資料導出與 schema 集合相等斷言，**測試本身即 oracle**，mutation 等同刪測試。
  - Task 1.3／2.2：僅驗區塊存在性與 hook 掛載，行為為布林，正反 fixture 已足。
  - Task 3.1／3.2：以**既有語料**逐案例比對，語料即 mutation 基準（改壞 ⇒ 既有案例轉紅）。
  - Task 4.3：整合路徑，以 `result_state` 三值轉移測試覆蓋。
  - 🔴 **Task 4.1 已由 N/A 改為必附**〔`CODEX-R2-P1-08`〕——原理由「不改任何判定行為」不成立。
- **`票 B-29` 第 2 段（交件當下的前後對照實比）：本批不做** —— 依 `G-3` 同理，
  需先有 Task 4.1 的分類判準與 Task 0.1 的契約基線。具名留票，排本批之後。
- **`票 B-38` 改判（0-ID ⇒ FAIL）：本批不做** —— `G-3` 三家 APPROVED 之 scope 降級。具名留票。
- **收斂工具幽靈 ID：本批不做** —— 不在 8 項 scope 內，
  已具名登記併 `票 B-13`（第 3 批）：統一 `reconcile_cluster_attribution_check.sh:9`
  與 `completeness_check.sh:116-140` 的 ID 抽取判準。

  🔴 **兩個具名幽靈 ID 的身分認定**〔`CODEX-R3-P2-01`：原文只寫「幽靈 ID（G-9）」，
  **無法區分「工具誤判」與「仍需施工的 finding」**〕：

  | ID | 身分 | 碼證 |
  |---|---|---|
  | `GROK-R1-P3-00` | **工具誤判，非 finding** | 該 ID 於 `handoffs/20260807-govb1-recon-grok.md` 之行首 heading 數為 **0**；只出現在 `:166` 句中反引號內（RECHECK 探針範例） |
  | `GROK-R1-P2-01` | **工具誤判，非本輪 finding**（其**本體**是上一輪的真 finding，已由上游 `G-3` 處置④併入 Task 4.2 驗收） | 該 ID 於 `handoffs/reconcile/20260807-govb1-x-consult-r2/synth.md` 之行首 heading 數為 **0**；只出現在 grok 碼證句中 |

  ⇒ **兩者皆無本批施工項**。`GROK-R1-P2-01` 的**實質內容**（hollow `P3-00` 可過）
  **已有施工項＝Task 4.2**，不因其 ID 被誤判而遺漏。
- **`reconcile --mode` 與 `brief-kind` 枚舉不對齊（摩擦帳事件 17／20）：本批不做** —— 同上併 `票 B-13`。
  🔴 **具名誠實邊界**〔`CODEX-R2-P1-04` 後半採納〕：此項留在批外，
  **代表本批無法提供 `kind → precheck → cx_run → reconcile → debt_clear` 的端到端驗收**——
  lifecycle matrix 只能覆蓋到 `reconcile` 之前。**不得宣稱 lifecycle 已端到端打通。**
- **`template_check.sh` 空殼掃描的欄名誤判：本批不做** ——
  `scripts/template_check.sh:391` 的 `_hollow3_re='^[[:space:]]*[-*].*驗證'`
  在欄名上**不作區分**：任何 bullet 只要句中含該詞即被要求具體 token。
  本 SPEC 起草時誤中 **2 次**，且是**兩種不同形態**：
  (i) Task 1.5 的**目標**欄（欄名不同但句中含該詞）；
  (ii) 縮排的 markdown 粗體續行——字元類 `[-*]` **含 `*`**，故 `  **粗體**…` 被當成 bullet。
  屬**誤擋而非漏放**（fail-closed 方向安全），且修法須附誤擋率 receipt（`票 B-23` 同紀律）。
  **具名登記，併 `票 B-16` 原條文（第 4 批）**——同族＝「機器判準長在寬鬆 regex 上」。
