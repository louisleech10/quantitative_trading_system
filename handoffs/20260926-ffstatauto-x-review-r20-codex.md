## CODEX-R20-P3-00

**斷言**: 本輪逐項核對後無 finding。r19 的四項 findings 均已在 v39 以可逐字核對的契約、映射或 TODO 同步條款閉合；v39 diff 未再產生可重現的 P0–P2 契約缺陷。

**碼證**: `git diff --stat bfb5ad83 fa3d1b85 -- docs/FFSTAT_SPEC.md` 僅為 `docs/FFSTAT_SPEC.md` 的 5 insertions/1 deletion。`nl -ba docs/FFSTAT_SPEC.md` 核對 :56 的完整遞移 `period_keys`、custom `outputs` 與 concat 前欄集合驗證，:118 的 CDL raw/frequency/Consensus 映射，及 :152 的 manifest test/gate/receipt/touches 清單。於隔離 `/tmp/ffstat-r20-work` 以真實 `BTCUSDT/12h` 1,696 根 HDF5 執行 probe，rc=0：microstructure 25/25、entropy 21/21、tail_risk 26/26、volatility 27/27、volume 8/8、pattern 68/68 的 output/metadata 集合均無缺漏；pattern sparse Consensus 操作序列亦輸出 `output_finite=true`。`rg` 未找到既有 `CustomIndicatorDef(...)`／API model construction，現行設定 `custom_indicators: []`。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#676e3fa04e17; handoffs/reconcile/20260926-ffstatauto-x-review-r19/synth.md#a0af3f31eef2; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0; momentum/FeatureEngineering/atomic/custom_indicators.py#c8d69c237696; momentum/FeatureEngineering/atomic/pattern_indicators.py#312a98ad227f; momentum/FeatureEngineering/atomic/microstructure_indicators.py#e497947a3f2; scripts/governance_verdicts.json#877d4072399e

必答成對核對：

**(1a) r19 findings 是否閉合**：`CODEX-R19-P1-01` 已閉合；v39 §C 明定 `CustomIndicatorDef.outputs` 必填，並在 `compute_all` concat 前驗回傳欄集合與宣告集合相等。`CODEX-R19-P1-02` 已閉合；v39 §C 明定完整遞移 `period_keys`、上游 K 遞推、上游已解析參數與取不到即 fail-closed。`CODEX-R19-P1-03` 已閉合；v39 §P 明列兩支測試、gate_cmd、coverage successor、NaN inventory、column-set delta、approval、blocked receipt 與 touches 的同步清單。`CODEX-R19-P2-04` 已閉合；Task 2.4 明定 CDL raw、frequency、Consensus 三類映射與輸出收據。

**(1b) 原反例／條文重跑**：逐字核對 `docs/FFSTAT_SPEC.md:56,118,152`；r19 的 custom 無宣告、microstructure VPIN z-score 遞移依賴、manifest 漏列兩支測試、pattern 空 params 無 K 映射，分別都有對應的 v39 強制條款。現行 source 仍是待施工的舊實作，未把舊碼誤報成 v39 已實作；本輪判定的是 SPEC contract closure。

**(2a) v39 新 defects**：未發現可列案的新 P0、P1 或 P2 finding；沒有為湊數新增實質 finding。

**(2b) 可重現反例核對**：真實 HDF5 probe 的 output/metadata 集合差集均為空；`pattern_indicators.py:80-81` 的 Consensus 對一個 raw pattern 欄注入間歇 NaN 後仍得到有限值（`output_finite=true`, `output_value=-1.0`），符合 §C:57 只遮開頭、不改 intermittent NaN 語意。未重現 v39 條款可接受錯誤欄集合、漏 upstream K 或將 sparse Consensus 解讀成另一個 K 的操作序列。

**(3a) 兩項 assumed 是否成立**：①「同引擎衍生輸出之 K＝上游 K 遞推」涵蓋 default L1 derived relationships：成立為 v39 contract 可執行假設。pattern、microstructure 的 derived output 有明確上游公式；entropy/tail-risk 的輸出與 metadata 可一一對位，nested MDD 的自然 rolling NaN 也未造成 metadata/output 缺漏。②「upstream resolved params 可在 engine 內取得且不改值／欄數」：成立為施工可行性假設。microstructure 的 bucket/window 已在 engine config 保存並被 derived loop 使用；Keltner 明確保存 EMA/ATR 同 window，Force Index 保存 EMA period；custom 預設為空且目前沒有 definition consumer。

