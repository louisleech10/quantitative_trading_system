# fracdiff max_lag 三方值守恆簽核 — Composer 腿（獨立審查）

> 2026-07-03 | task-id: fracdiff-maxlag-signoff-composer3-20260703 | read-only audit + this file
> 未讀 `*-golden-{G1,G2}.json` 大檔（OOM 風險）；僅 SUMMARY / postfix JSON / log tail / mutation receipt / 源碼

## 結論

**PASS（限縮範圍：SPEC §G run contract 下，BTC+ETH×1h、MR 同款 config 窗 2081；canonical raw digest 意義上的 feature values / dtype / index / per-column NaN mask 值守恆；不含整包 artifact byte-identical、不含 10×3 TF IC 定版重生成）。**

## §1 我親自核對的 receipt（獨立於 Claude/Codex 腿）

| 來源 | 核對結果 |
|------|----------|
| `G1-SUMMARY.json` | G1 run1/run2 `frame_digest_sha256` BTC=`ae9f16c…`、ETH=`7ea5e0b6…` 兩跑相同；`stability_precheck.passed=true`；`resolved_max_lag=208`；`fracdiff_hash=84c11cce…` |
| `G2-SUMMARY.json` | G2 `resolved_max_lag=50`；`fracdiff_hash=dcc154ce…`；BTC frame=`d90f9ee6…`、ETH=`ec266a81…`；`pin_method=preprocessor_instance_fracdiff_config_injection` |
| `085226Z-postfix-compare.json` | `passed=true, failures=[]`；cond1 R vs G2 全欄 0 diff；cond2 R vs G1 非 fracdiff 0 diff、fracdiff BTC=4546/ETH=3435；cond3 G2P vs R 全欄 0 diff；R/G2P `resolved_max_lag=50` |
| `094044Z-convfix-slow.log` tail | `2 failed, 4 passed, 1 xfailed`；xfail=截斷 MR（codec）；FAILED 尾擾=float16 2^-7 量化差；FAILED 舊版 calibration 控制 `DID NOT RAISE`（後由 132059Z 取代） |
| `132059Z-d2-control-final.log` tail | `1 passed in 1061.68s`（`test_mutation_fracdiff_calibration_perturb_fails` 單測） |
| `053419Z-mutation-test_dstar_cache_key_mutation.json` | `exit_code=0`；7 passed；含 max_lag / calibration_bars / row_count / time_range / symbol-timeframe / fingerprint 變異 |

**獨立交叉驗證（python，未載大 golden JSON）：** postfix R/G2P `frame_digest_sha256` 與 G2-SUMMARY `runs_summary` 逐 symbol 完全一致；cond 計數與兩腿引述一致。

## §2 方法論獵漏

### Digest oracle（`ff_maxlag_golden_helpers.py`）— PASS

- `canonical_column_digests`：逐欄 `value_sha256`（全列 bytes，float 正規化至 `<f8`）+ `nan_mask_sha256`（全列 packbits），**無抽樣**。
- `canonical_raw_dir_digests`：逐 parquet 串流、拒絕重複欄名、彙總 `schema_hash`（欄序+dtype）。
- `digest_frame_sha256` 含 `schema_hash`，故 receipt 層 `frame_digest_sha256` R==G2==G2P 可間接封住欄序缺口。

### Compare script 弱點 — PASS with note（與 Codex 一致）

- `_digest_columns_equal` 不直接比 `schema_hash`；但 postfix receipt 已載相等 `frame_digest_sha256`，且 cond1/3 為 **225784/224625 欄全 0 diff**（含 dtype），實際閉環。

### 兩腿推理漏洞複查

| 點 | Claude | Codex 註記 | Composer 判定 |
|----|--------|------------|---------------|
| cache hit/miss 當 freshness 證據 | §1 提及 hit/miss | 過度解讀；應靠空目錄+唯一路徑 | **同意 Codex**；SUMMARY 皆 `hits=1,misses=0` 只證 in-run 重用，不否定隔離 |
| 整包 artifact 等價 | §4 已限縮 §G | manifest/config_hash 可不同 | **同意**；不得簽 whole-dir byte-identical |
| G2 stability_precheck | 未單獨提及 | 未提及 | **新發現（非阻擋）**：G2-SUMMARY `stability_precheck` 誤載 G1 digest（`ae9f16c…`），但 `runs_summary[0]` 與 postfix 一致；屬 summary 生成 hygiene，不推翻 §G |
| 094044Z「mutation 全過」 | §1 稱 3 探針 PASSED | tail 失敗在 storage 層 | **部分同意**：tail 為 codec FAILED（現已 xfail）；calibration 舊版 FAILED，**已由 132059Z 補齊** |
| D2 控制路徑 | §5 引用 132059Z | R3+D2MATCH 放寬至 columns gate \| d_star | **同意**；132059Z 單測綠燈滿足 R3 D2 驗收前提 |

