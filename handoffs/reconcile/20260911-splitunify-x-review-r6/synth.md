# Reconcile — 20260911-splitunify-x-review-r6

**來源** 20260911-splitunify-x-review-r6-codex.md, 20260911-splitunify-x-review-r6-composer.md, 20260911-splitunify-x-review-r6-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

**Verdict**：需修補後合併——composer `proceed`（R5 五條全閉合、八項實質審查無 P0/P1）；codex 與 grok `blocked`，共開 5 條新 finding（3 P1／2 P2），**全數採納**。R5 之九條已由原提出方確認閉合（codex 自關其 P0、grok 關四條中之四、composer 關五條）；grok 之 R5-P2-02 未閉合、升為本輪 P2-01。修訂後派 R7 由原提出方閉合。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 producer 寫的是全框位置、規格要的是各標的自己的序號**——「D-001-C2要求`row_index」 | P1 | CODEX-R6-P1-01 | 採納（抽驗屬實：切分產生器以全框位置寫入 row_index，而規格第四點要求各標的 post-trim 索引內之序號；交錯標的時會對到錯時刻或越界。修法：規格明定所有具名 producer 轉為標的內序號，並同步修正全框驗證與既有凍結答案之期待；若保留全框語意，須改為明定唯一且可驗證的無損轉換層並附測試） |
| **W2 凍結腳本與接線測試未納入施工範圍**——「導入D-001新mapping/fing」 | P1 | CODEX-R6-P1-02 | 採納（抽驗屬實：凍結腳本有四處舊式呼叫、接線測試建無指紋欄之計畫並以舊式參數呼叫；兩者皆未列入施工檔案清單 ⇒ 只跑新測試切片無法證明既有綠徑仍綠。修法：檔案清單補這兩支，驗證命令加入其對應測試，並要求獨立對照答案逐值比對 producer 寫入之指紋） |
| **W3 指紋列的容器形狀未釘死**——「D-001-C2第1點同時要求指紋與`f」 | P1 | GROK-R6-P1-01 | 採納（抽驗屬實：同一邏輯列以清單形與字典形序列化，雜湊不同。修法：釘死為清單形、元素順序固定，與凍結腳本現行寫法逐字同形；欄位名稱僅作文件稱呼、不進序列化；同步修正凍結腳本註解之舊欄名） |
| **W4 身分分工敘述殘留互斥**——「C1.2經R5改寫後仍稱「同曆同切分的兩」 | P2 | GROK-R6-P2-01 | 採納（我在 R5 把標的納入指紋四元組時，沒同步改掉前一段「指紋不足以分辨」的舊敘述 ⇒ 兩處字面互斥。修法：改為「指紋已含標的、可區分列的歸屬；但三角相等仍是獨立必查，不得只靠指紋」） |
| **W5 覆寫範圍不清**——「觸及面把整節`###C-4…`列為「覆寫」 | P2 | GROK-R6-P2-02 | 採納（整節標覆寫但正文只換簽名，原節其餘約 87 行義務未重述 ⇒ 讀者可能誤以為已廢止。修法：觸及面改標「覆寫其簽名段」，並明示原節其餘段落原文仍有效） |
| **W6 sentinel**——「本輪逐項核對R5composer五條處置」 | P3 | COMPOSER-R6-P3-00 | 採納（紀錄；該家五條全閉合、八項實質審查無新 P0/P1，並接受程序駁回） |

### 本輪程序記錄

