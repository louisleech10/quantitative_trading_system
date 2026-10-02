# FFSTAT B6 review R1 — codex

task-id: 20260926-FFSTAT-B6-REVIEW-R1
brief-kind: review
round-id: 3e0620b0-1bb6-40a6-986c-cfcb1d3e0303

審查範圍：SPEC v59 Task 4.2、manifest、兩新測試檔、helpers 新增設定、可行性探針與兩份收據、RM-FULLSCALE ④⑤、consult-r4 較嚴版。結論：三條 P1，設計方向可用，但現行控制測試不足以證具名缺陷集合鑑別力，尚不適合投入整套約 6.5 小時驗收。

本輪唯讀；實跑於 `/tmp/ff-review-6Kq7nt` 複本，先 `isolate()`、`isolate_dstar_cache()`；真實 HDF5 僅以 `h5py.File(..., 'r')` 讀取。沒有生成型 node、沒有合成特徵 fixture、沒有生產碼／SPEC／manifest 修改。秒級控制流程探針替換 builder，用於證明例外處理行為，不作生成正確性證據。

## CODEX-R1-P1-01

**斷言**: 縮小版三個 fracdiff 長度耦合控制仍沿用飽和的 `min(len(df)//10,252)`，在實際 full／trunc 窗長下兩邊皆為 252；即使控制測試綠，也不能證明抓到長度耦合，尤其兩個正常 fracdiff 基線仍預登記 codec xfail。

**碼證**: `test_ff_fullchain_truncation_small_mr.py:77-96` 直接委派既有基線／控制；既有 `test_ff_fullchain_truncation_mr.py:173-193,210-232,249-292` 注入 capped resolver，僅檢查 `lengths_seen`／parallel 呼叫與任意 AssertionError。`ff_truncation_mr_helpers.py:158-160` 由必要 warmup 算窗。複本命令 `PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe.py` rc=0：`fracdiff=3342`，trunc=3332，`mutant_maxlags=[252,252]`；去 cap 的算術可行性探針得到 `[334,333]`，不是生成通過聲明。
CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:87
MUTATION: 複本內把委派控制之 resolver 換成 `lambda: 252`（與 full/trunc 現有 capped resolver 同值）；原 `lengths_seen`／parallel_calls 仍可滿足，原 codec AssertionError 仍被當作抓到，沒有參數差異守衛。

**來源摘要**: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#a8a8e2e7cc1e4

**類別**: code-contract

影響：正常 resolver 依 N=500 得 50；兩邊同改 252 可以改變算子，卻不構成這一對輸入的「依總長度改參數」反例。strict codec xfail 的同設定基線不能滿足 SPEC「正常基線綠」；任意 fracdiff AssertionError 不足以區分 codec 既有失敗與 mutant 引入的洩漏。本輪未跑 fracdiff 生成，因此不聲稱這三項實際已假綠或存活；已驗的是其前提退化与現行斷言不能排除假綠。

修法：只在新縮小入口調整此控制的長度耦合注入，使真實 full／trunc 解析出的 max-lag 不同，並記錄實際傳入 serial／parallel 的值；保留必要窗，不為避 cap 縮掉 warmup。例：去掉該 mutant 的 252 cap，在本例得到 334／333，仍小於 500 校準根数，參數計算本身可行；是否造成可辨識的數值差異仍須正常與 mutant 生成實證。控制驗收還需與同設定正常 fracdiff 基線區分 codec 既有失敗；若該基線仍 xfail，不能直接把同一 codec 失敗作 mutant 成功收據。這需要調整新入口及 Task 4.2 的「原控制照搬」限制，不改舊 gate／容差／舊兩檔，不新增機制或慢閘。可行性依據：秒級 resolver 探針與既有 serial／parallel `max_lag` 顯式參數（preprocessor:3464-3466,3555-3560,3701-3742）；完整行為修復未驗證。

## CODEX-R1-P1-02

**斷言**: 縮小版「calibration perturb」控制沿用舊公開域前 500 根擾動，沒有改到 FFSTAT 現行起始日前校準資料；因此其 columns／d-star 失敗不能按測試名稱解讀成校準擾動鑑別力。

