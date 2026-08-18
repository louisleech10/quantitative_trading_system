# GAP-2a／2b TODO adversarial 審查 R8（codex）

審查標的：`docs/GAP2_MARGINAL_IC_TODO.md` DRAFT R2；衝突時依 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md` A1-1..3。審查只讀，未修改 SPEC、TODO、程式或既有測試。

## 前置驗證

- `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS，rc=0。
- `bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → CROSSCHECK SMOKE PASS，rc=0。
- `bash scripts/ic_wiring_check.sh` → `R1a(24 toggles)/R1b(16 mapped)/R2(11 allowlist)/R3(5 sections) 全綠`，rc=0；目前 5 節是現況，TODO 要求 B4 改成契約驅動。
- R1–R7 `handoffs/reconcile/20260818-gap2-x-review-r{1..7}/synth.md` 逐檔核對，皆有 codex/composer/grok APPROVED 戳記；R7 synth 三家戳記內容相同。
- `rg -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` 命中 TODO:256；同一行的字串確實包含被禁止的連續子字串「獨立 OOS 驗證」。
- `bash scripts/mutation_probe_check.sh`（TODO B1 gate 的無參數寫法）→ `用法: mutation_probe_check.sh <test_path> ...`，rc=1。

## Verdict：需修補後派工

## CODEX-R8-P1-01

**斷言**: B5 要修改的既有 `FeatureTierPanel.tsx` 與 `icAnalysisStore.ts` 不在 SPEC §C 的「唯此七處」既有檔白名單內，TODO 同時把它們列為必改，執行端無法同時遵守兩個 scope 契約。

**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_SPEC.md:61-69` → §C 白名單列 `types.ts` 但未列 `icAnalysisStore.ts`／`FeatureTierPanel.tsx`；`nl -ba docs/GAP2_MARGINAL_IC_TODO.md:12,251-253` → TODO §0 宣稱沿用白名單，Task 5.1 卻要求修改 store 與 `FeatureTierPanel.tsx`。RECHECK: 重新逐項比對 §C 白名單與 Task 5.1 既有檔清單。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[MAJOR] 信心度=High。若按 SPEC scope，B5 會因越界停工；若按 TODO scope，則 SPEC 的 canonical 白名單失效。修法：由主委在受核准的延伸決策中明確把 store／panel 納入白名單，或把 TODO 改回 SPEC 允許的檔案集合；同時更新 scope 追溯與驗收檔案清單。

## CODEX-R8-P1-02

**斷言**: A1-3 已決定 OOS 欄只由 root 注入，但 TODO Task 4.1 仍要求以 `fit_scope=="train"` 推導 `pass_class="oos"`，事件 fallback 會產生互斥語意。

**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:79,201-202` → Task 1.2 明定 `oos_guarantees`／`pass_class` 不由純函式推導、由 `_stage7_report` 注入；同一 TODO:201 卻寫「`pass_class`（`oos` iff `fit_scope=="train"`）」；A1-3:13-15 明定 root 單一來源。現有 root resolver `nl -ba momentum/Analysis/ic_filter_orchestrator.py:1153-1175` 亦可在 event fallback 時回 `degraded_full_sample`。RECHECK: 用 holdout masks + `metadata.event_filter.fallback=True` 路徑，確認節 OOS 欄與 root 完全一致。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。執行端照 4.1:201 寫會讓「holdout 仍存在但 root degraded」路徑標成 OOS，或讓 validator ⑰ 失敗。修法：刪除 fit_scope 推導語句，明定 stage6b 回傳 `None` 佔位、`_stage7_report` 在 root resolve 後只注入 root 值，並將整合測試以 root status 作 oracle。

## CODEX-R8-P1-03

**斷言**: A1-2 要求 golden pre 檔保存實際 `case_id=ic_gatekeeper` 並驗證 `report_ref`，但 TODO Task 4.0 的 pre 檔輸出 schema 沒有 `case_id` 欄，也沒寫該 assertion。

**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:184-193` → `case_id 由 helper 決定`，但 4.0:187 的 pre 檔欄位只有 fixture/config/canonical/summary/filter/generator/ts，沒有 `case_id`；A1-2:10-11 明定真實值為 `ic_gatekeeper`、必寫入 pre 檔且 live `report_ref` 要與 pre 一致。RECHECK: pre 檔缺 `case_id` 時執行 golden test，確認它目前沒有可比對的 expected identity。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。Agent 可照 TODO 產出看似完整的 golden，但永遠無法驗證 report-ref identity，後續 case-id 漂移會綠。修法：把 `case_id`（A1-2 指定的 helper 實值）加入 pre schema、`--write/--check` 與 `test_gap2_golden.py` 的 exact assertion；不可回到 SPEC 舊的 `gap2_golden` 假設。

