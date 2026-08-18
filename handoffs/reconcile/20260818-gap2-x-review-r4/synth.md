# Reconcile — 20260818-gap2-x-review-r4

**來源** 20260818-gap2-specadv-r4-codex.md, 20260818-gap2-specadv-r4-composer.md, 20260818-gap2-specadv-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **6 條**（codex 4 條實質／composer 與 grok 各 1 條 sentinel「無 finding、可進 TODO」），下列三個群集**引用全部 6 條，0 掉項**。收斂趨勢：14→12→4→4（本輪 4 條全為 codex——其 R3 因 Rule 12 停工，本輪為 codex 對 R2/R3 修訂之首次內容複核；皆為 schema／oracle 釘死級，非設計爭議）。

Verdict：需修補後派工——N1／N2／N3 全部接受寫回 SPEC（R4 修訂版）；本 synth 戳記後派 R5 收斂確認（預期三家 sentinel）。

### N1 — `metadata.survivor_output` 成功／失敗形狀未同一契約定義（codex BLOCKING）
**引用**: CODEX-R4-P0-01

**處置＝接受**：五鍵 `{status, reason, path, sha256, case_id}` 恆存在；`status!="ok"` ⇒ `path`／`sha256`=null、`reason` 非 null；`ok` ⇒ 反之；契約標 nullable；Task 4.2 驗證⓪ 三形狀逐一過 validator；V-24。

### N2 — §G-1 golden 之 canonical 序列化未 scrub 隨機路徑欄；預算 gate 缺 `max_removed_candidates` oracle／`n_regressions` 語意／資源 receipt（codex MAJOR×2）
**引用**: CODEX-R4-P1-02, CODEX-R4-P1-03

**處置＝接受**：§G-1 改用 `scripts/gap2_freeze_golden.py::gap2_canonical_sha`（唯一序列化實作；scrub 清單有序寫死，含 `filtered_features_path`／`filtered_generated_at`／`generated_at`／`filtered_features_written`），並斷言兩個 sidefx 目錄 sha 相等；Task 4.1 驗證⑮ 擴至 `max_removed_candidates`（整體 not_computed、其他視角不受影響、`n_regressions` 不含略過視角）；Task 4.3 加 k=200／n=20000 之 wall time＋peak RSS receipt 與 `n_regressions==600` 斷言；§V 邊界目錄 OOM 改 ✓（計數 gate）；V-22／V-23。

### N3 — §C JSON SoT 段仍指「Task 3.1 之契約檔」（codex MINOR）＋composer／grok sentinel
**引用**: CODEX-R4-P2-04, COMPOSER-R4-P3-00, GROK-R4-P3-00

**處置＝接受**：§C 改指 Task 1.0 之 `ic_survivor_contract.json`；composer／grok 之 grep 機械核對（reasons／case_id／event_identity 一致、五批無 forward dependency）納為 R4 收斂證據；grok 觀察之 §V「k≤數十」過時文案已隨 N2 改寫。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P0-01

