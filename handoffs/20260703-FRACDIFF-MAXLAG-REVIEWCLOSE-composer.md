# FRACDIFF_MAXLAG B1+B2 — Review Close (Composer)

**task-id**: `fracdiff-maxlag-reviewclose-composer-20260703`  
**reviewer**: Composer 2.5（延續 `fracdiff-maxlag-review-composer-20260703`）  
**prior review**: `handoffs/20260703-FRACDIFF-MAXLAG-REVIEW-composer.md`（CHANGES_REQUIRED，3×BLOCKING）  
**method**: 親自開檔驗 receipt / reconcile / 測試碼；大 JSON 僅讀 summary 欄位

---

## BLOCKING 逐條 closure

### 3.5 — B-2 slow max_lag mutation 三測實跑 receipt

| 項 | 原缺口 | 重驗證 | 結論 |
|---|---|---|---|
| 3.5 | 三個 `test_mutation_fracdiff_maxlag_*` 僅 code review，無 slow 全鏈 receipt | `handoffs/run_receipts/20260703T094044Z-fracdiff-maxlag-convfix-slow.log` 尾段 + 行號對照 | **CLOSED** |

**碼證（094044Z，7 測全鏈 slow session）**：

| 測試 | 結果 | log 錨點 |
|---|---|---|
| `test_mutation_fracdiff_maxlag_len_coupling_truncation_fails` | **PASSED** | L3617 `[ 42%]` |
| `test_mutation_fracdiff_maxlag_len_coupling_tail_fails` | **PASSED** | L4824 `[ 57%]` |
| `test_mutation_fracdiff_maxlag_len_coupling_parallel_fails` | **PASSED** | L6134 `[ 71%]` |

session 摘要：`2 failed, 4 passed, 1 xfailed`（L16262）——失敗項為 **尾擾 MR**（當時尚未掛 xfail）與 **舊版 calibration 控制**（見 6.5/R3）；**不影響**本條所要求的 max_lag 三 mutation 穿透證明。

**補充（R3-D2 控制探針，非原 3.5 範圍但同族護網）**：`handoffs/run_receipts/20260703T132059Z-fracdiff-maxlag-d2-control-final.log` → `1 passed`（重設計後 `test_mutation_fracdiff_calibration_perturb_fails`）；測試現含 `match=r"columns gate failed \(strict\)|d_star"`（`test_ff_fullchain_truncation_mr.py:419`）。

---

### 6.5 — B-1 兩 MR slow receipt（裁決變更後）

| 項 | 原缺口 | 重驗證 | 結論 |
|---|---|---|---|
| 6.5 | xfail 已撕、要求兩 MR「2 passed」slow receipt | **依雙戳記裁決變更**：`handoffs/20260703-FRACDIFF-MAXLAG-R3-RECONCILE.md`（codex+composer APPROVED，sha256 一致）→ 兩 MR **誠實 xfail**（pre-existing storage codec），非轉綠 | **CLOSED（修訂準則）** |

**R3 收斂要點**（L8–14）：尾擾 MR reason 必須載明 storage codec / 2^-7 量化差；截斷 MR 亦歸 materialization/codec 家族；轉綠時點 = storage epic。

**測試碼 xfail reason 對照**（`test_ff_fullchain_truncation_mr.py`）：

| 測試 | 行號 | reason 關鍵字 | 與 R3 一致 |
|---|---|---|---|
| `test_fracdiff_truncation_invariant` | `:110–116` | `pre-existing materialization` / `storage codec/精度 epic` | ✓ |
| `test_fracdiff_tail_perturbation_invariant` | `:133–138` | `pre-existing storage codec` / `094044Z` / `2^-7` / `非 max_lag/conv` | ✓（逐字對齊 R3-D1） |

**receipt 對照（094044Z）**：

- `test_fracdiff_truncation_invariant` → **XFAIL**（L1211–1213），reason 與碼一致。
- `test_fracdiff_tail_perturbation_invariant` → 該 run 為 **FAILED**（L2411；codec float16 證據見 L16255–16262），**早於** R3 掛回 xfail；現碼已 strict xfail，後續 slow run 預期為 XFAIL 而非假綠。

**判定**：原 review 6.5 的「2 passed」門檻已被委員會 reconcile **明示廢止**；現準則為誠實 xfail + 根因立案。碼與裁決一致 → 本條 closure。

---

### 5.7 — G2' config 路徑交叉驗證（Task 1.2 / §G D）

