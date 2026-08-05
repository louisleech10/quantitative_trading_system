# 第 0 批 TODO 確認輪（R9）— **最後一輪**

brief-kind: review

target: `docs/GOVB0_FRICTION_TODO.md`（`template_check todo` rc=0）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。本 brief 只收斂範圍。

## 🔴 finding heading 格式（**引用檢查器正則本身，勿依散文描述**）

`scripts/completeness_check.sh:153` 的 canonical 正則**逐字**為：

```
^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$
```

**本輪合法範例**：`CODEX-R9-P1-01`／`COMPOSER-R9-P0-02`。
`P` 後只能 `0`–`3`；序號**至少兩位數**；**必須有 `R<數字>` 段**。

**本輪唯一允許的 `##` 標題**：`## Verdict`／`## §0 前提宣告`／`## 逐項核對表`／`## 出場判準核算`
＋ 上述 canonical finding heading。**其餘分段一律用 `###`。**
零 findings 請明寫一行 `FINDINGS_COUNT: 0`（`票 B-38`）。

## 🔴 本輪是 TODO 的**最後一輪**（終止條件，逐字）

依使用者定死的「**95% 解法就收・殘留先記錄**」與「兩輪斷路器」：

- TODO 已歷經 **R8 前輪（9 條）→ 修 → R8（6 條）→ 修 → 本輪**，共兩輪補丁。
- **本輪之後不再為 TODO 開 R10。**
- 你若發現新缺口，**除非**能證明「該缺口使**執行端無法照本 TODO 動工**」（＝實作者會做出錯的東西，
  或根本不知道要做什麼），否則一律**降為具名殘留**寫入 `票 B-16` 擴充，**不阻擋標 Internal Frozen**。
- 請在 `## 出場判準核算` 明確分類每條新 finding：**blocks-implementation** 或 **named-residual**。

⚠️ 這不是放水。**該找照找、該證偽照證偽**；差別只在找到之後怎麼處置。

## §0 前提宣告

**已查證**（可自行復跑）：

- fact-verified: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0。
- fact-verified: SPEC Task 數 **11** == TODO Task 數 **11**
  （`grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` ／ `grep -c '^### Task ' docs/GOVB0_FRICTION_TODO.md`）。
- fact-verified: 五個機器標記**行首錨定後**實測各為 —— `^RESIDUAL: reclaim-orphan-manual-cleanup` **1**、
  `^TASK-STATUS: INCOMPLETE` **1**、`^LOCK-STATUS: COMPLETE` **0**、
  `票 B-24` bounded section 內 `^TICKET-STATUS: PARTIAL` **1**、
  `票 B-14` bounded section 內 `^TICKET-STATUS: PROVISIONAL` **1**。
- fact-verified: R8 收斂檔已**正規銷帳**（非 abandon）→ `handoffs/reconcile/20260805-govb0-todo-r8/synth.md`。

**假設**（請優先攻）：

- assumed: **6 條修補彼此不衝突，且未引入第三輪新缺口**。
  🔴 **主委對此的信心已被實證推翻兩次**——前兩輪的「修補」各自引入了新缺口，
  且主委在修 I-1／I-2 的過程中**又踩同一陷阱兩次**。**這是本輪最該攻的前提。**
- assumed: **行首錨定的機器標記方案沒有殘留漏洞**。未驗證：
  ①標記若出現在程式碼區塊（``` 內）是否仍被 `grep -c` 計入；
  ②bounded section 擷取法在 backlog 標題格式改變時是否仍穩定。
- assumed: **§T 的具名排除表已完整**。上一輪 codex 抓到 `F-7`／`B-36` 漏列 ⇒ 可能仍有漏。
- assumed: **新增的 Test ID 在實作端可構造**（`TEST-3.2-LOCK-⑬` 的 ③→④ crash probe、
  `TEST-3.1-MANIFEST` 的 49／50 筆構造資料、`TEST-2.5-CORPUS-SHA` 的 sidecar 雙比對）。**未實作、未實跑。**

## 本輪範圍：只驗 R8 六條是否關閉 ＋ 是否引入第三輪缺口

| 群 | R8 原 finding | 主委修法 |
|---|---|---|
| I-1 | 狀態斷言引用目標區段內不存在的字串 ⇒ 測試恆為 FAIL（BLOCKING） | `票 B-24` 補 `TICKET-STATUS: PARTIAL` 機器標記行 |
| I-2 | 斷言自我引用（宣稱 `grep -c` == 1，實測 2） | 改用 `TASK-STATUS: INCOMPLETE` **行首錨定**標記；全面禁散文關鍵字比對 |
| I-3 | snapshot 所有權矛盾（B0 是 producer，Task 2.5 仍列在修改檔案） | Task 2.5「修改檔案」只列 `gate_decision_delta.sh`；snapshot 與 corpus 及 sidecar 改列**唯讀輸入** |
| I-4 | corpus immutability mutation 不可證偽（標頭與實算值一起變） | `TEST-2.5-CORPUS-SHA` 改為**同時**比對①當前實算值②**已 commit 的 `.sha256` sidecar**；mutation 明訂須針對 sidecar 那一半 |
| I-5 | §T 宣稱 100% 覆蓋為不實（`F-7`／`B-36` 無落點） | §T 改名為「in-scope 覆蓋 ＋ 明列排除清單」，新增具名排除表 |
| I-6 | provenance 漂移（SPEC:5 停在 R4，實際 R7） | SPEC:5 更正並列全部輪次 |

**你要確認**：

| # | 查什麼 | 通過條件 |
|---|---|---|
| 1 | 六條是否**真的關閉** | 逐條標 CLOSED／NOT-CLOSED，附你自己的實跑命令與結果 |
| 2 | **是否引入第三輪缺口** | 🔴 **本輪最高價值**。特別查：機器標記方案是否有新漏洞（程式碼區塊內的標記、bounded section 邊界）、Task 2.5 唯讀化後 B0 的產出定義是否完整 |
| 3 | **追溯複查** | 上一輪抓到 `F-7`／`B-36` 漏列 ⇒ 重跑一次全量 SPEC 具名 ID 對照，列出你 grep 到的清單與落點 |
| 4 | **執行端可動工性** | 冷啟動實作者拿本 TODO 是否能開寫？有無「看了還是不知道要改哪個函式」的 Task？ |

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`，不計入 findings）

1. 重開 SPEC 的設計裁決（已七輪收斂＋三家戳記）。**例外**：該決策使 TODO 無法被實作。
2. `E-SCOPE` 四項、R7 兩條殘留（`H-1`／`H-2`）、`F-7`／`B-36`（已列具名排除）。
3. **防蓄意繞過**類——本批目標是擋意外。
4. 措辭／可讀性／命名一致性。
5. 「委員債務無 OPEN」不必查（派工本身會開債）。
6. `票 B-16` 擴充 A／B 的設計細節（已由使用者裁定合併並排第 1 批，本批不實作）。

## 出場判準

> **findings ≤5 且 blocks-implementation = 0 ⇒ TODO 標 Internal Frozen，進實作。**

## 硬性要求

1. **禁改碼、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
4. 每條 finding 附**可執行修法**（具體到「哪個 Task 的哪一欄補什麼」）。

## 產出

上表四項逐項判定、findings（若有，須分類 blocks-implementation／named-residual）、
`## 出場判準核算`、對 §0 四條假設的攻擊結果。收尾清 /tmp workdir（保留 claude-501）。
