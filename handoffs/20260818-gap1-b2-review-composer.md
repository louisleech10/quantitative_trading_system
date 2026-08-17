# GAP-1 B2 實作 code review（R14）— COMPOSER

**task-id**: `20260818-GAP1-B2-REVIEW-R14` | **family**: composer | **brief**: `handoffs/20260818-gap1-b2-review-BRIEF.md`
**審查標的**: commit `7f0decc8`（B2 Task 2.1–2.3）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ -q` → **90 passed** rc=0
- mutation receipt（唯讀）`handoffs/run_receipts/20260818T030000Z-gap1-mutation-locked.log` → baseline/post-restore rc=0、8 條 mutant rc=1
- `ledger_path(research_session_id='x', dataset_key='y')` → `.../results/strategy_validation/x__y.jsonl`
- `snapshot_hash` 碰撞探針：`dataset_key="a|b", session="c"` 與 `dataset_key="a", session="b|c"` → **同 hash** `690f6a9b75db556d…`
- `_row_is_valid` 型別探針：`Enum(str)` metric_unit → **valid=True**；`numpy.int64` attempt_index → valid=False；`"true"` metric_valid → valid=False
- annualized 單列實跑：`n_evaluated=1`、`n_rows_rejected=0`、`valid_sharpe_values=()`
- TOCTOU 探針（10 thread 同 `evaluation_id`）：success=1、lines=1（讀後寫無鎖，執行緒下僥倖未雙寫）
- 契約 JSON：頂層鍵 16、`n_fields` 6、`reasons` 12、`reason_conditions` 雙向相等、`capability_status` 六值字面 grep 策略契約 JSON=0

**工作區備註**：主委宣稱本輪不動工作區；`git status` 見 `.claude/gate/audit.log`、`handoffs/reconcile/.../synth.md`、`scripts/governance_families.json` 等**與 B2 標的無關**之 dirty／untracked，非本委員造成。

---

## Verdict：需修補後進 B3

段 A 契約條文**達標**；段 B／D 各有一項可執行反例（`snapshot_hash` 分隔符碰撞、Enum 型別陷阱）與段 C 路徑推導零覆蓋，**非根本重作**但應在 B3 前修補：`snapshot_hash` 改用不可碰撞之 tuple 編碼（或 length-prefix）、補 `ledger_path` 整合測試、`_row_is_valid` 對 `str` 欄位加 `type(value) is str`（或拒 `Enum` 子類）。TOCTOU 與 mutation 缺口列 P2／P3，可與 B3 wiring 一併處理或文件化為 G1-R1 生產者落地前提。

**BLOCKING**：0。**MAJOR**：2（P1-01、P1-02）。**MINOR**：3（P2-01、P2-02、P3-01）。

---

## 段 A — 契約符合度（Task 2.1–2.3）

| Task | 結論 | 要點 |
|------|------|------|
| **2.1** | **符合** | 頂層鍵恰 16（`test_exactly_sixteen_top_level_keys`）；`n_fields` 六值含 `n_rows_rejected`；`reasons` 12 含 `reporter_failed` 且 `set(reason_conditions)==set(reasons)`；`universe_scope_values==["ledger_recorded_only"]`；五節 `required_keys` 與 A1-13 逐字相等（`test_report_sections_required_keys_match_a1_13_literally`）；`capability_status` 未在策略契約 JSON 複列六值字面，`capability_status_ref` 執行期 dereference IC 契約且缺檔／缺鍵 raise。 |
| **2.2** | **符合（見段 D ⑥b 字面）** | `n_evaluated`＝schema-valid；`n_valid_metrics`／`n_failed_or_pruned` 依 `metric_valid` 二分且不變式由構造保證；schema-invalid 進 `n_rows_rejected`；缺檔／零列 ⇒ `status=unavailable`、`reason=n_unknown`（禁 n=1）。 |
| **2.3** | **符合** | `append_trial_attempt` 為唯一寫入口；schema 失敗 raise 不寫半列；重複 `evaluation_id` 拒收；2×50 執行緒併發實測 100 行皆可 `json.loads`。 |

---

## 段 B — 攻主委實作決定

| # | 議題 | 結論 |
|---|------|------|
| **1** `_row_is_valid` 一次 `set` 比對 | **刻意且與契約一致**。契約／A1-7 僅定義單一 `ledger_row_invalid`；缺鍵與額外鍵語意上等價於「不符 ledger_record_keys」，無需區分 reason。 |
| **2** `float` 接受 `int` | **可接受**。JSON 整數與浮點互通；`valid_sharpe_values` 收集時 `float(row["metric_value"])`，未見統計失真反例。 |
| **3** 同型陷阱 | **有漏網**：`str` 欄位（含 `metric_unit`）接受 `str` 子類 `Enum`（見 P2-01）；`numpy.int64` 已拒；`"true"`／`int` 冒充 `bool` 已拒。 |
| **4** 併發寫入 | 單次 `write`+`O_APPEND` 對**執行緒**內短行有效（測試通過）。**多行程**與 **TOCTOU**：`evaluation_id` 檢查為讀全檔後再 append，無 `flock`／原子 rename（見 P2-02）；超 PIPE_BUF 風險對 JSONL 單行通常低於 id 競態。 |
| **5** `reasons_seen[0]` | **可接受**。`LedgerReadResult.reasons_seen` 保留完整 tuple；頂層 `reason` 為契約單值欄位，取第一個契約 reason 合理；混合 invalid 列皆映射同一 `ledger_row_invalid`。 |
| **6** `_contract_cache` | **Rule 8 技術債**（模組級 mutable cache）；預設路徑唯讀場景可接受；測試用 `path=` 可繞過，生產契約檔熱更新會 stale——列 P3 備查，非 B2 阻擋。 |

---

## 段 C — 測試品質

- **monkeypatch `ledger_path`**：**確認為最大覆蓋洞**（見 P1-02）。`ledger.py:56-59` 之 `MomentumConfig.from_project_root().results_path / "strategy_validation" / f"{a}__{b}.jsonl"` **零測試**；三檔 ledger 測試皆 autouse patch。
- **廉價綠燈**：核心計數／fail-closed 有值斷言；`test_unreadable_file_raises` 驗 OSError 非僅不 crash。`pytest.raises(ContractViolation)` 多數帶 `match=`；`test_ledger_conformance` 之 invalid record 僅 `ContractViolation` 無 match——可接受。
- **mutation**：receipt 八條含 §V-7 全轉紅；B2 專屬缺口見 P3-01（`snapshot_hash`、Enum 型別、`ledger_path` 推導等無 probe）。

---

## 段 D — 數值／契約正確性

- **`snapshot_hash`**：`|` 分隔 `dataset_key` 與 `research_session_id` **可碰撞**（見 P1-01）；`artifact_hashes` 內容未參與邊界歧義但 session/dataset 邊界不安全。
- **`n_for_dsr = n_candidates_considered`**：與 SPEC「DSR 之 N＝試過幾個不同候選」一致（`len(candidate_ids)`）。
- **annualized 列**：主委 brief 假設「計入 `n_rows_rejected`」**被反例推翻**。`metric_unit_values` 含 `annualized`（契約合法枚舉）；A1-7 規定 schema-invalid 才進 `n_rows_rejected`；實作與 `test_valid_sharpe_values_only_per_period` docstring 一致——**schema-valid、不入 `valid_sharpe_values`**。TODO Task 2.2 驗收⑥b 字面「annualized ⇒ n_rows_rejected」與 A1-7／契約矛盾，應走延伸檔修正 TODO 字面而非改實作。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| 90 passed | fact-verified | **覆核 rc=0** |
| mutation 8 條 rc=0 | fact-verified（receipt） | **唯讀覆核** |
| 契約 16 鍵／reasons 12 等 | fact-verified | **覆核** |
| `set(row)!=set(schema)` 無語意損失 | assumed→**verified** | 契約僅單一 `ledger_row_invalid` |
| O_APPEND 含多行程足夠 | assumed→**部分推翻** | 執行緒 OK；多行程 id 檢查 TOCTOU（P2-02） |
| annualized→`n_rows_rejected` | assumed→**disproved** | 實跑 `n_evaluated=1`；A1-7 支持現行實作 |
| monkeypatch 未使路徑推導失覆蓋 | assumed→**verified** | 零 `ledger_path(` 整合測試（P1-02） |

---

## Findings（canonical）

## COMPOSER-R14-P1-01

**斷言**: `snapshot_hash` 以裸 `|` 拼接 `dataset_key` 與 `research_session_id`，存在不同 `(dataset_key, session)` 組合產生相同 SHA-256 的可執行碰撞。

**碼證**: `ledger.py:161-165`：`",".join(sorted(artifact_hashes)) + "|" + dataset_key + "|" + research_session_id`。RECHECK：`venv/bin/python -c` 計算 `snap({"h1"},"a|b","c")` 與 `snap({"h1"},"a","b|c")` → 兩者皆 `690f6a9b75db556d…`（本輪實跑 collision=True）。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。不同研究 session／dataset 組合可綁到同一 `snapshot_hash`，Task 3.2 snapshot 守衛可能誤判或漏判 `ledger_snapshot_mismatch`。修法：改用 length-prefix／JSON tuple／`\x00` 等不可歧義編碼，並加碰撞回歸測試。

---

## COMPOSER-R14-P1-02

**斷言**: 全部 ledger 測試以 `monkeypatch.setattr(ledger_mod, "ledger_path", …)` 繞過真實路徑推導，使 `MomentumConfig.results_path` 與 `f"{session}__{dataset}.jsonl"` 命名**零覆蓋**。

**碼證**: `test_ledger.py:17-25`、`test_ledger_conformance.py:20-26` autouse patch；`ledger.py:56-59` 真實 `ledger_path` 無任何測試 import 不 patch 之路徑。RECHECK：`rg 'ledger_path' tests/momentum/Analysis/strategy_validation` 僅見 monkeypatch，無 `MomentumConfig` 斷言。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。`results_path` 配置錯誤或檔名模板回歸不會被 90 條測試抓到。修法：加一則不 patch 之整合測試（`monkeypatch.setenv`／tmp `MomentumConfig`）斷言 `ledger_path(...)` 結尾路徑；或抽純函式 `_ledger_filename(session, dataset)` 單測。

---

## COMPOSER-R14-P2-01

**斷言**: `_row_is_valid` 對 `str` 欄位使用 `isinstance(value, str)` 語意（經 `_PY_TYPES["str"]=(str,)`），`enum.Enum` 子類可冒充 `metric_unit` 等字串欄位通過 schema。

**碼證**: `ledger.py:77-80`；本輪探針 `class S(str, Enum): X="per_period"` → `_row_is_valid(..., metric_unit=S.X)` **valid=True**。RECHECK：同上 Enum 探針。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=High。生產者若傳 Enum 物件，`json.dumps` 可能失敗或序列化意外；讀端 `isinstance` 過寬。修法：`type(value) is str` 或拒絕 `enum.Enum` 實例；補測試。

---

## COMPOSER-R14-P2-02

**斷言**: `append_trial_attempt` 之重複 `evaluation_id` 檢查為讀全檔後再 append，無檔案鎖或原子寫入，多行程並發下兩寫者可同時通過檢查並各寫一列。

**碼證**: `ledger.py:219-236` 先 `open("r")` 掃描再 `open("a")` write；無 `fcntl.flock`／`os.replace`。執行緒探針 10 併發同 id → 1 成功（GIL 下僥倖）；架構上為經典 TOCTOU。RECHECK：兩 process 同時 `append_trial_attempt` 同 `evaluation_id`（需 `fork`+`PYTHONPATH`）。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=Medium（多行程未在本機穩定重現，但讀-改-寫模式明確）。G1-R1 無生產者今日風險低；未來 `ProcessPool` 寫帳本可能 N 灌水。修法：`fcntl.flock`、或寫入前 `os.open(..., O_APPEND|O_EXCL)` 配合 sidecar lock；文件化單寫者假設。

---

## COMPOSER-R14-P3-01

**斷言**: mutation 探針僅覆蓋 B2 之 §V-7（缺檔回 n=1），未對 `snapshot_hash` 拼接、`ledger_path` 推導、Enum 型別陷阱等 B2 關鍵語意設 mutant。

**碼證**: `scripts/gap1_b1_mutation_probe.sh` 末段 §V-7 改 `ledger.py`；無 `snapshot_hash`／`ledger_path`／`_row_is_valid` str 檢查之 mutant。receipt `20260818T030000Z-gap1-mutation-locked.log` 八條皆 B1 域。RECHECK：grep probe 腳本無 `snapshot_hash`／`ledger_path`。

**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e

[MINOR] 信心度=High。B2 回歸依賴單元測試而無 mutation 自證。修法：B2 收案前增 §V-7b（delimiter 移除）、§V-7c（id 檢查刪除）等；或 B3 gate 明列最低 mutant 集。

---

## §1 必查（11 類摘要）

1. 矛盾：TODO ⑥b vs A1-7（段 D，非實作 bug）。2. 漏項：`ledger_path` 整合測試（P1-02）。3. 不可測：無。4. quant：`snapshot_hash` 碰撞（P1-01）。5–8. 無阻擋。9. 測試：patch 洞（P1-02）、mutation 缺口（P3-01）。10–11. 無。

STATUS: DONE
