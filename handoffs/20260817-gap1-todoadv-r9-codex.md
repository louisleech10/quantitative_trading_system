# GAP-1 TODO R2 受限複驗 R9 — CODEX

task-id: `20260817-GAP1-X-REVIEW-R9`  
family: `CODEX`  
審查標的：TODO R2、A1-1..A1-15、母 SPEC R8、R8 收斂 J1-J6

## Verdict：需修補後 Frozen

R2 已實際重現三條 J1 數值處置，且兩條 codex 原始反例在新契約中有對應處置。新增機制仍有三個需在 Frozen 前修補的問題：AST wiring 的全函式 body 掃描可被條件／死分支假綠、reporter 的 `ValueError` 捕獲仍會吞掉呼叫方參數 bug、母 SPEC §R 仍宣稱 B3/B4 可獨立 revert 而 R2 TODO 已使 B4 依賴 B3。這些是局部契約／閘門修補，不是架構重作。

## 段 A：CODEX R8 findings closure

| R8 ID | 判定 | 原始反例重跑／R2 核對 | 仍開放可否具名殘留 |
|---|---|---|---|
| CODEX-R8-P0-01 | PARTIAL | top-K probe：ledger 50 個 ID、呼叫方 10 個 ID；count/hash 自洽但 set check=False，舊 literal guard 仍會印 `literal_guard_status=ok`。R2 新增 `frozenset(candidate_ids)==ledger_result.candidate_ids` 並明列 G1-R9，所以呼叫方子集已拒絕，但 ledger 自身是否完整仍未證明。 | yes；G1-R9 已具名，且 `universe_scope=ledger_recorded_only` 會強制降級。 |
| CODEX-R8-P0-02 | CLOSED | 原始 `rankdata((0.1,0.2))[2]` probe 仍以預期 `IndexError` rc=1 重現舊演算法缺陷；R2 以 `pos={original_col_index: compressed_position}` 並規定 champion 在 IS/OOS 非有限時 skip path，④d／§V-14 對應覆蓋。 | no。 |
| CODEX-R8-P1-03 | CLOSED | R2 移除 `budget_capped`，`eligibility_keys` 不增欄；`x>700` 改為 `ValueError`，不再以 `10**18` 破壞 `ub(budget)<=T<ub(budget+1)`。 | no。 |
| CODEX-R8-P1-04 | CLOSED | reporter 增加 `dataset_key`／`t_years`／`target_sharpe` optional 輸入；三者任一缺失明確走 `n_unknown`，三者齊備才讀 ledger，不再自創 `trial:<n>`。 | no。 |
| CODEX-R8-P1-05 | PARTIAL | R2 已把 catch-all 改為有限集合並要求 `TypeError` 5xx、捕獲時 `logger.error(..., exc_info=True)`；但集合仍含裸 `ValueError`，`assess_eligibility` 參數錯誤仍可被轉成 `reporter_failed`，見 `CODEX-R9-P1-02`。 | no；這是目前可修的 caller bug masking，不是外部依賴殘留。 |
| CODEX-R8-P1-06 | CLOSED | A1-6／TODO Task 1.4 將 `t_semantics` 改為 required，且固定 `bar_count` 非 DSR 合法輸入，三種語意之選定規則已寫死。 | no。 |
| CODEX-R8-P1-07 | CLOSED | A1-7／Task 2.2 將 schema-valid `metric_valid=False` 明確計入 `n_failed_or_pruned`，schema-invalid 另計 `n_rows_rejected`；Task 2.3 不變式由構造成立。 | no。 |
| CODEX-R8-P1-08 | PARTIAL | regex 已換成 AST，直接 dict／assignment／compare 形已覆蓋，helper／loop／`dict(**kwargs)`／`setattr` 會 fail-closed；但掃描整個 function body 的 Constant 仍可把未執行分支算入，見 `CODEX-R9-P1-01`。 | no；需修 wiring gate 本身。 |
| CODEX-R8-P1-09 | PARTIAL | TODO §B 已補 B4 依賴 B3 Task 3.3，A1-11 也補 B2 2.2；但母 SPEC §R:650-654 仍寫 B4 不依賴 B3 且可獨立 revert，見 `CODEX-R9-P1-03`。 | no；是文件契約漂移，應在 Frozen 前修正。 |
| CODEX-R8-P1-10 | CLOSED | registry G1-R3 改為 `user-ruling:2026-08-17 ... frontend`；Task 3.4 已提供空／降級 API 三鍵，理由不再是「後端無資料可顯示」。 | no。 |
| CODEX-R8-P1-11 | CLOSED | G1-R7 trigger 改為具名票 `GAP-1-R7-MC` 且 owner／ROADMAP 已指定；不再使用不可機械判定的「排程即可做」。 | no。 |
| CODEX-R8-P1-12 | CLOSED | G1-R8 自 registry 收回，ROADMAP 已建立 PA-CUMSUM 獨立小票並排在 GAP-1 B4 後；不再以不成立的 `blocked-by` 留置。 | no。 |

