# FFSTAT B6 review R2 — codex

審查標的：`d3c8d339`、SPEC v60 Task 4.2、manifest、四支 MR 測試與共用 helpers、r1 收斂及前置實跑收據。結論：本家 r1 三條閉合；新捕獲器與實際 gate 訊息不一致，修正前不宜啟動約 6.5 小時全跑。本輪未跑生成型 node，亦未宣稱 Task 4.2 驗收完成。

## CODEX-R2-P1-01

**斷言**: `_expect_causal_gate_failure` 拒收三種實際因果 gate 失敗（warmup mask、fracdiff atol values、metadata），因此正確抓到 mutant 的控制仍可被判紅；brief assumed ③ 不成立。

**碼證**: helpers:903-908／931-936 傳入 `context=f"warmup {fname}::{col}"`，實際為 `warmup 1h_L3.parquet::close_fracdiff NaN mask mismatch`，不是白名單的 `warmup NaN mask`；helpers:1036-1042 使用 `np.testing.assert_allclose(..., err_msg="fracdiff values ...")`，實際訊息先是換行＋`Not equal to tolerance rtol=0, atol=1e-08`，lstrip 後仍不是 `fracdiff `；helpers:1061-1093 的 metadata assertions 多數無訊息，其他以 `present_timeframes missing`／`config_used.timeframes.training missing` 開頭，均不是 `metadata gate`。複本命令 `PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat_b6_r2_check/probe.py --collect` rc=0：呼叫原 gate 取得三個 AssertionError，再餵原捕獲器，三者均 `REJECT`；主 values 與 d_star 正例 `ACCEPT`；準備／coverage 反例 `REJECT`。
CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:1520
MUTATION: 在隔離複本建立 full parquet `close_fracdiff=[0,1,2]`、trunc parquet `[NaN,1,3]`，直接呼叫 `_assert_warmup_nan_masks_equal(...,warmup=1,n_trunc=3)` 與 `_assert_values_gate(...,warmup=1,n_trunc=3,atol=1e-8)`；另以 manifest symbol A／B 呼叫 `_assert_metadata_gate`；將各原生 AssertionError 訊息交給 `_expect_causal_gate_failure`（秒級探針只略過其準備步驟，以單獨測捕獲邊界），三者皆被當成非因果 gate 拒收。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#9c98ca5e8002

**類別**: code-contract

影響：serial／parallel 長度耦合截斷控制允許 fracdiff values 失敗，卻不能收下原 atol gate 之真實訊息；其他控制若先在 warmup mask 或 metadata 抓到差異，同樣假紅。這是可重現的捕獲契約缺陷，不代表某一生成型 node 已實跑失敗，也不是假綠。尾擾動 fracdiff 控制仍須拒收 values，不受本修法放寬。

修法：在既有 gate 補一致的因果診斷標籤，保留原斷言與數值容差；warmup 白名單與原 `warmup <file>::<column>` context 對齊；atol gate 捕獲其 `np.testing.assert_allclose` 的 AssertionError 後以 `fracdiff values gate failed: ...` 重拋；metadata 每個 assert 補 `metadata gate failed: ...`。這需要明示擴大「既有 helpers gate 不改」的 scope 到診斷訊息，不增加機制、不改 gate 判準、不把 numpy 的通用 `Not equal to tolerance` 廣泛加入白名單。

修法可行性：同命令 rc=0，僅於 `/tmp` 探針將 metadata 函式 AST 的 assert message 補標籤、用 wrapper 為原 numpy AssertionError 補 fracdiff 標籤、warmup allowed prefixes 改為 `warmup `；同三個失敗皆輸出 `FIX_FEASIBILITY ACCEPT warmup/atol/metadata`。原 gate 仍因相同輸入拋 AssertionError，容差與比較內容完全保留。此為秒級診斷修法證據，不是完整生成驗收。準備檢查在捕獲區外之結構維持，sampling／coverage 反例仍不可作 mutant 成功。

## 必答 (1a)／(1b)：本家 r1 閉合

- `CODEX-R1-P1-01`：閉合。原真實窗反例重算為 3342／3332；舊 capped 公式兩邊 252，新 uncapped 公式 334／333。helper:1713-1716 記錄 resolver 結果，1733-1737 在捕獲區外要求不同 max_lag 與 parallel seam。探針輸出 `REAL_KLINE 20352 window 3342 lags [334,333]`；若 cap 漂回，`len(lags)>=2` 會直接紅。未宣稱數值鑑別力已生成驗證。
- `CODEX-R1-P1-02`：閉合。以同真實 K 線與解析 start，`_patch_kline_pre_start_ohlcv` 改到 17010 列前史、公開域起始日及之後改動 0 列；探針斷言 changed positions 與 `_pre_start_rows` 完全一致。helpers:1741-1766 的 full-only patch 以起始日前史為範圍，校準 seam／前史列数檢查在捕獲區外。這閉合「零校準列被改」原反例，不保證 d* 一定變。
- `CODEX-R1-P1-03`：閉合。分母控制已撤除，保留控制的 pair 建立、seam、preparation 均在捕獲區外。秒級原缺 L4 訊息反例輸出 `PREPARATION propagated mutation layer coverage failed (sampling design error): missing L4`；因果值／d* 正例被收，coverage／sampling 反例被拒。新 P1 是診斷不相符造成假紅，與原準備錯誤冒充成功的缺陷不同。

## 必答 (2a)／(2b)：assumed 及未查面

① 擾動起始日之前全部前史的設計可接受：只證校準或欄集合敏感，且捕獲器只承認 strict columns／d*。本輪實測時間範圍成立；factory:2408-2420、adapter_registry fetch 路徑與 full-only patch 可使校準前史受擾動。生成是否拋 CalibrationError、是否成功改變 d* 未驗證；那些錯誤在 pair 建立時傳出，不能假裝抓到。公開域預熱也改動屬已揭露邊界，公開 values 差異不能被此控制承認。

