# GAP-1 B2 實作 code review / grok | task-id=20260818-GAP1-B2-REVIEW-R14

brief-kind=review；家族=GROK；輪次=R14；審查標的 commit `7f0decc8`（HEAD 另有 `fbb12301` mutation 鎖，B2 本體未再改）；禁改碼／禁 commit。

## Verdict：需修補後進 B3

Task 2.1–2.3 契約本體（16 頂層鍵、A1-7 計數由構造成立、fail-closed `n_unknown`、唯一寫入口）**大體成立**；
`pytest tests/momentum/Analysis/strategy_validation/ -q` → **90 passed rc=0**。mutation receipt
`handoffs/run_receipts/20260818T030000Z-gap1-mutation-locked.log` 八條皆 rc=1（本輪**未**重跑探針，遵 brief 鎖／併發指引）。

但主委本輪四條 assumed 中有三條被可執行反例削弱或推翻：

| assumed | 本輪結論 |
|---|---|
| `set(row)!=set(schema)` 無語意損失 | **部分成立**——契約只有單一 `ledger_row_invalid`，診斷粒度損失是刻意簡化；非正確性 bug |
| 單次 write + O_APPEND 含多行程足夠 | **推翻**——`evaluation_id` 唯一性是讀後寫 TOCTOU；多行程可寫入同 id 兩列（見 P1-05） |
| annualized 計入 `n_rows_rejected` 符合 TODO 字面且合理 | **字面不一致、字面不合理、實作較合理**——測試已靜默改寫 ⑥b（見 P1-01） |
| monkeypatch `ledger_path` 未使路徑推導失覆蓋 | **推翻**——路徑推導邏輯零測試覆蓋（見 P1-03） |

另：`metric_value=NaN` 可寫入且進入 `valid_sharpe_values`（見 P1-02）；`snapshot_hash` 分隔符可碰撞（見 P1-04）。
非根本缺陷、不需重作 B2；建議修補後進 B3。

**工作區觀察**：B2 標的檔 clean；工作區另有無關 dirty／untracked（`.claude/gate/audit.log`、`handoffs/reconcile/...`、`scripts/governance_families.json` 等）。本輪未改任何產品碼。

---

## 段 A — 契約符合度（Task 2.1–2.3）

### Task 2.1 — **符合**
- 頂層鍵**恰 16**（集合相等，非只數個數）：`version`／`capability_status_ref`／`ledger_record_keys`／`n_fields`／`report_sections`／`eligibility_keys`／七組 `*_values`／`reasons`／`reason_conditions`。
- `n_fields` 六值含 `n_rows_rejected`；`reasons` 12 值含 `reporter_failed`；`set(reason_conditions)==set(reasons)`。
- `universe_scope_values == ["ledger_recorded_only"]`。
- 五節 `required_keys` 與 A1-13 **逐字**相等（本輪對五節實比）。
- `capability_status` 六值字面**不**在策略契約內；`capability_status_ref` 於執行期 dereference IC 契約，缺檔／缺鍵 raise（測試覆蓋）。

### Task 2.2 — **語意符合 A1-7；⑥b 字面見段 D**
- `n_evaluated`＝schema-valid；`n_valid_metrics`／`n_failed_or_pruned` 依 `metric_valid` 二分；不變式由構造保證。
- schema-invalid（JSON 錯／缺鍵／型別／額外鍵／`metric_unit` 非法）→ `n_rows_rejected`，**不**進 `n_evaluated`。
- 缺檔／真·零列 → `status=unavailable`、`reason=n_unknown`、`n_for_dsr=0`（禁 n=1）。
- 全列非法時 `n_rows_rejected>0` 但仍 `reason=n_unknown`——見 P2-01。

### Task 2.3 — **符合（單執行緒／執行緒池）；多行程唯一性不成立**
- `append_trial_attempt` 為唯一寫入口；schema 失敗 raise 且不寫半列；同檔重複 `evaluation_id` 在**序列**路徑拒收。
- `ThreadPoolExecutor(2)×50` 測試通過；多行程 TOCTOU 見 P1-05。

