# Handoff
**Agent**: Claude | **Time**: 2026-07-01 | **Branch**: main

## ★現役任務:驗收防偽閘 epic(使用者定全硬化,進行中)
起因=P0-FF-3 驗收捏造事故(見下方 FF 段紅燈 + 記憶 project_ff_verify_fabrication_incident)。三方裁定 A 類(編排端捏造,委員無責)。使用者選**全硬化** + 加 Gemini 議「合理性/會否過嚴撞牆」+ 掃全流程其他漏洞。
- **文件鏈**:`docs/VERIFY_GATE_BRIEF.md`(白話)→ `docs/VERIFY_GATE_SPEC.md`(過範本機檢,4 Phase)→ 雙家族 adversarial **CHANGES-REQUESTED**(`...-SPEC-ADV-{CODEX,COMPOSER,RECONCILE}.md`,6 收斂BLOCK)→ Claude 平衡版+全流程漏洞掃描 W1-W9(`...-BALANCE-AND-WORKFLOW-CLAUDE.md`)。
- **議事完成✅(四方收斂)**:`handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`。全硬化=可執行的「約束式硬化」。定案:claim-object 偵測(router)+provenance(judge);誠實邊界 careless-proof+tamper-evident非防惡意偽造;W2/W3/W4=P0(同型);硬性順序:claim-object 測試誤報=0 才接 PreToolUse 否則退 commit-hook+CI。
- **SPEC v2.1✅**`docs/VERIFY_GATE_SPEC.md`(claim-object偵測+三層enforcement+W1-W13+硬性順序)。v1雙家族adversarial CHANGES-REQUESTED→v2→closure再驗(BLOCK-1..5全CLOSED,剩W12/audit-schema/operational-block/fingerprint/EXEMPT表/W4/V17)→已補為v2.1。
- **SPEC v2.1 gate-ready✅**:兩家最終確認 APPROVED;`reconcile_stamps_check` PASS(body sha256:86fe39f...,codex task b1eicjnuo/composer bwhprlh0j)。
- **接手下一步**:① **TODO 生成**(TODO_GENERATION_PROMPT,依 SPEC v2.1 五 Phase)→ ② gate dispatch(--spec docs/VERIFY_GATE_SPEC.md --todo <檔> --adversarial handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md,機檢雙戳記)→ ③ **Composer 實作 5 Phase + Codex review**。實作硬性前提:claim-object 測試誤報=0 才接 PreToolUse,否則降 commit-hook+CI。
- **⏸️ 等使用者拍板**:是否現在啟動多小時實作,或先回 P0-FF-3。
- **reconcile 戳記**:`20260701-FF-FORENSICS-RECONCILE.md` Composer 已 CHANGES-REQUESTED(SPEC補規後重戳)。

## ★FF 深稽 P0(暫停,驗收防偽閘後回來)— 冷啟動接手指南
深稽藍圖 7 項:P0-FF-1/2/3/4 + P1-FF-5/6/7(優先序見 `handoffs/20260627-FF-AUDIT-RECONCILE.md`)。

### 已完成(commit+push)
- **B0 `2d13f2d`** = P0-FF-4(requires_kline marker + DATA_MANIFEST 10×3)。
- **B1 `2247c39`** = P0-FF-1(atomic differential + 修 2 真 bug:BUG-1 BETA/CORREL 餵 close,volume 非 high,low;BUG-2 手刻 Klinger 反相關→改 canonical)。三方數據簽核 PASS。
- **B2 `c94c850`** = P0-FF-2(全鏈 bar 級截斷 MR,單 TF)。
- **防假綠機制 `d6de3ba`/`0d377e6`** = 章程 §B1.1-1.3 + `scripts/mutation_probe_check.sh` + `scripts/mutation_probe_static.py`。
- **★FF 因果性三方數據簽核 PASS**:Claude+Codex+Composer 各獨立讀碼確認**無 look-ahead,可用於量化**(`handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md`;記憶 project_ff_causality_signoff)。2 caveat:float16 跨窗≤0.1%、特徵集列數依賴→stateful-param-audit epic。

### ⚠️ P0-FF-3 驗證紅燈(2026-07-01 首次真跑揭露)
- **全 mutation 真跑(bgr3kn4p6,2:25:45):3 passed(center/winsor/lag✅)、2 FAILED**:
  `test_mutation_align_lookahead_fails` + `..._with_tail_perturb_fails`。
