# Reconcile — 20260910-evtlabel-x-review-r3

**來源** 20260910-evtlabel-x-review-r3-codex.md, 20260910-evtlabel-x-review-r3-composer.md, 20260910-evtlabel-x-review-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**輪次計數**：codex 4（4×P1）、composer 2（2×P2）、grok 5（2×P1、3×P2）＝ **11 條**；P0＝0。
D1–D8 判定：composer 全 CLOSED；grok D2 在 TODO I/O 面 NOT-CLOSED（殘句）、其餘 CLOSED；codex D1（殘 digest 句）／D2（q95 語意）／D4（雙實作）NOT-CLOSED。
Verdict：composer **可派工**；grok **修兩殘句後可凍結**；codex **修 P1-01/02/04 後可凍結**。三家一致：P1／P2 可凍結進 B0；主目標不延後。

Verdict: 需修補後合併（E1–E5 皆為文件層修訂，已於本輪同步寫入 v4；R4 不再開全審，改序列化戳記輪由三家對 v4＋三份 synth 一併核可）

---

### E1 — 殘留 digest 消費指令（D1 未閉之字面殘句）
**ID**：`CODEX-R3-P1-01`、`GROK-R3-P1-02`
**處置**：M-P3-5 改為「替換 `ValidatedBinaryLabel` ⇒ 三守衛 raise，無 digest 比對」；TODO 3.6 SPEC ref 句改「三守衛」；全文 grep `digest 對證／比對／重算 digest` ＝ 0。

### E2 — 負對照 q95 語意與 N；`n_observed=0` 短路；TODO I/O 殘句
**ID**：`CODEX-R3-P1-02`、`GROK-R3-P1-01`、`COMPOSER-R3-P2-01`、`GROK-R3-P2-01`
**處置**：`N=50`（config `negative_control_n`）、`q95=int(np.quantile(counts,0.95,method="higher"))`（整數 order statistic）；`n_observed==0` 先短路 `skipped:no_survivors`，不標 failed；TODO 3.7 I/O 句改寫為與要點 4／SPEC 同鍵同比較符（刪 `>0` 與舊鍵名）。

### E3 — 負對照成本無獨立閘；NaN 逐欄迴圈 8.9s/次
**ID**：`CODEX-R3-P1-03`
**處置**：Task 3.5 改 `mannwhitneyu(..., axis=0, nan_policy="omit")` 單次向量化（scipy 1.13.1），**禁**逐欄 python 迴圈；Task 3.7 驗證新增負對照 benchmark 閘：39,373×31、N=50、clean 與 10% NaN 兩形狀皆 `< 120s` 否則 FAIL（獨立於 per-survivor 置換 benchmark）。

### E4 — D4 預檢雙實作；mismatch 容忍流
**ID**：`CODEX-R3-P1-04`、`COMPOSER-R3-P2-02`、`GROK-R3-P2-02`
**處置**：新純函式 `momentum/core/split_preview.py::holdout_test_row_index(n_rows, *, oos_test_size, purge_gap, embargo)`；orchestrator `_build_holdout_split_plan` 之 `test_rows` 與 service 預檢**皆**呼叫它；`effective_horizon` 由 service 以 `_resolve_effective_label_horizon` 同源解析；預檢與 stage3 不一致 ⇒ raise（同函式同輸入不一致＝bug），不容忍揭露流；`tests/momentum/core/test_holdout_test_row_index.py` 對證受理 run test 段。

### E5 — 保 index 之值列重排殘形（不加 value-digest）
**ID**：`GROK-R3-P2-03`
**處置**：Task 3.6 驗證段具名殘形＋祈使句「對證後直接餵入」＋靜態守衛（`inspect` 斷言對證與 `mann_whitney_table` 呼叫間無 `X =` 再賦值）。

---

### §0 假設裁定
- 20 次置亂 q95 充分：**推翻**（codex：離散尾部解析度不足＋`np.quantile` 插值）⇒ E2。
- `n_observed=0` 與負對照互斥：**邊界未寫清** ⇒ E2 短路。
- 受理批 min_gap／L／n_blocks：三家＋Claude 實算一致 `min_gap=12, L=1, n_blocks=165`（median 48 或 60 依算法取向，不影響 L）。
- 20×MW 成本：codex 實測 NaN 逐欄 8.9s/次 ⇒ E3 向量化＋獨立閘。

