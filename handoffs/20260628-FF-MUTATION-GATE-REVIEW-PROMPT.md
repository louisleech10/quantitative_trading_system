# 任務:adversarial 審新 mutation 機制(不同模型,作者不自審)

被審(commit 0d377e6):
- `docs/TEST_DESIGN_CHARTER.md` §B1.1/B1.2/B1.3 + B1-驗收紀律
- `scripts/mutation_probe_check.sh`

背景:FF C1-2 假綠(oracle 從 `_INPUT_TYPE_MAP` 衍生→改 source 同時改 oracle→永遠相等;且 registry 快取使無效 mutation 假裝通過)。機制目標=把「測試有沒有真牙齒」從靠 reviewer 自由心證,變成機器強制。

你是 adversary,獵這機制本身的洞。逐項:

## A. 漏洞(假綠仍能過閘)
1. 我能不能寫一個**過閘但沒牙齒**的探針?例如:`def test_mutation_x(): assert True`(空探針)——閘只看「有 test_mutation_* 且跑過」,擋得住嗎?若擋不住,怎麼補(章程或腳本)?
2. oracle 獨立性(§B1.2)目前靠 adversarial「必問」,**非機器驗**。有沒有低成本機器啟發式可加(如偵測 test 是否 import 被測模組當 oracle)?或誠實標明這條只能靠人?
3. `-k mutation` 收集邏輯:若某檔探針命名不含 mutation(如 `test_atr_removed_fails`)會被漏跑嗎?N/A 豁免會不會被濫用成「整批 n/a」?

## B. 誤擋(擋正當測試)
4. 純邊界/smoke/契約測試檔(本就不該有 mutation)被閘要求探針——N/A 逃生口夠不夠?會不會逼人寫假探針?
5. 腳本 bash 3.2 相容?路徑含空格?`collected` 解析(`grep '[0-9]+ passed'`)在「mutation 探針 0 passed 但有 xfail/skip」時誤判嗎?

## C. 腳本邏輯
6. 讀 `scripts/mutation_probe_check.sh` 逐行:exit code、find、grep、pytest 調用有無 bug?`venv/bin/python` fallback 對嗎?

輸出 `handoffs/20260628-FF-MUTATION-GATE-REVIEW-<你>.md`:結論(機制可用/須補)+ 漏洞清單(每條:攻擊法+反例+修法)+ 誤擋清單 + 腳本 bug。只寫 review 檔。完成 STATUS: DONE。
