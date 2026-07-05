# Template 審查 RECONCILE — 四方委員會最終結論（2026-07-04）

委員：Claude(Fable 5) + Codex(GPT-5.5) + Composer 2.5 + Gemini 3.1 Pro(read-only)。
流程：四方各自產完整獨立版（互不可讀）→ 第二輪交叉詰問（Q1-Q6，含反駁機會）→ 本 reconcile。
證據基礎：Composer 對 `template_check.sh` 實跑 3 個反例探針（bypass 實證）；Claude 實跑 grep/regex 覆核 2 條。

## 三問題最終答覆

**1. 合適性：方向正確，保留 V13 設計，不推翻。**「緊湊範本+gate 錨點機檢+adversarial 語義補洞」分層對症真實事故（四方一致）。但「制度聲稱」強於「機檢實作」：多處機檢擋不住文件聲稱要擋的事，gate 給出過度安全感。

**2. 冗長度：範本本體（4 檔 ~250 行）不冗，不可再砍。**唯一真 token 黑洞 = TODO 生成階段 0 無條件全讀 copilot-instructions(739)+ARCHITECTURE(1989)+DEVELOPMENT_GUIDE(2407) ≈ 每次 5,100+ 行（四方一致）。階段 1 覆蓋追溯、10 類必查、雙家族 adversarial 均判「值得付」。

**3. 遺漏/瑕疵：有，且兩條 BLOCKING 已被反例實證。**核心模式：範本↔機檢↔制度鐵律三層互相漂移。

## 定案 Findings（依優先序）

| # | 級別 | 內容 | 證據狀態 | 共識 |
|---|------|------|----------|------|
| 1 | **BLOCKING** | **U1** FACT-RECEIPT 漂移+繞過：機檢只在「已確認」行觸發，「已驗證事實」寫未實測資料結構宣稱可全繞過；範本未教 FACT-RECEIPT 格式；範本自帶「已確認結果」標籤即滿足 facts-resolved | 探針 `/tmp/spec_verified_bypass.md` PASS(不應)；現役 IC_PHASE0_SPEC 即中招 | 4/4 |
| 2 | **BLOCKING** | **U2** §RISK↔§G 脫鉤：高風險(a/d) SPEC 可在 §N 標「§G：N/A」逃 Golden | 探針 `/tmp/spec_highrisk_no_g.md` PASS(不應) | 4/4 |
| 3 | MAJOR | **U3** TODO per-Task 三欄僅全域 grep，10 個 Task 只 1 個有欄位也 PASS → 改 awk 按 `### Task` 分段檢 | 探針 `/tmp/todo_bad.md` PASS(不應) | 4/4 |
| 4 | MAJOR | **CL-2** adversarial prompt 加「§A 實核義務」條款：可低成本核實（grep/讀檔/一行 python）的宣稱，reviewer 必須實跑附輸出；無法實跑→標未經覆核、finding ≥MAJOR、不得 reconcile 降級 | Q1 四方 AGREE；Composer 給定稿文字 | 4/4 |
| 5 | MAJOR | **U9** finding 閉合機制：(a) 每 finding 加 `ID:`+`RECHECK:`（prompt 改，0 成本）＋(b) gate 輕量 grep Verdict/未處理 BLOCKING（~15 行）＋(c) reconcile 強制 `[ID]→[修補章節]→[RECHECK 結果]` 對映表（一期人工+模板，語義機檢留二期防新假綠） | Q2 收斂 | 4/4 |
| 6 | MAJOR(快贏) | **U11** 治理文件殘留舊錨點 §1.0/§1.4 共 6 處（gate.sh:9,254、CLAUDE.md:41、MULTI_AGENT_ORCHESTRATION.md:69,101,212,308）→ 全庫替換 V13 錨點名 | Claude grep 實證 | 4/4 |
| 7 | MAJOR | RESULT 規則未機檢：`RUNTIME_CHECK=PASS ⇒ RECEIPTS 非空`、`MUTATION_CHECK=NOT_RUN ⇒ 禁 DONE 極性`寫在範本但機器不擋（後者須豁免 `claim-context: discussion` 區塊） | 讀碼確認 | 3/4 提出 |
| 8 | MAJOR | **Q3 定案（條件版）**：§RISK 命中 (a)/(d) 或測試宣稱驗「正確性」時，§V 須附可證偽/mutation 設計並引用 `docs/TEST_DESIGN_CHARTER.md`；其他任務 §N 標 N/A+理由。接通 RESULT.MUTATION_CHECK 上游斷鏈 | Q3 收斂 | 4/4 |
| 9 | MAJOR | **Q4 定案（憲法瘦身）**：TODO 階段 0 改讀 `AGENTS.md`（執行端真合約，修 copilot-instructions 分叉）+ CLAUDE.md 治理三節 + SPEC §C；ARCHITECTURE/DEV_GUIDE 改按需節選（觸發詞寫進 prompt）；**不**另立第四份憲法檔（防再漂移）；防事故面靠 adversarial 加查「TODO §0 完整性」 | Q4 收斂 | 4/4 |
| 10 | MAJOR | 三方數據簽核鐵律未下沉範本：§G 加條件子條款——涉 feature/kline 生成/合併/split/洩漏時強制真實 `kline_cache.h5`+三方簽核計畫，禁合成 fixture | Codex C7+Composer C-8 | 2/4 提出 0 反對 |
| 11 | MINOR | U13「待使用者確認：本任務無」regex 誤擋（範本教精確寫「待確認：無」或修 regex）；hollow 檢查「含數字即過」可被「確認有 1 個檔案」游走（adversarial §2 加例示）；coverage 輸出改名「ID PRESENCE PASS」防過度解讀；adversarial prompt 死變數 STRICTNESS 刪除；SPEC 範本頭注 11 行加「複製後刪除」；TODO 勿整段複製 SPEC §A（引用 manifest ID） | 各 1-2 方提出 0 反對 | — |

## 被反駁撤回/降級（交叉詰問成果）
- **Claude C-10**（§G canonical 容差預設值）：Codex 反駁成立——跨任務硬給官方寬鬆值會被濫用；**撤回**，維持「SPEC 自述容差+來源」。
- **Codex C8**（spec-to-todo 第二覆蓋模式）：三方判與 manifest 慣例重複、增 churn；**降 SUGGESTION**（Codex 本人同意）。
- **Gemini PREMISE-2**（coverage 跳過清單游走）：**降 MINOR**——需刻意造假，U3 分段機檢+階段1索引已覆蓋主風險。
- **Composer C-6**（RESULT/ASSUMPTIONS 雙軌）：維持 MAJOR 但非阻擋主線——修法收窄為「映射一行+sync 腳本加錨點」。

## 明確不可砍清單（四方一致，防「省 token」誤傷）
§RISK-§N 錨點全集；§A facts-resolved；反空殼三件套；adversarial §0 挑戰前提+10 類必查；§G value/NaN-mask hash；TODO 深度紅線與階段 1 覆蓋追溯；雙家族 adversarial+作者不自審；manifest coverage_check；FACT-RECEIPT 概念（要擴大不要刪）；RESULT 枚舉欄位。

## 後續（未派工，待使用者決定）
上述修補=改 2 個範本+1 個 prompt+`template_check.sh`/`gate.sh`+治理文件錨點替換。命中 (b) 共用路徑（gate 擋所有派工）→ 屬**中～大任務**，動工須走完整管線（SPEC+TODO+雙家族 adversarial+RECONCILE-STAMP）。

RECONCILE-STAMP: pending（本檔為審查結論，非實作 SPEC；派實作前須 codex+composer 戳記）
