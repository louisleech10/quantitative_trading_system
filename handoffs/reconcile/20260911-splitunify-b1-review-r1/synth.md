# Reconcile — 20260911-splitunify-b1-review-r1

**來源** 20260911-splitunify-b1-review-r1-codex.md, 20260911-splitunify-b1-review-r1-composer.md, 20260911-splitunify-b1-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——**不可進 B2b**，修完 G1／G2 即放行（兩條皆為可直接落地的修正）。

三家 verdict：codex「不可進 B2b：`CODEX-R1-P1-01`、`P1-02`」；composer「可進」（零 findings
sentinel）；grok「可進」（4 條 P2/P3）。依「看碼證不數人頭」採 codex——
其兩條 P1 都經主委實跑複驗成立，且 **G1 有 grok 獨立附議**（`GROK-R1-P2-01` 同指）。

主委自產版另存 `handoffs/20260911-splitunify-b1-b2a-claude-selfreview.md`（`CLAUDE-R1-P3-01/02`）。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **G1 D-002 之「覆寫」錨點不是 BASE 的真實 heading** | P1 | CODEX-R1-P1-01、GROK-R1-P2-01 | **採納，實跑複驗成立**。`grep -nE '^#{2,4} ' docs/GAP3_EVENT_UX_SPEC.md` 共 27 個 heading，**沒有任何一個**是「B1.3 事件切分」——真文住在**兄弟檔** `docs/GAP3_EVENT_SPEC.md:168`（`**Task B1.3 — per-symbol 時間切分＋interval-aware purge＋跨標的 time-cluster**`）。⇒ 我把兩份不同的凍結文件搞混了。修法：①D-002（BASE＝UX_SPEC）之「覆寫」改列 UX_SPEC 之**真實** heading——經逐行對照，`capability`／`n_train` 之 17 處命中落在 `### Phase 1 — 使用者自篩 CSV 匯入（依賴：無）　【#0(b) ＋ #5】` 之下（行 1369／1372／1433／1498）；②B1.3 邊界來源之變更**移出 D-002**，改寫進 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`——該檔是 `GAP3_EVENT_SPEC.md` 檔頭逐字指定的修訂路徑（「後續修訂走延伸檔 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`，不就地改本檔」），**不是** D-00N 慣例。 |
| **G2 Task 1.3 驗證條件自相矛盾（19 ≠ 30）** | P1 | CODEX-R1-P1-02 | **採納**。我在 B1 補 `grep '::'` 過濾（因為 `-q` 的進度條殘片會混進 `^FAILED `），卻**沒同步改驗證條件**——SPEC／TODO 仍寫「清單行數 == receipt 內 `^FAILED ` 行數」，而 receipt 是 **30** 行 `^FAILED `、清單是 **19** 行。⇒ 驗證條件永遠不成立。修法：條件改為「清單行數 == receipt 內 `^FAILED ` 且**含 `::`** 的行數」，並在 SPEC／TODO 逐字寫出該過濾。🔴 這是我在**修一個洞的同一次動作裡開了另一個洞**，正是「改裁決必同步所有引用」那條的形態。 |
| **G3 `_as_ms` 對 int64 假設「已是毫秒」直通，無測試鎖** | P2 | GROK-R1-P2-02 | **採納，且我認為它被低估**。餵 epoch **秒** 的 int64 index（`data_cache/features/**/timestamps.parquet` 正是秒）會**靜默**得到 year=1970 的邊界；B2b／B3 複用就會讓答案窗比較錯 1000 倍。我自己在寫探針時已經踩過一次這個坑，卻沒在 `_as_ms` 內設防。修法：`_as_ms` 對 int64 加**量級判定**——`abs(v) < 1e11` ⇒ raise（「looks like epoch seconds, expected milliseconds」，與 `_normalize_ic_time_index` 之反向守衛對稱），並補 `-k unit_seconds_rejected` 測試。 |
| **G4 SPEC/TODO 之 Task 2.1 回傳型別與實作不一致** | P3 | GROK-R1-P3-02 | **採納**。文件寫元組 `(train_row_index, …)`，B2a 實作回 `Dict[str, Any]`（回 dict 是為了讓 B3 呼叫端不必記順序，較不易錯）。⇒ 改文件對齊實作。另 Task 1.2 驗證欄仍寫「與 Python 常數集合相等」，B1 實測是 SPEC 字面對證 ⇒ 一併改寫並註明 B2b 補。 |
| **G5 「20 條」既有紅與凍結的 19 條不一致** | P3 | GROK-R1-P3-01、CLAUDE-R1（自評） | **採納 grok 的判準**。grok 指出 passed 基數 **1615 vs 1103** 證明「20」不是本 receipt 的漏抓——兩次跑的**收集面根本不同**（1615 那次應含更多檔）。⇒ 不是浮動、也不是我少抓，是兩個不同的量測。修法：`HANDOFF.md` 與 Task 1.3 之目標句改寫為「以 B1 凍結之 receipt 為準（19 條 / 1103 passed）」，並註明舊的 20/1615 是不同收集面的舊量測，**不再引用**。 |
| **G6 B1 的「兩端對證」是弱形式** | P2 | CODEX-R1-P2-03（主委自評同結論） | **接受為具名限制，不擋 B2b**。JSON↔SPEC 只是字面 substring，且兩者由**同一人同一批**寫成 ⇒ 共同模式失效風險真實。它擋得住「日後只改一邊」，擋不住「一開始兩邊都寫錯」。已在測試檔尾以 `TODO(B2b)` 具名；B2b 之 Python 常數對證才是真第二來源。codex 亦判「非單獨阻擋項，為 B2b 必補證據」。 |
| **G7 `_as_ms` 之 tz 行為（已自證）** | P3 | CLAUDE-R1-P3-01 | **記錄**。主委實跑：naive 與 UTC 逐值相同（`1736964000000`），Asia/Tokyo 差 9 小時（`1736931600000`）——**行為正確**（回 UTC 毫秒），但要求同票內時區慣例一致。修法：docstring 與 SPEC C-0 各補一句。 |
| **G8 `tests/baselines/` 不被 pytest 收集（已自證否）** | P3 | CLAUDE-R1-P3-02 | **記錄**。`pytest --collect-only tests/baselines` → `collected 0 items`，不干擾。本條為我 brief 之「我沒查的」第 2 條，派工後自查掉。 |

