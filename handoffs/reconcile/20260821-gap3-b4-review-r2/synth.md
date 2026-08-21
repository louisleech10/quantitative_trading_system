# Reconcile — 20260821-gap3-b4-review-r2

**來源** 20260821-gap3-b4-review-r2-codex.md, 20260821-gap3-b4-review-r2-composer.md, 20260821-gap3-b4-review-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；閉合輪＋codex 兩條 R1 漏抓寫回）

**Verdict**: 需修補後合併——R1 八條由原提出方重跑全數 CLOSED（codex 4/4、composer 2/2、grok 2/2）、他家交叉複核同意；codex 本輪另抓兩條 R1 漏抓（P1）全數採納修補；R3 由 codex 重跑同一反例閉合（composer／grok sentinel 複核）→ 全 CLOSED 後三家 RECONCILE-STAMP → B4 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Y1 R1 閉合（八條） | （codex 正文 R1_CLOSURE 四條；COMPOSER-R1-P1-01／P2-02、GROK-R1-P1-01／P2-01 於各家正文表列 CLOSED） | **CLOSED**；附錄逐字保留於各家交件 |
| Y2 provenance 交易完整性 | CODEX-R2-P1-01 | **採納**：寫入順序改 **sidecar 先、帳本後**（帳本 append 失敗只留 provenance 孤兒、N 不變）；`run_dsr_pbo` 消費端 `provenance_reconcile` 檢查——帳本候選缺 sidecar ⇒ 整體 `unavailable:provenance_incomplete`；`provenance_reconcile(key)` 公開 orphan 對帳路徑（`ledger_without_provenance`／`provenance_without_ledger`）。推翻 R2 brief assumed「sidecar 失敗 raise 即可接受」 |
| Y3 stale receipt | CODEX-R2-P1-02 | **採納**：`receipt_digest(series)`＝f(index, values, entry_semantic, label_definition) 為唯一 digest 定義；`to_return_series` 產生、`_assert_return_series` 重算比對，不符 ⇒ `MetricTypeError(stale receipt)`；測試：真實 kline 產出 copy 後改值／改 index 皆拒、未改通過 |
| Y4 兩家 sentinel | COMPOSER-R2-P3-00, GROK-R2-P3-00 | **採認**：0 新 findings；R1 修補未引入新問題 |

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**: ledger append 成功而 provenance sidecar 失敗時，`record_candidate` 雖 raise，仍留下 1 筆無 sidecar 的 ledger；`run_dsr_pbo` 只讀 ledger，之後仍回 `capability_status=ok`/DSR `ok`，故 provenance 完整性不是 fail-closed。
**碼證**: `candidate_ledger.py:229-244` 先 append ledger、後寫 sidecar；`:286-310` 不檢查 sidecar。暫時 probe `PYTHONPATH=. venv/bin/python review_tmp/gap3_b4_r2_probe.py` → `record_rc=raised OSError sidecar write unavailable; ledger_rows=1; sidecar_exists=False; run_capability_status=ok; run_ledger_status=ok; run_dsr_status=ok`。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#a825e470d626; docs/GAP3_EVENT_TODO.md#df04bdabf37d; handoffs/20260821-gap3-b4-review-r2-brief.md#839fc031c057
[P1] 信心度=High；這推翻「sidecar 失敗 raise 即可接受」前提：後續 consumer 看不到失敗，且相同 evaluation_id 的 retry 會撞 duplicate。修法需使 sidecar 缺失的 evaluation 在 DSR/PBO 變 unavailable，並提供可驗證的 orphan/reconcile 路徑。
## CODEX-R2-P1-02
**斷言**: 收據 attrs 閘只驗欄位形狀與 hash 為 64 hex，未驗 hash 對應目前 values；普通 `Series.copy()` 後原地改值會帶著舊 hash 通過 `_assert_return_series`，可把改過的報酬寫入 ledger。
**碼證**: `candidate_ledger.py:68-99` 無 digest 重算；`:178-181` producer digest 包含 values。真實 kline probe `venv/bin/python -c '...to_return_series(...); mutated=s.copy(); mutated.iloc[0]+=0.123; _assert_return_series(...)...'` → `accepted=True; attrs_hash_matches_values=False`（原 hash `0688e34f...`，重算 `09d1e6f0...`）。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#a825e470d626; tests/momentum/event_samples/test_candidate_ledger.py#79411209968d; handoffs/20260821-gap3-b4-review-r2-brief.md#839fc031c057
[P1] 信心度=High；這不是蓄意偽造 attrs，而是 pandas 普通 copy/mutation 的 stale receipt，會讓 GAP-1 snapshot membership 綁到錯誤資料。修法需在 consumer 重算並比對 canonical digest，或使 return payload/receipt 不可變且只能由 `to_return_series` 建立。
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R1-P1-01／P2-02 兩條原反例均 CLOSED；修補 diff 未引入可證偽 P0–P2 缺陷；他方六條 R1 複核皆同意 CLOSED；brief assumed 攻擊不推翻已裁誠實邊界。

