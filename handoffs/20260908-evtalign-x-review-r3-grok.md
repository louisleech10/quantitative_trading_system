brief-kind: review
task-id: 20260908-EVTALIGN-X-REVIEW-R3
family: grok
findings-round: R3
標的 commit: `efb16e4c`（B1；對照基線 `097dae40`）
SCOPE: review-only；禁改產品碼／SPEC／TODO（本輪曾 `git checkout --` 還原 mutate C0 殘留註解至 HEAD，非改碼）
CONTRACTS-DIGEST: momentum/core/contracts.py#f817321f9e43
ORCH-DIGEST: momentum/Analysis/ic_filter_orchestrator.py#ad7b19170f9a
SERVICE-DIGEST: api/services/ic_analysis_service.py#5134e9ce7184
TODO-DIGEST: docs/GAP3_EVENT_ALIGNMENT_TODO.md#e2b6c6eebb68
SPEC-DIGEST: docs/GAP3_EVENT_ALIGNMENT_SPEC.md#52935f426843
COUNTEREX-OLD: handoffs/20260907-evtalign-r2-grok-counterexamples.py#aae975eec9d1
COUNTEREX-NEW: /tmp/evtalign-r3-grok-work/r3_vs_newcode.py（對新 API；收尾已清）

---

## Verdict：可合併進 B2——但 P1（D5／TODO 要點 3）須在 B2 參數化變成機械契約，不得帶歧義進 B3

B（`_coterminalize_close` 兩呼叫點）與 D（`derive_label_kind`／`validate_event_given` 值綁定／service 三元組）對 grok 在 R2 提出的 **P0 主洩漏**（spoof `label_kind`、值旋轉）已在新碼上重跑反例關閉。  
**唯一未關之原提出項＝D5／`GROK-R2-P0-02`**：TODO 要點 3 要求事件覆寫前不驗鷹架，實作仍跑 stage2 `validate_alignment`；B 已消掉截短主誤擋，但中段缺口／覆蓋率紅仍可「驗了就丟」。此為 **P1**，建議交 B2（Task 2.2「被驗＝被用」）收斂，**非**新 P0。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/momentum/test_close_coterminalize.py tests/api/test_event_label_alignment.py -q -rs` | **14 passed, 0 skip**, rc=0 |
| `bash scripts/evtalign_phase_gate.sh 1` | **`GATE PASS: phase=1`**, rc=0（mutation UNCOVERED=0） |
| `venv/bin/python handoffs/20260907-probe-split-baseline.py` | rc=0；`與既有 golden 相同？ **True**`；sha256=`e378c706…ba7201` |
| `venv/bin/python handoffs/20260908-probe-stage0-trim-oracle.py` | rc=0；`逐鍵相同 = True`（checked_samples 58＝58） |
| `venv/bin/python -m pytest tests/momentum/event_samples/test_gap3_conditional_ic.py -q` | **8 passed**, rc=0 |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_ichc_p2_golden.py -q` | **1 failed**（`config_hash` 漂移，見 §0；**非** B 裁切所致） |
| `shasum -a 256 -c handoffs/20260908-evtalign-r3-baseline.sha` | 還原 C0 殘留後 **全 OK**, rc=0 |
| `venv/bin/python handoffs/20260907-evtalign-r2-grok-counterexamples.py` | rc=0；紙上舊假設仍印 G/I/J 漏／誤擋（對照用） |
| `PYTHONPATH=. venv/bin/python /tmp/…/r3_vs_newcode.py` | rc=0；對新 API：D1/D2/I/G 主路徑 **BLOCKED**；A 截短＋B **PASS** |

開工時工作區 `ic_filter_orchestrator.py` 留有 mutate **C0** 對照註解 `(control)`（與 HEAD 差 1 行）；已 `git checkout --` 還原後 baseline 全綠。疑為 gate／並行 mutate 還原競態，非 B1 邏輯改動。

---

## 1a. R2 逐條 CLOSED／OPEN（原提出方＝grok 者附重跑）

