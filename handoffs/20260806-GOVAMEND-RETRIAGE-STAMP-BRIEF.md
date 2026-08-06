
# 全票重裁收斂戳記

brief-kind: stamp

stamp-target: handoffs/reconcile/20260806-govamend-x-consult-r1/synth.md

## 委員範本

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。

## 🔴 標題規則（**依本輪 `GROK-R21-P0-01` 修正，勿沿用舊指示**）

上一輪 brief 寫「禁用任何 `###` 子標題」——**該指示基於主委過寬的診斷，已被實測推翻**：
`### G-1 extra` rc=1（id-like 才擋）、`### 另外要回答的` rc=0（中文子標題通過）。

⇒ **本輪不禁止 `###`**。但請避免讓子標題**長得像 canonical finding ID**
（大寫字母＋連字號＋數字的組合，例如 `### OUT-OF-SCOPE`、`### G-1`）。
中文或一般英文子標題可正常使用。
`##` 標題仍限：`Verdict`／`§0 前提宣告`／`逐項核對表`／`出場判準核算`／canonical finding ID。
零 findings 請明寫 `FINDINGS_COUNT: 0`。本輪 finding 前綴用 `R26`。

🔴 **每一條 P0／P1 finding 必須附 `**來源摘要**: <path>#<sha 前綴>` 行。**
範本已載明，但本日已有委員**連續兩輪**因漏此欄整份判不合規（各燒掉一輪三家）。
**交件前請自查**：`grep -c '來源摘要' <你的產出>` 應 ≥ 你的 P0/P1 條數。

## 任務

複核**群集／處置段**是否忠實反映本輪 9 條 findings，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

## 你要查的

### 查1 — 主委被推翻的四項，記載是否忠實

收斂檔列出主委四項被推翻的陳述（38 張全有失誤／31 張關鍵字計數／`###` 一律作廢／`B-32` 錯掛）。

**請確認**：這四項的記載**與你的報告一致嗎**？有無**過度或不足**陳述你的結論？
特別是 `GROK-R21-P0-01` 對「範圍」的修正，主委是否忠實轉述而非放大。

### 查2 — 🔴 掉項已補回，請驗證歸戶正確

**上一輪 `codex` 判定「掉項成立」**——四條 finding 未給群集編號，
「處置分散在別處」不算歸戶。**主委已採納並補回。**

**現行完整歸戶（9 條全數，0 掉項）**：

```
G-1 ← GROK-R21-P1-01 ＋ codex CLOSED_STANDALONE: 行（Verdict 段宣告，非 finding ID）
G-2 ← CODEX-R21-P0-01 ＋ GROK-R21-P0-01     （id-like heading）
G-3 ← CODEX-R21-P1-02 ＋ GROK-R21-P1-02     （群集 ID 未登記＋群集段機械完整性）
G-4 ← GROK-R21-P1-01                        （批次規劃仍成立）
G-5 ← CODEX-R21-P1-03                       （mutation_probe_static.py 無 owner）
G-6 ← GROK-R21-P0-02                        （B-38 應提前）
G-7 ← GROK-R21-P1-03                        （B-32 錯掛應為 B-19）
G-8 ← GROK-R21-P2-01                        （B5 短命工）
```

**主委已自行以 `scripts/reconcile_cluster_attribution_check.sh` 機械核對**：
9 條 finding 全數被群集引用，**未被引用者 = 0**。

🔴 **請獨立複核，不採信主委的自檢**：
1. 每個群集引用的 ID，**斷言內容是否真的對應該群集的描述**（機械檢查只驗「有沒有被引用」，**不驗語意**）。
2. `G-1` 與 `G-4` 都引用 `GROK-R21-P1-01`——**一條 finding 歸入兩個群集是否恰當**？
   若不恰當，該歸哪一個？

### 查3 — 🔴 交集已由 **9 張修正為 7 張**，請驗證修正正確

**上一輪 `grok` REJECTED 的理由**（逐字）：

> G-1「交集 9 張」含 B-20/B-21，但 grok 裁定為做/降級非關閉；誤標交集，不可當兩家一致關閉

**主委已逐張 `grep` 比對 grok 裁定欄並修正**：

| 票 | codex | grok | 現行處置 |
|---|---|---|---|
| `B-1` `B-2` `B-3` `B-8` `B-12` `B-23` `B-35` | 關閉 | **關閉** | ✅ 真交集 7 張 → 關閉 |
| `B-20` | 關閉 | **做** | 不關閉，依 grok |
| `B-21` | 關閉 | **降級** | 不關閉，依 grok |
| `B-7` `B-10` `B-18` `B-32` | — | 關閉／DONE | 單家主張 ⇒ 待二輪 |

**請驗證**：
1. 這 7 張**是否真的兩家皆判關閉**？請自行重跑比對，不採信主委的表。
2. 分歧兩張採「不關閉」對嗎？🔴 **在關票這件事上，「較嚴」是哪個方向？**
   （保留一張沒用的票 vs 關掉一張還有用的票，何者代價高？）

### 查5 — 🔴 R3 codex 的兩條意見已修，請驗證修正到位

