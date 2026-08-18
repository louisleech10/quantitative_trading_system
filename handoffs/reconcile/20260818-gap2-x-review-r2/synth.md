# Reconcile — 20260818-gap2-x-review-r2

**來源** 20260818-gap2-specadv-r2-codex.md, 20260818-gap2-specadv-r2-composer.md, 20260818-gap2-specadv-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **12 條** findings（codex 6／composer 3／grok 3），下列五個群集**引用全部 12 條，0 掉項**。三家皆判「需修補後派工」；R1 六群集中 K1／K3／K5／K6 三家判閉合，K2／K4 各有實跑反例；三家 O2／O4（σ 修正後）／O5／O7 實跑值皆落帶。

Verdict：需修補後派工——五群集全部**接受並寫回 SPEC**（R2 修訂版）；修訂後派 R3 複核（預期收斂：本輪 findings 皆為可機械核對之條文缺陷，非設計爭議）。

### L1 — §G O1 raw 反向斷言在表定產生器下不成立；O4 噪聲尺度歧義（三家同判 BLOCKING）
**引用**: CODEX-R2-P0-01, COMPOSER-R2-P1-01, GROK-R2-P0-01, GROK-R2-P0-02

**處置＝接受**：
1. **刪除** O1a／O1b 之「raw 空間殘差 Spearman > 0.10」斷言（codex：O1a −0.196／O1b −0.00008；grok：−0.223／0.031；皆非正向）。「防退回 raw 空間」改由 **O1a 本身**擔任：raw 空間下 `x³` 對 `s1` 之殘差**非退化**（var≫1e-10）⇒ status 為 `ok` 而非 `residual_degenerate` ⇒ O1a 紅；V-2 文案改為對映 O1a。O1b 只保留「`residual_degenerate` 或 `|marginal_ic|≤0.02`」（codex 實跑 0.0056）。
2. O4：噪聲一律以**標準差 σ** 表述——`ε~N(0, σ=0.8)`（Var=0.64 ⇒ Var(y)=1）；規格表所有噪聲欄改為 σ（O1／O2／O7 之 0.75／0.66 皆為 σ 值重新核算：O1／O7 `σ_ε=√0.75=0.866`、O2 `σ_ε=√0.66=0.812`；表內直接寫 σ 數值）。三家實跑（σ 正確時）O4 ratio 0.96／0.99、composite 0.574／0.595、margs 0.27–0.29 皆落帶。

### L2 — `reasons_ref` 之 B1／B3→B4 forward dependency 與 Task 1.2 過期指向（三家）
**引用**: CODEX-R2-P1-02, COMPOSER-R2-P2-01, GROK-R2-P1-01

**處置＝接受（採 codex 選項一＋grok live-resolve）**：reason 字面集合（節級 `marginal_ic`／feature 級 `marginal_ic_feature`）**改住 `ic_survivor_contract.json#reasons`（Task 1.0）**，刪除 `reasons_ref`；`ic_report_contract.json` 於 B4 **只**加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`（不加 reasons，避免兩處列舉）；Task 4.1 加驗證：orchestrator 寫入之 marginal reason 字面 ⊆ survivor 契約 `reasons`（AST／字串掃描）；Task 1.2 文字改指 Task 1.0 契約。B3 round-trip 因此可在乾淨 B3 tree 成立。

### L3 — 身分欄對照來源：report metadata 不保證 `symbol`／`timeframe`／`case_id`（codex／composer）
**引用**: CODEX-R2-P1-04, COMPOSER-R2-P1-02

**處置＝接受**：`case_id` 對照改為 `report_ref` 檔名段（`ic_report_{case_id}.json`；與 `_resolve_case_id` 一致），**不**動 report metadata；`symbol`／`timeframe` 由 orchestrator 從輸入 `metadata` 取，缺任一 ⇒ 倖存者檔 `status=computation_failed`、`reason=identity_missing`（不寫身分不明之檔）；validator：payload 身分三欄必填，且 `symbol`／`timeframe` 與 `report_ref` 報告 metadata **exact 相等**，metadata 缺欄 ⇒ raise（禁 `None==None` 過關）；測試三組：正常／缺欄／篡改。

### L4 — 事件 identity 於 cache 無 owner ⇒ refilter 無法重建 `timestamps_hash`（codex）
**引用**: CODEX-R2-P1-03

**處置＝接受**：Task 4.1 於 stage3 pop timestamps **之前**計算 `event_identity={mode, definition_hash, timestamps_hash, n_requested}` 並存 `_ic_cache["event_identity"]`（不可變）；`refilter` 只讀該 identity；canonical 序列化寫進契約 `_doc`（timestamps → int64 epoch ms UTC → sorted unique → JSON 陣列無空白 → sha256；query 模式 `definition_hash=sha256(query.strip().encode())`、`timestamps_hash=null`；無事件 ⇒ 兩者 null）；測試：同 request analyze→refilter 兩次 payload event hash 相等；換 request 不沿用舊 cache（cache key 含 identity hash）。

### L5 — 計算量無上界；identity mutation 未逐欄（codex）
**引用**: CODEX-R2-P1-05, CODEX-R2-P2-06

**處置＝接受**：`MarginalICConfig` 加 `max_survivors_for_loo: int = 200`、`max_removed_candidates: int = 200`；超限 ⇒ 該視角整體 `not_computed:candidate_budget_exceeded`（禁部分靜默輸出），結果帶 `n_regressions`／`budget` 欄；效能以計數 gate 而非時間斷言（決定性）。V-19 參數化為 `symbol`／`timeframe`／`case_id` 三欄各自 tamper；validator 加 OOS 四欄互斥組合（`ok_oos`＋`oos_guarantees=False`、`pass_class` 與 root 不一致 ⇒ raise），V-13 加反向案例。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R2-P1-01

**斷言**: §G L87 要求 O1a／O1b「raw 空間殘差 Spearman `> 0.10`」與同節產生器規格表（O1a `f=s1³`、O1b `f=tanh(2·s1)+0.05·η`、`y=0.5·s1+ε`、seed／n 寫死）矛盾——依釘死參數實跑無法同時滿足，B1 §G O1 測試必假紅或迫使放寬反向斷言（削弱 V-2／V-21）。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:81-87`；VERIFY `python /tmp/composer-gap2-specadv-r2/oracle_probe.py`（receipt `/tmp/composer-gap2-specadv-r2/oracle_probe.txt`）→ O1a `residual_degenerate`（秩 gate 正確）但 raw OLS 殘差 Spearman **−0.196**（不滿足 `>0.10`）；O1b `|marginal_ic|=0.00018≤0.02` 但 raw **0.022**（&lt;0.10）。RECHECK: 重跑上述腳本；對照 D1 L44「tanh raw≈0.14」係不同 label／無 `y=0.5·s1+ε` 之前提。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High。實作者按 SPEC 寫 §G O1 斷言會永久紅；常見繞路＝改 `>0.10` 為 `|·|>0.10` 或換 label／去噪聲，皆未寫入規格表。修法：① 將 raw 反向斷言改為 `|raw_residual_spearman|>0.10` **且** 重跑 O1a 確認；② 或把 O1b 改回 grok R1 探針條件（`f=tanh(2s)` 無噪聲、或 label 與 f 同型）並把實測值寫回規格表；③ V-2 文案與 O1a／O1b 對齊。

