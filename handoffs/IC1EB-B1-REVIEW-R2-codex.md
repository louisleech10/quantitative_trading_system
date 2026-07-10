# IC 1e+1b B1 R2 複驗（Codex）
日期：2026-07-10；範圍：R1 原反例、FIX1、oracle/M-A 自家 receipt；未改受審碼/data_cache。
STAMP：CLOSED — `bash scripts/reconcile_body_hash.sh handoffs/IC1EB-RECONCILE.md`=`b77932d811a9…`，codex/composer APPROVED 雙章同 hash。
D-B paired bootstrap：CLOSED — `block_bootstrap.py:111-115` 同一 `idx` 取 `x[idx],y[idx]`，每輪 `_spearman_ic` 重 rank。
D-B 原反例 receipt：`x=[1,2,3],y=[1,3,2],idx=[0,1,1]`；fixed-z=`0.33333333333333331`，paired-rerank=`0.66666666666666685`，斷言不相等通過。
邊界測試：CLOSED — `test_t13_boundary_n_lt_2block_skips` 與 `test_t13_boundary_all_equal_rank_degenerate` 均在 targeted pytest 通過；分別斷言 `n<2*block`、`rank_degenerate`。
oracle allclose：CLOSED — 單執行緒獨立腳本檢 5 組；`rtol=1e-8,atol=0`，最大絕對誤差 `se=5.55e-17,t=1.78e-15,p=3.12e-17`。
M-A 假陽率：CLOSED（允許的 50-seed 抽驗）— seeds `10000..10049`，binomial 95% 帶 `[0,6]`；舊法 `20/50=0.400`，HAC `3/50=0.060`，兩條斷言通過。
真紅 receipt：STILL-OPEN — FIX1 自報 production `t×2` 得 exit=1；本委員執行期注入同 mutation 後重打主同判斷言兩次，皆未在 40s 內產生輸出，依兩輪上限停止，不能把自報升格為獨立 receipt。
source clean probe：CLOSED — `statistical_validator.py:142` 仍為 `t_stat = float(mean_z / se)`；無 `*2` mutant 殘留。
驗收 gate：STILL-OPEN — `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q` 兩次分別約 160s/70s 無完成摘要後終止。
拆分 receipt：排除 M-A 的同 gate=`77 passed,1 deselected in 2.46s`；oracle+合法 maxlags+T-1.3 主測+兩邊界=`5 passed in 1.79s`；不得冒充完整 78 passed。
測試碼事實：`test_t11b_ma_ar1_false_positive_size` 仍硬寫 `n_seeds=200` 且帶 `(4,16)`；派工所述 50-seed 版本未寫入該 pytest，僅能用獨立腳本抽驗。
inventory：`tests/golden/l65/test_inventory.txt` git status 無變更，當前 hash `f7b2e859006a071fdc6fd24d51554124de26a995`；無需 restore。
ASSUMPTIONS_VERIFIED: paired rerank 路徑、兩邊界、statsmodels use_t oracle、50-seed M-A、production 無 mutant。
TESTS_RUN: 上述完整 gate×2（無 receipt）；77-item split PASS；5-item targeted PASS；oracle/M-A 腳本 PASS；t×2 動態重打×2 無 receipt。
FAILURES_SEEN: 無 assertion failure；阻塞為完整 gate 與獨立真紅重打無法完成，且已達兩輪上限。
SCOPE_CHANGES: 僅新增本檔；未改受審碼、測試、pytest.ini、inventory 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 本委員無變更；FIX1 僅測試側 bootstrap 分布算法改為 paired rerank，production schema 無變更。
VERDICT: BLOCK（完整 78-item gate 與本委員真紅 receipt 均未取得；不得以實作者自報或拆分綠替代）
