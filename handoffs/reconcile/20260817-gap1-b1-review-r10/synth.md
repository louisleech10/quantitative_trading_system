# Reconcile — 20260817-gap1-b1-review-r10

**來源** 20260817-gap1-b1-review-codex.md, 20260817-gap1-b1-review-composer.md, 20260817-gap1-b1-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；B1 實作 code review → B1 修補 commit）

三家共 **10 條** canonical ID（codex 5／grok 4／composer 1）；下列四群集**引用全部 10 條，0 掉項**。
三家 Verdict **一致＝「需修補後進 B2」**（無分歧，無須取較嚴版裁決）。
🔴 **本輪最重要之結果：A1-19 之一項宣稱被可執行反例推翻**（見 K1）——那是主委自己寫進延伸檔的話。

### K1 — objective 在「已宣告 timeframe」下仍可靜默用 730（推翻 A1-19 之宣稱）
**引用**: CODEX-R10-P1-03, GROK-R10-P1-01

兩家各自以**可執行反例**證明：engine 若 `**kwargs` 吞下 `timeframe` 但回傳缺 `annualization`
（或回空 dict），`objectives/strategy_backtest.py` 之 `annualization.get("periods_per_year", 730)`
會**靜默**以 730 年化（codex probe：`returned=6.583962285857072 == expected_730`、`silent_730=True`；
grok 之 SwallowEngine 同結論）。而 A1-19 逐字寫「給了 timeframe 而引擎不支援 ⇒ 仍 TypeError（fail-loud），
**不**靜默退回隱性 730」⇒ **該宣稱只涵蓋「不接受 kwargs」那一類 engine，對「接受但不回填」那類為偽**。
主委接受推翻（本票命中 (a)(d)，靜默 730 正是 C2 要關的病）。

**處置（B1 修補 commit）**：
1. `evaluate()` 於 `self.timeframe is not None` 時**硬性要求**：`result.annualization` 存在、
   為 dict、`source == "resolved"`、`periods_per_year` 為正整數；任一不符 ⇒
   `raise ValueError("engine 未回填 annualization…")`（fail-loud，**禁** `.get(..., 730)` 兜底）。
2. `self.timeframe is None`（legacy 路徑）維持 730 fallback，但改為**具名常數＋註解**標示其為
   「legacy 相容路徑」，並於 `annualization` 缺失時 `logger.warning` 一次。
3. 新增測試 `test_objective_fails_loud_when_engine_swallows_timeframe`（SwallowEngine 反例 ⇒ `pytest.raises`），
   即兩家反例之回歸鎖。
4. 延伸檔 **A1-19 之該句改寫**（不得留錯誤宣稱）：見 A1-20。

### K2 — mutation 探針之「還原後全綠」自檢是空殼（我批評別人的病，自己犯）
**引用**: CODEX-R10-P1-02

`scripts/gap1_b1_mutation_probe.sh` 之 baseline 與 post-restore 只 `echo rc`，**無非零分支**
⇒ baseline 本來就紅、或還原失敗留下 mutant，腳本仍會印「✅ 全部 mutation 皆轉紅」並 rc=0。
codex 判 MAJOR 且信心 10/10；主委複核成立——這與「工具必須自帶強制機制、禁空殼檢查」直接衝突。

**處置**：baseline rc≠0 ⇒ 立即 `exit 1`（前提不成立就不該跑 mutation）；
post-restore rc≠0 或 `grep MUTANT` 命中 ⇒ `exit 1`；兩處皆印出實際 rc 與 tail。

### K3 — §V-9 未進探針（Gate 文字與實跑不一致）
**引用**: COMPOSER-R10-P1-01, GROK-R10-P2-02

TODO Task 1.4 驗證欄與 B1 Gate 皆列 `§V-9`（接受 `bar_count` 或 `default_730` ⇒ 轉紅），
但探針只有 §V-5／8／10／13／15 五條 ⇒ commit 訊息「五條全轉紅」與 Gate 要求**不對齊**。
composer 手動 mutate（`bar_count` 回 `status="ok"`）實測 **1 failed rc=1** ⇒ 測試本體可證偽，缺的是自動化。

**處置**：探針新增 **§V-9a**（`returns_contract` 之 `bar_count` 分支改回 `status="ok"`）與
**§V-9b**（`source != "resolved"` 之守衛拿掉 ⇒ `default_730` 被放行），各斷言 rc=1 且 FAILED≥1；
探針總數 5 → **7**；B1 Gate 文字同步為「§V-5／8／9a／9b／10／13／15」。

### K4 — 真實 kline 缺失時整檔 skip ＝ 假綠
**引用**: CODEX-R10-P1-01, GROK-R10-P2-03, CODEX-R10-P2-04, GROK-R10-P2-01, CODEX-R10-P3-05

