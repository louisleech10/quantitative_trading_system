# Reconcile — 20260818-gap1-b2-review-r14

**來源** 20260818-gap1-b2-review-codex.md, 20260818-gap1-b2-review-composer.md, 20260818-gap1-b2-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；B2 實作 code review → B2 修補 commit ＋延伸檔 A1-21）

三家共 **21 條** canonical ID（codex 6／composer 5／grok 10）；下列 **十群集 L1–L10 引用全部 21 條，0 掉項**。
三家 Verdict **一致＝「需修補後進 B3」**（無 P0／BLOCKING；無 Verdict 分歧）。分歧只在**嚴重度**
（L2：codex P1 vs grok P2；L5：codex／grok P1 vs composer P2）⇒ 一律**取較嚴版＝本輪修**，不登記殘留。
🔴 主委 brief 四條 assumed 之判定（三家一致）：①`set(row)!=set(schema)` **成立**（刻意折衷，非 bug）
②O_APPEND 含多行程足夠 **推翻**（TOCTOU 被 grok 強制重現）③annualized→`n_rows_rejected` **推翻**
（且 Frozen 字面本身錯）④monkeypatch 未使路徑失覆蓋 **推翻**（三家皆確認零覆蓋）。
主委**接受全部三項推翻**；本輪最重要結果＝**主委在 brief 寫的「實作已計入 n_rows_rejected」與實作不符**
（實作是 schema-valid、不入 valid_sharpe），亦即我對自己的碼描述錯了——三家皆以實跑抓到。

### L1 — 非有限 `metric_value`（NaN／inf）通過 schema、可寫入並進 `valid_sharpe_values`
**引用**: CODEX-R14-P1-02, GROK-R14-P1-02

碼證：`ledger.py:27-32,78-80` 無 finite 檢查；`:234` `json.dumps` 預設 `allow_nan=True`。
grok 實跑：append(nan) 落檔且 read 得 `valid_sharpe_values=(nan,)`、`status=ok`——B3 DSR 之
`variance` 路徑會被投毒。codex 同結論（`NONFINITE ... nan`）。兩家皆 P1；主委複核成立。
**處置（修）**：① `_row_is_valid`：`float` 欄位加 `math.isfinite`（NaN／±inf ⇒ schema-invalid，
讀側計 `n_rows_rejected`＋`ledger_row_invalid`）② `append_trial_attempt` 之 `json.dumps(..., allow_nan=False)`
（雙保險）③ 測試：寫入 nan／inf ⇒ `ContractViolation`；手植 NaN 列 ⇒ `n_rows_rejected==1`、
`valid_sharpe_values==()` ④ 探針新增 **§V-7b**（拿掉 isfinite ⇒ 轉紅）。
契約 `ledger_row_invalid` 之 `condition` 字面補「非有限數值」（延伸檔 A1-21 同步）。

### L2 — 檔存在但全列非法時 `reason` 被強制覆為 `n_unknown`，遮蔽 `ledger_row_invalid`
**引用**: CODEX-R14-P1-02, GROK-R14-P2-01

碼證：`ledger.py:171-172` `n_evaluated==0 ⇒ reason=n_unknown`，即使 `n_rejected>0`。
codex 判 P1、grok 判 P2 ⇒ **取較嚴版＝修**。fail-closed 本身成立（`status=unavailable`、N=0），
問題是運維會誤判「無帳本」而非「帳本損壞」；且 `test_invalid_rows_rejected_with_named_reason`
只斷言 `reasons_seen` 不斷言 `got.reason`（grok 抓到的測試漏洞）。
**處置（修）**：`n_evaluated==0 and n_rejected>0 ⇒ status=unavailable、reason=ledger_row_invalid`；
`n_unknown` 只留給「檔缺／真·零列」；測試加 `got.reason` 斷言（全非法檔 ⇒ `ledger_row_invalid`；
空檔 ⇒ `n_unknown`）。契約 `n_unknown` 之 `condition` 字面不需改（已是「不存在／無任何列」）。

### L3 — annualized 列：實作（schema-valid）與 Frozen TODO／母 SPEC ⑥b 字面（`n_rows_rejected`）矛盾
**引用**: CODEX-R14-P1-03, GROK-R14-P1-01

