# Composer 白話版互審 — Codex on Composer

## Scope
- 原文：`docs/VERIFY_GATE_SPEC.md`（讀到 EOF，111 行）
- 白話版：`docs/VERIFY_GATE_SPEC_PLAIN_COMPOSER.md`（讀到 EOF，316 行）
- 任務：逐項核對忠實度、§C 誠實邊界、§N 殘餘風險、§RISK 硬性順序，以及非技術讀者友善度。

## Overall
Composer 版整體忠實，能讓非技術決策者理解「防疏忽驗收捏造，不防惡意偽造」與「收據 + claim checker + 三層 enforcement」的主線。§C 的核心誠實邊界、§N 大多數殘餘風險、§RISK 的 PreToolUse 前置條件都有翻出來。

但目前不建議標 ACCURATE，原因是有 3 個需要修正或澄清的忠實度問題，其中 1 個會造成讀者誤解 enforcement 範圍。

## Findings / Fixes Needed

1. **高優先：`改待辦/阻塞/決策文字不觸發` 與 SPEC 不一致**
   - Composer 版 §⑤.C「收據疲勞」寫：「只對 operational 新宣稱強制；改待辦/阻塞/決策文字不觸發」。
   - SPEC §P3-1 明確把新增/修改文字落在 `## 正在做|## 待辦|## 已完成|STATUS:|RESULT` 或 root HANDOFF 狀態段，且非 fenced/quote 的新增行，視為 operational，過 checker。
   - 正確白話應改成：`只有在這些正式狀態/待辦/結果段落新增驗收宣稱時才強制；純待辦、純阻塞、純決策且不含已驗/DONE/ready/真跑等驗收宣稱時不擋。`
   - 風險：現句會讓人以為待辦/阻塞段是完全免掃區，與 W4 fail-closed 精神衝突。

2. **中優先：新增了 SPEC 未列的 W8/W9/W5，需移除或標成「非本 SPEC 內容」**
   - Composer 版 §⑤.D 寫 W8/W9 記憶體簽核、RESULT 欄位與收據交叉驗證，W5 派工 token 與前後快照配對。
   - 這些不在本次 `VERIFY_GATE_SPEC.md` v2.1 的 Phase / §V / §N 內；可能來自更大 workflow 掃描，但以「對應技術規格」文件呈現時會混入未背書範圍。
   - 建議：刪除 §⑤.D，或改標 `延伸背景，非本 SPEC v2.1 驗收範圍`，避免後續 TODO 生成或驗收誤把它們當 v2.1 scope。

3. **中優先：§C 的「不弱化既有 gate_check.sh；並存新通道」未明確翻出**
   - SPEC §C 明列：不弱化/繞過既有 `gate_check.sh`，本閘為並存新通道。
   - Composer 版雖說「不動既有派工門邏輯，可整包 revert」，但沒有直接說新閘不是替代舊 gate、不得削弱舊 gate。
   - 建議在 §③ 或 §④ 加一句：`這套機制是加在既有派工門旁邊的新驗收通道，不取代、不放寬、不繞過原本 gate_check.sh。`

4. **低優先：§G/§N 的 Golden N/A 可再白話化**
   - Composer 版有說「不碰數值/ML/回測正確性」，但未直接翻出「沒有 numeric golden；改用假 claim 擋、真 claim 放、快測冒充慢測擋、誤報=0 作為可證偽 golden」。
   - 建議在 §⑤.B 或 §⑥ 驗收標準補一句：`這個 epic 的 golden 不是數值基準，而是 V1-V19 這組行為測試。`

5. **低優先：SPEC 標題與白話版版本號不一致，建議註明依 v2.1 定稿脈絡**
   - 原文檔案標題仍寫 `SPEC v2`，HANDOFF 與白話版稱 v2.1。
   - 這不是 Composer 忠實度錯誤，但會讓非技術讀者疑惑。
   - 建議白話版首段改成：`對應 docs/VERIFY_GATE_SPEC.md（文件標題仍為 v2，但依 HANDOFF/確認戳記視為 v2.1 定稿版）`，或先修原文標題。

## Section Check
- **§RISK 硬性順序**：大致忠實。Composer 版在 §③ 降級路徑與 §⑥ 實作硬性順序都寫出「claim-object 誤報=0 才上第一層，未達標降級到 commit-hook + CI + receipt」。建議保留。
- **§C 誠實邊界**：核心忠實。已清楚說不保證詮釋正確、不防惡意偽造、careless-proof + tamper-evident、語意分類器是 router 不是 judge。缺口是未明說不弱化既有 `gate_check.sh`。
- **§N 殘餘風險**：大致忠實。已列惡意偽造、解讀錯誤、未知同義詞 WARN、完整 HANDOFF 索引延後、pending 無 file lock、run_receipts 索引延後。可補 Golden N/A 的行為測試定位。
- **Phase 1**：忠實且友善。收據 + 審計 + hash + runtime_class 的白話說明準確。
- **Phase 2**：大致忠實。claim-object、VERIFY/REF、SUPERSEDED、discussion、runtime_class 防冒充、readonly signoff、exempt、pending ledger 都有涵蓋。
- **Phase 3**：大致忠實，但需修正「待辦/阻塞不觸發」那句。
- **Phase 4**：忠實。P4-1 行為不變、W2/W3 provenance、W7 人工抽查都有翻出。
- **Phase 5**：忠實。RESULT 硬欄位、#6 衝突檢查、完整 render 延後、W1 FACT-RECEIPT 都有涵蓋。
- **§V 驗證策略**：沒有逐項列 V1-V19，但以非技術版而言可接受；事故原文 V17、快測不能撐慢測 V4、誤報=0 V7 有明確點名。

## Non-Technical Friendliness
- 優點：結構清楚；「收銀機小票 / 會計對帳 / 三層防線」類比有效；先講事故再講防線，對非技術讀者友善。
- 優點：表格把事故型態、三層 enforcement、殘餘風險、決策問題整理得好。
- 可改善：`claim-object`、`runtime_class`、`VERIFY/REF/SUPERSEDED` 是必要術語，但可在首次出現時加一句「這些是機器可讀標籤」降低門檻。
- 可改善：§⑤.D 混入非 SPEC 項目會讓決策者誤解 v2.1 scope，應刪或降級成背景。

## Concrete Patch Suggestions
1. 將 §⑤.C「收據疲勞」對策改為：`只對正式狀態/待辦/結果段落中的 operational 新宣稱強制；純待辦、阻塞、決策且不含驗收宣稱時不觸發。`
2. 在 §③ 核心分工後補：`本閘是既有 gate_check.sh 旁邊的新增驗收通道，不取代、不放寬舊 gate。`
3. 刪除 §⑤.D，或標題改成：`延伸背景（非本 SPEC v2.1 驗收範圍）`。
4. 在 §⑥「最該盯的驗收標準」附近補：`本 epic 無數值 golden；golden 是 V1-V19 行為測試。`
5. 處理 v2/v2.1 命名不一致，避免讀者以為白話版對錯版本。

VERDICT: NEEDS-FIX (items: 1 high-priority wording mismatch; 2 medium scope/omission clarifications; 2 low clarity fixes)