## CODEX-R8-P1-04

**斷言**: TODO 一方面要求 `_persist_outputs` 以顯式 kwargs 避免讀尚未建立的 `_ic_cache`，另一方面 4.2 偽碼仍直接讀 `self._ic_cache["event_identity"]`，與現有 persist-before-cache 呼叫順序衝突。

**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:202,220-221` → 4.1 明寫新增 `stage6b_results`／`event_identity`／`features_path`／`label_series` kwargs 且「不讀 `_ic_cache`」，4.2 卻寫 `event_identity=self._ic_cache["event_identity"]`；現況 `nl -ba momentum/Analysis/ic_filter_orchestrator.py:3422-3449` → `_persist_outputs` 在 `_ic_cache` 建立於 3449 前被呼叫，且 `nl -ba ...:3789-3796` 的舊簽名没有上述 kwargs。RECHECK: 在新 call graph 中於 `_ic_cache` 尚為 `None` 時跑正常 analyze、refilter 與 fallback rerun，確認 persist 仍只使用顯式 owner 參數。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[MAJOR] 信心度=High。照 4.2 實作會在正常路徑 `None` 解參照，或為了避錯擅自改變 cache 建立順序；也可能 refilter 沿用舊 event identity。修法：4.2 的 build/persist 偽碼改成只使用顯式 kwargs，並列出 `_stage7_report`、fallback wrapper、refilter 三個 caller 的參數來源；`_ic_cache` 只能在 persist 完成後承接 immutable snapshot。

## CODEX-R8-P1-05

**斷言**: `persist_suppressed` 的 status/reason 形狀在 A1-1 與 TODO 4.2 不一致，且 TODO 的字面可能被實作成未列於 reason SoT 的 `not_computed:persist_suppressed`。

**碼證**: VERIFY A1-1:7 → 五鍵形狀為 `status:"not_computed", reason:"persist_suppressed"`；TODO:220 → 寫成 `survivor_output 為 not_computed:persist_suppressed`，同時又說將 `persist_suppressed` 加入 `reasons.survivor_output`。RECHECK: 對 suppress 路徑檢查五鍵 exact、`status` 屬 capability status、`reason` exact 等於 contract reason 值，而不是把兩欄串成一個字串。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。不同 Agent 會產生不同 JSON：一個通過 A1-1，另一個把 `not_computed:persist_suppressed` 當 reason；validator、前端與 contract sync 會不一致。修法：TODO 明寫完整五鍵 object；reason 一律由 `load_survivor_contract()["reasons"]["survivor_output"]` 取值，`status` 與 reason 禁混寫。

## CODEX-R8-P1-06

**斷言**: B5 要顯示的警語仍含自己禁止的連續子字串，因此任何忠實實作都會同時滿足 positive text 與 negative `not.toContain` 失敗。

**碼證**: VERIFY `rg -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → TODO:256；該短句包含 `獨立 OOS 驗證`，而 TODO:256、259、262 同時要求禁該 substring。RECHECK: 用 JavaScript `text.includes("獨立 OOS 驗證")` 對指定警語執行，結果為 `true`。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d

[MAJOR] 信心度=High。B5 元件測試無法在正確文案下通過。修法：改用不含該連續字串但保留「同一 test 被 selection 消費、僅描述統計」語意的文案，並同步 TODO、SPEC 延伸決策與 component oracle。

## CODEX-R8-P1-07