**碼證**: 新檔:111-112 委派既有 `test_mutation_fracdiff_calibration_perturb_fails`；舊檔:399-430 用 `_patch_kline_calibration_ohlcv(window_bars=3342, calibration_bars=500)`。helpers:1434-1447 的範圍是 `len(df)-window_bars` 起的 500 列；factory:2408-2420 在全量 fetch 後只取 `index < output_start` 作校準，preprocessor:576-582 只讀封包。複本命令 `PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python evidence.py` rc=0，真實 BTCUSDT/1h 20352 列，output_start=`2025-12-09 18:00:00`，`changed_before_start=0`、`changed_at_or_after_start=500`。
CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:111
MUTATION: 以現行真實 K 線呼叫 `_patch_kline_calibration_ohlcv(raw, window_bars=3342, calibration_bars=500, delta=PERTURB_DELTA)`，再對 `timestamp < output_start` 比對 close；校準域零列改變，而原控制仍要求 columns 或 d_star 失敗。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#b0f5f222bd03

**類別**: code-contract

校準域採用的 adapter fetch 與公開域同為完整原始資料（adapter_registry:40-64），其後才按起始日裁切。這個控制所改的是公開域起點後的資料，且全鏈 warmup 已達數千根；它不再是舊合約中的 calibration 窗。`_calibration_series` spy 次數大於零只證校準值有被取用，不證校準值有被擾動。若因欄集合、公開值、codec 而失敗，不能據此聲稱 d-star 校準負控制已實現。

修法：新入口的負控制改為針對 full 側 `output_start` 之前真實列擾動，保留 trunc 側原始資料；具體時間選取由真實 timestamp 与校準封包的 first／last calibration timestamp 決定，收據記錄封包值／指紋確有變化與失敗 gate。不是改 `calibration_bars` 或容差。可行性證據：同 `evidence.py` rc=0，該起點前確有 500 真實列，舊 patch 在這些列完全未改；factory 的 `_load_calibration_klines`／既有 full-only fetch seam 可直接承接按時間的 patch。考慮深指標時可依封包時間擴大擾動區間，不能假設最後 500 原始根覆蓋所有欄的 500 有效校準值。校準／生成結果尚未實跑。

## CODEX-R1-P1-03

**斷言**: 新分母尺度控制把 `_build_truncation_pair` 放在 `raises(AssertionError)` 內，且 seam 次數僅要求大於零；生成準備／層覆蓋錯誤可以令控制通過，違反 Task 4.2「準備錯誤不算抓到」。

**碼證**: 新檔:132-141 將 builder 与 invariant 一起捕獲；helpers:666-704 的缺 L4／抽樣設計錯誤本身就是 AssertionError。複本 `evidence.py` rc=0：builder 先以真實 volume 呼叫被注入的尺度 seam，再拋 `AssertionError('mutation layer coverage failed (sampling design error): missing L4')`；`test_small_mutation_denominator_scale_full_column_fails` 正常返回，invariant 從未執行。探針不是生成型 node。
CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:133
MUTATION: 複本把新模組 `_build_truncation_pair` 換成 `broken_preparation`（附錄原碼）：先呼叫 `numeric_guards.causal_denominator_scale(real_volume)`，再拋缺 L4 AssertionError；直接呼叫新控制函式會正常返回。

**來源摘要**: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#a8a8e2e7cc1e4

**類別**: code-contract

同設定正常基線先跑也無法排除 mutant 自身造成準備／覆蓋失敗；欄層存在的靜態設定，更不等於 mutant run 的實際 survivor／sample 集合有效。舊 L3／winsor／L4 控制也有相同的寬捕獲，直接委派使新入口承接此風險；本 finding 以新增分母控制為最小可重現例。

修法：新入口先在捕獲區外完成 pair 生成與必要列／層／抽樣／seam 證據確認，捕獲區只包預期因果 values／NaN-mask／columns 等 gate 的失敗；錯誤文字與失敗欄／位置進收據，以排除 preparation/coverage guard。各控制有不同合法失敗種類，判別不必新增共用控制層，也不能放寬原 gate。可行性證據：同秒級反例把 builder 移出 `raises` 後，缺 L4 錯誤直接傳出（`FIX_FEASIBILITY` 輸出），不再假綠；`_build_column_frame_map`／`_build_sampled_columns`／`_assert_mutation_layer_coverage` 已存在且可在預期失敗前呼叫。舊委派 body 若不允許修改，新入口可只承接其 mutant seam 與 gate，將錯誤邊界調整明列於 Task 4.2，維持 gate 與容差不變。

