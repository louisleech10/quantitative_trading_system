# TEMPLATE_GATE_FIX TODO　（版本 3／狀態 **Frozen**（雙家族 adversarial 兩輪＋雙戳記 APPROVED，見 handoffs/2026-07-04-TGF-TODO-ADV-RECONCILE.md）／基於 docs/TEMPLATE_GATE_FIX_SPEC.md v3＋docs/TEMPLATE_GATE_FIX_MANIFEST.md 29 ID／2026-07-05）

> 生成聲明（供 adversarial 審）：憲法讀取＝`.github/copilot-instructions.md` 全文＋CLAUDE.md 協作協議三節；ARCHITECTURE/DEVELOPMENT_GUIDE 未全讀（偏離現行 prompt「無條件讀」）——理由：本 epic 僅觸 `scripts/*.sh`、`templates/*.md`、治理文件，零 momentum/api 程式碼。此偏離即本 epic [E-1] 要制度化的行為。
> WAIVER: TODO_GEN_STAGE0_DEVIATION — 本 epic 範圍排除 momentum/api/frontend/data_cache，補償控制＝SPEC §C＋TODO §0 紅線枚舉＋雙家族 adversarial；此 waiver 由 TODO 輪 reconcile 雙戳記核可後生效（ADV-CODEX-9）。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **只加強機檢，不得放寬任何既有檢查**（need/hollow/facts-resolved 全保留）。
- **本 epic 適用之解耦/紅線子集**（[E-3] 完整清單見 AGENTS.md）：①不碰 momentum/、api/、frontend/、data_cache/（越界寫入即違規——含解耦規則 #1「momentum 不 import api」與 #6「測試不依賴 run_api.py」之保護面）；②禁 fake 資料/合成結果冒充實測（EXPECTED 先驗手填、BASELINE 實測）；③不弱化 NaN·inf gate 與任何既有品質檢查（本 epic 對機檢的修改只允許加嚴）；④factories.py／protocols.py 等共用程式路徑不在範圍，碰到即停（規模膨脹訊號）。
- `.claude/gate/audit.log` 為 append-only 稽核檔，**任何 Task 不得修改**。
- gate.sh 是所有派工的守門：**每次改 gate.sh/template_check.sh 後，立即實跑一次真 gate 與 `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md`（預期 exit 0）**，破壞即 revert 該 commit。
- 防假綠：`tests/gate_fixtures/EXPECTED.txt` 由 SPEC §G 先驗手填，**禁止跑完回填**；不得刪改既有測試斷言。
- Shell 風格：跟隨 template_check.sh 現行寫法（`set -u`、awk/grep、繁中訊息、誠實邊界註解）。
- Git：每 Phase 獨立 commit，訊息用 `feat(gate):`/`fix(gate):`/`docs:`/`test(gate):` 前綴。
- 卡關 ≤2 輪未解 → 輸出 `STATUS: BLOCKED — <問題>` 停下，不硬猜（斷路器）。

## §B 批次執行策略（依賴拓撲 → 最少批次，每批=一次派工 prompt）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1, 1.2 | 無 | 同屬 fixture/baseline，互相引用 | 中 |
| B2 | 2.1, 2.2, 2.3, 2.4 | B1 | 全在 template_check.sh 單檔，一次改完跑矩陣 | 中 |
| B3 | 3.1, 3.2, 4.1, 5.1 | B2（教學須對齊定稿規則） | 三個 template 檔互不重疊，無共檔衝突 | 中 |
| B4 | 6.1, 6.2 | B2（矩陣綠）；可先行僅限 6.2 之 [D-3] 舊錨點替換，[F-3] 盤點必須在 B2 後 | gate.sh＋治理文件＋盤點收尾 | 中 |

