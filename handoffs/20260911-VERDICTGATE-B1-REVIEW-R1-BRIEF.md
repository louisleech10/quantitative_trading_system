# VERDICTGATE B1（Task 1.1＋1.2）code review R1

brief-kind: review
task-id: 20260911-VERDICTGATE-B1-REVIEW-R1
findings-round: R1

🔴 **這是審碼（review），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套。**
🔴 **本輪產出即為本票 Task 1.2 之第一批實戰輸入**：你的交件檔末段**必須**含機械裁決塊（見下），`cx_run` 會自動 `register-output`——寫錯會被拒收並留 `verdict_rejected`。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`（B1 審碼之 R 計數自 R1 起）。末段：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED:                    （本輪為首輪，留空）
```

## 審查對象（commit 範圍＝`git diff <上一 commit>..HEAD -- scripts templates tests`）
依 `docs/VERDICTGATE_TODO.md`（FROZEN）Task 1.1／1.2 與 `docs/VERDICTGATE_SPEC.md` v9 Task 1.1／1.2、C-1／C-5／C-8／C-9：
- `scripts/governance_verdicts.json`（新）；`scripts/audit_events.json`（registry v3：`committee_output` 移出 legacy、三新事件、`brief_kind`、origin allowlist、`verdict_rejected`）
- `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`／`COMMITTEE_FINDING_TEMPLATE.md`／`BRIEF_REVIEW_TEMPLATE.md`（機械塊）；`scripts/template_check.sh`（`template` 模式）；`scripts/verdict_filled_check.sh`（接受 `VERDICT:`）
- `scripts/verdict_parse.sh`（新，唯一 parser）；`scripts/gate.sh` register-output 分支（family 尾碼／roster／expected_outputs／同 root CLOSED corpus／`--kind stamp --family`／經 `audit_append`）
- `scripts/cx_run.sh`（`_maybe_register_review_output`、stamp 帶 `--kind`、`verdict_rejected`、harness `CX_STUB_TAIL`）；`scripts/committee_run.sh`（round_open 寫 `brief_kind`）
- `tests/governance/test_verdictgate_p1.py`（26 條）；`handoffs/20260911-verdictgate-mutate-b1.py`（9 條，UNCOVERED=0）

## 🔴 必答
1. **SPEC ASSERT 對應**：Task 1.1 三條驗證命令＋Task 1.2 十二條 ASSERT＋Task 2.2 之 stamp `verdict=null` 那條——逐條指出對應 test 函式；缺者列出。
2. **假綠獵殺**：每個 fail-closed 測試是否真的走到判定（例：`test_12_path_not_expected_output_rejected` 是否可能因更早的錯誤——如找不到 round_open——而 rc≠0 卻不是因為 expected path）？請對每條「拒收」測試確認錯誤訊息斷言鎖定的是**該條**判定。
3. **舊列相容**：`committee_output` 自 legacy 移入 debt_events 後，audit 既有 ~1,400 筆無 `sequence`／`family=unknown` 之 `committee_output` 列會不會被 `audit_append` 連續性掃描、`debt_ledger`、`reconcile_build`、`verify_task_provenance.py`、`verification_claim_check.py` 任一消費端判為違規或誤讀？實跑對真 audit 的唯讀命令（禁寫）。
4. **`_task_has_dispatch` 前置**：register-output 仍要求 `committee_dispatch` 存在；`committee_run` 派出的輪 gate.sh dispatch 會寫它——確認 `cx_run` 自動註冊路徑在真實流程下該事件必存在（碼證）。
5. **同 root corpus 規則**：root＝`^(.*?)-(b\d+|x)-`（大小寫不敏感）。對真 audit 抽 5 個 task_id 驗算 root 是否合理（例：`20260911-VERDICTGATE-X-REVIEW-R3`→`20260911-verdictgate`；`P16-B5-TASK31-REV`→？）。有無會把不同票併成同 root 的命名？
6. **stamp 分流**：`--kind stamp` 不驗 expected_outputs——stamp 之 `committee_output.output_path` 是 synth.md；Task 2.2 之 C-9 roster 判定要排除這類事件靠 `verdict=null`，`null` 以字串存（enum）——給立場：可接受，或應改 JSON null？
7. `CX_STUB_TAIL` 為 harness-only：確認未綁 harness 時無效（碼證），非新逃生口。
8. **可否收 B1**？

## 停輪條件
①必答 1–8 皆有立場；②必答 3、5 附實跑；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在 B2 具體失敗」。

## 前提
fact-verified: `pytest tests/governance/test_verdictgate_p1.py` → 26 passed（主委 2026-09-11）；mutation 9/9 COVERED；回歸 7 檔 125 passed；`gov_check --fast`、`gen_fact_key_blocks --check` 見 commit 前檢查。
fact-verified: `verdict_parse.sh` 對真實產出實跑：R13 grok proceed／R9 codex blocked 解析正確；R2 codex `CLOSED: none` 被拒（ID 格式）——**面向未來**，舊產出不回補。
assumed: `audit_append` 之連續性掃描只對有 `sequence` 之 debt 列取 max，無 seq 之舊 `committee_output` 列被跳過（主委讀 `audit_append.sh:215-230` 推論）⇒ 否證觀測：對真 audit 跑一次 `audit_append`（harness 隔離複本）若因舊列報 ERROR 即否證。／我跑了：**沒對真 audit 複本跑**。請必答 3 正面打。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；只跑 `tests/governance/test_verdictgate_p1.py` 與你點名的單檔。收尾清 /tmp workdir（保留 claude-501）。