三家一致：`annualized` 是契約**合法**枚舉（`metric_unit_values`）；A1-7 定義 schema-invalid 只含
「`metric_unit` **非法**」⇒ 實作（schema-valid、計入 `n_evaluated`、**不入** `valid_sharpe_values`）
**對齊 A1-7 且較合理**；TODO:210 ⑥b「計入 `n_rows_rejected`」與母 SPEC ⑥b「記 `reason=ledger_row_invalid`」
是**把合法枚舉誤判為 schema-invalid**。grok 另指出測試 docstring 已靜默跟實作而偏離 Frozen 字面——
後續 agent 若「按字面修回」會破壞 A1-7 不變式。主委 brief 段 D 自述「我計入 `n_rows_rejected`」
**與實作不符**（三家實跑 `n_rows_rejected=0`）——是我描述錯，不是碼錯。
**處置（延伸檔 + 測試鎖）**：Frozen 文件不就地改 ⇒ **A1-21** 作廢 TODO ⑥b 與母 SPEC ⑥b 之
「計入 `n_rows_rejected`／記 `ledger_row_invalid`」句，改為「annualized ⇒ schema-valid、計入
`n_evaluated`（依 `metric_valid` 二分）、`n_rows_rejected` **不**增、**不入** `valid_sharpe_values`」；
`test_valid_sharpe_values_only_per_period` 加顯式 `assert got.n_rows_rejected == 0`
與 `n_evaluated` 含該列之斷言（把「不是 rejected」鎖成可證偽）。

### L4 — `snapshot_hash` 以裸 `|` 拼接可碰撞
**引用**: CODEX-R14-P1-04, COMPOSER-R14-P1-01, GROK-R14-P1-04

三家各自實跑碰撞（`("a|b","c")` vs `("a","b|c")`；`hashes=["x|a"]` vs `dataset_key="a|b"`）。
`dataset_key`／`research_session_id` 契約僅 `str`，無禁 `|`。三家皆 MAJOR。
**處置（修）**：payload 改為 **`json.dumps([sorted(artifact_hashes), dataset_key, research_session_id],
separators=(",",":"), ensure_ascii=False)`**（JSON 序列化對每個字串定界，任何分量含 `|`／`,`／引號皆無歧義），
`sha256` 不變。測試新增三家反例之碰撞回歸（斷言 hash **不等**）；探針新增 **§V-7c**（改回 `|` join ⇒ 轉紅）。
🔴 誠實邊界：既有帳本無（今日無生產者），故無舊 hash 相容問題（面向未來不溯及既往）。

### L5 — `evaluation_id` 唯一性為讀後寫 TOCTOU；append 未綁定 row context；PIPE_BUF 註解不成立
**引用**: CODEX-R14-P1-01, COMPOSER-R14-P2-02, GROK-R14-P1-05, GROK-R14-P2-02

grok 以 barrier 強制重現兩行程同 id 各寫一列（`TOCTOU_CONFIRMED`）；codex 另抓 **`CROSS_CONTEXT`**：
`append_trial_attempt` 只以參數造 path，**不比對** `record["research_session_id"]／["dataset_key"]`
⇒ 一列可寫進別人的帳本；grok 量到 `PIPE_BUF=512 <` 典型列 ≈610B ⇒ 「單次 write 不交錯」註解在
POSIX 嚴格語意下**對本 schema 不成立**。codex／grok P1、composer P2（「今日無生產者」）⇒
**取較嚴版＝本輪修**（唯一寫入口的承諾今天就該成立，不留給生產者落地時再補）。
**處置（修）**：① 掃描＋寫入包在 **`fcntl.flock(LOCK_EX)`**（sidecar `<ledger>.lock`；跨行程／跨執行緒皆互斥；
同時消掉 PIPE_BUF 交錯疑慮，註解改寫）② **context 綁定**：`record` 之 `research_session_id`／`dataset_key`
與參數不等 ⇒ `ContractViolation`（不寫）③ 測試：(a) context mismatch ⇒ raise 且檔不存在
(b) 可證偽 TOCTOU 回歸：模組級 `_after_duplicate_scan_hook`（預設 `None`，測試注入 sleep）＋兩執行緒同 id
⇒ 恰 1 成功 1 `ContractViolation`、檔內 1 列（**拿掉鎖 ⇒ 2 列 ⇒ 紅**）(c) 多**行程**（`subprocess` 4 個、
各寫 >PIPE_BUF 的 8KB 列）⇒ 每列可 `json.loads` 且列數＝4 ④ 探針新增 **§V-7e**（拿掉 flock ⇒ 轉紅）。

