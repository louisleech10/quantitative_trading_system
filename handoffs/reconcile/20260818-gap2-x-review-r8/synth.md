# Reconcile — 20260818-gap2-x-review-r8

**來源** 20260818-gap2-todoadv-r8-codex.md, 20260818-gap2-todoadv-r8-composer.md, 20260818-gap2-todoadv-r8-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **15 條**（codex 9／grok 4／composer 2），下列十個群集**引用全部 15 條，0 掉項**。判定：codex／grok「不可 Frozen」、composer「可 Frozen（B4 前修）」⇒ 未收斂；**14 條接受**寫回 TODO DRAFT R3，**1 條駁回**（CODEX-R8-P1-06，碼證見 U6）；SPEC 義務側擴張一處走延伸檔 A1-4（B5 既有檔白名單）。grok 文內回指之 GROK-R7-P0-01／GROK-R7-P1-02／CODEX-R7-P1-02 為 R7 歷史 finding（已在 R7 synth T4／T2 收斂），非本輪新條，不另立群集。

Verdict：需修補後派工——TODO DRAFT R3＋A1-4 寫回；本 synth 戳記後派 R9 複核；三家「可 Frozen」即 TODO FROZEN → B1。

### U1 — B5 既有檔白名單：SPEC §C#6／TODO §0 未列 `icAnalysisStore.ts`／`FeatureTierPanel.tsx`，Task 5.1 卻必改
**引用**: CODEX-R8-P1-01, GROK-R8-P0-01
**處置＝接受**：實核 SPEC §C#6 只列 `types.ts`；TODO §0⑥ 列 store 未列 panel。走延伸檔 **A1-4**：§C#6 擴為 `types.ts`＋`icAnalysisStore.ts`＋`FeatureTierPanel.tsx`（僅 `TOGGLES` 加一列＋計數）；TODO §0⑥ 同步三檔；Task 5.1 修改檔案清單與 A1-4 逐字一致。

### U2 — Task 4.1 步驟 1 殘句「`pass_class`（`oos` iff `fit_scope=="train"`）」與 A1-3 root 單一來源互斥
**引用**: CODEX-R8-P1-02, GROK-R8-P1-02
**處置＝接受**：刪該推導句；`_stage6b_marginal_ic` 只回 `{**res.to_dict(), "composite": ...}`（`oos_guarantees`／`pass_class` 為 `None` 佔位）；`_stage7_report` 於 `_resolve_root_status` 後**只**注入 root 值；整合測試①／③ 以 root `analysis_status` 為 oracle（含 holdout 存在但 event fallback ⇒ root `degraded_full_sample` ⇒ 節 `oos_guarantees is False`）。

### U3 — A1-2 未落地：Task 4.0 pre 檔 schema 無 `case_id`、Task 4.3 無 `report_ref` 斷言
**引用**: CODEX-R8-P1-03, GROK-R8-P1-01
**處置＝接受**：Task 4.0 `--write` schema 加 `case_id`（helper 實值 `ic_gatekeeper`，不改 helper）；`--check` 比對 `case_id` exact；Task 4.3 `test_gap2_golden.py` 加斷言 live `metadata.survivor_output.case_id == pre["case_id"]` 且倖存者檔 `report_ref == f"ic_report_{pre['case_id']}.json"`。

### U4 — Task 4.2 偽碼 `event_identity=self._ic_cache["event_identity"]` 與 Task 4.1「persist 顯式 kwargs、不讀 `_ic_cache`」互斥
**引用**: CODEX-R8-P1-04, GROK-R8-P0-02, COMPOSER-R8-P1-01
**處置＝接受**：Task 4.2 偽碼改 `event_identity=event_identity`（`_persist_outputs` 顯式 kwarg）；明列三 caller 參數來源：`_stage7_report`（analyze／analyze_full／fallback 遞迴皆經此）＝`self._event_identity`＋本輪 `stage6b_results`＋`self._features_path`＋`label_series`；`refilter()` 同（`_event_identity` 沿用同 request 之值）；`_ic_cache` 只在 persist 完成後承接 immutable snapshot；測試 ⑧ 於 `_ic_cache is None` 下三路徑 persist 不 raise。