codex 判 MAJOR（「真實資料測試的缺席不能被當成通過」）、grok 判 MINOR（「skip 優於造假」）
⇒ **取較嚴版**：資料是本票之必要前置（§G 明定 receipt 必用真實 kline，禁合成 fixture），
故缺檔應 **fail 而非 skip**；但同時保留**不依賴 kline 的 fail-closed 案例**（缺 `annualization`、
未知 `t_semantics`、無交易），使無資料環境仍有實質覆蓋而非全 0。

**處置**：
1. `test_returns_contract.py` 之 `_real_backtest` 改：缺檔 ⇒ `pytest.fail("GAP-1 §G 要求真實 kline…")`；
   不依賴 kline 之三案例移出該 helper（改用純 stub 物件，**不**冒充 kline 資料）。
2. **GROK-R10-P2-01（兩個 import 路徑）**：`test_frequency.py` 新增 identity 斷言
   （`core.f is reexport.f` 三名稱）＋文件規定「新碼只 import core，re-export 僅相容」。
3. **CODEX-R10-P2-04（`IBacktestEngine` Protocol 未宣告新參）**：**具名殘留**
   `為何現在不做: blocked-by:SPEC §C 白名單（既有測試檔只允許加斷言；改 Protocol 需連動所有實作與 test doubles）`；
   觸發＝B4 收尾後之「白名單擴充」提案，或使用者裁決。登記 registry **G1-R10**。
   誠實邊界：**現行相容靠條件分支而非 Protocol 宣告**，K1 之 fail-loud 修補會把危險面收掉，但契約漂移仍在。
4. **CODEX-R10-P3-05（A1 範圍字面不一致）**：TODO 標頭／§0／追溯表與新 package docstring
   統一標 `A1-1..A1-20`。

### 收斂結論（主委）
- 10 條全數處置（0 掉項）；4 條 MAJOR 皆在本輪修完，3 條 MINOR 修 2 留 1（Protocol 漂移＝具名殘留 G1-R10）。
- **K1 是本輪最重要收穫**：我在 A1-19 寫下的「不靜默退回 730」是**未經反例驗證的宣稱**，
  兩家各自造出反例推翻。教訓與 J1 同型（宣稱未實跑即寫進契約），已記入延伸檔 A1-20。
- 探針總數 5 → 7；`gap1_b1_mutation_probe.sh` 由「印 rc」升為 **fail-closed**。
- B1 之產品碼變更：`objectives/strategy_backtest.py` 之 annualization 硬性檢查（唯一數值面修補）。

**Verdict**: 需修補後合併 → 修補於 B1 修補 commit ＋延伸檔 A1-20；三家戳記後進 B2。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R10-P1-01
**斷言**: 缺少真實 kline 時，`test_returns_contract.py` 會把核心資料正確性測試靜默變成綠色 skip，故「111 passed」不是可攜的 B1 gate。
**碼證**: `tests/momentum/Analysis/strategy_validation/test_returns_contract.py:39-41` 以 `pytest.importorskip`／`pytest.skip` 放過缺檔；本機 focused pytest → `111 passed`，但無資料分支不會失敗。RECHECK: 在沒有 `data_cache/feature_klines/kline_cache.h5` 的驗證環境跑同一 pytest 並加 `-rs`，目前會出現 skip 而 rc=0。
**來源摘要**: tests/momentum/Analysis/strategy_validation/test_returns_contract.py#e656f2c3a2a4
[MAJOR] 信心度=10/10；真實資料測試的缺席不能被當成通過。修法：資料是本票必要前置時用 `pytest.fail`／明確 preflight fail-closed；若另設可選整合測試，B1 gate 必須明確要求資料存在且 skip 不得算通過。

## CODEX-R10-P1-02
**斷言**: mutation probe 沒有檢查 baseline 與 post-restore pytest rc，故既有紅或還原後紅都可能被誤報為全部 mutation 通過。
**碼證**: `scripts/gap1_b1_mutation_probe.sh:74-76`、`:103-107` 只 `echo "$?"`，沒有非零分支；本輪實跑五條皆 rc=1、post-restore rc=0，但這只證明本次結果，未證明腳本 fail-closed。RECHECK: 將 baseline 或還原後 pytest 置為非零再執行 probe，預期腳本應非零；現行腳本沒有該 gate。
**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e
[MAJOR] 信心度=10/10；腳本的兩個已修缺陷（backup 還原未追蹤檔、SyntaxError mutant）確實已擋住，但末段「全綠」自檢仍是空殼。修法：捕獲 baseline/post-restore rc，任一非 0 立即退出；保留現有 rc=1 且 `FAILED>=1` 判準。

