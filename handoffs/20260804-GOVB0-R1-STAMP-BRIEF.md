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

### 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-04 sha256:1088062c7da80a7ea23978675f6a19d433b90d7523c21d5b75eb72470b581d7d task:<派工注入給你的 task-id>
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
