# 第 0 批 TODO adversarial 審查

brief-kind: review

target: `docs/GOVB0_FRICTION_TODO.md`（DRAFT，611 行）
基準 SPEC: `docs/GOVB0_FRICTION_SPEC.md`（R7 版，七輪收斂，收斂檔三家戳記 sha `b502bac9…0f82fa4bd`）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。本 brief 只收斂範圍。

## 🔴 產出格式（**本輪唯一允許的 `##` 標題清單**）

`## Verdict`／`## §0 前提宣告`／`## 逐項核對表`／`## 出場判準核算`／
finding heading `## <家族大寫>-TODO-P<嚴重度>-<序號>`。
**除上列外不得出現其他 `##` 標題**（分段用 `###`）。
不符 schema 的 `##` 會被 `completeness_check` 判 invalid finding ID ⇒ **整份 format-failed**（`票 B-31`，本批已踩兩次）。

🔴 **若結論是零 findings，請明寫一行 `FINDINGS_COUNT: 0`**（`票 B-38`，本批已因此棄輪一次）。

## §0 前提宣告

**已查證**：

- fact-verified: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0
  → receipt `todo-template-pass`。
- fact-verified: SPEC Task 數 **11**（`grep -c '^\*\*Task '`）== TODO Task 數 **11**（`grep -c '^### Task '`）。
- fact-verified: SPEC R7 收斂檔三家 `RECONCILE-STAMP APPROVED`
  → `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` rc=0。

**假設**（請優先攻）：

- assumed: **§T 追溯表宣稱 100% 覆蓋，但主委只做了 Task 級對照，未逐條核對 SPEC 內的具名 finding ID**
  （`D-*`／`E-*`／`F-*`／`G-*`／`H-*` 系列）是否都有 TODO 落點。**這是最可能漏的地方。**
- assumed: **每個 Task 的「實作要點」足以讓冷啟動執行端不回讀 SPEC 就能寫碼**。未經第三方實測。
- assumed: **B1–B7 的批次切分不會產生同檔衝突**。主委只檢查了 `gate_check.sh:86` 與 `_emit_family_result` 兩處，
  未窮舉所有跨批次同檔改動。
- assumed: **`TEST-3.3-PROVISIONAL` 三條件（§0 含字樣／Task 3.3 標未完工／`票 B-14` 標未定稿）真的可被測試機械讀取**。
  未實作，未驗證第三條（票面狀態在 `handoffs/20260801-GOV-AMEND-BACKLOG.md`，跨檔）。

## 本輪必查（**這就是全部工作**）

| # | 查什麼 | 通過條件 |
|---|---|---|
| 1 | **追溯完整性** | SPEC 內每個具名 ID（`D-*`／`E-*`／`F-*`／`G-*`／`H-*`／`E-SCOPE`／`OPEN-*`）在 TODO 有落點或有具名「合理合併」說明。**逐條列出缺失。** |
| 2 | **深度紅線** | 每 Task：實作要點 ≥3 且含偽碼／修改檔案到函式名／邊界 ≥2 具體／驗證有具體通過條件。**逐 Task 判定，非抽查。** |
| 3 | **§0 三項狀態宣告可機械驗證** | `B-24` 部分完成／reclaim 孤兒需人工清理／timeout `PROVISIONAL` ——三者是否真的有對應的可執行斷言，或只是寫在散文裡？ |
| 4 | **批次切分正確性** | B1–B7 的依賴是否完整？是否有跨批次同檔改動會衝突？Gate 命令是否真的可執行？ |
| 5 | **`rc` 斷言配對** | SPEC §V `票 B-24` 紀律面要求：**每一條 `ASSERT … rc` 都必須有同 Task 內對應的狀態斷言**。逐條檢查，列出違反者。 |
| 6 | **測試可證偽性** | 每條 mutation 是否真的會讓對應斷言轉紅？有無「廉價綠燈」（恆真斷言／只驗不拋錯）？ |

## 🔴 不受理範圍（命中標 `OUT-OF-SCOPE`，不計入 findings）

1. **重開 SPEC 的設計裁決**——SPEC 已七輪收斂並三家戳記。若你認為某個 SPEC 決策有誤，
   請標 `OUT-OF-SCOPE` 並指名，**不作為 TODO 的 BLOCKING**。**例外**：該決策使 TODO 無法被執行端實作。
2. `E-SCOPE` 四項（`票 B-35`／`B-34`／`B-24` 機械強制面／`B-15` FP-2 定位）。
3. R7 兩條具名殘留（`H-1` 允許清單枚舉／`H-2` reclaim 孤兒）——已具名接受並寫入 §0。
4. **防蓄意繞過**類——本批目標是**擋意外**。
5. 措辭／可讀性／命名一致性。
6. 「委員債務無 OPEN」不必查（派工本身會開債，固有競態）。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ TODO 可標 Internal Frozen，進實作。**

請在 `## 出場判準核算` 給出逐項數字與是否需要第二輪的結論。

## 硬性要求

1. **禁改碼、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
4. 每條 finding 附**可執行修法**（具體到「哪個 Task 的哪一欄補什麼」），不得只說「不夠詳細」。
5. 第 1 項（追溯完整性）**必須逐條列出**你實際 grep 到的 SPEC ID 清單與其 TODO 落點，
   **不得只寫「大致完整」**——這是本輪最高價值的檢查。

## 產出

上表六項的逐項判定、findings（若有）、`## 出場判準核算`、對 §0 四條假設的攻擊結果。
收尾清 /tmp workdir（保留 claude-501）。