P0-01 的「PARTIAL」不是把新契約誤判為失敗：R2 明確承認純統計層無法證明 producer-side exhaustive coverage；本輪只確認呼叫方對已讀 ledger 的子集污染面已機械拒絕，G1-R9 保留完整性殘留。

## 段 B：J1 數值處置實跑

| 案例 | 實跑結果 | 判定 |
|---|---|---|
| `alpha_detectable`，`mu=0.01*0.15`，default RNG `(1200,50)` | PBO `0.0000`；條件 `<0.30` | PASS |
| 全噪音 band，`rng.default_rng(20260817)`、`M.shape=(1200,50)` | PBO `0.6483`，落在 `[0.30,0.70]` | PASS |
| 全噪音兩變體 | `(50,1200).T`=`0.6158`；legacy seed=`0.5357` | 支持放寬 band；固定 default RNG 仍可重現 |
| `alpha_undetectable`，`mu=0.01*1.0/sqrt(8760)` | default RNG=`0.5411`；轉置變體=`0.6201`；legacy=`0.5487`，均 `>0.40` | PASS |
| §V-4 新 mutation：champion 改由 OOS metric 選 | noise baseline=`0.6483`→mutation=`0.0000`，noise band 轉紅；alpha_detectable baseline=`0.0000`→`0.0000` | PASS，至少一條轉紅 |
| Task 3.1 驗收⑨ | 20-seed mean=`0.843077`；解析值=`0.833943`；relative error=`0.01095279`；mean `<=1.0`；per-seed max=`1.216377` | PASS；只對 mean 下上界，未錯誤要求 all-seed |

實跑命令：

- `venv/bin/python handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.py` → rc=0；輸出含上述三 RNG 變體、alpha sweep、`E[maxSR]/sqrt(V)` 三點。
- `venv/bin/python handoffs/run_receipts/20260817T150000Z-gap1-minbtl-conservatism-probe.py` → rc=0；輸出 `mean(max annualized SR)=0.843077`、`max=1.216377`、解析值 `0.833943`。
- 等價 OOS-champion probe → `noise baseline=0.6483 mutation_oos_champion=0.0000`、`alpha_detectable baseline=0.0000 mutation_oos_champion=0.0000`，rc=0。
- `venv/bin/python -c ... rankdata((0.1,0.2))[2] ...` → rc=1、`IndexError`；此為原始缺陷反例，非 R2 產品測試失敗。
- top-K 等價 probe → `count_check=True hash_self_consistent=True set_check=False literal_guard_status=ok`，說明 R8 舊 literal guard 的缺陷；R2 新 set equality 規則會拒絕此案例。
- `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS (todo)` rc=0。

全噪音「924 paths 高度相關」足以作為固定 seed band 放寬的合理解釋，三變體的實測散布也與其一致；它不是對有效獨立樣本數的正式估計。R2 已把 RNG API、形狀、seed、dtype 與 provenance 寫死，因此本輪不新增多 seed 平均 finding。

## 段 C：新增機制攻擊面

### 1. AST wiring（A1-11／Task 2.4）

helper、`**dict`／`dict(**kwargs)`、迴圈、`setattr` 或跨檔 alias 若沒有可直接取得的 `ast.Constant`，依 R2 的 `[unresolved]`／缺鍵邏輯會 fail-closed（通常 rc=1），不是假綠；這是保守但可能誤擋的邊界。真正的假綠在於目前文字要求掃 function body 內的 Constant，沒有控制流／可達性條件。可執行反例：

```python
def build_validation_section():
    eligibility = {}
    if False:
        eligibility = {
            "eligible": None,
            "required_years_upper_bound": None,
            "available_years": None,
            "trials_budget": None,
            "trials_used": None,
            "target_sharpe": None,
            "n_source": "assumed_not_ledgered",
            "display_downgrade": True,
            "warning_text_key": "strategy_validation.downgraded",
        }
    return {"eligibility": eligibility, "min_btl": {}, "dsr": {}, "pbo": {}, "provenance": {}}
```

按 R2 所描述的「Return＋function body 內 ast.Dict Constant 鍵集合」，W1 看到五個 section，W4 看到九個 eligibility keys；但執行結果 `runtime_eligibility={}`。等價 AST probe 實跑輸出 `return_sections=['eligibility','min_btl','dsr','pbo','provenance']`、九個 `w4_seen`、`runtime_eligibility={}`。需補一條控制流／不可達 mutation，或採更窄的規則：只接受所有路徑上直接構造的 canonical return dict，對 conditional／loop／helper／unpack／setattr 一律 rc=1。

