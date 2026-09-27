# Reconcile — 20260926-ffstatauto-x-review-r19

**來源** 20260926-ffstatauto-x-review-r19-codex.md, 20260926-ffstatauto-x-review-r19-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 自訂指標無逐輸出宣告欄位：v38要求每個customoutputc | P1 | CODEX-R19-P1-01 | 採納（§C 輸出點契約：`CustomIndicatorDef` 新增必填之 `outputs` 宣告〔輸出欄名 → 已解析參數與 period_keys〕；`CustomIndicatorEngine.compute_all` 於 concat 前驗回傳欄集合＝宣告集合，無宣告或不相等即 blocked；設定格式變更之影響：預設 `custom_indicators: []`〔`config/scan_config.yaml:593`〕，無現行設定受影響） | code-contract |
| 進階輸出漏遞移依賴：v38以既有get_feature_me | P1 | CODEX-R19-P1-02 | 採納（§C：`period_keys` 定義為產生該輸出所需之**完整遞移週期集合**；同一引擎內由其他輸出再算出之欄，K＝上游輸出 K 之最大者＋本步窗長−1〔窗型〕或上游 K 之最大者〔逐點聚合〕；microstructure `ms_vpin_zscore_*` 之 metadata 須帶 base bucket 與 sigma bucket 之已解析值；取不到即輸出前 fail-closed） | code-contract |
| manifest 未列 v38 新測試：v38新增的Task2.3test_ff | P1 | CODEX-R19-P1-03 | 採納（同 CODEX-R14-P1-01 之處置：SPEC 定案後、實作派工前同步 manifest；v39 於 §P 增列 TODO 同步之必含清單——`test_ffstat_stable_start.py`、`test_ffstat_warmup_table.py` 入 test_files 與 gate_cmd，覆蓋、column-set delta、approval、blocked 收據入 script_acceptance／receipts——TODO 審查輪逐項對證） | doc-sync |
| CDL 三類輸出映射未定：v38對period_keys=[]的無 | P2 | CODEX-R19-P2-04 | 採納（Task 2.4：raw CDL＊ 之 period_keys＝空、K＝表內 pattern 條目之登記值〔現 `pattern_default_warmup_bars: 5`，改為表內具名條目〕；frequency 輸出 K＝上游 raw K＋window−1；Consensus K＝上游 raw K 之最大者〔即上一列之遞移規則〕；三者列入輸出點收據） | doc-sync |
| 零 finding：本輪逐項核對v38差分與r18採納修法後 | P3 | COMPOSER-R19-P3-00 | 採納（composer 判 proceed；無修訂） | other |

**主委說明**：§G⑦ 雙起點收斂對證以 1h、4h 預設全設定實跑，任何輸出之 K 算短（含本輪之 VPIN z-score、pattern Consensus）皆會使 B 之開頭值偏離 A 而紅，故輸出點契約之精確度另有實證終審；契約之作用在於「不依欄名、缺即擋」與非預設設定（自訂指標）之 fail-closed。

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R19-P1-01

**斷言**: v38 要求每個 custom output column 在 concat 前提供自己的 params 與 period_keys，且 params={} 未逐輸出宣告必須 fail-closed；但沒有定義 custom definition 的輸出宣告欄位或 structured-return ABI。現行 CustomIndicatorDef 只有一組任意 params，CustomIndicatorEngine 接受函式任意回傳的多欄 DataFrame 後直接 concat，因此只加 mapping/mask 無法對 short=rolling(5) 與 long=rolling(233) 產生可驗證的逐欄 provenance。

**碼證**: feature_config.py:451-457 的 custom schema 沒有 output declaration；custom_indicators.py:12-33 以單一 definition params 呼叫任意函式並接受任意 DataFrame；feature_factory.py:991-998 將該結果直接送入 L1 task。隔離複本以真實 BTCUSDT 12h 1,696 根執行 probe，params={} 的 custom_case.make 回傳兩欄，仍得到 first_finite_row={"long":232,"short":4}。
CODE-ANCHOR: momentum/FeatureEngineering/feature_config.py:451
MUTATION: 在隔離複本執行 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat-r19-run/numba PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python inspect_l1_contract.py；其中 custom 函式回傳 rolling(5)/rolling(233) 兩欄且 params={}，若沒有逐輸出 declaration 仍被接受，即重現 v38 fail-closed contract 缺口。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#7fac252e8abb; momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2; momentum/FeatureEngineering/atomic/custom_indicators.py#c8d69c237696; momentum/FeatureEngineering/feature_factory.py#47f362f67de2; data_cache/feature_klines/kline_cache.h5#b1ee5b9abcc1

