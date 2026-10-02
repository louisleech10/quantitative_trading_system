# Reconcile — 20260926-ffstat-b6-review-r4

**來源** 20260926-ffstat-b6-review-r4-codex.md, 20260926-ffstat-b6-review-r4-composer.md, 20260926-ffstat-b6-review-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

三家 proceed、零 finding。諮詢 r1 各條由原提出方確認閉合：codex CLOSED CODEX-R1-P1-01；grok CLOSED GROK-R1-P0-01、GROK-R1-P2-01；composer 於正文（1a）逐條確認 COMPOSER-R1-P0-01／P1-01（置中窗 mutant 於 v61 碼 m2 被抓到）與 P2-03（尾擾動長度耦合已撤）閉合。三家一致：六段逐 node 結果與收據一致；v60 碼段之結果於 v61 下轉用之依據成立（基線 informational 0 行、允許 gate 集合未縮）；Task 4.2 兩新檔現行 18 node（單週期 10 過＋1 strict xfail、多週期 7 過）滿足驗收條款 ⇒ **Task 4.2 完成，可作 FF-STAT 收案前置**；既有兩檔完整版仍為大機器驗證清單 ④⑤，縮小版不代其通過。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 放行：本輪逐項核對後無finding；本家諮詢 | P3 | CODEX-R4-P3-00 | 採納（proceed；Task 4.2 完成） | other |
| 放行：本輪對v61gate、六段收據／log、 | P3 | COMPOSER-R4-P3-00 | 採納（proceed） | other |
| 放行：本輪逐項核對後無finding；諮詢r1 | P3 | GROK-R4-P3-00 | 採納（proceed） | other |

Verdict: 可合併（Task 4.2 完成；FF-STAT 收案前置滿足）

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；本家諮詢 CODEX-R1-P1-01 已閉合，六段逐 node 結果與收據一致，現存縮小版 18 項皆有符合 v61 驗收條款之結果或版本轉用依據。

**碼證**: `tests/feature_engineering/ff_truncation_mr_helpers.py:797-818,977-993,1456-1466,1493-1524`；`git diff 2fe07ae3 ab94ec28 -- tests/feature_engineering/ff_truncation_mr_helpers.py` 顯示 mask gate 改嚴、允許 gate 集合未改，fracdiff 長度耦合僅撤 tail 路徑。`git diff ab94ec28 055af679 -- tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py` 無輸出。/tmp 複本實跑捕獲邊界 12 passed；換回舊分層規則後兩方向 mask 案 2 failed（DID NOT RAISE）、同位置稀疏 1 passed。六段 log 解析與 AST 具名 node 對證 `AUDIT PASS`，單週期 10 passed／1 XFAIL，多週期 7 passed；詳細命令、行號及邊界如下。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#8aa3e85a536c; handoffs/run_receipts/20261002-ffstat-small-mr.json#913352d34cf3

**類別**: other

### 必答 1

**(1a)** 本家諮詢 r1 唯一 finding `CODEX-R1-P1-01` 閉合。主值 gate 比較窗之 NaN mask 現為雙方向全等，低 fill 不再旁路；原本存活之單週期置中窗 mutant 已以 v61 實跑抓到。尾擾動長度耦合控制於既有檔、縮小版及共用 helper 同步撤除，截斷／並行兩控制仍在且有通過紀錄；沒有新增 xfail。

**(1b)** s2 log `:1184-1802` 原單週期 center 為 FAILED；m2 `:3006-3627` 同名 node 為 PASSED。m3 `:10-1509` 多週期 center 為 PASSED。s1 `:3400-4471` 長度耦合截斷 PASSED；s2 `:10-1183` 並行 PASSED。讀碼 `test_ff_fullchain_truncation_small_mr.py:97-106` 及 `test_ff_fullchain_truncation_mr.py:168-177` 僅保留撤除說明、沒有 tail 測試函式。秒級複驗見下方實跑紀錄。

### 必答 2

**(2a)** assumed ①在本輪既有觀測與兩版本差異下成立，屬可支持的結果轉用，不是新碼整條已跑。assumed ②不能宣稱已實證成立；也沒有具體反例能判為假。縮小版兩基線沒有不對稱，並不能推出未選欄類之全設定必無不對稱。