### L6 — `ledger_path` 真實推導零測試覆蓋（主委自承最可疑處，三家確認）
**引用**: CODEX-R14-P2-05, COMPOSER-R14-P1-02, GROK-R14-P1-03

三檔 ledger 測試皆 autouse **整函式**替換 `ledger_path` ⇒ `MomentumConfig.results_path/"strategy_validation"/
f"{s}__{d}.jsonl"` 無回歸鎖（grok：改 `strategy_validation` 字面測試仍全綠＝假綠）。
**處置（修）**：① 抽純函式 `_ledger_filename(research_session_id, dataset_key) -> str`（單測字面）
② 新增 `test_ledger_path.py`：**不** patch `ledger_path`，改 patch `MomentumConfig.from_project_root`
回傳 `results_path=tmp`，斷言完整路徑 `tmp/strategy_validation/<s>__<d>.jsonl` 與 parent 名
③ 主委加碼（同群集、路徑安全）：`research_session_id`／`dataset_key` 含 `os.sep`／`..`／NUL／`__`（檔名內兩識別字之分隔符，放行會使 `("a__b","c")` 與 `("a","b__c")` 落同一檔）／空字串／非 str ⇒
`ValueError`（禁 path traversal；今日無生產者，面向未來） ④ 探針新增 **§V-7d**（目錄字面改名 ⇒ 轉紅）。

### L7 — 型別檢核不對稱：`str` 收 `Enum` 子類；`float` 收 `numpy.float64` 但 `int` 拒 `numpy.int64`
**引用**: COMPOSER-R14-P2-01, GROK-R14-P2-03

composer 實跑 `class S(str, Enum)` 之 `metric_unit` 通過；grok 實跑 `np.float64` 通過而 `np.int64` 被拒。
**處置（修，取較嚴＝只收純 Python 純量）**：`_row_is_valid` 改用 **`type(value) is`** 精確比對
（`str`→`str`；`int`→`int`；`float`→`float`／`int`；`bool`→`bool`），Enum／numpy 純量一律拒
（讀側 JSON 解出的本就是純 Python 型別，不受影響；寫側生產者須自行 `float(x)`／`int(x)`，
docstring 明寫）。測試：Enum／`np.float64`／`np.int64`／`"true"` 四者皆 `ContractViolation`。

### L8 — 契約 loader fail-open（不驗頂層鍵集合／不驗枚舉 membership）＋ `_contract_cache` 可被外部改
**引用**: CODEX-R14-P2-06, GROK-R14-P3-02

codex 實跑：多一個未知頂層鍵仍 load 成功；`universe_scope` 非法值通過 `validate_against_contract`；
`load()` 回傳即快取物件（`CACHE_MUTATION True`）。grok／composer 段 B6 同指 Rule 8 衝突。
**處置（修）**：① loader 驗**頂層鍵集合恰為 16**（`_EXPECTED_TOP_LEVEL_KEYS` frozenset；多／少即 raise）
② `validate_against_contract` 之枚舉檢查改為**機械對映**：obj 之鍵 `k` 若契約存在 `f"{k}_values"`
⇒ 值須屬該枚舉（涵蓋 `universe_scope`／`metric_unit`／`n_semantics`／`t_semantics`／`annualization_source`／
`variance_source`／`universe_source`／`selection_metric`；`status`／`reason` 維持既有）
③ 快取改 **`(mtime_ns, size)` 鍵控**＋回傳 **deepcopy**（外部改不到快取；檔變即失效）；
`_row_is_valid` 改收 `contract` 參數，讀迴圈只 load 一次（原本每列都 load）。
🔴 誠實邊界：仍是模組級 memo（非 singleton 狀態），Rule 8 之精神已滿足（不可變、鍵控失效）；不宣稱「已無快取」。

### L9 — `set(row)!=set(schema)` 使缺鍵／額外鍵同 reason；`reasons_seen[0]`（刻意折衷，接受）
**引用**: GROK-R14-P3-01

三家一致：契約只有單一 `ledger_row_invalid`，正確性無損。**處置（微修）**：`append_trial_attempt`
之錯誤**訊息**列出 `missing=[...]／extra=[...]／bad_type=[...]`（reason 字面不變）；讀側不改。