- 批次間 Gate：B1→B2 gate＝`bash scripts/test_template_check.sh --freeze` 產出 13 行 BASELINE 且預設模式 exit 1（繞過探針未擋=可證偽起點）；B2→B3 gate＝`bash scripts/test_template_check.sh; echo $?` = 0 **且** `for id in A-1 A-3 A-4 A-5; do bash scripts/test_template_check.sh --mutate $id || exit 1; done; echo $?` = 0（--mutate 語義見 Task 1.2：套用 MUTATION.txt 破壞 → 矩陣須轉紅 → 自動還原 → `git diff --exit-code scripts/template_check.sh` 淨）；B3→B4 gate＝Task 3.1/3.2/4.1/5.1 的全部 grep 斷言通過；B4 完成 gate＝gate fixture 拒/拒/拒/拒/發（5 例，見 Task 6.1）＋舊錨點 grep=0＋真 gate 實跑 exit 0。
- B1 派工 prompt：「讀 docs/TEMPLATE_GATE_FIX_TODO.md §0 與 Phase 1，完成 Task 1.1/1.2，產出 13 fixture＋test_template_check.sh＋EXPECTED.txt（依 SPEC §G 手填）＋BASELINE_BEFORE.txt，收尾依 templates/RESULT_TEMPLATE.md 寫 handoffs/TGF-B1-RESULT.md」。
- B2 派工 prompt：「讀 §0 與 Phase 2，改 scripts/template_check.sh 完成 Task 2.1–2.4，驗收=test_template_check 矩陣全綠＋4 mutation 轉紅＋本 SPEC 自檢 exit 0，收尾同上寫 TGF-B2-RESULT.md」。
- B3 派工 prompt：「讀 §0 與 Phase 3/4/5，改三個 template 檔完成 Task 3.1/3.2/4.1/5.1，驗收=各 Task grep 斷言，收尾寫 TGF-B3-RESULT.md」。
- B4 派工 prompt：「讀 §0 與 Phase 6，改 gate.sh＋治理文件完成 Task 6.1/6.2，驗收=gate fixture 5 例（exit 1/1/1/1/0）＋舊錨點=0＋真 gate 實跑，收尾寫 TGF-B4-RESULT.md」。

## Phase 1 — 探針固化與 baseline（目標：把繞過證據變永久 fixture；完成後系統有 13 fixture＋可證偽矩陣工具）

### Task 1.1 — [F-1][F-2] fixture 重建與正負樣本庫
- SPEC ref：Task 1.1　目標：13 個 fixture 入 repo 固化繞過/誤擋/合規證據
- 輸入/輸出：兩份 adversarial 檔內嵌探針原文（handoffs/2026-07-04-TGF-SPEC-ADV-{codex,composer}.md）→ `tests/gate_fixtures/` 13 個 .md＋`POSITIVE_SAMPLES.txt`
- 實作要點：①負樣本 7：`spec_verified_bypass.md`、`spec_heading_verified_bypass.md`（標題含「已驗證」、事實在下層 bullet，照 ADV-CODEX-1 VERIFY 區塊原文）、`spec_ic_phase0_style.md`（`### 已驗證事實` 標題＋bullet 含 DatetimeIndex/int64 而行內無關鍵詞）、`spec_highrisk_no_g.md`（`RISK-HIT: a,d`＋§N 寫 §G N/A）、`todo_bad.md`（末 Task 缺三欄）、`result_pass_empty_receipts.md`（RUNTIME_CHECK=PASS＋RECEIPTS=[]）、`result_notrun_done_operational.md`（NOT_RUN＋discussion 外 DONE）；②維持 FAIL 1：`spec_pending_unresolved.md`；③正樣本 5：`spec_good_full.md`（FACT-RECEIPT＋RISK-HIT: b,c＋真 §G＋全錨點）、`todo_good_full.md`、`spec_pending_none_variant.md`（「待使用者確認：本任務無」）、`spec_risk_false_positive.md`（含「參見 (a) 原則」「| (a) | 否 |」干擾句＋RISK-HIT: none）、`result_notrun_done_in_discussion.md`（DONE 僅在 claim-context: discussion 內）；④統一 LF 無 BOM。
- 修改檔案：全新建 `tests/gate_fixtures/*.md`＋`POSITIVE_SAMPLES.txt`（列 docs/TEMPLATE_GATE_FIX_SPEC.md 等現役合規文件路徑）。既有 caller：無（新建）。
- 不可做：不得修改 scripts/template_check.sh（本 Phase 只固化現狀）；不得把探針寫成修後才 FAIL 的「預期版」——必須重現**現行**繞過。
- 邊界：fixture 無 `## §A` 段時 W1 整段跳過不誤炸（spec_highrisk_no_g 即此型）；CRLF/BOM 混入會使 grep 錨點失效（存檔後 `file tests/gate_fixtures/*.md` 確認 ASCII/UTF-8 text）。
- 風險緩解：[F-1][F-2]
- 驗證：`bash scripts/template_check.sh spec tests/gate_fixtures/spec_verified_bypass.md; echo $?` 印 0（重現繞過）；`ls tests/gate_fixtures/*.md | wc -l` == 13；`bash scripts/template_check.sh spec tests/gate_fixtures/spec_pending_unresolved.md; echo $?` 印 1。