修法：明定 custom output declaration（例如 output name → resolved params/period_keys）或唯一的 structured return wrapper，並在 compute_all／跨引擎 concat 前驗證回傳欄集合與宣告完全相等；plain 多欄 DataFrame 沒有 declaration 時直接 blocked，receipt 列 engine、output columns 與缺少的 keys。這會改變 custom config/return ABI，需明標 schema 影響；有效宣告的輸出欄數與指標數值可維持不變。

可行性證據：本輪 probe 已在 CustomIndicatorEngine.compute_all 的 plain-frame 邊界重現可攔截的輸入，故驗證點可放在現有 concat 前，不需改 rolling 數值計算；TA-Lib 既有 compute／compute_batch 已持有 params，可沿用同一 output-point contract。現況只證明反例會被接受，未宣稱此修法已實作或通過測試。

## CODEX-R19-P1-02

**斷言**: v38 以既有 get_feature_metadata 作為 advanced output 的欄級參數來源，但沒有要求 metadata 反映跨輸出點的遞移依賴。ms_vpin_zscore_21 的 metadata 只有 window=21；實際計算先以 max(vpin_n_buckets)=50 建立 sigma，再以第一個 bucket 30 的 VPIN 做 21-window z-score。直接依 metadata 的 period_keys 算 K 會漏掉該輸出真正使用的 30/50 依賴。

**碼證**: microstructure_indicators.py:108-112 對 VPIN 與 z-score 分別只登記 window；:260-288 顯示 sigma 使用 bucket 最大值、z-score 使用第一個 bucket 的 base VPIN。真實切片 probe 輸出 config={"vpin_n_buckets":[30,50],"vpin_zscore_windows":[21,55]}、metadata={"ms_vpin_zscore_21":{"window":21}}、first_finite_row={"ms_vpin_30":29,"ms_vpin_zscore_21":49}。
CODE-ANCHOR: momentum/FeatureEngineering/atomic/microstructure_indicators.py:111
MUTATION: 在隔離複本將 K resolver 的 input 限制為 MicrostructureIndicatorEngine.get_feature_metadata()["ms_vpin_zscore_21"]["params"]，再用真實 BTCUSDT 12h 1,696 根執行；觀測 params 仍只有 {"window":21} 而 engine 的 buckets 是 [30,50]，即重現輸出 provenance 漏依賴。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#7fac252e8abb; momentum/FeatureEngineering/atomic/microstructure_indicators.py#e497947a3f2; data_cache/feature_klines/kline_cache.h5#b1ee5b9abcc1

修法：把 period_keys 定義為產生該輸出值所需的完整遞移週期集合，要求 advanced metadata 對 z-score 輸出顯式帶出 base bucket 與 sigma bucket 的已解析值，並使 Task 2.4 的表鍵集合覆蓋這些依賴；若無法取得則在 L1 輸出前 fail-closed，不以欄名補推。不要以另一層事後遮罩掩蓋缺失 provenance。

可行性證據：現有 engine 已在同一物件保存 vpin_n_buckets、vpin_zscore_windows 並在一次 compute_all 中產生輸出，故可在 metadata/contract builder 補充已解析依賴，不必改變 VPIN 數值公式或欄數；probe 已給出可機械比對的 30、50、21 與首個有效列數字。這是 metadata/table schema 補強，並非已完成的實作證明。

## CODEX-R19-P1-03

**斷言**: v38 新增的 Task 2.3 test_ffstat_stable_start.py 與 Task 2.4 test_ffstat_warmup_table.py 驗收目前只出現在 SPEC；docs/manifests/FFSTAT.json 的 test_files（:9-15）與 batch_card.gate_cmd（:84）均沒有兩支測試。當前 tree 也沒有這兩個檔案；manifest 的 coverage prose 提到它們不等於 gate 會執行它們，因此 machine TODO 可在完全未跑 v38 新驗收時通過既有 gate。