### L10 — B2 之 mutation 探針缺口
**引用**: COMPOSER-R14-P3-01

**處置（修）**：探針 8 → **12** 條：新增 §V-7b（isfinite 拿掉）／§V-7c（snapshot 改回 `|`）／
§V-7d（`strategy_validation` 目錄字面改名）／§V-7e（flock 拿掉），每條 rc=1 且 FAILED≥1；
互斥鎖不變、只由一家跑。B2 Gate 文字同步為「§V-7／7b／7c／7d／7e」。

**Verdict**: 需修補後合併 → 修補於 B2 修補 commit ＋延伸檔 A1-21；三家戳記後進 B3。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R14-P1-01
**斷言**: append 未綁定 record 的 research_session_id/dataset_key，且 evaluation_id 檢查是讀後寫；可跨帳本污染並讓同 ID 併發重複落列。 **碼證**: ledger.py:210-236 只以參數造 path、未比對 row context；反例 `CROSS_CONTEXT 1`；兩 writer 可同時讀空檔後各 write；RECHECK: two-process same evaluation_id。
**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19；tests/.../test_ledger_conformance.py#164199e6a7dd。P1 信心=10/10；修法是 atomic uniqueness/lock 或 durable unique index，並拒絕 context mismatch。
## CODEX-R14-P1-02
**斷言**: metric_value 的 NaN/inf 會通過 schema gate，且檔案全為非法列時公開 reason 被錯置為 n_unknown。 **碼證**: ledger.py:66-84 未 isfinite、json.dumps 預設 allow_nan；:167-174 強制 n_evaluated==0 時 n_unknown；反例 `NONFINITE ... nan`、`INVALID_ONLY unavailable n_unknown 1 ('ledger_row_invalid',)`。
**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19；BRIEF#5fd6d3654564。P1 信心=10/10；修法是拒絕非有限 metric_value，並保留 ledger_row_invalid；補 invalid-only/inf 測試。
## CODEX-R14-P1-03
**斷言**: annualized 是契約合法 enum，實作把它 schema-valid 且排除 valid_sharpe_values；這符合資料語意但不符合 Frozen TODO ⑥b 的 rejected 字面，B2 gate 無法同時滿足兩者。 **碼證**: contract.json:168-169；ledger.py:81-83,150-153；反例 `ANNUALIZED ok  1 0 () ()`；RECHECK: run annualized row。
**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#3cc06afd3b47；docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#d239583e439c。P1 信心=10/10；不可直接改 frozen 文件，須走延伸裁決：合法 enum 應 schema-valid/filter，或移除 enum 後才 reject。
## CODEX-R14-P1-04
**斷言**: snapshot_hash 的 `|` 未 escape/length-prefix，dataset_key 或 research_session_id 含分隔符即可碰撞不同輸入。 **碼證**: ledger.py:161-165；`{a},b|c,d` 與 `{a},b,c|d` 都串成 `a|b|c|d`，實跑 `SNAPSHOT_COLLISION True`。
**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#3cc06afd3b47；momentum/.../ledger.py#5f914fb8cb19。P1 信心=10/10；修法是 canonical length-prefix/JSON tuple，並新增 delimiter-in-id collision test。
## CODEX-R14-P2-05
**斷言**: 測試 fixture monkeypatch ledger_path，故真實 `MomentumConfig.results_path/strategy_validation/<session>__<dataset>.jsonl` 推導完全未覆蓋。 **碼證**: test_ledger.py:17-25、test_ledger_conformance.py:20-25 以 fake path 取代 ledger_path；ledger.py:56-59 才是 production path；現有 90 tests 仍全綠。
**來源摘要**: tests/.../test_ledger.py#43477bd8daf2；tests/.../test_ledger_conformance.py#164199e6a7dd。P2 信心=10/10；修法是保留隔離 fixture 外，加入 config-backed path test，並覆蓋 process/large-line/duplicate-id/context/non-finite cases。
## CODEX-R14-P2-06
**斷言**: `_contract_cache` 是可被 caller 修改的 mutable global 且無 mtime/version key；loader 亦不拒絕 unknown top-level key 或 report enum，會造成 stale/漂移 fail-open。 **碼證**: contract.py:29,66-88,143-160；反例 `CACHE_MUTATION True True`、`UNKNOWN_TOP_LEVEL accepted True`、`ENUM_VALIDATION accepted invalid universe_scope`。
**來源摘要**: momentum/Analysis/strategy_validation/contract.py#de4d4a4270f0；CLAUDE.md The 7 Decoupling Rules Rule 8。P2 信心=10/10；修法是 immutable/no cache 或 keyed invalidation，並在 load/validate 強制 exact top-level 與各 enum membership。
STATUS: DONE
## COMPOSER-R14-P1-01

