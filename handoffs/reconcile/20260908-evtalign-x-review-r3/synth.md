# Reconcile — 20260908-evtalign-x-review-r3

**來源** 20260908-evtalign-x-review-r3-codex.md, 20260908-evtalign-x-review-r3-composer.md, 20260908-evtalign-x-review-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**三家 Verdict 行一致**：codex「可合併——R2 六 P0 形態已消除；無新 P0」／composer「可合併——…D5 需 user-ruling 或同步改 TODO」／
grok「可合併進 B2——但 P1（D5）須在 B2 參數化變成機械契約」。R2 之 D1／D2／D3／D4／D6／D7／D9 三家皆 CLOSED（原提出方重跑反例：
grok G／I 對新碼 BLOCKED；codex D2 mutation 紅；composer 逐條）；D3／D7 以殘留 `EA-RESID-4`／`EA-RESID-5` 收。

### E1 🔴 P1 — D5 未閉：事件 label 將覆寫時，stage2（與 stage0 預載）仍對鷹架硬閘（三家獨立命中）
**出處**：`CODEX-R3-P1-01`（`risk_adjusted` 截短＋合法 event labels ⇒ `target coverage too low`；`excess` ⇒ `benchmark_close is required`）、
`COMPOSER-R3-P1-01`（TODO `:165-169` 字面矛盾；grok Case J 仍 `MISBLOCK_DISCARDED_SCAFFOLD`）、`GROK-R3-P1-01`（close 中段缺根 ⇒ 覆蓋率紅，
事件 label 其實可對齊）。
**主委 brief 必答 4a 的主張被三家一致削弱**：我把 §C-6「禁止整段 skip」擴成「必須驗即將丟棄的序列」；三家指出判準是
「**資料是否將被替換**」（`event_label_values is not None`，在 `analyze()` 入口可知），不是 mode 字串分支 ⇒ 不違 §C-6。
**處置（採 grok／composer 最小修法，且補 codex 指出的反面）**：stage0／stage2 之 `validate_alignment` 在 `event_label_values is not None`
時**延後**（不 raise，暫存 `_deferred_scaffold_violation`）；stage3 得知該序列是否真被消費後裁定：
覆寫 ⇒ 降為診斷（`info["scaffold_alignment_deferred"]` 揭露訊息）；**未**覆寫（事件不足 fallback、filter 未啟用）⇒ 原樣 raise。
主線／無 event_label_values 路徑行為逐位元組不變。TODO Task 2.1 要點 3 改寫為此「延後裁定」語意（原文「覆寫前不驗」會漏掉「未覆寫仍須擋」）。

### E2 — P1 stage0 預載 labels 在截短 K 線下無逐值對照／mutation（codex＋composer；皆標 needs-research）
**出處**：`CODEX-R3-P1-02`、`COMPOSER-R3-P1-02`。兩家誠實標「測試／證據缺口，未證實 prod 漂移」。
**處置**：不必 research——可**直接證明 fail-closed**：預載 label 若由更長 K 線離線生成，reindex 到 feature 後尾端 lag 列有真值
⇒ `tail_nans ≠ lag` ⇒ 守衛 raise（守衛未動）。補測試 `test_stage0_preloaded_labels_from_longer_close_still_raise`（截短 K 線＋
「長 K 線生成」之預載 label ⇒ raise；「同尾生成」之預載 label ⇒ 通過且 payload sha256 不變）。不登殘留。

### E3 — P2 mutation 集合對 D5 無紅錨（grok）
**出處**：`GROK-R3-P2-01`。**處置**：mutate 腳本加 `E1-scaffold-hard-gate-restored`（把延後改回直接 raise ⇒ 覆寫案例紅）與
`E2-deferred-reraise-removed`（stage3 未覆寫時不再 raise ⇒ 事件不足案例紅）。