### 主委之自我記帳

G2 是我在 B1 修 `awk` 過濾洞的**同一次動作**裡開的新洞——過濾加了、驗證條件沒跟著改。
G3 是我已經踩過、已經寫進 HANDOFF 踩坑清單、卻沒在自己新寫的函式裡設防的同一個單位坑。
兩條都不是「沒想到」，是「想到了但沒把它變成機械閘」。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: D-002「覆寫」兩個 touchset 錨點不是 BASE 實際存在的 heading，違反 frozen D 程序，故無法作為可機檢的原檔覆寫。
**碼證**: `FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md:84-95` 要求 heading 逐字存在；`git show e0f3cb52:docs/GAP3_EVENT_UX_SPEC.md | rg 'B1\.3|n_train|n_test|n_purged|summary\.split'` 無輸出(rc=1)；`D-002:12` 仍宣告兩項，實際 B1.3 heading 在 `GAP3_EVENT_TODO.md:115`。
**來源摘要**: docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914; docs/GAP3_EVENT_UX_SPEC.D-002.md#92cd70b1f366
正文：[MAJOR] 信心度=High。修法是改用正確 BASE/實際 heading，或將 touchset 宣告為 `none` 並升 R 處理；RECHECK：重跑上述 `git show ... | rg ...` 與 dext template check。
## CODEX-R1-P1-02
**斷言**: Task 1.3 驗證條件「清單行數等於 receipt 的 `^FAILED ` 行數」對 frozen receipt 不成立：19 ≠ 30。
**碼證**: `SPLITUNIFY_SPEC.md:405-411`、`SPLITUNIFY_TODO.md:144-149` 寫 raw 計數；實跑 `raw_FAILED=30, filtered_nodeids=19, baseline_list=19, set_diff=empty, pytest_rc=1`，receipt summary 為 `19 failed, 1103 passed, 15 skipped`。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#1bf699fbde5b; docs/SPLITUNIFY_TODO.md#f18c6a09ec30; handoffs/run_receipts/splitunify-analysis-baseline.stdout#12b86d456500
正文：[MAJOR] 信心度=High。raw 進度列含非 nodeid 的 `FAILED`，會令自有驗收 gate 永遠誤判；修法是用與產檔相同的 `awk '/^FAILED / && $2 ~ /::/'` 計數。RECHECK：重跑該 extractor、`comm` 差集及 baseline nodeid collect-only。
## CODEX-R1-P2-03
**斷言**: B1 contract test 的「兩端對證」只有 JSON↔SPEC 字面 substring 檢查，不是獨立的 JSON↔Python 語意證明。
**碼證**: `test_splitunify_contract.py:97-109` 只查 `spec_text` 是否含 literals；`tests/...:112-115` 明示 Python constants/import-raise 延至 B2b；本測試實跑 8 passed。
**來源摘要**: tests/momentum/Analysis/test_splitunify_contract.py#901b0758baca; docs/SPLITUNIFY_TODO.md#f18c6a09ec30
正文：[MINOR] 信心度=High。B1 不動生產碼使此限制可理解，但不可把它稱為完整 self-proof；B2b 應補 JSON loader、集合相等與缺鍵 import-raise mutation。
## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–7、B1/B2a 審查對象與主委驗收項後無 P0/P1/P2 finding；可進 B2b（投影純函式）。