### 2. `universe_scope`（A1-4）

本輪判定 R2 方案在指定報告路徑足夠誠實：`ledger_recorded_only` 明示「只證到 ledger 已記錄集合」，Task 3.3 即使三關 `status=ok` 也強制 `display_downgrade=True`／非空警語，API 又只投影 eligibility、downgrade、warning 三鍵，避免直接把 PBO value 暴露成前端推薦依據。

仍存在直接呼叫純函式後只讀 `PBOResult.value`、忽略 `universe_scope` 的一般性旁路；但目前新模組無既有 caller，且這正是 A1-4／registry G1-R9 已具名的 producer-side completeness residual，不是本輪新 finding，也不應宣稱 top-K 完整性已關閉。較嚴的 producer conformance gate 應在 G1-R1 落地後把 scope 升為 `producer_conformance_verified`，而非現在把 PBO 永久禁用。

### 3. 例外分類（A1-8）

集合 `(OSError, json.JSONDecodeError, ContractViolation, ValueError)` 不夠窄。`assess_eligibility(t_years=-1.0, ...)` 的參數驗證會 raise `ValueError`；依 TODO:319-324，reporter 會把它轉成 `reporter_failed` 的 2xx 降級回應。實跑等價 probe 輸出 `negative_t_years='reporter_failed'` rc=0。應移除裸 `ValueError`，讓參數／程式錯誤上拋，或建立專用的資料不可用例外階層，只捕獲明確可預期的 ledger／JSON／I/O failure；`TypeError` 測試不足以覆蓋此路徑。

### 4. `n_rows_rejected`（A1-7）

六欄語意自洽：schema-valid 列進 `n_evaluated`；其中 `metric_valid=True/False` 分別進 `n_valid_metrics`／`n_failed_or_pruned`；schema-invalid 列只進 `n_rows_rejected`，不進 evaluated；`n_candidates_considered` 只取 schema-valid 的 distinct candidate IDs，因此在拒絕列或 producer 缺漏下仍是 lower bound。`n_is_lower_bound=True` 是明示的保守語意，不是完整 universe proof；兩者不衝突。

Task 2.3 conformance 是可證偽的：合法 `metric_valid=False` 列會測出 failed 計數；缺鍵／錯型／重複 ID／並發寫入會分別影響驗收；schema-invalid fixture 已在 Task 2.2 直接檢查 `n_rows_rejected`。本項無新 finding。

### 5. Task 2.4 移至 B4 末（A1-11）

新拓撲確實使母 SPEC §R 的「B4 不依賴 B3」與「B3／B4 可獨立 revert」失效：TODO §B:49、A1-11:184-187 明定 B4 之 wiring 依賴 B3 Task 3.3 `report.py`；若保留 B4 而 revert B3，wiring 的 AST target 消失，B4 的 gate／可執行路徑不再成立。修法應為在 amendment 明確 supersede §R，寫死「B3 是 B4 wiring gate 的前置，revert 順序為先 B4 後 B3」；若產品真的要求雙向獨立 revert，則把 wiring 移到 B4 之外的 post-B4 gate，而非保留現行落點。

## CODEX-R9-P1-01

**斷言**: Task 2.4 的 AST W1/W4 仍可被條件／死分支中的 `ast.Dict` 常數假性滿足，讓 wiring check rc=0 而實際 `build_validation_section` 回傳缺少 eligibility keys 的報告。

**碼證**: TODO:425-434 宣稱掃 Return 與 function body 的 Constant 鍵且「dead branch 之字面不再造成假綠」，但未定義控制流或可達性分析。實跑等價 probe：`return_sections=['eligibility','min_btl','dsr','pbo','provenance']`、`w4_seen` 含九鍵、`runtime_eligibility={}`；因此上述 snippet 會通過集合子集檢查而 runtime contract 不完整。RECHECK：以同 snippet 加入 `if False` 或未涵蓋的 `if flag`，跑該 probe 或 Task 2.4 scanner，確認 gate 靜態集合仍齊而回傳 dict 缺鍵。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#e6d673841704

[MAJOR] 信心度=High；helper／loop／unpack／setattr 多數是 fail-closed 誤擋，但死／條件分支是可執行假綠。修法：做可達性／資料流封閉分析，或明確禁止 indirect/control-flow assembly 並對這些 mutation 強制 rc=1；加一條實際回傳缺鍵但靜態鍵齊全的 mutation。現有 24 案例可擋被測到的 runtime 缺鍵，但不能替代 wiring gate 的閉包。

## CODEX-R9-P1-02

**斷言**: A1-8 的 reporter 捕獲集合含裸 `ValueError`，因此 `assess_eligibility` 的呼叫方參數錯誤會被誤報為 `reporter_failed`，而非暴露程式 bug。

