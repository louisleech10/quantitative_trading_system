# 規則提案詰問 — Grok 委員回覆（制度規則詰問腿）

**審查標的**：原提案 `handoffs/RULE-PROPOSAL-ORCH-SELF-ARTIFACT.md` + 合併條文 v2 `handoffs/RULE-PROPOSAL-RECONCILE.md`  
**角色**：第三家詰問委員；執行端視角（IC1EB B1–B5 派工消費方）  
**方法**：獨立讀提案/兩家 ADOPT-WITH-CHANGES/v2 聯集條文；對照出生事故逃脫點（編排端 Bash 無 hook、§G 單人指派、先跑後補審）；**未改** gate 程式與其他檔。  
**誠實邊界**：本檔為制度設計詰問，非 gate 實作 ticket；機械可行性依 v2 文字與既有 codex/composer 對 `gate.sh`/`template_check.sh` 靜態結論交叉核對。

---

## (1) 四條殘留可鑽縫總覽

| 條文 | 殘留縫（摘要） | 嚴重度 |
|------|----------------|--------|
| 1 | disposable 無機械標記；輸入「身分」未釘 content-hash；approval 綁 envelope 不綁輸出正確性且未強制產後複驗 | 中–高 |
| 2 | 僅 RISK-HIT a/d 才必填 → 任務誤判可跳過；`none` 矛盾檢查被 v2 刪弱；receipt 可偽造性未釘；runner 未落地前仍是紙規則 | 高 |
| 3 | 「合理值」「尺」的單位未定義；schema/sidecar 與 path vs content 灰帶；假凍結範圍可洗成執行細節 | 中 |
| 4 | 無制度縫；僅需把控制映射寫進 SCAR 列 | 低 |

v2 已正確收斂：功能定義取代檔名、委外不豁免、canonical runner + 消費端拒收為主力（優於 Bash regex）、反事實切分防委員會癱瘓。下列 CHALLENGE 針對**仍可被善意或惡意繞過**的殘留，不是重開已閉合爭議。

---

## 條文 1 — 先審後跑（驗收尺產物）

**立場**：**CHALLENGE**（方向與 Codex 邊界定義採納正確；三處執行縫仍在）

### 殘留可鑽縫

1. **disposable 無機械定義**  
   文稱「試探執行只可產 disposable 輸出，禁被最終產物/決策引用」，但未要求路徑前綴、manifest 旗標或 schema 欄 `disposable:true`。逃脫：試跑寫入 `handoffs/tmp_…` → 事後 `cp`/`mv` 進 canonical 路徑，宣稱「未重新產生、只是搬移」。  
   **對出生事故**：等同「先跑再補審」的變體。

2. **「輸入身分」未釘 content-hash**  
   envelope 含「輸入身分」——若實作為路徑字串，則同內容換路徑/symlink/cache 重建會被誤判為「envelope 變更須重審」或反過來「路徑同但內容已換仍免重審」。IC1EB 後期才補 inputs sha；規則應直接採 content-hash（+ 可選路徑註記），否則「完全依既核可 envelope 重跑免重審」可洗髒輸入。

3. **核可客體 = envelope，≠ 輸出正確性**  
   戳記綁 body hash（設計本體）合理，但 v2 **未**要求 new-or-changed 首次落地後仍須 ≥1 非作者對「可證偽條件」做產後複驗（或明列：產後複驗屬既有 Finding/B5，不在本條）。縫：審過的壞產生器（靜默 no-op）仍可產「有 receipt 的錯尺」。本條防「沒審就跑」，不防「審漏」——須在文末一句劃清，避免被解讀成 stamp = 正確性簽核。

4. **（較輕）「間接決定…正確性主張」過寬但從嚴可接受**  
   reverify 報告、委員會 PASS 文本身也是正確性主張；實務應排除「read-only 審查產物」以免遞迴。建議 defer 到條文 1 排除句，不必另開條。

### 修文建議（替代/補句，併入 v2 §1）

