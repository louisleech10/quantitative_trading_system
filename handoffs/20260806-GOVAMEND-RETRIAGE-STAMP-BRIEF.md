
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
零 findings 請明寫 `FINDINGS_COUNT: 0`。本輪 finding 前綴用 `R22`。

## 任務

複核**群集／處置段**是否忠實反映本輪 9 條 findings，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

## 你要查的

### 查1 — 主委被推翻的四項，記載是否忠實

收斂檔列出主委四項被推翻的陳述（38 張全有失誤／31 張關鍵字計數／`###` 一律作廢／`B-32` 錯掛）。

**請確認**：這四項的記載**與你的報告一致嗎**？有無**過度或不足**陳述你的結論？
特別是 `GROK-R21-P0-01` 對「範圍」的修正，主委是否忠實轉述而非放大。

### 查2 — 🔴 ID 歸戶（主委本 session 已錯位 9 次）

```
G-1 ← codex CLOSED_STANDALONE ＋ grok 裁定欄（交集 9 張）
G-2 ← CODEX-R21-P0-01 ＋ GROK-R21-P0-01
G-3 ← CODEX-R21-P1-02 ＋ GROK-R21-P1-02
G-4 ← GROK-R21-P1-01（Q2 批次規劃）
```

**未歸入任何群集者**：`CODEX-R21-P1-03`（`mutation_probe_static.py` 無 owner）、
`GROK-R21-P0-02`（B-38 應提前）、`GROK-R21-P1-03`（B-32 錯掛）、`GROK-R21-P2-01`（B5 短命工）。

🔴 **請判定：這四條被漏掉是否構成掉項？** 主委認為它們已在「執行順序」與
「推翻主委四項」中處置，但**未給獨立群集編號**。若你認為這是掉項，請明說。

### 查3 — 「採交集 9 張、單家主張 4 張待確認」是否合理

grok 主張關閉 13 張、codex 主張 9 張。主委採**交集 9 張**，
grok 多出的 `B-7`／`B-10`／`B-18`／`B-32` 標「待二輪確認」。

**請判定**：這個保守作法對嗎？還是應該直接採較嚴（關閉 13 張）？
🔴 **注意本 epic 慣例是「兩家分歧採較嚴」**——但「較嚴」在關票這件事上是哪個方向？

### 查4 — composer 未計入是否影響結論

composer 本輪格式不合規未計入，本輪以 codex＋grok 兩家收斂。

**請判定**：兩家是否足以支撐「38 張全部裁定」這個結論？
composer 的報告（`handoffs/20260806-govamend-retriage-composer.md`，內容仍在）
是否含有兩家都沒提到、且會改變裁定的內容？**請實際讀它再答。**

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-06 sha256:f11009aaa6ca999418336345a93110d072acd280bf7c699efac260bf05b5bf97 task:<派工注入給你的 task-id>
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