### 不採納
無。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01

**斷言**: v3 雖已把 D1 定為 `index + length + rows_frozenset` 的唯一 stage5 守衛，但 SPEC/TODO 仍保留「stage5 digest 對證」的舊指令；實作者依舊指令加入全批 digest 相等檢查時，合法的 test 子集會再次全部被拒。

**碼證**: `docs/EVTLABEL_SPEC.md:225` 明寫「唯一守衛」且「無 digest 相等比對」，但 `:298` 的 M-P3-5 仍寫「stage5 digest 比對 raise」；`docs/EVTLABEL_TODO.md:322` 仍寫「stage5 消費前 digest 對證」，而 `:325` 才改成「無 digest 相等比對」。R2 的原始矛盾就是全批 165 對 selection 子集 31 時 digest 不相等；RECHECK：`rg -n 'digest.*(對證|比對|相等)|無.*digest' docs/EVTLABEL_{SPEC,TODO}.md`。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880；docs/EVTLABEL_TODO.md#5afff7b7fdfb

[MAJOR] 信心度=High。這是可直接導致實作選錯守衛的文件矛盾，不是措辭偏好。刪除 M-P3-5 與 Task 3.6 標題中的 digest 消費要求，統一寫成「替換 validated cache 後，D1 三條守衛必須 raise；digest 只封存／揭露」。mutation 的名稱與斷言也應指向 rows/index guard，而不是 digest comparison。D1 的 `rows_frozenset` 欄位不應刪除；三條守衛各自不可刪。

## CODEX-R3-P1-02

**斷言**: D2 的 20 次置亂不足以穩定估計離散 null 的 95% 分位，且 `np.quantile` 預設插值使整數倖存數得到分數 q95；同一個 null 尾部形狀可由 q95=0.05 跳成 q95=1.0，`n_observed <= q95` 的結果因此不具明確、可重現的 order-statistic 語意。

**碼證**: `docs/EVTLABEL_SPEC.md:233`／`docs/EVTLABEL_TODO.md:350` 只定 `20` 與 `np.quantile(counts, 0.95)`，沒有 quantile method 或整數化規則；實跑 `venv/bin/python -c '...np.quantile...'` stdout：`one_nonzero q95=0.05000000000000071`、`two_nonzero q95=1.0`、`all_zero q95=0.0`。20 個樣本的 95% 位置只落在排序後最末端附近，尾部有效觀測不是一個穩定的 95% 區間。另，SPEC `:238` 寫「倖存者 0 ⇒ skipped:no_survivors」，但 TODO `:350` 無條件跑 20 次並以 `n_observed=0` 參與 `<= q95`，語意互斥。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880；docs/EVTLABEL_TODO.md#5afff7b7fdfb

[MAJOR] 信心度=High。建議預註冊一個有明確尾部解析度的候選：`N=100`，以整數 order statistic 或 `np.quantile(..., method="higher")` 取得 q95，保持 `n_observed <= q95 ⇒ suppressed`；`n_observed==0` 先短路為 `skipped:no_survivors`，只寫 `n_observed=0` 的揭露，不標 `negative_control_failed`，也不跑 20/N 次全表統計。N=100 是需要以成本 gate 核准的工程候選，不是已由資料證明的唯一正確樣本數；若採別的 N，需在文件寫出尾端 order statistic、比較符號與重現 seed。全 null 的「0 倖存者」仍可由既有 survivor stub/loud consumer 契約處理，但不應被誤報成負對照失敗。

## CODEX-R3-P1-03

**斷言**: D2 的負對照迴圈沒有對實際 `N×mann_whitney_table` 成本設獨立可證偽 gate；TODO 的 3.5 非 clean 路徑逐欄呼叫 scipy，在 39,373×31、10% NaN 的同形資料上已達每次約 8.9 秒，N=20 的線性成本約 178 秒，可能違反 SPEC §V 的總增量 `<2 分鐘`，而 clean-only 20 次 benchmark 會掩蓋此路徑。