## 必答 1a／1b — 收案前置與 r4 設計逐項對照

**(1a)** 方向足以作為本機補驗方案；現行測試本體尚不足以作為收案前置完成證據，因 P1-01～03。縮小版綠＋完整版登 RM-FULLSCALE 仍是較嚴版收斂的要求，不是刪除完整驗證。

**(1b)** 對照 codex r4 P2-02：

| r4 要點 | v59 / 現碼評估 |
|---|---|
| 獨立新入口，不弱化原 gates | 兩新檔直接委派，13＋7 node；設定只縮生成範圍，原 gates 未改 |
| 真實 kline、full/trunc 同日期算法、CGSA/persist | fixture 讀真實 cache；helper `_build_truncation_pair`／`_run_generation` 沿用 persist=True、固定 env |
| trend 起點、RSI/STOCHRSI/ADXR、非 close source、L2/L3/L4/L6.5 | trend＋momentum 類別、close＋volume、L2 開、L3 5/13 全聚合器、L4 開、原 rank/zscore/gaussian/L6；未選其他指標／參數不作等價聲明 |
| 必要 window_bars | 秒級 resolver：values 3594、fracdiff 3342、multi 12786，未手裁 warmup |
| 正常與尾擾動基線、原 L3/winsor/L4 控制 | node 皆在；实际 seam／鑑別力需正式收據，現有寬捕獲有 P1-03 |
| fracdiff 長度/parallel、校準擾動、全量 d-star fit | node 皆在，但前兩種控制 P1-01／02；codec xfail 不能充當正常綠基線 |
| 分母全欄尺度附加控制 | 已新增，seam 位置正確；實際數值敏感性未驗；P1-03 |
| 三種遮罩刪除另由雙起點負責 | v59 明文由 §G⑦ 承接，不以尾截斷 MR 替代 |
| multi-TF 原 1h＋4h＋12h 與 alignment 控制 | 本機改 1h＋4h，12h 明示未涵蓋且全版另列；資料長度限制可接受，不宣稱原集合等價 |
| mutant 逐條 seam／基線／失敗原因收據 | SPEC 有要求，但現 body 無法確保準備錯誤被排除，P1-03；整套收據未產 |
| 未選指標、跨來源、大規模非等價；全版待換機 | Task 4.2 誠實邊界與 RM-FULLSCALE ④⑤皆已列，保留交易決策限制 |

## 必答 2a／2b — 前提與未查事項

**(2a)** assumed ①設定替換成立；②seam 靜態可達，但生成時被呼叫與抽樣仍未驗，不能僅由層覆蓋 guard 宣稱已驗；③同起點、只移除因果前綴遮罩的 mutation 可以兩邊同錯，交雙起點合理，不能擴大為所有遮罩相關缺陷必不可見。未查 1：strict xfail 是否 XPASS 未驗；2：分母 mutant 是否跨近零閾值未驗；3：既有 +1 forward mutant 在 4h 的 12h 邊界仍可觀測，不證其他未注入漂移；4：close/volume 的跨來源 Ratio 並不存在於此配對路徑；5：v59 的非全設定等價與全版待驗邊界足夠。

**(2b)**