```
VERIFY: venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ -q
→ 90 passed, rc=0
```

---

## 段 B — 攻主委實作決定

### B1. `set(row) != set(schema)` 一次擋缺鍵＋額外鍵
- 缺鍵與多鍵在 reason 上**無法區分**；契約只有 `ledger_row_invalid` 一值，故屬**刻意**診斷折衷，非漏設計。
- 正確性無損（兩者皆應 reject）；除錯時需另看 raw row。→ P3-01。

### B2. `float` 接受 `int`
- JSON `1` vs `1.0` 相容合理；`metric_value=1` 通過。
- 整數 Sharpe 罕見；統計失真風險低。更大問題是 **非有限 float**（NaN/inf）也被接受——見 P1-02。

### B3. `bool` 防冒充 + 漏網同型陷阱
- `bool` 冒充 `int`／`float` 已擋（`metric_valid=1` 拒、`metric_value=True` 拒）。
- **漏網**：
  1. `numpy.float64` 被接受（`float` 子類）、`numpy.int64` 被拒（**非** `int` 子類）——不對稱。
  2. `str` Enum（`class S(str, Enum)`）通過 `str` 欄。
  3. `metric_valid="true"` 正確拒絕。
  4. **`float("nan")`／`inf` 通過**並可寫入帳本。→ P1-02、P2-03。

### B4. 併發寫入
1. **多行程**：O_APPEND 不解決 **evaluation_id 讀後寫**；強制在 check 與 write 之間對齊兩行程 ⇒ **兩列同 id**（TOCTOU_CONFIRMED）。→ P1-05。
2. **PIPE_BUF**：本機 `PC_PIPE_BUF=512`；典型合法列 encode 後 **≈610B 已 > PIPE_BUF**。宣稱「單次 write 不交錯」在 POSIX 嚴格語意下對本 schema 的典型列**不成立**（本輪 4×~8KB 未重現交錯，但不能當證明）。→ P2-02。
3. **TOCTOU**：見上；執行緒池下因 GIL／時序常只寫 1 列，**測試綠 ≠ 多行程安全**。

### B5. `reason = reasons_seen[0]`
- 今日讀路徑實質只累積 `ledger_row_invalid`（+ 全非法時覆寫為 `n_unknown`）。
- `reasons_seen` 已保留完整集合；主欄位取首個在多 reason 未來擴張時會遮蔽。現階段影響有限；全非法遮蔽見 P2-01。

### B6. `_contract_cache` 模組級快取
- 僅 default 路徑快取；tmp drift 測試不命中快取——測試假綠風險低。
- 與 Rule 8「不得有 mutable global singleton」精神衝突（現況專案仍有殘留 singleton 技術債）。
- 同行程內改 default 契約檔會拿到舊值。→ P3-02。

---

## 段 C — 測試品質

### `monkeypatch.setattr(ledger_mod, "ledger_path", ...)`
- **確認**：`test_ledger.py` 與 `test_ledger_conformance.py` 的 autouse fixture **整函式替換** `ledger_path`。
- `MomentumConfig.from_project_root().results_path / "strategy_validation" / f"{a}__{b}.jsonl"` **完全沒被測到**。
- 本輪手動呼叫真實 `ledger_path` ⇒ 路徑正確落在 `results/strategy_validation/sess__ds.jsonl`；但**無回歸鎖**。
- 修法：至少一則測試 **不** patch 整函式，改 patch `MomentumConfig.from_project_root` 回傳假 `results_path`，再斷言相對結構；或對 `ledger_path` 做純字串單元測。→ P1-03。

### 廉價綠燈
- 多數測試斷言計數／集合／reason，非只 smoke。
- `pytest.raises(ContractViolation)` 多處有 `match=`；部分裸 raise 可接受（conformance 缺鍵）。
- `test_valid_sharpe_values_only_per_period` docstring 已改成「annualized 屬 schema-valid」——**與 Frozen TODO ⑥b 字面相反**，且**未**斷言 `n_rows_rejected`。→ 併入 P1-01。
- `test_invalid_rows_rejected_with_named_reason` 只斷言 `reasons_seen`，不斷言 `got.reason`——掩蓋全非法 → `reason=n_unknown`。→ P2-01。