1. **三家本輪皆做了實質審查**：codex 已補做它 R5 略過的八項（其 Q2 逐項給立場），並自行關閉其 R5 之程序性 P0——與本票 R5 收斂之駁回結論一致（規則原文「動工前…不動工」管的是實作動工，非唯讀審查）。grok 亦接受該駁回，並指出「若仍主張須先蓋章，須在規則中找到『唯讀審查』之字面——落不到」。
2. **主委抽驗**：三條新 P1 之關鍵碼證逐條抽驗**全部屬實**（producer 全框位置寫入、凍結腳本四處舊呼叫與接線測試無指紋欄、清單形與字典形雜湊不同）。
3. **W1 為本輪最重**：它不是文件措辭問題，而是 producer 與 consumer 的身分契約不一致——R5 我補上了「誰負責寫指紋」，但沒發現「寫進去的 row_index 語意本身」在多標的下就不對。
4. **摩擦（第 13 筆）**：codex 交件之 runlog 達 14568 行而交件檔僅 25 行；另兩家 runlog 僅 40 餘行。過程量體差異極大，但不影響交件品質——本輪 codex 兩條 P1 皆屬實且是最重的一條。記錄供日後評估派工成本。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R6-P1-01
**斷言**: D-001-C2 要求 `row_index` 是各 symbol 的 post-trim `feature_index` 內 positional ordinal，但 Task 8.2 點名的兩個 producer 目前仍輸出全框 position；若直接按新契約投影，交錯 symbol 會把 row 對到錯時刻或越界。
**碼證**: D-001 §C2 lines 58-61、Task 8.2 lines 83-90；`contracts.py:657-661,665-677` 與 `ic_split_adapter.py:230-236` 都以 `positions[local]` 寫入 `row_index`。VERIFY: `rg -n -e 'positions\[.*train_local' -e 'positions\[.*test_local' -e 'row_index=train_rows' momentum/core/contracts.py momentum/Analysis/ic_split_adapter.py` → stdout 命中上述兩 producer；RECHECK: 交錯 A/B fixture 應同時驗證 local/global ordinal 不可混用。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_split_adapter.py#c2dd93482826；momentum/Analysis/event_samples/split_projection.py#98ee62905643
[P1] 信心度=High。這是 producer/consumer identity contract 的實質缺口，不是單純實作偏好。修訂須明定所有 named producer 轉成 symbol-local ordinal，並同步修正 full-frame validation、holdout/既有 golden 期待；或明定唯一、可驗證的無損轉換層與其測試。否則 b8 的 per-symbol path 無法在資料交錯時同時滿足 C2 與現有 producer 語意。
## CODEX-R6-P1-02
**斷言**: 導入 D-001 新 mapping/fingerprint 入口後，現有 golden 與 wiring 綠徑不能由列出的驗證命令涵蓋：golden script 仍呼叫舊 scalar API 且建 plan 不帶 fingerprint，wiring test 仍傳舊 singular pipeline 參數且建 plan 不帶 fingerprint；這些檔案未列入 Task 8.1/8.2 的更新範圍。
**碼證**: D-001 Task 8.1 lines 68-78、Task 8.2 lines 83-97 的檔案/驗證清單未列 script、`test_splitunify_golden.py` 或 wiring test；`freeze_splitunify_golden.py:68-71,145-147,224-225,240-241` 保留舊呼叫；`test_splitunify_golden.py:40-49` 執行該 script；`test_splitunify_wiring.py:68-80` 建立無 fingerprint 的 plan 並傳 singular kwargs。VERIFY: `rg -n -e 'derive_event_split_from_plans\(' -e 'fingerprint_rows' scripts/freeze_splitunify_golden.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py momentum/Analysis/event_samples/split_projection.py` → stdout 命中 script 舊呼叫與 projection 唯一入口；RECHECK: 新簽名後應納入並執行 golden script、golden pytest、wiring pytest，且獨立 oracle 逐值比對 plan fingerprint。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73；scripts/freeze_splitunify_golden.py#6fb0c7361dad；tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e；tests/momentum/event_samples/test_splitunify_wiring.py#0b24aed23fe3；momentum/Analysis/event_samples/pipeline.py#55ca7327764f
[P1] 信心度=High。這會讓 b8 驗收在新 API/欄位落地時於未涵蓋的既有測試面失效，且現行獨立 oracle 只計算 fixture fingerprint，未被要求拿 producer-attested 欄位逐值對證。修訂須把上述 script/test/wiring surface 與更新後命令納入 scope，否則「pytest -k fingerprint/per_symbol」不能證明整條 frozen/golden/wiring 綠徑。
Q1（自身 R5 findings）: `CODEX-R5-P0-01` 關閉；R5 synth 判定為程序性阻塞且拒絕，理由是 Rule 12 的「動工前」限於 implementation；本輪 recheck 兩份 synth stamp 均 rc=1（缺 `## 戳記`），但不改變其 read-only review 性質。
Q2（八項實質裁決）: ①D-vs-R＝D，Task 3.2 明示改寫且未推翻既有設計；②touch set＝覆寫 C-2/Task 3.2/C-4/§N、依賴 §V/§G，C-0/C-1 no-touch，錨點格式檢查通過；③hash＝接受同 symbol train/test 相等、cross-symbol 可共享 joint hash、symbol triangle 對證；④fingerprint＝欄位/型別/empty/duplicate/NaT/normalizer 規則已寫，但 producer local identity 與可執行 oracle scope 未閉合（P1-01/02）；⑤golden＝要求改前/改後逐值重凍及獨立 oracle，但現行 script/test 未納入（P1-02）；⑥ASSERT＝多數可 falsify，惟 non-empty 不等於 digest 正確，需補逐值 oracle；⑦mutation＝M-SU-D1-01..07 已列且 D1-07 命中跨 symbol index 混用；⑧scope＝D1/R5/SU-RESID-2 排除後 single-TF 中間狀態自洽，SU-RESID-2 仍 fail-closed。
Q3（程序性 block）: Reject。AGENTS Rule 12 的精確限制詞是「動工前」；其語義是開始 implementation，不是 read-only review。R5 synth 亦記錄前三輪曾在未 stamped upstream synth 下完成審查，且 consult synth 非 frozen consensus；本輪不要求繞過 stamp，只將它作為程序證據。
Q4（C-4 wrapper）: 可接受的唯一入口是 `derive_event_split_from_plans(plans, event_keys, feature_index_by_symbol, manifest=..., bucket_ms=..., tier_min_test_events=...)`；single-symbol 舊 API 只能由薄 wrapper 包成單鍵 Mapping 後 call-through，多 symbol pipeline 直接傳 Mapping，wrapper 不得複製投影邏輯或保留第二條 scalar logic path。
Q5（是否可進 implementation）: 不可；P1-01 與 P1-02 尚未關閉，先補 producer row identity、完整驗證 surface 與 oracle 後再 proceed。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、brief、D-001、R5/consult synth、amendment procedure；D-001 `doc_format_precheck.sh` rc=0，`template_check.sh dext` rc=0；producer/consumer 靜態證據與 pipeline 舊呼叫已核對。
TESTS_RUN: `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/template_check.sh dext docs/SPLITUNIFY_SPEC.D-001.md` rc=0；兩次 `reconcile_stamps_check.sh` rc=1（均缺 `## 戳記`，作為 Q1/Q3 證據）；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r6-codex.md --family codex` rc=0（2 個 canonical ID）。
FAILURES_SEEN: 上游 R5/consult stamp checker 均報缺 `## 戳記`；未執行 full pytest/governance，未修改測試斷言。
SCOPE_CHANGES: none；未改 tracked code/data，產出檔=`handoffs/20260911-splitunify-x-review-r6-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無數值、schema、golden 或輸出檔變更；僅指出 D-001 新增 `row_time_fingerprint` 的落地與 refreeze 風險。
VERDICT: blocked
BLOCKED-BY: CODEX-R6-P1-01,CODEX-R6-P1-02
CLOSED: CODEX-R5-P0-01
STATUS: DONE
## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 composer 五條處置、D-001 修訂版八項實質審查、C-4 wrapper 新面與程序駁回重驗後，無新增可證偽 P0/P1 finding。

**碼證**: `sha256sum docs/SPLITUNIFY_SPEC.D-001.md`→`9bb033a39a73`；`rg row_time_fingerprint momentum/ --glob '*.py'`→0；八 anchor `git show b095cc7` 各 1 hit；D-001 Task 8.2 `:83-97` producer＋ASSERT；C-4 覆寫 `:16`＋C1 `:28-42`；`M-SU-D1-07` `:117`；`pipeline.py:745-748` 單標的呼叫；`bash scripts/debt_ledger.sh --has-open`→rc=1。RECHECK: 重讀 D-001 全文＋上述命令。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73;handoffs/reconcile/20260911-splitunify-x-review-r5/synth.md

[P3] 信心度=High。R5 採納項均已落字；殘差（Task 8.2 生產 ASSERT 未逐字點名 orchestrator holdout、freeze 腳本未列檔案）在檔案清單與 C2 第 7 點已覆蓋，缺欄會在 derive fail-closed，不構成 b8 假綠路徑。勿捏造 finding。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R5-P1-01,COMPOSER-R5-P1-02,COMPOSER-R5-P2-01,COMPOSER-R5-P2-02,COMPOSER-R5-P2-03

---

ASSUMPTIONS_VERIFIED: D-001 sha256[:12]=`9bb033a39a73`；八 anchor @ b095cc7 各 1 hit；`rg row_time_fingerprint momentum/`→0；`ic_split_adapter.py:189-199` joint hash；`pipeline.py:745-748`；`freeze_splitunify_golden.py:152-155` 四元組；`bash scripts/debt_ledger.sh --has-open`→rc=1
TESTS_RUN: `sha256sum docs/SPLITUNIFY_SPEC.D-001.md`；`git show b095cc7:docs/SPLITUNIFY_SPEC.md` 八 anchor loop；`rg row_time_fingerprint momentum/ --glob '*.py'`；`bash scripts/debt_ledger.sh --has-open`；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r6-composer.md --family composer`→見下
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-x-review-r6-composer.md
TMP_CLEANUP: 已清 `/tmp/workdir-su-r6`（保留 `claude-501`）

