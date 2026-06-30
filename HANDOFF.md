# Handoff
**Agent**: Claude | **Time**: 2026-06-30 | **Branch**: main

## ★FF 深稽 P0(進行中)— 冷啟動接手指南
深稽藍圖 7 項:P0-FF-1/2/3/4 + P1-FF-5/6/7(優先序見 `handoffs/20260627-FF-AUDIT-RECONCILE.md`)。

### 已完成(commit+push)
- **B0 `2d13f2d`** = P0-FF-4(requires_kline marker + DATA_MANIFEST 10×3)。
- **B1 `2247c39`** = P0-FF-1(atomic differential + 修 2 真 bug:BUG-1 BETA/CORREL 餵 close,volume 非 high,low;BUG-2 手刻 Klinger 反相關→改 canonical)。三方數據簽核 PASS。
- **B2 `c94c850`** = P0-FF-2(全鏈 bar 級截斷 MR,單 TF)。
- **防假綠機制 `d6de3ba`/`0d377e6`** = 章程 §B1.1-1.3 + `scripts/mutation_probe_check.sh` + `scripts/mutation_probe_static.py`。
- **★FF 因果性三方數據簽核 PASS**:Claude+Codex+Composer 各獨立讀碼確認**無 look-ahead,可用於量化**(`handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md`;記憶 project_ff_causality_signoff)。2 caveat:float16 跨窗≤0.1%、特徵集列數依賴→stateful-param-audit epic。

### P0-FF-3(多 TF,進行中)— 設計三方戳記✅、實作✅、驗證收尾中
- 設計 reconcile 雙戳記:`handoffs/20260630-FF-P0FF3-RECONCILE.md`(sha256:5da75188)。
- 檔:**新** `tests/feature_engineering/ff_truncation_mr_helpers.py`(B2 共用 helper)+ `test_ff_multitf_truncation_mr.py`(primary=1h, training=[1h,4h,12h]);B2 檔改 import helper。
- **已驗 ✅**:① 對齊 look-ahead mutation `test_mutation_align_lookahead_fails` **真紅**(babu8o07p);② **c3 主 MR + perturbation 2 passed**(bwx3t2jqq,64分,metadata 修後)= 多 TF 對齊因果健全無 look-ahead。程式碼在 WIP commit `9f9839d`。
- **下一步(接手 session 收尾 P0-FF-3,再做 P1)**:
  1. 全 mutation 真紅(內層 `timeout 14400` 4h):`bash scripts/mutation_probe_check.sh tests/feature_engineering/test_ff_multitf_truncation_mr.py`(5 探針:align×2+center/winsor/lag,~2-3h)。
  2. **B2 回歸**(抽 helper 後 P0-FF-2 行為不變,4h timeout):`pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -m requires_kline`(c2_1/c2_2/fracdiff/5 mutation)。
  3. 兩者過 → 派 Codex code review P0-FF-3 diff → 正式 commit P0-FF-3(收 WIP)。
  4. 然後做 **P1-FF-5/6/7**。

### 剩餘
P1-FF-5(跨 symbol 值隔離 MR)、P1-FF-6(d-star/fracdiff probe;B2 已部分)、P1-FF-7(wrapper 多路徑+polars/numba+float16;B1 已部分 wrapper source)。**FF preset 盤點**另 epic(記憶 project_ff_preset_audit)。

## 鐵律(慢測試/執行)
- generate_features 全開 ~20分/次,warmup≈2051 需窗>暖機;驗證用內層 `timeout 14400`(4h)一次跑完別賭邊界(使用者 2026-06-30);**改完即交別硬撐自驗到 timeout**;**別巢狀 `&` 孤兒**;跑後 `git checkout -- tests/golden/l65/test_inventory.txt`+tier2 還原(測試副作用)。
- 中大一律 **Composer 實作 + Codex review**(使用者 2026-06-27,記憶 feedator_override)。資料正確性/測試設計決策走三方委員會非 solo。慢測試委員勿跑全鏈,讀碼推理。
- 記憶索引見 MEMORY.md。pre-existing v8 失敗=test_ic_engine(非深稽)。
