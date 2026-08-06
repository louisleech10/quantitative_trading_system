
# B3R SPEC 草案 R1 審查（三家）

brief-kind: review

**受審**：`docs/GOVB0_B3R_LEXER_SPEC.md`（DRAFT R1，主委起草）
**上游裁定**：`handoffs/reconcile/20260805-gatelex-redesign2/synth.md`（三家 APPROVED，`sha256:862f7bee…`）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。

## 🔴 `##` 標題白名單（**本 epic 曾整輪因此作廢**）

**唯一允許的 `##` 標題**：

```
## Verdict
## §0 前提宣告
## 逐項核對表
## 出場判準核算
## <canonical finding ID>      例：GROK-R20-P1-01
```

finding heading 逐字格式 `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`，本輪用 `R20`。
本 brief 的小節代號（`攻1`～`攻5`）是給你**引用**用的，**不是叫你當 `##` 標題**。
分項請用 `###`、表格或條列。零 findings 請明寫 `FINDINGS_COUNT: 0`。

🔴 **`OUT-OF-SCOPE` 不是標題**：要標出不受理項目，請寫在 `## 逐項核對表` 之內
（表格列或條列，例如 `- OUT-OF-SCOPE: latency 門檻（本輪不受理）`）。
**不得另立 `## OUT-OF-SCOPE` 標題**——上一輪 composer 即因此整份判不合規。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: SPEC 三支檢查器皆 rc=0——`doc_format_precheck.sh`／
  `template_check.sh spec`／`verification_claim_check.py --files`。
- fact-verified: 換行語意實測（`.claude/tmp/probe_nl.sh`）——
  引號內多行 commit 訊息 rc=0、heredoc body 內派工字樣 rc=0（皆正確放行）；
  `echo start⏎codex exec hi` rc=2（正確擋下）；
  **唯獨** `bash scripts/gate.sh⏎codex exec hi` rc=0（**應為 2**）。
  ⇒ 換行的一般處理正確，**只有自我豁免路徑壞掉**。
- fact-verified: `grep -Eq '\n'` 餵真換行 → rc=1（**抓不到**），
  證實 `_gate_lex.sh:354` 的分隔符偵測失效。
- fact-verified: 引號內字元數對耗時——10K→0.09s／100K→1.32s／500K→29.92s（二次方）。

**假設**（請優先攻）：

- assumed: §B.3 的 11 契約對照表**這次真的補齊了**。
  上一輪三家判主委原提案導不出契約 3／5／7／10，**本表為補寫後版本，未經任何獨立驗證**。
- assumed: §B.3 末的自我豁免述詞**沒有新的繞法**。主委只想到分號與換行兩種。
- assumed: `PATHWORD` 與 `CMD` 的產生順序、`ARGSPAN` 與 `HEREDOC` 重疊時的優先序
  可在實作階段釐清而不影響契約設計。**主委未驗證此假設。**

---

## 🔴 攻擊標的

### 攻1 — 11 契約對照表（**最高優先**）

§B.3 逐條列出「每條契約由哪些事件導出」。**上一輪就是這張表不足而被判 BLOCKING。**

**請逐條核對，並對每一條標 `可／不可`**：

| 要查什麼 | 通過條件 |
|---|---|
| 11 列是否**全部**指名 ≥1 個 §B.2 事件 | 無空列 |
| 指名的事件**欄位是否真的足夠**導出該契約 | 逐條給理由，不接受「看起來可以」 |
| 契約 **3／5／7／10**（上一輪的破口）是否真的補齊 | 各自構造一個反例試圖打穿 |
| §B.2 是否有**多餘**事件（列了但沒有任何契約用到） | 多餘＝過度設計，請具名 |

🔴 **若你判某條「不可導出」，請直接寫出缺什麼欄位**，不要只說不足。

### 攻2 — 自我豁免述詞

新述詞（§B.3 末）：

```
豁免 ⟺ CMDCOUNT.n == 1 ∧ 該唯一 CMD 的 depth == 0
      ∧ ( word1_decoded 為 gate 腳本路徑
          ∨ (word1_decoded ∈ {bash,sh,zsh} ∧ 其第二個 word 正規化後為 gate 腳本路徑) )
      ∧ 無任何 LEXERR
```

**請構造繞法**。已知被繞過兩次（分號、換行）。候選方向（不限於此）：
`env VAR=1 bash scripts/gate.sh`／`command bash scripts/gate.sh`／
符號連結或相對路徑變形／`bash -c "scripts/gate.sh"`／背景執行 `&`／
`gate.sh` 後面接參數注入。**繞得掉即 BLOCKING。**

### 攻3 — 主委承認沒查的四條（SPEC §D）

1. awk 能否真正 O(1) 記憶體串流（bash 3.2 + macOS awk）
2. `PATHWORD` 與 `CMD` 的產生順序未定義
3. `ARGSPAN` 與 `HEREDOC` 重疊時的優先序未定義（`bash -c "cat <<EOF"`）
4. `phase2_expected_flips` 由抽取器產生——**它本身可信嗎**？若抽取器有漏，差分基準就有漏

**第 1 與第 4 請實測**，不要只讀碼推論。

### 攻4 — 排程裁定：**B3 是否應被 B3R 吸收**

現行文件寫「B3 停手 ＋ 新增 B3R」。

**主委主張改為「B3 被 B3R 吸收，不再單獨驗收」**，理由：
B3R 的驗收（§V.2 C-1～C-6）已完整涵蓋 B3 原本要驗的 11 契約、26 parity、11 mutation
⇒ 保留 B3 的獨立驗收等於對同一份程式碼驗兩遍。

**請裁定**：吸收 vs 保留兩批？若吸收，第 0 批的批次序列變成
`B0／B1／B2／B3R／B4～B7`，**這樣記帳會不會遺漏 B3 已達成的部分**？

### 攻5 — 工作區未 commit 修補的去向

現有未 commit 的 B3 修補：已關三條原始 fail-open，但帶換行繞道與大輸入二次方。
SPEC §R 判定「長期不 commit 會使回退基準模糊」，列為開工前須先解的障礙。

**請給明確建議**：(a) 併入 B3R 一起落地 (b) 先獨立 commit 再開工
(c) 部分回退 (d) 你提的其他。**請說明對差分基準的影響。**

---

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`）

1. **重開 latency 裁決**——三家已一致「維持現狀」，本輪不重議。
2. C6（多 heredoc 第二 body 誤擋）——已裁順延 B4。
3. B4 以後的 Task 內容設計。
4. `audit.log` 封存／瘦身。
5. 措辭／命名／可讀性。
6. 重開「是否該重寫」這個決策——上一輪已三家戳記定案，本輪只審**規格本身**。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ SPEC 可定版，進 Phase 2 原型。**

## 硬性要求

1. **禁改碼、禁改測試、禁改 SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報，不要自行還原。
4. 不要 commit、不要 push；**禁碰 `data_cache/`**。
5. ⚠️ 工作區有未 commit 的 B3 修補且含已知卡死路徑；**測大輸入請自行加 `timeout`**。
6. 跑全套請**丟背景並導檔再取尾**；跑完須 `bash scripts/restore_golden_inventory.sh`。

## 產出

攻1 的**逐條 11 列判定表**（含 `可/不可` 與缺什麼欄位）、攻2 的繞法構造嘗試、
攻3 四項（第 1、4 須實測）、攻4／攻5 的明確建議、`## 出場判準核算`。
收尾清 /tmp workdir（保留 claude-501）。