### Task 1.2 — [F-4] 一鍵驗證器＋§G baseline 凍結
- SPEC ref：Task 1.2　目標：矩陣工具＋EXPECTED（先驗）＋BASELINE_BEFORE（實測）
- 輸入/輸出：Task 1.1 的 13 fixture → `scripts/test_template_check.sh`＋`tests/gate_fixtures/{EXPECTED.txt,BASELINE_BEFORE.txt,MUTATION.txt}`
- 實作要點：①kind 由檔名前綴判定（spec_*/todo_*/result_*）；②迴圈 `bash scripts/template_check.sh <kind> <f>`，輸出 CSV `<fixture>,<kind>,<exit>`；③`--freeze` 寫 BASELINE_BEFORE.txt，預設模式 `diff EXPECTED.txt <當次結果>`，diff 非空 → exit 1；④空 fixture 目錄 → exit 2＋ERROR 訊息；⑤EXPECTED.txt 依 SPEC §G 手填：7 繞過探針=1、pending=1、5 正樣本=0（13 行）；⑥MUTATION.txt 格式 `<id>|<sed 破壞命令（單字元級，作用於 scripts/template_check.sh）>`（4 條 A-* 各一列，破壞命令由 B2 填實）；⑦**`--mutate <id>` 模式（ADV-CODEX-8／ADV-COMPOSER-20 契約）**：套用該列 sed 破壞 → 跑矩陣，預期 exit 非 0（轉紅）→ `git checkout -- scripts/template_check.sh` 還原 → 重跑矩陣須綠 → `git diff --exit-code scripts/template_check.sh` 確認淨；全序列成立 → `--mutate` exit 0，任一步不成立 → exit 1＋點名步驟。
- 修改檔案：全新建。既有 caller：無。
- 不可做：EXPECTED 不得由跑當下結果生成（恆真測試）；不得吞 template_check 的 stderr。
- 邊界：fixture 檔名含空格（引號包覆變數）；EXPECTED 與 fixture 數不一致 → 明確 FAIL 訊息列缺漏檔名。
- 風險緩解：[F-4]
- 驗證：`bash scripts/test_template_check.sh --freeze && wc -l < tests/gate_fixtures/BASELINE_BEFORE.txt` 印 13；`bash scripts/test_template_check.sh; echo $?` 印 1（修前預期紅=Phase 2 可證偽起點）；`wc -l < tests/gate_fixtures/EXPECTED.txt` 印 13。

## Phase 2 — 機檢硬化（目標：template_check.sh 堵 U1/U2/U3/RESULT 洞；完成後矩陣全綠＋mutation 全轉紅）

### Task 2.1 — [A-1][A-2] §A 段級狀態機與防標籤繞過
- SPEC ref：Task 2.1　目標：fact-scope 內資料結構行強制 FACT-RECEIPT；facts-resolved 防「已確認結果：待回覆」
- 輸入/輸出：現行 W1 段 → 段級狀態機版；矩陣中 3 個 §A 類探針轉 1
- 實作要點：①awk 狀態機偽碼：`in_secA && /已驗證事實|已確認/ 子段標題(-|###|\*\*) → fact_scope=1；遇下一同級子段標題 → fact_scope=0；fact_scope && 行含資料結構 token（沿用現行清單）&& 前/本/後行無 FACT-RECEIPT: → 記缺失`；②facts-resolved：「已確認」行須含 `[0-9]{4}-[0-9]{2}-[0-9]{2}` 或「使用者」，且行含 `待回覆|未確認|無法確認` → 不算已確認；③FAIL 訊息點名缺 receipt 的行內容。
- 修改檔案：`scripts/template_check.sh` spec 分支 W1 段（sec_a 迴圈區塊）。既有 caller：gate.sh、test_template_check.sh。
- 不可做：不得要求非資料結構行附 FACT-RECEIPT；不得動 result/todo 分支；不得改 token 清單語意（只沿用）。
- 邊界：§A 純設計敘述（無 token）不觸發；「已確認」在 §A 外章節不觸發 facts-resolved；fact-scope 內含 `handoffs/`、`.md` 路徑而無型別斷言的引用行不觸發。
- 風險緩解：[A-1][A-2]
- 驗證：spec_verified_bypass、spec_heading_verified_bypass、spec_ic_phase0_style 三者 exit 轉 1 且輸出點名行；spec_good_full 維持 0；mutation（A-1 破壞命令填入 MUTATION.txt 後）：`bash scripts/test_template_check.sh --mutate A-1; echo $?` 印 0。