| R2 群集 | 原 ID | 本輪 | 重跑／碼證 |
|---|---|---|---|
| D1 spoof `label_kind` | `GROK-R2-P0-01` | **CLOSED** | 新碼 `derive_label_kind("event_given")`／`None` → `AlignmentViolationError`；合法僅 `event_label_value`／`mainline_return_N`。mutation D2 錨此。 |
| D2 `bars_after` 可偽造 | （codex 主提；grok R2-P2-02） | **CLOSED** | 參數不存在；`_coterminalize_close` 依 `feature_index[-1]`；trim len=40＝feat。 |
| D3 close 污染自洽 | `GROK-R2-P2-01` | **CLOSED→殘留** | 守衛未改；`EA-RESID-4` 保留。紙上 Case H 仍成立，非本批回歸。 |
| D4 值旋轉 | `GROK-R2-P1-01` | **CLOSED** | `validate_event_given` 值≠expected → raise；service `_assert_event_triple_bound` 旋轉 → raise。 |
| D5 覆寫前仍驗鷹架 | `GROK-R2-P0-02` | **OPEN（降為 P1）** | 見必答 4 與 `GROK-R3-P1-01`。截短主誤擋已被 B 消掉；TODO 要點 3 仍未落地。 |
| D6 基線不足 | `GROK-R2-P1-02` | **CLOSED** | golden v2：`split_row_fingerprint`＋`retained_event_ids`＋預載；probe **True**。 |
| D7 excess 無 oracle | （codex） | **CLOSED→殘留** | B 後同尾 proper＋`excess`：`validate_alignment` **PASS**（checked=0）；`EA-RESID-5`。 |
| D9 mutation ID | （codex） | **CLOSED** | gate phase1 PASS；腳本 8 條唯一 ID（B1/B2/B3/D1/D2/D3/A4/C0）。 |

### 1b. 閉合有無新誤擋

| 閉合 | 合法 run 因閉合而 raise？ |
|---|---|
| D1 | 否。合法 producer `label_source` 映射通過；缺席／未知才紅（有意 fail-closed）。 |
| D2/B | 同尾 no-op；截短化約同尾後 proper log 通過（Case A）。短於 feature 之 close 仍交守衛紅（有意）。 |
| D4 | 否。值與 owners 一致通過；旋轉／缺 owner／dup owner 才紅。 |
| D6 | 否。基線對證 True，未改切分。 |

---

## 必答（成對）

### 2a. B 會不會漏（裁切後守衛過、仍 look-ahead）？

**在正規化後之單調唯一 index＋oracle 種類下：R1/R2 那類未 shift／錯 lag 仍擋**（新碼 Case B：`trailing NaN … expected 5, got 0`）。  
提示路徑逐項：

| 構造 | 結果 |
|---|---|
| 非單調 close index | `_normalize_ic_time_index`／`_normalize_frame_time_index` **先** raise（兩呼叫點皆經此）→ 裁切前已擋 |
| 重複 timestamp | 同上 `must be unique` |
| close 中段缺 index（gap） | 裁切後 proper 生成 → 覆蓋率紅（`actual=0.8000, required>=0.8662`）——擋的是品質，不是放行 look-ahead |
| K 線尾早於 feature 尾 | coterminalize **no-op**；守衛仍以尾端 NaN／oracle 判定（本票明文） |

**未構成「裁切後放行 look-ahead」之新洞。** 殘留信任邊界仍是污染 close 自洽（`EA-RESID-4`）。

### 2b. B 會不會誤擋？

**同尾／截短＋proper log／simple：不誤擋**（A PASS；stage0 oracle 逐鍵相同）。  
**短 close**：守衛紅（既有）。  
**excess／risk_adjusted**：B 後同尾 proper **PASS**（不再因截短＋無 oracle 誤擋）——與 brief assumed 一致。

### 3a. D 會不會漏（錯事件 label 同時過 `validate_event_given`＋owners **與** service 回比）？

**在產生者自洽前提下：值旋轉／錯 id 回報會紅**（I＋svc_rotation）。  
**仍漏**：攻擊者（或 bug）讓 `event_label_values`、`event_label_owners`、`event_label_by_id` **三者一起**寫成同一套錯誤真相 → 兩層皆 PASS。這是 **producer 信任邊界**，不是 timestamp→value 三檢查那種結構洞；D 把信任從 caller 字串推到 service 產生迴圈，**不能**再證外部事件檔未被竄改。

### 3b. D 會不會誤擋？

| 情形 | 結果 |
|---|---|
| `event_owners=None` | 契約層 PASS（`consumed_event_labels={}`）；**service** 對 `label_source=event_label_value` 且空 consumed → **raise**（有意：service 路徑必帶 owners） |
| tz-aware index 自洽 ms 鍵 | `validate_event_given` **PASS**；naive／UTC 同壁鐘 `asi8//10**6` 鍵相同 |
| float／JSON 往返（`1/3`、`0.1+0.2`） | `_assert_event_triple_bound` **PASS**（本輪未見誤擋） |
| fallback `mainline_return_N` | service 早退不回比（碼證 `:117-118`） |