### U5 — `persist_suppressed` 之 `survivor_output` 五鍵形狀寫成 `not_computed:persist_suppressed` 速記，易被實作成單一字串
**引用**: CODEX-R8-P1-05
**處置＝接受**：Task 4.2 明寫完整五鍵 object `{status:"not_computed", reason:"persist_suppressed", path:None, sha256:None, case_id}`（與 A1-1 逐字一致）；`reason` 由 `load_survivor_contract()["reasons"]["survivor_output"]` 取值；驗證 ⓪ 加第四形狀（suppressed）五鍵 exact。

### U6 — 警語「非獨立 OOS 驗證」含禁字串（codex）
**引用**: CODEX-R8-P1-06
**處置＝駁回（碼證）**：TODO L256 實際文案為「倖存者選於同一測試段；本節數字為描述統計，非獨立驗證」（R7 T5 已改），**不含**「OOS」；`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 命中；grok T5／composer T5 本輪皆實核 substring `False`。codex 之 `rg` 命中宣稱與檔案內容不符（疑審 R7 前快取）。不改文案；R9 由 codex 重跑同一 grep 確認關閉。

### U7 — bench `n_regressions==600` 只驗 counter 未驗實際 `fit_projection` 呼叫數
**引用**: CODEX-R8-P1-07
**處置＝接受**：Task 4.3 bench 與 Task 1.2 測試 ⑭ 加獨立 spy：`monkeypatch` 包裹 `marginal_ic.fit_projection` 計數並記每次 `Z_S.shape[1]`；斷言 spy count == `res.n_regressions` == 期望值（loo k＋sequential k＋removed m）、每次欄數 `≤ max_survivors_for_loo+1`；超預算 case：被略過視角 spy 增量 == 0。V-22a／V-22 探針對映不變。

### U8 — xsec 路徑 `not_applicable:cross_sectional_mode` 無插入點／無測試；reporter 未透傳新節 ⇒ 裸空節
**引用**: CODEX-R8-P1-08
**處置＝接受**：Task 4.1 明列 `analyze_cross_sectional()` 之 `analysis_results` 加 `"marginal_ic": dict(_xsec_na)`（現 `:1518-1536` 五節旁；**禁**呼叫計算函式）；`ic_reporter.generate_json_report` 透傳 `marginal_ic`（白名單④；`analysis_results.get("marginal_ic")` 缺 ⇒ **不得**寫裸 `{}`，由 orchestrator 保證恆給 status object）；驗證加 ⑯ xsec：`report["marginal_ic"] == {"status":"not_applicable","reason":"cross_sectional_mode"}` 且 `ic_wiring_check` R3 綠。

### U9 — B1 gate `bash scripts/mutation_probe_check.sh` 無參數必 rc=1；新測試檔 marker 對映未逐檔列
**引用**: CODEX-R8-P1-09
**處置＝接受**：B1 gate 改 `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py`；各批 gate 同法明列該批新測試檔；每個新增 Python 測試 Task 之驗證欄指定 `test_mutation_*` 名（1.0／1.1／1.2／2.1／3.1／3.2／4.1／4.2／4.3）。

### U10 — §0 L12／Task 4.1 標題殘留「掛四處」，正文已收斂為兩插入點
**引用**: COMPOSER-R8-P2-01
**處置＝接受**：§0①、§B B4 列、Task 4.1 標題統一改「兩插入點＋`_in_fallback_rerun` 旗標」。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R8-P1-01

**斷言**: Task 4.2 L220 偽碼仍寫 `event_identity=self._ic_cache["event_identity"]`，與 Task 4.1 L202「`_persist_outputs` 在 `_ic_cache` 建立前被呼叫、須顯式 kwargs、不讀 `_ic_cache`」直接矛盾；照 L220 實作會在 persist 時讀到**上一輪 stale cache** 或 `KeyError`。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:202`「新增 kwargs `stage6b_results`／`event_identity`／`features_path`／`label_series` **顯式傳入**（不讀 `_ic_cache`）」；L220「`event_identity=self._ic_cache["event_identity"]`」；`momentum/Analysis/ic_filter_orchestrator.py:3432` `_persist_outputs` 早於 `:3449` `self._ic_cache = {`。RECHECK: 對照 L202 與 L220 是否同寫 `event_identity` 來源（應為 persist kwarg 或 `self._event_identity`）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[MAJOR] 信心度=High。B4 `_persist_outputs`／倖存者檔 provenance 會用錯事件身分或執行期炸。修法：Task 4.2 L220 改為 `event_identity=event_identity`（`_persist_outputs` 新 kwarg，由 `_stage7_report` 傳 `self._event_identity`）或明寫 `self._event_identity`；刪除 `_ic_cache` 讀取。

