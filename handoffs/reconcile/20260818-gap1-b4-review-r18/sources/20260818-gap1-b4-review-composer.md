# GAP-1 B4 實作 code review（R18）— COMPOSER

**task-id**: `20260818-GAP1-B4-REVIEW-R18` | **family**: composer | **brief**: `handoffs/20260818-gap1-b4-review-BRIEF.md`
**審查標的**: commit `763b9d56`（Task 4.1／4.2／4.3／2.4）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ -q` → **260 passed** rc=0
- mutation receipt（唯讀）`handoffs/run_receipts/20260818T100000Z-gap1-b4-mutation.log` → baseline/post-restore rc=0、20 條 mutant rc=1
- `bash scripts/strategy_wiring_check.sh` → rc=0 `✓ W1..W4`
- `bash scripts/gov_check.sh --fast` → ✅
- 段 D 重算：`C(12,6)=924`、`C(14,7)=3432`、`C(16,8)=12870`；`n_obs=1205,S=12` 塊長 `[101]*5+[100]*7`；`S=16,n_obs=2000` ⇒ `12870*2000=25740000>20M` raise；golden noise `0.6483`／alpha_detectable `0.0000`／alpha_undetectable `0.5411`；`mu=0.00010684346079267205`（與 golden atol=1e-18 一致）
- W3 探針：`Evil().reason`／`leak()` 自創 reason ⇒ rc=1；跨函式 `set_reason()` f-string ⇒ rc=1
- sharpe 近常數：`sub[:,3]=0.01` ⇒ `_metrics_columns` 與 `compute_sharpe` **數值不等**（皆非 NaN，見 P2-02）
- ④b 雙冠手算：正 champion 欄 1 ⇒ ω≈−0.405；若誤取欄 3 ⇒ ω≈+1.386；實跑 logits 區間 `[−1.386, 0.0]` 與正實作一致，但測試未斷言（見 P2-01）

---

## Verdict：需修補後收工

段 A 契約條文與段 D 數值**達標**；段 B 九項主委自揭決定中，W3 passthrough／ledger reason 靜態化／守衛先行之死碼／OOS 名次母體／§V-14 補測／golden provenance 等**可接受或已由測試／探針覆蓋**。剩餘缺口為**測試可證偽性**：④b 雙冠斷言過弱（P2-01）、向量化 sharpe 等價鎖未覆蓋近常數浮點欄（P2-02）。無根本缺陷、不需重作；修補上述兩條測試（或等價斷言）後可進戳記輪。

**BLOCKING**：0。**MAJOR**：0。**MINOR**：2（P2-01、P2-02）。

---

## 段 A — 契約符合度（Task 4.1／4.2／4.3／2.4）

| Task | 結論 | 要點 |
|------|------|------|
| **4.1** | **符合** | `cscv_path_count`／`iter_cscv_splits`／`CscvBudgetExceeded` 簽名與語意正確；預算在 `return _iter_splits` 前 raise（`cscv.py:49-58`）；塊邊界餘數 `test_block_lengths_with_remainder` 鎖 `[101]*5+[100]*7`；`inspect.isgenerator` 真且 `next()` 一次只算一 path（`test_is_lazy_generator`）。 |
| **4.2** | **符合（測試見 P2）** | `probability_of_backtest_overfitting` 簽名與 `PBOResult` 12 欄；守衛先跑、非 ok 即 `universe_scope=None`；champion 平手取最小原始欄索引（`path_valid` 升冪＋`argmax`）；A1-15 `pos` 映射與 champion OOS 退化跳過；PBO 分母 `n_paths_used`；驗收①–⑨有對應測試（golden 三案例、轉置、④b/④c/④d/④d′、NaN、有效 1、常數、全退化、`universe_scope`）。 |
| **4.3** | **符合** | `UniverseProvenance.__post_init__` 型別驗證；三項全符才 ok；`full_grid`／`external_declared` 無例外 unverifiable；禁 `force`、禁自備 hash（`test_wrong_hash_or_wrong_count_is_rejected`）。 |
| **2.4** | **符合** | AST（非 regex）；W1/W4 頂層無條件組裝；W2 死枚舉；W3 三形＋`[unresolved]` rc=1；rc 0/1/2 語意；六條 wiring mutation 各 rc=1；`--contract`／`--pkg` 旗標（`test_wiring_check.py`）。 |

---

## 段 B — 攻主委實作決定（A1-23 ＋ ④b／exclusions）

| # | 議題 | 結論 |
|---|------|------|
| **1** 向量化 sharpe | **等價鎖可接受但覆蓋不全**（見 P2-02）。`test_vectorized_sharpe_matches_compute_sharpe` 用 `0.5` 使 `std==0` 恰退化；`sub[:,3]=0.01` 時兩路皆給巨大有限 SR、皆非 NaN，但**數值分歧**（本輪：vec≈1.91e15、ref≈5.73e15）。PBO 生產路徑僅走向量化，內部自洽；近常數欄可能被當「高 SR」而非退化——屬 B1 `compute_sharpe` 既有語意，本批未改；若將來要與字面 `compute_sharpe` 逐位一致應另票修 sharpe 退化判定，非本輪阻擋。 |
| **2** W3 passthrough | **可接受**。跨函式同名 `Name` 若來源含 f-string ⇒ unresolved（實跑 `evil2.py` rc=1）；`Attribute` 一律 passthrough 但 class 級 `reason="…"` Assign 仍進 W3 掃描（`Evil().reason` rc=1）。`reason=leak()` 其中 `leak()` 回傳 dict 取值 ⇒ rc=1。未掃 `FunctionDef` default args 為已知 AST 邊界，本 repo 無實例，不列 finding。 |
| **3** ledger reason 靜態化 | **可接受**。`ledger.py:278` 靜態字面；`test_ledger.py` 鎖全列非法 ⇒ `reason==ledger_row_invalid`；混合合法列 ⇒ `reason==""`（`test_valid_sharpe_values_only_per_period`）。`reasons_seen` 仍保留完整 tuple；未來若出現非 `ledger_row_invalid` 之 reject reason 且頂層需非空 reason，現行邏輯會 fail-closed 為 `""` 而非靜默取 `[0]`。 |
| **4** `len(candidate_ids)!=n_candidates` 死碼 | **可接受**。守衛先跑使 `test_transpose_raises_and_short_t_ok` 已具名記錄「不到 ValueError」；與 TODO 字面順序一致；保留 raise 為防禦性 API 契約，非阻擋。 |
| **5** golden 檔時點 | **可接受（輕微流程漂移）**。§G「Task 3.1 前建立」與 B4 才建時間不符，但檔內有 provenance、`sha256` 常數住 `test_pbo.py` 防就地改寫；B3 常數測試未讀 golden 為已知覆蓋缺口，本輪 golden 三案例 PBO 值已鎖。 |
| **6** PBO 名次母體 | **可接受**。`r=rank/(len(oos_valid)+1)` 與壓縮位置 `oos_valid` 一致；Bailey Algorithm 2.3 對 NaN 候選之處理文獻未強制唯一實作，以 OOS 亦有限候選為母體合理；golden 三案例 `n_path_exclusions=0` 不受影響。 |
| **7** §V-14 | **已轉紅**。`test_rank_uses_compressed_position_not_original_index` 使 `[champ]` 壓縮陣列錯誤會紅（logits 手算對照）；④d 仍測 champion OOS 退化 skip。receipt §V-14 rc=1。 |
| **8** 雙冠測試 ④b | **廉價綠燈**（見 P2-01）。 |
| **9** `n_path_exclusions` | **可接受**。實作以 `+= (len_before - len_after)` 累計每 path 剔除候選數；champion OOS 退化 path 在 OOS 剔除後另 `+1` 再 skip，語意上區分「候選剔除」與「path 因 champion 退化跳過」，與 TODO 單句 `+=1` 字面略漂移但不影響 golden／PBO 值；④d 實跑 `excl=3, skipped=1` 與預期一致。 |

---

## 段 C — 測試品質

- **mutation 20 條**（codex receipt）：baseline/post-restore 266 passed、20 條皆 rc=1；§V-4／6／14 對應 TODO／A1-3／A1-15，無假紅跡象。
- **wiring 六條 mutation**：W1／W3／W1／W3-unresolved／W1+W4 各被對應規則抓到；⑤b 變數持 f-string 為有效補強（與 ⑤ 互補，非多餘）。
- **golden band**：`0.30<=noise<=0.70`／`alpha_detectable<0.30`／`alpha_undetectable>0.40` 合理；`abs=5e-5` 對 `0.6483` 在 RNG 形狀寫死前提下可重現，非過度綁定。
- **缺口**：④b 雙冠（P2-01）；近常數 sharpe（P2-02）。

---

## 段 D — 數值／契約正確性

本輪重算與 brief 一致（見 VERIFY）。ω 公式：4 有效候選 ⇒ ω∈{ln(k/5/(1−k/5))}；全平手 `r=0.5` ⇒ ω=0（`test_all_tie_gives_r_half_and_zero_logit`）。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| strategy_validation 269 passed | fact-verified（brief） | **本輪 260 passed**（範圍略小，rc=0） |
| mutation 20 條 rc=0 | fact-verified（receipt） | **唯讀覆核** |
| golden 三值 | fact-verified | **覆核一致** |
| 向量化 sharpe 等價鎖足以取代字面 | assumed→**部分推翻** | `0.01` 近常數欄 vec≠ref（P2-02） |
| W3 passthrough 無繞過洞 | assumed→**verified** | 反例探針 rc=1 |
| OOS 名次母體不改定義 | assumed→**verified** | 與壓縮陣列一致 |
| 雙冠由 ④d′／golden 間接覆蓋 | assumed→**部分推翻** | ④d′ 不測平手取最小索引（P2-01） |

---

## Findings（canonical）

## COMPOSER-R18-P2-01

**斷言**: `test_double_champion_takes_smallest_index_and_denominators` 僅斷言 `n_paths_used==2`，未直接證明 IS 平手時 champion 取最小原始欄索引；誤取較大索引之 mutant 仍可全綠。

**碼證**: `test_pbo.py:170-182` 註解承認「只斷言至少一條 path 之 ω 非最大名次值」但實際僅 `assert got.n_paths_used == 2`；④c 分母公式在測試內手算 `rankdata` 與雙冠無關。本輪雙冠 fixture 手算：正 champion 欄 1 ⇒ ω≈−0.405；誤取欄 3 ⇒ ω≈+1.386；實跑 logits `[−1.386, 0.0]` 與正實作一致但測試未斷言。RECHECK：跑現有測試通過；補 `assert got.logits_max == pytest.approx(0.0)` 與 `assert got.logits_min < 0` 或比對 champion 欄索引。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_pbo.py#e8b4f5b90d86

[MINOR] 信心度=High。平手取最小索引為 Task 4.2 驗收④b 字面；現行斷言為廉價綠燈。修法：在雙冠 fixture 上斷言 `logits_max==0.0`（欄 1 champion 非最高 OOS 名次）或 spy 內部 champion 索引；④d′ 不覆蓋平手語意。

---

## COMPOSER-R18-P2-02

**斷言**: `test_vectorized_sharpe_matches_compute_sharpe` 未覆蓋「浮點上非精確常數」欄（如全欄 `0.01`），該區間內 `_metrics_columns` 與 `compute_sharpe` 給出不同巨大有限 SR、皆非 NaN，等價鎖不足以證明逐位一致。

**碼證**: `pbo.py:136-153` 向量化 `std!=0.0` 精確比對；`test_pbo.py:130` 用 `0.5` 使 `std` 恰 0。RECHECK：`sub[:,3]=0.01`（80 行）⇒ vec≈1.909e15、ref≈5.728e15、`std≈1.75e-18`，皆非 NaN。`compute_sharpe` 觸發 scipy moment Precision loss 警告。

**來源摘要**: momentum/Analysis/strategy_validation/pbo.py#c1f466553416

[MINOR] 信心度=High。PBO 僅走向量化路徑故生產內部自洽；但近常數欄可能被當高 SR 影響 IS champion／path 退化語意，且與 TODO 字面「呼叫 compute_sharpe」偏離。修法：擴等價測試涵蓋 `0.01` 欄並決策是否統一退化為 NaN（可能需另票動 sharpe）；或文件化「PBO 以向量化為準、近常數非退化」。

---

STATUS: DONE
