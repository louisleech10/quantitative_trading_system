# 第二輪交叉詰問 — Composer 2.5 作答（2026-07-04）

已讀：CROSSEXAM BRIEF、Claude/Codex/Composer 三份 review、附錄 Gemini 節錄。已定案 U1/U2/U3/U11/U13 不重新辯駁。

---

## Q1: AGREE — adversarial prompt 須制度化「廉價實跑反例」

**理由**：本輪三個探針（`spec_verified_bypass`、`spec_highrisk_no_g`、`todo_bad`）證明「純讀文件 adversarial」與機檢各擋一半，中間縫隙可過 gate。這正是 V2-timestamp 事故模式：§A 假事實 + reviewer 只標 assumption Medium → reconcile 降級放行。鐵律在 `CLAUDE.md` 但 prompt 未落地，屬制度斷鏈而非「建議加強」。

**最小可行條款**（建議插入 adversarial prompt §0 末，≤4 行）：

```text
**§A 實核義務**：凡 §A「已驗證事實／已確認」中含可低成本核實宣稱（grep 碼庫、讀指定檔、一行 python 對真資料），reviewer 必須實際執行並在 finding 附 `VERIFY:` 命令+stdout 摘要；無法執行則該宣稱標「未經覆核」，且相關 finding severity 不得低於 MAJOR、不得 reconcile 為 NON-BLOCKING。
```

---

## Q2: PARTIAL — 最小充分組合 = (a) + (b)，(c) 作 reconcile 人工義務、二期機檢

**最小充分組合**：

| 組件 | 納入？ | 理由 |
|------|--------|------|
| **(a) Finding ID + RECHECK** | **必須** | 閉合追溯的最低成本單位；純 prompt 改動，零腳本成本；無 ID 則「已修」無法對號重跑（FF 驗收捏造同型）。 |
| **(b) gate 輕量 grep Verdict + 未處理 BLOCKING** | **必須** | `gate.sh` 已驗檔案存在（C-13）；加 ~15 行：`grep -q 'Verdict：可派工'` 且 `grep '\[BLOCKING\]'` 在 reconcile stamp 後仍出現則 WARN/FAIL。誠實邊界：可偽造，但把「空 findings 派工」成本從 0 提到需刻意造假。 | 〔REF:handoffs/2026-07-04-template-review-RECONCILE.md〕 〔SUPERSEDED:早期紅燈紀錄已由 TGF epic 修復+stamped reconcile 取代〕
| **(c) reconcile `[Finding ID]→[章節]` 對映表** | **人工必做、機檢二期** | Gemini PREMISE-1 正確（狐狸審雞窩），但語義對映難用 grep 可靠驗證（作者可寫 `[C-2]→§A` 而 §A 未真修）。一期：reconcile 模板強制表格 + Claude 人工驗 `[ID]` 是否在 SPEC diff 中出現；二期：腳本驗每個 ID 在 SPEC/TODO diff 有對應章節錨點（~40 行 awk，中成本）。 |

**機檢實作成本評估**：(a) 0h；(b) 0.5h；(c) 人工模板 0.5h + 二期腳本 2h。**不建議一期上 (c) 機檢**，否則假綠（表填了、內容空）與現行 substring 機檢同病。

---

## Q3: PARTIAL — §V 加條件引用，非全任務強制

**理由**：`RESULT_TEMPLATE` 已有 `MUTATION_CHECK`；`TEST_DESIGN_CHARTER` 存在且 VERIFY_GATE 域已用。對**宣稱資料正確性/ML/回測驗證**的任務，§V 缺上游設計要求會導致下游只能填 `NOT_RUN` 或被 N/A 帶過——這是真斷鏈。但對純 refactor/文檔/薄 route 任務，強制 mutation 設計是過度工程。

**建議最小改法**（一行，條件觸發）：

```text
§V：若測試宣稱驗證**正確性**（非僅存在性），須附可證偽設計或 mutation 摘要（見 `docs/TEST_DESIGN_CHARTER.md` §?）；否則 §N 標「mutation: N/A + 理由」。
```

觸發條件綁 §RISK `(a)/(d)` 或 §V 含「正確性/洩漏/golden」關鍵詞，避免全任務強制。

---

## Q4: AGREE (b) 為主幹，吸收 (a) 的「短摘要」概念 — 不選純 (a) 或純 (c)

**選 (b) Composer 案**，並補一條不新增 739 行 copilot 分叉：

1. **TODO 階段 0 必讀改為**：`AGENTS.md`（執行合約同源）+ `CLAUDE.md` 僅「Multi-Agent 協議 + 驗證保真度 + 三方簽核」三節（~80 行）+ 本 SPEC §C/§RISK 已列約束（不重複展開）。
2. **按需讀取觸發器**（寫進 prompt，可機檢 grep 觸發詞）：觸及 `momentum/FeatureEngineering` → `ARCHITECTURE.md` Feature Factory 章；觸及 API route → `DEVELOPMENT_GUIDE.md` API 節；跨域/factory → 兩檔各一節。Gemini (c) 的「輕量 CODING_STANDARDS」可由 `AGENTS.md` Code Standards 節替代，不重複造檔。
3. **防「沒讀憲法」事故面**：
   - 解耦 7 條、data_cache 紅線、反提示注入 → 已在 `AGENTS.md` + SPEC §C，執行端與 TODO 生成同源；
   - gate 錨點機檢（§A/§G/§V/per-Task）不依賴人記憶；
   - adversarial 10 類必查保留語義補洞；
   - **不**無條件刪 ARCHITECTURE 可讀性，只刪「每次全讀 4400 行」。