**碼證**: `docs/EVTLABEL_TODO.md:305` 定 clean 欄向量化、非 clean 欄逐欄呼叫 `mannwhitneyu`；`:350` 於每次負對照重跑 Task 3.5＋BH＋效應量閘；`docs/EVTLABEL_SPEC.md:306` 只給總增量 `<2 分鐘`，`:237` 的 benchmark 是另一個 K=2000 permutation 場景，沒有量負對照本身。實跑 clean 20 次命令輸出 `shape=(31, 39373) ... repeats=20 seconds=0.936437`；實跑 TODO 逐欄 NaN 路徑 1 次輸出 `shape=(31,39373) nan_fraction=0.100 one_repeat_seconds=8.913055 results=39373`，所以 `20×8.913055≈178.26s` 是可重現路徑的成本警訊（不是把估算冒充成 20 次實測）。

**來源摘要**: docs/EVTLABEL_TODO.md#5afff7b7fdfb；docs/EVTLABEL_SPEC.md#44e743458880

[MAJOR] 信心度=Medium。實際 NaN 密度與 scipy 版本會改變秒數，但文件已要求保留 NaN/inf gate，不能用刪欄或放寬品質閘換速度。新增與 D2 所選 N 完全相同的 negative-control benchmark，涵蓋 clean、10% NaN、全 NaN/常數欄與實際 39k×selection-row 形狀，將「負對照本身」設為 `<120s` 或明確 FAIL；若需優化，應保留逐欄 pairwise 語意並以 scalar scipy 對照／NaN mask golden 驗證。不能只引用 clean 20 次 0.94 秒作為成本通過。

## CODEX-R3-P1-04

**斷言**: D4 的 fast-fail 預檢尚未真正與 `_build_holdout_split_plan` 共用同一規則；其簽名缺少目前 split helper 從 `labels_df` 解析的 `effective_horizon`，且 fast-fail 發生在 stage3 前時，預檢與 stage3 不一致的「以 stage3 為準並揭露 `preview_mismatch`」在 false-reject 方向根本無法發生。

**碼證**: 現行 `momentum/Analysis/ic_filter_orchestrator.py:478-497` 的 split helper 同時吃 `features_df`、`config`、`labels_df`，在 `:487` 解析 effective horizon、`:492-496` 算 split/purge/embargo/test rows；`:373-405` 證明 effective horizon 可能由 label 欄名而不是 config default 決定。v3 `docs/EVTLABEL_TODO.md:267` 卻只規劃 `prevalidate_imported_binary_selection_classes(bin_map, feature_index, cfg, label_window_rows, embargo_rows)`，未把該值或同一 split-plan 結果作為契約輸入。SPEC `docs/EVTLABEL_SPEC.md:192` 同時要求「立即 422、不進 preprocessing」與「預檢與 stage3 不一致由 stage3 揭露」；前者拒絕後，stage3 沒有機會產生 disclosure。RECHECK：以 `labels_df` 的 horizon 與 config default 不同、再以同一 feature index 造一個 preview 低於 floor 的案例，觀察兩方向（preview reject / stage3 reject）的可達性。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530；docs/EVTLABEL_SPEC.md#44e743458880；docs/EVTLABEL_TODO.md#5afff7b7fdfb

[MAJOR] 信心度=High。選擇單一實作，不接受雙份 arithmetic 加一個事後 `preview_mismatch` 欄位的容忍方案。建議把可純化的 row-plan 抽到 `momentum/core/split.py`（不 import `api`），例如：

`build_holdout_row_plan(*, n_rows: int, oos_test_size: float, effective_horizon: int, label_window_rows: int, embargo: int, min_test_rows: int) -> HoldoutRowPlan | SkippedResult`

回傳 `split_point`、`purge_gap`、`embargo`、train/test positions、skip details 與 deterministic fingerprint；orchestrator 以它建時間 bounds，service preview 以同一 plan 計 binary 類數。`effective_horizon` 必須是 caller 明確解析後的值，不能在 service 另猜 config default。preview 與實際 stage0 後的 feature index 也要對同一長度／位置 fingerprint；只有 preview 通過並實際進 stage3 後，才可揭露 mismatch。若 preview reject，錯誤應是明確的 preview rejection，不得宣稱 stage3 已確認。

