# FFSTAT B6 review R3 — codex

task-id: 20260926-FFSTAT-B6-REVIEW-R3

審查標的：commit `1d09aaa4`、SPEC v60 Task 4.2、manifest、r2 收斂檔及實際 helpers 呼叫鏈。結論：本家 r2 P1 閉合；本輪無新增 finding，可進入既定串行、獨占生成驗收。此結論是全跑前審查，不是 Task 4.2 已驗收或生產資料正確性簽核。

## CODEX-R3-P3-00

**斷言**: 本輪逐項核對後無 finding。原 warmup／fracdiff atol／metadata 反例均被新捕獲器接收，實際 coverage／sampling 守衛仍拒收，對齊 oracle 與主 MR 捕獲鏈未見衝突。

**碼證**: 複本命令 A → `9 passed in 2.65s`、rc=0；命令 B → `ACCEPT main_value`、`ACCEPT main_mask`、`REJECT real_coverage_guard`、`REJECT real_sampling_fail Failed`、`ACCEPT dstar_prevalues`、`ACCEPT align_oracle_then_main`、三條 `R2_CLOSED`、`PROBE_OK`，rc=0。helpers:1456–1472 定義六個因果函式與非因果守衛，1517–1530 以 traceback 做分流；1089–1126／1157–1171 之 check 呼叫鏈全部斷言落點已對照，align oracle 僅於1689之捕獲區外執行。命令 C → 四檔 `41 tests collected in 2.23s`、rc=0，無生成。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b;tests/feature_engineering/test_ff_truncation_capture_boundary.py#3332fe88dc49;docs/FFSTAT_SPEC.md#f8a327dafd6a;docs/manifests/FFSTAT.json#b1c0efc364c3

**類別**: other

## 必答 (1a)／(1b)：本家 r2 原反例

(1a) `CODEX-R2-P1-01` 閉合。修法改用 traceback 函式名，未採本家所提補訊息標籤，但確實排除原缺陷，既有 gate 判準、容差與訊息保留。warmup 實際仍是 `warmup <file>::<col> NaN mask mismatch`；atol 實際仍由 numpy 拋 `Not equal to tolerance`；metadata 仍可裸 assert。三種訊息無須對上前綴即可被認定。

(1b) 命令 A 的三個具名 node（`test_fracdiff_atol_values_gate_failure_is_accepted`、`test_warmup_nan_mask_failure_is_accepted`、`test_metadata_gate_failure_is_accepted`）均 passed；命令 B 另直接重跑同三個真實 gate 輸入，逐條印 `R2_CLOSED <node>`，rc=0。輸入同原反例：full fracdiff `[0,1,2,9]`、trunc `[0,1,3]` 製造 atol 值差；trunc `[NaN,1,2]` 製造 warmup mask 差；metadata symbol A／B 製造裸 assert。只對這三個極小捕獲邊界案例略過 `_assert_mr_preparation`，不把它們當 FF 生成或資料正確性證據；其餘主 gate 探針走原準備檢查。

## 必答 (2a)／(2b)：assumed ①②③

① 在現行六個 gate 的實際失敗路徑成立。命令 A 證 columns、warmup、metadata、numpy atol traceback 均含表列 caller，即使最內層 raise 在 `_assert_arrays_values_close` 或 numpy。命令 B 補真實 `_assert_values_gate_main`→`_assert_values_both_non_nan_close`、`_assert_nan_mask_layered` 與 `_assert_d_star_gate`：值、high-fill NaN mask、d* 失敗均被收。`pytest.raises` 的 traceback 在這些原生路徑保留 caller，沒有截掉 gate。這是現行環境／現行 gate 的實測，不外推未來所有 Python 或 pytest 行為。

② 在現行主 MR／fracdiff MR `check()` 呼叫鏈成立。helpers:1089–1126 順序為 columns→main values（或 values）→warmup→metadata；1157–1171 為 strict columns→d*→values→warmup→metadata。`_assert_nan_mask_layered`、`_assert_values_both_non_nan_close` 與 `_assert_arrays_values_close` 雖不在表內，皆經表列 caller，不是裸露於 wrapper 之外。`_assert_d_star_gate` 缺檔／無共同 key 使用 `pytest.fail`，不會冒充 d* 差異；JSON／parquet 讀取錯誤若非 AssertionError 同樣向外傳出。現行 wrappers 沒有另一個表外因果斷言入口。