**斷言**: `snapshot_hash` 以裸 `|` 拼接 `dataset_key` 與 `research_session_id`，存在不同 `(dataset_key, session)` 組合產生相同 SHA-256 的可執行碰撞。

**碼證**: `ledger.py:161-165`：`",".join(sorted(artifact_hashes)) + "|" + dataset_key + "|" + research_session_id`。RECHECK：`venv/bin/python -c` 計算 `snap({"h1"},"a|b","c")` 與 `snap({"h1"},"a","b|c")` → 兩者皆 `690f6a9b75db556d…`（本輪實跑 collision=True）。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。不同研究 session／dataset 組合可綁到同一 `snapshot_hash`，Task 3.2 snapshot 守衛可能誤判或漏判 `ledger_snapshot_mismatch`。修法：改用 length-prefix／JSON tuple／`\x00` 等不可歧義編碼，並加碰撞回歸測試。

---

## COMPOSER-R14-P1-02

**斷言**: 全部 ledger 測試以 `monkeypatch.setattr(ledger_mod, "ledger_path", …)` 繞過真實路徑推導，使 `MomentumConfig.results_path` 與 `f"{session}__{dataset}.jsonl"` 命名**零覆蓋**。

**碼證**: `test_ledger.py:17-25`、`test_ledger_conformance.py:20-26` autouse patch；`ledger.py:56-59` 真實 `ledger_path` 無任何測試 import 不 patch 之路徑。RECHECK：`rg 'ledger_path' tests/momentum/Analysis/strategy_validation` 僅見 monkeypatch，無 `MomentumConfig` 斷言。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。`results_path` 配置錯誤或檔名模板回歸不會被 90 條測試抓到。修法：加一則不 patch 之整合測試（`monkeypatch.setenv`／tmp `MomentumConfig`）斷言 `ledger_path(...)` 結尾路徑；或抽純函式 `_ledger_filename(session, dataset)` 單測。

---

## COMPOSER-R14-P2-01

**斷言**: `_row_is_valid` 對 `str` 欄位使用 `isinstance(value, str)` 語意（經 `_PY_TYPES["str"]=(str,)`），`enum.Enum` 子類可冒充 `metric_unit` 等字串欄位通過 schema。

**碼證**: `ledger.py:77-80`；本輪探針 `class S(str, Enum): X="per_period"` → `_row_is_valid(..., metric_unit=S.X)` **valid=True**。RECHECK：同上 Enum 探針。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=High。生產者若傳 Enum 物件，`json.dumps` 可能失敗或序列化意外；讀端 `isinstance` 過寬。修法：`type(value) is str` 或拒絕 `enum.Enum` 實例；補測試。

---

## COMPOSER-R14-P2-02

**斷言**: `append_trial_attempt` 之重複 `evaluation_id` 檢查為讀全檔後再 append，無檔案鎖或原子寫入，多行程並發下兩寫者可同時通過檢查並各寫一列。

**碼證**: `ledger.py:219-236` 先 `open("r")` 掃描再 `open("a")` write；無 `fcntl.flock`／`os.replace`。執行緒探針 10 併發同 id → 1 成功（GIL 下僥倖）；架構上為經典 TOCTOU。RECHECK：兩 process 同時 `append_trial_attempt` 同 `evaluation_id`（需 `fork`+`PYTHONPATH`）。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=Medium（多行程未在本機穩定重現，但讀-改-寫模式明確）。G1-R1 無生產者今日風險低；未來 `ProcessPool` 寫帳本可能 N 灌水。修法：`fcntl.flock`、或寫入前 `os.open(..., O_APPEND|O_EXCL)` 配合 sidecar lock；文件化單寫者假設。

---

## COMPOSER-R14-P3-01

**斷言**: mutation 探針僅覆蓋 B2 之 §V-7（缺檔回 n=1），未對 `snapshot_hash` 拼接、`ledger_path` 推導、Enum 型別陷阱等 B2 關鍵語意設 mutant。

