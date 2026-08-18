# GAP-1 B4 實作 code review / grok | task-id=20260818-GAP1-B4-REVIEW-R18

brief-kind=review；家族=GROK；輪次=R18；審查標的 commit `763b9d56`；禁改碼／禁 commit。

## Verdict：需修補後收工

Task 4.1／4.2／4.3／2.4 契約本體（CSCV lazy＋雙預算、PBO＋A1-15 壓縮名次、宇宙守衛、AST wiring）**大體成立**；
`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q`
→ **269 passed rc=0**；`test_ledger.py` → **25 passed rc=0**。
mutation receipt `handoffs/run_receipts/20260818T100000Z-gap1-b4-mutation.log`：**20／20 皆 rc=1**、baseline／post-restore 266 passed（本輪**未**重跑探針，遵 brief 鎖／互斥指引）。
數值重算：`C(12,6)=924`／`C(14,7)=3432`／`C(16,8)=12870`；塊長 `[101]*5+[100]*7`；`12870*2000=25740000>20M`；golden noise **0.6483**；`mu=0.00010684346079267205` 與 JSON 逐位一致。

但段 B 攻擊中，**W3 passthrough 過寬可繞過自創 reason** 被實跑推翻為須修補；另有雙冠廉價綠燈、`n_path_exclusions` 重複計數、名次母體字面漂移等 P2。

| assumed / 攻擊點（A1-23＋brief） | 本輪結論 |
|---|---|
| 向量化 sharpe 等價鎖足以取代字面 `compute_sharpe` | **可接受**（exact／近常數兩邊一致；近常數不視為退化＝B1 既有，非本批引入） |
| W3 passthrough 封閉無繞過洞 | **推翻** → P1-01（Attribute／任意 Subscript key／unbound Name／`get` 任意 key） |
| `ledger.py` 靜態化等價＋未來 fail-closed | **成立**（25 passed；多 reason 須顯式處理） |
| `len(ids)!=n` ValueError 不可達 | **可接受**（守衛先＝TODO 字面；保留死碼作腰帶或刪並註解皆可） |
| golden 晚建／sha256 只在 `test_pbo` | **可接受本批收工**；過程債 → P2-04 |
| OOS 名次母體＝OOS 有限候選 | **語意可接受、字面漂移** → 須延伸檔鎖死 → P2-03 |
| §V-14 新測使壓縮索引突變轉紅 | **成立**（receipt §V-14 rc=1；④d′ 手算 ω） |
| 雙冠斷言雖弱但間接覆蓋 | **推翻為廉價綠燈** → P2-01 |
| `n_path_exclusions` 計數 | **champion OOS 退化重複 +1** → P2-02 |

非根本缺陷、不需重作 B4；建議修補 W3 謂詞＋補雙冠可證偽斷言（及計數／延伸檔）後收工。

**工作區觀察**：本輪未改任何產品碼；探針鎖不存在；`/tmp` workdir 收尾清除（保留 `claude-501`）。

---

## 段 A — 契約符合度（Task 4.1／4.2／4.3／2.4）

### Task 4.1 — **符合**
- `cscv_path_count`／`iter_cscv_splits`／`CscvBudgetExceeded` 簽名與語意到位。
- 預算於 generator 建立前 raise（`path_count` 算完即判，再 `return _iter_splits`）。
- 餘數規則：`base+1` 前 `rem` 塊；驗收①–⑥皆有對應測試；`inspect.isgenerator` 真。

### Task 4.2 — **語意符合；兩處字面／測試弱點見段 B**
- 簽名與 `PBOResult` 12 欄在場；守衛非 ok 即回、`universe_scope=None`；ok ⇒ `ledger_recorded_only`。
- 平手取最小原始索引（`path_valid` 升冪＋`argmax` 首個）；A1-15 `pos`／champion OOS 退化跳過不重選；分母＝`n_paths_used`。
- 驗收①–⑨有測試覆蓋；④b 斷言弱（P2-01）；向量化偏離字面但有等價鎖（可接受）。

### Task 4.3 — **符合**
- `UniverseProvenance.__post_init__` 型別驗證；三項全符才 ok；`full_grid`／`external_declared` 無例外 unverifiable。
- 無 `force`、不接受自備 hash 為證明；驗收①–⑤d 落地；§V-6 receipt 6 條轉紅。

### Task 2.4 — **AST／W1–W4／六 mutation／旗標符合；W3 passthrough 過寬（P1-01）**
- AST 非 regex；W1／W4 只認頂層無條件（If／For／While／Try／With 內不計）——mutation ⑥ 鎖死。
- W2 死枚舉；W3 三形＋`[unresolved]`；rc 0／1／2；`--contract`／`--pkg` 禁 env。
- ⑤b（變數持 f-string）**有效補強**（非多餘）：單測⑤只打 JoinedStr 直傳，⑤b 打 Name 鏈。
- 現行 `bash scripts/strategy_wiring_check.sh` 本輪未重跑；以 brief fact-verified＋mutation／單元測試為準。

