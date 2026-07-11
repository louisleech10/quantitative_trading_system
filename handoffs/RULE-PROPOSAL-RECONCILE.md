# 規則提案 reconcile — 編排端自產驗收尺「先審後跑」(R1:codex+composer 均 ADOPT-WITH-CHANGES)

**裁決者**:Claude(編排端);兩家修文高度收斂,採聯集;**待補**:Grok 委員腿(B5 後)+使用者否決。

## 最終條文(v2,合併兩家替代文字)

1. **先審後跑(驗收尺產物)**:凡內容會**直接或間接決定實作通過/失敗、比較基準、納入集合或正確性主張**的新建/變更產物(Golden/baseline/oracle/canonical 快照/manifest/雜湊/遮罩/標籤;名稱路徑不影響;委外撰寫不豁免)——首次產生**前**,其 approval envelope(設計+產生器雜湊+輸入身分+全部參數+選樣排除+輸出 schema/路徑+可證偽條件)須由 ≥2 個非作者模型家族核可,戳記綁 body hash。envelope 任一項改變即重審;完全依既核可 envelope 重跑免重審。BLOCKING 依 Finding 閉合鐵律原提出方複驗;不可用時記名轉交另一非作者委員。**邊界不明一律按 new-or-changed 從嚴**。試探執行只可產 disposable 輸出,禁被最終產物/決策引用。
2. **機械兜底(兩層)**:①SPEC_TEMPLATE §G 增機讀欄(RISK-HIT 含 a/d 必填):`VALIDATION-ARTIFACT: none|existing-approved|new-or-changed`+`VALIDATION-MANIFEST: <path|N/A:reason>`+`VALIDATION-REVIEW: <families;body-hash;stamp task-ids>`;`template_check.sh spec` 對 new-or-changed 強制 manifest+足額同 hash 戳記。②新 `gate.sh validation-run --spec --manifest`:執行前驗欄位+產生器/輸入/config 雜湊+provenance;**下游驗收拒收無 run receipt 的產物**(fail-closed 主力;Bash 關鍵字 regex 不可靠,故以 canonical runner+消費端拒收為準)。`gate.sh artifact` 僅留建檔留痕定位,不宣稱驗過內容。
3. **裁量切分(反事實測試)**:SPEC 凍結時同步凍 execution envelope+內容不變量。免委員會的「執行細節」須同時滿足:值可機械決定或落在已核可範圍/範圍內任一替代值不改變納入集合、順序、值雜湊、容差、seed、缺值處理、pass set 或 schema/可重現且不變量有檢查。**白話判準:換一個合理值,尺或量出來的結果會不會變——不會=執行細節記 manifest 即可;會=驗收語義決策,回委員會**。不確定從嚴。
4. **SCAR 獨立登記**:本事故(xsec 截斷靜默無效/passed 假快照/1a gitignored 原件滅失不可 restore/各輪 review 軌跡)作為歷史事實登記,不依提案通過與否;每個「已驗證」主張附實跑命令。

## 成本控制(codex 建議採納)
一次凍結 approval envelope,例行同 hash 重跑免重審;§G review 列為 adversary 必查項批次戳記——避免小參數逐一開會。

## 出處
- `handoffs/RULE-PROPOSAL-REVIEW-codex.md`(ADOPT-WITH-CHANGES;反事實測試判準+canonical runner 設計)
- `handoffs/RULE-PROPOSAL-REVIEW-composer.md`(ADOPT-WITH-CHANGES;引用即尺邊界+兩層掛點修正+DELTA-ACK 維持 PASS)
- 待:`handoffs/RULE-PROPOSAL-REVIEW-grok.md`(B5 後補)+使用者簡述否決

## 戳記
(委員 append RECONCILE-STAMP;Grok 腿回來+使用者不否決後生效,屆時另開實作票改 template/gate)

## R2(Grok 腿補齊,2026-07-11):三家全 ADOPT-WITH-CHANGES
Grok(handoffs/RULE-PROPOSAL-REVIEW-grok.md)確認 v2 收斂正確,補三處執行縫(觸發條件與 receipt 綁定/善意繞過路徑/執行端負擔評估),灰帶三例判定入卷。**v3 定稿原則**:條文 1/3/4 依 v2;條文 2 機械化實作時吸收 Grok 之 receipt 綁定強化。實作票於使用者否決權行使後另開(改 SPEC_TEMPLATE+template_check+gate.sh validation-run+消費端拒收)。
