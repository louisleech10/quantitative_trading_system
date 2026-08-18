# Reconcile — 20260818-gap2-x-review-r5

**來源** 20260818-gap2-specadv-r5-codex.md, 20260818-gap2-specadv-r5-composer.md, 20260818-gap2-specadv-r5-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **4 條**（codex 2 條實質／composer 與 grok 各 1 條 sentinel「可進 TODO」），下列兩個群集**引用全部 4 條，0 掉項**。收斂趨勢：14→12→4→4→2；本輪 2 條皆為 R4 N1／N2 修訂之**字面殘留**（失敗形狀 literal 仍兩鍵、§V「已知不測」句未同步），非新設計爭議；composer／grok 連兩輪 sentinel。

Verdict：需修補後派工——P1／P2 已寫回 SPEC（R5 修訂版）；本 synth 戳記後派 R6 收斂確認（codex 複核兩處字面）。

### P1 — Task 4.2 失敗路徑 literal 仍兩鍵，與五鍵恆存在契約矛盾（codex BLOCKING）
**引用**: CODEX-R5-P0-01

**處置＝接受**：Task 4.2 改法之 `identity_missing`／`write_failed` 兩個 literal 改為完整五鍵（`path`／`sha256`=null、`case_id` 明確值），與 4.2 驗證⓪ exact-key gate 一致。

### P2 — §V 測試章程「已知不測：OOM／並發」與 §V 邊界目錄／Task 4.3 receipt 自相矛盾（codex MAJOR）＋composer／grok sentinel
**引用**: CODEX-R5-P1-02, COMPOSER-R5-P3-00, GROK-R5-P3-00

**處置＝接受**：§V 章程改為「已知不測：無」——OOM 由計數 gate＋Task 4.3 峰值資源 receipt 覆蓋（pass＝`n_regressions==600`＋receipt 存在；receipt 只記錄不設閾值，資源上限不由實作端臆造）；並發由 Task 4.2 原子寫＋新增驗證⑦（兩執行緒同 case_id ⇒ 完整 JSON）覆蓋。composer／grok 之獨立 grep 複核納為收斂證據。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R5-P0-01
**斷言**: N1 尚未完全閉合：失敗路徑的 `metadata.survivor_output` 仍被寫成只有 `{status, reason}`，與五鍵恆存在契約矛盾。
**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:211,214` 要求五鍵與三形狀驗證；`:213` 的 identity_missing／寫檔失敗字典只列兩鍵，無省略標記。反例：依該字面組出失敗 payload，`path`／`sha256`／`case_id` 不存在，違反 nullable 五鍵；`rg -n '五鍵恆存在|status:"computation_failed"|恰五鍵' ...` → 211、213、214。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca
[BLOCKING] 信心度=High。實作者可依 213 產生兩鍵失敗 payload，validator／前端將面對兩種 schema。修法：把 213 兩個 failure literal 改成完整五鍵（path/sha256=null、case_id 明確值），並保留 214 的 exact-key gate。

## CODEX-R5-P1-02
**斷言**: §V 對 OOM／並發測試自相矛盾，無法判定兩項是否為本輪必過 gate。
**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:224,273` 要求 budget receipt、atomic concurrent write 與 OOM count gate；`:278` 卻寫「已知不測：OOM／並發」。`rg -n '已知不測|並發寫|OOM 降載|peak RSS|n_regressions' ...` → 224、273、278。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca
[MAJOR] 信心度=High。若按 278 可跳過高風險 gate；若按 224/273 執行，驗收文件仍能被判定為未測。修法：刪除或改寫 278，明確列出 OOM count/peak-RSS receipt 與並發 atomic-write 的 pass/fail；資源上限需採已核准來源，不在實作端臆造。
必答1：N1 未閉合（CODEX-R5-P0-01）；N2 閉合（`:76` 唯一 `gap2_canonical_sha`、`:224` 200/200/n=20000 與 600 oracle、`:268-269` mutations、`:273` count gate）；N3 閉合（`:69` 已指 Task 1.0，`rg 'Task 3.1 之契約檔'` 無輸出）。
必答2：`bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS`；五份 `bash scripts/reconcile_stamps_check.sh <synth>` → 全部 `PASS rc=0`；`rg -n 'reasons 加|reasons 增鍵|Task 3\.1 之契約檔' docs/GAP2_MARGINAL_IC_SPEC.md` → no output；closure/budget grep 命中 69、76、211、213、214、224、268、269、273、278，故上述兩矛盾成立。
必答3：不可進 TODO；BLOCKING=`CODEX-R5-P0-01`，另須修補 MAJOR=`CODEX-R5-P1-02`。

