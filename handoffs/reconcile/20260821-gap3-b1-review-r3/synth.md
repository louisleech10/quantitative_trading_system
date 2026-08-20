# Reconcile — 20260821-gap3-b1-review-r3

**來源** 20260821-gap3-b1-review-r3-codex.md, 20260821-gap3-b1-review-r3-composer.md, 20260821-gap3-b1-review-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；suite 100 passed）

**Verdict**: 需修補後合併——R2 三條 codex 原提出方全 CLOSED；新 1 條 P2（hash 只驗長度未驗 hex）採納修補（逐字元 hex 檢查＋非 hex／大寫反例）；R4 由 codex 重跑 probe 閉合、兩家 sentinel，全 CLOSED 後三家 RECONCILE-STAMP → 進 B2。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Z1 hash 逐字元 hex 驗證 | CODEX-R3-P2-01 | **採納**：`baseline.py` 增 `set(h) - hexdigits` 檢查；`"g"*64`／大寫 `"AB"*32` 反例入 `test_baseline_oracle.py` |
| — sentinel | COMPOSER-R3-P3-00 | 記錄：三修補落地、無 finding |
| — sentinel | GROK-R3-P3-00 | 記錄：三行為碼證皆落地、無 finding（其檔尾自附戳記不計；正式戳記蓋終輪 synth） |

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P2-01

**斷言**：`feature_manifest_hash` 的修補只驗 `str` 與長度 64，沒有驗十六進位字元；長度正確但非 hash 的 provenance 仍可產生 baseline receipt。

**碼證**：`momentum/Analysis/event_samples/baseline.py:98-100` 只有 `len(feature_manifest_hash) != 64`，未有 hex-pattern 檢查；`venv/bin/python -c 'from tests.momentum.event_samples.test_baseline_oracle import synth,OC; from momentum.Analysis.event_samples.baseline import single_feature_binary_baseline as f; X,y,p=synth(); r=f(X,y,p,oracle_config=OC,feature_manifest_hash="g"*64); print("nonhex_manifest_hash_accepted",r["receipts"]["feature_manifest_hash"]); raise SystemExit(0)'` → `nonhex_manifest_hash_accepted ggg...`，rc=0。相對地省略參數 probe → `TypeError`、rc=0（由 `pytest.raises` 捕獲）。

**來源摘要**：`momentum/Analysis/event_samples/baseline.py#026cc7bca318`

P2；信心度=10/10；採納處置明列 `feature_manifest_hash` 為 64-hex 且格式錯須 fail-closed，但目前只保證長度，會讓 malformed provenance 進入 receipt。修法：以既定 sha256 hex 契約做完整 `[0-9a-f]{64}` 驗證，並補 64 字元非 hex 的回歸負例；不改本輪產品碼。
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；R2 三條修補（uint64 差分 int64 化、有限值閘前移、feature_manifest_hash 必填）未引入新的 alignment/baseline 可證偽缺陷——合法 uint64 ms 與 int64 等價放行、超 int64 max 拒、降序拒；hash 必填僅觸及已更新的測試呼叫端，省略即 TypeError/ValueError fail-closed。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed rc=0；`PYTHONPATH=. venv/bin/python /tmp/composer_r3_sentinel.py` → 六探針全符合預期；`momentum/Analysis/event_samples/alignment.py:45-47,54` uint64 超界拒＋`astype(int64)` 再差分；`baseline.py:98-100,108-112` hash 64-hex 必填＋one-class 前 finite gate；`rg -l single_feature_binary_baseline momentum/ tests/ api/` → 僅 baseline 定義＋兩測試檔（均已傳 hash）；`git diff e0cecf7c..HEAD -- momentum/ tests/` 含三反例回歸。

**來源摘要**: momentum/Analysis/event_samples/alignment.py#0a7cf0773cc4; momentum/Analysis/event_samples/baseline.py#5ebe4e2fe875; tests/momentum/event_samples/test_alignment.py#acf9b8f1b45a; tests/momentum/event_samples/test_baseline_oracle.py#de818fd70529; handoffs/reconcile/20260821-gap3-b1-review-r2/synth.md

---

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——R2 三條寫回落地且未引入新矛盾；合法 uint64→int64 行為不變／超界拒；hash 必填未破壞既有呼叫端。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed rc=0；`git diff e0cecf7c..HEAD --stat -- momentum/ tests/` → 5 files +56/-24；uint64 probe A升序/`''`、B降序/`unsorted_bar`、C超界/`invalid_timestamp_unit`、D int64/`''`、E parity True；baseline omit→TypeError、None→ValueError、one-class+NaN→loud「非有限值」；呼叫端僅兩測試檔且皆已傳 hash。

**來源摘要**: handoffs/reconcile/20260821-gap3-b1-review-r2/synth.md#42996e573afa；momentum/Analysis/event_samples/alignment.py#0a7cf0773cc4；momentum/Analysis/event_samples/baseline.py#5ebe4e2fe875；tests/momentum/event_samples/test_alignment.py#acf9b8f1b45a；tests/momentum/event_samples/test_baseline_oracle.py#de818fd70529；handoffs/20260821-gap3-b1-review-r3-brief.md#fca26740b988

正文：sentinel 義務（hash 呼叫端／uint64 轉型）與 brief assumed 攻擊完成；adversarial 候選「非 hex 64 字元仍接受」低於可證偽 P0–P2 門檻（見上殘餘觀察）。禁捏造湊數。

