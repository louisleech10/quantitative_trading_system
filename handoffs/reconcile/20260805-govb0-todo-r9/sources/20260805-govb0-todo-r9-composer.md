## Verdict：可派工（TODO 標 Internal Frozen）

本輪為 R9 **最後一輪**確認；R8 六條修補已關閉，未發現 `blocks-implementation` 級缺口。下述 2 條均降為 `named-residual`，不阻擋凍結。

FINDINGS_COUNT: 2

## §0 前提宣告

### fact-verified（本輪復跑）

| 宣稱 | 命令 | 結果 |
|---|---|---|
| template_check | `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` | `TEMPLATE PASS` rc=0 |
| Task 數對齊 | `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md`／`grep -c '^### Task ' docs/GOVB0_FRICTION_TODO.md` | 11／11 |
| `^RESIDUAL:` | `grep -c '^RESIDUAL: reclaim-orphan-manual-cleanup' docs/GOVB0_FRICTION_TODO.md` | 1 |
| `^TASK-STATUS:` | `grep -c '^TASK-STATUS: INCOMPLETE' docs/GOVB0_FRICTION_TODO.md` | 1 |
| `^LOCK-STATUS:` | `grep -c '^LOCK-STATUS: COMPLETE' docs/GOVB0_FRICTION_TODO.md` | 0（grep rc=1） |
| B-14 bounded | `awk '/^## B-14 /{p=1;next} /^## B-/{if(p) exit} p' handoffs/20260801-GOV-AMEND-BACKLOG.md \| grep -c '^TICKET-STATUS: PROVISIONAL'` | 1 |
| B-24 bounded | `awk '/^## B-24 /{p=1;next} /^## B-/{if(p) exit} p' handoffs/20260801-GOV-AMEND-BACKLOG.md \| grep -c '^TICKET-STATUS: PARTIAL'` | 1 |
| B-24 無 DONE | 同上 bounded 管道 + `grep -c '^TICKET-STATUS: DONE'` | 0（grep rc=1） |
| 程式碼區塊污染探針 | 全文 `grep -n '^TASK-STATUS:\|^TICKET-STATUS:\|^RESIDUAL:' docs/GOVB0_FRICTION_TODO.md` | 僅 L22／L614 為真標記；L655／L664／L669 為縮排敘述，不命中 `^` |
| R8 銷帳 | 讀 `handoffs/reconcile/20260805-govb0-todo-r8/synth.md` | 6/6 已正規銷帳 |

### 四條假設攻擊結果

| 假設 | 結論 |
|---|---|
| ① R8 六條修補彼此不衝突、未引入第三輪缺口 | **大部分成立**；I-4 延伸的 corpus sidecar 需求在 Task 2.0 產出欄漏列（見 `COMPOSER-R9-P1-01`），屬文檔落差非邏輯衝突 |
| ② 行首錨定機器標記無殘留漏洞 | **當前檔案成立**——`^` 錨定後計數與 bounded `awk` 擷取皆符合測試預期；風險在**未來**若於 ``` 區塊行首寫入同名標記會污染（目前無實例） |
| ③ §T 具名排除表完整 | **成立**——`F-7`／`B-36`、`E-SCOPE` 四項、`H-1`／`H-2`、`OPEN-2`／`D-8` 均有落點；11 個 SPEC Task 與 §T in-scope 表雙向對齊 |
| ④ 新增 Test ID 實作端可構造 | **未實作驗證**（brief 已標 assumed）；`TEST-3.2-LOCK-⑬`／`TEST-3.1-MANIFEST` 49／50 筆在 TODO 有探針描述，實作難度高但非邏輯不可構造 |

## 逐項核對表

### 1. R8 六條關閉狀態

| R8 ID | 查什麼 | 判定 | 證據 |
|---|---|---|---|
| I-1 | B-24 bounded 含 `^TICKET-STATUS: PARTIAL` == 1 | **CLOSED** | backlog `awk` bounded → count=1；`DONE` count=0 |
| I-2 | `^TASK-STATUS: INCOMPLETE` 行首錨定、無自我引用 | **CLOSED** | 全文 count=1（L614）；L655 為縮排敘述不計入 |
| I-3 | Task 2.5 修改檔案 vs B0 snapshot 產權 | **CLOSED** | Task 2.5「修改檔案」僅 `gate_decision_delta.sh`；snapshot／語料列為 B0／Task 2.0 **唯讀輸入**（L418-423） |
| I-4 | `TEST-2.5-CORPUS-SHA` 雙比對（實算 + sidecar） | **CLOSED** | L439-443 明訂①②缺一不可；mutation 須針對 sidecar 半（L446-448） |
| I-5 | §T 改名 + F-7／B-36 具名排除 | **CLOSED** | §T 標題已改（L686-690）；排除表 L696 含 `F-7`／`票 B-36` |
| I-6 | SPEC provenance 列全輪次 | **CLOSED** | SPEC L5-6 列 R1–R7 全數修訂項，不再停在 R4 |

### 2. 第三輪缺口掃描（最高價值）

| 查什麼 | 結果 |
|---|---|
| 機器標記在 ``` 內行首污染 `grep -c` | **無實例**（見 §0 探針） |
| bounded section `^## B-14 `／`^## B-24 ` 擷取穩定性 | **當前 backlog 穩定**——B-14 區段下一 `## B-` 為 B-15；B-24 下一為 B-27；各僅 1 行機器標記 |
| Task 2.5 唯讀化後 B0 產出定義 | **完整**——§B B0（L82）+ B0→B3 Gate（L93-95）+ Task 2.5 要點 2（L413-416）三處一致 |
| R8 修補交叉矛盾 | **未發現**；唯一落差為 Task 2.0 未列 corpus sidecar（見 finding） |