**碼證**: docs/FFSTAT_SPEC.md:116 與 :123 是兩支 v38 必跑驗收；docs/manifests/FFSTAT.json:9-15 只有六支既有測試，:84 的 pytest 命令也只列那六支；git ls-tree -r --name-only bfb5ad83 -- tests/feature_engineering | rg 'test_ffstat_(stable_start|warmup_table)\\.py$' 無輸出。
CODE-ANCHOR: docs/manifests/FFSTAT.json:84
MUTATION: 在隔離複本建立一個必紅斷言於 tests/feature_engineering/test_ffstat_warmup_table.py 與 test_ffstat_stable_start.py，再逐字執行 manifest 的 batch_card.gate_cmd；因兩路徑未列入命令，pytest 不會收集它們，gate 對 v38 斷言失敗保持不敏感。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#7fac252e8abb; docs/manifests/FFSTAT.json#cea32416655f; handoffs/20260926-FFSTATAUTO-X-REVIEW-R19-BRIEF.md#f9dbe32c20ea

修法：在 SPEC 定案、實作派工前同步 manifest 的 test_files 與 gate_cmd，把兩支測試列為同一 machine gate；同步更新其 TODO 的 digest/receipt 依專案既有 manifest 流程。若某支確實暫不可執行，必須在 not_executable 以 owner、reason、expiry 明示，而不能只留在 coverage prose。

可行性證據：manifest 已有封閉的 test path 陣列與單一 pytest gate，修法只是增加兩個明確路徑與命令 token，不涉及數值、資料或 runtime 生成邏輯；上述必紅測試序列能直接驗證 gate 是否真的收集新驗收。現況檔案尚未落地，因此本輪沒有假稱該 gate 已重跑。

## CODEX-R19-P2-04

**斷言**: v38 對 period_keys=[] 的無參數輸出只說 K 取表內登記值，沒有定義 pattern engine 產生的 raw CDL、rolling frequency 與 Consensus 三類輸出如何各自映射到表項。現行 pattern metadata 對 raw CDLDOJI、CDLENGULFING 與 Consensus 都是空 params，warmup_table.yaml 只有全域 pattern_default_warmup_bars: 5，沒有對應的 output/derived provenance；實作者可在 K=0、全域 5、或 upstream max 之間作出不同但都看似符合文字的解釋。

**碼證**: pattern_indicators.py:38 以 {} 呼叫 raw CDL，:116 產生 raw output 的空 params metadata，:123-139 產生 frequency windows，:141-148 產生空 params 的 Consensus；warmup_table.yaml:387 只有 pattern_default_warmup_bars: 5。真實 BTCUSDT 12h probe 得 9 個 pattern outputs，其中 ohlc_pattern_CDLDOJI、ohlc_pattern_CDLENGULFING、ohlc_pattern_Consensus 的 params 為空。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#7fac252e8abb; momentum/FeatureEngineering/atomic/pattern_indicators.py#312a98ad227f; momentum/FeatureEngineering/atomic/warmup_table.yaml#d1fbdeae67c8; data_cache/feature_klines/kline_cache.h5#b1ee5b9abcc1

修法：在 Task 2.4 明定三種 mapping：raw CDL* 的 period_keys=[] 與其表內採用 K（若沿用預設 5，明寫它等於何處的表項）；frequency output 的 window key；Consensus 的 K 取其 upstream raw outputs 的最大 K。三者都列入 AST/output-point receipt，避免以空 params 推成無遮罩。

可行性證據：probe 已確認三類 output 的實際欄名、空 params 與現行 default=5，故可用純 metadata/table contract 加測試固定語意；不需更改 TA-Lib pattern 數值或產欄數。這是非阻塞的文字/驗收補明，未把現行尚未補表誤報為綠。

**必答（成對）**