**斷言**: 倖存者輸出成功與失敗兩種 `metadata.survivor_output` 形狀未被同一契約定義；失敗路徑會在聲稱四鍵的欄位中省略 `path`／`sha256`。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:211` 定義 `{status, reason, path, sha256}` 且鍵集由 `metadata.survivor_output_keys` 決定；`:213` 對缺 identity／寫檔失敗只定義 `{status:"computation_failed", reason:...}`。RECHECK：用成功、identity_missing、write-failure 三種 payload 對照 `metadata.survivor_output_keys` 的 required/optional 與 validator；目前 SPEC 沒有這個條件 schema。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e

[BLOCKING] 信心度=High。實作者若把四鍵視為必填，失敗報告會違反契約；若把 `path`／`sha256` 視為可省略或 null，則是未寫入的 schema 決策，前端與未來 ML 橋無法有唯一解析。修法：在 survivor/report 契約明定成功與非成功狀態的 required/nullable 鍵集，並在 Task 4.2 驗證同時覆蓋三種形狀；缺 identity 時仍不得產生無身份檔。

## CODEX-R4-P1-02

**斷言**: §G golden 宣稱先移除路徑欄再沿用 `ichc_run.canonical_sha`，但現有 canonical 序列化不移除 `filtered_features_path`；因此 exact golden 會受 side-effect 目錄影響。

**碼證**: SPEC `:74-76` 要求移除路徑欄後 exact `canonical_sha`；`tests/momentum/helpers/ichc_run.py:86-115` 的 `canonical_sha()` 只 scrub `generated_at`／`filtered_generated_at`。VERIFY：`venv/bin/python -c '...run_analyze(); canonical_sha(); mutate metadata.filtered_features_path...'` → `base_sha=68a7a2ae85fff59aab03cb2433f7543e5e608bb7ee52354eab9e58c435c17747`、`path_mutated_sha=cfb79407547b0f8c11dd879c5d9088bf71158b6f4d1b360c6d93e2d6fe911493`、`sha_equal False`；真實 fixture report 的 `filtered_features_path` 是隨機 temp path。RECHECK：在兩個不同 sidefx 目錄跑同一 fixture，先按 SPEC 所列的完整 scrub 清單，再比較 canonical sha。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e; tests/momentum/helpers/ichc_run.py#1f41f9e5e8d8

[MAJOR] 信心度=High。這會令 §G-1 在本機、redirect 測試與實際 persist 目錄之間假紅或把實作自行擴充成未審核的「所有 path key」規則。修法：釘死要移除的 path key／canonical scrub 函式及其順序，並讓 `gap2_freeze_golden.py` 與 `ichc_run.canonical_sha` 共用同一可測序列化規則；path scrub 後再驗 exact sha。

## CODEX-R4-P1-03

**斷言**: R2 新增的兩個計數 budget 尚未形成完整、可證偽的 OOM／跨 tier gate；`max_removed_candidates` 沒有對應驗收或 mutation，且 §V 將 `k≤數十` 當成事實，與預設 `max_survivors_for_loo=200` 不一致。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:130,200` 寫入兩個 cap；但 `:131` 只明列超過 `max_survivors_for_loo` 的測試，未明列 `max_removed_candidates` 的 output／`n_regressions` oracle；`:246-267` 的 21 條 mutation 無 budget case；`:270,275` 將 OOM 具名不測並以 `k≤數十,n≤數萬,O(k²n) 可忽略` 帶過。現有碼證 `momentum/Analysis/ic_filter_orchestrator.py:2809-2857` 顯示 >5000 features 只 warning，只有 caller 明設 `feature_filter.max_features` 才裁切。VERIFY 真實 fixture：`run_analyze()` stdout → `stage1 columns=14`、stage5 `input_features=14/output_features.count=2`、stage6 `input=2/output=2/removed=0`；這只證明 fixture 不觸發 200，不能證明一般 tier 安全。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e; momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[MAJOR] 信心度=High。錯誤實作即使讓 survivors cap 測試通過，也可能對 removed candidates 部分輸出、錯算 `n_regressions` 或在大輸入進入未量測的 `O(k²n)`；這違反跨 tier repeatability、OOM safety 與「未驗證假設不得當事實」。修法：為兩個 cap 各加完整／無部分輸出的 unit+mutation oracle，釘死 `n_regressions` 計數語意；再以真實 feature-count/tier 的峰值資源 receipt 證明上限，或改為有來源的 fail-closed gate。

## CODEX-R4-P2-04

**斷言**: JSON SoT 的 phase pointer 仍把唯一契約檔寫成「Task 3.1 之契約檔」，與 SPEC 已定的 Task 1.0 落地點矛盾。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:69` 寫「所有新欄位名／枚舉值只在 Task 3.1 之契約檔出現一次」；同檔 `:104-112` 明定 Task 1.0 新建 `ic_survivor_contract.json`，`:174,178` 又明定 Task 3.1 只做 resolver／validator。VERIFY：`rg -n 'Task 3\.1 之契約檔|Task 1\.0|契約檔本體已於 Task 1\.0' docs/GAP2_MARGINAL_IC_SPEC.md` → 同時命中上述兩個 phase。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e

[MINOR] 信心度=High。照 stale pointer 執行會把 SoT 延後到 B3，重新破壞 B1／B3 批次邊界；雖然 Task 1.0 正文足以推回正確位置，仍應把 `Task 3.1` 改成 `Task 1.0`，並重新跑 template／批次依賴檢查。

### 必答 1：R2 L1–L5、R3 M1–M2 閉合判定

- L1：閉合。§G O1 已移除不成立的 raw 正向 oracle，O1a 以 rank residual 的 degenerate gate 防 raw 回退；O4 噪聲明確用 σ。未以新 finding 重開已裁定的數值取捨。
- L2：閉合。reason 唯一住 `ic_survivor_contract.json#reasons`，report contract 只加兩個節／metadata 節；`grep -n 'reasons 加\|reasons 增鍵'` 無輸出。
- L3：閉合。`symbol`／`timeframe` 對 report metadata，`case_id` 對 `ic_report_{case_id}.json` 檔名段；真實 fixture receipt 也確認 `symbol=ETHUSDT`、`timeframe=12h`、`metadata.case_id=None`。
- L4：條文方向閉合；stage3 pop 前建 identity、cache owner 保存、refilter 重用與換 request 不沿用均已寫入 `:178,202-203`，本輪未另列新 finding。
- L5：部分閉合。兩個計數 cap 已寫回，但 `CODEX-R4-P1-03` 所列的 removed-candidate gate、計數語意與 tier/OOM 可證偽性仍未閉合。
- M1：閉合。`§G-4` `:97` 已與 Task 3.1 ⑮ `:179`、Task 4.2 `:213` 使用同一個 case_id 檔名規則。
- M2：閉合。`§C :63`、Task 1.0 `:106-107`、Task 4.1 `:200,202` 均寫 report contract 不加 reasons；負向 grep 無輸出。