```markdown
1. **先審後跑（驗收尺產物）**：（保留 v2 主文）並補：
   - **輸入身分**預設為輸入位元 content-hash（可附路徑註記）；禁止僅以路徑字串充當身分。
   - **disposable**須同時滿足：(i) 路徑落在明示 disposable 根（如 `handoffs/_disposable/` 或 run 暫存且不入 SPEC §G 引用）；(ii) 產出 manifest/檔頭含 `disposable:true`；(iii) **升級為 canonical 視同 new-or-changed**，須新 envelope + 重審，禁止搬移/改名洗白。
   - **核可範圍**：stamp 只核可「可跑的 approval envelope」，**不**替代產後可證偽複驗；new-or-changed 首次 canonical 落地後，消費/複驗路徑仍適用既有 FAIL-CLOSED 與 VERIFY claim 義務。
   - **排除**：read-only 審查/複驗報告本身、對既有已核准尺的唯讀重算（不寫新 canonical）不觸發本條。
```

---

## 條文 2 — 機械兜底（兩層）

**立場**：**CHALLENGE**（架構對：§G 機讀 + validation-run + 消費端拒收；**觸發條件與 receipt 綁定**不足，且為再犯主力縫）

### 殘留可鑽縫

1. **「RISK-HIT 含 a/d 必填」可被任務大小誤判跳過**  
   出生事故逃脫點 #3 正是「跑快照腳本」被當小任務、未按 a/d 升級。v2 把機讀欄掛在 a/d 上 → 編排端若 § 標 RISK-HIT 不含 a/d、`VALIDATION-ARTIFACT: none`，template_check 不強制 manifest，**紙面合法重演**。  
   **應改**：下列**任一**成立即強制走 validation 機檢，而非僅 a/d：  
   - RISK-HIT 含 a 或 d；**或**  
   - §G/TODO 出現產生/引用 baseline|golden|oracle|canonical 驗收尺；**或**  
   - 將執行 `gate.sh validation-run` / capture 類 canonical runner。

2. **`none` / `existing-approved` 檢查被 v2 寫弱**  
   Codex 原文：`none` 須理由且不得與 §G 新產生程序矛盾；`existing-approved` 強制既核可 manifest/hash。v2 只詳寫 `new-or-changed`。縫：§G 大段描述 capture 卻標 `none`；或標 `existing-approved` 但 hash 已漂。

3. **run receipt 可偽造**  
   「下游拒收無 run receipt」若 receipt 只是手寫 markdown/`echo`，執行端或編排端可事後補造。須：**僅 canonical runner 簽發**；receipt 至少綁 `generator_sha256 + inputs_content_sha256 + config_sha256 + outputs_content_sha256 + envelope_body_hash + utc`；消費端驗的是綁定相等，不是檔案存在。

4. **落地前空窗**  
   規則生效敘事若不等於 runner+template_check+消費端三點同時上線，中間仍可靠編排端 Bash 直跑。提案層應標：**未實作前標 PARTIAL-MECH，不得宣稱 fail-closed 已恢復**（composer 亦提「部分機械化」誠實標）。

5. **（同意 v2）不靠 Bash 關鍵字 regex**  
   與 codex 一致；composer 的 capture 檔名 hook 可作**可選加速擋**，不得當主力。Grok **不**要求加回 regex 主力。

### 修文建議（替代/補句，併入 v2 §2）

```markdown
2. **機械兜底（兩層）**：
   ① SPEC_TEMPLATE §G 機讀欄（觸發=上列「任一」條件，非僅 a/d）：
      VALIDATION-ARTIFACT: none|existing-approved|new-or-changed
      VALIDATION-MANIFEST: <path|N/A:reason>
      VALIDATION-REVIEW: <families;envelope-body-hash;stamp task-ids>
      template_check.sh：
        - new-or-changed → manifest + 足額同 hash 戳記
        - existing-approved → 既核可 manifest 路徑存在且 envelope/outputs 綁定 hash 未漂
        - none → 非空理由，且與 §G/TODO 全文無「將新產/變更驗收尺」表述矛盾（機讀關鍵詞+人工抽樣）
   ② gate.sh validation-run --spec --manifest：
      執行前驗欄位+generator/inputs(content)/config 雜湊+provenance；
      **唯 runner 可寫** run receipt（綁定欄位見上）；
      下游驗收（B5/harness/gate --manifest 消費）拒收：無 receipt、receipt 綁定不符、或 outputs hash 與 receipt 不一致。
   gate.sh artifact 仍只做建檔留痕。
   實作未齊前：SCAR/ORCH 標 PARTIAL-MECH，禁止宣稱本逃脫點已關閉。
```

