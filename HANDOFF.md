# Handoff
**Agent**: Claude | **Time**: 2026-07-07 | **Branch**: main

## ★IC 第二刀首項 = feature_library.load 貼回時間軸(row_index attach) — ✅ 完成(三方簽核 PASS)

### 成果
- **根因**:載入走 V2 reader 回位置整數 index,從不貼回時間軸→下游寫 np.arange 偽 timestamps→頻率校驗誤判 raise。全 tf 中(1h 走現成 fixture 未現形)。
- **修法**:`feature_library.py` 新增 `_attach_row_index`(鏡像 `_attach_cgsa_row_index`),`_load_internal` V2 分支 return 前貼回;無 sidecar→no-op,長度不符→ValueError。只改 index,值/欄/列/檔大小不變。
- **測試**:新增 row_index attach 單元(no-op/length-guard)+ 真 run 值守恆/時間軸 byte-equal;追蹤測試 retarget 至失敗邊界(materialize→真時間軸→split 校驗不 raise;218k 特徵 full analyze>17min 屬正交效能問題)。回歸 `tests/momentum/test_feature_library_row_index.py tests/momentum/test_feature_library_config_hash.py tests/api/test_ic_analysis_service.py` 13 passed VERIFY:20260706T165905Z-cut2-rowindex-regression exit0;解耦 grep=0;mutation 對照已證。
- **清中毒 cache**:刪 bug 期 BTC/12h/e53e2290 ingest cache(arange 偽軸,gitignored,已重生真時間軸)。

### 三方數據正確性簽核(全 PASS 零 BLOCKING)
- Claude 自產 + Codex adversarial(語義時間 oracle 交叉驗列序 0 mismatch,9 run)+ Composer 資料正確性,各自獨立實跑。產出:`handoffs/CUT2-ROWINDEX-REVIEW-{codex,composer}.md`。
- reconcile:`handoffs/CUT2-ROWINDEX-RECONCILE.md`,RECONCILE-STAMP codex+composer APPROVED,reconcile_stamps_check PASS(body sha256:22153e82…)。
- NON-BLOCKING 已修:還原 L6.5 golden(conftest scoped-collect 副作用)、SPEC §G-3/TODO 對齊 retarget。

### Follow-up(登記,不阻本刀)
- IC ingest cache 版本化/timestamp 校驗(防殘留中毒 h5 被 exists-gate 重用)。
- `tests/conftest.py:108` scoped pytest 收集 clobber L6.5 golden inventory——測試基建 smell。
- 1d `EXPECTED_FREQ_BY_TIMEFRAME` 補值(需真 1d run)。
- full-analyze(218k 特徵>17min)完成驗收 →「79 合成 IC 測試換真實資料」epic。

### 續(第二刀後段)
- 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖;grouped_ic 止血。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員派工帶 --task-id+--output,產出後 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要,diff 既有測試斷言防假綠;執行端不得 git checkout tracked 共用檔。