STATUS: DONE
## GROK-R6-P1-01

**斷言**: D-001-C2 第 1 點同時要求指紋與 `freeze_splitunify_golden.py`「同一形狀」、又強調「欄名採 `position`／`feature_ts_ms`」，但未釘死 `rows` 是與 freeze 相同的 **list-of-lists** 還是 **list-of-dicts**；兩形之 sha256 不同，b8 會讓 plan 指紋、G-5、獨立 oracle 永久對不齊或各凍一份。

**碼證**: D-001-C2 L56「四元組…同一形狀…`json.dumps(rows, sort_keys=True, …)`…欄名採…`feature_ts_ms`，不得使用舊稱…`ts_ms`」；BASE §G G-5① 文件稱呼含 `feature_ts_ms`；freeze `:152-154` 實作為 `[[int(p), int(ms[p]), SYM, "splitunify-golden"], …]` 且註解寫 `ts_ms`。VERIFY: `venv/bin/python` 對同一邏輯列 list-dumps sha=`da52843ab235…`、dict-dumps sha=`3a725986cbe4…`。RECHECK: 對讀 D-001 L56 與 `sed -n '152,154p' scripts/freeze_splitunify_golden.py`；重跑上述兩形 sha 對照。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73;scripts/freeze_splitunify_golden.py#6fb0c7361dad;docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[BLOCKING] 信心度=High。不改會在 b8 實作／收案失敗：①實作讀「欄名」→用 dict → plan 指紋 ≠ freeze／既有 G-5 演算法；②實作跟 freeze 用 list → 與「欄名／禁 ts_ms」文案衝突，reviewer／第二實作者可改成 dict 而使 ASSERT「同一 index 重算兩次」在不同 helper 間假綠、跨端比對紅。修法：釘死 `rows: list[list]`，元素順序固定為 `[int(position), int(feature_ts_ms), str(symbol), str(base_universe_hash)]`（與 freeze `:153-154` 逐字同形）；「欄名」僅文件稱呼、**不進 JSON**；同步改 freeze 註解之 `ts_ms`→`feature_ts_ms`；Task 8.2 檔案列明 `scripts/freeze_splitunify_golden.py`。

