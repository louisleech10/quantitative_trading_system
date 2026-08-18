# GAP-2a／2b SPEC adversarial 審查 R2（CODEX）

## Verdict

需修補後派工；目前不可進 TODO。BLOCKING：CODEX-R2-P0-01。其餘為 MAJOR：CODEX-R2-P1-02～05；MINOR：CODEX-R2-P2-06。

## CODEX-R2-P0-01

**斷言**: §G O1a／O1b 的 raw-space residual Spearman `> 0.10` oracle 在 SPEC 固定產生器下不成立，正確的秩空間實作會被 O1 測試打紅。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:81-87,245-247`；`VERIFY: venv/bin/python -c '<按表格 seed/n、前60% train/後40% test、OLS raw residual、Spearman>'` → O1a `raw_residual_spearman=-0.196263826`，O1b `=-0.000083541`。同一探針之秩空間結果：O1a `var=4.73791958e-32`（gate 應為 `residual_degenerate`），O1b `var=0.135631261`、`marginal=0.005631237`（≤0.02）。將噪聲 0.75 解作標準差仍得 O1a `-0.196263826`、O1b `-0.000083541`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[BLOCKING] 信心度=High；O1a／O1b 都不是 raw residual 的正向 `>0.10` 案例，故 §G 的 baseline 本身不綠，V-2／V-21 也不能在綠色基線上驗證。保守修法是刪除或改寫這個 raw-space 斷言，或另行固定一個已實跑且確實滿足該條件的產生器；不得只把 threshold 放寬或把 signed comparison 偷換成未驗證的條件。RECHECK：重跑上述探針並逐項比較 O1a/O1b 的 raw residual 與 rank-normal residual。

## CODEX-R2-P1-02

**斷言**: R1 將 `reasons_ref` 留在 B1 的 SoT、卻把其目標鍵移到 B4，與 B3「獨立綠」及 round-trip validator 要求互斥，形成明確的 forward dependency。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:105-109` 明寫 `reasons_ref` 指向 B4 才新增的 `ic_report_contract.json#reasons.marginal_ic*` 且目標缺席；`:173-182` 又要求 B3 round-trip 先過 validator、resolver 對缺失目標 fail-closed，並宣稱 B3 不改 `ic_report_contract.json`。`VERIFY: jq -r '.reasons|keys[]' momentum/Analysis/contracts/ic_report_contract.json` → 僅 `net_ic_unavailable`、`event_fallback`、`xsec_not_applicable`，沒有 `marginal_ic`／`marginal_ic_feature`；baseline `venv/bin/pytest tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q --tb=short` → `46 passed`（既有樹綠，不代表 GAP-2 B1–B4 已可獨立綠）。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713; momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MAJOR] 信心度=High；若 B3 validator 真正解析 `reasons_ref`，實際 B3 工作樹會因缺鍵 fail-closed；若為了 round-trip 暫不解析，則 B3 的 fail-closed 要求只在 tmp fixture 成立，產物在 B4 前有未驗證窗。修法三選一且須寫死批次邊界：把 B1/B2 所需 reason 字面及其鍵集放入 survivor SoT；或將 B3+B4 的 resolver、validator、report contract 視為同一 atomic gate；或明確把 B3 round-trip 改成帶 B4 contract fixture 的非獨立測試並取消「B3 單獨綠」宣稱。RECHECK：在不改既有 contract 的乾淨 B3 tree 執行 `validate_survivor_output(build_survivor_output(...))`，並另以缺 ref fixture 驗證 resolver 的 raise；兩者不能靠同一實際檔案同時滿足。

## CODEX-R2-P1-03

