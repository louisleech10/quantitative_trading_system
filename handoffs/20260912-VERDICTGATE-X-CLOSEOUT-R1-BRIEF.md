# VERDICTGATE 收票審 R1（三家：C-4 範圍修正＋強制清單登記＋殘留清單＋結案裁決）

brief-kind: review
task-id: 20260912-VERDICTGATE-X-REVIEW-R11
findings-round: R11

🔴 **這是收票審（review），不是實作。禁改碼、禁動 tracked 檔；禁跑 `tests/governance` 全套；禁在本 repo commit／push。** 隔離路徑不得含家族名。
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄；findings 用 `## <FAMILY>-R11-P<0-3>-<NN>`；末段三行機械塊只准值集；**`STATUS: DONE` 逐字**。（R 計數延續本票 SPEC／TODO 審查：R1–R10 已用。）

## 審什麼（收票四件事，`docs/VERDICTGATE_TODO.md` §B「B4 → 收票」）
1. **C-4 範圍修正（SPEC 字面偏離，主委在真 audit 上發現並已改，須三家核）**：`scripts/verdictgate_check.sh` 於前批判定前新增——「b<N> 在 audit 已有任何 `committee_round_open`（task_id 以 `<root>-b<N>-` 起，大小寫不敏感）⇒ 印明跳過、rc=0」。理由：SPEC C-4 語意＝「開下一批前」；閉合輪／補裁決輪／修補後重領 token 都是**同一批**，不是進入新批；不加此規則時 SPLITUNIFY 補裁決輪（§E E-4，只要求 B5 前補一輪）會被 B3 無裁決擋、連鎖回溯到 B1（真 audit 實跑：b2–b5 全 🔴），違反使用者 2026-08-05「不溯及既往」。測試 `test_verdictgate_p2.py::test_check_batch_already_entered_skips_prev_verdicts`＋mutate-b2 M4b／M4c。**請正面打**：此規則是否開了「先開一個假審查輪、再領 token 越過前批 blocked」的縫？（主委立場：開審查輪本身經 gate.sh ⇒ 該次 dispatch 已對前批跑 verdictgate；假輪要能開，前批就已放行。）
1b. **`register-output` 語料補舊輪（同上，真 audit 發現並已改）**：SPLITUNIFY 補裁決輪 composer CLOSED 之 ID 存在於 B1 上線前之輪，語料只收 `committee_output.output_path` ⇒ 拒收 ⇒ 補裁決輪（§E E-4 之目的）永遠關不了舊 ID。改為語料另納同 root 各輪 `committee_round_open.expected_outputs[family]`（`test_verdictgate_p1.py::test_12_closed_id_in_legacy_round_expected_output_accepted`＋mutate-b1 M2e）。**請正面打**：expected_outputs 路徑可被開輪者任意指定——是否可藉此把他人檔案（或不存在之檔）納入語料而 CLOSE 不屬於自己的 ID？（主委立場：語料仍按 family 取 expected_outputs[family]，且 verdict_parse 只准 CLOSE 本家前綴 ID；不存在之檔讀不到 heading。）
2. **強制清單登記**（`docs/GOV_ENFORCEMENT_REGISTRY.md` E-022～E-025，票 B-62）：四掛載點與理由欄體例是否屬實（產出端 vs 豁免三段；行號指向可執行碼——`gen_fact_key_blocks --check` rc=0）。
3. **殘留 §E E-1～E-7**：逐條核「為何現在不做」仍成立。E-5 已做研究：`handoffs/20260911-verdictgate-e5-probe.sh`（結論：合法 amend／rebase 之 `ticket_commit` 序必在 token 後 ⇒ 序判對過期 token 恆放行；序＋ts 差 等價於以 audit ts 取代 mtime，無增量 ⇒ 第二層不做、mtime 保留）——請重跑並給立場。E-3／E-6 維持 needs-research（研究問題與完成判準已具名）。E-4 由本輪前一輪（SPLITUNIFY B7-REVIEW-R2 補裁決）處置。
4. **結案裁決**：B1–B4 皆三家審碼＋原提出方 CLOSED；四閘皆在自己票上實戰擋過（B1 契約閘拒收委員裁決行×3、B2 verdictgate 放行 B3／B4、B3 1c 放行 push、B4 synth hook 擋主委×1）。可否收票（`VERDICT: proceed`）？

## 🔴 必答
1. 第 1 點之縫：構造反例或給「無縫」碼證（`gate.sh` dispatch 路徑對 review 輪是否必經 verdictgate）。
2. 第 1 點與 SPEC C-4 字面之差：接受為收票內修正（記錄於本輪 synth＋HANDOFF）或要求走 FROZEN 修訂程序改 SPEC？給立場。
3. E-022～E-025 各列：產出端／豁免歸類正確？行號指向可執行碼？
4. E-5 probe 重跑結果＋立場。
5. 可否收票？

## 停輪條件
①必答 1–5 皆有立場；②必答 1、4 附實跑；③禁以「三家零 finding」當停輪。

## 前提
fact-verified: `pytest tests/governance/test_verdictgate_p1.py` 31、`p2`＋`p3` 77 passed；mutate-b1／b2 UNCOVERED=0；`gen_fact_key_blocks --check` rc=0；真 audit `verdictgate_check 20260911-SPLITUNIFY 8 …` 由 🔴 轉 ✓（補裁決輪三家 proceed 已清債）；`20260911-VERDICTGATE 4` ℹ 跳過（已進入）（主委 2026-09-12）。
fact-verified: `debt_ledger --has-open` rc=0（派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: 第 1 點規則無「假輪」縫 ⇒ 否證觀測：必答 1 之反例在暫存 audit 上讓 `--impl-self` 於前批 blocked 時仍發 token。／我跑了：**沒跑反例**（只跑正向 p2 test）。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
