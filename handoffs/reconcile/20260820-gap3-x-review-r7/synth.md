# Reconcile — 20260820-gap3-x-review-r7

**來源** 20260820-gap3-x-review-r7-codex.md, 20260820-gap3-x-review-r7-composer.md, 20260820-gap3-x-review-r7-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；逐條寫回 `docs/GAP3_EVENT_TODO.md` v0.2）

**Verdict**: 需修補後合併——12 個修訂群集全數寫回 TODO v0.2；R8 由原提出方（codex 11 條、grok 2 條）重跑同一反例閉合驗證，composer sentinel。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| W1 SoT 複列與優先序 | CODEX-R7-P1-01 | **部分採納**：B1.0/B2.4 列舉＝genesis 建檔規格（SPEC 同法「下為規格要求，非複列」），不刪；補「檔建立後以契約檔為準、本列不再維護」優先序宣告於 §0-5 與兩 Task；標題「不必回讀 SPEC」改誠實層級（操作依據＝本檔／語意權威＝SPEC／字面 SoT＝契約檔）；機械綁定＝B1.0 驗證①鍵集 `==` 契約列舉（既有） |
| W2 白名單互斥 | CODEX-R7-P1-02 | **採納**：§0-6 補 ⑦ `momentum/factories.py` 只在 B5.1（SPEC §RISK 末行明文授權一個出口）⑧ 收尾文件（`HANDOFF.md`/`docs/ROADMAP.md`/`docs/IC_QUANT_GAP_REGISTRY.md`/`白話說明/`）只在 B5.3 |
| W3 conditional-IC 置亂 oracle | CODEX-R7-P1-03 | **採納**：B2.3 驗證補 conditional_ic permutation oracle（共用 B1.4 oracle 核心；null 中心 0、固定 seed、經驗分位帶）；B2 Gate 補對應 `-k` 命令 |
| W4 digest tamper oracle | CODEX-R7-P1-04 | **採納**：B1.0 驗證補⑥ `source_file_digest`/`data_snapshot_digest` 篡改 negative fixture ⇒ 拒；§G-4 對應落點明列 |
| W5 B1.6 failures 通道 | CODEX-R7-P1-05 | **採納**：簽名改三元 `(features_at_decision, feature_manifest_hash, failures)`；reason 枚舉同契約檔；`test_feature_materialization.py` 補記帳守恆斷言 |
| W6 B3.1 role context | CODEX-R7-P1-06 | **採納**：`parse_condition(expression, column_registry, expression_role)`；`ConditionSpec.expression_role`；補 selection_predicate 放行未來欄＋feature 拒兩個可執行案例 |
| W7 B3.3 算子語意 | CODEX-R7-P1-07 | **採納**：TODO 階段定五算子精確語意（公式/閉區間/方向/NaN 規則/exact expected case）＝V13 授權細化（SPEC 只命名算子，未定公式；非改 frozen 行為） |
| W8 B4.2 exit 輸入 | CODEX-R7-P1-08 | **採納**：`to_return_series` 增 `label_definition`＋`receipts` 輸入；exit＝答案窗末 close（D1-4）；測 D1-6 各 entry × 退出窗一致 |
| W9 可執行命令補全 | CODEX-R7-P2-09, CODEX-R7-P2-10 | **採納**：B1.2 ASSERT 恢復 SPEC 全文命令；B5.2 vitest 檔名規約 `gap3_*.test.{ts,tsx}`＋命令 `cd frontend && npx vitest run gap3`；B5.3 UAT checklist 落 `docs/GAP3_UAT_CHECKLIST.md`（B5.3 產出） |
| W10 萬級牆鐘驗收形 | CODEX-R7-P2-11 | **部分採納**（不捏門檻——SPEC §V 列偵察待辦 T-3）：B5.1 前置＝T-3 偵察定 workload；驗收改記錄型可證偽＝receipt `handoffs/run_receipts/gap3_import_scale.json` 存在且含 `{n_events≥10000, wall_clock_s, peak_rss_mb}`；效能門檻若需，偵察後走 SPEC amendment |
| W11 `decision_at ≤ t0_open_ms` | GROK-R7-P1-01 | **採納**：B1.1 偽碼三段鏈旁顯式加該 validator 檢＋failures reason＋`test_alignment.py` 負例 |
| W12 direction 批內單值 | GROK-R7-P1-02 | **採納**：B1.0 改法＋驗證補「單批 `direction` 唯一值，否則拒」（規則住契約檔 validator/_doc，不複列鍵表） |
| — sentinel | COMPOSER-R7-P3-00 | 無修訂項；記錄其 20/20 無漂移＋M 表 RECHECK 佐證 |
| W14 B3.3 測試路徑（composer SPEC-AMENDMENT 註記，非 canonical finding） | — | **裁決＝免 amendment**：B3.3 明示新建 `tests/momentum/feature_engineering/` 目錄承載新測試 ⇒ SPEC/TODO 命令 `pytest tests/momentum/feature_engineering/ -q -k state_counters` 字面可跑（實測：該目錄現不存在、FF 既有測試在 `tests/feature_engineering/`，新建不動既有） |