**斷言**: event 模式的 `timestamps_hash` 在 `refilter()` 路徑無法由現有 cache 重建，故 K4 的 exact event provenance 與 K6 的 cache-hit refilter 互相未閉合。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2733-2776`：stage3 正規化 timestamps 後，`:2773-2776` `pop("timestamps")` 只留計數；`:3449-3464` 的 `_ic_cache` 只保存 `event_info`，沒有原始 timestamps／canonical hash；`:1732-1765` 的 `refilter()` 直接從該 cache 重建 stage7。`momentum/Analysis/event_filter.py:66-70` 顯示原始 timestamps 只在 filter_info 暫存。SPEC `docs/GAP2_MARGINAL_IC_SPEC.md:177-179,202-203` 同時要求 pop 前計算 hash、且 cache-hit refilter 刷新結果。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c; momentum/Analysis/event_filter.py#e2c89cb3ad7c; docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High；第一次 analyze 可在 pop 前計算 hash，但 refilter 沒有原始 request（尤其 requested timestamps 含未命中列時，從 filtered index 反推會改變語意），只能漏填、重算成不同 hash，或誤把 stale provenance 當新結果。修法：在 cache owner 內持久保存已正規化且 canonicalized 的 event identity/hash，refilter 只讀該不可變 identity；同時把 timestamp serialization（timezone/epoch/排序/JSON bytes）寫成契約規格。RECHECK：以同一分析器先用 timestamp request 跑 analyze，再改 threshold 跑 refilter，斷言兩次 survivor payload 的 event hash 相等且改 request 後不會沿用舊 cache。

## CODEX-R2-P1-04

**斷言**: Task 3.1 的 `symbol`／`timeframe` 對照沒有可依賴的 report-metadata 必填來源，缺欄時 validator 的 identity check 不具 fail-closed 保證。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:3690-3748` 的 `_build_report_metadata()` 只 `meta = dict(metadata)`，再加入計數、event、warnings、split 等欄位，沒有建立或要求 `symbol`／`timeframe`。`VERIFY: venv/bin/python -c '..._build_report_metadata(..., metadata={}, ...)'` → keys 為 `event_filter,n_samples,split_method,total_features_input,total_features_output,warnings`，`symbol None timeframe None case_id None`。SPEC `docs/GAP2_MARGINAL_IC_SPEC.md:96,177-178` 卻要求 payload 的身份欄與 `report_ref` 報告 metadata exact 相等。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c; docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High；正常 holdout fixture 的輸入 metadata 可能恰好有身份欄，但 builder/validator 契約沒有保證這件事；在缺欄、fallback 或舊報告下，checker 沒有可比值，可能接受 caller 傳入的任意 `symbol`／`timeframe`。修法：在 report metadata 產生點把 `symbol`、`timeframe`、`case_id` 設為真實來源的 required identity；`report_ref` 解析失敗或任一欄缺失時 validator 必須 raise，並以缺欄、篡改、正常三組測試固定 exact compare。RECHECK：用 `metadata={}` 與只含 symbol 的 payload 驗證都必須 fail-closed，不得把 `None` 當相等值。

## CODEX-R2-P1-05

