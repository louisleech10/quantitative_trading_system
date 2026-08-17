# GAP-1 B2 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap1-b2-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–D 是「請你查證的項目與我的待攻假設」，非主委結論；
> 結論在你們的產出與收斂檔。檔頭 `fact-verified:` 附主委實跑命令。

brief-kind: review

## 審查標的（commit `7f0decc8`；`git show 7f0decc8 --stat`）
- 契約：`momentum/Analysis/contracts/strategy_validation_contract.json`（16 頂層鍵）
- 程式：`momentum/Analysis/strategy_validation/contract.py`、`ledger.py`
- 測試：`tests/momentum/Analysis/strategy_validation/test_{contract,ledger,ledger_conformance}.py`
- 契約來源：TODO **FROZEN R3** Task 2.1–2.3 ＋延伸檔 **A1-1..A1-20**（衝突以延伸檔為準）
- 🔴 **B1 之教訓請帶進本輪**：上一批我在延伸檔寫下未經反例驗證的宣稱（A1-19「不會靜默退回 730」），
  被你們兩家用可執行反例推翻。本批請同樣**優先攻我的宣稱**，而非只核對條文。

## 本輪任務（四段皆必答）
**段 A — 契約符合度（逐 Task）**
- 2.1：頂層鍵**恰 16**？`n_fields` 六值含 `n_rows_rejected`？`reasons` 12 值含 `reporter_failed` 且
  `reason_conditions` 雙向相等？`universe_scope_values`？五節 `required_keys` 與 A1-13 **逐字**相等？
  `capability_status` 是否真的**沒有**在策略契約內複列（六值字面 grep 應為 0）且 ref 為**執行期** dereference？
- 2.2：計數語意是否如 A1-7（`n_evaluated` = schema-valid；`n_valid_metrics`／`n_failed_or_pruned` 依
  `metric_valid` 二分；schema-invalid 只進 `n_rows_rejected`）？不變式是否**由構造成立**而非靠測試巧合？
  缺檔／零列是否 fail-closed `n_unknown`（**禁** n=1）？
- 2.3：`append_trial_attempt` 是否為唯一寫入口、失敗不寫半列、重複 `evaluation_id` 拒收？

**段 B — 🔴 攻我的實作決定（本輪重點）**
1. **`_row_is_valid` 用 `set(row) != set(schema)` 一次擋掉「缺鍵＋額外鍵」**：這是否讓
   「缺必填」與「多了未知鍵」在 reason 上無法區分？契約只有一個 `ledger_row_invalid`——這是刻意還是漏設計？
2. **`float` 型別接受 int**（`_PY_TYPES["float"] = (float, int)`）：JSON 的 `1` 與 `1.0` 視為相容。
   這會不會讓 `metric_value` 收到整數而在後續統計上失真？有無可執行反例？
3. **`bool` 防冒充**：我對 `bool`/`int` 做了特判（bool 是 int 子類）。請找出**我漏掉的同型陷阱**
   （例如 `int` 欄位收到 `numpy.int64`、`str` 欄位收到 `Enum`、或 `metric_valid` 收到 `"true"`）。
4. **併發寫入**：我以「單次 `write()` + POSIX `O_APPEND`」宣稱不交錯，測試用 `ThreadPoolExecutor(2)×50`。
   請攻：① 這在 **多行程**（非多執行緒）下是否仍成立？② 超過 PIPE_BUF／單行 >4KB 時？
   ③ `evaluation_id` 重複檢查是**讀後寫**（TOCTOU）——兩個並發寫入同一 id 是否可能都通過？**請給反例**。
5. **`read_trial_ledger` 之 reason 取 `reasons_seen[0]`**：當同時有多種問題時只回第一個。
   這是否會遮蔽資訊？契約是否應允許多 reason？
6. **快取**：`contract.py` 之 `_contract_cache` 為模組級全域（僅 default 路徑快取）。
   這是否與 Rule 8「不得有 mutable global singleton」衝突？測試若先載入再改檔會不會拿到舊值？

**段 C — 測試品質（禁廉價綠燈）**
- `test_ledger.py` 以 `monkeypatch.setattr(ledger_mod, "ledger_path", ...)` 改路徑：
  這是否讓**真正的路徑推導邏輯**（`MomentumConfig.results_path / "strategy_validation" / f"{a}__{b}.jsonl"`）
  **完全沒被測到**？若是，請給修法（我懷疑這是本批最大的測試漏洞，請確認）。