**(2b)** assumed ①：s1、m1 之舊分層 gate 只有 mask 不等且低 fill 才印 informational；高 fill 不等會 fail。四個正常主 MR 基線均 PASSED 且兩段 informational 都 0，因此所比較的抽樣格 mask 已相同，新 mask gate 在同產物上仍通過。fracdiff gate 原已 exact mask，不受這次修改。舊碼已抓到的主 MR mutant 若更早在新 mask gate 失敗，traceback 仍經 `_assert_values_gate_main`，屬同一允許集合；準備／抽樣／coverage 排除條款不變。校準兩控制僅收 columns／d*，其 fracdiff 路徑與出口未變；長度耦合 trunc／parallel 的非 tail 路徑也未變。這些支持不追加慢重跑；未保留／重放全部生成產物，本家沒有新碼逐條實跑聲明。

assumed ②：對相同輸入共同前綴、相同已完成 bar 決策時間，合法稀疏欄應在同位置缺值；高低 fill 本身不是不對稱的豁免理由。若完整版出現差異，仍需具體格之輸入、時間對齊或計算證據定性。全設定與 12h 未跑的限制已由 SPEC Task 4.2 誠實邊界和 RM-FULLSCALE 承接，不能據此把嚴格 gate 放寬。

**(2a)** 「我沒查」1：逐 node 判定與 log 一致。2：確切 gate 名未列入收據可接受，無須重生成只為列印回傳值。3：以 v61 明列之既有 XFAIL 例外及有證據的版本轉用，兩新檔全部現存 node 之驗收已滿足。

**(2b)** 1：解析每段測試執行區（FAILURES／warnings summary 前），以具名 node 起始行和緊接之 PASSED／FAILED／XFAIL 行配對，逐鍵對照 JSON；未使用尾部 warning 名稱或單靠清單順序猜測。再用兩新檔 AST 列舉全部 test 函式，取各 node 最後結果，18／18 有對應，沒有將撤除 node 算進分母。2：`_expect_causal_gate_failure` 準備檢查在捕獲外，只收 AssertionError，traceback 不經 `_assert_mutation_layer_coverage`、訊息不含非因果守衛、且至少經允許 gate；不符合任一條即 node FAILED。捕獲邊界秒級測試 12 passed 又直接驗其接受／拒收行為。故 PASSED 已證有允許之 gate 出口；缺少確切名稱是診斷留痕邊界，沒有具體未來洩漏漏測反例。3：逐 node 證據如下表；XFAIL 是原 codec 值精度問題，並非本輪把 center 漏測改成豁免。

| 段 | node 次序（簡稱）與 log 起始→結果行 | 結果 |
|---|---|---|
| s1 | capture atol 10→10；C2-1 11→636；C2-2 637→1255；fracdiff trunc 1256→2327；fracdiff tail 2328→3399；length trunc 3400→4471；length tail 4472→5543 | 前四過；tail XFAIL；length trunc 過；length tail 紅且 v61 撤除 |
| s2 | length parallel 10→1183；center 1184→1802；winsor 1803→2421；L4 2422→3040；calibration perturb 3041→4233；full d* 4234→5321 | center 紅、後於 m2 新碼閉合；其餘五過 |
| m1 | C3 trunc 10→1513；C3 tail 1514→2980 | 兩過、informational 0 |
| m2 | align 10→1509；align tail 1510→3005；single center 3006→3627 | 三過、v61 |
| m3 | multi center 10→1509；multi winsor 1510→2995 | 兩過、v61 |
| m4 | multi L4 10→1509 | 一過、v61 |

表中 log 前綴均為 `handoffs/run_receipts/20261002-ffstat-small-mr-<段>.log`。s1 額外 capture node 不算兩新檔分母；s2 舊 center 結果由 m2 同名重跑取代。單週期現存 11＝10 過＋1 XFAIL；多週期 7＝7 過。

### 必答 3

**(3a)** Task 4.2 完成，可作為 FF-STAT 收案前置。停止本輪的依據是：具名缺陷之 seam 與允許出口已由控制內斷言約束、原唯一存活 center 有新碼實跑閉合、mask 兩方向捕獲可證偽、全部現存 node 有逐項證據且版本轉用理由成立。没有必要為診斷列印或無關 gate 改動再付出成對生成成本。

**(3b)** 無擋收案前置之 P0／P1。此判斷不等於全設定或所有未來洩漏已被證明不存在；原 codec strict xfail 和 RM-FULLSCALE 範圍仍如 SPEC 明列，不以本輪縮小版替代完整版。

### 實跑命令與觀測

本輪 workdir `/tmp/ffstat-review-427fb0f0`，測試源、momentum、api、config、scripts、pytest.ini、各層 conftest 與六段 log／JSON 均複製至此；不複製真實 data_cache、不跑生成型 node。以下命令 cwd 均為該 workdir，Python＝專案 `venv/bin/python` 的絕對路徑。