### Task 2.2 — [A-3] RISK-HIT 結構化宣告制
- SPEC ref：Task 2.2　目標：§RISK 宣告行驅動 §G 強制，零 NLP 誤擋
- 輸入/輸出：現行 §G need_or → 宣告制；spec_highrisk_no_g 轉 1、spec_risk_false_positive 維持 0
- 實作要點：①awk 抽 §RISK 段第一個 `RISK-HIT:` 行（允許 `a, d` 空白變體，重複行取第一並 echo WARN）；②無宣告行 → FAIL（訊息教補 `RISK-HIT: <a,b,c,d 子集|none>`）；③值含 a 或 d → 要求 `## §G` 存在＋§G 段含 `atol|rtol|sha256` 任一（exit/== 不算）＋§N 內 `§G.*N/A` 出現 → FAIL；④值不含 a/d → 維持現行 need_or。
- 修改檔案：`scripts/template_check.sh` spec 分支 §G 檢查段。既有 caller：同上。
- 不可做：不得對 b/c 強制 §G；不得用散文關鍵詞推斷（ADV-COMPOSER-4 已實證誤擋）。
- 邊界：`RISK-HIT: none` 合法；宣告行在 §RISK 外出現不採計；docs/TEMPLATE_GATE_FIX_SPEC.md 自身（RISK-HIT: b,c＋自願 §G）維持 exit 0。
- 風險緩解：[A-3]
- 驗證：spec_highrisk_no_g exit 轉 1；spec_risk_false_positive 維持 0；`bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md; echo $?` 印 0；mutation：`bash scripts/test_template_check.sh --mutate A-3; echo $?` 印 0。

### Task 2.3 — [A-4] TODO per-Task 分段檢查
- SPEC ref：Task 2.3　目標：每個 `### Task` 塊獨立驗三欄
- 輸入/輸出：現行全域 need → 分段 awk；todo_bad 轉 1
- 實作要點：①awk 以 `^### Task` 為塊界（最末塊至 EOF）；②每塊 grep 驗證/邊界/不可做，缺欄記「Task 標題＋缺欄名」；③零個 `### Task` 維持既有 `need "### Task"` FAIL。
- 修改檔案：`scripts/template_check.sh` todo 分支。既有 caller：同上。
- 不可做：不得要求三欄以外欄位（實作要點/SPEC ref 等交 adversarial 語義層）。
- 邊界：Task 標題含 `/`、`[]` 特殊字元（awk 塊界用行首錨定非內容匹配）；最末 Task 到 EOF。
- 風險緩解：[A-4]
- 驗證：todo_bad exit 轉 1 且輸出含缺欄 Task 標題；todo_good_full 與本 TODO 自身 `bash scripts/template_check.sh todo docs/TEMPLATE_GATE_FIX_TODO.md; echo $?` 印 0；mutation：`bash scripts/test_template_check.sh --mutate A-4; echo $?` 印 0。

### Task 2.4 — [A-5][A-6] RESULT 交叉規則＋待確認 regex
- SPEC ref：Task 2.4　目標：RUNTIME PASS⇒RECEIPTS 非空、NOT_RUN⇒禁 DONE 極性、誠實變體不誤擋
- 輸入/輸出：result 分支＋facts-resolved regex → 3 result fixture 按預期翻轉、spec_pending_none_variant 轉 0
- 實作要點：①RUNTIME_CHECK=PASS 且 RECEIPTS 為 `[]`/`[ ]`/`[" "]` 類空值 → FAIL；②MUTATION_CHECK=NOT_RUN 時，掃 `claim-context: discussion` 標記區塊**之外**的 `已驗|DONE|全綠` → FAIL（反引號 code span 內豁免）；③spec 分支 facts-resolved regex 增列 `待[^：:]*確認[^：:]*[：:].*任務無` 類變體，以 spec_pending_none_variant 轉 0 為準。
- 修改檔案：`scripts/template_check.sh` result 分支＋spec 分支 regex。既有 caller：同上。
- 不可做：不得解析 JSON 全語法（字串級＋誠實邊界註明）；不得放寬 RECEIPTS 既有 presence 檢查。
- 邊界：RECEIPTS 多行值（僅檢同行，註明邊界）；DONE 出現在 RECHECK 命令引用（code span 豁免）。
- 風險緩解：[A-5][A-6]
- 驗證：result_pass_empty_receipts、result_notrun_done_operational exit 轉 1；result_notrun_done_in_discussion 維持 0；spec_pending_none_variant exit 轉 0；mutation：`bash scripts/test_template_check.sh --mutate A-5; echo $?` 印 0；Phase 2 收尾跑 `bash scripts/test_template_check.sh; echo $?` 印 0（全矩陣綠）＋B2→B3 gate 之 4 mutation 迴圈整體 exit 0。