**斷言**: `include_removed_candidates=True` 加上每候選重做完整 residual projection，使計算量沒有可驗證上界；§V 以「k≤數十」推定 `O(k²n)` 可忽略，與現有輸入面不符。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2799-2813` 對超過 5000 features 只 warning、沒有 implicit truncation；`:2856-2857` 只有使用者明確設 `feature_filter.max_features` 才裁切。SPEC `docs/GAP2_MARGINAL_IC_SPEC.md:129,199-203,269` 預設 `include_removed_candidates=True`，並把 OOM 降載列為不測且以 `k≤數十` 作假設。`VERIFY: rg -n 'include_removed_candidates|max_features|5000|O\(k' docs/GAP2_MARGINAL_IC_SPEC.md momentum/Analysis/ic_filter_orchestrator.py` → 預設開啟、無 marginal stage budget，且 >5000 僅 warning。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c; docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High；若 p=5000、s=2500、n=20000，loo 與 removed-candidate 路徑需重複數千次 rank／OLS，`O(k²n)` 遠非「可忽略」，會破壞跨 tier repeatability、延遲與 OOM safety；更不能靠靜默丟候選來過 gate。修法：先以真實 feature-count/tier benchmark 釘出可證偽的計算／記憶上限，超限時 fail-closed 為 `not_computed` 並記 reason，或採有 provenance 的分批／共享分解方案；不得以未驗證的「數十」假設取代 guard。RECHECK：用實際允許的最大 feature count、survivor count、n 跑 peak-RAM/time benchmark，並驗證超限結果不是部分靜默輸出。

## CODEX-R2-P2-06

**斷言**: §V 的 mutation coverage 沒有獨立打壞 `timeframe` 或 `case_id` identity，雖然 Task 3.1 ⑮ 把 timeframe、且 contract 又要求 case_id。

**碼證**: SPEC `docs/GAP2_MARGINAL_IC_SPEC.md:105,177-178` 要求頂層 `symbol/timeframe/case_id`；`:262-266` 的 V-19 只寫「symbol 寫死或漏帶」並映射驗證⑮，沒有 timeframe/case_id tamper case；`:96` 的 §G-4 也只把 symbol 篡改列為明示 mutation。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MINOR] 信心度=High；即使 symbol mutation 變紅，實作仍可能只比較 symbol、漏驗 timeframe/case_id，而 21 條探針全綠。修法：將 V-19 參數化為 symbol、timeframe、case_id 各自 tamper，或加入三欄 identity mutation，且每一欄都以缺失／不符 metadata 的 raise 斷言收斂。RECHECK：逐欄改值後各跑 validator；三次均須 rc=1，還原後 rc=0。

### 必答 1：K1–K6

- K1：未閉合。SoT 先行與 B4 report section 同 commit 已寫回，但 `reasons_ref` 的 B1/B3→B4 缺席窗仍存在（CODEX-R2-P1-02）。
- K2：未閉合。O8、O4、O5、O7 的 R1 修訂方向與本輪實跑數值相容；O1 raw-space oracle 硬紅（CODEX-R2-P0-01）。
- K3：閉合（就 SPEC 所寫介面）。`fit_scope` 已為必填 Literal，train 全 True raise、full-sample fallback 與 no-holdout 分支均有明列；本輪沒有新增反例重開已裁定方向。
- K4：未完全閉合。欄位已補，但 report metadata 身份來源與 fail-closed exact compare 不足（CODEX-R2-P1-04）；event hash cache 亦未閉合（CODEX-R2-P1-03）。
- K5：部分閉合。V-1～V-21 均有形式上的測試映射，但 identity mutation 缺 timeframe/case_id（CODEX-R2-P2-06），且 O1 基線先紅。
- K6：部分閉合。cache-hit `refilter` 的 refresh 斷言已列，但 event provenance 在 cache 中沒有 owner（CODEX-R2-P1-03）。

### 必答 2：新引入風險

新洞為：B3 round-trip 與 B4-only reason ref 的批次矛盾；event timestamp 在一次 analyze 後不可供 refilter 重建；`_build_report_metadata` 不保證身份欄；OOS 四欄雖列入契約，但驗證清單未覆蓋所有互斥組合；預設 removed candidates 令計算量無界。R1 已裁定的拆分、橋 blocked、取捨交委員會、GAP-3 均未重議。

### 必答 3：§G 產生器實跑值

以下使用 `rng=np.random.default_rng(seed)`、表格列出順序生成因子後生成 label noise、前 60% train／後 40% test、rankdata average/(n+1) + OLS(intercept) 的獨立探針；O5 使用 O2 data seed=20260803、test permutation seed=20260805。

`VERIFY: venv/bin/python -c '<O1a/O1b/O2/O4/O5/O7 generator probe>'`：

- O1a：`residual_var=4.73791958e-32`，gate 前診斷 `marginal=-0.472170212`，raw residual `=-0.196263826`；應走 `residual_degenerate`。
- O1b：`residual_var=0.135631261`，`marginal=0.005631237`，raw residual `=-0.000083541`；≤0.02，但 raw `>0.10` 不成立。
- O2：`gross=0.390939953`，`marginal=0.385116771`，`delta=-0.005823181`，`|delta|≤0.02`。
- O4：sequential marginal `[0.282388077, 0.274101684, 0.284192006, 0.284336889]`；`composite=0.574309023`，`ic_weighted=0.574396468`，ratio `0.959544318`；均在 SPEC 區間。
- O5：marginals `[0.023406724,-0.003452390,0.017309842]`，Bonferroni threshold `0.053531016`；composite `0.015974455`，single threshold `0.043826127`；本解讀下三因子皆過。
- O7：`gross=-0.477896832`，`marginal=-0.491498489`，`train_insample=-0.008614357`，test-fit `=-0.019586111`，兩段差 `0.482884132`；通過差異 oracle。

O1 的 raw 反向斷言是本輪唯一已實跑的 oracle 紅；O5 的「mutation 去 gate 必紅」及 21 條 mutation 的實際 red/restore 尚未驗證，因 `scripts/gap2_mutation_probe.sh` 與 GAP-2 新測試檔目前不存在。

### 必答 4：§V 21 條 mutation

映射完整性：V-1～V-9 對應 B1/B2 projection、rank、排序、seed、權重與 block length；V-10～V-12 對應 B3 envelope/validator；V-13～V-16 對應 fallback、disabled、persist 與 golden；V-17～V-18 對應 OOS/train-insample 與名稱排序；V-19～V-20 對應 symbol/hash；V-21 對應 O1 gate 順序。這是 SPEC 的靜態映射，不是已實跑證明。

仍缺具體可證偽覆蓋：① V-19 沒有 timeframe/case_id mutation（CODEX-R2-P2-06）；② V-13 只打 `oos_guarantees=True` 的 fallback 方向，沒有反向 `analysis_status=ok_oos`／`oos_guarantees=False` 或 `pass_class` 矛盾組合；③ O1a baseline 先因 raw oracle 紅，故 V-2/V-21 暫不能宣稱「改壞才紅」而非「基線本來就紅」。

### 必答 5：可進 TODO？BLOCKING 清單

不可進 TODO／不可派工。先閉合：

1. `CODEX-R2-P0-01`：修正 O1 raw oracle 並重跑 O1a/O1b。
2. `CODEX-R2-P1-02`：消除 B1/B3 對 B4 reasons 的 forward dependency，或把批次 gate 改為 atomic。
3. `CODEX-R2-P1-03`：保存 event canonical identity/hash 並使 refilter 可驗。
4. `CODEX-R2-P1-04`：報告 metadata identity required + 缺欄 fail-closed。
5. `CODEX-R2-P1-05`：補 tier/feature-count budget 與超限 fail-closed gate。

## §1 必查 11 類

1 矛盾：見 P0/P1-02；2 端到端：見 P1-03/P1-04；3 可測驗收：O1 與 mutation reverse gap；4 quant 假設：O1、O4 的 k≤數十假設；5 過度工程：無新增 finding；6 OOM/並行：P1-05；7 cache：P1-03；8 API/型別：K3 closed，K4 identity partial；9 測試品質：P0/P2；10 Agent 可執行性：P1-02/P1-05；11 必要性/短命工：各 Task 的「存活至」未見新覆蓋刪除矛盾，但 B1/B3 reason 依賴仍須先修。

## 被當成事實的未驗證假設（§0）

- `k≤數十`、`O(k²n) 可忽略`：未由現有 feature filter 上限保證；已列 CODEX-R2-P1-05。
- O1 raw residual `>0.10`：被寫成 oracle 事實但實跑反例，已列 CODEX-R2-P0-01。
- 五批各自獨立綠：GAP-2 新測試／probe 檔尚未存在；本輪只驗既有 baseline 46 passed，不宣稱未來批次已綠。
- `_build_report_metadata` 一定含 symbol/timeframe：空 metadata 實跑不含，已列 CODEX-R2-P1-04。

ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → TEMPLATE PASS；`bash scripts/ic_wiring_check.sh` → rc=0；既有同步／wiring／persist baseline → `46 passed`；O1a/O1b/O2/O4/O5/O7 獨立數值 probe 已實跑；`shasum -a 256` 已取得本檔引用來源 digest；指定 completeness check → rc=0。
TESTS_RUN: `venv/bin/pytest tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q --tb=short` → `46 passed in 2.70s`; `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS; `bash scripts/ic_wiring_check.sh` → rc=0; `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r2-codex.md --family codex` → `COMPLETENESS PASS(single)`, `EXIT_CODE=0`。
FAILURES_SEEN: 初次數值探針的內部 basis 索引寫法錯誤；修正探針後重跑並取得上述值。SPEC review 本身未修改任何測試斷言。
SCOPE_CHANGES: 只新增本 review 與 task-id 交接檔；未改程式、測試、SPEC、TODO、data_cache 或根 HANDOFF；未修改 git history。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值、schema、輸出大小；僅指出 SPEC oracle／provenance／效能 gate 缺口。
OUTPUT: `handoffs/20260818-gap2-specadv-r2-codex.md`；task handoff=`handoffs/20260818-20260818-GAP2-X-REVIEW-R2.md`。
STATUS: DONE