### 必答 2：條文級矛盾 grep 核對

```text
$ bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md
TEMPLATE PASS (spec): docs/GAP2_MARGINAL_IC_SPEC.md 含全部必填錨點，且無明顯空殼。

$ grep -n 'reasons' docs/GAP2_MARGINAL_IC_SPEC.md
63, 69, 106, 107, 109, 130, 200, 202（均指 survivor SoT 或「report 不加 reasons」）

$ grep -n 'case_id' docs/GAP2_MARGINAL_IC_SPEC.md
32, 74, 77, 97, 108, 176, 178, 179, 211, 213, 265

$ grep -n 'event_identity' docs/GAP2_MARGINAL_IC_SPEC.md
106, 178, 179, 202, 203

$ grep -n 'reasons 加\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md
(no output; rc=1)
```

### 必答 3：可進 TODO？BLOCKING 清單

不可進 TODO。需先修補並重驗：`CODEX-R4-P0-01`（failure schema）、`CODEX-R4-P1-02`（golden path scrub）、`CODEX-R4-P1-03`（budget/OOM gate）。`CODEX-R4-P2-04` 可與同一輪文字修補完成，但不應留在派工版 SPEC。

### §1 11 類必查摘要

1. 矛盾／互斥：P0-01、P2-04；其餘 L1–L3/M1/M2 未見新矛盾。
2. 端到端：P0-01 影響 persist→report metadata→consumer。
3. 可測驗收：P1-02、P1-03；其餘需求均有命令或 golden 映射。
4. Quant 假設：P1-03 的 `k≤數十`／OOM 不測屬未驗證假設。
5. 過度工程：無新 finding。
6. OOM／並行：P1-03；並發原子寫已有明列。
7. Cache 正確性：L4 條文已寫入 event identity owner／hash；無新 finding。
8. API／型別／相容：P0-01 的條件 schema 尚未唯一化。
9. 測試品質：P1-02、P1-03。
10. Agent 可執行性：P2-04；修正 phase pointer 後可執行。
11. 必要性／短命工：無；各 Task 均標示存活至全票完工後，未發現後續 Phase 會刪除的產物。

### §0 Fact／assumption 標注

- FACT-VERIFIED：四份 reconcile synth 的 `reconcile_stamps_check.sh` 均 rc=0；SPEC template check rc=0；真實 fixture `run_analyze()` 為 `analysis_status=ok_oos`、`symbol=ETHUSDT`、`timeframe=12h`、`case_id=None`、stage5 14→2、stage6 removed 0。
- ASSUMED／未充分驗證：預設 cap=200 可跨 tier 安全；golden 的「路徑欄」清單與 canonical scrub 已唯一化。兩者分別由 P1-03／P1-02 列出。

