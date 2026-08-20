# Reconcile — 20260821-gap3-b1-review-r2

**來源** 20260821-gap3-b1-review-r2-codex.md, 20260821-gap3-b1-review-r2-composer.md, 20260821-gap3-b1-review-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；寫回 commit 見 git log「R2 codex 三條全修」，suite 100 passed）

**Verdict**: 需修補後合併——R1 閉合：composer 1/1 CLOSED、codex 7 條中 4 CLOSED、3 條「修未修淨」再列為 R2 新 finding，全部採納修補；R3 由 codex 重跑三 probe 閉合、兩家 sentinel；全 CLOSED 後三家 RECONCILE-STAMP → 進 B2。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| Y1 uint64 差分下溢 | CODEX-R2-P1-01 | **採納**：`_validate_bar_table` 時間戳一律 `astype(int64)` 再差分（unsigned 超 int64 max ⇒ `invalid_timestamp_unit`）；uint64 降序反例入 `test_alignment.py` |
| Y2 有限值閘位置 | CODEX-R2-P2-01 | **採納**：閘前移至 one-class 分支之前；one-class＋NaN 反例入測試（loud 非 unavailable） |
| Y3 hash 可省略 | CODEX-R2-P2-02 | **採納**：`feature_manifest_hash` 改必填 64-hex、缺／格式錯 fail-closed；全部呼叫端更新；反例入測試 |
| — sentinel | COMPOSER-R2-P3-00 | 記錄：COMPOSER-R1-P1-01 CLOSED（夾心反例通過）；union-find 順掃無新 finding |
| — sentinel | GROK-R2-P3-00 | 記錄：無新 finding；其 R1「相鄰鏈對等價」判斷已明文覆核撤回 |

X1 gap 語意（事件 i 自身窗 duration 對所有 j>i）與 X6 較嚴處置經 codex probe 確認無矛盾。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**：R1 P1-04 的 close-time ordering guard 對 `uint64` timestamp 仍可繞過；`np.diff(uint64)` 下降時下溢，PIT 可能在未排序 bars 上繼續。
**碼證**：`alignment.py:42-50` 接受 dtype kind `u` 且直接做 `np.diff`; `venv/bin/python -c 'import numpy as np,pandas as pd;from momentum.Analysis.event_samples.alignment import _validate_bar_table as v;t=np.uint64(1704067200000);b=pd.DataFrame({"open_time_ms":np.array([t+86400000,t],dtype=np.uint64),"close_time_ms":np.array([t+172800000,t+86400000],dtype=np.uint64),"open":[1.,1.],"close":[1.1,1.1]});print("uint64_descending_validator_result",repr(v(b)))'` → `''`，rc=0。
**來源摘要**：`momentum/Analysis/event_samples/alignment.py:42-50`#0e7591c6b591；嚴重度=P1；修補=先轉有號/安全差分或拒 unsigned timestamp，再驗排序。