| codex R3 意見 | 主委處置 |
|---|---|
| `G-4` 寫「僅 grok 明確作答」為誤——codex `ADDITIONAL_ANSWERS` #2 亦答了 Q2，且更詳細；另 `GROK-R21-P1-01` 是票務 triage，**不能作 G-4 的語意來源** | 已改為兩家並列；G-4 展開採 codex 版（含「**原 B3 不再獨立驗收，B3R 吸收其驗收項**」）；已註明 G-4 **無 canonical 來源**（屬答問段） |
| 推翻表第 1 項**範圍偏窄**（只舉 `B-1`～`B-3`，未反映「至少 13 張」） | 已補全，並列出 DONE／0 實證／高摩擦三類 |

**請驗證**：這兩處修正**是否真的關閉了你的意見**？特別是——
`G-1` 與 `G-4` 現在**是否仍同時引用 `GROK-R21-P1-01`**？若是，該如何拆？

### 查6 — 主委已自行修掉戳記檢查器的一個缺陷（請複核）

`scripts/reconcile_stamps_check.sh` 原本 **REJECTED 用 `grep -q` 全檔掃**（任一行命中即永久擋），
而同檔 APPROVED 用 `tail -1`（取最新）⇒ **同一支腳本前後不一致**，
導致本收斂檔的 grok 在 R2／R3 連續 APPROVED 後仍被判 REJECTED。

**使用者裁定選項 A**：每個家族**取最後一筆戳記**，最新的蓋掉舊的。主委已實作並自驗：

```
現行版本  grok 被判 REJECTED: 0 次   （期望 0）
突變版本  grok 被判 REJECTED: 1 次   （還原舊邏輯即誤判 → 可證偽）
```

**請複核**：
1. 修法**有沒有弱化保護**？（最後一筆為 REJECTED／無戳記／雜湊不符／provenance 不符，四項應仍擋）
2. 有沒有主委沒想到的繞法？例如**同一行同時含 APPROVED 與 REJECTED**、大小寫變體、
   家族名為另一家族的前綴（`codex` vs `codexx`）。

#### 🔴 R5 更新：`CODEX-R26-P0-01` 已補，本輪請只驗這一條

**你 R4 的唯一反對點**（其餘查1～查5 你已全數確認到位）：

> `last_stamp`/REJECTED regex 對同一行 `APPROVED ... REJECTED` 走 APPROVED 分支
> ⇒「保護未減弱」之宣稱不成立

**主委查證後承認**：該洞**舊版同樣存在**（舊碼亦把狀態詞錨定在家族名之後）⇒ **非本次回歸**；
但主委原句是**把「沒變差」講成「沒有洞」**，宣稱確實不成立。

**已補**（`scripts/reconcile_stamps_check.sh`）：戳記行同時含 `APPROVED` 與 `REJECTED`
⇒ 判為畸形，**fail-closed** 拒收。

**主委自驗 4/4**（判準＝訊息內容，因合成檔過不了 provenance 故 rc 恆 1）：

| 案例 | 期望 | 結果 |
|---|---|---|
| 舊 REJECTED + 新 APPROVED | 不判 REJECTED | ✓ |
| 最新一筆為 REJECTED | 判 REJECTED | ✓ |
| **同一行混用** | **判畸形** | ✓ |
| `codexx` 前綴 | 不誤匹配 `codex` | ✓ |

🔴 **本輪範圍限縮**：其餘各查你 R4 已確認，**請只複核上述補丁**；
若補丁無誤即蓋章，不需重跑查1～查5。

⚠️ **composer 與 grok 已蓋現行 body hash**（主委未動收斂內容，僅改腳本），
故本輪**只派 codex 一家**。

### 查4 — composer 未計入是否影響結論

composer 本輪格式不合規未計入，本輪以 codex＋grok 兩家收斂。

**請判定**：兩家是否足以支撐「38 張全部裁定」這個結論？
composer 的報告（`handoffs/20260806-govamend-retriage-composer.md`，內容仍在）
是否含有兩家都沒提到、且會改變裁定的內容？**請實際讀它再答。**

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-06 sha256:df82cd54109b3164d3da2f90b5a022b832dd4ba5036c384c18a37153aac9be6e task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**。
- **只 append 到 `## 戳記` 區段之後**，不得改動該檔任何其他位元組。
- **不同意就不要蓋**，但仍須交產出說明理由。

## 不受理範圍（寫在 `## 逐項核對表` 內）

1. 重開個別票的技術修法設計——本輪只裁「做／不做／順序」。
2. B3R 技術設計。
3. latency 門檻。
4. 既有票號改名——「釘死不動」。

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **禁改碼、禁改票、禁改 backlog**。
3. **rc 一律直接取，禁經 pipe**。
4. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報。
5. 不要 commit、不要 push；**禁碰 `data_cache/`**。
6. 貼出 `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260806-govamend-x-consult-r1/synth.md` 的完整 stdout 與 rc。

## 產出

改了哪一行（貼 diff）、檢查器 stdout 與 rc、**查1～查4 的逐項判定**。
收尾清 /tmp workdir（保留 claude-501）。