## Phase 3 — SPEC 範本更新（目標：範本教會機檢實際要求；完成後照範本填=過機檢）

### Task 3.1 — [B-1][B-2][B-5] §A 教學、RISK-HIT 宣告與頭注
- SPEC ref：Task 3.1　目標：FACT-RECEIPT 格式＋RISK-HIT 教學＋頭注刪除指示入範本
- 輸入/輸出：templates/SPEC_TEMPLATE.md → 教學版；spec_good_full 同步更新後仍 0
- 實作要點：①§RISK 加 `RISK-HIT: <a,b,c,d 子集|none>` 教學行（含「機檢依據，缺行 FAIL」）；②§A 加格式行 `FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`＋一個實例；③教「待確認：無」精確寫法＋「已確認結果：YYYY-MM-DD 使用者…」結構；④頭注末行加「複製為 SPEC 後刪除本 HTML 註解」。
- 修改檔案：`templates/SPEC_TEMPLATE.md` §RISK/§A 段＋頭部註解。既有 caller：所有未來 SPEC 作者＋gate --template-opened。
- 不可做：不得增加新 `## §` 錨點；不得為讓範本自身過機檢而弱化樣板殘留檢查（範本自身 FAIL 屬預期）。
- 邊界：範本含雙大括號占位符跑機檢預期 exit 1（正常）；教學範例行本身不得含未附 receipt 的資料結構斷言（避免示範即違規）。
- 風險緩解：[B-1][B-2][B-5]
- 驗證：`grep -c "FACT-RECEIPT" templates/SPEC_TEMPLATE.md` ≥ 2；`grep -c "RISK-HIT" templates/SPEC_TEMPLATE.md` ≥ 1；`grep -c "刪除本 HTML 註解" templates/SPEC_TEMPLATE.md` = 1；spec_good_full 依新範本更新後 `bash scripts/template_check.sh spec tests/gate_fixtures/spec_good_full.md; echo $?` 印 0。

### Task 3.2 — [B-3][B-4] §G 三方簽核子條款與 §V 章程掛鉤
- SPEC ref：Task 3.2　目標：制度鐵律下沉範本
- 輸入/輸出：templates/SPEC_TEMPLATE.md §G/§V → 條件子條款版
- 實作要點：①§G 加條件行「涉 feature/kline 生成/計算/merge/split/洩漏 → 真實 `data_cache/feature_klines/kline_cache.h5`＋三方簽核計畫必填，禁合成 fixture；不適用即略過」；②§V 加條件行「RISK-HIT 含 a/d 或測試宣稱驗正確性 → 附可證偽/mutation 設計（引 docs/TEST_DESIGN_CHARTER.md），否則 §N 標 mutation N/A＋理由」。
- 修改檔案：`templates/SPEC_TEMPLATE.md` §G、§V 段。既有 caller：同 3.1。
- 不可做：不得把三方簽核寫成機檢錨點（流程義務，gate --review-role 已覆蓋）。
- 邊界：非 feature 任務讀 §G 子條款有明確「不適用即略過」措辭；範本行數增幅 ≤ 12 行（詳見下方驗證欄）。
- 風險緩解：[B-3][B-4]
- 驗證：`grep -c "kline_cache.h5" templates/SPEC_TEMPLATE.md` = 1；`grep -c "TEST_DESIGN_CHARTER" templates/SPEC_TEMPLATE.md` = 1；行數增幅（ADV-CODEX-7／ADV-COMPOSER-22 修正，基線凍結 60）：`before=60; after=$(wc -l < templates/SPEC_TEMPLATE.md); test $((after-before)) -le 13 && echo DELTA_OK`（≤12 內容行＋1 頭注刪除指示行）。

## Phase 4 — Adversarial prompt 更新（目標：實核義務＋閉合欄位＋output 端守門；prompt 檔唯一改動點）

