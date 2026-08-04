# 第 0 批 SPEC R2 收斂戳記

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-spec-r2/synth.md

## 任務

複核 `handoffs/reconcile/20260805-govb0-spec-r2/synth.md` 的**群集／處置段**是否忠實反映你 R2 的 findings，
確認無誤後 **append 一行 RECONCILE-STAMP** 到該檔的 `## 戳記` 區段。

### 你要確認的（逐條，不是形式蓋章）

1. **你自己 R2 的每一條 finding 都被歸入某個 E 群，且處置與你的主張一致。**
   findings 在附錄逐字保留（byte-faithful），群集表在前段。
   **上一輪 codex 就是在這一步抓到主委把 finding 歸錯 ID**——請照樣逐條核對 ID 對應，不要只看語意。
   若有任一條被歸錯群、處置被弱化、或主張被改寫 ⇒ **不要蓋章**，寫明哪一條、怎麼錯。

2. **`E-SCOPE`（本批明確不受理範圍）是主委裁決，不是你的原話。**
   它把四項劃為本批不做：**產出截斷偵測 oracle**（→`票 B-35`）／**`B-34` 語意閉合**／
   **`B-24` 機械強制面**（R1 已裁 SPLIT）／**`B-15` FP-2 定位**。
   裁決依據＝使用者定死「沒 100% 解就做 95% 那版現在收，殘留具名記錄不當阻塞」＋
   收斂趨勢警訊（R1 19 條 5 P0 → R2 17 條 7 P0，**P0 未下降**，命中 P16 的 scope-accretion 失敗模式）。
   🔴 **若你認為某項不受理會使本批交付物本身失效**（而非只是不夠完美），**不要蓋章**，寫明失效路徑。
   若只是「不夠完美」，請接受並蓋章——這是使用者定死的取捨。

3. **`E-3` 的主委獨立驗證與原型③**（`handoffs/govb0_probes/b15probe4.sh`／`b15probe5.sh`）你可自行重跑核對。
   宣稱是：四個向量（`eval`／`$()`／反引號／子 shell）**在現行 gate 就已 fail-open**，
   且原型③對 26 條語料 **26/26 全對**。

4. **`E-6` 改設計**（並發由「兩者皆保留」改為「序列化拒絕」）是主委裁決。不同意請寫明。

### 🔴 本輪為第二次戳記輪（第一次三家全數拒章，兩個缺陷已修）

第一輪 `GOVB0-R2-STAMP`：**codex／composer／grok 三家全部拒章**，其中 codex 與 composer
**各自獨立**指出同兩個缺陷，均已修正：

| 缺陷 | 委員指認 | 修正 |
|---|---|---|
| **群集表漏 `COMPOSER-R2-P1-01`**（未列入任何 E 群） | codex `MISMATCH_1`／composer 不蓋章理由 | 新增 **`E-13`** 一列，並記錄此事暴露的檢查器盲點 |
| **`E-10` 弱化 `CODEX-R2-P1-07`**（codex 要求每家族 ≥50 筆、≥3 session／UTC 日期、未達門檻不得用暫定值；主委只寫 composer 的 ≥20／<10） | codex `MISMATCH_2` | 定稿門檻改採 **codex 較嚴者（≥50 筆 ＋ ≥3 session／日期）**；未達門檻時的處置由主委明示取捨並寫明與 codex 主張的差異 |

⚠️ **`E-10` 的取捨請特別看**：codex 主張「未達門檻**不得用暫定值**」，
主委改為「機制上線並以暫定值運作，但 **Task 3.3 不得宣稱完工**、值標 `PROVISIONAL`」，
理由是**無 timeout 正是 `B-14` 事故的成因**（空等 2h20m），「有暫定 timeout」嚴格優於「無 timeout」。
**若你不同意此取捨，請拒章並寫明。**

⚠️ **檢查器盲點（本輪實證，已記入 synth）**：`completeness_check --lock` 只驗
「來源 ID 是否出現在綜合檔」，而附錄逐字保留使任一 ID **必然存在**
⇒ **「該 ID 有沒有進群集表」沒有任何機器檢查**，本輪即因此漏掉一條而 rc 仍為 0。
主委已加人工自檢（17/17 皆在群集表）。**請你們順便複核這道自檢是否可靠。**

### 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:<派工注入給你的 task-id>
```

- `<你的家族名>` 以派工注入的家族名為準。
- `sha256` **逐字照抄上方**（`bash scripts/reconcile_body_hash.sh <該檔>` 對「`## 戳記` 之前內容」算出）。
- `task:` **逐字使用派工注入給你的 task-id**，brief 內任何範例一律不得採用。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄為 byte-faithful 委員原文）。

🔴 **grok 的立場**：`reconcile_stamps_check.sh` 要求 `review_families` 全員，但 grok 是 implementer、
被角色閘擋在 R2 review 之外（`票 B-34`）。⇒ **grok 請以「第三方複核歸戶正確性」立場審**：
不是確認「我的 findings 有沒有被歸戶」（你沒有 findings），而是確認
「**群集表對附錄逐字 findings 的歸戶是否正確、處置是否忠實、`E-SCOPE` 的裁決是否有隱藏掉項**」。

## 硬性要求

1. **只准動 `handoffs/reconcile/20260805-govb0-spec-r2/synth.md` 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **驗收＝狀態，不是 rc**：貼出
   `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r2/synth.md` 的**完整 stdout** 與 rc；
   並貼 `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r2/sources.lock` 的 rc（須維持 0）。
3. **rc 一律直接取，禁經 pipe**。
4. 禁 `git checkout`／`git restore`；不要 commit、不要 push。
5. 若你決定**不蓋章**，一樣要交產出說明理由，**不要留空檔**。

## 產出

改了哪一行（貼 diff）、兩支檢查器的完整 stdout 與 rc、逐條確認 findings 歸戶的結果、
以及你對 `E-SCOPE` 四項不受理的立場。收尾清 /tmp workdir（保留 claude-501）。