1. **(1a)** 本家 R18 的 CODEX-R18-P1-01 與 CODEX-R18-P2-02 均已在原始範圍內閉合：§C:55 已寫出 TA-Lib／advanced／custom 的逐 output-column params、period_keys、缺鍵 fail-closed、AST 對證；Task 2.3:123 已寫 12h 對 ConfigManager 啟用集合之每個 L1 output point 與每組 resolved params，receipt 列已驗/未驗，blocked 只豁免雙起點。R18 的 COMPOSER-R18-P2-01 也已由 Task 2.4:115-116 明列每指標 period_keys 與 resolved-key superset fail-closed；它不是本家 CLOSED ID，因此不列入末段 CLOSED。
2. **(1b)** 以 rg -n 'L1 輸出點契約|12h 逐輸出點|period_keys' docs/FFSTAT_SPEC.md 與本輪真實 probe 核對：條文採納成立；原 params={} 反例在目前未實作 v38 的 code 仍被接受，這暴露本輪 P1-01 的 ABI/validation 缺口，不是把「文字已採納」誤報成「實作已通過」。本輪未跑 full FF，故不宣稱全路徑綠。
3. **(2a)** v38 有新缺陷：P1-01 custom declaration/return ABI 未定義、P1-02 advanced transitive period provenance 不封閉、P1-03 machine manifest gate 漏列新驗收；P2-04 pattern raw/derived output 的無參數 K mapping 未定義。
4. **(2b)** 真實操作序列為：在 /tmp/ffstat-r19-run 複本執行 inspect_l1_contract.py 讀 data_cache/feature_klines/kline_cache.h5 的 BTCUSDT/12h 前 1,696 根。輸出重現 custom short=4/long=232、micro metadata 只帶 21 但 buckets 為 30/50、pattern 9 outputs 且三欄 params 為空；另以 git ls-tree 與 manifest gate command 對照重現 P1-03。
5. **(3a)** assumed ①「只加逐欄 mapping/mask、不改 schema/ABI 即可涵蓋所有 custom/advanced」不成立；custom 必須新增 declaration 或 structured-return contract，microstructure 還需補遞移依賴。assumed ②「v38 契約要求 params={} fail-closed」文字上成立，但「現行介面已能做到」不成立；本輪實跑的 params={} custom 仍成功回傳兩欄，故必須先補 validation/ABI 才能驗收。
6. **(3b)** ①的碼證為 feature_config.py:451-457、custom_indicators.py:12-33、feature_factory.py:991-998 與 probe 的 2 欄/1696 rows；②的碼證為同一 probe 與 v38 Task 2.3:123 的明文負例。micro 的數字為 metadata window=21、config buckets=[30,50]、first finite rows 29/49。
7. **(4a)** ①未命中可列為 finding：本輪真實 12h probe 中 entropy 為 15/15 output↔metadata、tail-risk 為 26/26，均無 missing metadata；這不是對未測內部依賴的全面保證。②命中：microstructure 有遞移依賴缺口，pattern 有 raw/derived 無參數 K mapping（P1-02、P2-04）。③沒有取得 full default 12h all-L1 的 8 GB 耗時結論；選定六類 engine 的 probe 只在約 9.8 秒完成，不能外推全設定。12h 驗收屬 acceptance test，未將它當生成期 recurring check。
8. **(4b)** ①命令為 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat-r19-run/numba PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python inspect_l1_contract.py，輸出上述 15/15、26/26；②同命令輸出 micro/pattern 欄級摘要，並由 nl -ba 核對 microstructure_indicators.py:108-112,260-288、pattern_indicators.py:38,84-148 與 warmup_table.yaml:387；③ h5py slice 顯示 BTCUSDT/12h rows=1696，coverage probe 顯示 total_indicators=76 in_table=37 missing=39，沒有跑全設定生成。
9. **(5a)** 不可 VERDICT: proceed；擋項是本輪 P1-01、P1-02、P1-03，因它們分別使 custom fail-closed、advanced K provenance 與 v38 machine acceptance 仍不可驗收。
10. **(5b)** 只列 blocking P0/P1：CODEX-R19-P1-01、CODEX-R19-P1-02、CODEX-R19-P1-03；P2-04 不列入 BLOCKED-BY。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、本輪 brief、r18 synth、R1–R7 rulings、target diff、template 與 governance verdict values；已以 nl -ba／rg 核對 v38 §C:55、Task 2.3:123、Task 2.4:115-116、manifest:9-15/84；已在 /tmp/ffstat-r19-run 以真實 HDF5 12h slice 驗證 1696 rows、custom 2 欄、micro 30/50/21 依賴、pattern 9 欄、entropy 15/15、tail-risk 26/26；未宣稱 full FF 或全設定成本已驗證。
TESTS_RUN: git diff --no-ext-diff --unified=0 5551dc5b bfb5ad83 -- docs/FFSTAT_SPEC.md → 僅 v38 版本註記、§C output-point contract、Task 2.4 period_keys、Task 2.3 12h/custom acceptance；PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/ffstat-r19-run/numba PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python inspect_l1_contract.py（cwd /tmp/ffstat-r19-run）→ rc=0，輸出上述實測摘要；同環境執行 20260927-warmup-table-coverage.py → total_indicators=76 in_table=37 missing=39；git status --short -- momentum api scripts tests docs templates config 與開跑 snapshot 相同；test -e /tmp/claude-501 → present；bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r19-codex.md --family codex --round-id f5529faa-db13-406a-8ee5-356b4cf4dc22 → rc=0，COMPLETENESS PASS(single)，4 個 canonical ID。未跑 full pytest/full FF 或修改受保護檔案。
FAILURES_SEEN: brief 要求所有實跑在 /tmp；本輪最初曾從 repository root 直接執行一次既有 coverage script，屬 read-only 輸出探查，之後才建立 /tmp/ffstat-r19-run 複本並重跑所有本輪 probes；此合規偏差與實際輸出在此列明。沒有發生 probe 的 PreToolUse hook denial，也沒有以改寫命令繞過 hook。收尾原命令 rm -rf -- /tmp/ffstat-r19-run 被環境 safety guard 拒絕（rm -f style commands are not permitted）；未改寫成其他清理形式。
SCOPE_CHANGES: none；只寫本輪指定 committee artifact，並對既有同 task status handoff 做 append-only 狀態追加；未改 source、SPEC、manifest、template、CLAUDE、git history 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 未實作任何數值或輸出變更；P1-01 修法會新增 custom output declaration/structured-return ABI，P1-03 修法會新增 machine gate 測試路徑，均為待核准 contract/manifest 變更；本輪 probe 只讀真實 HDF5，未改欄數、欄值或測試門檻。
TMP_CLEANUP: rm -rf -- /tmp/ffstat-r19-run 被環境 safety guard 拒絕，故 workdir 仍在；未執行替代刪除命令。/tmp/claude-501 已確認存在並保留。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r19-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R19.md（既有 composer 狀態檔，僅 append codex 狀態）