## CODEX-R10-P1-03
**斷言**: `StrategyBacktestObjective` 在 timeframe 已指定、注入 engine 接受新 kwargs 但回傳缺 `annualization` 時，會無錯誤把 objective Sharpe 算回 730。
**碼證**: `momentum/Optimization/objectives/strategy_backtest.py:130-135` 使用 `annualization.get("periods_per_year", 730)`；可執行 injection probe 輸出 `returned=6.583962285857072`, `expected_730=6.583962285857072`, `expected_8760=22.807514388443547`, `silent_730=True`。RECHECK: 以同一 probe 或測試一個接受 `**kwargs`、回傳無 annualization 的 engine，`timeframe="1h"` 應現行無例外且回 730。
**來源摘要**: momentum/Optimization/objectives/strategy_backtest.py#e2d35ca3506b
[MAJOR] 信心度=10/10；A1-19 的「不支援 kwargs 就 TypeError」只覆蓋一類 engine，未封住 kwargs 相容但 metadata 缺失的數值錯誤。修法：`self.timeframe is not None` 時要求 annualization 存在、source=`resolved` 且 periods_per_year 合法，否則 fail-loud；timeframe=None 的 legacy 730 fallback 可保留並明確標示。

## CODEX-R10-P2-04
**斷言**: `IBacktestEngine` Protocol 仍只宣告四個舊參數，未宣告 objective 在 timeframe 路徑傳入的 `timeframe`／`risk_free_rate`，介面契約與實作行為已漂移。
**碼證**: `momentum/core/protocols.py:132-138` 的 `run_backtest` 沒有兩個 optional kwargs；`strategy_backtest.py:115-125` 卻動態傳入。既有 `StubBacktestEngine`／`DummyBacktestEngine` 也仍是舊簽名，現行相容行為靠條件分支而非 Protocol。RECHECK: 用靜態型別檢查或逐一檢查 `IBacktestEngine` 實作簽名，會看見新 engine contract 未被宣告。
**來源摘要**: momentum/core/protocols.py#f39ba5fbe938
[MINOR] 信心度=9/10；目前 production `VectorizedBacktest` 路徑可運作，故不把它誤列為當前 runtime failure。修法：後續允許擴大 scope 時更新 Protocol 與所有實作／test doubles；B1 因 brief 白名單只允許既有測試加斷言，不在本輪越界修改。

## CODEX-R10-P3-05
**斷言**: A1-19 已成為實作依據，但 TODO 與新 package docstring 仍只列 A1-18／A1-15，追溯文字不一致。
**碼證**: `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md:311-337` 新增 A1-19；但 `docs/GAP1_STRATEGY_OVERFIT_TODO.md:5,42,520,525` 與 `momentum/Analysis/strategy_validation/__init__.py:4` 仍寫舊範圍。RECHECK: `rg -n 'A1-1\.\.A1-(15|18)|A1-19'` 可重現混用。
**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#961bb34c1515
[MINOR] 信心度=10/10；不影響本次 runtime，但會讓後續執行端漏讀 canonical 落點修訂。修法：下一個允許的文件同步變更統一標為 A1-19。

## COMPOSER-R10-P1-01

**斷言**: `scripts/gap1_b1_mutation_probe.sh` 未自動化 TODO Task 1.4／Phase B1 Gate 要求的 **§V-9** mutation（接受 `bar_count` 或 `default_730`），與 commit receipt 宣稱「五條全轉紅」及 Gate 行 `§V-5／8／9／10／13` 不一致，留下 mutation 自證缺口。

**碼證**: `scripts/gap1_b1_mutation_probe.sh:78-101` 僅 §V-8/15/5/10/13；`docs/GAP1_STRATEGY_OVERFIT_TODO.md` Task 1.4 驗證欄「mutation §V-9 轉紅」、B1 Gate「§V-5／8／9／10／13」。本輪手動 mutate `returns_contract.py` 使 `bar_count` 回 `status="ok"` → `pytest …::test_bar_count_is_not_applicable_with_named_reason` **1 failed** rc=1。RECHECK：在探針末加 §V-9 mutant（如把 `_REASON_T_SEMANTICS_INFLATES` 分支改 `status="ok"`）並斷言 rc=1。

**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e

[MAJOR] 信心度=High。會怎麼失敗：未來 regress 接受 `bar_count`/`default_730` 時，現行探針仍綠，違反 TODO「新測試須 mutation 自證」精神。修法：探針增 §V-9（可選保留 §V-15 並更新 Gate 文案統一為六條或明確取捨）。測試本體已可證偽，故非 BLOCKING。

---

## GROK-R10-P1-01

