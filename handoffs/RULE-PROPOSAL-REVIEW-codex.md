# 編排端自產驗收基準產物規則 — Codex 詰問

審查依據：已讀提案、`templates/SPEC_TEMPLATE.md`、`scripts/gate_check.sh`、`scripts/gate.sh`、`scripts/template_check.sh`、`scripts/reconcile_stamps_check.sh` 與 ORCH Gate 現行條款。本案只評制度與可機械化程度，未改任何治理程式。

## 條文 1 — CHALLENGE（原則同意，邊界與核可客體不足）
- 新縫：用別名（snapshot/fixture/report）、不落盤、委外寫產生器但由編排端選參數、先以「試跑」產出再沿用、或稱「既有重跑」但改 input/config/exclusion，皆可避開原文；只審設計檔也抓不到產生器實作偏離設計。
- 修文替代：**「驗收基準產物（validation-reference artifact）係任何新建或變更之程式、設定、manifest、快照、資料集、標籤、遮罩、雜湊或報告，只要其內容會直接或間接決定實作之通過/失敗、比較基準、納入集合或正確性主張；名稱、路徑、是否持久化均不影響。編排端只要參與設計、修改、選參數、指定輸入/排除或觸發產生，即屬編排端控制，不因委外撰寫而豁免。候選產物首次產生前，須由至少兩個非作者模型家族核可同一 approval envelope（設計、產生器檔案雜湊、輸入身分、全部參數、選樣/排除、輸出 schema/路徑、用途與可證偽條件），戳記綁定本體雜湊。任一項改變即重新審；僅完全依既核可 envelope 重跑者免重審。BLOCKING finding 須閉合並由原提出方複驗；不可用時須記名轉交另一非作者委員。邊界不明一律按 new-or-changed 處理。試探執行僅可產生明示 disposable、不得被最終產物或決策引用之輸出。」**

## 條文 2 — CHALLENGE（可實作，但不能只掛現行 artifact 檢查）
- 現況證據：`gate_check.sh` 的 artifact 只攔「新建 docs/*SPEC|TODO|PLAN*.md 的 Write」；Edit 既有 SPEC 不走此 gate。`gate.sh artifact` 在寫檔前只驗 `--file/--template-opened/--sections` 非空及 template 存在，未讀目標內容；真正的 SPEC 內容檢查在 dispatch 時由 `template_check.sh` 執行。任意自跑 Bash 又不屬 executor dispatch pattern，因此單增 §G 欄位仍擋不住事故路徑。
- 現有相容性缺口：adversarial ID/provenance 分支硬編 `CODEX|COMPOSER`，stamp checker 預設亦為 `codex,composer`；若「兩家」可含 Grok，須先泛化 family 設定與 provenance，否則規則與機檢語義不一致。
- 修文替代：**「SPEC §G 必含機讀欄：`VALIDATION-ARTIFACT: none|existing-approved|new-or-changed`、`VALIDATION-MANIFEST: <path|N/A:reason>`、`VALIDATION-REVIEW: <required families; body hash; stamp task-ids>`。`template_check.sh spec` 對 new-or-changed 強制 manifest 與足額、同 body-hash 戳記；existing-approved 強制既核可 manifest/hash；none 須具理由且不得與 §G 的新產生程序矛盾。另設 `gate.sh validation-run --spec --manifest`，於執行前驗上述欄位、產生器/input/config 雜湊及 provenance；所有驗收基準產生須經 canonical runner，所有下游驗收亦拒收無 run receipt 的產物。`gate.sh artifact` 僅負責建檔前模板留痕，不宣稱已驗最終內容。」**
- 可行性評估：中等改動、結構上可行；需 template fixture/mutation tests、新 validation-run token/runner、消費端 receipt gate。只靠 Bash 命令名稱 regex 不可能可靠判斷任意程式是否在產 oracle；若要求真正 fail-closed，須靠 canonical runner 加「下游拒收無 provenance」，或更強的寫入沙箱，而非擴充關鍵字列舉。

## 條文 3 — CHALLENGE（「一律」會癱瘓，須用驗收語義切分）
- 修文替代：**「SPEC 須先凍結 execution envelope（允許範圍）與內容不變量。只有同時滿足下列條件才屬執行細節、免委員會但須記入 run manifest：(i) 值可由凍結文件/設定機械決定，或明確落在已核可範圍；(ii) 任一範圍內替代值均不會改變納入集合、順序/對齊、值/雜湊、容差、精度、seed、缺值處理、排除、coverage、pass set 或輸出 schema；(iii) 可重現且內容不變量有檢查。batch size、concurrency、retry、log/output 暫存路徑僅在 determinism/resume 不變量已驗時屬此類。凡不滿足任一條、超出 envelope、加入例外，或兩個合理選項可能改變任何驗收結果者，均為驗收語義技術決策，須修訂 approval envelope 並送委員會；不確定時從嚴。」**
- 白話切分：不是看參數「大或小」，而是反事實測試（counterfactual test）——換另一個合理值，尺或被量的人會不會變；不會變才是日常執行，會變就是決策。

## 條文 4 — AGREE（事故登記不應依本提案是否通過）
- 修文替代：**「將本事故作為獨立歷史事實登記 SCAR，列出 xsec 截斷靜默無效、passed 集合假快照、各輪 review/reconcile/receipt 路徑及控制映射；每個『已驗證』主張附實跑命令與摘要。規則是否採用另列決策狀態，不得把提案通過倒寫成事故事實。」**

## 成本效益
- 較便宜且近等效：一次凍結 approval manifest，兩家只審「驗收語義＋產生器/輸入雜湊」，同 hash 的例行重跑免重審；把 §G review 明列為 adversary 必查項並批次戳記。這比每個小參數都開會便宜，又保留事故最需要的獨立審查與篡改可見性。
- 不等效方案：純 checklist、自我聲明、檔名 regex、只在產後 review；它們都保留本次「編排端可直接跑 Bash」的根逃脫點。新增 runner/receipt 有一次性工程成本，但可避免錯 oracle 污染所有後續驗收，對 a/d 高風險工作效益為正。

VERDICT: ADOPT-WITH-CHANGES