**碼證**: `scripts/gap1_b1_mutation_probe.sh` 末段 §V-7 改 `ledger.py`；無 `snapshot_hash`／`ledger_path`／`_row_is_valid` str 檢查之 mutant。receipt `20260818T030000Z-gap1-mutation-locked.log` 八條皆 B1 域。RECHECK：grep probe 腳本無 `snapshot_hash`／`ledger_path`。

**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e

[MINOR] 信心度=High。B2 回歸依賴單元測試而無 mutation 自證。修法：B2 收案前增 §V-7b（delimiter 移除）、§V-7c（id 檢查刪除）等；或 B3 gate 明列最低 mutant 集。

---

## GROK-R14-P1-01

**斷言**: Frozen TODO／母 SPEC 之 Task 2.2 驗證⑥b 要求 annualized 計入 n_rows_rejected 並記 ledger_row_invalid，但實作與 test 將其當 schema-valid（只排除出 valid_sharpe_values），且無 A1 修訂——驗收閘已靜默偏離 Frozen 字面。

**碼證**: TODO:210 字面 vs ledger.py:150-153 實作 vs test_ledger.py:121 docstring；VERIFY annualized+per_period 兩列 n_evaluated=2 n_rows_rejected=0 valid_sharpe=(1.1,)；A1-7 僅 metric_unit 非法才 schema-invalid；RECHECK 寫 annualized 合法列後比 TODO 字面與實作計數。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#3cc06afd3b47

[MAJOR] 信心度=High。實作選擇合理（合法枚舉不應 schema-reject）；失敗模式是文件／閘漂移——後續 agent 按 Frozen 字面「修好」測試會破壞 A1-7。修法：延伸檔作廢 ⑥b 之 n_rows_rejected 句，改為 schema-valid 但不入 valid_sharpe_values；測試加顯式 assert n_rows_rejected==0。

## GROK-R14-P1-02

**斷言**: _row_is_valid／append_trial_attempt 接受非有限 metric_value（NaN／inf）；metric_valid=True 時 NaN 進入 valid_sharpe_values，會在 B3 DSR statistics.variance 路徑投毒。

**碼證**: ledger.py:27-32,78-80 無 finite 檢查；ledger.py:234 json.dumps 預設 allow_nan=True；VERIFY append(nan) 檔內 metric_value: NaN 且 read 得 n_evaluated=1 n_rows_rejected=0 valid_sharpe_values=(nan,) status=ok；RECHECK 另測 inf。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。今日無生產者仍應在唯一寫入口 fail-closed。修法：math.isfinite(metric_value) 納入 schema；json.dumps(..., allow_nan=False)；讀側對非有限值計 n_rows_rejected。

## GROK-R14-P1-03

**斷言**: test_ledger.py 與 test_ledger_conformance.py 以 monkeypatch 整函式替換 ledger_path，使 TODO 規定的 MomentumConfig.results_path/strategy_validation/{session}__{dataset}.jsonl 路徑推導零覆蓋。

**碼證**: TODO:195 路徑公式；ledger.py:56-59 真實推導；test_ledger.py:18-25 與 test_ledger_conformance.py:20-26 autouse 全替換；測試目錄無 MomentumConfig/results_path 斷言；手動真實路徑正確但無鎖；RECHECK 改 strategy_validation 字面後測試仍全綠即假綠。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_ledger.py#43477bd8daf2

[MAJOR] 信心度=High。主委自承最可疑處，本輪確認。修法：至少一則測試 patch MomentumConfig.from_project_root（或 results_path）而非整顆 ledger_path，斷言 parent 名與檔名格式。

## GROK-R14-P1-04

**斷言**: snapshot_hash 以裸 | 拼接 artifact_hashes／dataset_key／research_session_id，當任一分量含 | 時不同輸入可產生相同 digest（provenance 碰撞）。

**碼證**: ledger.py:161-165 公式；VERIFY snap(["x"],"a|b","c")==snap(["x|a"],"b","c") 同 hex；dataset_key 契約僅 str 無禁 |；RECHECK 重算兩組 sha256 payload。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High。修法：對各欄先分別 hash、或 json.dumps([sorted(hashes),dk,sid])、或長度前綴編碼，禁止可逆拼接歧義。