---

## COMPOSER-R8-P2-01

**斷言**: §0 L12 與 Task 4.1 標題 L197 仍寫「`_stage6b` 掛四處／四處掛載」，正文 L202 已收斂為「**兩個插入點**」，執行端若只讀 §0 會重複掛載或找第四呼叫點。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:12`「掛四處」；L197「stage 6b 四處掛載」；L202「掛載**兩個插入點**…`analyze()`…`refilter()`」。R7 T3 已接受兩插入點處置。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[MINOR] 信心度=High。不阻 B1；建議 §0／Task 4.1 標題改「兩處插入」與 L202 對齊。

---

## GROK-R8-P0-01

**斷言**: Task 5.1 要求改 `frontend/src/components/ic-analysis/FeatureTierPanel.tsx`，但 TODO §0「既有檔改動白名單（唯此七處）」未列入該檔；執行端若守 §0 則無法完成 R7 T4 寫回的可見 toggle，若改該檔則違反 §0／派工「白名單外一律不碰」。

**碼證**: TODO §0 L12 白名單⑥＝`types.ts`＋`icAnalysisStore.ts`，無 `FeatureTierPanel.tsx`（VERIFY: `grep -n FeatureTierPanel docs/GAP2_MARGINAL_IC_TODO.md` → 僅 L3 敘事與 Task 5.1 L253，§0 無）。Task 5.1 L253 明示改 `FeatureTierPanel.TOGGLES`；實核面板仍硬編碼 24 鍵、`已啟用 {enabledCount}/24`（`FeatureTierPanel.tsx:20-51,:97`）。SPEC §C 白名單亦無此檔／無 store（§C#6 僅 `types.ts`）→ 標 **SPEC 義務側**（建議 A1-4 擴白名單）。RECHECK: §0 是否把 `FeatureTierPanel.tsx` 列入白名單（並與 SPEC §C／Task 5.1 檔案清單一致）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[BLOCKING] 信心度=High。失敗：B5 再犯 R7 GROK-R7-P0-01（UI 無 checkbox）或 agent 因 §0 拒改／越權。修法：§0 白名單加入 `FeatureTierPanel.tsx`；SPEC §C 以延伸檔同步（store＋panel＋types）。

---

## GROK-R8-P0-02

**斷言**: Task 4.1 已釘死「`_persist_outputs` 在 `_ic_cache` 建立前呼叫 ⇒ `event_identity` 等須**顯式 kwargs、不讀 `_ic_cache`」；Task 4.2 組裝呼叫仍寫 `event_identity=self._ic_cache["event_identity"]`，與 4.1 互斥，執行端照 4.2 會在首跑 persist 讀到未寫入／舊 cache。

**碼證**: TODO Task 4.1 L202：「persist…於 `_ic_cache` 建立前…kwargs `…／event_identity／…` **顯式傳入（不讀 `_ic_cache`）**」。Task 4.2 L220：`build_survivor_output(..., event_identity=self._ic_cache["event_identity"], ...)`。實核 orchestrator：`_persist_outputs` 於 `:3432-3438`，`self._ic_cache = {` 於 `:3449`（之後）。RECHECK: Task 4.2 是否改為使用 4.1 新增之 `event_identity`（及 `stage6b_results`／`features_path`／`label_series`）參數，並刪除對 persist 當下 `_ic_cache[...]` 的依賴。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#92580fd8db66

[BLOCKING] 信心度=High。失敗：`KeyError`／沿用上一次 analyze 的 event_identity／provenance 錯；R7 T3 寫回在 4.1／4.2 未收斂。修法：4.2 偽碼與 4.1 kwargs 對齊；可保留 `self._event_identity` 實例欄作 refilter 備援，但 persist 路徑不得讀尚未建立的 `_ic_cache`。

---

## GROK-R8-P1-01

**斷言**: 延伸檔 A1-2 要求 pre 檔寫入實際 `case_id`（`ic_gatekeeper`）且 `test_gap2_golden.py` 斷言 live `report_ref` 檔名段與 pre 一致；TODO Task 4.0 `--write` 欄位清單與 Task 4.3 驗證皆未納入該義務。

**碼證**: A1-2（`docs/GAP2_MARGINAL_IC_AMENDMENTS.md` L9-11）：寫入 pre 之 `case_id` 欄＋golden 斷言 `report_ref`。Task 4.0 L187：`--write` → `{fixture_sha256, config_hash, canonical_sha, summary_table, filter_log, generated_by, ts}`——**無 `case_id`**；僅「`case_id` 由 helper 決定」。Task 4.3 L234 驗證列無 `case_id`／`report_ref`／A1-2。RECHECK: 4.0 寫檔 schema 加 `case_id`；4.3 加 `report_ref` 檔名段 == pre[`case_id`]；註明不改 helper（A1-2）。

**來源摘要**: docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。失敗：R7 T2／CODEX-R7-P1-02 之 case_id 漂移在 B4 golden 再現；agent 可能仍寫死 `gap2_golden`。修法：把 A1-2 逐字落進 Task 4.0／4.3。

---

## GROK-R8-P1-02

**斷言**: Task 4.1 步驟 1 仍要求 `_stage6b` 回傳「並帶 `pass_class`（`oos` iff `fit_scope=="train"`）」，與 A1-3／同 Task 步驟 2「`oos_guarantees`／`pass_class` 由 `_stage7_report` 於 root 解析後注入」及 Task 1.2「OOS 欄 `None` 佔位」衝突；事件不足 fallback（holdout 仍在、`fit_scope=train`、root=`degraded_full_sample`）會讓執行端在注入前寫入謊稱 OOS 的 `pass_class`。

**碼證**: TODO L201 步驟 1 末句；L202 步驟 2 注入句；Task 1.2 L79／A1-3 L13-15。實核 root：`event_filter.fallback is True` ⇒ `degraded_full_sample` 即使 holdout applied（`ic_filter_orchestrator.py:1164-1167`）。RECHECK: 刪除步驟 1 之 fit_scope→pass_class 推導；明確 `_stage6b` 只回 `res.to_dict()`（含 `None` 佔位）＋composite，OOS 兩欄只在 stage7 注入。

**來源摘要**: docs/GAP2_MARGINAL_IC_AMENDMENTS.md#6fdc01cb5613

[MAJOR] 信心度=High。失敗：重開 R7 GROK-R7-P1-02；validator ⑰／整合③與節上欄互斥。修法：步驟 1 與 A1-3 對齊刪除該推導句。

---


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:60163294cb12282a3b397a1df75c5946b98476ad79ea07b8fe14ea316ea946a6 task:20260818-GAP2-X-STAMP-R9
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:60163294cb12282a3b397a1df75c5946b98476ad79ea07b8fe14ea316ea946a6 task:20260818-GAP2-X-STAMP-R9
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:60163294cb12282a3b397a1df75c5946b98476ad79ea07b8fe14ea316ea946a6 task:20260818-GAP2-X-STAMP-R9