---

## COMPOSER-R2-P1-02

**斷言**: §G-4 契約 oracle（L96）要求倖存者 `case_id` 與**報告 metadata** exact 相等，但現行 `_build_report_metadata`（`:3690-3747`）不寫入 `case_id`，真實路徑 `run_analyze()` 報告 `metadata.case_id=None`（檔名則經 `_resolve_case_id`→`ic_gatekeeper`）——validator／§G-4 無穩定對照來源，Task 3.1 驗證⑮亦未覆蓋 `case_id`。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:96,178`；`momentum/Analysis/ic_filter_orchestrator.py:3690-3747,3856-3860`；VERIFY `run_analyze()` → `metadata.case_id=None`、`symbol/timeframe` 存在。RECHECK: 同上；`rg case_id docs/GAP2_MARGINAL_IC_SPEC.md` 對照 Task 4.1／4.2 是否要求鏡像進 `report_meta`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High。`build_survivor_output(..., case_id=...)` 可從 orchestrator 傳入，但 §G-4「對報告 metadata」語意無法實作；實作者可能 skip `case_id` 相等、或硬編預設字串假綠。修法：Task 4.1／4.2 明定 `report_meta["case_id"]=self._resolve_case_id(metadata)`（與 persist 檔名一致）＋Task 3.1 驗證⑮ 擴至 `case_id`；或改 §G-4 為「與 `report_ref` 路徑內 `case_id` 段／檔名一致」並刪 metadata 字面。

---

## COMPOSER-R2-P2-01

**斷言**: K1 已把 `ic_report_contract.json#reasons.marginal_ic*` 移至 B4 Task 4.1，但 B1 Task 1.2 L129 仍規定 `compute_marginal_ic` 之 reason 字面集合＝該 report 契約鍵——B1 單獨落地時 report 契約尚無這些 reason，與「B1 可獨立綠」及 Task 1.0「report 契約本 Task 不動」衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:105-106,129`；`rg marginal_ic momentum/Analysis/contracts/ic_report_contract.json` → 0（2026-08-18 repo）。RECHECK: 對照 K1 synth `c0786915b314` 處置 2 與 Task 1.2 驗證⑩–⑪。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-review-r1/synth.md#c0786915b314

[MINOR] 信心度=Medium。實作可暫從 `ic_survivor_contract.json` 內嵌枚舉或測試 fixture 讀 reason，但 SPEC 文字指向錯誤 SoT。修法：Task 1.2 改指 Task 1.0 契約之 reason 枚舉（或 `survivor_contract` resolver 於 B4 前允許 stub），B4 再與 report 契約 sync。

---

## GROK-R2-P0-01