---

## 條文 3 — 裁量切分（反事實測試）

**立場**：**CHALLENGE**（判準方向正確、可執行；須釘「尺的觀測項」與三類灰帶預設）

### 殘留可鑽縫

1. **「合理值」無集合** — 沒有預先核可範圍時，「換另一個合理值」變成修辭；編排端可主張唯一合理值而跳過委員會。  
2. **「尺或量出來的結果」雙指涉** — 改 metadata-only 欄是否算「尺變了」？改 log 路徑是否算？v2 列了 schema 但未分 **compare-schema** vs **sidecar-schema**。  
3. **假凍結** — envelope 寫「batch_size ∈ 任意正整數」把語義參數洗成「範圍內執行細節」。反事實在「過寬範圍」內永遠「可能變」——應從嚴；但若檢查器不驗證範圍寬度，形同未凍。

### (2) 反事實測試：三個灰帶例與判定

| # | 案例 | 反事實（換合理值） | 尺/結果會變？ | **判定** |
|---|------|-------------------|---------------|----------|
| G1 | capture 的 `n_jobs`/`OMP_NUM_THREADS`：1 vs 8；envelope 未釘 determinism，value/hash 偶發隨歸約順序變 | 會（平台相依，非必現） | **驗收語義（從嚴）** — 除非 envelope 已凍 `n_jobs=1`（或等價 determinism 鎖）**且**有不變量檢查（重跑 hash 穩定）。不可當「純效能執行細節」。 |
| G2 | 輸入改為**同 content-hash** 的另一路徑（symlink / 重建 cache 後路徑變、位元不變） | 不應變（若身分=content-hash） | **執行細節** — 記 manifest 路徑註記即可。若身分仍用路徑字串 → 誤觸重審；故條文 1 須釘 content-hash（見上）。 |
| G3 | manifest 增 `generator_host` / `wall_time_sec` 等**不進入** B5 比較鍵的 sidecar；compare 用的 value hash / pass set / 納入集合不變 | 比較結果不變；檔案 schema 字面變 | **執行細節（條件）** — 僅當 approval envelope 的**內容不變量**明文排除 sidecar、且消費端比較鍵清單已凍。若「schema」籠統入不變量且無排除句 → 從嚴變**驗收語義**。**預設建議**：不變量=納入集合/順序/值雜湊/容差/seed/缺值/pass set/**compare-schema**；sidecar 預設排除。 |

**補充（非灰、用來校準尺）**：

- 改 `random_seed` 或排除清單 → 必變 → 委員會（非灰）。  
- 改 timeout 3600→7200 且**失敗不可入 canonical**（runner 成功才發 receipt）→ 執行細節。  
- 在已核可 run 矩陣內只選子集做**本地冒煙**、B5 仍跑全集 → 執行細節；若用子集結果主張「baseline 全過」→ 正確性主張越權 → 違條文 1/4 VERIFY 義務。

### 修文建議（替代/補句，併入 v2 §3）

```markdown
3. **裁量切分（反事實測試）**：
   SPEC 凍結時同步凍 execution envelope（**有上界的**允許範圍，禁止「任意正整數」類假凍結）+ 內容不變量。
   不變量預設觀測項：納入集合、順序/對齊、值雜湊、容差、seed、缺值處理、pass set、**compare-schema**（不含已聲明之 sidecar 元數據）。
   免委員會的執行細節須同時：(i) 值機械決定或落在已核可**有界**範圍；(ii) 範圍內任一替代值不改變上述不變量；(iii) 可重現且不變量有檢查。
   白話：換一個範圍內的值，**比較用的尺或量出的 pass/fail 集合**會不會變——不會=記 manifest；會或不確定=回委員會修 envelope。
   平台相依/非必現之數值漂移（執行緒數、BLAS）預設視為「會變」，除非已鎖 determinism 並有檢查。
```

---

## 條文 4 — SCAR 獨立登記

**立場**：**AGREE**

- 事故事實與提案採納解耦正確；與既有 VERIFY claim / SCAR 義務同向。  
- 建議 SCAR 列明示控制映射（非否決條件）：  
  `VALIDATION-ARTIFACT` 機讀、`validation-run` receipt 綁定、消費端拒收、disposable 不可洗白、輸入 content-hash。  
- 「每個已驗證主張附實跑命令」維持，避免 stamp 文字充當驗證。

### 修文建議（微補，可併 v2 §4）

```markdown
4. **SCAR 獨立登記**：（保留 v2）登記項至少含：xsec 截斷靜默無效、passed 假快照、1a gitignored 原件滅失、編排端 Bash 無 hook、§G 單人指派無審查義務；對策欄指向條文 1–3 控制點；規則 ADOPT 狀態另列，不得倒寫事故。
```

---

## (3) 執行端視角：派工流程實際負擔

**角色假設**：Grok 為 high-risk 實作端（如 IC1EB B1–B5），消費 §G 尺與 manifest，不自產 oracle。

| 環節 | 負擔變化 | 說明 |
|------|----------|------|
| 接派工前 | **略降意外** | SPEC 若 `new-or-changed` 未戳滿，dispatch/template_check 應擋下；少在中途才發現尺是編排端私跑 |
| 實作中 | **持平或微增** | 禁止「順便產小 golden」；本地 disposable 探針須標記且不可寫進回報當通過證據 |
| 驗收命令 | **微增** | 除 pytest 外多一步：確認 manifest/receipt 綁定存在（或 harness 內建 fail-closed） |
| 斷路器 ≤2 輪 | **持平** | 尺錯應 BLOCKED 回編排端/委員會，不可在執行端改尺「假綠」——與現行 C-OPT-3 一致 |
| 例行同 hash 重跑 | **近零** | v2 成本控制正確；執行端無感 |
| 首次 baseline 管線 | **編排端重、執行端輕** | 主要 token/延遲在 ≥2 家族審 envelope + runner 實作；執行端多等一拍，但少吃錯尺重工（IC1EB 四輪複驗級成本） |

**總評負擔**：對**執行端**可接受（大約每次高風險任務 +0–15 min 機械檢查，非常態開會）；對**編排端首次產尺**明顯變重——這是對症成本，且「一次凍 envelope、同 hash 免重審 + adversary 批次戳 §G」已把小參數開會壓住。  
**癱瘓風險來源**不在執行端，在條文 3 假凍結/過寬「合理值」；用上面有界範圍 + compare-schema 預設可壓。  
**拒絕的負擔轉嫁**：不要要求執行端在允許檔內「補審」編排端未核准的尺；BLOCKED 上交即可。

---

## 彙總

| 條文 | 立場 | 一句 |
|------|------|------|
| 1 先審後跑 | CHALLENGE | 功能定義對；補 content-hash 輸入、disposable 機械標記、劃清 stamp≠輸出正確 |
| 2 機械兜底 | CHALLENGE | runner+拒收主力對；觸發勿僅 a/d；強化 none/existing-approved；receipt 唯 runner 簽且綁 hash |
| 3 反事實 | CHALLENGE | 判準可用；釘有界範圍+compare-schema；G1/G2/G3 灰帶按上表 |
| 4 SCAR | AGREE | 獨立登記；附控制映射 |

**與兩家關係**：支持 v2 採 codex 功能定義 + runner/消費端主力、採 composer「引用即尺/部分機械化誠實」精神；**不**要求 Bash 檔名 regex 作 fail-closed 主力。主要增量是 v2 合併時**寫丟/寫弱**的觸發面與 receipt 綁定，以及反事實觀測項邊界。

ASSUMPTIONS_VERIFIED: v2 四條文字以 `handoffs/RULE-PROPOSAL-RECONCILE.md` 為準；兩家裁決為 ADOPT-WITH-CHANGES（`RULE-PROPOSAL-REVIEW-codex.md` / `RULE-PROPOSAL-REVIEW-composer.md`）；出生逃脫點與原提案一致；未重跑 gate 腳本（採納兩家靜態結論：artifact 不驗 SPEC 內容、Bash 不攔 capture）
TESTS_RUN: none（制度詰問；未改程式、未跑 pytest）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅本檔）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: 使用者限 scope 僅本檔；根 HANDOFF 由編排端維護

VERDICT: ADOPT-WITH-CHANGES