- 有無測試只驗「不 crash」而未驗值？有無 `pytest.raises` 過寬（例如只 `ValueError` 而未驗訊息／型別）？
- mutation：`bash scripts/gap1_b1_mutation_probe.sh`（**8 條**；🔴 **有互斥鎖，請勿三家同時跑**——
  前輪三家並行導致 baseline 不穩、codex 兩度 BLOCKED；併發時會 `exit 3`。
  建議：**只由 codex 跑一次**，另兩家讀 receipt `handoffs/run_receipts/20260818T030000Z-gap1-mutation-locked.log`）。
  §V-7 之外，B2 是否還有該有而沒有的 mutation？

**段 D — 數值／契約正確性**
- `snapshot_hash` ＝ `sha256(",".join(sorted(artifact_hashes)) + "|" + dataset_key + "|" + research_session_id)`：
  分隔符 `|` 若出現在 `dataset_key` 內是否會造成**碰撞**（不同輸入同 hash）？請給反例或證明不可能。
- `n_for_dsr = n_candidates_considered` 是否與 SPEC「DSR 之 N ＝試過幾個不同候選」一致？
- `valid_sharpe_values` 只收 `sharpe∧per_period∧valid`——`metric_unit="annualized"` 之列我**計入
  `n_rows_rejected`**（因 `metric_unit` 屬枚舉合法值，但 DSR 只收 per_period）。
  🔴 **請攻這條**：annualized 是契約**合法**枚舉值，把它當 schema-invalid 是否為誤判？
  正確做法應是「schema-valid 但不入 `valid_sharpe_values`」嗎？（TODO Task 2.2 驗證⑥b 之字面為
  「該 row 記 `reason=ledger_row_invalid` 且不進 `valid_sharpe_values`」——請判斷我的實作與該字面是否一致，
  以及**該字面本身是否合理**。）

## 範本
`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13 之 §0／§1／§3 與 canonical 四欄。
ID＝`## <FAMILY>-R14-P<0-3>-<NN>`，**本輪輪次=R14**。零 findings 用 sentinel `## <FAMILY>-R14-P3-00`。

## ⚠️ 前置說明
- **禁改碼／SPEC／TODO／延伸檔；禁 commit／push**；只產你自己的 review 檔。
- 可自由跑測試；跑完貼 rc。**探針有鎖，勿並行**（見段 C）。
- 既有紅 2 條（`test_model_hyperparam_enhanced`）與本 epic 無關，勿列為 finding。
- 🔴 主委本輪**不動工作區**（前兩次戳記輪因此被 codex 正確 BLOCKED）。若你發現工作區變動，請具名回報。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ -q` → **90 passed**（Claude 實跑）
fact-verified: `bash scripts/gap1_b1_mutation_probe.sh` → rc=0、8 條皆 rc=1（receipt 見段 C）
fact-verified: 契約頂層鍵 16、`n_fields` 6、`reasons` 12、`reason_conditions` 與 `reasons` 雙向相等（Claude 實跑 json 檢查）
assumed: `set(row) != set(schema)` 之一次性檢查無語意損失 ← 請攻
assumed: 單次 write + O_APPEND 於本專案使用情境下足夠（含未來多行程生產者）← 請攻，要反例
assumed: 把 `metric_unit="annualized"` 之列計入 `n_rows_rejected` 符合 TODO 字面且合理 ← 請攻
assumed: `monkeypatch ledger_path` 之測試策略未使路徑推導邏輯失去覆蓋 ← 請攻（我自承這是最可疑處）

## Time-box
優先序＝段 B（我的決定）＞ 段 D（數值／契約）＞ 段 C（測試品質）＞ 段 A（條文符合）。
**不受理**：使用者裁決、已 Frozen 之 TODO 契約本身（要改請走延伸檔提案並說明為何非改不可）、
B3／B4 尚未實作之部分、前端、治理機制。

## 產出
Verdict（可進 B3／需修補後進 B3／有根本缺陷需重作）＋段 A–D 結論＋canonical findings。
收尾清 /tmp workdir（保留 claude-501）。
