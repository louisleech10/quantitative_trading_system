# DECOUPLE-ALLOWLIST — 解耦白名單機制+scanner 校準 — SPEC

> 來源 PLAN/診斷：handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md(§C-1/§C-3)　|　日期：2026-07-14(r2:三家 adversarial 9 BLOCKING/14 MAJOR 全吸收,架構改 AST+戳記機檢)　|　對應 TODO：docs/DECOUPLE_ALLOWLIST_TODO.md

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中。
- **命中高風險原則**：(b) 跨模組共用路徑(scanner=全 repo 決策依據,放行錯=永久假綠)。零數值/ML。
- RISK-HIT: b
- §G 於 §N 登記;adversarial 已跑三家(r1),BLOCKING 修訂=本 r2。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**(receipt ×6;r2 依三家 VERIFY 補強)：
  - FACT-RECEIPT: `nl -ba scripts/check_decoupling.sh | sed -n '44,95p'` → R2 僅查 top-level `^from momentum\.`,且**經 python filter `re.match(r'…:from momentum\.…')` 判同域**——任何 `import momentum.X` 形式或縮排 `from` 全漏(codex/grok 實證);R3 僅 services top-level+services 四空格 lazy `from`+routes/websocket top-level(Claude/三家實跑一致)。
  - FACT-RECEIPT: codex 實跑 regex 反例 → 未 escape 的 `from momentum.FeatureEngineering.consumer_gate(import| |$)` 會誤放 `from momentum.FeatureEngineeringXconsumer_gate import`(`.` wildcard);2-space/tab `from`、任意縮排 `import` 皆合法 Python 且現 selector 漏。
  - FACT-RECEIPT: codex 實跑 → repo 無 `.github/CODEOWNERS`、無 allowlist-hash 綁戳記的 gate;「同 PR 改快照常數」單人可完成,不構成治理(r1 快照設計作廢的根據)。
  - FACT-RECEIPT: `bash scripts/check_decoupling.sh` → 現況 R2=5/R3=10/R4=0,15 筆全落 RECONCILE 六模組。
  - FACT-RECEIPT: composer 實跑 → `api/models/` 存在 concrete momentum import 且**不在現行 R3 掃描根**;`docs/ARCHITECTURE.md` L161 現況表仍寫 R3=12(過時,實為 10)。
  - FACT-RECEIPT: `bash scripts/reconcile_body_hash.sh handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md` → 822514…6fef 與 codex/composer v2 stamps 相符(裁決有效)。
- **待使用者確認**：無(機制形態=技術選型,依三家 adversarial 一致方向:AST+戳記機檢;RECONCILE 已授權「落地方式實作票內定」)。
- **已確認結果**：`2026-07-14 使用者指示「照順序完成三段」`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- **manifest 逐 module+逐 symbol 精準**;禁 glob/prefix/substring;module 名先過 `^momentum(\.[A-Za-z_][A-Za-z0-9_]*)+$` 驗證,比對用**字串 equality**(AST 名稱),不得把 module 名插進 regex(codex ADV-3)。
- `feature_library` 禁入;`run_locks` 的 `RunLease` **symbol 級禁止**(api 只准 `RunBusyError`/`is_run_active`——RECONCILE 少數意見吸收條款,r2 機器強制)。
- **r4 增補(AST 新揭露處置)**:B1 實跑 AST 揭露舊 grep 漏掉的 5 筆 momentum/Optimization 縮排跨域 import(→ `momentum.Strategy.performance_metrics`/`momentum.Analysis.strategy_registry`/`momentum.Analysis.pareto_analyzer`)。處置=manifest 增**第二表「新揭露暫豁免(pending triage)」**(3 module,精準 symbol,owner=`pending/DECOUPLE-TRIAGE-2`,contract=「舊 scanner 盲區既存依賴,暫豁免維持現狀;真偽 triage 另立票」);**是否豁免由 Task 1.3 戳記輪(委員會)裁決**,任一家 REJECTED → 改走修 code 路線;follow-up triage 票入 ROADMAP。scanner 對兩表同語意處理。T1b 驗收改:FF 表 6 條+pending 表 3 條。
- 白名單=單一機讀來源;ARCH 只 pointer。
- 收緊不放鬆:R1/R4-R7 檢查不碰;R2/R3 只准更嚴。
- **範圍誠實**:本票 R3 掃描根=services/routes/websocket(現行語意+盲區補洞);`api/models/` 覆蓋=**已知缺口**,不靜默擴(擴=新紅字需 triage),立 follow-up 小票記入 ROADMAP(composer ADV-8 處置)。