## COMPOSER-R3-P2-01

**斷言**: v3 Task 3.7 在 `n_observed=0` 時仍可能因 `n_observed<=q95(shuffled_counts)`（尤其 counts 全 0 ⇒ q95=0）設定 `negative_control_failed`，與同 Task 邊界① `skipped:no_survivors` 語意衝突，使 UI 紅幅「負對照失敗」出現在「本無倖存者可交」情境。

**碼證**: `docs/EVTLABEL_SPEC.md` Task 3.7 邊界①「倖存者 0 ⇒ 不跑置換、`skipped:no_survivors`」與正文「`n_observed <= q95` ⇒ suppressed／`reason=negative_control_failed`」未規定短路；`docs/EVTLABEL_TODO.md` Task 3.7 要點 4 同構。RECHECK：全 null fixture 在負對照前令 `passed_after_step3=[]`，斷言 `survivor_output.reason` 為 `no_survivors` 而非 `negative_control_failed`。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880, docs/EVTLABEL_TODO.md#5afff7b7fdfb

[MINOR] 信心度=Medium。會怎麼失敗：使用者見误导性紅 banner，以為統計校準失敗而非「門檻後零倖存」。修法：Task 3.7 明寫 `if n_observed==0: 跳過負對照，僅 receipt=skipped:no_survivors`；M-P3-6 測試分拆兩 reason。

---

## COMPOSER-R3-P2-02

**斷言**: D4 要求 service 預檢與 orchestrator `_build_holdout_split_plan` 使用「相同」holdout 規則，但 v3 僅在兩處各寫敘述、未抽共用純函式；`effective_horizon` 解析依 `labels_df`（`ic_filter_orchestrator.py:487`）時，service 預檢易與 stage3 分歧，只能靠 `preview_mismatch` 事後揭露。

**碼證**: `docs/EVTLABEL_SPEC.md` Task 3.3「相同 chronological holdout 規則」；`docs/EVTLABEL_TODO.md` Task 3.3 要點 6 `prevalidate_imported_binary_selection_classes`；現網切分實作 `momentum/Analysis/ic_filter_orchestrator.py:478-541`。RECHECK：故意讓 service 預檢用 `purge=label_window`、stage3 用 `max(effective_horizon, label_window)`，斷言 `label_mode.preview_mismatch=True` 且 stage3 權威。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880, momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530

[MINOR] 信心度=Medium。修法：見必答 5b `holdout_test_row_index` 落 `momentum/core`；兩端 import 同一函式。`preview_mismatch` 保留作 drift 探測，非唯一防線。

---

## GROK-R3-P1-01

**斷言**: TODO Task 3.7「輸入／輸出」仍寫 `n_survivors_shuffled>0 ⇒ suppressed` 與舊 metadata `{n_survivors_shuffled,seed,block_len}`，與同 Task 要點 4／SPEC Task 3.7 之「20 次 q95、`n_observed<=q95`、`{n_observed,shuffled_counts,q95,seed_base}`」互斥；agent 若實作 I/O 句會把 D2 校準整段退回 R1 `>0` 整批殺。

**碼證**: `docs/EVTLABEL_TODO.md:345` 仍含 `n_survivors_shuffled>0 ⇒ ... negative_control_failed`；同檔 `:350` 要點 4 已是 q95 路徑；`docs/EVTLABEL_SPEC.md:233` 僅 q95。RECHECK：`grep -n 'n_survivors_shuffled>0' docs/EVTLABEL_TODO.md` 應於修訂後為 0，且 I/O metadata 形＝要點 4。

**來源摘要**: docs/EVTLABEL_TODO.md#5afff7b7fdfb

[MAJOR] 信心度=High。會怎麼失敗：實作者掃「輸入／輸出」契約先寫舊門檻 ⇒ ≈α 假 suppress 稅回流，與 R2 D2 裁定相反。修法：刪 `:345` 之 `>0` 句與舊鍵名，改寫成與要點 4／SPEC 同一組鍵與比較符。D2 在 TODO I/O 面標 **NOT-CLOSED** 直至此句清除。

---

## GROK-R3-P1-02