### E4 🔴 主委事故（自報，非委員 finding）：brief「golden 8 檔 rc=0」為**不實**
三家皆實跑到 `test_ichc_p2_golden::test_feature_set_and_config_exact` 紅並質疑。查我的背景任務 log：實為 **4 failed／78 passed，rc=1**；
我只看了 harness「exit code 0」（那是 `echo rc` 之後的 shell rc），沒讀 pytest 的 rc。A/B 於 `097dae40` worktree 重跑：
三條同樣 FAILED（`test_ic_1a_cut1_golden`／`test_ic_persist_redirect_golden_ab`＝reporter stub 缺 `analysis_status` kwarg，
2026-07-16 起；`test_ichc_event_timestamps…kwarg`＝brief 已列既有紅）；config_hash 那條凍結於 8/17、schema 改於 8/27，B1 未碰 schema。
⇒ **四條皆 B1 之前就紅，非本批造成**；但「主委把 rc=1 報成通過」本身是 `SCAR_LEDGER` 同型事故（FF 驗收捏造），
處置：HANDOFF／白話更正；四條既有紅另立 `EA-RESID-6`（`needs-research`：凍結 receipt 是否該重凍，屬 ICHC 票非本票）。

Verdict: 可合併——三家一致無新 P0；E1（D5）依三家共識實作「延後裁定」並改 TODO 要點 3；E2 以 fail-closed 測試閉合；E3 補兩條 mutation；E4 主委自報更正。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01

**斷言**: event label 會被 stage3 覆寫且不被消費，但 stage2 仍先對 forward-return scaffold 跑 `validate_alignment`；`return_type` 為 `risk_adjusted` 或 `excess` 的合法事件 run 可在 scaffold 階段 fail-closed，形成「驗了就丟」。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2939-2957` 先生成並驗 scaffold；`momentum/Analysis/ic_filter_orchestrator.py:3059-3093` 才覆寫並驗 consumed label；`docs/GAP3_EVENT_ALIGNMENT_TODO.md:165-170` 明定 event producer 應覆寫前不驗。只讀命令 `venv/bin/python -c ... return_type=risk_adjusted ...` → `AlignmentViolationError target coverage too low: actual=0.8344, required>=0.9585`；同類 `excess` → `ValueError benchmark_close is required for excess`；R2 grok Case J → `MISBLOCK_DISCARDED_SCAFFOLD`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#47c9ffb0ba23; docs/GAP3_EVENT_ALIGNMENT_TODO.md#c0961bbf2267; handoffs/20260907-evtalign-r2-grok-counterexamples.py#aae975eec9d1

[MAJOR] 信心度=High；這是 TODO/實作契約矛盾與可重現的誤擋，不是新 look-ahead P0。未直接改碼的理由=`user-ruling`：brief 明確要求裁定是否刻意保留 scaffold gate；最小修法見必答 4b。未取得裁定前，P1-01 不應被誤標 CLOSED。

## CODEX-R3-P1-02

**斷言**: B 的逐值截短→同尾證據只覆蓋 stage2 重新生成 labels；stage0 預載 labels 只裁 oracle `close`、不重生或保存 label producer parity，因此相同缺陷可讓 8 條 mutation 全綠且目前沒有 byte-level preload 對照。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2788-2821` 讀入既有 `labels_df` 後只在有 reader 時裁 `close`，再直接以既有 `label_series` 驗證；`tests/momentum/test_close_coterminalize.py:80-97` 的逐值測試只呼叫 `_stage2_label_generation`；`handoffs/20260907-evtalign-mutate.py` 的 8 條 mutation 無 stage0 preload payload mutation。指定 stage0 oracle probe 只輸出 `逐鍵相同 = True`（alignment report），不等價於 label payload parity。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#47c9ffb0ba23; tests/momentum/test_close_coterminalize.py#e51721648f7; handoffs/20260907-evtalign-mutate.py#4528ba20e650

[MAJOR] 信心度=Medium；目前是測試/證據缺口，未由本輪 probe 證明實際 production label 漂移。未修理由=`needs-research`：需先確認產品允許「長 K 線離線預載 label＋短 feature run」的組合，再補 stage0 byte-level parity 與 mutation；不應在本輪捏造 production finding。

## COMPOSER-R3-P1-01

**斷言**: 實作保留 stage2 對鷹架之 `validate_alignment`，與 TODO Task 2.1 要點 3「事件模式覆寫前不驗」矛盾；在 `return_type∉ORACLE`＋截短 K 線＋合法 `event_label_values` 下，stage2 可在覆寫前 fail-closed，形成「驗了就丟」擋死（grok Case J）。

**碼證**: `ic_filter_orchestrator.py:2951-2957`（stage2 仍 `validate_alignment`）；`docs/GAP3_EVENT_ALIGNMENT_TODO.md:165-169`（覆寫前不驗）；`handoffs/20260907-evtalign-r2-grok-counterexamples.py` Case J → `MISBLOCK_DISCARDED_SCAFFOLD`。RECHECK: 事件路徑＋`return_type=excess`＋`N_CLOSE>N_FEAT`＋合法 `event_label_values` 跑 `_stage2`→`_stage3` 觀察是否在 stage2 raise。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#ad7b19170f9a; docs/GAP3_EVENT_ALIGNMENT_TODO.md#e2b6c6eebb68