### Mutation
- 讀 receipt：§V-5／7／8／9a／9b／10／13／15 皆 rc=1；§V-7 覆蓋缺檔 n=1。
- 本輪**未**並行跑探針。
- B2 建議增補（非本輪 blocker 列 P 級）：
  - `metric_value=NaN` 仍進 `valid_sharpe_values` 應轉紅；
  - 多行程同 `evaluation_id` 應轉紅（或文件降級為 best-effort + 單寫者假設）；
  - `ledger_path` 結構 mutation（改目錄名）應轉紅。

---

## 段 D — 數值／契約正確性

### `snapshot_hash` 與 `|`
- 公式：`sha256(",".join(sorted(hashes)) + "|" + dataset_key + "|" + session)`。
- **碰撞反例**（本輪實跑同 digest）：
  - A：`hashes=["x"]`, `dataset_key="a|b"`, `session="c"` → payload `x|a|b|c`
  - B：`hashes=["x|a"]`, `dataset_key="b"`, `session="c"` → payload `x|a|b|c`
- `dataset_key` **無**禁止 `|` 的契約約束。→ P1-04。
- 修法：長度前綴／`json.dumps` 正規化／NUL 分隔／對各欄先 hash 再組合。

### `n_for_dsr = n_candidates_considered`
- 與 SPEC「DSR 之 N＝試過幾個**不同候選**」一致；同 candidate 多 attempt ⇒ considered=1、evaluated=2。**符合**。

### annualized 與 ⑥b
- **實作**：`metric_unit="annualized"` 為合法枚舉 ⇒ schema-valid ⇒ 計入 `n_evaluated`／`n_valid_metrics`，**不**進 `n_rows_rejected`，且不進 `valid_sharpe_values`。
- **Frozen TODO 驗證⑥b 字面**：「annualized row ⇒ 計入 `n_rows_rejected` 且不入 `valid_sharpe_values`」。
- **母 SPEC ⑥b** 亦寫「記 `reason=ledger_row_invalid`」。
- **A1-7** 定義 schema-invalid 僅含「`metric_unit` **非法**」——annualized 不在此列。
- **結論**：實作＝合理且對齊 A1-7；Frozen TODO/SPEC ⑥b 字面＝誤判合法枚舉為 schema-invalid；測試已靜默跟實作、偏離 Frozen 字面。須延伸檔修正 ⑥b，否則後續 agent 可能「修回」字面而破壞 A1-7 不變式。→ P1-01。

---

## Canonical findings

## GROK-R14-P1-01

**斷言**: Frozen TODO／母 SPEC 之 Task 2.2 驗證⑥b 要求 annualized 計入 n_rows_rejected 並記 ledger_row_invalid，但實作與 test 將其當 schema-valid（只排除出 valid_sharpe_values），且無 A1 修訂——驗收閘已靜默偏離 Frozen 字面。

**碼證**: TODO:210 字面 vs ledger.py:150-153 實作 vs test_ledger.py:121 docstring；VERIFY annualized+per_period 兩列 n_evaluated=2 n_rows_rejected=0 valid_sharpe=(1.1,)；A1-7 僅 metric_unit 非法才 schema-invalid；RECHECK 寫 annualized 合法列後比 TODO 字面與實作計數。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#3cc06afd3b47

[MAJOR] 信心度=High。實作選擇合理（合法枚舉不應 schema-reject）；失敗模式是文件／閘漂移——後續 agent 按 Frozen 字面「修好」測試會破壞 A1-7。修法：延伸檔作廢 ⑥b 之 n_rows_rejected 句，改為 schema-valid 但不入 valid_sharpe_values；測試加顯式 assert n_rows_rejected==0。

## GROK-R14-P1-02

**斷言**: _row_is_valid／append_trial_attempt 接受非有限 metric_value（NaN／inf）；metric_valid=True 時 NaN 進入 valid_sharpe_values，會在 B3 DSR statistics.variance 路徑投毒。