**(3b) 證據**：`momentum/FeatureEngineering/atomic/microstructure_indicators.py:60-67,283-288`、`volatility_indicators.py:186-201`、`volume_indicators.py:226-236`、`pattern_indicators.py:52-82` 顯示參數與上游運算均在同一 engine 邊界可取得。隔離 probe 實測 1,696 rows 與六類 engine 的 `25/25, 21/21, 26/26, 27/27, 8/8, 68/68` output/metadata counts；沒有執行全 FF，未把此 probe 外推成全設定效能或施工完成證明。

**(4a) brief 列出的三項未檢查是否命中**：① entropy/tail-risk derived outputs 與 metadata upstream params：未命中，實測集合無差集，並以 entropy direct rolling 與 tail-risk output census 核對。②既有 tests/API models 是否建構 `CustomIndicatorDef`：未命中；rg 只找到 model 定義、engine 空列表 smoke test 與 `custom_indicators: []` 設定。③ Consensus 在 upstream sparse/intermittent NaN 時的 max-K 是否不明：未命中；§C:57 已規定只遮第一個有效值以前，且實際 sparse NaN probe 保留後續 skipna 行為。

**(4b) code evidence**：① `entropy_indicators.py:88-106,138-184`、`tail_risk_indicators.py:180-194` 與真實 probe；② `feature_config.py:451-457`、`tests/feature_engineering/atomic/test_atomic_differential.py:138-143`、`config/scan_config.yaml:593` 與 rg 結果；③ `docs/FFSTAT_SPEC.md:57`、`pattern_indicators.py:79-82` 與 sparse Consensus probe。這些證據只支持「本輪未命中」，不宣稱 v39 implementation 已完成。

**(5a) 是否可定案 `VERDICT: proceed`**：可以。r19 四項已閉合，v39 diff 之新條款沒有可重現 blocker；本輪沒有 P0/P1。

**(5b) 若不能，blocking IDs**：不適用；`BLOCKED-BY:` 留空。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、本輪 brief、v39 target diff、r19 synth、R1–R7 rulings、template 與 governance category allowlist；已核對 r19 四項 closure、兩項 assumed、三項 not-checked；真實 probe 以 `data_cache/feature_klines/kline_cache.h5` 複本執行，未宣稱 full FF。
TESTS_RUN: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/louis/Desktop/quantitative_trading_system /Users/louis/Desktop/quantitative_trading_system/venv/bin/python inspect_contract.py`（cwd `/tmp/ffstat-r20-work`）→ rc=0；輸出 microstructure 25/25、entropy 21/21、tail_risk 26/26、volatility 27/27、volume 8/8、pattern 68/68，sparse Consensus `output_finite=true`。另以 `git diff --stat bfb5ad83 fa3d1b85 -- docs/FFSTAT_SPEC.md`、`nl -ba`、`rg -n` 完成條文與 consumer 核對；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r20-codex.md --family codex --round-id 834914c8-b3c3-4732-a09f-1b3f4fc6bcb2` → `COMPLETENESS PASS(single)`, rc=0。
FAILURES_SEEN: 暫存 probe 初次插入 sparse 檢查時誤置於 `compare()`，出現 `NameError: raw is not defined`；修正後又因以 `int(Timestamp)` 取 row index 出現 `TypeError`，改用位置索引重跑 rc=0。未改寫成繞過驗證的命令。指定 `/tmp` 清理命令的結果列於 `TMP_CLEANUP`。
SCOPE_CHANGES: none；未修改 source、SPEC、manifest、templates、CLAUDE.md、git history 或 data_cache；只新增本輪指定交件檔與 append-only 狀態交接。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪唯讀審查，未改數值、schema、輸出大小或既有測試斷言；probe 只讀真實 HDF5 複本。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r20-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R20.md
TMP_CLEANUP: `rm -rf -- /tmp/ffstat-r20-work` 被環境安全閘拒絕，未改寫成替代刪除命令；`/tmp/ffstat-r20-work` 仍存在，`/tmp/claude-501` 已確認存在並保留。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R19-P1-01,CODEX-R19-P1-02,CODEX-R19-P1-03,CODEX-R19-P2-04