- **根因:HANDOFF/WIP 宣稱「align mutation 真紅(babu8o07p)」不實**。RESULT handoff 顯示 babu8o07p 只跑
  mutation_probe_static(靜態 AST)+helper smoke+py_compile,「2 passed in **0.38s**」≠ 真 generate_features
  慢測(每次~25分)。**align 慢探針從未真跑過**(命中驗證保真度鐵律:smoke 不算數)。我這次首次真驗→紅。
- **traceback(b8uou6xj6,1:01:57)定性確認:兩探針皆 `DID NOT RAISE AssertionError`**=注入 +1 forward
  as-of 偏置後 `_assert_truncation_invariants` 完全沒報錯=**探針確實無牙齒**(非 production look-ahead 已證)。
  因 +1 偏置對稱套 full+trunc 兩跑→比較區 `[warmup:n_trunc)` 內可抵消。**修向(委員共識)**:不對稱注入
  (只 patch 單側)或 oracle 直接斷言指定 coarse 欄在已知 12h 邊界 index 的值差/source-index 差,不靠大抽樣。
- **下一步**:traceback 定性後,test-design 修(探針有牙齒)走委員會(Composer 實作+Codex review),非 solo。
  center/winsor/lag 3 探針已真綠可信。B2 回歸尚未跑。**勿 commit 收 WIP 直到 align 探針真紅+B2 綠**。

### P0-FF-3(多 TF,進行中)— 設計三方戳記✅、實作✅、驗證收尾中
- 設計 reconcile 雙戳記:`handoffs/20260630-FF-P0FF3-RECONCILE.md`(sha256:5da75188)。
- 檔:**新** `tests/feature_engineering/ff_truncation_mr_helpers.py`(B2 共用 helper)+ `test_ff_multitf_truncation_mr.py`(primary=1h, training=[1h,4h,12h]);B2 檔改 import helper。
- ~~**已驗 ✅**:① align mutation 真紅(babu8o07p)~~ **【SUPERSEDED 2026-07-01:此為驗收捏造,見上方紅燈段 + `handoffs/20260701-FF-FORENSICS-RECONCILE.md`。babu8o07p 從沒真跑 align 慢探針;首次真跑 align×2 FAILED。勿採用。】** ② c3 主 MR + perturbation 2 passed(bwx3t2jqq,64分)為**正向不變量綠**,**不**等於 align 探針有牙齒、亦不單獨證明無 look-ahead(category error)。程式碼在 WIP commit `9f9839d`。
- **下一步(收尾 P0-FF-3)**:
  1. traceback(b8uou6xj6)定性 align 假綠 → 修探針牙齒(走委員會 Composer 實作+Codex review)→ align×2 真綠。
  2. **B2 回歸**(抽 helper 後 P0-FF-2 行為不變,4h timeout):`pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -m requires_kline`。
  3. 兩者過 → 派 Codex code review P0-FF-3 diff → 正式 commit P0-FF-3(收 WIP)。
  4. **驗收捏造防再犯結構修補**(verify receipt+claim gate)另立 epic,走完整管線。
  5. 然後做 **P1-FF-5/6/7**。

### 剩餘
P1-FF-5(跨 symbol 值隔離 MR)、P1-FF-6(d-star/fracdiff probe;B2 已部分)、P1-FF-7(wrapper 多路徑+polars/numba+float16;B1 已部分 wrapper source)。**FF preset 盤點**另 epic(記憶 project_ff_preset_audit)。

## 鐵律(慢測試/執行)
- generate_features 全開 ~20分/次,warmup≈2051 需窗>暖機;驗證用內層 `timeout 14400`(4h)一次跑完別賭邊界(使用者 2026-06-30);**改完即交別硬撐自驗到 timeout**;**別巢狀 `&` 孤兒**;跑後 `git checkout -- tests/golden/l65/test_inventory.txt`+tier2 還原(測試副作用)。
- 中大一律 **Composer 實作 + Codex review**(使用者 2026-06-27,記憶 feedback_executor_override_composer_impl)。資料正確性/測試設計決策走三方委員會非 solo。慢測試委員勿跑全鏈,讀碼推理。
- 記憶索引見 MEMORY.md。pre-existing v8 失敗=test_ic_engine(非深稽)。