### Task 4.1 — [C-1][C-2][C-3][C-4][C-5][E-3] 實核義務、閉合欄位與 output 端守門
- SPEC ref：Task 4.1　目標：把「實跑反例」「family-scoped ID＋RECHECK」「TODO §0 完整性查核」寫進 prompt
- 輸入/輸出：templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md → v14；單一 commit
- 實作要點：①§0 末插 §A 實核義務條款（≤4 行：可低成本核實宣稱必實跑附 `VERIFY:` 命令＋stdout 摘要；無 shell 者標「未經覆核」且相關 finding ≥MAJOR、不得 reconcile 為 NON-BLOCKING）；②輸出格式每 finding 加 `ID:`（`ADV-CODEX-<n>`／`ADV-COMPOSER-<n>` family-scoped）與 `RECHECK:`（可重跑命令或可 Ctrl+F 步驟）；③§2 加三條必查：FACT-RECEIPT 落實／RISK-HIT 含 a,d ⇒ §G 非 N/A 且含數值 golden token／TODO §0 含解耦 7 條＋不可違反原則相關子集（純前端/文檔可聲明不適用；缺 → MAJOR）；④刪 STRICTNESS 死變數整行；⑤§2 獵空殼加例示「『確認有 1 個檔案』含數字仍空殼」。
- 修改檔案：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0、§1 變數表、§2、輸出格式段。既有 caller：所有 adversarial 派工 prompt。
- 不可做：不得刪 10 類必查任一類；不得改 Verdict 三值枚舉（gate D-1 依賴）；Phase 5 不得再碰本檔。
- 邊界：read-only 委員（無 shell）優雅降級文字必在；「相關子集」可為空但須明示聲明。
- 風險緩解：[C-1][C-2][C-3][C-4][C-5][E-3]
- 驗證：`grep -c "RECHECK" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` ≥ 2；`grep -c "STRICTNESS" ...` = 0；`grep -c "VERIFY:" ...` ≥ 1；`grep -c "ADV-CODEX" ...` ≥ 1；`grep -c "解耦" ...` ≥ 1；`wc -l < templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` ≤ 78。

## Phase 5 — TODO 生成 prompt 瘦身（目標：砍 5,100 行固定開銷、修合約分叉；僅改 TODO_GENERATION_PROMPT.md）

### Task 5.1 — [E-1][E-2][E-4] 憲法來源置換與按需讀取
- SPEC ref：Task 5.1　目標：必讀改 AGENTS.md＋CLAUDE.md 三節＋SPEC §C；按需觸發表；§A 引用不複製
- 輸入/輸出：templates/TODO_GENERATION_PROMPT.md 階段 0/階段 2 → 瘦身版
- 實作要點：①階段 0 必讀清單改：`AGENTS.md`（執行端真合約）＋CLAUDE.md「Multi-Agent 協作協議／驗證保真度鐵律／三方數據正確性簽核鐵律」三節＋SPEC §C；②按需觸發表：觸及 momentum/FeatureEngineering → ARCHITECTURE.md Feature Factory 章；觸及 api/routes|services → DEVELOPMENT_GUIDE.md API 節；跨域/factories.py → 兩檔對應節；SPEC 未列觸及模組 → 僅必讀清單，不得回退全讀；③階段 2 §0 生成規則加「引用 SPEC §A 之 manifest ID（如 [A-1]），不整段複製」。
- 修改檔案：`templates/TODO_GENERATION_PROMPT.md` 階段 0＋階段 2。既有 caller：所有 TODO 生成派工。
- 不可做：不得刪階段 1 覆蓋追溯／階段 3 自檢／深度紅線；不得碰 SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md。
- 邊界：AGENTS.md 改名/搬移時的引用脆弱性（prompt 內註明「與 CLAUDE.md『其他 agent』節同步」）；憲法讀不到 → 維持現行「要求貼全文」fallback。
- 風險緩解：[E-1][E-2][E-4]
- 驗證：`grep -c "copilot-instructions" templates/TODO_GENERATION_PROMPT.md` = 0；`grep -c "AGENTS.md" ...` ≥ 1；`grep "無條件讀" templates/TODO_GENERATION_PROMPT.md | grep -cE "ARCHITECTURE|DEVELOPMENT_GUIDE|copilot"` = 0；`grep -c "manifest ID" ...` ≥ 1。

## Phase 6 — gate 閉合與治理文件（目標：空 findings 不過門、對號銷帳、舊錨點歸零、grandfather 清單）

