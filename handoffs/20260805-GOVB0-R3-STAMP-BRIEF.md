# 第 0 批 SPEC R3 收斂戳記

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-spec-r3/synth.md

## 任務

複核 `handoffs/reconcile/20260805-govb0-spec-r3/synth.md` 的**群集／處置段**是否忠實反映你 R3 的 findings，
確認無誤後 **append 一行 RECONCILE-STAMP** 到該檔的 `## 戳記` 區段。

**本輪為 R3 收斂的第一次戳記輪。**（R1／R2 各自的戳記輪皆已完成並三家 APPROVED。）

## 你要確認的（逐條，不是形式蓋章）

### 1. 你自己 R3 的每一條 finding 都被歸入某個 F 群，且處置與你的主張一致

findings 在附錄逐字保留（byte-faithful），群集表在前段（`F-1`～`F-7`）。
🔴 **請逐條核對 ID 對應，不要只看語意**——R1 與 R2 兩輪的戳記輪，codex 都是在這一步抓到主委把 finding 歸錯 ID。

**本輪主委已犯同樣的錯兩次，兩次都已修**：
- **第一次**（主委自檢抓到）：把 `COMPOSER-R3-P1-02`／`P2-01`／`P2-02` 誤寫成 `P0-02`／`P1-04`／`P2-01`，
  其中 `COMPOSER-R3-P2-02` 完全未被引用。
- **第二次**（🔴 **本輪你們三家全數拒章時各自獨立指出**）：`COMPOSER-R3-P1-01`（E-10 門檻）與
  `COMPOSER-R3-P1-02`（1b 語料）在 **F-4／F-6 之間對調**。已依你們的指認修正
  （F-4 ← `P1-01`、F-6 ← `P1-02`），主委並回查原檔逐條確認。

⚠️ **這第二次暴露了主委自檢的邊界，請特別注意**：自檢問的是「每個 ID **是否出現**在群集段」，
兩個 ID **都出現了**、只是**掛在錯的列** ⇒ **自檢 rc=0、`completeness --lock` rc=0，兩道機檢皆無感**，
只有你們的**語意複核**抓得到。
⇒ **`票 B-36` 的產出端修法（骨架預列 ID）也只能擋「漏」，擋不了「錯位」**；
「錯位」目前**沒有任何機械防線**。此殘留已寫入 synth 與 `票 B-36`。
**請你們在本輪特別針對「ID 錯位」逐條核對。**

### 2. 主委在本輪定死的三組裁決，請逐組表態

| 裁決 | 內容 | 依據 |
|---|---|---|
| **`F-2` 契約四項判定結果** | unquoted `-c` → BLOCK；遞迴深度**上限 3 層**逾限 fail-closed；跳脫字元**不終止引號 span**、無法確定邊界時 fail-closed；heredoc 本體**視為引號 span** | R3 只列項目未定結果（`CODEX-R3-P0-02`），主委補定 |
| **`F-2` 第二半：放寬至 `awk`** | Task 2.1 限制由「純 shell/`sed`」改為「純 shell／`sed`／`awk`」，維持禁 python | `CODEX-R3-P0-02` 要求「明文解除限制**並附效能 receipt**」。**receipt 已補**：`bash handoffs/govb0_probes/awk_hotpath_bench.sh` → 每次工具呼叫 **+5 ms**（正常工具呼叫約 80 ms、權限分類器 2300–3000 ms）⇒ 約 6% 開銷 |
| **`F-3` lock 生命週期** | ownership 綁 attempt id（含 pid＋UTC 起始戳）／release 在 `_emit_family_result` 後**必定執行**（不依賴 publish 成功）／stale 判定＝pid 已死**或**逾 (家族 timeout＋外層安全閥)／`failed` 後同 `<out>` 重派**正常放行**／被拒 attempt **不寫 `result_state`** 只記拒絕事件 | `CODEX-R3-P0-03`／`COMPOSER-R3-P1-03` 指出 R3 只寫「拒絕」未定生命週期 |

🔴 **不同意任一組請拒章並寫明**，特別是 `F-3` 的「被拒 attempt 不寫 `result_state`」——
理由是它會污染 Task 3.1 的 duration 統計進而影響 Task 3.3 定稿，但這也意味著
「每 attempt 恰一筆 `result_state`」的斷言必須排除被拒者，請確認此設計自洽。

### 3. `E-SCOPE`（不受理範圍）維持不變

四項：截斷 oracle（`票 B-35`）／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位。
**你們已於 R2 戳記輪表態接受**（codex 逐項確認「不使本批交付物本身失效」），R3 輪 codex 亦標為 `OUT-OF-SCOPE`。
本輪**不再重新徵詢**；若你改變立場，請拒章並寫明失效路徑。

### 4. 收斂趨勢的判斷

群集段宣稱「R3 的 11 條大多是主委自身的漏改與計數漂移，非新機制缺口 ⇒ accretion 已中止」。
**請攻這個判斷**：若你認為 R4 仍會再生出同量級的新 P0，請說明理由——這關係到本批要不要再開 R5。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:2949edaacb5f7a35a3e4cfadd143a4b48962d1534fd73eeec3ba162b2ccf696b task:<派工注入給你的 task-id>
```

- `<你的家族名>` 以派工注入的家族名為準。
- `sha256` **逐字照抄上方**（`bash scripts/reconcile_body_hash.sh <該檔>` 對「`## 戳記` 之前內容」算出）。
- `task:` **逐字使用派工注入給你的 task-id**，brief 內任何範例一律不得採用。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄為 byte-faithful 委員原文）。

🔴 **grok 的立場**：`reconcile_stamps_check.sh` 要求 `review_families` 全員，但 grok 是 implementer、
被角色閘擋在 R3 review 之外（`票 B-34`）。⇒ **grok 請以「第三方複核歸戶正確性」立場審**：
不是確認「我的 findings 有沒有被歸戶」（你沒有 findings），而是確認
「**群集表對附錄逐字 findings 的歸戶是否正確、處置是否忠實、主委的三組裁決是否有隱藏掉項**」。

## 硬性要求

1. **只准動 `handoffs/reconcile/20260805-govb0-spec-r3/synth.md` 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **驗收＝狀態，不是 rc**：貼出
   `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r3/synth.md` 的**完整 stdout** 與 rc；
   並貼 `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r3/sources.lock` 的 rc（須維持 0）。
3. **rc 一律直接取，禁經 pipe**。
4. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
5. 若你決定**不蓋章**，一樣要交產出說明理由，**不要留空檔**。

## 產出

改了哪一行（貼 diff）、兩支檢查器的完整 stdout 與 rc、逐條確認 findings 歸戶的結果、
對主委三組裁決的表態、以及對「accretion 已中止」判斷的攻擊。
收尾清 /tmp workdir（保留 claude-501）。
