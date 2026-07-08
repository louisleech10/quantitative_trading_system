# 實作派工:1-align Batch B1(task-id: ic1a-align-impl-b1)

你是實作端(Codex)。SPEC/TODO 已 Frozen(雙 RECONCILE-STAMP),**逐字照做,不重新設計**:

- SPEC=docs/IC_PHASE1_1A_ALIGN_SPEC.md(v3 Frozen;§ADV-RESOLUTION/D-1~D-4 為裁決,不可偏離)
- TODO=docs/IC_PHASE1_1A_ALIGN_TODO.md(v3 Frozen)
- **本批只做 B1 = Task 1.1 + Task 1.2**(TODO §B);不碰 Task 2.x。

## Task 摘要(細節以 TODO 為準)
- **Task 1.1**:`momentum/core/contracts.py::validate_alignment` 落地(Tier-1 不變量 D-1/D-3+Tier-2 bar-ordinal 抽樣 oracle D-2)+`AlignmentViolationError`+`AlignmentReport`;改寫 `tests/momentum/core/test_alignment_contract.py`。
  - **實作註記(Codex R2 你自己的 note)**:尾端 NaN==lag 檢查對完整 target/close 軸,非截斷 feature 子集。
- **Task 1.2**:共用 horizon resolver(`return_(\d+)` 解析;帶單位→換算或 raise);`_resolve_effective_label_horizon` 真解析;`purge_gap` 同源。

## 紅線(違反=退件)
- 不改 AlignmentSpec 欄位/label 生成語意/loader schema/cut1/cut2 已簽核行為。
- 不放寬/刪除既有測試斷言(接回時 diff 驗)。
- data_cache 唯讀;測試輸出走 pytest tmp。
- 不 git checkout/commit;寫檔即可,接回由編排端驗。
- 疑問/卡關 2 輪解不了→停下回報,禁 solo 硬幹。

## 驗收(B1 Gate,逐字跑並附輸出)
```
pytest tests/momentum/core/test_alignment_contract.py -q
pytest tests/momentum/ -k "horizon_resolver" -q
grep -r "from api\." momentum/ | wc -l   # 須 0
```
+ mutation 轉紅 receipt:M1(平移±1 bar)/M3(RangeIndex)/M4(錯 freq)/M7(return_5+default=1)各證明「正確資料 PASS、變異資料 raise」。

## 回報格式
寫 `handoffs/IC1A-ALIGN-IMPL-B1-RESULT.md`:改了哪些檔(函式級)/上列命令實際輸出/mutation 四條 receipt/ASSUMPTIONS_VERIFIED/FAILURES_SEEN/SCOPE_CHANGES/NUMERIC_OR_SCHEMA_IMPACT/STATUS。
