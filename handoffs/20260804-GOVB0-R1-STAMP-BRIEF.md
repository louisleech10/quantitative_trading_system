# 第 0 批 SPEC R1 收斂戳記

brief-kind: stamp

stamp-target: handoffs/reconcile/20260804-govb0-spec-r1/synth.md

## 任務

複核 `handoffs/reconcile/20260804-govb0-spec-r1/synth.md` 的**群集／處置段**是否忠實反映你 R1 的 findings，
確認無誤後 **append 一行 RECONCILE-STAMP** 到該檔的 `## 戳記` 區段。

### 你要確認的（逐條，不是形式蓋章）

1. **你自己 R1 的每一條 finding 都被歸入某個 D 群，且處置與你的主張一致。**
   你的 findings 在該檔附錄逐字保留（byte-faithful），群集表在檔案前段。
   若有任一條被歸錯群、處置被弱化、或主張被改寫 ⇒ **不要蓋章**，改為寫明哪一條、怎麼錯。
2. **D-6（`票 B-24` SPLIT）與 D-7（timeout 暫定值）是主委裁決，非你的原話。**
   若你不同意該裁決，**不要蓋章**，寫明理由。
3. **D-1 的主委獨立驗證表**（`.claude/tmp/b15probe3.sh` 原型①／②對照）你可自行重跑核對。

### 🔴 本輪為第二次戳記輪（第一次已作廢，原因如下）

第一輪 `GOVB0-R1-STAMP`：composer 已蓋章，**codex 依本 brief 規定拒章**並指出一個真實錯誤——
D-7（timeout）誤引 `CODEX-R1-P0-07`，但該 ID 是 locale fail-open，timeout 主張實為 `CODEX-R1-P1-06`。
**該歸戶錯誤已修正**（D-7 現引 `CODEX-R1-P1-06`（timeout 主張部分）；D-13 續引 `CODEX-R1-P1-06`，
與 codex 自述的「P1-06 → D-7 的 timeout 主張及 D-13 的依賴摘要」一致）。
body hash 因此由 `1088062c…` 變更為 `25e1241f…`，composer 前一枚戳記自動失效並已移除。
**本輪三家（含 grok）重新蓋章。**

🔴 **grok 為何在本輪**：`reconcile_stamps_check.sh` 要求 `review_families` 全員（codex／composer／grok），
但 grok 是現行 implementer，**被角色閘擋在 R1 review 之外**，故未參與該輪審查。
此不一致已開 `票 B-34 GOV-STAMP-ROSTER-VS-ROLEGATE`。
⇒ **grok 請以「第三方獨立複核」立場審**：不是確認「我的 findings 有沒有被歸戶」（你沒有 findings），
而是確認「**群集表對附錄逐字 findings 的歸戶是否正確、處置是否忠實**」。
若你發現任何歸戶錯誤（如 codex 上一輪抓到的那種），**不要蓋章**。

### 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-04 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:<派工注入給你的 task-id>
```

- `<你的家族名>` 換成 `codex` 或 `composer`（以派工注入的家族名為準）。
- `sha256` 值**逐字照抄上方**，那是 `bash scripts/reconcile_body_hash.sh <該檔>` 對「`## 戳記` 之前內容」算出的值。
- `task:` 欄位**逐字使用派工注入給你的 task-id**，brief 內任何範例一律不得採用。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄是 byte-faithful 的委員原文，改了會破壞完整性檢查）。

## 硬性要求

1. **只准動 `handoffs/reconcile/20260804-govb0-spec-r1/synth.md` 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **驗收＝狀態，不是 rc**：貼出
   `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260804-govb0-spec-r1/synth.md` 的**完整 stdout** 與 rc；
   並貼 `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260804-govb0-spec-r1/sources.lock` 的 rc（須維持 0）。
3. **rc 一律直接取，禁經 pipe**。
4. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
5. 若你決定**不蓋章**，一樣要交產出說明理由，**不要留空檔**。

## 產出

改了哪一行（貼 diff）、`reconcile_stamps_check.sh` 完整 stdout 與 rc、`completeness_check --lock` 的 rc、
以及你逐條確認 findings 歸戶的結果。收尾清 /tmp workdir（保留 claude-501）。
