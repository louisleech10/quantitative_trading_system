# 票 2 實作主委驗收 finding C-5(BLOCKING:V7 真洩漏,redirect 接縫缺口)
Task-id: p2debt-t2 | Chair: Claude(Fable 5) | Date: 2026-07-11

## 現象(final5 receipt /tmp/t2-final5.log)
V1/V2/V5 PASS;V6 新 gate PASS(V6_NO_NEW_RED=1+DIGEST=1);**V7:1 failed, 132 passed + DIGEST_DIFF_EMPTY[V7]=0**。

## 實錘證據(主委蒐證)
- `find data_cache -newer /tmp/dc-digest-pre.txt -type f` → 4 檔於 V7 期間(23:03)寫進 repo data_cache:
  - `data_cache/models/lightgbm_bad_payload.pkl`(29 bytes)
  - `data_cache/reports/ic_report_ic_gatekeeper.json`、`ic_filter_log_ic_gatekeeper.json`、`ic_summary_ic_gatekeeper.md`
- aggregate digest pre=f0224e8b... → current=3181b6a4...(守衛判定正確)。
- 失敗測試 `test_lightgbm_analyzer.py::test_save_load_format_error_branches`:
  FileNotFoundError 路徑=**redirect 犧牲根** `.../ic_redirect0/models/lightgbm_bad_payload.pkl`。
- 故事線:**寫路徑繞過 redirect 寫進真 data_cache/models;讀路徑走 redirect 在犧牲根找不到** → 一個 bug 兩個症狀。
  reports 3 檔同理=另一寫路徑(疑 ic_filter_orchestrator.py:3182 硬編 output_dir="data_cache/reports")未掛接縫。

## 定性
- **守衛設計成功**(VERIFY-EXEMPT:doc-example:p2debt-t2-c5;證據見本 finding §實錘 find 輸出):digest oracle 對 lightgbm_bad_payload.pkl 洩漏亮紅,證明 gate 可證偽非廉價綠燈。
- **實作缺口**:S1-S11 seam manifest 漏掉(至少)lightgbm 模型 save 路徑與 orchestrator 報告寫入路徑,
  或 V7 這幾個測試的 redirect fixture 掛載不完整(寫端未 patch、讀端有 patch)。

## 修法要求(派 codex)
1. 先定位:test_save_load_format_error_branches 的 save 呼叫鏈實際寫檔路徑解析點;報告 3 檔的寫入點。
2. 補接縫(tests/fixtures/ic_persist_redirect.py 的 patch set/seam manifest)使寫讀同根;若屬 S1-S11 manifest
   遺漏須同步更新 SPEC 接縫清單(AMENDED 註記+出處本 finding)。禁改 momentum//api/ 生產碼(除非委員會另裁)。
3. 自證:單跑 V7 須 132+1 passed(原 failed 轉綠)+DIGEST_DIFF_EMPTY[V7]=1;>60s DELEGATED 交 grok 跑。
4. 主委已清除 4 個洩漏檔恢復 repo 狀態(見下)。

## 主委清理(恢復基線)
rm 上列 4 檔(V7 測試產物,非使用者資料;pickle 為壞 payload fixture、reports 為 ic_gatekeeper 測試報告)。