**碼證**: B4 Gate 本輪複驗：`-k "pattern_bridge or candidate_ledger"` → **27 passed** rc=0；event_samples 全套 → **222 passed** rc=0；strategy_validation → **272 passed** rc=0。本家閉合：`-k "disguised or auc_fed"` **2 passed**；`-k pbo_observation_axis` **1 passed**。修補引入檢：`grep extract_event_patterns momentum/` 無 B4.1 外 caller；`test_to_return_series_hand_exact_each_entry_semantic` 五語意 parametrize 仍綠；manifest 必填反例與 `n_events_raw=400` 一致。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md#8finding；momentum/Analysis/event_samples/candidate_ledger.py#bfcd52b2b98b；momentum/Analysis/event_samples/pattern_bridge.py#2d4c5b8daf18；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/20260821-gap3-b4-review-r2-brief.md

正文：閉合義務本家 2/2 CLOSED；他方 6/6 複核同意；§0 assumed 兩條攻擊後仍成立（偽造 attrs 路徑為 R1 已登記邊界，非新缺陷）。禁捏造湊數。

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——GROK-R1-P1-01／P2-01 兩條原反例均 CLOSED；八條 R1 修補未引入可證偽 P0–P2 新缺陷；brief 兩條 assumed（非原子 sidecar／蓄意偽造 attrs）攻擊不推翻。

**碼證**: `pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → **27 passed** rc=0；`-k pbo_observation_axis` → 1 passed；`-k "disguised or auc_fed"` → 2 passed；`-k manifest_required` → 1 passed 且手跑 `n_events_raw=400`；`-k "unlogged_candidate or record_guards or requires_command or hand_exact"` → **8 passed**；手跑疏忽分數拒／偽造 attrs 仍過（誠實邊界）；手跑 sidecar 失敗 orphan＋集不等拒；`git diff e9e0257c..HEAD --stat -- momentum/ tests/` → 4 files +198/−47（白名單內）。全套 222／GAP-1 272 引 receipt，本輪未並行重跑。

**來源摘要**: handoffs/reconcile/20260821-gap3-b4-review-r1/synth.md#dbfe6fe45b91；handoffs/20260821-gap3-b4-review-r1-grok.md#e3cc1be68e18；handoffs/20260821-gap3-b4-review-r2-brief.md#839fc031c057；momentum/Analysis/event_samples/candidate_ledger.py#a825e470d626；momentum/Analysis/event_samples/pattern_bridge.py#d8b69a49dde2；tests/momentum/event_samples/test_candidate_ledger.py#79411209968d；tests/momentum/event_samples/test_pattern_bridge.py#ebe6d74f9965；docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；handoffs/run_receipts/20260821T153000Z-gap3-b4-r1-fix-gate.log#6a2b11e7af20

正文：閉合義務兩條全 CLOSED；§0 assumed 已攻；不受理 SPEC/TODO 重審／B5／GAP-1 本體／R1 已裁成立前提再議。禁捏造湊數。