## §G Golden / Baseline
- 移 §N(RISK-HIT 僅 b;可證偽性由 §V 永久 regression 測試矩陣承擔)。

## §P Phase 與依賴

### Phase 1 — 四 Task(依賴:1→2→3→4)

**Task 1 — AST import 掃描器+機讀 manifest**
- 目標:R2/R3 改 AST 掃描,天然覆蓋全部 import 形式;manifest 含 symbol+owner+contract。檔案:新建 `scripts/check_decoupling_imports.py`、`scripts/decouple_allowlist.md`;改 `scripts/check_decoupling.sh` R2/R3 段(委派 python,其餘不動)。
- 改法:
  - manifest(`decouple_allowlist.md`)本體=表格:module(完整路徑,六條)/allowed symbols(顯式列舉,由執行端 grep 現況 15 筆 import 蒐齊最小集;`run_locks`=`RunBusyError,is_run_active`)/module-level `import M` 准否(預設 deny)/owner/contract 一句(§C 六契約+run_locks FS 副作用註記);末尾 `## 戳記` 區(v2 格式)。
  - scanner(python):ast.parse 全部 `momentum/**/*.py`(R2,排除 tests/core/factories/contracts 同現行豁免語意)與 `api/{services,routes,websocket}/**/*.py`(R3);走訪所有 `Import`/`ImportFrom` 節點(任意縮排/同行多 alias 逐一檢);R2 同域判定沿現行語意(momentum/<pkg> vs import 目標 pkg);命中 momentum 目標 → 查 manifest:`ImportFrom` 逐 alias 驗 symbol ∈ allowed(拒 `*`);`import M` 須 module-import=allowed;違規列 檔:行:形式 並 exit 1。
  - **fail-closed 全譜**(codex ADV-6;r3 修矛盾):manifest 缺檔/0-byte/不可讀/僅註解/表為空/module 名非法/重複條目/owner 空/symbols 欄空/戳記驗證失敗 → 明確 stderr+exit 1。**條目數不 hardcode**:「==6」僅本票驗收值(T1b grep);新增第 7 條的防護=**戳記機檢**(body hash 變 → stamps 失效 → 紅),非計數。**scanner 每次執行先跑 `reconcile_stamps_check.sh` 驗 manifest 戳記+body hash;production CLI 無任何 bypass flag**(r3 依 codex 新 BLOCKING:移除 r2 的 `--skip-stamp-check`;測試路徑=直接呼叫 python 函式並注入 stub stamp-verifier,CLI 不可觸達)。
  - shell:R2/R3 段改為呼叫 python 腳本,exit code 傳遞;R1/R4-R7 原樣。
- 既有 caller:CI/人工;phase4 不碰。
- 驗證(r3):戳記前 `bash scripts/check_decoupling.sh` **紅且錯因=戳記驗證失敗**(fail-closed 實證);15→0 歸因由 Task 2 矩陣以注入 stub verifier 的函式呼叫驗證(對真實 repo 根實跑 scan 函式);戳記後(Task 3)全綠 exit 0;`python scripts/check_decoupling_imports.py --skip-stamp-check` → **exit ≠0(unknown option)**,永久測試釘死 CLI 無 bypass;manifest 條目數 `grep -cE "^\| momentum\." scripts/decouple_allowlist.md` == 6(SPEC/TODO 統一此一命令)。
- 邊界:(1) 同行 `import a, momentum.FeatureEngineering.feature_library` → 逐 alias 檢出紅(grok ADV-3);(2) `from momentum.FeatureEngineering import consumer_gate`(包層級形式)→ 語意=import 允許模組,**明文規格:等價於 `import …consumer_gate`,按 module-import 准否處理**(grok ADV-8);(3) 語法錯誤的 .py → 列檔名警告+exit 1(fail-closed,不靜默跳過)。
- 不可做:不放行 feature_library;不動 R1/R4-R7;不掃 api/models(follow-up 票);manifest 不用 regex 比對。