## CODEX-R2-P2-01
**斷言**：R1 P1-06 修補只在 test labels ≥2 類時檢查非有限值；one-class branch 先於 finite gate return，NaN 可被誤報為 `one_class_test_segment`。
**碼證**：`baseline.py:114-123`; `venv/bin/python -c 'import numpy as np;from tests.momentum.event_samples.test_baseline_oracle import synth,OC;from momentum.Analysis.event_samples.baseline import single_feature_binary_baseline as f;X,y,p=synth();X.iloc[120,0]=np.nan;y.iloc[120:]=1;r=f(X,y,p,oracle_config=OC);print("one_class_nonfinite_result",r["capability_status"],r["reason"],"raises",False)'` → `unavailable one_class_test_segment raises False`；混合類 targeted test 2 passed，不覆蓋此分支。
**來源摘要**：`momentum/Analysis/event_samples/baseline.py:114-123`#63e6be0a20ec；嚴重度=P2；修補=將 finite gate 前移，或在 unavailable receipt 明列 nonfinite failure。
## CODEX-R2-P2-02
**斷言**：R1 P2-07 仍可省略 provenance；`feature_manifest_hash` 是 Optional，呼叫者不傳時 baseline 正常產報且 receipt hash 為 `None`。
**碼證**：`baseline.py:88,109-112`; `venv/bin/python -c 'from tests.momentum.event_samples.test_baseline_oracle import synth,OC;from momentum.Analysis.event_samples.baseline import single_feature_binary_baseline as f;X,y,p=synth();print("omitted_manifest_hash_receipt",repr(f(X,y,p,oracle_config=OC)["receipts"]["feature_manifest_hash"]))'` → `None`，rc=0；僅提供 hash 的 regression test 2 selected passed。
**來源摘要**：`momentum/Analysis/event_samples/baseline.py:88-112`#63e6be0a20ec；嚴重度=P2；修補=要求非空 hash 或 typed materialization result，缺 hash fail-closed。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF/CLAUDE/brief/SPEC/TODO/D-001；X1 gap probe、R2 seam/反例 probes 與 code line 對證完成；truncated_mode 壞 row_id 被接受但仍以 timestamp `ms[pos]==target` 定位，符合 D-001 明示語意，非 finding。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed in 11.15s；mutation M1/M2/M3/M5/M8/M9/M10/M12 → 8 passed；dedupe/alignment/import/row_id/baseline targeted → 2+1+5+1+2 passed；`bash scripts/completeness_check.sh --single handoffs/20260821-gap3-b1-review-r2-codex.md --family codex` → rc=0（scratchpad 執行；直接入口先被 debt gate 擋）。
FAILURES_SEEN: uint64 ordering、one-class nonfinite、omitted hash probes 分別產生上述 findings；未改碼、未修改 SPEC/TODO；data_cache 僅作真實 kline/FF 輸入，未納入交件，未 commit。
SCOPE_CHANGES: review-only；HANDOFF_OUTPUT: `handoffs/20260821-gap3-b1-review-r2-codex.md`；NUMERIC_OR_SCHEMA_IMPACT: 未改產品輸出，報告指出 PIT guard、nonfinite gate、provenance receipt 風險。
STATUS: DONE
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；COMPOSER-R1-P1-01 原 A/C/B 夾心 RECHECK 與 union-find 順掃（O(n²)、決定性編號、per-event-i gap 語意）均已 CLOSED，修補 diff 未引入新的 dedupe／manifest 可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q` → 8 passed rc=0；`PYTHONPATH=. venv/bin/python /tmp/composer_r2_recheck.py` → A/C/B 同簇 c0/1、a/b/c 同簇 c0/1；gap 探針 150>100→2 簇、800<=1000→1 簇；`momentum/Analysis/event_samples/dedupe.py:51-84` union-find＋`root_order`；`git diff df45bc82..e0cecf7c -- dedupe.py test_dedupe.py` 含兩家反例測試。

**來源摘要**: momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0; tests/momentum/event_samples/test_dedupe.py#3290a1d85bf2; docs/GAP3_EVENT_TODO.md#df04bdabf37d

---

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——R1 八條修補落地且未引入新矛盾；R1「相鄰鏈對等價」已撤回；X1／X6 兩條 assumed 攻擊不成立。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed rc=0；`git diff df45bc82..e0cecf7c --stat -- momentum/ tests/` → 13 files +254/-62；舊鏈模擬 composer 反例 A/C/B → B 入 c1，新 UF＋`test_dedupe` 兩反例 → 全 c0；X1 gap 探針 touch 同簇／短早遠晚異簇；X6 單 cell NaN/inf → ValueError；mutation 四 seam 皆 monkeypatch 生產路徑；truncate_mode 仍強制 ms[pos]==target。

**來源摘要**: handoffs/reconcile/20260821-gap3-b1-review-r1/synth.md#d680f3943116；handoffs/20260821-gap3-b1-review-r1-grok.md#60f4db270029；momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0；momentum/Analysis/event_samples/baseline.py#e13696f0eb59；tests/momentum/event_samples/test_dedupe.py#3290a1d85bf2；docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：adversarial 候選（gap 不對稱／TODO「全 NaN」字面／truncate_mode 繞過 row_id）逐項核對後不達可證偽 P0–P2 門檻或落在不受理之 SPEC/TODO 重審。禁捏造湊數。

