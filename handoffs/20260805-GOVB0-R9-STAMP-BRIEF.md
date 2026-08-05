# 第 0 批 TODO R9 收斂戳記（**實作前最後一道**）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-todo-r9/synth.md

## 任務

複核該檔的**群集／處置段**是否忠實反映 R9 的 findings，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

**本輪過關 ⇒ 實作可開工**（`gate.sh dispatch --adversarial` 要求本檔已獲戳記，
主委首次派 Grok 實作即被此閘擋下，故補本輪）。
來源：codex 3 條 ＋ composer 2 條 ＝ 5 條，群集為 `J-1`～`J-4`。

## 你要確認的（逐條，不是形式蓋章）

### 1. 歸戶正確性

`J-1` ← `CODEX-R9-P1-02`＋`COMPOSER-R9-P1-01`（`.sha256` sidecar 無 producer）
`J-2` ← `CODEX-R9-P1-01`（B-24 bounded 擷取只給自然語言）
`J-3` ← `CODEX-R9-P2-03`（`D-4`／`D-6`／`F-1`／`F-3` 無 literal 落點）
`J-4` ← `COMPOSER-R9-P2-01`（Gate 正文仍寫 ⑨～⑫ 四條）

🔴 **請逐條核對 ID 對應**。本批 10 輪中主委已犯 **7 次** ID 歸錯或對調，
兩道機檢（`completeness_check --lock`、主委自檢）**對「錯位」皆無感**，只有你們的語意複核抓得到。

### 2. **五條殘留主委已全部就地修完，請驗證修法是否真的關閉**

兩家原本都判 `named-residual`、不阻擋凍結，但主委依「第一性原理・現在修」全部修了。
**請實跑驗證**（修法細節見群集表處置欄）：

| 群 | 你該驗什麼 |
|---|---|
| `J-1` | Task 2.0 的「輸出」與「修改檔案」是否**都**列了 `gate_decision_corpus.txt.sha256`，且明訂 producer 與 commit ownership |
| `J-2` | `TEST-3.3-B24-PARTIAL` 的 `awk` 擷取命令**實跑**是否真的得 1（主委宣稱已驗，請獨立複跑） |
| `J-3` | §T 是否真的補上那四個 ID（`D-4`／`D-6`／`F-1`／`F-3`）的落點 |
| `J-4` | `B6→B7` 與 Phase 3 Gate **兩處**是否都改成 ⑨～⑬ |

### 3. **請攻「收斂訊號」的判斷**

群集段宣稱「R9 首次未出現『修補引入 blocking 缺口』，前兩輪各有 2 條與 1 條」。
🔴 **請驗證這個計數是否屬實**，並判斷：主委的修補品質是否真的改善，
還是只是本輪剛好沒被抓到？**這關係到實作階段該用多嚴的 code review。**

### 4. `E-SCOPE` 與既有殘留維持不變

`票 B-35`／`B-34`／`B-24` 機械強制面／`B-15` FP-2／`B-36` ID 錯位／`H-1`／`H-2`，**本輪不再徵詢**。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄為 byte-faithful 委員原文）。

🔴 **grok 的立場**：你是 implementer、被角色閘擋在 R9 review 之外（`票 B-34`），沒有自己的 findings。
⇒ 請以「**第三方複核**」立場審，並特別注意——**你即將是本 TODO 的實作者**，
所以請額外回答：**拿這份 TODO 你能不能直接開寫？有沒有哪個 Task 看完仍不知道要改哪個函式？**

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **驗收＝狀態，不是 rc**：貼出下列完整 stdout 與 rc——
   `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-todo-r9/synth.md`／
   `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-todo-r9/sources.lock`（須 0）／
   `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md`（須 0）。
3. **rc 一律直接取，禁經 pipe**。
4. 禁 `git checkout`／`git restore`／`git clean`；不要 commit、不要 push；**禁碰 `data_cache/`**。
5. 不蓋章一樣要交產出說明理由，**不要留空檔**。

## 產出

改了哪一行（貼 diff）、三支檢查器完整 stdout 與 rc、逐條歸戶確認、
第 2 點四項修法的**獨立實跑驗證**、第 3 點對收斂訊號的攻擊、
（grok 另答）拿這份 TODO 能否直接開寫。
收尾清 /tmp workdir（保留 claude-501）。