寫回檔＝`docs/GAP3_EVENT_TODO.md`（v0.1→v0.2）；全部修訂不觸 SPEC FROZEN 條文。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R7-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的實質 finding；20 Task 抄寫漂移比對、§V RECHECK、brief 三條 assumed 攻擊、§1/§2 掃描均未見 BLOCKING/MAJOR。

**碼證**: `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → 空輸出 rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；`rg -c '^### Task '` TODO=20 SPEC=20；`rg -c '^  - M'` TODO=12；`shasum -a 256 docs/GAP3_EVENT_{SPEC,TODO}.md` → `544c2922ef2e`／`511c3f1b3b84`；路徑探針 `survivor_contract.py`/`pbo.py`/`min_btl.py`/`ichc_run.py:30`/`tests/golden/la0/inputs/` 皆存在；`gap2_freeze_golden.py` scrub ①②③⑤ 與 TODO §B B2 前言一致。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

## GROK-R7-P1-01

**斷言**: TODO Task B1.1 推導偽碼列了 D2-1 三段鏈與 D1-6，但未落地 SPEC D2-2／AR-1 要求的獨立不變式 `decision_at ≤ t0_open_ms`，冷啟動 agent 只讀 TODO 會漏做該 validator 檢。

**碼證**: SPEC `docs/GAP3_EVENT_SPEC.md` D2-2（約 L37）「validator 增 `decision_at ≤ t0_open_ms`」；AR-1（約 L82）同文。TODO B1.1（L84）偽碼不變式集合＝PIT／label／持有三段鏈＋`entry_after_label_start`＋as-of cutoff，全文 `grep t0_open|decision_at ≤ t0` 於 TODO → **0 命中**。§0-13 對 D2 的摘要亦只寫「三段鏈＋兩層收據＋失敗枚舉」，未點該檢。RECHECK：`grep -n 't0_open\|decision_at ≤ t0' docs/GAP3_EVENT_TODO.md` 須出現於 B1.1 改法／驗證。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MAJOR] 信心度=High。會怎麼失敗：執行端按偽碼實作對齊時不寫 `decision_at ≤ t0_open_ms` 守恆檢（推導式在 k≥0 時雖常自然成立，但缺防 regress／缺 bar 錯錨時的 loud 拒）；與「D2 全落地」／AR-1 不符。修法：在 B1.1 偽碼三段鏈旁顯式加入該檢＋對應 failures reason，並於 `test_alignment.py` 加負例。

---

## GROK-R7-P1-02

**斷言**: TODO Task B1.0 將 SPEC 必填列之 `direction ∈ {long, short}`（U1：匯入批內單值）縮成欄名 `direction`＋「值集與型別全在檔內定義」，未把「匯入批內單值」寫進改法／驗證／契約要求，屬漏抄。

**碼證**: SPEC Task B1.0 必填（約 L134）原文含「`direction ∈ {long, short}`（U1：一次只研究一向，匯入批內單值）」。TODO B1.0（L55）required_fields 列 `direction` 但無「批內單值」；驗證欄①–⑤亦無跨列 direction 唯一斷言。RECHECK：`grep -n '匯入批內單值\|批內單值' docs/GAP3_EVENT_TODO.md` 須非空，且落在 B1.0 改法或 `test_import_contract.py` 斷言描述。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MAJOR] 信心度=High。會怎麼失敗：契約 JSON／validator 只做枚舉閉集、允許同一匯入批 long+short 混入，下游 U1「一次只研究一向」與分層表假設被靜默打破。修法：B1.0 改法與驗證補「單批 `direction` 唯一值，否則拒」；字面規則可住契約檔 `_doc`／validator 規則，仍遵守不複列鍵表。

---

STATUS: DONE
