# IC Phase 1 1-contract TODO — 雙家族 adversarial Reconcile（Claude 綜合）

> CODEX(GPT-5.5) / CURSOR(Composer 2.5) 各獨立審 TODO。兩家 Verdict 皆「需修補後派工」。
> 一致結論：TODO 方向對、覆蓋齊（[C-1..C-12]+R1-R9 無掉項），但**冷啟動執行細節有假綠/改壞舊路徑的洞**。

## 雙家收斂 BLOCKING（必修，最高優先）

| # | 收斂 finding | Claude 自驗 | 修法 |
|---|---|---|---|
| T1 | **G1 baseline 排到 B5(改碼後才凍結)→「改後 vs 改後」假綠** | ✅ 真(§B B5 依賴 B1-4) | 新增 **B0 baseline freeze**,任何改碼前凍結 baseline；B1-4 gate 引用 B0；config_hash 派工前由我寫死 |
| T2 | **`eval_status` 會被 `_to_json_compatible` 的 `asdict()` 洩進 v1 JSON**;B1「純 dataclass」與 flag-off 矛盾 | ✅ 真(`ic_analysis_service.py:1098 asdict`) | 把「加欄+v1序列化排除+真實 get_result regression」同批;允許改 `_to_json_compatible`;驗收測真實 v1 payload 不含新鍵 |
| T3 | **API negotiation 只改 service 簽名,route 無 Query→v2 不可達** | ✅ 真(`ic_analysis.py:62 get_result(task_id:str)` 無 Query) | Task 3.2 修改檔加 `api/routes/ic_analysis.py::get_result` 加 `schema_version: Optional[int]=Query(None)`;加 route-level TestClient 測試 |
| T4 | **CPCV effective embargo「最近邊界距離」定義不可執行/誤判** | ✅ 真(CPCV 用 `embargo_pct` 非 SplitPlan.embargo,且 purge≠embargo) | 寫死演算法:用原 requested config 重算每 test range expected excluded `[start-purge_gap, end+purge_gap+requested_embargo_len)`,assert returned train set 完全一致;分別檢查 pre-purge 與 post embargo |
| T5 | **tier/RSS/page_size 空殼(門檻未寫死);tracemalloc 量不到 pyarrow native RSS** | ✅ 真(SPEC §V「待量測」) | 改可證偽**相對**門檻(不靠硬數字):filter read peak RSS < tier RAM×25% 且**不隨總 feature 數成長**(O(page) 非 O(total));量測用 `psutil.rss` 非 tracemalloc;page_size cap 按 tier 寫死 |
| T6 | **既有子端點(decay/quantile/correlation/grouped/export)回歸缺**;只測 /result | ✅ 真(各 route 取 get_result 子鍵) | 加 route regression matrix:flag off 全 caller golden;flag on 無參仍 v1;flag on ?v=2 僅 /result 回 v2 |
| T7 | **ICArtifactSchema.horizon 與 ICResult(無 horizon)無映射** | ✅ 真 | 寫死 `build_ic_artifact_rows(results, default_horizon, scope_id)`;Phase 1 單 horizon 寫死來源,multi-horizon §N 登記 |

## 單家獨有 BLOCKING/重要

- **[CODEX 獨有 BLOCKING] validate_split_integrity 多 symbol 通過條件太弱**:sorted/grouped ≠ per-symbol split;按(symbol,time)排好但整 frame 丟 CPCV 仍可能通過 → 假綠。✅ 真。**修**:SplitPlan 強制 `symbol is not None` 且 `unique(symbols[row_index])=={plan.symbol}`;多 symbol 必拆 child plans;G3 加「sorted 但未 per-symbol」反例必 raise。
- **[CODEX 獨有 MINOR(但實) ] §0 Logging 規則自打臉**:寫 `from api.core.logging` 會誘導 momentum→api(違反 Rule 1)。✅ 真。**修** §0:momentum 層用 `momentum.core.logging`,contracts.py 優先不 log。
- **[CURSOR 獨有 MAJOR] WF `_generate_rolling_splits` 回區間 tuple 非 `(train_idx,test_idx)`**;與 CPCV `np.array_equal` 對照會錯。✅ 真。**修** Task 1.4:區間→`np.arange(s,e)` 展開偽碼;WF/CPCV 測試分開斷言(`test_adapter_wraps_wf` 獨立)。
- **[CURSOR 獨有 MAJOR] gap 偵測算法模糊**。**修** Task 1.3:`gap if max(diff(ts)) > pd.Timedelta(expected_freq)*(1+atol)` 可複製偽碼;§0 加「已知技術債:purge_semantic rows,1a 改 timedelta,Phase 1 靠 1.3+expected_freq 擋 rows-purge gap 洩漏」。
- **[CURSOR MINOR] [C-11] 無獨立檢查**。**修** Task 4.1 加 `grep -r "from api.models" momentum/core`==0 雙向。

## 分歧
- 無實質分歧;兩家方向一致,差異僅在各自抓到對方漏的點(WF 形狀=cursor;多 symbol 弱條件+logging=codex)→ 互補,全收。

## 我要做的事（修 TODO）
1. config_hash:派工前我去 feature library 撈最新 BTC/1h hash 寫死(或撈不到→標 BLOCKED 不交實作者選)。
2. 重排批次:**B0 baseline freeze → B1..B5**;修 T1-T7 + 4 單家項。
3. 修完重跑機檢 → gate → 派實作(Codex 實作 + Composer code review)。
