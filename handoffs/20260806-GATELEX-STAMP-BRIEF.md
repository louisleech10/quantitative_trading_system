
# 詞法層設計重審收斂戳記（B3.5 派工前最後一道）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-gatelex-redesign2/synth.md

## 委員範本

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。

## 🔴 `##` 標題白名單（**上一輪三家全因此作廢，務必照做**）

**唯一允許的 `##` 標題**：

```
## Verdict
## §0 前提宣告
## 逐項核對表
## 出場判準核算
## <canonical finding ID>      例：GROK-R19-P1-01
```

本 brief 的小節代號（`查1`～`查4`）是給你引用用的，**不是叫你當 `##` 標題**。
分項請用 `###`、表格或條列。零 findings 請明寫 `FINDINGS_COUNT: 0`。

## 任務

複核**群集／處置段**是否忠實反映本輪 13 條 findings，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

## 你要查的

### 查1 — 🔴 ID 歸戶（**本輪第二次送審；上輪 codex 與 grok 皆因此 REJECTED**）

**現行（已依上輪意見修正）**：

```
F-1 ← COMPOSER-R17-P0-01 ＋ GROK-R17-P0-02        （E-1 根因）
F-2 ← CODEX-R17-P0-01 ＋ COMPOSER-R17-P1-01 ＋ COMPOSER-R17-P1-02
      ＋ COMPOSER-R17-P2-01 ＋ GROK-R17-P0-01      （提案②契約覆蓋不足）
F-3 ← CODEX-R17-P1-02 ＋ GROK-R17-P1-01            （E-2 超線性）
F-4 ← CODEX-R17-P1-03 ＋ COMPOSER-R17-P2-02
      ＋ GROK-R17-P1-02 ＋ GROK-R17-P2-01          （latency）
```

**上輪被抓到的兩處錯位（皆已修）**：

| 次 | 錯位 | 誰抓到 |
|---|---|---|
| 8 | `GROK-R17-P0-01`／`P0-02` 對調 | 主委自檢 |
| 9 | `GROK-R17-P1-01`（E-2 超線性）／`P1-02`（min-of-N）對調，且推翻表與 latency 段亦錯引 | **codex ＋ grok 戳記輪 REJECTED** |

🔴 **請不要因為「上輪已抓過」就略過**——請獨立重新核對全部 13 條。
`completeness_check` 只驗 ID 有沒有出現，**對「歸錯群」完全無感**。

### 查2 — 主委承認被推翻的兩項，記錄是否準確

| 主委原判 | 收斂檔記載的裁定 |
|---|---|
| 提案①：E-1 根因＝「轉換＋grep」架構 | 推翻；真因＝`_gate_cmd_is_self_gate` 字面 `\n` 致早退 |
| E-1／E-2 同根因 | 推翻；根因獨立 |
| latency 改 min-of-N | 撤回；屬統計手法達標 |

**請確認**：這三項的記載與你的報告一致嗎？有無**過度或不足**地陳述你的結論？

### 查3 — B3.5 差分基準（**已依上輪 codex 意見補寫，請複核是否到位**）

上輪 codex 判「不足：只寫『新舊』差分，未定義可信舊基準」。**已採納並補**：

> 以**凍結 snapshot ＋ `phase2_expected_flips`** 合成不可變的 old/expected 判定矩陣
> （snapshot 給本來的判定、flips 給本批應翻轉的條目），驗收＝**非預期差集為零**；
> 另對 E-1／E-2 新契約加獨立 TP/TN、mutation、timeout／資源上限 gate。

**請判斷**：這個補寫**真的關閉了你的意見嗎**？還有沒有缺口？
特別是：`phase2_expected_flips` 本身是由抽取器產生的——**它可信嗎**？

### 查4 — 保留 live 未 commit 修補（**已依上輪 codex 意見撤回安全宣稱**）

上輪 codex 判「不同意『保留 live 修補安全』；10K/0.09s 只覆蓋小輸入」。**已採納**：
收斂檔的殘留 3 已改為——

> **保留**是兩害相權（全回退會重開三條原始 fail-open），
> 但**「非即時風險」的說法撤回**：`10K→0.09s` 既不證明 E-1 fail-open 無害，
> 也不證明大輸入 O(n²) 可接受。**風險未經證明**；B3.5 完成前不得 commit，
> 且不得以此宣稱現況安全。

**請判斷**：這個表述是否忠實反映你的意見？**還是你認為應該現在就部分回退**？
若主張回退，請具體指出回退哪一段、以及如何避免重開三條原始 fail-open。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-06 sha256:862f7bee23daa514f6c01d8ce6990ca202afe737737df65f8ff12e1e418ad6e1 task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**。
- **只 append 到 `## 戳記` 區段之後**，不得改動該檔任何其他位元組。
- **不同意就不要蓋**，但仍須交產出說明理由。

## 不受理範圍（標 `OUT-OF-SCOPE`）

1. 重開 latency 裁決（三家已一致「維持現狀」，本輪不重議）。
2. B3.5 的**實作細節**——下一輪 SPEC 專門處理，本輪只判驗收設計有無缺口。
3. C6、B4 以後的 Task 內容。
4. `audit.log` 封存／瘦身。
5. 措辭／命名／可讀性。

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **禁改碼、禁改測試**。
3. **rc 一律直接取，禁經 pipe**。
4. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報，不要自行還原。
5. 不要 commit、不要 push；**禁碰 `data_cache/`**。
6. ⚠️ 測大輸入請自行加 `timeout`，工作區有已知卡死路徑。
7. 貼出 `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-gatelex-redesign2/synth.md` 的完整 stdout 與 rc。

## 產出

改了哪一行（貼 diff）、檢查器 stdout 與 rc、**查1～查4 的逐項判定**。
收尾清 /tmp workdir（保留 claude-501）。