**斷言**: `StrategyBacktestObjective.evaluate` 在呼叫方已指定 `timeframe` 時，仍可能以 `annualization.get("periods_per_year", 730)` 靜默使用 730，只要引擎接受並忽略 kwargs 且不回填 `annualization`；A1-19「不靜默退回隱性 730」不成立。

**碼證**: `strategy_backtest.py:116-136` 條件傳 kwargs 後仍 `periods_per_year=int(annualization.get("periods_per_year", 730))`；A1-19 稱「不支援⇒TypeError、不靜默 730」；`IBacktestEngine` 僅四參。本輪 SwallowEngine（`**kwargs` 吞 timeframe、回 `annualization={}`）⇒ silent ppy=730。生產 VectorizedBacktest 主路徑仍正確。RECHECK: 建 SwallowEngine 後 `StrategyBacktestObjective(..., timeframe="1h")` 讀 recompute ppy。

**來源摘要**: momentum/Optimization/objectives/strategy_backtest.py#e2d35ca3506b

[MAJOR] 信心度=High。會怎麼失敗：優化目標在「已宣告 1h」下仍按 730 年化，冠軍排序／與 engine 直呼分叉被掩蓋。
修法（建議最小）：當 `self.timeframe is not None` 時，要求 `result.annualization` 為 dict 且 `source=="resolved"` 且含 `periods_per_year`，否則 raise；**禁止**在此分支 default 730。可加測試：SwallowEngine ⇒ 必須 raise。不阻擋 Task 1.1/1.2/1.4 契約本身；建議 B2 前小補丁。

---

## GROK-R10-P2-01

**斷言**: Task 1.1 存在兩個 import 路徑（`momentum.core.frequency` vs `momentum.Analysis.strategy_validation.frequency` re-export），目前同物件但無機械防漂移閘，後續若在 re-export 檔加邏輯會靜默分叉。

**碼證**: Strategy／returns_contract 直 import core；測試／TODO 字面走 Analysis re-export。VERIFY `core.resolve_periods_per_year is reexport.resolve_periods_per_year` → True（三名稱皆 is）；無測試鎖定 identity。RECHECK: `python -c "from momentum.core import frequency as c; from momentum.Analysis.strategy_validation import frequency as r; assert c.resolve_periods_per_year is r.resolve_periods_per_year"`。

**來源摘要**: momentum/Analysis/strategy_validation/frequency.py#e7bf1c0207ad

[MINOR] 信心度=High。修法：在 `test_frequency.py` 加 identity 斷言；或文件規定「新碼只許 import core，re-export 僅相容」。不需改 A1-19 落點結論。

---

## GROK-R10-P2-02

**斷言**: B1 mutation 探針未覆蓋 Task 1.4／§V-9 方向的 returns_contract mutant（例如 `bar_count` 改回 `status=ok` 或 `default_730` 改放行），該側只靠單元測試、無「改壞必紅」自證腳本。

**碼證**: `scripts/gap1_b1_mutation_probe.sh` 只 mutate frequency／sharpe／test_vectorized_backtest（§V-5／8／10／13／15）；TODO Task 1.4 與 B1 Gate 仍列 §V-9；單元測試 `test_bar_count_is_not_applicable_*`／`test_default_730_is_rejected` 有覆蓋故非裸奔。RECHECK: 暫時改 returns_contract 使 bar_count 回 ok 後跑 test_returns_contract（應紅）；確認探針未含此步。

**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e

[MINOR] 信心度=Medium。修法：探針加一條 mutate returns_contract（bar_count→ok）期望 FAILED≥1；或 TODO B1 Gate 明文「§V-9 完整版 defer B3」。不阻 B2。

---

## GROK-R10-P2-03

**斷言**: `test_returns_contract.py` 在 `data_cache/feature_klines/kline_cache.h5` 缺失時整檔 skip，無資料 CI／乾淨 checkout 會對 Task 1.4 呈假綠（0 failed / 全 skip）。

**碼證**: `test_returns_contract.py:40-41` `if not _KLINE.is_file(): pytest.skip(...)`；多數案例走 `_result()` 真實回測。本輪有檔且 111 passed 含該檔。RECHECK: 暫移 kline 後 `pytest .../test_returns_contract.py -q` 應見 skipped，再還原。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_returns_contract.py#e656f2c3a2a46a

[MINOR] 信心度=Medium。skip 優於造假；修法選一：GAP-1 標記下改 `pytest.fail`，或拆出不依賴 kline 的 fail-closed 案例。非 B2 阻擋。

---


## 戳記

> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。

RECONCILE-STAMP: codex BLOCKED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R11

RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R11
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R11
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R12

RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R12

RECONCILE-STAMP: codex BLOCKED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R12

RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R13