**斷言**: B4 bench 只驗 `n_regressions==600` 數值，未驗該計數真的等於 `fit_projection`／`lstsq` 呼叫數，因此可用假 counter 掩蓋超額計算或錯誤預算 gate。

**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:80,90,230-242` → TODO 將 `n_regressions` 語意宣稱為實際 fit 呼叫次數，但 bench 只有 `n_regressions==600` 與 receipt 存在，沒有 spy、呼叫計數器、超預算 case 的獨立 call-count assertion。SPEC:225、279 同樣只有 600 計數與 receipt。RECHECK: monkeypatch/spy `fit_projection` 後跑 200 survivors＋200 removed，要求 spy count、結果 counter、三視角 expected count exact 相等；再跑兩個超預算 gate，確認被略過視角沒有任何 fit call。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d

[MAJOR] 信心度=High。錯誤實作仍可產生 600 這個漂亮數字，卻無法支持「每次 lstsq n×≤201」及不超額的 OOM 防護宣稱。修法：用獨立 spy 或可驗證的累計 owner；bench 與超預算 mutation 同時斷言實際呼叫數、每次設計矩陣欄數上界及 result counter。

## CODEX-R8-P1-08

**斷言**: SPEC/TODO 要求 xsec 路徑輸出 `not_applicable:cross_sectional_mode`，但沒有指定 `analyze_cross_sectional()` 的插入點或測試；現行 xsec `analysis_results` 也沒有 `marginal_ic`，reporter 預設會形成裸空節。

**碼證**: VERIFY `nl -ba momentum/Analysis/ic_filter_orchestrator.py:1510-1536` → xsec 五節 status object 清單沒有 `marginal_ic`；`nl -ba momentum/Analysis/ic_reporter.py:327-347` → reporter 目前只會把明列的 analysis result key 透傳，未列者取空 dict。TODO:201 只寫「xsec 呼叫方傳」但 Task 4.1 驗證:211 沒有 xsec case；TODO:232-236 要 B4 wiring 讀全部 report sections。RECHECK: 加入 report 契約新節後，以 xsec input 跑 `analyze_cross_sectional()`，驗 `marginal_ic == {status:not_applicable, reason:cross_sectional_mode}` 且 wiring 不報裸空。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；momentum/Analysis/ic_reporter.py#e7eb62b1699e

[MAJOR] 信心度=High。若只按兩個 global 插入點實作，xsec 報告會缺節或裸 `{}`，與 §D7、§N R3 及 B4 R3 wiring 衝突。修法：Task 4.1 明列 `analyze_cross_sectional()` 的 N/A 組裝與測試，並禁止 xsec 呼叫計算函式。

## CODEX-R8-P1-09

**斷言**: TODO B1 gate 直接執行 `bash scripts/mutation_probe_check.sh`，但該腳本的正式用法要求至少一個 test path，故 gate 按原文必然 rc=1；同時 B2/B4 新 Python 測試的 marker/探針落點沒有逐檔列出。

**碼證**: VERIFY `bash scripts/mutation_probe_check.sh` → `用法: mutation_probe_check.sh <test_path> [<test_path>...]`，rc=1；TODO:19 要求新測試含 `test_mutation_*` 或行首 N/A，TODO:110 卻使用無參數命令；TODO:128、211、226、234-242 列新測試與外部 mutation case，但未給每個新 Python 測試的 marker／`test_mutation_*` 對映。RECHECK: 以明列的 `test_survivor_contract.py test_marginal_ic.py test_factor_combiner.py test_gap2_stage6b_wiring.py test_gap2_survivor_persist.py test_gap2_golden.py` 跑 checker，並要求每檔有非空 marker 或真探針。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66；scripts/mutation_probe_check.sh#03309f359005

[MAJOR] 信心度=High。B1 gate 會在執行測試前硬失敗，且後續批次可能只有外部 sed probe、沒有被 `mutation_probe_check.sh` 機械保護的正確性測試。修法：把 gate 命令改成明列測試路徑或目錄，並在每個新增 Python 測試 Task 的驗證欄指定 marker／`test_mutation_*`；保持 `scripts/mutation_probe_check.sh` 的非空探針規則。

## §1 必查 11 類

1. 矛盾／互斥：有，P1-01、P1-02、P1-05、P1-06。
2. 漏項／端到端：有，P1-03 的 golden identity、P1-04 的 persist owner、P1-08 的 xsec N/A。
3. 不可測驗收：有，P1-07 的 counter 與 P1-09 的 gate 命令；其餘主要 oracle 有明列輸入、容差或 rc。
4. quant 假設：未發現新的 D1–D5 定義方向錯誤；O1b 的「degenerate 或 `|marginal|≤0.02`」與 O4 aggregate 帶寬仍是建議加獨立性檢查的取巧面，但不另列 blocking，因 O1a/O6/O7 已提供相鄰反證。
5. 過度工程：無；五批拓撲與新增模組邊界沒有再擴大。
6. OOM／並行：有，P1-07；receipt 觀測降級本身已由 R7/A1 正確處理，問題是 counter 未被獨立驗證。
7. Cache 正確性：有，P1-04；`event_identity` 的 owner／persist 時序仍互相矛盾。
8. API／型別／相容：有，P1-01；B5 的既有檔 scope 必須先對齊。
9. 測試品質：有，P1-07、P1-08、P1-09；B1 mapping 本身已列十條唯一 V-ID，未重複列 finding。
10. Agent 可執行性：有，P1-02、P1-03、P1-04、P1-08、P1-09。
11. 必要性／短命工：無；各 Task 的「存活至」均指全票完工後保留，未見後續 Phase 會刪除或覆蓋其輸出。

## 必答 1 — Agent 可執行性

- B1 Task 1.0 loader、1.1 三個純函式、1.2 計算偽碼與 1.3 十條 V-ID 對映大致可落地；但 B1 gate 命令本身先由 P1-09 擋住。
- B2 Task 2.1 的 `combine_factors`、paired bootstrap、train-only sign/weight 與驗證目標足夠；新 test file 的 mutation marker 仍需依 P1-09 補釘。
- B3 Task 3.1 已列完整 `build_survivor_output` kwargs、validator 規則與驗收；B4 接線前不應再自行猜 root OOS，須採 P1-02 的 A1-3 單一來源。
- B4 Task 4.0–4.3 是主要卡點：P1-03 的 pre case_id 欄、P1-04 的 persist caller／cache owner、P1-07 的 counter oracle、P1-08 的 xsec caller／test 尚需明文補全；P1-05 另需鎖定五鍵 object。
- B5 Task 5.1 的 store custom／具名 preset、`FeatureTierPanel.TOGGLES`、後端 mapping 與三路徑驗證方向已明確；仍先受 P1-01 scope 與 P1-06 文案 oracle 阻擋。

## 必答 2 — 義務覆蓋

D1–D7、D3′、D3″、§G 1–4、§V 24 條、§N G2-R1/R2/R3/R5 都有 TODO 落點或 registry pointer；R7/A1-1..3 的方向也已被引用。實質漂移是：§C 白名單與 B5（P1-01）、§G golden case_id（P1-03）、D3′ root OOS（P1-02）、persist/cache lifecycle（P1-04）、A1-1 reason object（P1-05）、xsec N/A（P1-08）。因此機械 `template_check`／crosscheck PASS 不等於義務語意已收斂。

## 必答 3 — 批次獨立性／forward dependency

- B1→B2 的兩條 pytest gate 已按 `-k load` 與 marginal 全檔拆開，十條 B1 V-ID 目前各一對映；但 gate 呼叫缺 path（P1-09）。
- B2→B3 與 B3→B4 的 dataclass／validator 依賴拓撲清楚；B3 不改 report 契約的約束與 B4 同 commit 增鍵方向一致。
- Task 4.0 確實位於 B4 首件、4.1 前；但 pre schema 沒 case_id（P1-03）。
- B4→B5 依賴 `STAGE_OVERRIDE_PATHS["marginal_ic"]` 合理，且 TODO 已要求 foundation/intermediate/advanced/custom；然而既有 scope 白名單未同步（P1-01）。
- A1-1 的 `persist_suppressed` 只增 reason value、不增 key set，批次形狀可獨立；TODO 的 status/reason 寫法仍需 P1-05 釘死。

## 必答 4 — 取巧面

- `n_regressions==600` 可由獨立 counter 造出，未必代表 600 次 `fit_projection`，見 P1-07。
- O1b 接受「退化或 `|marginal|≤0.02`」，可讓部分錯誤實作靠小 IC 通過；O1a raw-space probe、O6 rank invariance、O7 independent reference 是緩解但不是完整替代。
- O4 以 aggregate ratio／IC range 為主，需保留 sequential 順序與 per-feature exact assertions，避免局部漂移仍綠。
- B5 的 custom／具名 preset wiring 已有明確驗證要求，不能只驗 checkbox；P1-01 指出驗收檔案 scope 必須先合法化。
- bench receipt 已明確降級為觀測，沒有未授權的 wall-time/RSS 閾值；問題不是缺閾值，而是 P1-07 缺實際呼叫數 oracle。

## 必答 5 — 測試設計

B1 十條唯一 V-ID、V-22a 與 B4 V-22、B4 V-24 的批次分工沒有重複；A1-2 golden identity 與 A1-3 root OOS 應各有獨立 falsification。主要缺口是 P1-07 的 call spy、P1-08 的 xsec N/A case、P1-09 的每檔 mutation marker／可執行 gate；P1-06 的文案 positive/negative oracle 目前自相矛盾。現有純函式 oracle 多數可證偽，未將「函式不存在」當 finding。

## 必答 6 — 可以 Frozen 進 B1 嗎？

不能宣告整票 TODO FROZEN；BLOCKING 清單：

- P1-09：B1 gate 原文必然 rc=1。
- P1-02、P1-04、P1-05：B4 root／persist／reason lifecycle 會產生互斥或 runtime failure。
- P1-03、P1-07、P1-08：golden identity、OOM counter、xsec report coverage 不可由現行驗收充分證明。
- P1-01、P1-06：B5 既有檔 scope 與文案 oracle 未收斂。

修補上述條目並重新跑 template/crosscheck、三家 review/stamp 後，才可重新判斷 Frozen。B1 的統計核心本身不需重作，但不能以它局部可行取代整票 TODO 的 Frozen gate。

## 被當成事實的未驗證假設（§0）

- `n_regressions` 被寫成「實際 fit 呼叫次數」目前只是 TODO 語意宣稱，沒有獨立 receipt/spy 證據（P1-07）。
- 「xsec 呼叫方傳 N/A」被寫成足以覆蓋 xsec 端到端，但沒有指名現有 `analyze_cross_sectional()` caller 或測試（P1-08）。
- B5 已可依 SPEC §C 直接落地是假設；實際 §C 與 Task 5.1 的既有檔清單不一致（P1-01）。

ASSUMPTIONS_VERIFIED: R1–R7 reconcile stamps 三家 APPROVED；template_check rc=0；todo_spec_crosscheck rc=0；現況 ic_wiring_check rc=0；TODO 文案 substring 命中；mutation_probe_check 無參數 rc=1；現有 orchestrator persist 先於 `_ic_cache` 建立；現有 xsec analysis_results 未含 marginal_ic。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` PASS rc=0；`bash scripts/ic_wiring_check.sh` PASS rc=0；`bash scripts/mutation_probe_check.sh` usage failure rc=1；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-todoadv-r8-codex.md --family codex` PASS rc=0；其餘為 `rg`/`nl`/`shasum` read-only probes。
FAILURES_SEEN: `mutation_probe_check.sh` 無參數 rc=1（TODO B1 gate 原文重現）；現況 wiring 只報 R3(5 sections)，屬尚未實作的預期基線，不改檔。
SCOPE_CHANGES: 只新增 `handoffs/20260818-gap2-todoadv-r8-codex.md`；未修改 SPEC/TODO/程式/測試/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 未改產品數值、schema 或輸出大小；審查指出 pre case_id、reason shape、xsec section 與 counter oracle 缺口。
HANDOFF_OUTPUT: `handoffs/20260818-gap2-todoadv-r8-codex.md`; task-id=20260818-GAP2-X-REVIEW-R8; family=codex。
STATUS: DONE