1. `/Users/louis/Desktop/quantitative_trading_system/venv/bin/python audit.py > audit.log` → rc=0、六段逐鍵 node-map OK；informational s1=0、s2=236、m1=0、m2–m4=0；AST 現存 single 11／multi 7，`AUDIT PASS`。探針 sha256 `5f8d5795d507c50348a114f0d7c820cdbb3d216818881c4d4b51d36de14a9b1f`。探針只讀複本 log／JSON、做字串解析與 AST 列舉，未 import 生產生成器。
2. `NUMBA_CACHE_DIR=/tmp/ffstat-review-427fb0f0/numba /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q -p no:cacheprovider --basetemp=/tmp/ffstat-review-427fb0f0/pytest-complete > boundary-complete.log 2>&1` → rc=0、12 passed in 0.41s。首跑尚未複製根 conftest，同檔亦 12 passed in 0.22s；以完整 conftest 複驗之結果為本輪證據。
3. 僅在複本 helper 將 mask 不等分支換回「兩側 fill ≥0.95 才 raise，否則 informational」，其他測試／gate 不改。`NUMBA_CACHE_DIR=/tmp/ffstat-review-427fb0f0/numba /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -k 'mask_only_asymmetry or equal_sparse_mask' -q -p no:cacheprovider --basetemp=/tmp/ffstat-review-427fb0f0/pytest-mutant > mutant.log 2>&1` → rc=1、2 failed／1 passed／9 deselected in 0.33s；兩方向皆 DID NOT RAISE，同位置稀疏仍通過。這是預期 mutant 紅，沒有生成或 fake kline。
4. `git status --short -- momentum api frontend tests templates config` 開跑前後各存快照；`cmp /tmp/ffstat-review-427fb0f0/status-before.txt /tmp/ffstat-review-427fb0f0/status-after.txt` → rc=0、無輸出，既有 dirty 列未變。

ASSUMPTIONS_VERIFIED: 六段逐 node 與收據一致；mask 捕獲兩方向及同位置稀疏已實跑；assumed ①有讀碼／log 轉用證據，②全設定不假紅未驗證。
TESTS_RUN: 上列 audit rc=0；完整 conftest 邊界 12 passed rc=0；舊規則 mutant 2 failed／1 passed rc=1（預期）。
FAILURES_SEEN: 預期舊 gate mutant 兩例 DID NOT RAISE；讀檔時曾使用不存在之多週期檔名，後由實際檔名 test_ff_multitf_truncation_small_mr.py 完成讀取；未修生產碼。
SCOPE_CHANGES: none；僅本交件與本次 /tmp 複本，未改碼／SPEC／manifest／git。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_NOT_UPDATED: 本輪唯讀 brief；未寫另份狀態交接、未改根 HANDOFF.md，交件落點為本檔。
OUTPUT: handoffs/20260926-ffstat-b6-review-r4-codex.md

交件自驗：`bash scripts/completeness_check.sh --single handoffs/20260926-ffstat-b6-review-r4-codex.md --family codex --round-id 427fb0f0-661e-4ba5-8a68-8c8e65139c9e` → rc=0，`COMPLETENESS PASS(single)`、1 個 canonical ID。最終 `git status --short -- momentum api frontend tests templates config` 存 status-final.txt，再 `cmp /tmp/ffstat-review-427fb0f0/status-before.txt /tmp/ffstat-review-427fb0f0/status-final.txt` → rc=0、無輸出。`rm -r /tmp/ffstat-review-427fb0f0` 後 `test ! -e /tmp/ffstat-review-427fb0f0 && test -d /tmp/claude-501` → rc=0；本次 workdir 已清理，claude-501 保留。其他非本次暫存與服務目錄未動。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R1-P1-01
## COMPOSER-R4-P3-00

**斷言**: 本輪對 v61 gate、六段收據／log、諮詢 r1 閉合條與 12 項捕獲邊界測逐項核對後，無達 P0／P1 且可重現之未來洩漏漏測。