```
VERIFY: venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q
→ 269 passed, rc=0
VERIFY: venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_ledger.py -q
→ 25 passed, rc=0
VERIFY: 讀 receipt handoffs/run_receipts/20260818T100000Z-gap1-b4-mutation.log
→ 20/20 mutation rc=1；baseline/post-restore 266 passed；探針總 rc=0
```

---

## 段 B — 攻主委實作決定（A1-23 七項＋brief 兩項）

### B1. 向量化 sharpe（A1-23 #1）— **可接受**
- 等價鎖含 std=0（用 `0.5` 使 std 恰 0）／NaN／n<2，atol 1e-15。
- 實跑：`ones*0.01` 因 float 使 `std≈1.7e-18≠0` ⇒ 兩邊皆回 ~5e15 **且逐位相同**；近常數 `0.01+1e-16·arange` 兩邊 diff=0。
- 「浮點近常數不視為退化」＝`compute_sharpe` 之 `std == 0.0` 精確比對（B1 既有）；**非向量化引入之歧異**。
- 裁定：向量化可留；若要收緊退化語意應**另票修 `compute_sharpe`**（會影響 PBO path 級剔除），不在本批強制改回逐欄呼叫。

### B2. W3 passthrough（A1-23 #2）— **須改（P1-01）**
- ① 跨函式同名＋f-string：**不會**誤判合規——`_name_assignments` 不分作用域，任一來源為 JoinedStr ⇒ 全鏈 unresolved（實跑 `cross_fn_fstring_blocks` ⇒ unresolved）。此場景是**誤擋（假紅）**而非放行。
- ② Attribute **一律** `True`（不要求 `attr=="reason"`）；Subscript 只要求 slice 為 str Constant（**不要求 key=="reason"`**）；`get` 同理不檢查首參；無指派 Name ⇒ 當參數放行。
- ③ 實跑繞過（tmpdir 複製 pkg）：
  - `reason=data["x"]`（`data={"x":"invented_v"}`）⇒ wiring **rc=0**
  - `reason=o.reason`（執行期寫入自創字串、檔內無 `reason=<Const>`）⇒ **rc=0**
  - `reason=dyn`（檔內無 Assign）⇒ unresolved=False
- 裁定：passthrough **應保留**（否則 `eligibility.reason` 使 gate 不可達），但謂詞須收窄為延伸檔白名單：`x.reason`／`x["reason"]`／`x.get("reason", <Const|passthrough>)`／兩支合規 IfExp／Name（同函式作用域來源皆白名單或為參數）。**現行過寬＝可繞過 W3 自創 reason 之 fail-closed 宣稱**。

### B3. `ledger.py` reason 靜態化（A1-23 #3）— **可接受**
- `reason = _REASON_ROW_INVALID if _REASON_ROW_INVALID in reasons_seen else ""`；`reasons_seen` 只 append 該字面。
- `test_ledger.py` 25 passed 鎖今日等價；未來多 reason 若仍只認 `_REASON_ROW_INVALID` 會把其他 reason 靜默丟成 `""`（fail-closed 於「須改碼才支援」），W3 亦不再允許 `reasons_seen[0]` 動態取值。

### B4. 不可達 `len(ids)!=n` ValueError（A1-23 #4）— **可接受**
- TODO 字面＝守衛先；`test_transpose_raises_and_short_t_ok` 具名記錄 unverifiable 路徑。
- 刪死碼或保留腰帶皆可；**不**建議改守衛順序（會違 TODO）。

### B5. golden 檔（A1-23 #5）— **過程債，不擋演算法（P2-04）**
- §G「Task 3.1 前建立」時序違約已發生；B4 補建＋`test_pbo` sha256 雙點變更可審計。
- sha256 **只**在 `test_pbo.py` 檢一次：改 golden 會紅 PBO／解析常數測試，但**不**自動紅未讀檔之 B3 內嵌常數測試——若兩處日後分叉靠人。provenance 欄具文獻／A1 出處，合 §G 精神。

### B6. PBO 名次母體（A1-23 #6）— **語意可接受；須延伸檔鎖字面（P2-03）**
- Bailey／CSCV 敘事：對**具 OOS 表現之策略**取相對名次，`r=rank/(N+1)`。`rankdata` 遇 NaN 會污染全體 ⇒ 實作改 `oos_valid` 母體是數值上必要。
- 與 TODO「`len(valid_cols)+1`」在 excl>0 時**不等價**（golden excl=0 故觀察不到）。
- 裁定：**不改回** IS `valid_cols` 分母；走延伸檔把母體寫成「該 path OOS 亦有限之候選」。

### B7. §V-14 首版未轉紅（A1-23 #7）— **已修好，確認**
- `test_rank_uses_compressed_position_not_original_index`：欄 0 全 NaN ⇒ `valid_cols=[1,2,3]`、champion 原始索引 3、壓縮位置 2；手算 `ω=ln((3/4)/(1/4))`；receipt §V-14 → 1 FAILED。
- ④d 仍測「OOS 退化跳過不重選」（與 ④d′ 分工清楚）。

### B8. 雙冠測試（④b）— **廉價綠燈（P2-01）**
- 只斷言 `n_paths_used==2`；④c 段落**未呼叫 PBO**，只測 `rankdata` 公式。
- 可證偽寫法（本輪實跑骨架）：S=2、`mean_return`、IS 平手最小索引 champion 之 OOS 名次最低 ⇒ `logits` 含 `ln((1/4)/(3/4))`；若誤取較大索引則得 `ln(3)`——**直接 assert logits**，勿只數 path。

### B9. `n_path_exclusions`（brief #9）— **重複計數（P2-02）**
- 路徑：先 `n_excl += len(path_valid)-len(oos_valid)`（已含 champion OOS 非有限），再於 skip 分支 `n_excl += 1`。
- 實跑 ④d fixture：`skipped=1, used=1, excl=3`（champion 被計兩次）。
- TODO／A1-15 各自寫 +1，疊加後語意漂移；應二擇一：剔除時已 +1 則 skip 不再 +1，或 skip 的 +1 取代一般剔除計數並具名。

---

## 段 C — 測試品質

### Mutation（讀 receipt，未並行重跑）
- §V-4／6／14 皆 rc=1；對應 TODO／A1-3／A1-15 字面；**無假紅跡象**（§V-4 打 golden band；§V-6 打守衛測試；§V-14 打壓縮索引）。
- baseline 紅即 fail-closed、post-restore 全綠——程序正確。

### Wiring 六＋⑤b
- ① W1、②③ W3 字面、④ W1 註解假綠、⑤ unresolved、⑥ W1+W4 死分支——各打不同規則。
- ⑤b **有效**：鎖「經變數之 f-string」；與⑤互補。

### Golden band／`abs=5e-5`
- band 為主契約；`abs=5e-5` 對寫死 RNG 之 0.6483 可重現（本輪實跑 round 4 位＝0.6483）。
- 非過度綁定實作細節（未鎖中間 ω 向量）；可接受。

---

## 段 D — 數值／契約正確性

| 項目 | 結果 |
|---|---|
| `C(12,6)/C(14,7)/C(16,8)` | 924／3432／12870 |
| `n_obs=1205,S=12` 塊長 | `[101]*5+[100]*7` |
| `S=16,n_obs=2000` | 25,740,000 > 20M ⇒ raise |
| noise／α_det／α_undet | 0.6483／（測試 `<0.30`）／（測試 `>0.40`；brief 0.5411） |
| `0.01/sqrt(8760)` | `0.00010684346079267205`＝golden mu |
| 全平手 ⇒ ω=0 | `test_all_tie…` 鎖住 |
| 4 有效 ⇒ ω∈{ln(k/5/(1-k/5))} | `test_nan_candidate…` 鎖住 |

---

## Canonical findings

## GROK-R18-P1-01

**斷言**: W3 passthrough 謂詞過寬——任意 `Attribute`、任意字串鍵 `Subscript`／`get`、以及檔內無 Assign 之 `Name` 皆放行，可使自創 reason 經屬性／字典查找繞過 wiring 閘而 rc=0。

**碼證**: `scripts/strategy_wiring_check.py` `_is_passthrough`（Attribute 無條件 True；Subscript 只驗 slice 為 str；Name 無來源⇒True）。RECHECK：tmpdir 複製 `strategy_validation` 後寫 `reason=data["x"]`（`data={"x":"invented_v"}`）⇒ `strategy_wiring_check.py --pkg …` **rc=0**；`reason=o.reason`（執行期自創字串）⇒ **rc=0**；對照 `reason=f"x_{i}"`／`tmp=f"..."; reason=tmp` ⇒ rc=1。

**來源摘要**: scripts/strategy_wiring_check.py#4d8c4fe6e979

[MAJOR] 信心度=High。修法：白名單收窄為 `x.reason`／`x["reason"]`／`x.get("reason", …)`／合規 IfExp／同**函式**作用域 Name；其餘維持 unresolved。並加 mutation：`reason=data["not_reason"]` 與 `reason=obj.other` 必須 rc=1。延伸檔具名白名單（對應 A1-23 #2 裁定「改字面＋白名單」）。

## GROK-R18-P2-01

**斷言**: `test_double_champion_takes_smallest_index_and_denominators` 未直接證明「平手取最小原始索引」——只斷言 `n_paths_used==2`，且 ④c 未呼叫 PBO。

**碼證**: `tests/momentum/Analysis/strategy_validation/test_pbo.py` 該測末段；本輪構造 S=2／IS 平手／OOS 名次分離矩陣 ⇒ 正確實作 `logits` 含 `ln(1/3)≈-1.0986`，誤取大索引則得 `ln(3)`——**現行測試兩者皆能綠**。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_pbo.py#e8b4f5b90d86

[MINOR] 信心度=High。修法：assert 至少一條 path 之 ω 等於最小索引 champion 之手算值（或 mock／spy champion 索引）；④c 改為兩次真實 PBO 呼叫比較不同 `n` 有效候選下之 ω。

## GROK-R18-P2-02

**斷言**: champion OOS 退化時 `n_path_exclusions` 對同一候選重複 +1（一般 OOS 剔除一次＋skip 分支再一次）。

**碼證**: `pbo.py` 約 L213–218：`n_excl += len(path_valid)-len(oos_valid)` 後，`if not finite(champ) or len(oos_valid)<2: n_excl += 1`。RECHECK：④d fixture ⇒ `n_paths_skipped=1, n_paths_used=1, n_path_exclusions=3`（champion 雙計）。

**來源摘要**: momentum/Analysis/strategy_validation/pbo.py#c1f466553416

[MINOR] 信心度=High。修法：skip 時若 champ 已在 OOS 剔除集合則不再 +1；或具名「path-skip 附加計數」並改測試期望。同步延伸檔／TODO 一句話消歧。

## GROK-R18-P2-03

**斷言**: 實作以「OOS 亦有限候選」為名次母體，與 TODO 字面 `r=rank/(len(valid_cols)+1)` 在 `n_path_exclusions>0` 時不等價；golden 三案例 excl=0 蓋不住此差。

**碼證**: TODO Task 4.2 步驟 2 vs `pbo.py` L220–223 `r = rank/(len(oos_valid)+1)`；A1-23 #6 自揭。Bailey／CSCV 敘事支持對有定義 OOS 指標者排名（`rankdata`+NaN 不可用）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#e559a616f00a

[MINOR] 信心度=High。修法：**保留** `oos_valid` 母體；延伸檔改寫 TODO 字面並加 excl>0 之單測（手算分母）。不要求改回 `valid_cols`（會強迫 NaN 進 `rankdata` 或需另造填充規則）。

## GROK-R18-P2-04

**斷言**: golden 檔未在 Task 3.1 前建立（§G 時序），且 sha256 防篡只掛在 `test_pbo.py`——B3 內嵌解析常數測試不讀該檔，存在雙源漂移窗口。

**碼證**: A1-23 #5；`_GOLDEN_SHA256` 僅 `test_pbo.py`；`gap1_reference_cases.json` provenance 欄完整。B4 補建後 PBO／cscv／min_btl 對照已進 `test_golden_file_sha256_and_analytic_constants`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#3a32678eeed8

[MINOR] 信心度=Medium。修法：過程債入帳即可；可選讓 B3 常數測改讀 golden，或在 CI／gate 加「golden sha256 單點」。不擋 B4 演算法收工。

---

## 被當成事實的未驗證假設（§0）

1. assumed「向量化 sharpe 等價鎖足夠」→ **成立**（含近常數兩邊一致）；近常數不退化＝B1 既有，另票可選。
2. assumed「W3 passthrough 無洞」→ **推翻**（P1-01）。
3. assumed「OOS 名次母體不改變 PBO 定義」→ **對 golden 無觀測差；對 excl>0 改變分母**（P2-03；語意仍合理）。
4. assumed「雙冠弱斷言由 ④d′／golden 間接覆蓋」→ **推翻**（P2-01；④d′ 測壓縮索引非平手最小索引）。

## 11 類速檢（V13 §1）
1. 矛盾：TODO 名次分母 vs 實作（P2-03）；其餘無。
2. 漏項：無（2.4 已落 B4 末）。
3. 不可測：雙冠④b 偏不可證偽（P2-01）。
4. quant：近常數 SR 爆炸＝B1 行為；名次母體見 P2-03。
5. 過度工程：無（向量化有等價鎖）。
6. OOM：雙預算在場。
7. Cache：本批無。
8. API／型別：無跨域 DTO 問題。
9. 測試：見 P1-01 缺 mutation、P2-01。
10. Agent 可執行：契約足夠。
11. 短命工：無。

STATUS: DONE
