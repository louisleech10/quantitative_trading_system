# VERDICTGATE B2（Task 2.1＋2.2）code review R1

brief-kind: review
task-id: 20260911-VERDICTGATE-B2-REVIEW-R1
findings-round: R1

🔴 **這是審碼（review），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套。**
🔴 交件檔末段**必須**含機械裁決塊（`cx_run` 自動 `register-output`；漏 `VERDICT:` ⇒ `verdict_rejected`）。**請在檔內寫 `STATUS: DONE`。** 本輪是 B1 閘上線後第一輪由「前批裁決」放行的開輪（`verdictgate_check 20260911-VERDICTGATE 2` rc=0）。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`（B2 審碼自 R1 起）。末段：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>
CLOSED:
```

## 審查對象（`docs/VERDICTGATE_TODO.md` FROZEN Task 2.1／2.2；SPEC v9 C-3／C-4／C-9）
- `scripts/prev_review_resolve.sh`（新；唯一前批解析：`^<root>-b<K>-` re.I、`brief_kind=review` 或缺欄且不命中排除 regex、回傳真 task_id 前綴去 `-r<M>`）
- `scripts/verdictgate_check.sh`（新；三參數必填；roster＝前批全部 review 輪 `quorum_eligible` 聯集；缺機械裁決／`verdict_rejected` ⇒ 擋並指名補裁決輪；`blocked_by` 聯集須同家後續 review／closure 之 `closed`；`proceed` 不解除；stamp／consult 之 CLOSED 不解除；abandon 之 round 豁免）
- `scripts/verdictgate_baseline.sh --report`（新；`has_verdict|unknown|stamp|no_output`、`unknown=`、`live_roots_unwatched=`、`legacy_open_by_root=`；不寫檔）
- `scripts/gate.sh`：quorum 塊之前批回溯改由 helper（呼叫點不變）；新增 verdictgate 呼叫（task_id 含 `-b<N>-`、brief 非 closure）
- `scripts/committee_run.sh`：gate 前同一 helper＋checker（失敗零新增 audit）；`scripts/debt_clear.sh`：`--abandon --kind collection-failed` 對有 `committee_family_result` 之 round 拒
- `tests/governance/test_verdictgate_p2.py`（24）；`handoffs/20260911-verdictgate-mutate-b2.py`（8，UNCOVERED=0）

## 🔴 必答
1. **SPEC ASSERT 對應**：Task 2.1 三條＋Task 2.2 十九條——逐條指出對應 test；缺者列出。
2. **真 audit 實跑（唯讀）**：`prev_review_resolve.sh 20260911-VERDICTGATE 2`、`… 20260911-SPLITUNIFY 5`、`… P16 6`（主委得 `P16-B5-BOOTSTRAP`——BOOTSTRAP 被預設視為 review，是否合理？只影響活票，但請給立場）；`verdictgate_check.sh 20260911-SPLITUNIFY 5 "$(…)"` 應 rc=1 指名三家補裁決；`verdictgate_baseline.sh --report` 之 `unknown=` 值與你獨立 `jq` 實算是否一致（主委得 256）。
3. **雙呼叫點**：`committee_run.sh` 與 `gate.sh` 各跑一次 helper＋checker——結果會不會不一致（同一 audit、同一實作）？有無競態（committee_run 跑完到 gate 跑之間 audit 被 append）？給立場。
4. **`review_quorum_check.sh` 之輸入**：helper 回傳含 `-REVIEW` 之真前綴，主委以 `sed` 截到 `-b<K>` 餵 quorum（`gate.sh` 該行）。對 `P16-B5-TASK31-REV` 型（無 `-REVIEW`）會截成什麼？quorum 會不會誤判？
5. **報表 `live_roots_unwatched`**：主委實跑列出大量已收之舊票（無「收票」事件可判活）——這是 SPEC 定義之「活票」判準不足，還是實作錯？給立場與可證偽修法（若屬 SPEC 缺口，列為 TODO §E 殘留）。
6. **假綠獵殺**：`test_check_helper_and_checker_agree_on_descoped` 第二個斷言（字面 B2 ⇒ 跳過 rc=0）是不是在「證明洞存在」而非「擋洞」？該測試是否應改為斷言 caller 永不傳字面 N-1（即測 gate.sh 之接線）？
7. **可否收 B2**？

## 停輪條件
①必答 1–7 皆有立場；②必答 2 附實跑；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在 B3 具體失敗」。

## 前提
fact-verified: `pytest tests/governance/test_verdictgate_p2.py` → 24 passed；mutation 8/8；回歸 6 檔 110 passed；`test_debt_clear.py` 見 commit 訊息（主委 2026-09-11）。
fact-verified: 真 audit：`verdictgate_check 20260911-VERDICTGATE 2` rc=0；`… SPLITUNIFY 5` rc=1（三家缺機械裁決）；report `unknown=256`。
assumed: `committee_run.sh` 先跑 checker 再交 gate 跑同一 checker，兩次結果恆同（同一 audit、同一實作、中間無 append）⇒ 否證觀測：必答 3 找到 append 視窗。／我跑了：**沒跑**競態實驗。

## ⚠️ 前置
禁改碼；只跑 `tests/governance/test_verdictgate_p2.py` 與你點名的單檔。收尾清 /tmp workdir（保留 claude-501）。