## GROK-R14-P1-05

**斷言**: append_trial_attempt 的 evaluation_id 唯一性是先掃檔再 append 的 TOCTOU；多行程在 check 通過後 write 前交錯時可寫入相同 evaluation_id 兩列，N／候選計數可被灌水。

**碼證**: ledger.py:219-237 無鎖讀後寫；VERIFY 鏡像控制流於 check/write 間 barrier 兩行程皆 WROTE n_lines=2 eids=['DUP','DUP'] TOCTOU_CONFIRMED；既有測試僅 ThreadPoolExecutor 同行程；RECHECK 多行程同 id 並發 append。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR] 信心度=High（結構性漏洞已強制重現；無 barrier 時窗口窄但非零）。主委 assumed 含未來多行程生產者足夠 不成立。修法：fcntl.flock 包住掃+寫；或每 id O_CREAT|O_EXCL；或文件化單寫者並改測。今日無生產者可進 B3 但須登記殘留或本輪修。

## GROK-R14-P2-01

**斷言**: 當檔存在但零列 schema-valid（全非法）時 reason 被強制設為 n_unknown，掩蓋 reasons_seen 中的 ledger_row_invalid，與非法列應帶 ledger_row_invalid 字面的直觀／SPEC 驗證⑧部分衝突。

**碼證**: ledger.py:171-174 n_evaluated==0 強制 n_unknown；VERIFY 檔 {bad 得 status=unavailable reason=n_unknown n_rows_rejected=1 reasons_seen=(ledger_row_invalid,)；test_invalid_rows 只 assert reasons_seen 不斷言 got.reason；RECHECK 只寫非法列後讀 got.reason。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MAJOR 偏 P2] 信心度=High。fail-closed 仍成立（status 非 ok、N=0）；運維會誤判無帳本而非帳本損壞。修法：n_evaluated==0 and n_rows_rejected>0 時 reason=ledger_row_invalid。

## GROK-R14-P2-02

**斷言**: 註解宣稱單次 write 併發追加不交錯（POSIX O_APPEND）在本機 PIPE_BUF=512 下對典型帳本列 encode 約 610B 並無 POSIX 原子性保證。

**碼證**: ledger.py:236 註解；VERIFY os.pathconf PIPE_BUF=512 且典型 12 鍵列 len(encode)约610；4 行程 x 8KB 本輪未見交錯不足為證；RECHECK 量 PIPE_BUF 與線長後 fuzz。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=Medium（標準語意高；實害需壓力才現）。修法：文件化單寫者；或寫入前強制線長<=PIPE_BUF；或檔級鎖。

## GROK-R14-P2-03

**斷言**: int 欄拒 numpy.int64，float 欄收 numpy.float64——未來 numpy 生產者會在 attempt_index 上噴 ContractViolation，而 metric_value 靜默通過，行為不對稱。

**碼證**: VERIFY _row_is_valid attempt_index=np.int64(0) False；metric_value=np.float64(1.2) True；RECHECK 同上。

**來源摘要**: momentum/Analysis/strategy_validation/ledger.py#5f914fb8cb19

[MINOR] 信心度=High。今日無生產者。修法：寫入口統一 int(x)/float(x) 正規化（拒 bool），或文件要求純 Python 純量。

## GROK-R14-P3-01

**斷言**: set(row)!=set(schema) 使缺鍵與額外鍵共用 ledger_row_invalid，診斷不可分；在契約單一 reason 設計下為刻意折衷。

**碼證**: ledger.py:70-71 一次 set 相等；契約 reasons 無 finer codes。

**來源摘要**: momentum/Analysis/contracts/strategy_validation_contract.json#4a0ef05b2e1a

[MINOR] 信心度=High。非正確性 bug。可選：錯誤訊息區分 missing vs extra（仍同一 reason 字面）。

## GROK-R14-P3-02

**斷言**: contract._contract_cache 為模組級可變快取（default 路徑），與 Rule 8 精神衝突；同行程改契約檔會讀到舊值。

**碼證**: contract.py:29,66-88 global cache；load 兩次 is 同一物件。

**來源摘要**: momentum/Analysis/strategy_validation/contract.py#de4d4a4270f0

[MINOR] 信心度=High。生產可接受；測試改 default 檔需 cache clear 或重載模組。屬既有 singleton 技術債族。

---


## 戳記