## GROK-R6-P2-01

**斷言**: C1.2 經 R5 改寫後仍稱「同曆同切分的兩個 symbol 可得到相同的時刻序列，指紋不足以分辨」，但 C2.1 已把 `symbol` 納入四元組 payload——兩 symbol 指紋必異，該句為假；屬 GROK-R5-P2-02 修訂殘留。

**碼證**: D-001 C1.2 L48「指紋不足以分辨」；C2.1 L56 四元組含 `symbol`。RECHECK: 構思同 `position`／同 `feature_ts_ms`／同 `base_universe_hash`、不同 `symbol` 之兩列 → dumps 字面不等。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73

[MAJOR] 信心度=High。不擋作唯一 P0，但會誤導實作以為可省略 C1.3，或反向以為指紋已足夠而刪三角相等。修法：刪「指紋不足以分辨」；改為「指紋含 symbol 可區分列所屬標的，但 Mapping key／`plan.symbol`／事件 symbol 之三角相等仍為獨立必查，不得只靠指紋」。閉合後可將 GROK-R5-P2-02 標已閉合。

## GROK-R6-P2-02

**斷言**: 觸及面把整節 `### C-4 …` 列為「覆寫」，但延伸檔沒有 `### C-4` 全文替換塊，只在 D-001-C1.1 給新簽名＋薄 wrapper；BASE C-4 其餘義務（`event_keys` 欄位契約、禁 positional zip、兩段式判定、`build_event_keys` 具名等，約 87 行）未重述——merge 讀者可能把未重述段當成已廢止。

**碼證**: D-001 觸及面 L16 覆寫含完整 C-4 heading；L20 註「新簽名見 D-001-C1 第 1 點」；正文僅 L28-42 簽名塊；`grep -n '兩段式\|build_event_keys\|positional zip' docs/SPLITUNIFY_SPEC.D-001.md` → 無（僅簽名參數名 `event_keys`）；BASE C-4 自 L157 起至下一 `###` 約 87 行。RECHECK: 對讀觸及面表與 BASE C-4 全節。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73;docs/SPLITUNIFY_SPEC.md#3e39458b00e4

[MAJOR] 信心度=Medium。b8 若只改簽名、碼內兩段式仍在，短期不一定紅；但 SPEC 權威若丟 E1／E2，後續 refactor／第二 agent 可合法刪「禁 positional zip」而無規格違規訊號。修法：觸及面改「覆寫 C-4 **簽名段**」並把 BASE C-4 其餘段落改列「依賴（仍有效）」；或在內容貼上「C-4 其餘段落原文仍有效」之明示句。

---

ASSUMPTIONS_VERIFIED: R5 本家 5 條中 4 條閉合、P2-02 殘留升 R6；list vs dict sha 實跑不同；Rule 12 字面僅管動工；觸及面錨點逐字存在；pipeline 仍舊簽名；生產碼無指紋欄
TESTS_RUN: `grep -rn row_time_fingerprint momentum/ --include='*.py'` → 0 hits；`venv/bin/python` list/dict sha 對照 → 兩值不同；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-splitunify-x-consult-r2/synth.md` → rc=1（缺戳記，作 V0 反證材料）；`bash scripts/debt_ledger.sh --has-open` → rc=1（本輪 OPEN，符合 brief 預期）；completeness 見下
FAILURES_SEEN: none（審查輪）
SCOPE_CHANGES: none（僅新增本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r6-grok.md

VERDICT: blocked
BLOCKED-BY: GROK-R6-P1-01
CLOSED: GROK-R5-P1-01,GROK-R5-P1-02,GROK-R5-P2-01,GROK-R5-P2-03
STATUS: DONE