### 4a. 刻意保留 stage2 對鷹架之 `validate_alignment`——是否成立？

**部分成立，不能當 TODO 要點 3 已關閉。**

- **成立的部分**：B 之後，產生器吐出的 proper 鷹架在截短情形下不再觸發 UAT 那類尾端 NaN 誤擋；`excess` 同尾 proper 亦 PASS。作者「跳過＝`if 事件: skip validate`」若理解成**整段不驗任何 label**，確實違 §C-6。
- **不成立的部分**：§C-6 判準是「驗**被使用的那份**」；`event_label_values is not None` 時 stage2 序列**將被丟棄**，硬閘仍跑它＝TODO 要點 3 明文禁止的形狀。這是 **資料是否將被覆寫**（已在 `analyze()` 入口可知），不是「mode 字串分支決定要不要驗」。保留＝**文件／碼不一致**，且把「K 線缺口導致鷹架覆蓋率紅」轉成事件分析硬擋（4b）。

### 4b. 保留會不會「驗了就丟」擋死？最小修法？

**會。** 具體：`close` 中段缺根 → stage2 `validate_alignment` 覆蓋率 raise，即使 `event_label_values` 在選中 timestamp 齐全且有限、覆寫後 `event_given` 本可通過。  
**最小修法（不違 §C-6）**：當 `event_label_values is not None`（將消費 event_given）時，stage0／stage2 對鷹架之 `validate_alignment` **不得作分析硬閘**（可降級診斷／省略）；硬閘只留 stage3 覆寫後 `validate_consumed_label`＋service 三元組。主線／無覆寫路徑維持 forward_return 硬閘。同步改 TODO／SPEC 敘事與 mutation。

### 5a. mutation 集合夠不夠（8 條全綠仍可能有的缺陷）？

**「事件將覆寫時 stage2 仍對鷹架硬閘」**——現有 B1/B2/B3/D1/D2/D3/A4/C0 **全綠也抓不到**（無紅錨）。見 `GROK-R3-P2-01`。

### 5b. 有無「紅的理由不對」？

本輪 gate 只匯出 `GATE PASS`（mutate stdout 進變數）；腳本錨點為字串替換＋對應 `-k` 測試，C0 註解對照為 EXPECT_GREEN。**未**實見 import／語法誤紅。開工時 C0 註解殘留暗示還原路徑曾不乾淨，但不改「紅因斷言」結論。

### 6. ≥10× 不必要複雜？owners＋by_id 可否合一？

**無 10× 架構膨脹。** `event_label_owners`（ts→id，orchestrator 綁列）與 `event_label_by_id`（id→值，service 回比）職責不同；可合成單一結構但非必要。維持兩份可接受。

### 7. 可合併進 B2 嗎？

**可以合併進 B2（Task 2.2）**，條件：把「被驗序列＝被消費序列」寫成參數化必紅／必綠，覆蓋 `event_label_values` 將覆寫之情境，迫使 D5 收斂。  
**無新 P0 必須先改碼才能開 B2**；若委員會裁定 4a「保留鷹架硬閘」→ 先改 TODO 要點 3 與 SPEC 敘事再標 CLOSED，避免文件說不驗、碼仍驗。

---

## §0 挑戰前提

| 宣稱 | 裁定 | 證據 |
|---|---|---|
| fact: 新測試 14 條 0 skip | **成立** | pytest `-rs` 14 passed |
| fact: phase gate 1 PASS／UNCOVERED=0 | **成立** | `GATE PASS: phase=1` |
| fact: 守衛未動 | **成立** | `test_guard_untouched_sha256_pinned` 在 gate 路徑內；diff 只在 `validate_alignment` **之後**新增函式 |
| fact: stage0 裁切不改 oracle 抽樣 | **成立** | probe 逐鍵相同 True |
| fact: 非事件 golden 8 檔 rc=0 | **部分推翻** | `test_ichc_p2_golden` 本機 **config_hash** 紅（frozen `c1616bdf…` vs live `9fcdd0cb…`）；A/B：identity coterminalize 同樣 config 紅、**feature_set 仍綠** ⇒ **非 B 裁切**；屬 ICConfig 預設／receipt 漂移 |
| assumed: 保留鷹架驗證不違 §C-6 | **削弱** | 見 4a；資料驅動「不驗將丟棄序列」≠ mode skip |
| assumed: 截短 label＝同尾 | **成立** | 既有測試＋本輪 A PASS |

