# 規則提案:編排端自產關鍵產物「先審後跑」(待委員會詰問)

**提案人**:Claude(編排端)　**日期**:2026-07-10　**狀態**:草稿,待三家詰問+使用者否決權
**出生事故**(白話):1e+1b Golden baseline 由 Claude 單獨設計+單獨執行,事後委員會三家全 BLOCK——抓出 xsec 截斷靜默無效、passed 集合假快照等實害;若無使用者質疑「為何沒審就跑」,這些洞會直接進驗收尺。

## 逃脫點分析(為何現行制度沒攔住)
1. **機器閘只攔兩類**:派工(dispatch)與 `docs/*SPEC/TODO/PLAN*` 創建;編排端「寫 scripts/ 腳本+自己跑 Bash」全程無 hook。
2. **SPEC 指派單人**:§G 凍結文字指派「編排端產 baseline」,審查焦點在防實作者自產,沒人問編排端自產要不要審(委員會盲點,R1-R3 未抓)。
3. **任務大小誤判**:編排端把「跑快照腳本」按工作量歸小任務;按 a-d 判準它命中 (a)數值/資料品質+(d)回測正確性,應按大任務步驟處理。
4. **順序無成文義務**:制度只有「派工前 SPEC/adversarial」「接回必 review」,無「編排端自產物先審後跑」條款→「先跑再補審」未被禁止。

## 提案條文
1. **先審後跑**:編排端自產的 Golden/baseline/oracle/驗證性產物=實作級產物;動工(執行產生程序)前,其設計檔(含落地參數與明知排除清單)必過 ≥2 家委員審;BLOCKING findings 依 Finding 閉合鐵律由原提出方複驗。
2. **SPEC 範本義務**:SPEC_TEMPLATE §G 增列欄位「baseline 產生程序審查:誰審/戳記/日期」——凍結時未填=gate artifact 檢查不過(機械化,防再犯)。
3. **裁量=決策**:凍結文字未覆蓋、需編排端裁量之參數(規模/選樣/排除),一律視為技術決策,適用「技術決策委派委員會」既有條款;禁以「照 SPEC 執行」名義吸收。
4. **SCAR 登記**:本事故(含 xsec 靜默無效/passed 假快照兩實害+三輪複驗軌跡)入 `docs/SCAR_LEDGER.md`。

## 詰問請求(給三家委員)
- 條文是否有可鑽的新縫(如「什麼算驗證性產物」邊界)?
- §G 機械化檢查的實作點(gate_check.sh 現有 artifact 檢查掛鉤)是否可行?
- 有無更便宜的等效方案(成本 vs 再犯風險)?

## 委員回覆格式
`handoffs/RULE-PROPOSAL-REVIEW-{codex,composer,grok}.md`,逐條 AGREE/CHALLENGE+修文建議;結論行 `VERDICT: ADOPT / ADOPT-WITH-CHANGES / REJECT`。使用者保留最終否決。