③ 成立，且 brief 所稱「invariants 內部 align 相關檢查」須精確理解為主值抽樣／覆蓋中的 `align_coarse_tfs`，不是第二次呼叫 look-ahead oracle。helpers:1689 先於捕獲區外要求粗週期邊界有差異；1690 隨後執行原 `_values_check`，由主值 gate 比對。同一個粗週期值差既能令正向 oracle 通過，也能令主 MR 失敗，二者方向相容。命令 B 使用31／21列、warmup=1、1h時間戳、`close_4h_trend_EMA_5` index=11由11改21（12h收盤邊界），原 oracle 通過，隨後回傳 `_assert_values_gate_main: ... values mismatch`。這只是捕獲鏈鑑別力證據，不宣稱實際 align mutant 已生成驗證。

## 必答 (2a)／(2b)：未查面 1–3

1. coverage／sampling 分流完整於現行實作。main gate:993–1003 的 `coverage guard failed` 是 AssertionError，但1524之 marker 拒收；主 gate:949–952 的 sampling guard 是 `pytest.fail.Exception`，不屬 AssertionError，直接傳出。`_assert_mutation_layer_coverage` 同時有函式名排除與 marker，準備檢查又在捕獲區外。命令 B 以三個實際 L1／L3／L4 小 parquet 走準備檢查：兩側後綴全 NaN 時原 coverage guard 被拒；只改抽樣報告為不足（探針內將 min=3、reported sampled_count=1）時原 sampling 分支傳出 `Failed sampling guard failed: sampled=1 < min=3`。沒有改 repository gate 或其正式門檻。命令 A 的守衛函式路徑與守衛訊息反例亦均 passed。

2. lambda／閉包不影響現行判定。判定取整個 traceback 的名字集合，不要求 `check` 名字本身命中；命令 A 的真實 gate 成功案例均由 lambda 呼叫，命令 B 的兩個 wrappers 也都是 helpers 原 lambda。表外 `check` 即使訊息仿 `values something` 仍被拒，具名測試 passed。單靠函式名無法防蓄意同名偽造；本輪威脅模型為意外漂移與洩漏漏測，現行 check 路徑沒有同名非因果 helper，未以惡意偽造另開阻擋項。

3. 新增未列 gate 的 AssertionError 將因交集為空而令負控制紅，方向為 fail-closed，可接受。若新增 gate 作為既有 gate 的內部值比較 helper，仍會由既有 caller 被收，必須按 caller 的因果／準備語意理解，不能泛稱所有新增函式必拒。現有內部非因果 AssertionError 已明確排除；本輪未發現需要另加機制的現行缺口。

尾擾動 fracdiff、校準擾動及全量 d* 控制的 allowed 集合只含 strict columns／d*。values、warmup、metadata 不因完整集合存在而自動放行；命令 A 的尾擾動 values 拒收 node passed。非尾擾動長度耦合則使用完整集合，與 SPEC 一致。

## 必答 (3a)／(3b)：可否全跑

(3a) 可以進入 brief 所定约6.5小時、串行、獨占的縮小版生成驗收。依據是 r2 原反例閉合、六個 gate 與實際 caller 逐項對證、準備／coverage／sampling 分流成立、對齊正反檢查相容，以及41個node仍可收集；沒有額外慢閘或需先修的 P0／P1。

(3b) 擋之 P0／P1：none。生成後 mutant 是否確實改變 d*／欄集合、所有控制是否抓到、實際資源峰值及逐 node 收據仍未驗證，屬既定全跑驗收結果；本輪不把函式邊界通過當作這些結果已通過。完整版、12h、未選指標／參數及全欄覆蓋仍依 SPEC 誠實邊界。

## 實跑命令與輸出

以下命令 A–C 的 cwd 均為 `/tmp/ffstat_b6_r3_6d0c7851`，程式碼由工作樹唯讀複製，來源 helpers 與 commit `1d09aaa4` 無 diff。所有實跑未呼叫生成入口；極小 parquet／d* JSON 只測 gate 捕獲邊界，不是合成 FF 生成資料。