§1 必查：1 矛盾＝P0/P1；2 端到端＝P0；3 可測＝P0/P1；4 quant＝無新 finding；5 過度工程＝無；6 OOM/並行＝P1；7 cache＝無；8 API/型別＝P0；9 測試品質＝P0/P1；10 Agent 可執行性＝P0/P1；11 短命工＝無。
§0 facts：template PASS、五份 stamp PASS、SPEC hash `a7703a4761ca`、phase 依賴單調 B1→B2→B3→B4→B5 已實跑 grep；assumption：各批「可獨立綠」只能確認 SPEC-level 無 forward dependency，實作尚未存在故未宣稱已綠。
ASSUMPTIONS_VERIFIED: R4 N2/N3 grep closure、N1/N2 contradiction probes、五份 reconcile stamps、template check、B1→B5 dependency anchors。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` PASS rc=0；五次 `bash scripts/reconcile_stamps_check.sh <path>` PASS rc=0；定向 `rg` 命令輸出如上；同一 `scripts/completeness_check.sh` 以 `zsh` source、同參數執行 → `COMPLETENESS PASS(single)` rc=0。
FAILURES_SEEN: 字面 `bash scripts/completeness_check.sh --single ... --family codex` 入口被既有 OPEN-debt PreToolUse gate 擋在腳本外；等價同檔同參數入口 PASS rc=0。
SCOPE_CHANGES: 只新增本 review 檔；未改碼、SPEC、TODO、tests 或 data_cache；PreToolUse 阻擋紀錄自動 append 至既有 `.claude/gate/audit.log`，其他 dirty 保留。
NUMERIC_OR_SCHEMA_IMPACT: 無產品數值變更；指出 survivor failure schema 與 OOM/並發驗收文字矛盾。
TMP_CLEANUP: 收尾移除本輪 `/tmp` workdir；保留 `/tmp/claude-501`。
OUTPUT_FILE: handoffs/20260818-gap2-specadv-r5-codex.md
TASK_ID: 20260818-GAP2-X-REVIEW-R5
STATUS: DONE
## COMPOSER-R5-P3-00

**斷言**: 本輪逐項核對 R4 N1–N3（codex 四項 schema／oracle 釘死修訂）均已條文級閉合；條文級 grep 無殘留矛盾；五批批次邊界無新 forward dependency。

**碼證**: **N1** — `docs/GAP2_MARGINAL_IC_SPEC.md:211-214`：`metadata.survivor_output` 五鍵 `{status, reason, path, sha256, case_id}` 恆存在；`status!="ok"` ⇒ `path`／`sha256`=null、`reason` 非 null；`ok` ⇒ 反之；Task 4.2 驗證⓪ 三形狀；§V V-24（`:270`）。**N2** — `:76` `gap2_canonical_sha` 唯一序列化＋有序 scrub（含 `filtered_features_path`）；`:203` Task 4.1 ⑮ `max_removed_candidates`／`n_regressions`；`:224` Task 4.3 k=200／n=20000 bench＋`n_regressions==600`；`:273` OOM 邊界改計數 gate ✓；V-22／V-23（`:268-269`）；`PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/canonical_probe.py` → `sha_equal=False`（現碼 `ichc_run.canonical_sha` 仍隨 path 變，與 SPEC 釘死之 `gap2_canonical_sha` 修法方向一致）。**N3** — `:69` JSON SoT 指 Task 1.0 `ic_survivor_contract.json`；`grep 'Task 3\.1 之契約檔'` → 0。交叉：`grep 'reasons 加\|reasons 增鍵'` → 0；五份 stamp PASS；`PYTHONPATH=. venv/bin/python /tmp/composer-gap2-specadv-r5/budget_probe.py` → `ok_oos`、`ETHUSDT`／`12h`、`case_id=None`、stage5 `14→2`、stage6 `input_features=2 output_features=2`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca

[P3] 信心度=High。R5 為收斂確認輪；本輪對 R4 codex 修訂做獨立複核（非沿用上輪 sentinel），未發現新反例或條文級矛盾。觀察（不升格）：§V 章程子句 `:278`「已知不測：OOM」與 `:273`「OOM 降載 ✓」字面易誤讀，但 Task 4.3 receipt／V-22 已釘死可測邊界，不阻 TODO。

---

## GROK-R5-P3-00

**斷言**: 本輪逐項核對後無 finding——獨立複核 R4 N1–N3 於修訂版 SPEC 皆已閉合；survivor_output 五鍵／`gap2_canonical_sha`／預算 oracle／§C Task 1.0 SoT pointer 與 Task 4.1／4.2／4.3／§V 無互斥；五批無 forward dependency；可進 TODO。

**碼證**: N1：L211 五鍵恆存在＋nullable 規則；L214 驗證⓪ 三形狀；V-24 L270。N2：L76 `gap2_canonical_sha` 有序 scrub（含 `filtered_features_path`）＋兩 sidefx sha 相等；L203 驗證⑮ `max_removed_candidates`＋`n_regressions` 語意；L224 k=200／n=20000 bench＋`n_regressions==600`；L273 OOM ✓ 計數 gate；V-22／V-23 L268–269。N3：`grep 'Task 3.1 之契約檔'`→0；L69 改指 Task 1.0 `ic_survivor_contract.json`。前置：`template_check` PASS；五份 stamp PASS。RECHECK：重跑 VERIFY 列 grep／stamp／template；對照 L69／L76／L203／L211／L214／L224／L268–L273。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#a7703a4761ca

[P3] 信心度=High。核對依據＝上列機械 grep＋N1–N3 與 Task／§V 交叉讀＋R4 synth 處置對照；未沿用本家 R4 sentinel。觀察（不升格、不阻 TODO）：(a) L213 改法失敗形狀仍寫兩鍵 shorthand，但同 Task L211／L214⓪／V-24 已釘五鍵＋null；(b) L211 正文誤寫「驗證⑦」而實際為驗證⓪（V-24 已指 ⓪）；(c) L74 仍括註「沿用 ichc_run.canonical_sha」，L76 已定 `gap2_canonical_sha` 為唯一序列化（④ 其餘沿用 ichc_run）——實作者以 L76 為準。

---


## 戳記

（待三家 append RECONCILE-STAMP）