### 被當成事實的未驗證假設（§0）

1. 「保留 stage2 鷹架驗證＝符合 §C-6」——把「禁止整段 skip」擴成「必須驗即將丟棄序列」→ **P1-01**。  
2. 「ichc_p2 golden 已綠」——本機 config_hash 紅，且與 B 無關 → 記為環境／receipt 債，非本批 P0。

---

## §1 必查 11 類（摘要）

1. **矛盾**：TODO 2.1 要點 3「覆寫前不驗」vs 碼仍 stage2 硬閘 → P1-01。  
2. **漏項**：mutation 未覆蓋「覆寫前硬閘」缺陷 → P2-01。  
3. **不可測**：本批核心 ASSERT／gate 可執行。無。  
4. **quant**：主洩漏路徑已關；殘留 producer 自洽錯值、EA-RESID-4/5。  
5. **過度工程**：無。  
6. **OOM**：本批未加阻擋閘。無。  
7. **Cache**：未碰。無。  
8. **API**：無新可偽造參數；`label_source` producer 綁定。無。  
9. **測試**：新 14 條＋mutation 8；缺 D5 錨。  
10. **Agent 可執行性**：D5 文件／碼歧義會讓 B2 實作者不知驗哪份。  
11. **短命工**：無。

---

## Findings

## GROK-R3-P1-01

**斷言**: B1 實作仍在 `_stage2_label_generation`（及 stage0 預載）對**即將被 `event_label_values` 覆寫丟棄**的鷹架跑 `validate_alignment` 硬閘，違反 TODO Task 2.1 要點 3；在 close 中段缺根／覆蓋率不足時，會在事件 label 本身合法的情況下擋死分析（「驗了就丟」殘留）。

**碼證**: TODO `:165-170`「事件模式下，覆寫前那條序列不驗」；orch `:2934-2957` stage2 裁切後仍 `validate_alignment(...)`，`:3059-3099` 才覆寫並 `validate_consumed_label`。本輪探針：中段 drop 3 根後 proper 生成 → `AlignmentViolationError: target coverage too low`；同資料若只跑 `validate_event_given` 本可對齊。B 後 proper＋excess 已不再因截短誤擋（降級理由）。RECHECK：構造 `event_label_values` 齊全＋close 中段缺根 → 現況 stage2 紅；修後應 stage2 不硬擋、stage3 event_given 綠。

**來源摘要**: docs/GAP3_EVENT_ALIGNMENT_TODO.md#e2b6c6eebb68

[MAJOR] 信心度=High。修法：見必答 4b（資料驅動：有 `event_label_values` 則鷹架不硬閘；硬閘只驗被消費序列）。若委員會裁定保留鷹架硬閘 → 必須改寫 TODO／SPEC 要點 3，並接受缺口誤擋為明示行為。**不修理由若暫掛 B2**：`user-ruling:` 待委員會對 4a 定案／或 `blocked-by: Task 2.2` 參數化收斂。

## GROK-R3-P2-01

**斷言**: phase-1 mutation 八條（B1/B2/B3/D1/D2/D3/A4/C0）全綠仍放得過「事件將覆寫卻仍對鷹架硬閘」之缺陷——集合對 D5／TODO 要點 3 無紅錨。

**碼證**: `handoffs/20260907-evtalign-mutate.py` MUTATIONS 列表無「刪除／跳過 stage2 validate 當 event 覆寫」之反向或正向錨；gate `GATE PASS: phase=1`。RECHECK：新增 mutation／測試——`event_label_values` 非空時 spy／行為斷言 stage2 不得以覆蓋率／尾端契約否決分析，否則紅。

**來源摘要**: handoffs/20260907-evtalign-mutate.py#4528ba20e650

[MINOR] 信心度=High。修法：併入 B2 Task 2.2 參數化或 phase1 增一條 mutation；與 P1-01 同閉。

---

## ASSUME 總表（本輪）

| ID | verdict | 為什麼 |
|---|---|---|
| R2 D1/D4 主洩漏已關 | **成立** | 新 API 反例 BLOCKED |
| B 無新 look-ahead 洞 | **成立** | 2a；正規化先擋非單調／重複 |
| 保留鷹架硬閘已符合 TODO/§C-6 | **不成立** | P1-01 |
| ichc_p2 紅＝B 破壞 §G-1 | **不成立** | config_hash 漂移；feature_set 綠；identity 同樣 config 紅 |
| mutation 已覆蓋 D5 | **不成立** | P2-01 |

---

STATUS: DONE
