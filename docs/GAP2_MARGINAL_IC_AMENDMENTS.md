# GAP-2 SPEC — Amendments A1（延伸決策檔）

> 母 SPEC `docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN，2026-08-18）**不得就地改寫**；本檔為延伸層，記錄凍結後之實作決策與錨點。母 SPEC 與本檔衝突時**以本檔為準**。每條標母 SPEC 錨點與來源 finding。

## A1-1 — 契約 `reasons.survivor_output` 增值 `persist_suppressed`（母 SPEC Task 3.1／4.2；來源 R7 GROK-R7-P1-04）
- 母 SPEC Task 4.2 只列 `identity_missing`／`write_failed`；`_suppress_persist=True` 時倖存者檔不寫，`metadata.survivor_output` 仍須五鍵恆存在 ⇒ 需一個 reason 字面。
- 決策：`ic_survivor_contract.json#reasons.survivor_output` 於 **B4 Task 4.2 commit** 增值 `persist_suppressed`（只增值不改鍵集；Task 1.0 測試①鍵集斷言不受影響；契約 `version` 不變）。`survivor_output={status:"not_computed", reason:"persist_suppressed", path:null, sha256:null, case_id}`。

## A1-2 — §G golden 之 `case_id`（母 SPEC §G 凍結時機；來源 R7 CODEX-R7-P1-02）
- 母 SPEC 寫 `case_id=gap2_golden`；真實 fixture 經 `ichc_run.run_analyze()` 之 metadata 無 `case_id` ⇒ `_resolve_case_id` 回 `ic_gatekeeper`。
- 決策：golden 以 fixture 實際 `case_id`（`ic_gatekeeper`）為準並寫入 pre 檔 `case_id` 欄；`test_gap2_golden.py` 斷言 live 之 `report_ref` 檔名段與 pre 檔一致。不改 helper。

## A1-3 — 邊際 IC 節之 OOS 欄由 root 注入（母 SPEC Task 1.2 步驟「`fit_scope=train ⇒ oos_guarantees=True`」；來源 R7 GROK-R7-P1-02）
- 母 SPEC 讓 `compute_marginal_ic` 由 `fit_scope` 推 `oos_guarantees`／`pass_class`；事件不足 fallback 下 holdout 仍在但 root=`degraded_full_sample`，兩者可互斥。
- 決策：`fit_scope` 只描述投影擬合窗；`oos_guarantees`／`pass_class` 由 `_stage7_report` 於 `_resolve_root_status` 後注入（單一來源）；純函式回 `None` 佔位、`with_root()` helper 填值；validator ⑰ 一致性斷言不變。母 SPEC Task 1.2 驗證①（holdout ⇒ `oos_guarantees is True`）改於 Task 4.1 整合層斷言。