### 3. 追溯複查（SPEC 具名 ID → TODO 落點）

**§N／OPEN 具名殘留清單與 §T 對照**：

| SPEC 具名項 | TODO 落點 | 狀態 |
|---|---|---|
| `F-7`／`票 B-36` | §T 排除表 L696 | ✓ |
| `E-SCOPE` 四項 | §T 排除表 L697；§0.2；Task 3.2 要點 5 | ✓ |
| `H-1` 允許清單 | §T 排除 L698 + in-scope Task 2.0 要點 4 | ✓ |
| `H-2` reclaim 孤兒 | §0.1 L22 + §T 排除 L699 + Task 3.2 要點 8 | ✓ |
| `OPEN-2`／`D-8` locale | §0.2 L42-48 + §T 排除 L700 | ✓ |
| `OPEN-3`／`B-15` FP-2 | §0.2 L41 + §T H-1 列補查條件 | ✓ |
| `B-35`／`B-34`／`B-24` 機械面 | §T E-SCOPE 列 + §0.1 第 1 條 | ✓ |
| Task 0.1–3.3（11） | §T in-scope 表 L704-713 | ✓ |
| `E-10` PROVISIONAL | §0.1 第 3 條 + Task 3.3 | ✓ |
| `B-24` 紀律面 | §0.1 第 1 條 + §0.5 | ✓ |

差集：**空**（較 R8 前輪 F-7／B-36 漏列已修復）。

### 4. 執行端可動工性

| 維度 | 判定 |
|---|---|
| 冷啟動能否依 §B 批次開寫 | **能**——B0→B7 拓撲、每 Task 有修改檔案＋函式錨點 |
| 「不知改哪個函式」的 Task | **無 BLOCKING 級**；Task 2.0 缺 sidecar 產出說明可從 Task 2.5 反推（見 residual） |
| §1 必查 11 類（V13） | 矛盾/漏項/不可測/quant/OOM/cache/API/測試品質/Agent 可執行/短命工：**無新增 BLOCKING**（本批範圍內） |
| §2 範本錨點 | §0 三項狀態宣告可機械驗證；§T 追溯已補齊；空殼：**無** |
| §3 不可違反原則 | **無矛盾** |

## COMPOSER-R9-P1-01

**斷言**: Task 2.0 的「輸入／輸出」與「修改檔案」未列 `gate_decision_corpus.txt` 的 `.sha256` sidecar，但 Task 2.5 將其列為 Task 2.0 產出且 `TEST-2.5-CORPUS-SHA` 依賴已 commit sidecar。

**碼證**: Task 2.0 L258-259 輸出僅語料 + 測試；L284 修改檔案同。Task 2.5 L423 唯讀輸入含「語料 B … + 其 `.sha256` sidecar」；L439-443 `TEST-2.5-CORPUS-SHA` 雙比對。RECHECK: `rg -n 'gate_decision_corpus' docs/GOVB0_FRICTION_TODO.md` 比對 Task 2.0 輸出欄 vs Task 2.5 唯讀輸入欄。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MAJOR] 信心度=High；分類=**named-residual**。實作者僅讀 Task 2.0 時不知須產 sidecar；讀到 Task 2.5 可反推，不構成開工阻斷。修法：Task 2.0「輸出」補「`tests/governance/fixtures/gate_decision_corpus.txt.sha256`（語料 sha256 sidecar，與 B0 snapshot 同模式）」；「修改檔案」同步補列。

## COMPOSER-R9-P2-01

**斷言**: §B「B6→B7」Gate（L102）與「Phase 3 Gate」（L681-682）正文仍寫 `TEST-3.2-LOCK-⑨`～`⑫`「四條」，未提及已存在的 `TEST-3.2-LOCK-⑬`（reclaim 孤兒探針，L598-604）。

**碼證**: L102、L681-682 vs Task 3.2 驗證段 L598 `TEST-3.2-LOCK-⑬`。RECHECK: `rg -n 'LOCK-⑬\|LOCK-⑨' docs/GOVB0_FRICTION_TODO.md`。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MINOR] 信心度=High；分類=**named-residual**。全檔 `pytest tests/governance/test_atomic_publish.py` 仍會跑到 ⑬，Gate 文案漏列不致漏測。修法：§B B6→B7 與 Phase 3 Gate 改為「⑨～⑬」或明列 ⑬ 為 reclaim 孤兒釘扎測試。

## 出場判準核算

| 項目 | 值 |
|---|---|
| findings 總數 | 2（≤5 ✓） |
| blocks-implementation | 0 ✓ |
| named-residual | 2（`COMPOSER-R9-P1-01`、`COMPOSER-R9-P2-01`） |
| OUT-OF-SCOPE 未計入 | SPEC 設計重開、E-SCOPE、H-1/H-2、F-7/B-36、措辭、委員債務、B-16 擴充細節 |
| 建議處置 | **TODO 標 Internal Frozen → 進實作**；2 條 residual 建議併入 `票 B-16` 擴充或 code review checklist，不開 R10 |

## 被當成事實的未驗證假設（§0）

- brief §0「六條修補不衝突」：本輪實證**近乎成立**，corpus sidecar 產出欄漏列為 I-4 修補的輕微尾差（named-residual）。
- brief §0「Test ID 可構造」：仍為 **assumption**（未跑 pytest 探針）；不阻擋凍結。

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:22f05c3a427b61cacfea0b1a59aeda67ef528d72382d25dcfa628196904ee052 task:GOVB0-TODO-R9