| 項 | 原缺口 | 重驗證 | 結論 |
|---|---|---|---|
| 5.7 | schema 落地後 `max_lag=50` 真 config 路徑 G2' digest == G2（R） | `handoffs/run_receipts/20260703T085226Z-fracdiff-maxlag-postfix-compare.json` | **CLOSED** |

**碼證**：

- 頂層：`"passed": true`，`"failures": []`（L4–5）
- `symbols.BTCUSDT.cond3_G2P_vs_R`：`fracdiff_diff_count=0`，`non_fracdiff_diff_count=0`，`only_count=0`，`row_count_equal=true`（L89–99）
- `symbols.ETHUSDT.cond3_G2P_vs_R`：同上全 0 差異（L185–195）
- G2P / R 兩腿 `resolved_max_lag: 50`，`fracdiff_hash` 相同（`dcc154ced6b642083138ca516f09aab7`）；BTC `frame_digest_sha256` G2P==R（`d90f9ee6…`）

G2'（config pin=50）與 R 全欄位零差異 → Task 1.2 增強驗證滿足。

---

## 原 review 其餘項（狀態不變）

| ID | 級別 | close 輪結論 |
|---|---|---|
| 1.1–1.3 | PASS | 維持（helper 未弱化） |
| 2.1–2.4 | PASS | 維持 |
| 3.1–3.4 | PASS（設計） | 維持；3.5 現有 receipt 補齊 |
| 4.1–4.7, 4.9 | PASS | 維持 |
| 6.1–6.4 | PASS | 維持 |
| 6.5 | ~~BLOCKING~~ | **CLOSED**（修訂準則見上） |

---

## NON-BLOCKING 跟進（不擋 B1+B2 Gate）

| ID | 建議 |
|---|---|
| 2.5 / 2.6 | lag_processor / ADF `max_lag` 語意 out-of-scope（SPEC §A.9） |
| 3.6 | B-2 mutation 拆窄 `pytest.raises`（對齊 P0FF3） |
| 4.8 | `strong_value_fp` 與 `test_d_star_col_fingerprint.py` 分工註記 |
| 5.5 | B3 文件化 `config_hash` 因 `max_lag:0` 出現在 dump 的碎片化 |
| 5.6 | 已登記：d\* cache 走 `fracdiff_hash` 非 `config_hash` |
| 6.6 | `calibration_bars=10→max_lag=2` production 不可達（`_calibration_bars()>=500`） |
| 6.7 | Task 1.3 驗證命令改指向 `test_b6_warmup_trim.py` |
| 6.8 | 刪除 `test_fracdiff_maxlag_derivation.py` 未使用迴圈 fixture |

**營運備註**：下次全量 slow MR run 預期 `2 xfailed`（兩 invariant）+ max_lag 三 mutation `passed` + 控制探針 `passed`；勿以整包 exit 0 作為 B-1 轉綠條件。

---

## FINAL VERDICT: **APPROVED**（B1+B2 review gate）

**理由**：原三條 BLOCKING 均已用可稽核 artifact 閉合——(1) max_lag 三 mutation slow 全鏈 PASSED；(2) B-1 兩 MR 依 R3 雙戳記 reconcile 改為誠實 xfail且 reason 與碼一致；(3) G2' vs R `cond3` 雙 symbol 零差異。production resolver seam、helper 未弱化、快測/mutation 靜態護網方向維持原 review PASS 結論。

**剩餘項**：上表 NON-BLOCKING；storage codec epic 完成前兩 MR 維持 xfail；B3 golden 重生 / 文件化待後續 phase。

---

```
ASSUMPTIONS_VERIFIED: 094044Z convfix-slow log 行號對讀三 mutation PASSED；132059Z d2-control 1 passed；R3-RECONCILE 雙戳記+xfail reason 碼對讀；085226Z-postfix-compare.json cond3 全 0（未讀大 artifact 本體）
TESTS_RUN: review-only（未重跑 pytest）；證據=上述 receipt 檔
FAILURES_SEEN: none（closure 輪）；094044Z 歷史 2 fail 已納入 6.5/3.5 敘述
SCOPE_CHANGES: none（review-close only）
NUMERIC_OR_SCHEMA_IMPACT: 無新增；G2'≡R 已證零差異
```

HANDOFF_NOT_UPDATED: 執行合約 §7 — review-close 寫本檔，不重寫根 HANDOFF.md

STATUS: DONE