```text
A: PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat_b6_r3_6d0c7851/numba /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -m pytest tests/feature_engineering/test_ff_truncation_capture_boundary.py --noconftest -q -p no:cacheprovider --basetemp=/tmp/ffstat_b6_r3_6d0c7851/pytest_tmp
9 passed in 2.65s; rc=0

B: PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat_b6_r3_6d0c7851/numba /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe.py
IMPORT_FROM_COPY /private/tmp/ffstat_b6_r3_6d0c7851/tests/feature_engineering/ff_truncation_mr_helpers.py
ACCEPT main_value _assert_values_gate_main: ... values mismatch
ACCEPT main_mask _assert_values_gate_main: ... high-fill-rate NaN mask mismatch (fill_rate full=1.000 trunc=0.950)
REJECT real_coverage_guard AssertionError ... coverage guard failed: 0/3 ... required >= 95%
REJECT real_sampling_fail Failed sampling guard failed: sampled=1 < min=3
ACCEPT dstar_prevalues _assert_d_star_gate: d_star mismatch ... 0.2, 0.4
ACCEPT align_oracle_then_main _assert_values_gate_main: ... values mismatch
R2_CLOSED test_fracdiff_atol_values_gate_failure_is_accepted
R2_CLOSED test_warmup_nan_mask_failure_is_accepted
R2_CLOSED test_metadata_gate_failure_is_accepted
PROBE_OK; rc=0

C: PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat_b6_r3_6d0c7851/numba /Users/louis/Desktop/quantitative_trading_system/venv/bin/python -m pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py tests/feature_engineering/test_ff_multitf_truncation_mr.py tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py --collect-only --noconftest -q -p no:cacheprovider
41 tests collected in 2.23s; rc=0
```

`--noconftest` 用於獨立邊界測試與純收集，避免根 conftest 之 inventory／持久化插件副作用；邊界測試本身 autouse fixture 正常執行，沒有省略測試斷言。生成驗收不由這些命令代替。collect 出現未註冊 slow／requires_kline marker 警告；探針有 sandbox sysctl 權限警告，不影響 gate 斷言或 rc。

複本 tar 列入不存在的 `tests/__init__.py`，tar 曾報錯；其餘目標已提取，複本匯入路徑、A／B／C 執行成功。此為複本準備失誤，不是測試失敗或修改斷言後假綠。

ASSUMPTIONS_VERIFIED: A／B rc=0；原三反例、六個 gate caller 保留、real coverage／sampling 分流與對齊捕獲鏈如上。靜態證據分別列於必答段，未生成部分明示未驗證。
TESTS_RUN: A 9 passed rc=0；B PROBE_OK rc=0；C 41 collected rc=0；指定 completeness 與 status diff 結果於交件收尾補錄。
FAILURES_SEEN: 複本 tar 缺 tests/__init__.py；測試無失敗，探針預期拒收與 pytest.fail 皆符合預期。
SCOPE_CHANGES: none；僅明示交件檔寫入，repository 程式、測試、SPEC、manifest、git 均未修改。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_NOT_UPDATED: brief 本輪唯讀，依 AGENTS.md 唯讀例外，未另寫狀態交接或改根 HANDOFF.md。
產出：`handoffs/20260926-ffstat-b6-review-r3-codex.md`。

交件格式檢查：`bash scripts/completeness_check.sh --single handoffs/20260926-ffstat-b6-review-r3-codex.md --family codex --round-id 6d0c7851-df5d-470f-90b3-805001600c7d` → `COMPLETENESS PASS(single)`、1個canonical ID、rc=0。
工作樹比對：`git status --short -- momentum api frontend tests templates config` 前後存檔；`diff -u /tmp/ffstat_b6_r3_6d0c7851/status_before.txt /tmp/ffstat_b6_r3_6d0c7851/status_after.txt` → 無差異、rc=0，保留開跑前既有 dirty 檔。
暫存範圍：本次建立 `/tmp/ffstat_b6_r3_6d0c7851`；收尾清理結果另於最終輸出列出，`/tmp/claude-501` 保留，其他程序工作目錄不作本次所有物處理。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R2-P1-01