**斷言**: §G O4 產生器寫 `ε~N(0,0.64)` 並同時要求 `Var(y)=1` 與 `composite_ic∈[0.55,0.61]`／各 `marginal_ic∈[0.26,0.31]`；若實作者按 numpy／多數程式慣例取 `scale=0.64`（σ=0.64），正確實作會被 O4 容差帶假紅。

**碼證**: SPEC L84／L90。VERIFY：`seed=20260818,n=20000,y=0.3·Σf_i+ε`。literal `normal(0,0.64)` ⇒ `Var(y)≈0.779`，`composite_ic≈0.6766`，seq margs≈`0.348/0.320/0.337/0.337`（三帶僅 ratio 過）。改 `normal(0,√0.64)` ⇒ `Var(y)≈1.012`，`composite_ic≈0.5947`，margs∈帶，ratio≈0.991。母體：`Var(0.3·Σf)=0.36` ⇒ 要 `Var(y)=1` 須 `Var(ε)=0.64` 即 **σ=0.8**。RECHECK: 重跑上文兩組產生器。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[BLOCKING] 信心度=High。會怎麼失敗：B1 oracle 測試依表實作 → O4 紅；或實作者為過測自行改 σ／放寬帶＝驗收漂移。  
修法：表內改寫為 `ε~N(0, σ=√0.64)` 或 `ε~N(0, σ²=0.64)`（二選一釘死），並保留 `Var(y)=1` 母體檢查斷言；或把容差帶改為與 σ=0.64 一致（不建議，因會偏離 ρ=0.3／Spearman 0.582 推導）。

---

## GROK-R2-P0-02

**斷言**: §G O1 要求 O1a 與 O1b「同時」滿足 raw 空間殘差 Spearman `> 0.10`，但依合成產生器規格表實跑：O1b raw≈0.031（不達標）；O1a raw≈−0.223（有號 `>0.10` 亦不達標）。正確 vdW 實作會因反向斷言假紅。

**碼證**: SPEC L81–L82／L87（「兩案例同時斷言…`> 0.10`」；D1 L44 之 0.14 敘事來自不同 label 強度）。VERIFY O1b seed=20260802：`f=tanh(2s)+0.05η`，`y=0.5s+ε(σ=0.75)` → raw_sp≈0.0306；純 `tanh(2s)` 同 label → raw≈0.036。對照 `y=s+N(0,1)` 才出現 raw≈0.10–0.12（非表定 label）。O1a：raw_sp≈−0.223。RECHECK: 重跑 O1a／O1b 表定參數。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[BLOCKING] 信心度=High。會怎麼失敗：Task 1.2 O1 測試依字面加 raw>0.10 → 綠燈不可能；或刪反向斷言／改 label 未寫進規格表＝R1「參數寫死」回潮。  
修法（擇一寫死）：(a) 反向斷言改 `|raw_spearman| > 0.10` 且 **只綁 O1a**（O1b 改較低門檻或改 label 使 raw 過門）；(b) O1b label 改為能重現 D1≈0.14 之規格（須重跑釘帶）；(c) O1b 取消 raw 反向、改由 V-2（`normal_scores→恆等`）承擔防 raw 退回。V-2 對 O1b 主斷言（`|marg|≤0.02`）在 raw 空間會紅，可作替代防護。

---

## GROK-R2-P1-01

**斷言**: Task 1.0 允許 `reasons_ref` 指向尚未存在的 `ic_report_contract.json#reasons.marginal_ic*` 直至 B4，但 Task 4.1 驗證未要求 B4 後對 **live** survivor 契約做 `resolve_ref(reasons_ref)` 成功；同時 Task 1.2 仍寫 reason「Task 3.1 新增」與「Task 3.1 契約檔」——與 K1（reasons 在 4.1、鍵表在 1.0）矛盾，構成 fail-open 窗與實作誤導。

**碼證**: SPEC L105（允許 B4 前缺席）；L129「（Task 3.1 新增，本處不複列）」；L127「Task 3.1 契約檔 `marginal_ic_section_keys`」（實際 Task 1.0）；L178 ⑧只以 **tmp** fixture 驗缺席 raise；L199–L202 Task 4.1 寫入 reasons 與 `test_r6` 消費點，**無** survivor `reasons_ref` live resolve。RECHECK: `grep -n 'Task 3.1 新增\|reasons_ref\|resolve_ref' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High。會怎麼失敗：(1) 實作者於 B3 按 L129 把 reasons 寫進 `ic_report_contract` → 提前觸發 `test_r6` 節鍵／或與 K1 衝突；(2) B4 後 ref 路徑打錯／鍵名漂移無人擋。  
修法：L129／L127 改指向 Task 4.1／Task 1.0；Task 4.1 驗證加「`resolve_ref(load_survivor_contract()['reasons_ref'])` 成功且 ⊇ 本 commit 寫入之 reason 字面」；或採 brief 替代——reason 字面住 survivor 契約，`ic_report_contract` 以 ref 反指（消除懸空窗）。

---


## 戳記

（待三家 append RECONCILE-STAMP）