- ① `probe.py` rc=0：兩 payload equality True；多週期 globals `[1h,4h]`／`[4h]`、payload equality True。helpers `_fracdiff_window_bars` 接受 caller 傳入縮小 payload；`_build_truncation_pair(window_bars=None)` 也用傳入 payload，無定義期原全設定綁定。module-scoped 新 baseline fixture 自建 small payload，不依賴 function-scoped monkeypatch 的 setup 順序。
- ② rolling_aggregator:494 在呼叫期局部 import 全域 `fused_rolling_stats_multi_window`，:522 呼叫；L6.5 `_transform*` 經 `_apply_winsorization`，L4 委派 `LagProcessor.compute_all`。縮小設定未关層；helpers:666-704 要求抽樣 L3／L4／winsor／coarse 層。兩份可行性收據的 L3/L4 均有實際欄，但不是 mutant spy 證據。三生成 seam mutant 未執行。
- ③ `_build_truncation_pair` 在 full/trunc 共用同 start；純因果前綴遮罩刪除若只影響共同前綴，same-start 比較可同錯。L1／winsor 完整窗／第④類遮罩的雙起點控制仍由 §G⑦ 承接，未於本輪重跑。
- 未查 1：wrapper strict=True 且取原 reason；仍走原 `_assert_fracdiff_truncation_invariants` 與 persist/codec，縮小沒有關掉 codec。是否值域使型別選擇不再分歧，只有實跑可判；不以 xfail reason 斷言必 XFAIL。
- 未查 2：numeric_guards:111 在函式執行時取全域 `causal_denominator_scale`，patch 可命中；`calls>0` 不證 near-zero mask 差異。主委正在跑的結果未包含於本輪來源，故未驗，不能預先宣稱 mutant 紅。
- 未查 3：helpers:1217-1228 取 `[warmup,n_trunc)` 之 12h close 邊界；每個邊界也是 4h close 邊界，+1 forward map 在該列用下一個 4h 值，原 boundary oracle 可觀測。多週期 warmup=12744、n_trunc=12776 有 32 列，比 12h 間距長，連續 1h 真實窗至少有邊界；實際對齊值差異仍未跑。此是特定 mutant 的鑑別力論證，不宣稱涵蓋每個 4h 邊界的任意錯誤。
- 未查 4：derived_operators:272-277／522 依 `(source,category,indicator)` 分組作 Ratio/Cross 配對；兩來源各自有欄，不代表 close÷volume。現行 SPEC 已明示「不證跨來源」，故不另造 finding。非加密市場的生產正確性也不由此 BTC 單一輸入背書。
- 未查 5：Task 4.2:198-200 明示不證全設定等價、不可宣稱既有兩檔已通過；RM-FULLSCALE ④⑤保留完整驗證與資源／真實長歷史條件，不必再加一層機制。

## 必答 3a／3b — 委派與漏測

**(3a)** autouse 換全域的現行設定路徑正確，不構成自身假綠；直接委派讓原控制中的過期校準假設、max-lag cap 与寬捕獲一併繼承，故仍會有假綠或控制未瞄準目標的風險。

**(3b)** P1-01 的真實必要窗使兩邊參數同值；P1-02 的真實 timestamp 分區證明校準域改動為零；P1-03 的秒級 preparation 反例使新 wrapper 正常返回。module-global 取設定並無遺漏之直接全設定參照，兩新檔 collect 20 node，不代表鑑別力通過。

## 必答 4a／4b — 是否投入整套實跑

**(4a)** 否，目前不建議投入完整 6.5 小時收案驗收；現行 probes 僅證 values 基線成本可行，多週期探針還未帶 coarse-layer 覆蓋 gate。三條控制缺陷修補後，才有合理的同設定正常／mutant 成對驗收前提。

**(4b)** 擋項僅 `CODEX-R1-P1-01`、`CODEX-R1-P1-02`、`CODEX-R1-P1-03`。未跑生成、未得主委分母 mutant 結果是本輪授權邊界，不另列成缺陷。

## 秒級反例原碼與實跑紀錄

實跑 cwd 是 `/tmp/ff-review-6Kq7nt`，複本由 `rsync -a --exclude '__pycache__' --exclude '.DS_Store' --exclude 'golden' --exclude '_golden' momentum api tests config conftest.py pytest.ini /tmp/ff-review-6Kq7nt/` 建立，另複製 `_isolate.py` 与 scripts。下列是 evidence.py 的核心原碼；沒有 `generate_features` 呼叫，只有真實 cache 唯讀與控制流程替換。