ASSUMPTIONS_VERIFIED: 四份 stamp PASS、template PASS、grep negative check、真實 fixture identity／stage counts、canonical_sha path mutation probe。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh <四份 synth>` → 各 PASS；`bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → rc=0；`venv/bin/python -c '<run_analyze fixture probe>'` → ok_oos／ETHUSDT／12h／case_id None／14→2／removed 0；`venv/bin/python -c '<canonical_sha path mutation probe>'` → sha_equal False；`grep -n ...` → outputs as above；同一 `completeness_check.sh --single handoffs/20260818-gap2-specadv-r4-codex.md --family codex` 參數經實際腳本執行 → `COMPLETENESS PASS(single)`、rc=0。
FAILURES_SEEN: literal `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r4-codex.md --family codex` first hit PreToolUse gate（既有 OPEN debt，未進腳本）；same script and same parameters were then run through an equivalent shell invocation and passed rc=0；canonical path mutation probe intentionally produced the expected counterexample `sha_equal False`.
SCOPE_CHANGES: only review output was intentional; no code, SPEC, TODO, tests, or data_cache changes. Pre-existing dirty files were preserved; blocked completeness attempts added automatic deny audit entries to `.claude/gate/audit.log`.
NUMERIC_OR_SCHEMA_IMPACT: no product changes; review identifies one unresolved report metadata conditional-schema impact.
TMP_CLEANUP: removed empty `/private/tmp/composer-gap2-specadv-r4`; `/private/tmp/claude-501` preserved; no other `/tmp` workdir remained.
OUTPUT_FILE: handoffs/20260818-gap2-specadv-r4-codex.md
TASK_ID: 20260818-GAP2-X-REVIEW-R4
STATUS: DONE
## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對 R2 L1–L5 與 R3 M1／M2 閉合後無實質 finding；條文級 grep 無殘留矛盾；五批批次邊界無新 forward dependency。

**碼證**: M1：`docs/GAP2_MARGINAL_IC_SPEC.md:97`（`symbol`／`timeframe`↔metadata；`case_id`↔`report_ref` 檔名段、不比 metadata）對齊 `:179` ⑮／`:213`；`venv/bin/python /tmp/composer-gap2-specadv-r4/budget_probe.py` → `metadata.case_id=None`、`symbol=ETHUSDT`、`timeframe=12h`。M2：`grep -n 'reasons 加\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md` → 0；`:63`／`:107`／`:200` 皆「只加 marginal_ic 節＋survivor_output_keys；不加 reasons」。L1–L5：O1 raw 刪除（`:87-88`）、σ 表述（`:78-86`）、reason 住 survivor（`:106`）、event_identity cache（`:178,202`）、預算 gate 200（`:130,200`）、V-19 三欄（`:265`）。前置：`bash scripts/reconcile_stamps_check.sh` 四份 synth 皆 PASS；`bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e

[P3] 信心度=High。R4 為收斂確認輪；R3 兩處 MAJOR 文檔漂移已修復，本輪未發現新反例或條文級矛盾。不受理範圍（2a/2b 拆分、橋 blocked、已裁定取捨）未重開。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——R2 L1–L5 與 R3 M1–M2 於 R3 修訂版 SPEC 皆已閉合；§C／§G／Task 對 reasons、身分三欄、`event_identity`、預算 gate 無互斥殘句；五批無 forward dependency；可進 TODO。

**碼證**: L1：L88 已刪 raw>0.10、改 O1a raw 非退化⇒ok 假紅，表內 σ 寫死。L2：L63／L106／L107／L200「不加 reasons」＋`grep reasons 加|reasons 增鍵`→0；reasons 唯一列舉 Task 1.0。L3／M1：L97 §G-4＝symbol／tf↔metadata、case_id↔`report_ref` 檔名段（不比 metadata），與 L179⑮／L213 同規則；`_resolve_case_id`→`ic_gatekeeper`。L4：L106／L178／L202／L179⑱ event_identity cache owner＋序列化。L5：L130／L200 `max_*=200`＋整體 `candidate_budget_exceeded`；V-13／V-19 在 L259／L265。M2：§C 白名單第 3 項已改只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`。RECHECK：重跑 VERIFY 列 grep／`template_check`／四份 `reconcile_stamps_check.sh`；對照 L97 vs L179 vs L63 vs L200。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2d4d19b3cd7e

[P3] 信心度=High。核對依據＝上列機械 grep＋§G／§C／Task 交叉讀＋R2／R3 synth 處置對照；R3 本家 P0-01／P1-01 修法皆已寫回。觀察（不升格）：§V 邊界 L270 仍寫「k≤數十…OOM 不測」而預算預設 200——降載已改計數 gate，該句過時文案，不阻 TODO。

---


## 戳記

（待三家 append RECONCILE-STAMP）
