# TEMPLATE_GATE_FIX — Manifest（扁平 ID，coverage_check 基準）

來源：handoffs/2026-07-04-template-review-RECONCILE.md（四方委員會定案）。
每個 ID 必須落進 SPEC 與 TODO；機檢 `bash scripts/coverage_check.sh docs/TEMPLATE_GATE_FIX_MANIFEST.md <doc>`。

## A — 機檢硬化（template_check.sh）
- [A-1] FACT-RECEIPT 觸發擴大：§A 內「已驗證事實」行（非只「已確認」行）含資料結構詞也強制同/鄰行 FACT-RECEIPT（堵 U1 繞過，探針 spec_verified_bypass 修後必 FAIL）
- [A-2] facts-resolved 防標籤繞過：「已確認」判定須為結構化行（含日期或來源），該行含「待回覆/未確認/N/A/無法確認」→ 不算已確認（堵 Codex C2）
- [A-3] §RISK↔§G 聯動（結構化宣告制）：機檢認 §RISK 內 `RISK-HIT: <a,b,c,d 子集|none>` 宣告行（缺行 fail-closed）；宣告含 a/d → 強制 `## §G` 存在且含數值 golden token（atol/rtol/sha256 任一；exit/== 不算），拒絕 §N 對 §G 的 N/A（堵 U2，探針 spec_highrisk_no_g 修後必 FAIL；干擾句正樣本 spec_risk_false_positive 必 PASS）
- [A-4] TODO per-Task 分段檢查：awk 按 `### Task` 切塊，每塊獨立驗「驗證/邊界/不可做」三欄（堵 U3，探針 todo_bad 修後必 FAIL）
- [A-5] RESULT 交叉規則機檢：RUNTIME_CHECK=PASS ⇒ RECEIPTS 非空；MUTATION_CHECK=NOT_RUN ⇒ 檔內禁 DONE/已驗/全綠極性（豁免 `claim-context: discussion` 區塊）
- [A-6] 待確認 regex 修正：「待使用者確認：本任務無」等誠實變體不再誤擋（誤擋反例修後必 PASS）

## B — SPEC 範本更新（SPEC_TEMPLATE.md）
- [B-1] §A 加 FACT-RECEIPT 格式說明＋一行範例（命令＋stdout 摘要）
- [B-2] §A 語彙統一＋教精確寫法「待確認：無」；「已確認結果」須含日期＋來源
- [B-3] §G 加條件子條款：涉 feature/kline 生成/計算/merge/split/洩漏 → 強制真實 kline_cache.h5＋三方簽核計畫，禁合成 fixture
- [B-4] §V 加條件引用：§RISK 命中 (a)/(d) 或測試宣稱驗「正確性」→ 須附可證偽/mutation 設計並引用 docs/TEST_DESIGN_CHARTER.md；否則 §N 標 N/A＋理由
- [B-5] 頭部 11 行 HTML 註解加「複製為 SPEC 後刪除本註解」

## C — Adversarial prompt 更新（SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md）
- [C-1] §0 加「§A 實核義務」：可低成本核實（grep/讀真實檔/一行 python）的宣稱，reviewer 必須實跑並附 VERIFY: 命令＋輸出；無法實跑 → 標「未經覆核」、相關 finding ≥MAJOR、不得 reconcile 為 NON-BLOCKING
- [C-2] 輸出格式加每 finding `ID:` 與 `RECHECK:`（可重跑命令或可 Ctrl+F 檢查步驟）
- [C-3] §2 加三條必查（詳 SPEC Task 4.1）：FACT-RECEIPT 是否落實；RISK-HIT 含 a/d 時 §G 真存在非 N/A 且含數值 golden token；TODO §0 含解耦＋不可違反原則相關子集（即 [E-3]）
- [C-4] 刪除死變數 {{STRICTNESS}}
- [C-5] §2 獵空殼加假證偽例示（「確認有 1 個檔案」含數字仍屬空殼）

## D — 閉合機制與治理文件（gate.sh／reconcile／文檔）
- [D-1] gate.sh adversarial 品質輕檢：對 --adversarial 檔 grep Verdict 存在＋reconcile 後無未處置 [BLOCKING]（誠實邊界：字串級，防「空 findings 檔過門」）
- [D-2] reconcile 對映表義務：reconcile 檔強制含 `[Finding ID]→[修補位置]→[RECHECK 結果]` 表（一期人工＋模板說明；語義機檢明確列為二期不在本 epic）
- [D-3] 治理文件舊錨點替換：gate.sh／CLAUDE.md／MULTI_AGENT_ORCHESTRATION.md 內全部 7 處 §1.0/§1.4 引用改為不含舊錨點字面的 V13 表述（§V 可測性、§G Golden）
- [D-4] coverage_check.sh 輸出改名「ID PRESENCE PASS/FAIL」防語義過度解讀
- [D-5] RESULT↔執行端合約映射一行：RESULT_TEMPLATE 規則節註明 TESTS_RUN 項目應可對應 RECEIPTS 元素（收窄版 C-6；全域統一列二期）

## E — TODO 生成 prompt 瘦身（TODO_GENERATION_PROMPT.md）
- [E-1] 階段 0 憲法來源改為：AGENTS.md（執行端真合約）＋ CLAUDE.md「Multi-Agent 協議／驗證保真度／三方簽核」三節＋ SPEC §C；移除無條件全讀 copilot-instructions/ARCHITECTURE/DEVELOPMENT_GUIDE
- [E-2] 按需讀取觸發器：觸及 FeatureEngineering → ARCHITECTURE 對應章；觸及 API → DEVELOPMENT_GUIDE API 節；跨域/factory → 兩檔對應節
- [E-3] 防事故面轉移：adversarial §2 加查「TODO §0 是否含解耦 7 條＋不可違反原則之本任務相關子集」（守門從 input 移到 output）
- [E-4] TODO 不整段複製 SPEC §A，改引用 manifest ID

## F — 回歸驗證（探針固化）
- [F-1] 反例探針固化：spec_verified_bypass／spec_heading_verified_bypass（ADV-C1）／spec_ic_phase0_style（ADV-P2）／spec_highrisk_no_g／todo_bad／result_pass_empty_receipts／result_notrun_done_operational（ADV-P5）七探針＋facts-unresolved 正確 FAIL 探針入 repo（tests/gate_fixtures/），修後七繞過探針必 FAIL、facts-unresolved 維持 FAIL
- [F-2] 誤擋回歸：合規正樣本（含 FACT-RECEIPT 的 §A、RISK-HIT 宣告、真 §G、per-Task 三欄齊、「待確認：無」變體、§RISK 干擾句、discussion 區塊內 DONE）必 PASS
- [F-3] 現役文件盤點：新機檢對 docs/ 現役 SPEC/TODO 掃描一次，列出將 FAIL 清單與 grandfather 政策（不回頭追殺，僅新文件適用）
- [F-4] 驗證器：scripts/test_template_check.sh 一鍵跑全部 fixture，exit code 可證偽；CI 或 pre-dispatch 可調用