**碼證**: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py tests/momentum/core/test_splitunify_boundary.py` → 17 passed, rc=0；`pytest --collect-only` 19 baseline nodeids → 19 collected, rc=0；receipt `splitunify-analysis-baseline.stdout` 尾 `19 failed`＋`pytest_rc=1`；`grep -rn holdout_boundary momentum api` 無生產 caller；`holdout_boundary` 算術鏈 `split_preview.py:44-111`；mutation 守衛 `-k ms_same_source` → 3 passed；`git diff 9607430d^..9607430d -- docs/GAP3_EVENT_UX_SPEC.md` 僅索引行。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#1bf699fbde5b;docs/GAP3_EVENT_UX_SPEC.D-002.md#92cd70b1f366;momentum/Analysis/contracts/split_unify.json#5ff16a66f2ca;momentum/core/split_preview.py#58a4ef2c7033

[NON-BLOCKING] 信心度=High。核對依據＝必答 1（算術同源＋caller grep）與必答 4（receipt 19／nodeid 19／SPEC 過濾說明）之碼證；B1 JSON↔SPEC 為分階弱對證（必答 3）；D-002 覆寫兩條對 GAP3_EVENT_SPEC B1.3 與 pipeline 現碼。殘差：HANDOFF「20 failed」敘事過期（必答 4）、非 UTC tz-aware 未實測（brief 成本項）——均不擋 B2b。

---

## GROK-R1-P2-01

**斷言**: D-002「覆寫」欄宣告的 `B1.3 事件切分` 不是其 BASE（`docs/GAP3_EVENT_UX_SPEC.md`）內任何 heading；真文住在兄弟檔 `docs/GAP3_EVENT_SPEC.md` Task B1.3——凍結 D 延伸的觸及面錨點規則被架空，後續讀者／機檢無法對讀原檔。

**碼證**: `docs/GAP3_EVENT_UX_SPEC.D-002.md:3` BASE＝`GAP3_EVENT_UX_SPEC.md @ e0f3cb52`；`:12` 覆寫寫 `**B1.3 事件切分**`；`grep -c 'B1\.3' docs/GAP3_EVENT_UX_SPEC.md` → 內容提及亦無 Task heading；`docs/GAP3_EVENT_SPEC.md:168` 才有 `**Task B1.3 — per-symbol 時間切分＋…**`，改法句含「每標的各自按時間切＋緩衝 ≥ 答案窗」。`scripts/template_check.sh` dext 段註明「是否為原檔實際 heading 屬語意，交審查者」。RECHECK: 對 BASE 跑 `grep -n 'B1\.3\|^## \|^### ' docs/GAP3_EVENT_UX_SPEC.md | head`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.D-002.md#92cd70b1f366

[MAJOR] 信心度=High；**不擋 B2b**。修法：覆寫改指 UX SPEC 內真實 heading（例如 Task 1.12 之 event-study-only／報告鍵語意），並交叉引用 `GAP3_EVENT_SPEC` B1.3；或升 R／另開以 EVENT_SPEC 為 BASE 的延伸。勿再寫不存在於 BASE 的 `B1.3`。

---

## GROK-R1-P2-02

**斷言**: B2a `_as_ms` 對 int64 假設「已是 epoch ms」直通、對非 UTC tz-aware 會平移絕對 ms，且無測試鎖這兩條；與 FF `timestamps.parquet`（秒）及 orchestrator 秒語意同形的輸入會得到 year=1970 的「邊界」，B2b／B3 若複用會讓答案窗比較靜默錯位。

**碼證**: `split_preview.py:49-58`（datetime → `Timestamp.value//10**6`；else `int(value)`）；實跑 Taipei vs naive 差 8h；實跑 `pd.Index([1704067200+…])` → `train_end_ms=1705323600`、`unit='ms'`→1970、`unit='s'`→2024。現測只覆蓋 DatetimeIndex／int64 **ms**（`test_splitunify_boundary.py:91-96,100-105`），無秒級／tz-aware 用例。FF 樣本 `data_cache/features/BCHUSDT/1h/…/timestamps.parquet` 首值 `1704067200`（秒）。RECHECK: 對 `_as_ms` 餵秒 Index 與 `tz='Asia/Taipei'` Index；對照 `feature_reader.py:205` `unit="s"`。