VERDICT: blocked
BLOCKED-BY: CODEX-R19-P1-01,CODEX-R19-P1-02,CODEX-R19-P1-03
CLOSED: CODEX-R18-P1-01,CODEX-R18-P2-02
STATUS: DONE
## COMPOSER-R19-P3-00

**斷言**: 本輪逐項核對 v38 差分與 r18 採納修法後，未發現新的 P0／P1 SPEC 缺陷；r18 三家採納之三條在 v38 正文已對位閉合。

**碼證**: `git diff 5551dc5b bfb5ad83 -- docs/FFSTAT_SPEC.md` → 40 行，僅 §C「L1 輸出點契約」、Task 2.4 `period_keys` 交付／驗收、Task 2.3 ① 之 12h 逐輸出點與 `params={}` 自訂指標 fail-closed；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n 'L1 輸出點契約|12h 逐輸出點|period_keys' docs/FFSTAT_SPEC.md` → §C:55、Task 2.4:115-116、Task 2.3:123 同輪採納字面齊；`PYTHONPATH=. venv/bin/python -c "from tests.feature_engineering.ffstat_helpers import kline_frame; print(len(kline_frame('BTCUSDT','12h')))"` → 1696；`entropy_indicators.py:88-106`、`tail_risk_indicators.py:66-91` 皆具 `get_feature_metadata` 欄級 `params`（對齊 §C microstructure 範例）；`atomic/warmup_table.yaml:387` `pattern_default_warmup_bars: 5` 與 Task 2.4「無參數指標 `period_keys` 空集合、K 取表內登記」一致。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#7fac252e8abb; handoffs/reconcile/20260926-ffstatauto-x-review-r18/synth.md#e0710db20b29

---