**不選 (a) 單獨短憲法**：再增 `AGENT_CONSTITUTION.md` 易與 `AGENTS.md`/`CLAUDE.md` 四源漂移（我們剛在修 §1.0/§1.4 漂移）。**(b) 的精髓是「執行合約單一來源 + 按需」**，不是再立第四份憲法。

---

## Q5: 反駁 — 認為錯誤或過度的 finding

### 5.1 Codex [C8] SPEC ID→TODO 追溯 — **過度 / 與現行慣例重複**

**判定**：SUGGESTION 級，非 MAJOR。

**理由**：`TODO_GENERATION_PROMPT` 階段 1「每個 SPEC ID」指 **manifest 扁平 ID**（`[A-1]`）→ TODO 位置；`coverage_check.sh` 已驗 manifest→target 字串存在。SPEC 內部 `[P1-2]`/`[T1-2a]` 是 §P 展開細節，慣例上從 manifest 衍生而非獨立 ID 宇宙。要求 `spec-to-todo` 第二模式會強制 SPEC 內每個子 ID 進 TODO，增加中型任務 churn，而 **U3（per-Task 三欄分段）+ 階段 1 索引表** 已覆蓋「Task 漏項」主風險。Codex [C10] 建議 §P 穩定 ID 慣例足夠，[C8] 全模式機檢性價比低。 〔REF:handoffs/2026-07-04-template-review-RECONCILE.md〕

### 5.2 Composer [C-6] RESULT vs ASSUMPTIONS 雙軌 — **severity 偏高，實際衝突面窄**

**判定**：維持 MAJOR 可接受，但**非 operational 衝突**，是格式分裂。

**理由**：實測路徑上，一般派工執行端寫 `ASSUMPTIONS_VERIFIED/TESTS_RUN`（`check_agent_contract_sync.sh` 驗）；`RESULT_TEMPLATE` 主要服務 VERIFY_GATE/高風險驗收域。兩者**不互斥**——問題是缺映射表與 sync 腳本未含 RESULT 錨點，導致「寫了一邊另一邊機檢不查」。不應升 BLOCKING；修復 = `RESULT_TEMPLATE` 增「`TESTS_RUN` 可填入 `RECEIPTS`」一行 + sync 腳本加 3 token，優先序應在 U1–U3 之後（與我原報告一致）。

### 5.3 Claude [C-4] §V 強制 TEST_DESIGN_CHARTER — **部分過度若無條件強制**

**判定**：同意問題存在，不同意「§V 加一行無條件引用」為最小修法（見 Q3 條件版）。對小型/非正確性任務，無條件 mutation 要求會推高 SPEC 撰寫摩擦，與 V13 緊湊精神衝突。

### 5.4 Codex [C2]「已確認結果」標籤滿足 facts-resolved — **併入 U1，勿單獨升 BLOCKING**

**判定**：AGREE 問題真實，但與 U1（FACT-RECEIPT 觸發詞綁錯）同一修法簇：`template_check.sh` 統一掃 §A 資料結構詞 + 結構化 `已確認結果：YYYY-MM-DD 來源…`。不應列為與 U1 並列的第二個 BLOCKING 項，避免優先序分散。

### 5.5 Gemini PREMISE-2 coverage「跳過清單」游走 — **MAJOR 偏高，應 MINOR/SUGGESTION**

**判定**：ID 限標題行是合理加深（與我 C-12 同向），但現行 `coverage_check` 輸出應改名 `ID PRESENCE PASS`（Codex C9 已提）即可防過度解讀。實際失敗需**刻意**在 §0 堆砌 ID 清單而無 Task——U3 分段機檢 + 階段 1 人工索引更直接。severity 校準：真 BLOCKING 僅 **機檢聲稱擋住但探針證偽**（U1/U2）；U3 是 MAJOR（執行猜測風險）；coverage 語義遊走是 MINOR。

### 5.6 Claude [C-5] RESULT RECEIPTS 機檢 — **MAJOR 正確，非 BLOCKING**

**判定**：AGREE severity。模板規則未機檢是 drift，但需改 `template_check.sh` result 分支，不阻派工 SPEC/TODO freeze；屬驗收誠實邊界，與 U1/U2「錯前提進入執行」不同致命級。

### 5.7 無反駁（同意定案）

U1/U2/U3/U11/U13；Claude CL-2/Codex C1/C3/C4/C5；Composer C-1–C-5；Gemini DRIFT-1/DRIFT-2；三方 PREMISE-1 問題意識（修法見 Q2）。

---

## Q6: Top-5 修補順序

1. **U1** — FACT-RECEIPT 寫入 `SPEC_TEMPLATE` + 機檢觸發改掃「已驗證事實」/§A 資料結構詞（堵第三次事故同款）
2. **U2** — §RISK `(a)/(d)` 命中時拒 §N 對 §G 的 N/A，強制 `## §G` 含金標 token
3. **U3** — `template_check.sh` TODO 分支按 `### Task` 分段檢「驗證/邊界/不可做」
4. **CL-2 / adversarial §A 實核義務** — prompt 條款（Q1 文案）+ §2 增 FACT-RECEIPT/§RISK-§G 兩條必查
5. **U11 + C-5(RESULT RECEIPTS)** — 治理錨點 V13 對齊（防稽核找錯章）+ result 分支 PASS⇒RECEIPTS 非空（低成本閉合驗收誠實）

（U13 順位第 6；U5/TOKEN-1 憲法瘦身隨 TODO prompt 改版一併做，不與安全機檢搶前 5。）

---

STATUS: DONE