**Task 2 — 永久 scanner regression 測試矩陣(依賴:Task 1)**
- 目標:scanner 語義受永久測試釘死,退化即紅(取代 r1 一次性 canary;codex ADV-5/grok ADV-4)。檔案:新建 `tests/decoupling/test_import_scanner.py`(+`__init__.py`)。
- 改法:scanner python 模組提供可注入掃描根+**可注入 stamp-verifier**(測試用 stub;production CLI 固定用 reconcile_stamps_check,無 flag 可換);矩陣至少:①allowed module+allowed symbol → 綠;②allowed module+**非**allowed symbol(`RunLease`)→ 紅;③非 allowlist 模組(`feature_library`)from/import 兩形式 → 紅;④縮排矩陣 top-level/2-space/4-space/8-space/tab × from/import → 全紅;⑤同行多 alias → 紅;⑥near-miss `consumer_gate_v2`/`FeatureEngineeringXconsumer_gate` → 紅;⑦wildcard `from M import *` → 紅;⑧malformed manifest **全譜**(缺檔/0-byte/不可讀/僅註解/重複/module 名非法/owner 空/symbols 空)→ exit 1;⑨R2 同域 → 綠、跨域非白名單 → 紅;⑩**CLI 無 bypass**:`--skip-stamp-check` 等未知 flag → exit ≠0(r3 新增)。
- 驗證:`pytest tests/decoupling -q` 0 failed;mutation receipt(§V M1-M4)。
- 邊界:(1) fixture 用 tmp_path 不污染 production tree;(2) 測試不依賴真 manifest 內容(自帶 fixture manifest),另有一測驗真 manifest schema 有效。
- 不可做:禁 skip;禁鬆斷言;不得只測 shell 出口(直接測 python 模組)。

**Task 3 — manifest 戳記輪(依賴:Task 1 定稿)**
- 目標:manifest 獲 codex+composer v2 戳記,scanner 戳記驗證轉綠。主委派戳記輪(非本票執行端);執行端交付前 manifest 戳記區留空+scanner 此時預期紅=正確 fail-closed(receipt 記)。
- 驗證:戳記後 `bash scripts/reconcile_stamps_check.sh scripts/decouple_allowlist.md` PASS;`bash scripts/check_decoupling.sh` 全綠 exit 0。
- 邊界:(1) 戳記前 scanner 紅=設計正確(receipt 實跑證明);(2) 戳記後改 manifest 一字 → scanner 紅(mutation receipt)。
- 不可做:主委不得自寫戳記。

**Task 4 — ARCH pointer+現況表修正(依賴:Task 1)**
- 目標:docs 與機讀單源一致+修過時計數。檔案:`docs/ARCHITECTURE.md` 解耦節。
- 改法:①加 ≤15 行:機制/唯一權威=`scripts/decouple_allowlist.md`/六模組豁免語意(不抄清單)/出處 RECONCILE/治理=戳記機檢(scanner 內建);②現況表 R3=12 → 修為白名單放行後語意(15 筆豁免+R4 已修,出處 DECOUPLE-FIX4);③標明 api/models 未掃=已知缺口(follow-up 票)。
- 驗證:`bash scripts/check_doc_anchors.sh` New dead links 0;`grep -c "decouple_allowlist" docs/ARCHITECTURE.md` ≥1;FF H2 節零 diff。
- 邊界:(1) 不複製六模組清單;(2) 既有錨句不刪。
- 不可做:不動其他節/DEV_GUIDE。

## §V 驗證策略與邊界測試目錄
- **mutation(4 個,實跑 receipt 後還原)**:M1=排除改 substring 比對 → 測試⑥必 FAIL;M2=只掃 top-level(跳過縮排節點)→ 測試④必 FAIL;M3=manifest 驗證跳過(缺檔回綠)→ 測試⑧必 FAIL;M4=symbol 檢查移除(module 全放行)→ 測試②必 FAIL。
- 一次性 canary(輔助,非唯一 gate):交付時 api/services/ 放 `_allowlist_canary.py`(feature_library from+import 兩形式)→ scanner 紅;刪 → 綠;stdout 貼 `handoffs/DECOUPLE-ALLOWLIST-RECEIPT.md`+15→0 逐筆歸因表。
- 防假綠:review 方逐行審 AST 走訪邏輯;15→0 歸因表逐筆對 manifest 條目。
- 測試層級:單元(矩陣)/整合(scanner 全跑)/邊界(malformed)。獨立 pytest。

## §R 回退
- 4 Task 獨立 commit;revert scanner commit 即回 grep 舊行為;manifest 無 runtime 依賴。戳記機制 revert=回 r1 前狀態,零數據風險。

## §N N/A 登記
- §G:N/A — RISK-HIT 僅 b,零數值變更;可證偽性由 §V 永久矩陣+4 mutation 承擔。
- §V 邊界目錄之全NaN/Inf/std=0/並發/OOM/浮點:N/A — 純工具/測試/文件。
- api/models R3 覆蓋:N/A 於本票 — 已知缺口,擴根=新紅字需 triage,立 follow-up 小票(§C 範圍誠實條款)。