## §3 pre-existing 聲明 vs R3-RECONCILE — PASS

Claude §3 與 `20260703-FRACDIFF-MAXLAG-R3-RECONCILE.md` D3 四項對照：

1. **B1 + 尾擾 codec 家族**：已載明 pre-existing、per-column float16/32 全窗值域選型、storage epic 立案 — 與 D4 一致。
2. **MRFAIL 預測更正**：已載「conv 修後尾擾 MR 轉綠」被 094044Z 推翻 — 與 reconcile §5 一致。
3. **max_lag 殘留護網**：d\* gate + 3 mutation + full_fit + D2 控制（132059Z）— 與 D3③ 一致。
4. **雙戳記**：reconcile 檔 `codex APPROVED` + `composer APPROVED` 同 sha `8b0260a9…` — 存在且可讀。

### xfail reason 誠實性（`test_ff_fullchain_truncation_mr.py`）— PASS

- `test_fracdiff_truncation_invariant`：明確 B1 / materialization 精度 / 非 max_lag / MRFAIL idx508 / storage epic — **符合 R3，非假綠**。
- `test_fracdiff_tail_perturbation_invariant`：逐字符合 R3 D1(a) 模板（真實護面暫停、094044Z 2^-7、非 max_lag/conv）— **誠實**。
- 094044Z 執行時尾擾尚為裸 FAILED（xfail 後續掛上）；現況與 R3 裁決一致，不構成值守恆阻擋。

## §4 反例嘗試（本腿）

- **雙 symbol**：BTC/ETH cond1/3 皆 0 diff，非單標的巧合。
- **窗寬陽性對照**：cond2 fracdiff 4546/3435 欄差異 + 非 fracdiff 0 — oracle 對 max_lag 敏感。
- **G2 pin 鏈**：instance injection（G2）與真 config path（G2P）皆與 R 全欄相等。
- **metadata 反例**：未重跑 SHA，但 Codex 已證 manifest/config_hash 可異；本簽核範圍不含 artifact 表面 byte 恆等 — 不阻擋 PASS。
- **G2 stability_precheck 複製貼上**：見 §2；不影響 §G 數值鏈。

## §5 簽核範圍聲明（使用者可見）

- **已證**：修後 auto `max_lag=50` 與修前 pin50 全欄 digest 等價（cond1）；真 config pin 路徑等價（cond3）；非 fracdiff 欄相對 G1 不變（cond2）；d\* cache key mutation 7/7；D2 負向控制（132059Z）。
- **未證 / 另案**：storage codec 致兩 MR xfail；10 symbols×3 TF；整包 HDF5/parquet 目錄 byte-identical；`feature_manifest.json` 跨 run SHA 恆等。
- **殘留風險（披露）**：compare helper 未顯式斷言 `schema_hash`，靠 frame digest + 全欄 dtype 閉環；G2-SUMMARY stability 欄位應修正以免誤導後續審計。

---

ASSUMPTIONS_VERIFIED: G1/G2-SUMMARY、085226Z postfix JSON、094044Z/132059Z log tail、053419Z mutation JSON 已讀；ff_maxlag_golden_helpers + compare postfix `_digest_columns_equal` + xfail decorators + R3-RECONCILE 戳記已讀；frame digest 交叉用 python 驗證；未讀 397MB/199MB 大 golden JSON。
TESTS_RUN: 無新 pytest；read-only receipt/source audit。
FAILURES_SEEN: 094044Z 歷史 2 failed（尾擾 codec、舊 D2）— 已由 xfail + 132059Z 處置；本審計無新失敗。
SCOPE_CHANGES: none；僅寫本 handoff。
NUMERIC_OR_SCHEMA_IMPACT: none from this audit。

STATUS: DONE
