# Reconcile — 20260926-ffstatauto-x-review-r22

**來源** 20260926-ffstatauto-x-review-r22-codex.md, 20260926-ffstatauto-x-review-r22-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 12h 資格仍可能不足：v41的`M_tf=K_max_tf`尚 | P1 | CODEX-R22-P1-01 | 採納（§G⑦：收據必記實測 F_max_12h、各欄首個有限值、`6,656−(M_tf＋F_max_tf＋500)` 與資格結果；仍不合資格時不得自行 blocked 收案，交使用者三擇一裁定〔改資格／允許 blocked／另取更多真實資料〕——F_max 須實作後實跑方可得，主委之窗長推估〔約 5,366〕不作收據） | code-contract |
| 係數 mutant 目標不封閉：§G⑦的「倍數表某recursive指標 | P1 | CODEX-R22-P1-02 | 採納（§G⑦：係數 mutant 固定為 ADXR 233〔`period_keys`＝timeperiod〕，收據列 mutant 前後之 K、首個有限值、重疊列數與 normalized error；並記 EMA 5 係數偏小之偏差 0.0011 < 0.005 本即低於判準，屬判準設計界線） | code-contract |
| 零 finding：本輪逐項核對v41差分（§G⑦`M_tf | P3 | COMPOSER-R22-P3-00 | 採納（composer 判 proceed；無修訂） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R22-P1-01

**斷言**: v41 的 `M_tf=K_max_tf` 尚未閉合 `CODEX-R21-P1-01`：`N < K_max_tf+F_max_tf+500` 的 blocked 分支仍存在；只要真實 A run 的 `F_max_tf >= 4,106`，BTC/12h 的 6,656 根仍必須 blocked，與同一條「12h 不得以 blocked 收場」互斥。

**碼證**: `docs/FFSTAT_SPEC.md:91` 同時保留 `M_tf=K_max_tf`、`F_max_tf` 資格式與 12h 不得 blocked；真實長歷史讀取命令 `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -c '...h5py...BTCUSDT/12h...'` 輸出 `ROWS 6656 FIRST 1502928000 LAST 1790467200`。因此 `6656-2051-500=4105` 是可機械重算的臨界值。brief:22 已記錄實際 F_max_12h 超過該臨界值；本輪允許的廉價 probe 只得到 `_collect_l*_warmup_bars=[2051,233,233,34,0,55,500]`、`SUM=3106`、`QUALIFY_PROXY=5657`，這是窗長 proxy，不是 §G 要求的 A 逐欄首有限值 F_max，不能冒充收斂收據。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:91
MUTATION: 將真實 BTCUSDT/12h 6,656 列固定為輸入，令 A 收據的 F_max_tf=4,106；依 §G⑦ 計算 6,656 < 2,051+4,106+500=6,657，應輸出 blocked，若套用「12h 不得以 blocked 收場」即產生矛盾。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#976f6c4f47d7; handoffs/20260926-FFSTATAUTO-X-REVIEW-R22-BRIEF.md#0b6c69021887; handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md#edb13160501f; handoffs/run_receipts/20260927-ffstat-longhist-download.log#960155b7fe59

修法：保留 `M=K` 的收斂論證前，必須把真實 A run 的 `F_max_tf`、逐欄首有限值、`N-(K+F+500)` 與 blocked 判定寫入收據；若結果仍超過 6,656，需由使用者裁定「改資格／允許 blocked／取得更多真實資料」其中一項，不能以 layer-window proxy、刪欄或補值關閉。可行性證據：臨界算式與 6,656 列已由上列命令實跑，且 `cache_dir` 注入 probe 能讀同一長歷史 HDF5；修正是收據／條文對位，不需新增生成期機制。

## CODEX-R22-P1-02

**斷言**: §G⑦ 的「倍數表某 recursive 指標係數改為 1.0」沒有固定指標、period、output 或 `period_keys`，因此 mutant 是否變紅取決於任意選擇；真實 1h BTC 下 EMA(5) 目標不紅，但 ADXR(233) 目標變紅。

**碼證**: `config/scan_config.yaml:37-40` 啟用 EMA period 5，`:135-136` 啟用 ADXR period 233；`warmup_table.yaml:106-109` 的 EMA factor 為 1.44，`:25-28` 的 ADXR factor 為 8.8。以真實 `data_cache/feature_klines/kline_cache.h5`、`M=2051`、B 首個有限值起取 500 列並沿用 0.005 scale-normalized gate：EMA5 命令輸出 `ROWS 20352 ... normalized 0.0011543999770815896 red False`；ADXR233 命令輸出 `... normalized 0.1053480870298399 red True`。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:91
MUTATION: 將「某 recursive 指標」具體替換為 EMA period=5，將其 warmup factor 由 1.44 改為 1.0，對真實 BTCUSDT/1h 的 B 首 500 個 finite rows 執行 §G⑦ 比較；normalized=0.0011544 < 0.005，必要 mutation 不紅。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#976f6c4f47d7; config/scan_config.yaml#0dc95e4f0a10; momentum/FeatureEngineering/atomic/warmup_table.yaml#d1fbdeae67c8; handoffs/20260926-FFSTATAUTO-X-REVIEW-R22-BRIEF.md#0b6c69021887

修法：把 mutation 寫成封閉清單，至少固定 `indicator=ADXR`、`period=233`、輸出點與 `period_keys`，並在收據列出該列 mutation 前後的 K、首有限值、重疊數與 normalized error；若要測 EMA，另列 EMA5 並承認它在此 gate 下可能不紅。可行性證據：同一真實 1h 命令已顯示固定 ADXR233 會紅、EMA5 不會紅，故加入明確 target 與 expected red/非 red 結果即可消除選擇歧義，不需放寬 gate。

(3a)/(3b) assumed 判定：①「預設全設定 BTC/12h 6,656 根資格必可滿足」判不成立；v41 的 proxy 窗長不是 F_max，且 brief 的否證觀測使臨界式仍可能 blocked。②「四個 mutant 皆必紅」判不成立；本輪對 recursive mutant 實跑 EMA5 得 `red=False`，同一輸入換 ADXR233 才 `red=True`。

(4a)/(4b) 未查項複核：① cache_dir concern 未命中於 storage layer；`create_feature_factory(cache_dir="data_cache/feature_klines_longhist", validate_continuity=False)` 的 adapter probe 實讀 `ROWS 6656`。但 verifier 目前 `scripts/verify_l1_warmup_requirements.py:49-50` 固定一般快取，`--tf` CLI（`:369-388`）沒有 cache-dir 參數；依 r21 範圍判定，這是 Task 2.4 施工接線前提，未另列本輪 finding。② 5m 105,260 根只核對收據列數，未跑全量 memory/time，沒有可重現命中。③ ADA 12h 實讀 `6171`、BTC/ETH 各 `6656`；SPEC 已定跨標的取最大，未跑完整倍數腳本，沒有新 finding。

(5a)/(5b) 本版不能 `proceed`；擋項只為本檔兩條 P1：資格／不得 blocked 的未閉合契約，以及 recursive mutation target 不封閉。r21 的 P2-02 逐字核對：`rg -n '^  - 12h 校準長度|blocked-by：需更長之真實 12h 歷史' docs/FFSTAT_SPEC.md` 輸出 `NO_SECTION_N_12H_RESIDUAL`，故列為已閉合。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、本輪 review brief、v41 target diff、r21 synth、使用者 R1-R9 ruling、template 與 finding category allowlist；已實讀真實 BTC/ETH/ADA 12h rows、cache_dir 路徑、default warmup proxy、1h EMA5/ADXR233 mutation gate；確認 r21 P2-02 閉合，r21 P1-01 未閉合。
TESTS_RUN: `git diff 38ca2137 834f41af -- docs/FFSTAT_SPEC.md` → 1 file, 8 lines (4 additions/4 deletions); real longhist h5py probe → BTC/ETH 12h=6656, ADA 12h=6171; cache_dir factory/adapter probe → `ROWS 6656`; verifier `load_klines("BTCUSDT","12h")` → normal-cache `ROWS 1696`; warmup probe → `LAYERS [2051,233,233,34,0,55,500] SUM 3106 QUALIFY_PROXY 5657`; real 1h EMA5 probe → normalized `0.0011543999770815896`, `red False`; real 1h ADXR233 probe → normalized `0.1053480870298399`, `red True`; residual grep → `NO_SECTION_N_12H_RESIDUAL`; exact required `bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r22-codex.md --family codex --round-id 39e0702d-5a59-44bb-a2b5-ad0605e63211` → `COMPLETENESS PASS(single)`, rc=0.
FAILURES_SEEN: 初次 ConfigManager probe 讀不存在的 `IndicatorDef.combos` 屬性而 `AttributeError`，改用 `model_dump()` 後完成，未改 source；初次 storage 檔案路徑誤指 `momentum/FeatureEngineering/data/` 而讀不到，改讀 `momentum/DataExtraction/kline_storage.py`，未改 source；依 brief 禁止未跑全設定 FF run，故未把未實跑的 F_max 當成已驗證數字；收尾原命令 `rm -rf -- /tmp/ffstat-r22-2iBfeK` 被 PreToolUse 安全閘拒絕，未改寫命令形式。
SCOPE_CHANGES: none；唯讀審查，只寫本指定交件檔與 append-only 狀態交接，未改 source、SPEC、manifest、templates、CLAUDE.md、git history 或 data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: none；未修改數值、schema、輸出大小或測試斷言。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r22-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R22.md
TMP_CLEANUP: 嘗試 `rm -rf -- /tmp/ffstat-r22-2iBfeK` 被環境安全閘拒絕；快照仍約 858M，`/tmp/claude-501` 約 150M 且已確認保留；未以其他命令形式繞過。
STATUS: DONE

VERDICT: blocked
BLOCKED-BY: CODEX-R22-P1-01,CODEX-R22-P1-02
CLOSED: CODEX-R21-P2-02
## COMPOSER-R22-P3-00

**斷言**: 本輪逐項核對 v41 差分（§G⑦ `M_tf＝K_max_tf`、§A 交易所缺口、Task 4.1 12h N 一致率、§N 刪 12h 1,696 殘留）與 r21 採納修法對位後，未發現可重現之新 P0／P1 SPEC 缺陷；r21 之 `CODEX-R21-P1-01`／`CODEX-R21-P2-02` 在 v41 條文層已閉合。

**碼證**: `git diff --stat 38ca2137 834f41af -- docs/FFSTAT_SPEC.md` → 4 insertions／4 deletions；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`nl -ba docs/FFSTAT_SPEC.md | sed -n '91p'` → `M_tf＝K_max_tf` 且資格仍為 `M_tf＋F_max_tf＋500`（v40 之 `K＋2F＋500=7,155` 互斥已解除）；`nl -ba docs/FFSTAT_SPEC.md | sed -n '180p'` → 無 1,696 blocked 殘留（§N 末行為範圍外 winsor 說明）；`env PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat-r22-work/eligibility_r22_probe.py` → `btc_12h_rows=6656`、`estimate_max_warmup_bars_12h=2051`、`required_rows_M_plus_F_plus_500=4853 pass=True`、`overlap_worst_case_tail=4354 pass_500=True`、`row_margin=1803`；`handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md` 處置與 v41 版本註記一致；brief fact `dead_feature_filter.py:77-82`（`notna().sum`／`nunique`）、`talib_wrapper.py:316,347` 逐字成立。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#976f6c4f47d7; handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md#r21; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0; handoffs/run_receipts/20260927-ffstat-longhist-download.log#download6656

---