**碼證**: ledger.py:27-32,78-80 無 finite 檢查；ledger.py:234 json.dumps 預設 allow_nan=True；VERIFY append(nan) 檔內 metric_value: NaN 且 read 得 n_evaluated=1 n_rows_rejected=0 valid_sharpe_values=(nan,) status=ok；RECHECK 另測 inf。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。今日無生產者仍應在唯一寫入口 fail-closed。修法：math.isfinite(metric_value) 納入 schema；json.dumps(..., allow_nan=False)；讀側對非有限值計 n_rows_rejected。

## GROK-R14-P1-03

**斷言**: test_ledger.py 與 test_ledger_conformance.py 以 monkeypatch 整函式替換 ledger_path，使 TODO 規定的 MomentumConfig.results_path/strategy_validation/{session}__{dataset}.jsonl 路徑推導零覆蓋。

**碼證**: TODO:195 路徑公式；ledger.py:56-59 真實推導；test_ledger.py:18-25 與 test_ledger_conformance.py:20-26 autouse 全替換；測試目錄無 MomentumConfig/results_path 斷言；手動真實路徑正確但無鎖；RECHECK 改 strategy_validation 字面後測試仍全綠即假綠。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_ledger.py#43477bd8daf2

[MAJOR] 信心度=High。主委自承最可疑處，本輪確認。修法：至少一則測試 patch MomentumConfig.from_project_root（或 results_path）而非整顆 ledger_path，斷言 parent 名與檔名格式。

## GROK-R14-P1-04

**斷言**: snapshot_hash 以裸 | 拼接 artifact_hashes／dataset_key／research_session_id，當任一分量含 | 時不同輸入可產生相同 digest（provenance 碰撞）。

**碼證**: ledger.py:161-165 公式；VERIFY snap(["x"],"a|b","c")==snap(["x|a"],"b","c") 同 hex；dataset_key 契約僅 str 無禁 |；RECHECK 重算兩組 sha256 payload。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。修法：對各欄先分別 hash、或 json.dumps([sorted(hashes),dk,sid])、或長度前綴編碼，禁止可逆拼接歧義。

## GROK-R14-P1-05

**斷言**: append_trial_attempt 的 evaluation_id 唯一性是先掃檔再 append 的 TOCTOU；多行程在 check 通過後 write 前交錯時可寫入相同 evaluation_id 兩列，N／候選計數可被灌水。

**碼證**: ledger.py:219-237 無鎖讀後寫；VERIFY 鏡像控制流於 check/write 間 barrier 兩行程皆 WROTE n_lines=2 eids=['DUP','DUP'] TOCTOU_CONFIRMED；既有測試僅 ThreadPoolExecutor 同行程；RECHECK 多行程同 id 並發 append。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High（結構性漏洞已強制重現；無 barrier 時窗口窄但非零）。主委 assumed 含未來多行程生產者足夠 不成立。修法：fcntl.flock 包住掃+寫；或每 id O_CREAT|O_EXCL；或文件化單寫者並改測。今日無生產者可進 B3 但須登記殘留或本輪修。

## GROK-R14-P2-01

**斷言**: 當檔存在但零列 schema-valid（全非法）時 reason 被強制設為 n_unknown，掩蓋 reasons_seen 中的 ledger_row_invalid，與非法列應帶 ledger_row_invalid 字面的直觀／SPEC 驗證⑧部分衝突。

**碼證**: ledger.py:171-174 n_evaluated==0 強制 n_unknown；VERIFY 檔 {bad 得 status=unavailable reason=n_unknown n_rows_rejected=1 reasons_seen=(ledger_row_invalid,)；test_invalid_rows 只 assert reasons_seen 不斷言 got.reason；RECHECK 只寫非法列後讀 got.reason。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR 偏 P2] 信心度=High。fail-closed 仍成立（status 非 ok、N=0）；運維會誤判無帳本而非帳本損壞。修法：n_evaluated==0 and n_rows_rejected>0 時 reason=ledger_row_invalid。

## GROK-R14-P2-02

