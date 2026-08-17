# GAP-1 TODO R2 受限複驗 R9 — COMPOSER

**task-id**: `20260817-GAP1-X-REVIEW-R9` | **family**: composer | **brief**: `handoffs/20260817-gap1-todoadv-r9-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md` @ `e6d673841704`；`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md` @ `44556a29f5c1`；母 SPEC @ `502c93cae402`；收斂 `handoffs/reconcile/20260817-gap1-x-review-r8/synth.md` @ `32271ad1ccab`

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS` rc=0
- `venv/bin/python handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.py` → 與主委 receipt 一致（見段 B）
- `venv/bin/python /tmp/workdir/composer-r9-b-probe.py` → J1 五項全 PASS（見段 B）
- `venv/bin/python handoffs/run_receipts/20260817T150000Z-gap1-minbtl-conservatism-probe.py` → mean=0.843077 rc=0
- `venv/bin/python /tmp/workdir/composer-r9-ast-probe.py` → 五種 AST 繞道皆 rc=1（fail-closed，見段 C-1）

---

## Verdict：可 Frozen

R8 本家族三條處置於 TODO R2＋延伸檔 A1 均已落地且可機械驗收；J1 三條數值 golden 本輪獨立實跑可重現；新增機制（AST wiring／`universe_scope`／例外分類／`n_rows_rejected`／B4 拓撲）經攻擊面逐項核對後**未發現可執行假綠或會使 B1–B4 數值錯誤之缺口**。母 SPEC §R:653–654 與 A1-11 之 B4→B3 依賴仍漂移（段 C-5），屬文件殘差、不阻 Frozen；建議延伸檔補一條 §R 修訂或 ROADMAP 小票。

---

## 段 A — 本家族 R8 closure（COMPOSER 三條）

| ID | R8 主張（摘要） | 處置錨點 | 複驗 | 殘留帶入 TODO |
|---|---|---|---|---|
| COMPOSER-R8-P1-01 | `for_study_trial` 缺 `t_years`／`target_sharpe`／`provenance` 來源 | A1-8 §1–2；TODO Task 3.4 步驟 1（optional 三參＋任一 `None` 走誠實 `n_unknown`） | **CLOSED** — 簽名與 None-guard 逐字對齊；`assess_eligibility` 僅在三參齊備時呼叫 | no |
| COMPOSER-R8-P1-02 | API `strategy_validation` 與 SPEC 三鍵子集漂移 | A1-8 §3；TODO Task 3.4 步驟 4「只投影三鍵」＋驗收⑥ | **CLOSED** — 鍵集合 `{"eligibility","display_downgrade","warning_text_key"}` 具名斷言 | no |
| COMPOSER-R8-P2-01 | Task 2.4 W1 字面 `re.search` 可假綠 | A1-11 §4–5；TODO Task 2.4 全面 AST（W1/W4 組裝鍵、W3 三形、非 `Constant`→`[unresolved]` rc=1） | **CLOSED** — regex 已移除；五條 mutation＋誠實邊界具名 | no |

另兩家 R8 ID 本輪未逐條重評；抽樣對照收斂檔 J2–J6 與 TODO 追溯表（§R2 自檢清單）一致，無異議。

---

## 段 B — J1 數值可重現性（實跑）

| # | 斷言（A1／brief） | 本輪實跑值 | PASS |
|---|---|---|---|
| B-1 | `alpha_detectable`：`mu=0.01*0.15`，`default_rng(20260817)`，`M=standard_normal((1200,50))*0.01`，`S=12` ⇒ `pbo<0.30` | **0.0000** | ✓ |
| B-2 | 全噪音同生成式 ⇒ `pbo∈[0.30,0.70]`；band 放寬理由（924 path 相關） | **0.6483**（canonical 生成式）；三變體 0.6483／0.6158／0.5357 與 receipt 一致 | ✓ |
| B-3 | `alpha_undetectable`：`mu=0.01*1.0/sqrt(8760)` ⇒ `pbo>0.40` | **0.5411** | ✓ |
| B-4 | §V-4 新 mutation（champion 改 OOS 選）⇒ noise 或 alpha_detectable 至少一條轉紅 | noise 0.6483→**0.0000**（轉紅）；alpha_detectable 0.0000→0.0000（不轉紅，但「至少一條」已滿足） | ✓ |
| B-5 | Task 3.1 驗收⑨：`mean(max ann SR)<=1.0` 且與 `0.833943` 之 `rtol<0.05` | mean=**0.843077**，rtol=**0.010953**；per-seed max=1.216377（未斷言，與 A1-9 一致） | ✓ |

**band 放寬評估**：`[0.30,0.70]` 對 canonical 生成式足夠；三 RNG 變體極差 0.113 仍支持「path 高度相關」理由。多 seed 平均可作未來收緊研究，非本輪阻擋項。

---

## 段 C — 新增機制攻擊面（五項結論）

### C-1 AST wiring（A1-11／Task 2.4）

**結論：無可執行假綠路徑；實作風險為 fail-closed 過嚴（非假綠）。**

依 TODO W1 語意實作探針（`/tmp/workdir/composer-r9-ast-probe.py`）：`return dict(...)`、同檔 helper `return _sections()`、迴圈 `out[name]=`、`**dict` 展開 — assembled 鍵集合皆不完整 ⇒ **rc=1**。非 `Constant` 動態 reason 亦已具名 rc=1。誠實邊界（跨檔常數／f-string）同樣 fail-closed。建議實作端採 `return {字面 Constant 鍵}` 或 body 內 `out["節名"]=…` 模式。

### C-2 `universe_scope`（A1-4）

**結論：可觀測＋強制降級足夠誠實；API 路徑無法只讀 `pbo.value` 繞過。**

Task 3.4 只投影三鍵，不含 `pbo`；`build_validation_section` 於 `universe_scope=="ledger_recorded_only"` 機械 `display_downgrade=True`（TODO 3.3 步驟 3）。直接 import `PBOResult.value` 屬繞過展示契約，已由 G1-R9 具名殘留；不使 PBO 永不可用（範圍 A 成立）。

### C-3 例外分類（A1-8）

**結論：集合恰當；`ValueError` 吞參數 bug 之風險已被 None-guard 大幅緩解。**

今日 route 三 optional 皆 `None` ⇒ 不呼叫 `assess_eligibility`，不會觸發其 `ValueError`。未來 G1-R1 齊參後，錯誤 `t_years` 等仍可能變 `reporter_failed` 而非 5xx — 屬明知取捨（與 codex P1-05 收斂一致）；`TypeError` 等仍上拋（驗收⑤）。不需收窄集合即可 Frozen；若未來要區分「呼叫方參數錯」可另票自訂 `ParamValidationError`。

### C-4 `n_rows_rejected`（A1-7）

**結論：六欄自洽；與 `n_is_lower_bound` 恆真無語意衝突；conformance 可證偽。**

`n_candidates_considered` 只計 schema-valid 唯一候選；schema-invalid 進 `n_rows_rejected` 不進 `n_evaluated`（TODO 2.2 步驟 2／5）。`n_is_lower_bound` 表 N 下界語意，與 rejected 計數正交。Task 2.3 驗收②b／mutation §V-7 可證偽不變式。

### C-5 Task 2.4 移至 B4 末（A1-11）與 §R

**結論：§R「B3／B4 可獨立 revert」對 B3→B4 方向已弱化；B4 單獨 revert 仍可行。**

A1-11 使 B4 依賴 B3 Task 3.3（`report.py`）；revert B3 會使 B4 末 2.4 wiring rc=2。母 SPEC §R:653–654 未在延伸檔修訂。**處置建議**：延伸檔增 A1-16 改 §R 為「B4 依賴 B3 3.3；revert B3 須連帶 revert B4 或接受 wiring 紅」— 文件殘差，不阻 B1 開工。

---

## Findings

## COMPOSER-R9-P3-00

**斷言**: 本輪對 R8 本家族三條 closure、J1 五項數值 oracle、段 C 五類新增機制攻擊面逐項核對後，無達 BLOCKING／MAJOR 門檻之可證偽缺陷。

**碼證**: 段 A 表三 ID 皆 CLOSED；段 B 表五項實跑 PASS（命令見檔首 VERIFY）；段 C-1 `composer-r9-ast-probe.py` 五模式皆 rc=1；段 C-2–5 對照 `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md` A1-4／A1-7／A1-8／A1-11 與 TODO Task 2.2–3.4／2.4。RECHECK：`venv/bin/python /tmp/workdir/composer-r9-b-probe.py`；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-todoadv-r9-composer.md --family composer`。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-review-r8/synth.md#32271ad1ccab

[NON-BLOCKING] 信心度=High。§R 漂移（C-5）與 `ValueError` 邊界（C-3）已記於段 C 結論，不構成新 finding；勿為湊數捏造實質缺陷。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 |
|---|---|
| brief `assumed: 22 條處置皆真關閉` | **本家族三條成立**；他族未全量重跑反例 |
| brief `assumed: J1 golden 可重現` | **成立**（段 B 五項實跑） |
| brief `assumed: 新增機制未引入假綠` | **成立**（段 C；AST 為 fail-closed 非假綠） |
| A1-2 band 放寬「924 path 高度相關」 | **fact-verified**（三變體極差 0.113） |

---

ASSUMPTIONS_VERIFIED: template_check PASS；J1 五項＋MinBTL probe 實跑；AST 五模式探針；sha256 前 12 對前三檔＋synth
TESTS_RUN: 見檔首 VERIFY；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-todoadv-r9-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0（1 canonical ID）
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查＋/tmp 探針）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 TODO/SPEC/延伸檔）
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-todoadv-r9-composer.md`
TMP_CLEANUP: 收尾刪 `/tmp/workdir/*`；保留 `/tmp/claude-501`
STATUS: DONE