**碼證**: TODO:235-240 將 `t_years<=0`／`target_sharpe<=0` 定義為參數驗證 `ValueError`；TODO:319-324 又要求捕獲 `ValueError` 並回 `reporter_failed`，只把 TypeError/AttributeError/KeyError 上拋。等價實跑命令輸出 `negative_t_years='reporter_failed'` rc=0，證明此類 bug 可進降級 2xx 路徑。RECHECK：對 `for_study_trial(..., dataset_key='k', t_years=-1.0, target_sharpe=1.0)` 的 `assess_eligibility` 注入負值，觀察 reporter reason。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#44556a29f5c1

[MAJOR] 信心度=High；這會把不合法輸入與可預期資料不可用混同，造成錯誤被吞且 API 狀態不可觀測。修法：移除裸 `ValueError`，或讓參數驗證使用不在 catch tuple 的專用 `InvalidReporterArgument`；只捕獲明確的 ledger／JSON／I/O data failure，保留 `logger.error(..., exc_info=True)`。

## CODEX-R9-P1-03

**斷言**: R2 把 Task 2.4 移到 B4 末並加入 B3 Task 3.3 依賴後，母 SPEC §R 仍宣稱 B3/B4 可獨立 revert，形成未解的拓撲／回退契約矛盾。

**碼證**: TODO:49、51-58 及 A1-11:184-187 明定 B4 依賴 B3 `report.py`；母 SPEC:650-654 仍逐字寫「B4 ... 不依賴 B3」並推出「B3 與 B4 可獨立 revert」。實際保留 B4 而回退 B3 時，wiring 的 AST target 不存在，B4 gate 不能成立。RECHECK：`rg -n 'B4.*不依賴 B3|可獨立 revert|B3 Task 3.3|B4.*B3' docs/GAP1_STRATEGY_OVERFIT_{SPEC,TODO,AMENDMENTS}.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MAJOR] 信心度=High；不是要求改回不可達的 B2 落點。修法：在 A1-11 明確覆寫 §R，紀錄 B4→B3 的依賴與「先 revert B4、再 revert B3」順序；若必須維持雙向獨立回退，將 wiring gate 拆成 B4 之外的 post-B4 commit／phase。

## 被當成事實的未驗證假設（§0）

- fact-verified：TODO template check rc=0；R8 synth 三家 RECONCILE-STAMP 均 APPROVED；本輪 PBO／MinBTL receipts、OOS mutation、rankdata 反例、top-K 等價 probe、AST 等價 probe、ValueError 等價 probe 均有上述實跑命令與輸出。
- fact-verified：R2 TODO／A1 已寫入 J1 三條新 golden、`universe_scope`、`n_rows_rejected`、例外集合、B4→B3 拓撲；母 SPEC §R 仍保留舊拓撲，為文件實況而非推測。
- assumed but not promoted to finding：924 path 高度相關是 band 放寬的解釋，不是本輪以多 seed 估計有效獨立樣本數的正式證明；固定 RNG golden 的可重現性已由 receipt 驗證。
- 未驗證產品實作：本票尚未動工，沒有 `strategy_wiring_check.py`、`report.py` 或 reporter production code；AST／例外 findings 攻擊的是 R2 規格所指定的實作形狀，不宣稱已存在的產品 runtime bug。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、R9 brief、TODO R2、A1-1..A1-15、母 SPEC、R8 synth／CODEX source、review template；R8 三方 stamp APPROVED；上述所有 receipts／probes／template_check 均依命令實跑。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS rc=0；PBO receipt → rc=0；MinBTL receipt → rc=0；OOS-champion mutation → rc=0 且 noise 轉紅；rankdata 原始反例 → rc=1 IndexError（預期）；top-K 等價 probe → set_check=False；AST／ValueError 等價 probes → rc=0；未跑產品 pytest，因本輪禁止改碼且實作尚不存在。
FAILURES_SEEN: 兩次 exploratory shell quoting／Python inline syntax error，均以等價命令修正；rankdata rc=1 是刻意重跑的原始缺陷反例；無未解的驗收失敗。
SCOPE_CHANGES: 只新增 `handoffs/20260817-gap1-todoadv-r9-codex.md`；未改 SPEC、TODO、A1、程式、tests、data_cache、根 HANDOFF.md 或 git history。
NUMERIC_OR_SCHEMA_IMPACT: review-only，未改產品數值、runtime schema 或輸出檔；指出的 P1-01/P1-02/P1-03 是 Frozen 前規格／閘門修補。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-todoadv-r9-codex.md`
TMP_CLEANUP: `/tmp`（symlink 至 `/private/tmp`）無 `workdir` 目標；保留 `/private/tmp/claude-501`，未觸碰其他系統暫存項。
STATUS: DONE