**斷言**: SPEC mutation 清單 M-P3-5 仍要求「stage5 **digest 比對** raise」，與 D1「消費前**無** digest 相等比對、唯一守衛＝index＋`rows_frozenset`」互斥；agent 可能為讓 mutation 變紅而**加回** digest 相等，或寫出永不通的 mutation（假紅／假綠）。

**碼證**: `docs/EVTLABEL_SPEC.md:298` `M-P3-5：... stage5 digest 比對 raise`；對照 `:225`「取代任何 digest 相等比對」與 TODO `:325`「**無** digest 相等比對」。同段驗證 `:226` 已改為「替換 cache ⇒ raise」＋M-P3-5b index permute，唯 mutation 目錄殘句未改。RECHECK：修訂後 `grep 'digest 比對' docs/EVTLABEL_SPEC.md`＝0；M-P3-5 改述「換 cache 後三守衛／`AlignmentViolationError`」。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880

[MAJOR] 信心度=High。修法：M-P3-5 改為「替換 `ValidatedBinaryLabel`（錯 `rows_frozenset`／錯 series）⇒ stage5 三守衛 raise」；可保留 M-P3-5b。M-P3-6 標題「負對照非零」亦建議改「q95 路徑改 warning-only」以免語意回潮（非本條 blocking 核心）。

---

## GROK-R3-P2-01

**斷言**: Task 3.7 在 `n_observed=0` 時若仍執行 `n_observed<=q95`（counts 全 0 ⇒ q95=0），會標 `negative_control_failed`，與同 Task 邊界「倖存者 0 ⇒ `skipped:no_survivors`」語意衝突，UI 紅幅誤導為校準失敗。

**碼證**: SPEC Task 3.7 邊界① vs 正文 `<=q95⇒suppressed`；TODO `:350`／`:358`。本輪模擬：N0_SUPPRESS_RATE=1.0。RECHECK：`passed_after_step3=[]` fixture 斷言 reason＝`no_survivors`（或等價），**不是** `negative_control_failed`。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880

[MINOR] 信心度=High。修法：`if n_observed==0: 跳過負對照，只記 no_survivors`；M-P3-6 分拆兩 reason。

---

## GROK-R3-P2-02

**斷言**: D4 要求 service 預檢與 `_build_holdout_split_plan`「相同規則」，但 v3 只在兩處各寫敘述、未抽共用純函式；`effective_horizon` 依 `labels_df`（orchestrator `:487`）時預檢易與 stage3 分歧，僅靠 `preview_mismatch` 事後揭露不足以保證顯式模式 DX。

**碼證**: SPEC Task 3.3:192；TODO Task 3.3:267；現網 `ic_filter_orchestrator.py:478-541`。RECHECK：兩端改為 import 同一 `holdout_test_row_index`；故意讓舊複本 purge 不同 ⇒ 測試應在共用後無法漂移（或只測 preview_mismatch 探測器）。

**來源摘要**: docs/EVTLABEL_TODO.md#5afff7b7fdfb, momentum/Analysis/ic_filter_orchestrator.py#d374c57d1530

[MINOR] 信心度=Medium。修法：見必答 5b；`preview_mismatch` 保留作第二道。

---

## GROK-R3-P2-03

**斷言**: D1 三守衛在「保 index 的 X 值列重排」下可全過：`pd.DataFrame(X.to_numpy()[perm], index=X.index, columns=X.columns)` 之後 MW 看到錯配 X↔y，而 `rows_frozenset`／index.equals 仍真——守衛非密碼學封閉；v3 靠「中間不得重排」祈使句補洞，未在驗證／mutation 具名此殘形。

**碼證**: SPEC/TODO Task 3.6 三守衛定義；對照 grok R2 之 `iloc[perm]`（已被①擋）。RECHECK：單元測試在守衛後插入值重排，若無結構禁令則統計錯配且不 raise（證明殘形）；修法不強制加 digest，可選 M-P3-5c 靜態／審閱清單「assign 後立即呼叫、無中間 X 重綁」。

**來源摘要**: docs/EVTLABEL_SPEC.md#44e743458880

[MINOR] 信心度=High（形狀）；Medium（agent 誤觸機率）。**不**建議加 value-digest。修法：驗證段點名殘形＋保持祈使句；凍結不阻擋。

---


## 戳記