**斷言**: 註解宣稱單次 write 併發追加不交錯（POSIX O_APPEND）在本機 PIPE_BUF=512 下對典型帳本列 encode 約 610B 並無 POSIX 原子性保證。

**碼證**: ledger.py:236 註解；VERIFY os.pathconf PIPE_BUF=512 且典型 12 鍵列 len(encode)约610；4 行程 x 8KB 本輪未見交錯不足為證；RECHECK 量 PIPE_BUF 與線長後 fuzz。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=Medium（標準語意高；實害需壓力才現）。修法：文件化單寫者；或寫入前強制線長<=PIPE_BUF；或檔級鎖。

## GROK-R14-P2-03

**斷言**: int 欄拒 numpy.int64，float 欄收 numpy.float64——未來 numpy 生產者會在 attempt_index 上噴 ContractViolation，而 metric_value 靜默通過，行為不對稱。

**碼證**: VERIFY _row_is_valid attempt_index=np.int64(0) False；metric_value=np.float64(1.2) True；RECHECK 同上。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=High。今日無生產者。修法：寫入口統一 int(x)/float(x) 正規化（拒 bool），或文件要求純 Python 純量。

## GROK-R14-P3-01

**斷言**: set(row)!=set(schema) 使缺鍵與額外鍵共用 ledger_row_invalid，診斷不可分；在契約單一 reason 設計下為刻意折衷。

**碼證**: ledger.py:70-71 一次 set 相等；契約 reasons 無 finer codes。

**來源摘要**: momentum/Analysis/contracts/strategy_validation_contract.json#4a0ef05b2e1a

[MINOR] 信心度=High。非正確性 bug。可選：錯誤訊息區分 missing vs extra（仍同一 reason 字面）。

## GROK-R14-P3-02

**斷言**: contract._contract_cache 為模組級可變快取（default 路徑），與 Rule 8 精神衝突；同行程改契約檔會讀到舊值。

**碼證**: contract.py:29,66-88 global cache；load 兩次 is 同一物件。

**來源摘要**: momentum/Analysis/strategy_validation/contract.py#de4d4a4270f0

[MINOR] 信心度=High。生產可接受；測試改 default 檔需 cache clear 或重載模組。屬既有 singleton 技術債族。

---

## 被當成事實的未驗證假設（§0）

1. 「單次 write + O_APPEND 於多行程足夠」→ **assumed，本輪推翻**（P1-05／P2-02）
2. 「annualized → n_rows_rejected 符合 TODO 且合理」→ **字面 assumed 當 fact；實作未遵守字面且字面不合理**（P1-01）
3. 「monkeypatch ledger_path 仍覆蓋路徑推導」→ **assumed，本輪推翻**（P1-03）
4. 「schema float 足以保護 metric 品質」→ **assumed；NaN 反例**（P1-02）

## 建議修補優先序（進 B3 前）

1. **必**：P1-02 非有限 metric 拒收；P1-01 延伸檔對齊 ⑥b＋測試鎖 `n_rows_rejected==0`；P1-03 路徑推導測試
2. **必（或登記殘留）**：P1-05 多行程唯一性；P1-04 snapshot 編碼
3. **應**：P2-01 全非法 reason；P2-02 文件化 PIPE_BUF／單寫者
4. **可**：P2-03／P3-*

---

ASSUMPTIONS_VERIFIED: 16 頂層鍵／n_fields 六值／reasons 12+reporter_failed／reason_conditions 雙向／A1-13 五節／capability 不複列+ref 真解析；A1-7 計數構造；90 pytest；annualized 實測 n_rej=0；NaN 寫入+valid_sharpe；snapshot `|` 碰撞；TOCTOU 強制雙寫同 id；ledger_path 測試全 monkeypatch；PIPE_BUF=512<典型列長
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ -q` → 90 passed rc=0；mutation 未重跑（讀 locked receipt 8/8 rc=1）；自建 TOCTOU／NaN／hash 探針如上
FAILURES_SEEN: none in product tests
SCOPE_CHANGES: none（只產 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）

STATUS: DONE