**來源摘要**: momentum/core/split_preview.py#58a4ef2c7033

[MAJOR] 信心度=High；**不擋 B2b 開工**，但 B2b 的 `as_ms`／`feature_index` 契約須先 fail-closed（拒秒級 int、拒非 UTC tz，或先正規化），**禁止**盲 `from momentum.core.split_preview import _as_ms`。可選回修 B2a 加數量級閘＋兩條紅測。

---

## GROK-R1-P3-01

**斷言**: Task 1.3 目標句／HANDOFF 仍寫「20 條」既有紅，與 B1 凍結的 receipt／nodeids **19** 條不一致；passed 基數 1615 vs 1103 證明「20」不是本 receipt 的漏抓。

**碼證**: SPEC Task 1.3「把 HANDOFF…之 20 條落成」；HANDOFF.md:50「20 failed／1615 passed」；receipt 末行 `19 failed, 1103 passed, 15 skipped`＋`pytest_rc=1`；`diff <(awk …|grep '::') tests/baselines/analysis_known_failures.nodeids` 空。RECHECK: 重讀 receipt 摘要與 HANDOFF 段；勿在無新跑下把清單改回 20。

**來源摘要**: handoffs/run_receipts/splitunify-analysis-baseline.stdout#（pytest_rc=1）

[MINOR] 信心度=High；**不擋 B2b**。修法：主委更新 HANDOFF 散文為 19／1103（或註明舊快照）；SPEC／TODO 目標句改「以 B1 receipt 凍結之 N 條」免寫死 20。

---

## GROK-R1-P3-02

**斷言**: SPEC／TODO Task 2.1 輸入輸出仍寫元組形 `(train_row_index, …)`，B2a 實作回 `Dict[str, Any]`；Task 1.2 驗證欄仍寫「與 Python 常數集合相等」，B1 實測是 SPEC 字面對證——文件驗收句與交付不一致，B3 呼叫端可能按 tuple unpack 寫錯。

**碼證**: SPEC:417-418／TODO:153-154 之 `→ (train_row_index, …)`；`holdout_boundary` `:107-112` `return {…}`；測試一律 `out["test_start_ms"]`；SPEC Task 1.2 驗證「JSON 之值集與 Python 常數集合逐值相等」vs `test_splitunify_contract.py:2-7,97-109` 明文改 SPEC 字面。RECHECK: `sed -n '415,420p;360,370p' docs/SPLITUNIFY_SPEC.md` 對照 `split_preview.py:61-112`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#1bf699fbde5b

[MINOR] 信心度=High；**不擋 B2b**。修法：Task 2.1 改標 `Dict`／TypedDict；Task 1.2 驗證改「B1＝SPEC 字面；B2b＋＝Python 常數」。

---