② 全量 d* mutant 必讓兩 run d* 不同：未驗證，不能以差 10 根推論。feature_preprocessor:3407 的 statsmodels ADF 只讀前 N 根，`_fast_adf_numba.py:114-119` 同樣取前 N；尾截斷未必改這個判定窗。`_hurst_prior.py:197` 的 prior 仍讀全序列，因此不能僅由前 N 一樣斷言 d* 必同。現有控制只收 strict columns／d*，若兩者皆相同將紅而非假綠；實際鑑別力須由允許的後續獨占生成收據判定，本輪沒有生成證據。

③ 不成立：原 gate 真實訊息反例與修法可行性見 P1-01；合成四訊息正反例不足以證所有實際 gate 可被辨識。

未查 1：逐函式對照完成，結果為 P1-01。main values `values ...`、columns 與 d_star 前綴對得上；warmup、numpy atol 與 metadata 對不上。align oracle 在控制的捕獲區外，未把「沒有偵測到粗週期差異」當成功。

未查 2：對照 `git show d3c8d339^:<兩既有檔>` 的控制與現行共用本體：L3 center、全量縮尾、L4 反向 shift＋尾擾動、trunc-only align ＋1、對齊 oracle 及預期 TF 清單保留；變更為本輪明示的準備與捕獲邊界、lag 去 cap、前史擾動與 fracdiff 接受 gate 收窄。FULL_MULTITF_SCOPE 的 fracdiff_payload 雖填 values payload，現行多週期五個控制全走 `fracdiff=False`，沒有誤用；不宣稱其適合未來 fracdiff 控制。

未查 3：334／333 不超過實作的固定限制：`_get_weights_ffd(max_width=lag)` 接受任意正寬度並在該宽度終止；`_frac_diff_ffd` 有有效序列不足則全 NaN 的明確分支。秒級實跑兩值之權重計算均成功。它們小於本設定明示校準 500 根與解析窗長；深欄有限值／整體生成成功仍未驗證。

未查 4：與改前一致。舊 align 兩控制明示 `_bar_window_dates_at_12h_boundary`，其他控制使用 builder 預設 `_bar_window_dates`；共用本體保留相同選窗。正常 multi baseline 的 builder 也用預設窗。SPEC「窗末落 12h」應按對齊控制的顯式選窗理解；未據此擴成其他 baseline 均有邊界保證。

## 必答 (3a)／(3b)：可否全跑

否。擋項只有 `CODEX-R2-P1-01`。這是已重現的秒級捕獲診斷問題，先修能避免生成完成後因錯誤前綴白花數分鐘至數十分鐘。①② 的實際 mutant 鑑別力仍屬後續全跑驗收，沒有捏造成已知失敗或額外慢閘。縮小 multi 不含 12h、未選指標／市場／參數亦不在其覆蓋聲明內；審查結論沒有將方法限定於加密貨幣。

## 實跑與隔離紀錄

命令：`PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat_b6_r2_check/probe.py --collect`，rc=0；先呼叫複本 `_isolate.isolate()` 與 `isolate_dstar_cache()`，匯入複本 momentum／tests。真實 HDF5 以來源絕對路徑唯讀讀取。小數值 parquet 僅供 brief 允許的捕獲邊界訊息探針，不作 Feature Factory 正確性或生成證據。

輸出摘要：`REAL_KLINE 20352 window 3342 lags [334,333] pre_start_changed 17010 public_changed 0`；warmup／atol／metadata 原捕獲器均 REJECT；values／d_star ACCEPT；coverage／sampling REJECT；準備缺 L4 傳出；診斷修法三例 ACCEPT。四檔 `--collect-only --noconftest -q -p no:cacheprovider` → `41 tests collected in 0.06s`。`--noconftest` 僅用於收集，不用於生成驗收。

隔離複本初次 tar 包含不存在的 pyproject.toml 而 rc 非零；已提取的程式碼完整。初次 collect 啟用 tests/conftest 因複本未含 scripts.build_l65_golden，inventory 常數為 None 而 INTERNALERROR rc=3；改用上述純收集命令後 rc=0，沒有修改 repository 或既有測試來通過。

`git status --short -- momentum api frontend tests templates config` 前後存檔，以 `diff -u /tmp/ffstat_b6_r2_check/status_before.txt /tmp/ffstat_b6_r2_check/status_after.txt` 實跑 rc=0、無差異；保留既有 dirty 檔。根 HANDOFF.md 未修改。

ASSUMPTIONS_VERIFIED: 真實前史擾動範圍、窗長與 lag 算術、權重寬度可解析、捕獲真訊息反例與診斷修法；依上方 probe 命令 rc=0。
TESTS_RUN: 上方 probe＋collect rc=0，41 collected；status diff rc=0；指定 completeness 命令之結果見交件收尾。
FAILURES_SEEN: 複本 tar 不存在 pyproject.toml；首輪 collect 缺 inventory 模組 rc=3，純收集修正後 rc=0；原因果診斷誤拒收為未修 P1-01。
SCOPE_CHANGES: repository 生產碼、測試、SPEC、manifest 均未修改；提出診斷訊息 scope 擴大。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_NOT_UPDATED: 本輪唯讀，僅寫明示交件；沒有另寫狀態交接或改根 HANDOFF.md。
產出：`handoffs/20260926-ffstat-b6-review-r2-codex.md`。暫存清理只涉及本輪建立的 workdir，保留 `/tmp/claude-501` 及其他程序目錄。

VERDICT: blocked
BLOCKED-BY: CODEX-R2-P1-01
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03
