
# 第 0 批 B2 code review（雙家族）

brief-kind: review

**受審 commit**：`4e8e61c`（B2 ＋ B0/B1 兩條 review finding 補修）
**依據**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）Phase 1 / Task 1.1 ＋ B0/B1 補修項

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。

## 🔴 finding heading 格式（引用檢查器正則本身）

`scripts/completeness_check.sh:153` 逐字為：

```
^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$
```

本輪合法範例：`CODEX-R11-P1-01`／`COMPOSER-R11-P0-02`。
**本輪唯一允許的 `##` 標題**：`## Verdict`／`## §0 前提宣告`／`## 逐項核對表`／`## 出場判準核算`
＋ canonical finding heading。其餘分段用 `###`。零 findings 請明寫 `FINDINGS_COUNT: 0`。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: B0 snapshot 於 `fixtures/` 執行時無法載入 debt 依賴 ——
  `snapshot:19` 以自身位置推導 `SCRIPT_DIR`；`snapshot:41-42` 於該處尋找
  `_debt_ledger_core.py` 與 `debt_ledger.sh`，`fixtures/` 內不存在。
- fact-verified: 替代測試 `test_01_fresh_token_allow_when_no_open_debt` 實體存在且非空殼
  （構造 token ＋ 空債務日誌 ＋ `GOVERNANCE_TEST_HARNESS`／`DEBT_AUDIT_OVERRIDE`）。

**假設**（請優先攻）：

- assumed: **`727 passed` 為實作者轉述，主委本輪未親自復跑**（B0+B1 那次有親跑 receipt）。
- assumed: **語料 A 的 28 條真的涵蓋「現行可發出的每一個 `match_rule` 值」**——
  主委未逐條核對，僅採信實作者的覆蓋宣稱。
- assumed: **替代測試與「進語料 A 比對快照」等價**。未經第三方驗證；
  兩者驗的東西本質不同（前者只驗現行程式行為，後者驗改前改後一致）。

---

## 🔴 本輪首要攻擊標的：B0 snapshot 的結構性盲區

**事實**：B0 只複製了 `gate_check.sh`，**未複製其依賴**。
⇒ 快照置於 `fixtures/` 執行時，任何**依賴同目錄腳本**的分支都會 fail-closed，
無法與現行程式比對 ⇒ `TEST-0.1-INVARIANCE` 對這些分支**沒有保護**。

本次已知受影響：「fresh token ＋ 無 OPEN 債 → 放行」。

**請回答四題**：

| # | 問題 | 通過條件 |
|---|---|---|
| 1 | **還有哪些分支受同一盲區影響**？請窮舉 `gate_check.sh` 中所有依賴 `${SCRIPT_DIR}` 或外部腳本的路徑 | 逐條列出，並判定各自是否已有替代測試 |
| 2 | **替代測試是否真的等價**？它只驗「現行程式行為對」，不驗「改前改後一致」 | 明確判定「等價／不等價」，若不等價請說明漏掉什麼 |
| 3 | **B0 的修法**：是否該把依賴一併快照（或改用 `git show <sha>:path` 動態取得）？ | 給出可執行修法與其代價 |
| 4 | 主委判定「這不構成 brief 禁止的『調整語料使其變綠』」是否正確？ | 同意／不同意，附理由 |

🔴 **第 4 題請獨立判斷，不要因為主委已表態就跳過。**
brief 原文禁令：「若擴充後 diff 非空，代表 B1 真的改變了某分支的判定，屬 BLOCKING，
須停下回報，**不得調整語料使其變綠**。」

---

## 逐項核對表（**用表格，不要用標題**）

| # | 查什麼 | 判定 | 依據（實跑命令＋結果） |
|---|---|---|---|
| 1 | 語料 A 28 條是否**每條都有真實出處**、非憑空造 | | |
| 2 | `match_rule` 覆蓋宣稱是否屬實（對每一可發出值至少一次） | | |
| 3 | 值相等斷言是否真的驗到「完整指令」而非截斷後字串 | | |
| 4 | `TEST-1.1-UNKNOWN-NOSIDEEFFECT` 四項是否**逐項**驗證（非只驗 rc） | | |
| 5 | prompt 格式說明與 `cx_run.sh:345` 正則是否**機械一致**（同一樣本同時通過兩者） | | |
| 6 | **測試品質**：依範本 §1 第 9 類逐條舉證 | | |
| 7 | 既有測試斷言是否被改動（`git diff 4e8e61c^ 4e8e61c -- tests/`） | | |

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`，不計入 findings）

1. 重開 SPEC／TODO 的設計裁決。**例外**：該裁決導致本實作有實質缺陷。
2. B3 以後的 Task（`2.*`／`3.*`）——本批未實作。
3. `E-SCOPE` 四項、`H-1`／`H-2`、`F-7`／`B-36` 等已具名殘留。
4. 措辭／命名／可讀性。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ B2 驗收通過，可進 B3。**

## 硬性要求

1. **禁改碼、禁改測試、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`／`git clean`；不要 commit、不要 push；**禁碰 `data_cache/`**。
4. 每條 finding 附**可執行修法**與**重現命令**。
5. 跑全套 `pytest tests/governance -q` 請**丟背景並導檔再取尾**（約 235 秒）。

## 產出

四題首要標的的回答、上表七項逐項判定、findings（若有）、`## 出場判準核算`、
對 §0 三條假設的攻擊結果。收尾清 /tmp workdir（保留 claude-501）。