[MAJOR] 信心度=High。非新洩漏，是 **TODO／實作／R2 D5 未閉** 之治理項。不修理由=`user-ruling`（brief 必答 4a 已請裁定）。修法見必答 4b。

---

## COMPOSER-R3-P1-02

**斷言**: B 的「截短化約為同尾」僅在 stage2 **生成**路徑有逐值測試；stage0 **預載** labels 在截短 K 線下未驗「磁碟 label 字节＝同尾預載」，mutation 8 條亦未覆蓋。

**碼證**: `test_stage2_truncated_labels_equal_coterminal_labels_and_tail_nan_eq_lag` 僅呼叫 `_stage2_label_generation`；stage0 `:2808-2821` 裁切 close 但不重生 HDF5 label；mutate 清單無「stage0 預載 label 漂移」項。RECHECK: 預載 labels（`N_FEAT` 行）+ reader `N_CLOSE` 跑 `_stage0_ingestion`，比對 label payload sha256 与同尾 reader `N_FEAT`。

**來源摘要**: tests/momentum/test_close_coterminalize.py#9c8aeb691151; momentum/Analysis/ic_filter_orchestrator.py#ad7b19170f9a

[MAJOR] 信心度=Medium。誠實邊界＋測試缺口，非已證實 prod 洩漏。不修理由=`needs-research`（需確認產品是否用「長 K 線離線 label + 短 feature」預載組合）。建議 B2 增 stage0 預載對照或登記 `EA-RESID` 若確認不存在該用法。

---

## GROK-R3-P1-01

**斷言**: B1 實作仍在 `_stage2_label_generation`（及 stage0 預載）對**即將被 `event_label_values` 覆寫丟棄**的鷹架跑 `validate_alignment` 硬閘，違反 TODO Task 2.1 要點 3；在 close 中段缺根／覆蓋率不足時，會在事件 label 本身合法的情況下擋死分析（「驗了就丟」殘留）。

**碼證**: TODO `:165-170`「事件模式下，覆寫前那條序列不驗」；orch `:2934-2957` stage2 裁切後仍 `validate_alignment(...)`，`:3059-3099` 才覆寫並 `validate_consumed_label`。本輪探針：中段 drop 3 根後 proper 生成 → `AlignmentViolationError: target coverage too low`；同資料若只跑 `validate_event_given` 本可對齊。B 後 proper＋excess 已不再因截短誤擋（降級理由）。RECHECK：構造 `event_label_values` 齊全＋close 中段缺根 → 現況 stage2 紅；修後應 stage2 不硬擋、stage3 event_given 綠。

**來源摘要**: docs/GAP3_EVENT_ALIGNMENT_TODO.md#e2b6c6eebb68

[MAJOR] 信心度=High。修法：見必答 4b（資料驅動：有 `event_label_values` 則鷹架不硬閘；硬閘只驗被消費序列）。若委員會裁定保留鷹架硬閘 → 必須改寫 TODO／SPEC 要點 3，並接受缺口誤擋為明示行為。**不修理由若暫掛 B2**：`user-ruling:` 待委員會對 4a 定案／或 `blocked-by: Task 2.2` 參數化收斂。

## GROK-R3-P2-01

**斷言**: phase-1 mutation 八條（B1/B2/B3/D1/D2/D3/A4/C0）全綠仍放得過「事件將覆寫卻仍對鷹架硬閘」之缺陷——集合對 D5／TODO 要點 3 無紅錨。

**碼證**: `handoffs/20260907-evtalign-mutate.py` MUTATIONS 列表無「刪除／跳過 stage2 validate 當 event 覆寫」之反向或正向錨；gate `GATE PASS: phase=1`。RECHECK：新增 mutation／測試——`event_label_values` 非空時 spy／行為斷言 stage2 不得以覆蓋率／尾端契約否決分析，否則紅。

**來源摘要**: handoffs/20260907-evtalign-mutate.py#4528ba20e650

[MINOR] 信心度=High。修法：併入 B2 Task 2.2 參數化或 phase1 增一條 mutation；與 P1-01 同閉。

---