### Task 6.1 — [D-1][D-2] gate adversarial 品質輕檢與 --reconcile CLI
- SPEC ref：Task 6.1　目標：`--reconcile <path>` 契約＋Verdict/BLOCKING 處置機檢
- 輸入/輸出：scripts/gate.sh 參數解析＋--adversarial 檢查段 → 閉合版；5 gate fixture 拒/拒/拒/拒/發
- 實作要點：①參數解析加 `--reconcile) reconcile="${2:-}"; shift 2;;`；②--adversarial 檔須含 `Verdict` 行，缺 → 拒發；③--adversarial 檔含 `[BLOCKING]` **或** `ID:` 格式 finding **任一**（與 SPEC 同句，ADV-CODEX-5／ADV-COMPOSER-15）→ `--reconcile` 必填且該檔須對每個 `ADV-(CODEX|COMPOSER)-[0-9]+` 有 `→` 處置行，缺 → 拒發並列缺號；④無 `ID:` 且無 `[BLOCKING]` 的舊格式檔走現行行為（grandfather）；⑤多 adversarial 檔：`--adversarial` 逗號分隔逐檔檢（寫入 usage 說明）；⑥--reconcile 給了但 adversarial 無 BLOCKING/ID → 僅 WARN；⑦誠實邊界註解「字串級，語義真偽交人工＋二期」。
- 修改檔案：`scripts/gate.sh`（參數段＋檢查段＋usage）。既有 caller：Claude 每次派工、PreToolUse hook 間接依賴。
- 不可做：不得動 token 簽發/時效/audit 邏輯；不得實作語義級 reconcile 機檢（scope-out 二期）。
- 邊界：reconcile 檔同一 ID 多處置行不誤判缺；`--reconcile` 給了但 adversarial 無 BLOCKING → 不強制（僅 WARN）。
- 風險緩解：[D-1][D-2]
- 驗證：5 個 gate fixture（路徑寫死：`tests/gate_fixtures/gate_no_verdict.md`／`gate_blocking_no_reconcile.md`／`gate_id_major_no_reconcile.md`（僅 MAJOR＋ID:，驗「或」語義）／`gate_reconcile_missing_id.md`＋配套 reconcile／`gate_reconcile_complete.md`＋配套 reconcile），各以 `GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --risk high --spec docs/TEMPLATE_GATE_FIX_SPEC.md --todo docs/TEMPLATE_GATE_FIX_TODO.md --manifest docs/TEMPLATE_GATE_FIX_MANIFEST.md --adversarial <fixture> [--reconcile <fixture>] --intent test --facts-asked none-needed:test --review-role single-executor:n/a --template "跟過:test"` 跑，依序 exit 1/1/1/1/0（主驗收）；另跑低風險 smoke `GATE_DIR_OVERRIDE=/tmp/tgf-gate-test bash scripts/gate.sh dispatch --intent test --risk low --facts-asked none-needed:test --review-role single-executor:n/a --template "n/a:test"; echo $?` 印 0（僅 token 流程回歸，非主驗收——ADV-CODEX-6）。

### Task 6.2 — [D-3][D-4][D-5][F-3] 舊錨點替換、coverage 改名、RESULT 映射、現役盤點
- SPEC ref：Task 6.2　目標：7 處舊錨點字面歸零＋誠實命名＋映射一行＋GRANDFATHER 檔
- 輸入/輸出：3 治理檔＋coverage_check.sh＋RESULT_TEMPLATE.md → 一致版；新建 docs/TEMPLATE_GATE_FIX_GRANDFATHER.md
- 實作要點：①7 處（gate.sh 2、CLAUDE.md 1、MULTI_AGENT_ORCHESTRATION.md 4）全改寫為不含 `§1.0`/`§1.4` 字面（歷史紀錄行改「V12 舊『可測性準則』章，今 §V」式表述，語意保留字面移除）；②coverage_check.sh 輸出 `COVERAGE PASS/FAIL` → `ID PRESENCE PASS/FAIL`＋同步任何呼叫方 grep；③RESULT_TEMPLATE 規則節加一行「執行端合約之 `TESTS_RUN` 項目應可對應 `RECEIPTS` 元素（全域統一列二期）」；④用新 template_check 掃 docs/ 現役 SPEC/TODO（**明列 docs/IC_PHASE0_SPEC.md**），GRANDFATHER 檔記每檔 exit code＋政策「僅新文件適用，不回頭追殺」。
- 修改檔案：`scripts/gate.sh`、`CLAUDE.md`、`docs/MULTI_AGENT_ORCHESTRATION.md`、`scripts/coverage_check.sh`、`templates/RESULT_TEMPLATE.md`、新建 `docs/TEMPLATE_GATE_FIX_GRANDFATHER.md`。既有 caller：多 agent 共讀治理文件。
- 不可做：不得修改 `.claude/gate/audit.log`；不得竄改歷史語意（僅移除可 grep 字面）。
- 邊界：歷史紀錄行改寫保留原意；MANIFEST/SPEC/TODO/handoffs 內為修復記錄而引用舊錨點字樣的行**不在替換範圍**（僅治理三檔歸零）。
- 風險緩解：[D-3][D-4][D-5][F-3]
- 驗證：`grep -c "§1\.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md` 每檔印 0（修前基準 7 行）；`grep -rn "COVERAGE PASS" scripts/ --include="*.sh" | wc -l` 印 0；`grep -c "TESTS_RUN" templates/RESULT_TEMPLATE.md` ≥ 1；GRANDFATHER 檔存在且 `grep -c "IC_PHASE0_SPEC" docs/TEMPLATE_GATE_FIX_GRANDFATHER.md` ≥ 1。