**碼證**: 讀碼 `tests/feature_engineering/ff_truncation_mr_helpers.py:797-818,924-988,1456-1463`；收據 `handoffs/run_receipts/20261002-ffstat-small-mr.json`；log 行號見必答 **(1b)**；`pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → 12 passed 0.22s rc=0；`git status --short -- momentum api frontend tests templates config` 與 `/tmp/ffstat-r4-status-before.txt` 同型（無本輪源碼寫入）。

**類別**: other

**來源摘要**: handoffs/run_receipts/20261002-ffstat-small-mr.json#913352d34cf3;tests/feature_engineering/ff_truncation_mr_helpers.py#8aa3e85a536c;tests/feature_engineering/test_ff_truncation_capture_boundary.py#f7e0a495b156;handoffs/reconcile/20260926-ffstat-b6-consult-r1/synth.md;docs/FFSTAT_SPEC.md#af2d63a0fb19

正文：v61 採諮詢較嚴版「雙方向 mask 全等」，覆蓋本家 consult 最低限度「單側尾端 NaN 必抓」；舊分層規則下 s2 236 行 informational 於 v61 下改為硬失敗，m2 已證 center mutant。尾擾動長度耦合 tail 控制撤除與三家共識一致，不構成殘留漏測出口。未跑生成型 node；未審全設定 13 項假紅；收據未逐 node 列 gate 函式名屬誠實邊界，建議主委銷帳時保留 receipt `honest_bounds` 第 2 條，非本輪 blocking。

---

ASSUMPTIONS_VERIFIED: 主委 fact-verified 1–3 與 log／現行測試清單一致；m2 center PASSED；capture 12 passed 與 brief 一致。  
TESTS_RUN: `pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q` → 12 passed 0.22s rc=0；`grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-m1.log` → 0。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: `handoffs/20260926-ffstat-b6-review-r4-composer.md`

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

STATUS: DONE
## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；諮詢 r1 之置中窗漏測於 v61 下被抓到、尾擾動長度耦合已撤，Task 4.2 兩新檔現行 node 全綠，可作 FF-STAT 收案前置。

**碼證**: `venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → 12 passed in 0.19s rc=0。`--collect-only` 兩縮小檔＋捕獲邊界 → 30 collected in 0.04s（單週期 11、多週期 7、捕獲 12；無 `*_maxlag_len_coupling_tail_fails`）。六段 log 與收據 `handoffs/run_receipts/20261002-ffstat-small-mr.json` 逐 node 一致；s2:5331 DID NOT RAISE 對 v60 置中窗、m2:3627 同 node v61 PASSED；s1:5546-5558 尾擾動長度耦合值 gate 不在允許集。helpers:797-818 雙方向 mask 全等；`:1456-1462` 允許集含 `_assert_values_gate_main`。`cmp` 開跑前／後 scoped `git status --short -- momentum api frontend tests templates config` rc=0。

**類別**: other

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#8aa3e85a536c; tests/feature_engineering/test_ff_truncation_capture_boundary.py#f7e0a495b156; tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#1eea8efdbc3a; docs/FFSTAT_SPEC.md#af2d63a0fb19; handoffs/run_receipts/20261002-ffstat-small-mr.json#913352d34cf3; handoffs/run_receipts/20261002-ffstat-small-mr-s2.log#ff5498e42586; handoffs/run_receipts/20261002-ffstat-small-mr-m2.log#54d97f961456; handoffs/reconcile/20260926-ffstat-b6-consult-r1/synth.md#bea3cd80332c; handoffs/20260926-ffstat-b6-consult-r1-grok.md#d7192f2624e6; handoffs/20261002-FFSTAT-B6-REVIEW-R4-BRIEF.md#e5b504486bbe

核對範圍：諮詢 r1 本家 `GROK-R1-P0-01`／`GROK-R1-P2-01`；SPEC v61 Task 4.2 驗證條款與誠實邊界；現行 helpers mask／捕獲／允許集；六段 log 與收據；秒級捕獲邊界 12 項；collect-only 列點。未跑生成型 node。未發現可重現之未來洩漏漏測。`HIGH_FILL_RATE_THRESHOLD` 常數仍在 helpers:55、函式本體已不再讀它，屬死常數，不構成本輪 finding。

---

ASSUMPTIONS_VERIFIED: ① mask raise 仍經 `_assert_values_gate_main`（允許集未縮）；s1／m1 informational 0。②縮小版＋多週期基線 0 informational；全設定 13 項未跑、已登 RM-FULLSCALE。
TESTS_RUN: `venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py -q --tb=short -p no:cacheprovider` → 12 passed in 0.19s rc=0；`--collect-only` 三檔 → 30 collected in 0.04s rc=0；awk 六段 log 對帳與收據一致。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: `handoffs/20260926-ffstat-b6-review-r4-grok.md`
HANDOFF_NOT_UPDATED: 本輪唯讀 brief；根 HANDOFF 與另份狀態交接均未改寫，交件落點為本檔。

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R1-P0-01,GROK-R1-P2-01

STATUS: DONE
