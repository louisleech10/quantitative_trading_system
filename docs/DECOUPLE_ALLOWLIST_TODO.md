# DECOUPLE-ALLOWLIST TODO　(v2 / DRAFT / 基於 docs/DECOUPLE_ALLOWLIST_SPEC.md r2 / 2026-07-14;r1 依三家 9 BLOCKING/14 MAJOR 重寫:AST+戳記機檢)

## 階段 1 SPEC 索引(100% 覆蓋追溯)
| ID | SPEC 原文節錄(≤30字) | 本檔位置 |
|---|---|---|
| Task 1 | 「AST import 掃描器+機讀 manifest」 | Task 1.1 |
| Task 2 | 「永久 scanner regression 測試矩陣」 | Task 1.2 |
| Task 3 | 「manifest 戳記輪」 | Task 1.3(主委輪,執行端只留空戳記區+紅 receipt) |
| Task 4 | 「ARCH pointer+現況表修正」 | Task 1.4 |
| 矩陣①-⑩ | 「allowed/deny/縮排/同行/near-miss/wildcard/malformed 八型/R2 同域/CLI 拒 bypass」 | Task 1.2 |
| M1-M4 | 「substring/top-level/manifest 跳過/symbol 移除」mutation | Phase 測試 |
| V-CANARY | 「一次性 canary(輔助)+15→0 歸因表」 | Task 1.1 receipt |
| T1a-d/T2a/T4a-c | 驗證命令(含 T1d=CLI 拒 bypass) | 各 Task |
- 合計:4 Task、測試矩陣 10 類(⑩=CLI 拒 bypass)、mutation 4、驗證 ID 8(T1a-d/T2a/T4a-c)、receipt 義務 2(canary+戳記前紅證)。RISK-HIT: b。

## §0 全域規則與約束(執行端讀完即可遵守;r2 依 ADV-CODEX-7 補七條矩陣)
- **解耦 7 條 canonical(CLAUDE.md)本票適用矩陣**:R1 momentum不import api——不碰,規則仍適用;**R2 跨域走Protocol——本票把裁決豁免機制化(AST 掃描)**;**R3 api走factory——同左**;R4 服務不互import——scanner 邏輯不動(已 0);R5 config 單源——不碰;R6 測試獨立 pytest——新測試全獨立;R7 DTO 不跨界——不碰。named Rule 8(singleton 殘留)/Rule 9(callback bypass,phase4「Rule 6」語意)——本票不動其檢查,不得宣稱涵蓋。
- **比對紀律**:module 名字串 equality(先過 `^momentum(\.[A-Za-z_][A-Za-z0-9_]*)+$`);禁把 module 名插 regex;symbol 顯式列舉,拒 `*`;`import M` 預設 deny。
- **治理紀律**:manifest 改動=戳記失效=scanner 紅(機器強制);主委才可派戳記輪;執行端交付時戳記區留空。
- 防假綠:15→0 逐筆歸因表;矩陣測試禁 skip/鬆斷言;不得只測 shell 出口。
- 兩輪斷路器:卡 2 輪停手。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | Task 1.1→1.2→1.4 | 依序 | 一次派工,各自獨立 commit;1.3=主委戳記輪不在此批 | 中 |

- B1 驗收 Gate:T1a-d/T2a/T4a-c+矩陣 10 類+M1-M4 receipt+canary receipt+「戳記前 scanner 紅」receipt;`pytest tests/decoupling tests/api tests/momentum -q` 無新紅。
- B1 後主委跑 Task 1.3 戳記輪 → scanner 轉綠 → 全票收尾。
- 派工 prompt:「讀 docs/DECOUPLE_ALLOWLIST_TODO.md §0+Task 1.1/1.2/1.4(冷啟動自足),依序實作+自跑驗證+receipt(handoffs/DECOUPLE-ALLOWLIST-RECEIPT.md);不跑 git commit(主委代);結構化收尾。」

## Phase 1 — 白名單機制(完成後:R2/R3 AST 掃描全形式覆蓋,manifest 受戳記機檢,scanner 可入 CI)

### Task 1.1 — AST 掃描器+manifest(SPEC ref:Task 1)
- 輸入/輸出:輸入=RECONCILE 六模組+現況 15 筆(先 `bash scripts/check_decoupling.sh` 實跑抄錄);輸出=`scripts/check_decoupling_imports.py`+`scripts/decouple_allowlist.md`+改造 `scripts/check_decoupling.sh` R2/R3 段。
- 實作要點:
  1. **manifest**(`scripts/decouple_allowlist.md`):本體=Markdown 表,欄=module/allowed_symbols(逗號列舉)/module_import(allow|deny)/owner/contract 一句。六列:`momentum.FeatureEngineering.atomic.warmup_lookup`(symbols=由現況 import 蒐齊,如 `get_warmup_bars,…`;contract=行為凍結·資料品質政策)、`…consumer_gate`(三語意 browse=open/strict=closed/cache-reuse=closed)、`…feature_reader`(L7 解碼=正確性面)、`…run_locks`(**symbols 僅 `RunBusyError,is_run_active`;RunLease 禁**;單寫者+probe FS 副作用)、`…run_paths`(layout 凍結)、`…utils.hardware_utils`(FF tier policy,package 錯位 P3)。owner 全填 `committee/DECOUPLE-TRIAGE`。**allowed_symbols 蒐集法**:對 15 筆現況違規行逐筆抄 import 的 symbol,聯集=最小集,receipt 附對照。末尾 `## 戳記` 區(留空,附 v2 格式註解)。
  2. **scanner**(`check_decoupling_imports.py`):`ast.parse` 走訪;掃描根可注入(`scan(momentum_root, api_roots, manifest_path)`,CLI 預設 repo 實根);R2=`momentum/<pkg>/**`(排除 tests/、core、factories、contracts 同現行語意)內 import `momentum.<other_pkg>.*`;R3=`api/{services,routes,websocket}/**` 內 import `momentum.*`(排除 `momentum.core.*`/`momentum.factories` 同現行豁免);對命中:`ImportFrom` 逐 alias 驗 symbol ∈ manifest allowed(拒 `*`;`from momentum.FeatureEngineering import consumer_gate` 包層級形式=等價 module import,按 module_import 欄處理);`Import` 節點按 module_import 欄;違規印 `檔:行:形式:目標` exit 1。
  3. **fail-closed 全譜**(r3):manifest 缺檔/0-byte/不可讀/僅註解/表為空/module 名非法/重複/owner 或 symbols 欄空 → stderr 明確+exit 1;**條目數不 hardcode**(「6」僅本票 T1b 驗收;第 7 條防護=戳記 hash 失效);**執行開頭先 `subprocess` 跑 `bash scripts/reconcile_stamps_check.sh scripts/decouple_allowlist.md`,非 0 → exit 1**;**CLI 無任何 bypass flag**(argparse 不定義;測試以直接函式呼叫+注入 stub stamp-verifier 進行);語法錯 .py → 警告+exit 1。
  4. **shell 委派**:`check_decoupling.sh` R2/R3 段替換為呼叫 python(venv python,找不到 fallback python3);其餘段原樣。
- 修改檔案:新建 2 檔+`scripts/check_decoupling.sh`(僅 R2/R3 段)。既有 caller:CI/人工;phase4 不碰。
- 不可做:不放行 feature_library;不掃 api/models;不動 R1/R4-R7 段;不用 regex 比對 module;FF 表不含第 7 模組(新揭露 3 筆放**第二表 pending triage**,見 SPEC §C r4 增補;symbol 由該 5 行實際 import 蒐齊:`PerformanceMetrics`/`strategy_registry`/`ParetoAnalyzer`)。
- 邊界:(1) 同行多 alias `import os, momentum.FeatureEngineering.feature_library` → 紅;(2) 語法錯誤檔 → exit 1 非跳過;(3) 戳記區空 → scanner 紅(此階段=預期,receipt 記)。
- 風險緩解:矩陣+M1-M4+canary。
- 驗證(r3):**T1a** 戳記前 `bash scripts/check_decoupling.sh` 紅且錯因=戳記驗證失敗(receipt 貼 stdout);**T1b** `grep -cE "^\| momentum\." scripts/decouple_allowlist.md` 輸出 `9`(FF 表 6+pending 表 3,r4 增補);**T1c** 以 python 直接呼叫 `scan(...)`(注入 stub stamp-verifier)對真實 repo 根實跑 → R2=0/R3=0,15 筆歸因表入 receipt(命令+stdout 全貼;此路徑僅存在於函式層,CLI 不可觸達);**T1d** `python scripts/check_decoupling_imports.py --skip-stamp-check` → exit ≠0(unknown option,證 CLI 無 bypass);**V-CANARY** 以同 T1c 函式呼叫,api/services/ 放 `_allowlist_canary.py`(from+import feature_library 兩形式)→ 兩形式各列紅;刪→綠;stdout 入 receipt。

### Task 1.2 — 永久 regression 矩陣(SPEC ref:Task 2;依賴 1.1)
- 輸入/輸出:輸入=scanner 模組;輸出=`tests/decoupling/test_import_scanner.py`+`tests/decoupling/__init__.py`。
- 實作要點(r3):①tmp_path 建 fixture tree+fixture manifest(自帶,allowed module `momentum.B.util` symbols=`ok_fn`),**注入 stub stamp-verifier**;②矩陣 10 類(SPEC Task 2 ①-⑩ 逐項一測試函式,含縮排 top/2sp/4sp/8sp/tab × from/import 參數化、near-miss 兩型、wildcard、malformed **全譜八型**(缺檔/0-byte/不可讀/僅註解/重複/module 非法/owner 空/symbols 空)、R2 同域綠/跨域紅、**⑩CLI 拒 `--skip-stamp-check` 等未知 flag(subprocess 一測,exit ≠0)**);③另一測試驗**真** manifest schema(欄齊/module 名合法/無重複;不釘條目數,計數歸 T1b),直接函式呼叫;④除⑩外全部直接 import scanner 函式,不 shell out。
- 修改檔案:新建上列 2 檔。
- 不可做:禁 skip;禁 `>=` 鬆斷言;不污染 production tree。
- 邊界:(1) fixture manifest 與真 manifest 隔離;(2) 平台換行差異由 bytes/文字一致處理(測試自建檔)。
- 風險緩解:M1-M4。
- 驗證:**T2a** `pytest tests/decoupling -q` 0 failed;**M1-M4**(receipt):M1 改 substring 比對→⑥FAIL;M2 跳縮排節點→④FAIL;M3 缺 manifest 回綠→⑧FAIL;M4 移除 symbol 檢查→②FAIL;各還原後全綠,stdout 入 receipt。

### Task 1.3 — manifest 戳記輪(主委執行;依賴 B1 驗收)
- 主委派 codex+composer 審 manifest 本體(六條/symbol 集/契約與 RECONCILE 一致)並 append v2 戳記。
- 不可做:主委不得自寫戳記;戳記前不得宣稱本票完成。
- 邊界:(1) 任一家 REJECTED → 修 manifest 重戳,scanner 維持紅;(2) 戳記後改 manifest 一字 → scanner 必紅(mutation 實跑後還原)。
- 驗證:`bash scripts/reconcile_stamps_check.sh scripts/decouple_allowlist.md` PASS;`bash scripts/check_decoupling.sh` 全綠 exit 0;篡改 mutation receipt(紅→還原→綠)。

### Task 1.4 — ARCH pointer+現況表(SPEC ref:Task 4;依賴 1.1)
- 輸入/輸出:輸入=定稿機制;輸出=ARCH 解耦節 ≤15 行增補+現況表修正。
- 實作要點:①機制段:唯一權威=`scripts/decouple_allowlist.md`、六模組豁免語意摘要(不抄表)、出處 RECONCILE、治理=戳記機檢內建 scanner;②現況表:R3=12 過時 → 改「R2/R3 白名單放行後 0(15 筆豁免,出處 DECOUPLE-TRIAGE);R4=0(DECOUPLE-FIX4 已修)」;③標 api/models 未掃=已知缺口(follow-up)。
- 修改檔案:`docs/ARCHITECTURE.md` 解耦節。
- 不可做:不抄六模組清單;不刪錨句;不動 FF H2/其他節/DEV_GUIDE。
- 邊界:(1) anchor checker 紅→修連結非刪錨;(2) 增行 ≤15。
- 風險緩解:⊘。
- 驗證:**T4a** `bash scripts/check_doc_anchors.sh` New dead links 0;**T4b** `grep -c "decouple_allowlist" docs/ARCHITECTURE.md` ≥1;**T4c** `git diff docs/ARCHITECTURE.md | grep -c "R3=12"` ≥1(舊數被改掉)且 FF H2 節零 diff。

### Phase 1 測試 + Phase Gate
- 單元:矩陣 10 類。整合:scanner 全跑(戳記前紅/戳記後綠兩態都留 receipt)。邊界:malformed 全譜八型。效能:⊘。
- mutation:M1-M4(上列)。
- Phase Gate:T1a-d/T2a/T4a-c+矩陣 10 類+M1-M4+canary 全 PASS;`pytest tests/decoupling tests/api tests/momentum -q` 無新紅(inventory 慣例 revert);Task 1.3 戳記後 scanner 全綠 exit 0。

## 階段 3 自檢(0 FAIL)
- 追溯:4 Task/矩陣 10/mutation 4/驗證 8/receipt 2 全對應 ✓。深度:要點≥3+函式簽名(`scan(...)`)/檔案到位/邊界≥2/驗證可證偽 ✓;新測試檔在修改檔案清單 ✓。語義:1.2 依賴 1.1、1.3 依賴 B1、無 forward dependency;CLI 無 bypass flag(矩陣⑩+T1d 釘死),測試注入僅函式層 ✓。全棧:純工具,⋅跳過。錨點:§0/§B/驗證·邊界·不可做 ✓。
- ⚠️ 矛盾檢查(r3 已消解):scanner **不 hardcode 條目數**(schema 只驗欄齊/合法/唯一);「==6」僅 T1b 本票驗收 grep;新增條目的防護=戳記 hash 失效 → scanner 紅(SPEC/TODO 兩處已同語意,codex ADV-6 矛盾關閉)。
## 階段 4 Frozen 前 handoff
SPEC=docs/DECOUPLE_ALLOWLIST_SPEC.md TODO=docs/DECOUPLE_ALLOWLIST_TODO.md FOCUS=已閉合
狀態:**Frozen**(2026-07-14:grok/composer r2 FROZEN-OK;codex r3 揪 --skip-stamp-check 過寬+計數矛盾 → r3/r4 修齊後 codex FROZEN-OK;見 handoffs/DECOUPLE-ALLOWLIST-ADV-{CODEX,COMPOSER,GROK}.md)