## Phase 測試與 Gate 總表
- 單元層：test_template_check.sh 矩陣（13 fixture，EXPECTED 先驗）。
- 邊界層：各 Task 邊界欄（否定干擾句、discussion 豁免、特殊字元標題、空目錄 exit 2）。
- Mutation 層：MUTATION.txt 4 case（A-1/A-3/A-4/A-5 各一），每 case 改壞轉紅、改回轉綠。
- 端到端層：gate fixture 5 例拒/拒/拒/拒/發＋真 gate 實跑 exit 0＋本 SPEC/TODO 自檢 exit 0。

## 附錄 M — 階段 1 SPEC 索引（100% 覆蓋追溯；合計 29 ID）
| ID | SPEC 位置 | 原文節錄（≤30 字） |
|---|---|---|
| [A-1] | Task 2.1 | 「W1 從行級關鍵詞改為 §A 段級狀態機」 |
| [A-2] | Task 2.1 | 「已確認行須同時含日期樣式…或使用者」 |
| [A-3] | Task 2.2 | 「機檢只認 RISK-HIT: 宣告行…fail-closed」 |
| [A-4] | Task 2.3 | 「awk 按 ### Task 切塊，每塊獨立驗」 |
| [A-5] | Task 2.4 | 「RUNTIME_CHECK=PASS 且 RECEIPTS=[]…FAIL」 |
| [A-6] | Task 2.4 | 「待確認 regex 增列…誠實變體」 |
| [B-1] | Task 3.1 | 「§A 加 FACT-RECEIPT 一行格式…＋範例」 |
| [B-2] | Task 3.1 | 「教『待確認：無』精確寫法」 |
| [B-3] | Task 3.2 | 「涉 feature/kline…禁合成 fixture」 |
| [B-4] | Task 3.2 | 「附可證偽/mutation 設計並引用」 |
| [B-5] | Task 3.1 | 「複製為 SPEC 後刪除本 HTML 註解」 |
| [C-1] | Task 4.1 | 「§0 末插 Composer Q1 定稿條款」 |
| [C-2] | Task 4.1 | 「family-scoped：ADV-CODEX-<n>」 |
| [C-3] | Task 4.1 | 「§2 加查三條——FACT-RECEIPT 落實」 |
| [C-4] | Task 4.1 | 「刪 STRICTNESS 死變數」 |
| [C-5] | Task 4.1 | 「含數字仍空殼例示」 |
| [D-1] | Task 6.1 | 「--adversarial 檔須含 Verdict 行」 |
| [D-2] | Task 6.1 | 「--reconcile 必填且…→ 處置行」 |
| [D-3] | Task 6.2 | 「全部 7 處改寫為不含…字面」 |
| [D-4] | Task 6.2 | 「ID PRESENCE PASS/FAIL」 |
| [D-5] | Task 6.2 | 「TESTS_RUN 項目應可對應 RECEIPTS」 |
| [E-1] | Task 5.1 | 「必讀改 AGENTS.md＋CLAUDE.md 指定三節」 |
| [E-2] | Task 5.1 | 「按需觸發表（FeatureEngineering→…）」 |
| [E-3] | Task 4.1 | 「TODO §0 是否含解耦 7 條」 |
| [E-4] | Task 5.1 | 「引用 SPEC §A 之 manifest ID，不整段複製」 |
| [F-1] | Task 1.1 | 「負樣本 7…維持 FAIL 探針 1」 |
| [F-2] | Task 1.1 | 「正樣本 5：spec_good_full…」 |
| [F-3] | Task 6.2 | 「明列 docs/IC_PHASE0_SPEC.md…不回頭追殺」 |
| [F-4] | Task 1.2 | 「支援 spec/todo/result 三 kind」 |

合計數：Task 12（1.1/1.2/2.1/2.2/2.3/2.4/3.1/3.2/4.1/5.1/6.1/6.2）；manifest ID 29；探針 fixture 13（繞過 7＋維持 FAIL 1＋正樣本 5）；mutation case 4；gate fixture 5；批次 4。

## 階段 4 — Frozen 前 handoff
SPEC=docs/TEMPLATE_GATE_FIX_SPEC.md TODO=docs/TEMPLATE_GATE_FIX_TODO.md FOCUS=完整審查（雙家族 adversarial 兩輪完成、31 條 finding 全閉合、雙戳記 APPROVED；現狀=**Frozen** 2026-07-05，與頭部狀態一致）