```python
import os
os.environ['NUMBA_CACHE_DIR'] = '/tmp/ff-review-6Kq7nt/numba'
from _isolate import isolate, isolate_dstar_cache
root = isolate('ff-evidence-')
isolate_dstar_cache(root)
import h5py, numpy as np, pandas as pd, pytest
from tests.feature_engineering import ff_truncation_mr_helpers as h
from tests.feature_engineering import test_ff_fullchain_truncation_small_mr as s
from momentum.FeatureEngineering.utils import numeric_guards as ng
with h5py.File('/Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines/kline_cache.h5', 'r') as handle:
    raw = pd.DataFrame(handle[h.SYMBOL][h.TIMEFRAME]['data'][()])
w = h._fracdiff_window_bars(h._small_fracdiff_mr_config_payload())
print('MAXLAGS', w, w-h.TRUNC_K,
      [min(max(2,n//10),252) for n in (w,w-h.TRUNC_K)])
start, _, _ = h._bar_window_dates(raw, window_bars=w, trunc_k=h.TRUNC_K)
patched = h._patch_kline_calibration_ohlcv(
    raw, window_bars=w, calibration_bars=500, delta=h.PERTURB_DELTA)
before = pd.to_datetime(raw.timestamp, unit='s', utc=True) < pd.Timestamp(start).tz_localize('UTC')
changed = raw.close.to_numpy() != patched.close.to_numpy()
print('CALIBRATION_TARGET', int(np.sum(changed & before.to_numpy())),
      int(np.sum(changed & ~before.to_numpy())))
def broken_preparation(*args, **kwargs):
    ng.causal_denominator_scale(raw.volume.to_numpy(dtype=float))
    raise AssertionError('mutation layer coverage failed (sampling design error): missing L4')
with pytest.MonkeyPatch.context() as mp:
    mp.setattr(s, '_build_truncation_pair', broken_preparation)
    s.test_small_mutation_denominator_scale_full_column_fails(mp, root, raw)
    print('PREPARATION_FALSE_GREEN: returned normally; invariant never ran')
```

命令與結果：

1. `PYTHONDONTWRITEBYTECODE=1 /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe.py` → rc=0，3594／3342／12786 必要窗；單與多週期 global 設定替換 True；13＋7 wrappers；strict=True；未生成。
2. 同前綴 `python evidence.py` → rc=0，校準域改動 0／公開域 500、缺 L4 preparation 假綠、builder 移出捕獲會傳出、uncapped 334／333，前史 500 真實列可用；未生成。首次探針 UTC-aware 對 naive Timestamp 比較錯誤，僅複本探針明示 UTC 後修復。
3. 同前綴 `python collect.py`（先兩個 isolate，`pytest.main(['--collect-only','-q','-p','no:cacheprovider',兩新檔])`）→ rc=0，`20 tests collected in 0.06s`。第一次複本缺 scripts 導致 tests/conftest 依賴 fallback，collect hook 對 None Path 出錯 rc=3；補複製既有 scripts 后通過，無測試／gate 修改。
4. `git status --short -- momentum api frontend tests templates config` 前後導入複本 status-before.txt／status-after.txt；`cmp` → rc=0，原工作區既有 dirty 項完全相同，包括既有 golden／Numba cache 改動。

ASSUMPTIONS_VERIFIED: 設定替換完整、必要窗與 capped max-lag 同值、實際校準擾動未觸前史、preparation AssertionError 可造成控制正常返回；命令與輸出如上。
TESTS_RUN: collect-only rc=0/20 nodes；兩個秒級探針 rc=0；status cmp rc=0；生成型 node 未執行。
FAILURES_SEEN: 複本缺 scripts 的 collection rc=3 與探針 UTC 比較 rc=1，皆僅修複本後 rc=0。
SCOPE_CHANGES: none；審查中未改生產／測試／SPEC／manifest；本檔為指定產出。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_NOT_UPDATED: 本輪唯讀合約，未另寫狀態交接，未修改根 HANDOFF.md。
OUTPUT: handoffs/20260926-ffstat-b6-review-r1-codex.md

交件檢查：`bash scripts/completeness_check.sh --single handoffs/20260926-ffstat-b6-review-r1-codex.md --family codex --round-id 3e0620b0-1bb6-40a6-986c-cfcb1d3e0303` → rc=0，`COMPLETENESS PASS(single)`，3 個 canonical ID。
收尾：最終相同 status 命令＋`cmp status-before.txt status-final.txt` → rc=0；受控 `shutil.rmtree(Path('/tmp/ff-review-6Kq7nt'))` → rc=0，`WORKDIR_REMOVED True`、`CLAUDE_501_PRESERVED True`。本輪 workdir 已清，未刪其他工作者目錄。探針原碼與輸出摘要留在本產出，不依赖已刪複本作交件落點。

VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03
CLOSED:
