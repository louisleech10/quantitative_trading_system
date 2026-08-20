# GAP-3 TODO 對抗審 R7 — codex

TASK_ID: 20260820-GAP3-X-REVIEW-R7
SCOPE: `docs/GAP3_EVENT_TODO.md` 對 `docs/GAP3_EVENT_SPEC.md`；只產 review，不改碼／SPEC／TODO。

## Verdict：需修補後派工（不 Frozen）

本輪確認 20 Task 均有對應；下列 11 個 finding 需在 TODO 凍結前處理。§V M1–M12 逐字重驗通過，但這不抵銷 §G oracle、Task executable depth 與 SoT/白名單矛盾。

## CODEX-R7-P1-01

**斷言**: TODO 宣告 JSON 是唯一欄位/枚舉/reason SoT，卻在 B1.0 與 B2.4 再列出契約鍵、枚舉與 survivor 新欄，形成第二份可漂移來源。

**碼證**: `rg -n 'JSON SoT|required_fields|entry_price_semantic|failure_reasons|event_manifest_hash|label_definition_hash' docs/GAP3_EVENT_TODO.md` 命中 §0-5（line 14）、B1.0（line 55）及 B2.4（line 265）；`docs/GAP3_EVENT_TODO.md:5,14` 同時寫「本檔與程式禁複列鍵表」及「各 Task 僅寫 pointer」。RECHECK: `sed -n '5,15p;51,66p;261,269p' docs/GAP3_EVENT_TODO.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P1] 信心度=High；B1.0 或 B2.4 之後只要契約升版，TODO 的複列內容就可能與實際 JSON 不同，冷啟動 agent 也無法判斷哪一份優先。刪除實際鍵表/枚舉/新欄名稱，只保留契約檔 pointer；保留必要的行為語意與驗證條件。

## CODEX-R7-P1-02

**斷言**: TODO §0-6 的「既有檔白名單」會阻止 B5.1 必改的 `momentum/factories.py` 與 B5.3 必改的文件檔，和同一份 TODO 的 Task 修改清單互斥。

**碼證**: `docs/GAP3_EVENT_TODO.md:15` 的六項白名單沒有 `momentum/factories.py`、`docs/ROADMAP.md`、`docs/IC_QUANT_GAP_REGISTRY.md`、`HANDOFF.md` 或 `白話說明/`；但 `docs/GAP3_EVENT_TODO.md:419-425` 要新增 `create_event_sample_pipeline()` 並修改 `momentum/factories.py`，`docs/GAP3_EVENT_TODO.md:453-455` 要修改上述收尾文件。SPEC 的 §RISK 也明定 B5 需要 factory 出口（`docs/GAP3_EVENT_SPEC.md:19`）。RECHECK: `sed -n '15p;419,425p;448,455p' docs/GAP3_EVENT_TODO.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P1] 信心度=High；执行端若遵守全域禁令，会跳过 factory 与收尾文件；若遵守 Task，又违反全域 scope。把「既有檔白名單」明確改成「既有檔」例外/新增檔的完整允許範圍，並把 factory 與 B5 文件列入可改清單。

## CODEX-R7-P1-03

**斷言**: SPEC §G-3(i) 要求「二元辨別與 conditional IC」皆通過固定 seed 置亂 chance-level CI，但 TODO 只把置亂 oracle 落到 B1.4 的 binary baseline，B2.3 沒有 conditional-IC 置亂 oracle 或 Gate 斷言。

**碼證**: SPEC `docs/GAP3_EVENT_SPEC.md:119` 明列 binary/conditional IC；TODO `docs/GAP3_EVENT_TODO.md:166-171` 的 oracle 與驗證只有 B1.4 binary，`docs/GAP3_EVENT_TODO.md:246-257` 的 B2.3 驗證只有 conditional IC 接線、golden 與 fallback，`docs/GAP3_EVENT_TODO.md:37` 的 B2 Gate 也沒有 conditional-IC permutation check。RECHECK: `rg -n 'conditional_ic|置亂|chance|permutation|B2 Gate' docs/GAP3_EVENT_TODO.md`。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2a; docs/GAP3_EVENT_TODO.md#511c3f1b3b84

[P1] 信心度=High；B2 可在條件 IC 接線通過而未驗證 label 置亂是否落入 null band，量化結果可能被誤當訊號。把 conditional-IC permutation test、固定 seed/quantile 判準與其 Gate 歸入 B2.3 或共用 oracle，不能只寫「沿 B1.4」。

## CODEX-R7-P1-04

**斷言**: SPEC §G-4 的 digest tamper fail-closed oracle 沒有落到 TODO 的任何 B1.0 驗證或批次 Gate。

**碼證**: SPEC `docs/GAP3_EVENT_SPEC.md:120` 要求「digest 篡改 ⇒ 拒」；TODO `docs/GAP3_EVENT_TODO.md:63,69` 的 validator/驗證列缺 digest tamper case，B1 Gate `docs/GAP3_EVENT_TODO.md:36` 也未列；TODO 的追溯宣稱 `docs/GAP3_EVENT_TODO.md:487` §G 已全數入欄，與此遺漏不符。RECHECK: `rg -n 'digest|篡改|契約 oracle|B1 Gate' docs/GAP3_EVENT_TODO.md docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2a; docs/GAP3_EVENT_TODO.md#511c3f1b3b84

[P1] 信心度=High；輸入資料快照或來源 digest 被改寫時，TODO 沒有可證偽的拒絕測試，契約完整性 Gate 可假綠。補入 B1.0 的 mutation/negative fixture、預期 reason/rc，並讓 B1 Gate 明列。

## CODEX-R7-P1-05

**斷言**: B1.6 要求 warmup 不足進 failure enum，但其輸出型別只有 `(features_at_decision, feature_manifest_hash)`，沒有 failures 的回傳、receipt 欄位或明確 raise 契約。

**碼證**: `docs/GAP3_EVENT_TODO.md:136-150` 同時指定二元 tuple 輸出與「warmup 不足 ⇒ 該事件入失敗枚舉、非 NaN 混入」；B1.1 的失敗 DataFrame 只屬另一函式輸出（`docs/GAP3_EVENT_TODO.md:75,80`）。RECHECK: `sed -n '134,152p' docs/GAP3_EVENT_TODO.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P1] 信心度=High；实现者可能静默丢事件、返回带 NaN 的特征，或自行发明异常类型，均会破坏数据质量与记账守恒。明确返回 `(features, hash, failures)`、或明确统一抛出契约异常并说明调用端如何保留逐事件 reason；补对应断言。

## CODEX-R7-P1-06

**斷言**: B3.1 的驗證要求 `expression_role=feature` 時拒絕 future 欄，但 `parse_condition(expression, column_registry)`／`evaluate_condition(spec, df)` 沒有 expression role 輸入或 `ConditionSpec` 的角色上下文，無法同時允許 selection predicate 使用未來欄並拒絕 feature 使用未來欄。

**碼證**: TODO `docs/GAP3_EVENT_TODO.md:309-319` 的簽名只收 expression/column registry，卻在 line 319 寫 `selection_predicate` 可含未來欄、`feature` 必拒；驗證命令在 `docs/GAP3_EVENT_TODO.md:324` 又傳入未出現在簽名的 `expression_role=feature`。SPEC D3 同時要求這兩種角色語意（`docs/GAP3_EVENT_SPEC.md:41-45`）。RECHECK: `sed -n '309,325p' docs/GAP3_EVENT_TODO.md; sed -n '41,45p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P1] 信心度=High；实现者只能选择把所有 future 欄拒绝（错误地禁止合法 selection predicate），或放行 future 欄（泄漏到 feature）。为 expression context 增加 typed `expression_role`/role-aware AST contract，并同时给出 selection-predicate allowed 与 feature rejected 两个可执行案例。

## CODEX-R7-P1-07

**斷言**: B3.3 只列五个 state-counter 名称与一个示例签名，没有定义 cross/threshold/run/ratio/count 的精确公式、边界含义、方向、NaN/哨兵规则，无法让独立 agent 产出同一列语义。

**碼證**: TODO `docs/GAP3_EVENT_TODO.md:343-354` 只给出五个名称、`bars_since_cross` 一个签名、lookback/warmup 与「NaN 或哨兵」；SPEC `docs/GAP3_EVENT_SPEC.md:296-305` 同样只给名称与窗口约束，未提供可验证的算子定义。RECHECK: `sed -n '343,354p' docs/GAP3_EVENT_TODO.md; sed -n '296,305p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P1] 信心度=High；这是 Feature Factory 因果语义高风险路径，`cross_count` 是否含当前根、`window_max_ratio` 分子/分母、cross 方向与 warmup 结果都会改变特征值；现有「手算 exact」没有唯一 oracle。补每个算子的 typed 签名、公式/索引闭区间、NaN/哨兵值与至少一个 exact expected case；若需改 SPEC，应另走 amendment，不在 TODO 私自发明。

## CODEX-R7-P1-08

**斷言**: B4.2 的 `to_return_series(rule_or_scores, bars, entry_semantic)` 没有 exit/horizon/label window、decision offset 或 label mode 输入，无法保证「同 entry/exit 语意」而生成可供 DSR/PBO 消费的 OOS return series。

**碼證**: TODO `docs/GAP3_EVENT_TODO.md:384-400` 的输入只写 pattern/rule＋bars＋entry semantic，签名也只有三项；SPEC `docs/GAP3_EVENT_SPEC.md:322-331` 只要求同 entry/exit 语意与 GAP-1 对接，未在 TODO 补足退出窗来源。RECHECK: `sed -n '384,400p' docs/GAP3_EVENT_TODO.md; sed -n '322,331p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P1] 信心度=High；实现者会自行选择 horizon/label end，可能把事件标签收益、实际进场收益与 DSR/PBO 的 return series 混用。令函数接收 `AlignmentReceipts`/label-definition/exit config（或明确从 candidate provenance 解析），并测试 `D1-6` 各 entry semantic 与退出窗一致性。

## CODEX-R7-P2-09

**斷言**: B1.2 的关键 scenario=C primary assertion 不是可执行命令，TODO 用了字面 `ASSERT …`。

**碼證**: `docs/GAP3_EVENT_TODO.md:110` 为 `venv/bin/python -m pytest ...` 后接 `ASSERT … WHEN scenario=C policy=primary THEN rc=0`；SPEC `docs/GAP3_EVENT_SPEC.md:162` 有完整的 `ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q WHEN scenario=C policy=primary THEN rc=0`。RECHECK: `sed -n '110p' docs/GAP3_EVENT_TODO.md; sed -n '162p' docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P2] 信心度=High；V13 深度紅線要求每 Task 的驗證可直接執行，現況无法机械验收「簇首代表＝interval 最早」，应恢复 SPEC 的完整命令或给出等价可跑的 pytest 参数。

## CODEX-R7-P2-10

**斷言**: B5 的前端/UAT gate 没有给出可直接复制的 vitest 命令、测试路径、UAT 脚本路径或实际执行入口，无法完成冷启动验收。

**碼證**: TODO `docs/GAP3_EVENT_TODO.md:40` 只有裸词 `vitest`，`docs/GAP3_EVENT_TODO.md:444` 写「vitest 对事件模式入口与两表渲染之测试」，`docs/GAP3_EVENT_TODO.md:450-459` 写 UAT checklist/使用者签字但没有 checklist 文件或脚本路径。RECHECK: `sed -n '40p;433,465p' docs/GAP3_EVENT_TODO.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; templates/TODO_GENERATION_PROMPT.md#b5849908f02d

[P2] 信心度=High；B5 Gate 可只跑 build 而漏掉事件入口、两表、unavailable/empty state 的行为测试，UAT 也无法按文档复现。补 `npm` script 或 `npx vitest run <paths>`，并指定 UAT checklist/runner 文件及其逐项命令。

## CODEX-R7-P2-11

**斷言**: B5.1 的「万级事件分頁/串流不 OOM、實測記錄牆鐘」没有指定输入规模、内存/时间基线或通过阈值，属于不可证伪的性能验收。

**碼證**: TODO `docs/GAP3_EVENT_TODO.md:427` 只写万级事件与记录墙钟，`docs/GAP3_EVENT_TODO.md:464` 仍只写「实测记录」；SPEC `docs/GAP3_EVENT_SPEC.md:341` 同样没有规模/阈值，§V `docs/GAP3_EVENT_SPEC.md:386-387` 将其列为边界/侦察待办。RECHECK: `rg -n '萬級|万级|OOM|牆鐘|墙钟|T-3|T-4' docs/GAP3_EVENT_TODO.md docs/GAP3_EVENT_SPEC.md`。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2a

[P2] 信心度=High；在没有可重复 scale/threshold 前，streaming 是否足够与性能是否回归无法判定。补来源可证明的 workload、测量命令、内存/墙钟基线与 pass/fail，或把 B5.1 派工前的侦察结果作为明确前置 Gate；不要在 TODO 私自捏造门槛。

## 必答：20 Task 逐一抄寫漂移比對

逐欄核對目標／檔案／改法／驗證／邊界／不可做／存活至／覆蓋風險；「有」列出本輪 finding，其餘為「無」。

| Task | 結果 |
|---|---|
| B1.0 | 有：P1-01（SoT 重複）、P1-04（digest tamper oracle 漏接） |
| B1.1 | 無 |
| B1.2 | 有：P2-09（ASSERT 不可執行） |
| B1.3 | 無 |
| B1.6 | 有：P1-05（warmup failure 輸出契約缺口） |
| B1.4 | 無 |
| B1.5 | 無 |
| B2.1 | 無 |
| B2.2 | 無 |
| B2.3 | 有：P1-03（conditional-IC permutation oracle 未落地） |
| B2.4 | 有：P1-01（survivor 欄位重複列舉） |
| B2.5 | 無 |
| B3.1 | 有：P1-06（expression role context 缺失） |
| B3.2 | 無 |
| B3.3 | 有：P1-07（五個算子語意不足） |
| B4.1 | 無 |
| B4.2 | 有：P1-08（exit/label window 輸入不足） |
| B5.1 | 有：P1-02（白名單衝突）、P2-11（性能驗收不可證偽） |
| B5.2 | 有：P2-10（vitest 命令/測試路徑缺失） |
| B5.3 | 有：P1-02（文件白名單衝突）、P2-10（UAT runner/checklist 路徑缺失） |

## 必答：§V M1–M12 逐字重驗

實跑命令：`diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \\*\\*mutation 條件\\*\\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → stdout 空，`RECHECK_RC=0`。结论：M1–M12 byte-identical，未发现抄写增删；本轮 finding 来自其他 Task/Gate 缺口，不是 mutation 表漂移。

## 必答：TODO 相對 SPEC 的新增內容

- B2 批內順序與「B2.4 升版前不得寫 v2 payload」：核對後屬可執行細化，且不違反 SPEC 的 B2.3 動工前 §G 凍結與 `additional_properties:false`；無 finding。
- §G-1 復用 `scripts/gap2_freeze_golden.py::gap2_canonical_sha`、不另立 scrub 清單：已讀實檔；命令 `rg -n 'def gap2_canonical_sha|_META_SCRUB|marginal_ic|survivor_output|scope_id' scripts/gap2_freeze_golden.py` 命中唯一實作與相同 scrub 項，屬合法細化；無 finding。
- `ic_feed.py`、`generator.py`、`pipeline.py`、`types.py`、`create_event_sample_pipeline()`、`AlignmentReceipts`：均為 TODO 階段將 SPEC 的餵入層／產生器／factory／兩層 receipt 具名化，未見改變 frozen 行為；無 scope-accretion finding。B3.1/B4.2 的輸入語意問題另由 P1-06/P1-08 處理。

## 必答：V13 深度紅線與錨點

錨點與每 Task 的「實作要點／修改檔案／驗證／邊界／存活至／覆蓋風險」機械存在，且 20 Task 均有內容；但語義紅線未全過：P1-05、P1-06、P1-07、P1-08 是冷啟動輸入/輸出或公式不足，P2-09/P2-10/P2-11 是驗證命令或效能判準不足，P1-01/P1-02 是 SoT/scope 內部矛盾。故不能宣稱 V13 全 Task 過。

## 必答：冷啟動可執行性

不能完全通過。未讀 SPEC 的 agent 仍會在 B1.6、B3.1、B3.3、B4.2、B5.1/B5.2/B5.3 遇到明确冲突或缺输入/验证入口；对应证据为 P1-02、P1-05、P1-06、P1-07、P1-08、P2-09、P2-10、P2-11。

## 必答：§0/§A/§C/§G/§P/§V/§R/§N 与前提挑战

- `§RISK-HIT=a,b,d`、§G 四類 baseline、§P B1→B5、§V mutation/estimand/邊界、防假綠、§R 回退均有落點；未見新增行为绕过三项不可违反原则。
- brief 的三條 assumed 均完成核對：B2 順序與 payload gate 有依據；GAP-2 canonical scrub 實檔相符；新增具名檔案/簽名未改 frozen 語意。它們不是本輪 finding。
- §A 的 15 個 FACT-RECEIPT 逐項用其文件內命令抽驗：label close-to-close、/search default、allowed parameter、future-return、legacy silent continue、CaseRecord、匯入欄、multi-TF、event_filter、SplitPlan、survivor v1、UNWIRED sample_weight、既有 operator、IC event inputs、feature_cutoff 缺口均與 stdout 相符；未把 assumption 當 fact。
- §N 八條殘留逐條檢查：registry `G3-R1..G3-R8` 均存在，理由前綴為 `user-ruling`／`blocked-by`／`needs-research`，且各有觸發條件；無新增殘留 finding。

ASSUMPTIONS_VERIFIED: §V diff rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` rc=0；20 Task heading count=20；§A FACT-RECEIPT 抽驗 stdout 與宣稱相符；B2 順序、GAP-2 canonical scrub、TODO 新增具名細化均已核對。
TESTS_RUN: `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \\*\\*mutation 條件\\*\\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → empty stdout, rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；`rg -n '^### Task '` → 20；§A receipt commands → expected snippets present.
FAILURES_SEEN: none。
SCOPE_CHANGES: only `handoffs/20260820-gap3-x-review-r7-codex.md` added; no source/SPEC/TODO/data_cache changes。
NUMERIC_OR_SCHEMA_IMPACT: no implementation/output/schema changes; review records risks in existing TODO contract/gate text only。
HANDOFF_OUTPUT: `handoffs/20260820-gap3-x-review-r7-codex.md`
STATUS: DONE
