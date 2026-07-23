<!--
委員語意審 charter（Convergence Method Task 7.1 / B6）
機械層（completeness / Phase 3–4）擔完掉箱後，委員只審語意層。
-->

# 委員語意審範本（Semantic Review Charter）

## Charter（鐵律）

1. **只審語意**：委員審「講水 / 降級 / 錯併」語意層（假 body、錯併 finding、不當降級敘事、證據與斷言不符）。
2. **禁列漏掉的 ID**：不得在語意審中列「漏掉的 ID / missing IDs / dropped IDs」清單——**那是機械層（Phase 4 self-check / completeness）的活**。委員**不得**代替機械層找掉 ID（防退化）。
3. **順序不可逆**：機械層 PASS（`completeness_check` rc=0）在前 → 語意 stamp 在後。機械層 exit≠0 時委員**不得**蓋 final。
4. **fresh=NONE 收斂**：一輪 fresh review = **NONE**（0 新 finding）→ 允許收斂蓋章 + 產出 `committee_accepted.json`。
5. **產物 schema**（餵 Oracle⑤ residual）：

```json
{"accepted_ids": ["CODEX-R1-P2-01", "COMPOSER-R1-P2-01"]}
```

由 `scripts/write_committee_accepted.sh` 在 fresh=NONE 且 charter 合法後寫入 session。

## 何時蓋 final

| 前置 | 結果 |
|------|------|
| 機械層 completeness `rc≠0` | **拒 final**（gate 拒發；委員 stamp 無效） |
| 機械層 `rc=0` + fresh 有新語意 finding | 不蓋 final；修完再開一輪 |
| 機械層 `rc=0` + **Fresh findings: NONE** | **允許 final stamp** + producer 寫 `accepted_ids` |

## 產出格式（委員填）

```markdown
# 委員語意審 — <session_id>

## Scope
只審語意（講水/降級/錯併）。**禁列漏掉的 ID**。

## Mechanical precondition
- completeness: PASS（rc=0；由機器出口核實，非本檔自證）
- sources.lock: FROZEN

## Fresh findings
NONE

## Semantic findings（若有；fresh≠NONE 時填）
（每條必須是語意主張，不得只列 ID）

### SEM-01 講水 / 假證據
**斷言**: …
**碼證**: …
（無則整節省略；不得寫「漏了 CODEX-R1-…」當 finding）

### SEM-02 錯併
…

### SEM-03 不當降級
…

## Verdict
- [ ] CONDITIONAL（有語意 finding，不蓋 final）
- [x] APPROVED — Fresh findings: NONE → 收斂蓋章

## Producer 指令（主委執行）
```bash
bash scripts/write_committee_accepted.sh \
  --session handoffs/reconcile/<session> \
  --review <本語意審檔路徑>
# → handoffs/reconcile/<session>/committee_accepted.json
```
```

## 非法產出（charter 判拒）

| 非法 | 原因 |
|------|------|
| 只列 missing ID、無語意 | 侵佔機械層；producer 拒寫 |
| 裸列 `## FAM-R1-Pn-NN` / bullet canonical ID 清單無語意正文 | 冒充語意審；producer 拒寫（CODEX-B6-P1-01） |
| SEM finding 缺 polarity / **斷言** / **碼證** | 非語意主張；producer 拒寫 |
| Fresh findings: NONE 又含 SEM-* / Findings 實質內容 | 狀態混淆；producer 拒寫 |
| 缺 Verdict: APPROVED 或 Mechanical precondition | charter 不完整；producer 拒寫 |
| 機械層未 PASS 仍宣稱 final | 順序不可逆；gate final 拒發 |
| 省略 Fresh findings 卻要求 accepted | producer 拒寫 |
| `accepted_ids` 少於 union | Oracle⑤ residual>0 → completeness FAIL |

## 與機械層分工

| 層 | 負責 | 工具 |
|----|------|------|
| 機械 | 掉 ID / dup / late / roster / body-hash / residual | `completeness_check.sh` |
| 語意 | 講水、降級、錯併 | 本 charter + 委員人工 |
| 銜接 | fresh=NONE → `accepted_ids[]` | `write_committee_accepted.sh` |

## 可證偽反例（給複驗）

1. 機械 incomplete（roster 缺檔）→ 委員試 `gate.sh dispatch` final → **exit≠0**（`test_semantic_stamp_after_completeness`）
2. 機械 PASS + Fresh findings: NONE + producer → gate final **PASS**（`test_fresh_none_allows_final_stamp`）
3. 語意檔含「漏掉的 ID」清單 → producer **exit≠0**，不寫 `committee_accepted.json`
4. 裸 bullet / `## CODEX-R1-P0-01` ID 清單 + Fresh findings: NONE → producer **exit≠0**（`test_producer_rejects_bare_id_list`）
5. `### SEM-01` 無 **斷言**/**碼證**/polarity → producer **exit≠0**（`test_producer_requires_semantic_fields`）
