# 文件內 ASSERT 行：路 A 處置與具名殘留

**狀態**：已落地（2026-08-12）
**決策者**：使用者（原話：「就走路 A」）
**受影響檔**：`scripts/gate.sh`、`scripts/template_check.sh`、`scripts/doc_format_precheck.sh`

## 1. 原本的問題

`scripts/template_check.sh` 的 `_run_assert_lines` 會**真的執行**治理文件內
`ASSERT <cmd> THEN rc=<n>` 形式的命令列，而 `_TC_ASSERT_CMD_ALLOW` 允許
`bash`／`python3`／`pytest`。

⇒ 一份 SPEC 內寫一行 `ASSERT bash scripts/gov_check.sh --no-probe THEN rc=0`，
就會讓「檢查這份 SPEC」這個動作反過來跑整套治理閘門（其中含全套 pytest）。

**實測後果**：單次寫檔路徑 605 秒；三份 `template_check` 並行時 fork 耗盡
（per-user process 上限 1333）。代號：**文件自鎖**。

## 2. 兩條路與取捨

| | 路 A（本次採用） | 路 B（未採用） |
|---|---|---|
| 作法 | 只驗錨點、不執行文件內 ASSERT | 改宣告式 `ASSERT-TEST: <path>::<test_name>`，靠 pytest 驗 |
| 現行實作 | **產出端反轉預設**：`template_check.sh` 預設不執行，要執行須明示 `TEMPLATE_CHECK_EXEC=1`（初版曾是「呼叫端帶 `NO_EXEC=1`」，已廢，見 §3） | — |
| 改動量 | 2 行 | 見下方實測——**遠小於先前宣稱** |
| 需否動凍結檔 | 否 | **否**（先前宣稱「45 行卡凍結檔」為誤，見下） |

### 🔴 執行面實測（2026-08-12；先前的 89 行說法係量錯）

`_run_assert_lines` 的抽取條件是 `^[[:blank:]]*ASSERT[[:space:]]`，**且**整行須以
`THEN rc=<數字>` 收尾（`rc!=0` 不符，會被判文法錯而**不執行**）。

| 量法 | 結果 |
|---|---|
| 「文件內出現 ASSERT…THEN rc」之行（**先前誤用之量法**） | 90 行／9 檔 |
| 生產正則實際命中（行首錨定） | **14 行／4 檔** |
| 其中文法過關、**真的會被執行** | **2 行** |
| 兩份凍結檔（`GOVB1_INPUT_QUALITY_{SPEC,TODO}.md`）之命中 | **0 行** |

⇒ 先前「須使用者授權修改凍結檔」之判斷**建立在錯誤量測上**，該授權問題不存在。
   出處事故：連續八輪審查該 SPEC 期間**從未量過執行面**，只審文件記帳。
   教訓歸 `docs/SCAR_LEDGER.md`（實測 > 假設，本次再犯）。

## 3. 封堵點：**沒有封堵點清單**（2026-08-12 二訂）

🔴 **強制點在產出端，不在呼叫端**：`scripts/template_check.sh` 的執行閘已反轉為
「須明示 `TEMPLATE_CHECK_EXEC=1` 才執行」，**任何呼叫端都不必、也不該做任何事**。

### 為何不再列清單（走過的三個階段，留著當教材）

| 階段 | 做法 | 為何不成立 |
|---|---|---|
| ① T0 止血 | 只有寫檔 hook 帶 `NO_EXEC=1` | 派工路徑仍會執行 |
| ② 路 A 初版 | 人工盤點呼叫端，逐處補旗標 | 人工盤點說 2 處，機械掃描抓到第 3 處 |
| ③ 路 A 初版＋掃描 | 掃 `scripts/*.sh` 要求每處帶旗標，當作封閉集合 | **codex〔R1-P2-04〕實證不封閉**：`scripts/test_template_check.sh:64` 以 `bash "${TEMPLATE_CHECK}"` 呼叫，正則看不見；`eval`／`$(...)`／間接層同理 |
| ④ 現行 | **反轉預設**，呼叫端無須配合 | 忘記帶的後果由「危險」變「安全」；沒有集合要維護，就沒有集合會漏 |

階段②③正是本 repo 已知的病：**列舉式黑名單永遠列不完**
（前例：`_g2_regions` 一個機制衍生 4 條旁路）。

判準由 `tests/governance/test_gov_check_cheap_first.py` 兩條釘住：
`test_document_assert_is_not_executed_by_default`（行為面，真的跑一次看有無副作用）與
`test_no_caller_needs_to_opt_out_of_execution`（形態面，執行閘須為 opt-in 且無死旗標殘留）。

`scripts/gov_check.sh` 只檢查 `template_check.sh` 是否存在（fail-closed），不執行它。

`scripts/gov_check.sh` 只檢查 `template_check.sh` 是否存在（fail-closed），不執行它。

## 4. 🔴 具名殘留（不得宣稱已根治）

1. **那 2 行可執行 ASSERT 自此不再被任何路徑驗證**，等同註解。
   誠實邊界：在此之前它們也**只在派工當下**才驗，不是本次新開的缺口。
   其餘 12 行本來就因文法不符而未執行（只被印成文法錯），處置不變。
2. `_run_assert_lines` 本體**仍保留執行能力**，但已改為 **opt-in**（`TEMPLATE_CHECK_EXEC=1`）。
   ⇒ 呼叫端無論怎麼寫都不會意外執行；**這條殘留已由設計消除，不再靠紀律**。
   剩餘缺口：有人**刻意**帶該變數去跑一份惡意文件。屬蓄意範疇，本 repo 威脅模型不涵蓋。
3. 逐行 timeout（T0 止血②）仍在，故即使重演也不會再無上限地掛住。
4. **真正的病灶是新文件，不是既有文件**：自鎖事故來自本 session 新寫的一份 SPEC，
   其中含行首 ASSERT 呼叫 `gov_check.sh`。路 A 封的正是這條路徑。

## 5. 路 B 之現況

先前判斷「須使用者授權改凍結檔」係基於**錯誤量測**（見 §2）。實測後：
凍結檔命中 0 行，可執行者僅 2 行，皆不在凍結檔內。
⇒ **不存在需要使用者裁定的授權問題**；路 B 若要做，是純技術取捨，
   不再是被授權卡住的事項。本檔即該事實的唯一記錄處，**不另開票**
（使用者已明確反對把差最後一哩的事寫成沒人會做的票）。
