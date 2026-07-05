# tgf-todo-stamp-composer-r4（2026-07-05）

Composer 2.5 reconcile re-stamp 輪（B4 gate D-2 機檢處置索引後本體 hash 變更）。

## ① 索引核對 ADV-COMPOSER-12..24

| ID | 索引處置 | 本輪 RECHECK | 與 r3 重驗一致 |
|---|---|---|---|
| ADV-COMPOSER-12 | §G 13 fixture＋§A 計數移除（REOPEN CLOSED） | `4 探針\|…` = 0 | ✓ |
| ADV-COMPOSER-13 | manifest typo 已修（Composer 確認） | 前輪 CLOSED | ✓ |
| ADV-COMPOSER-14 | §0 解耦/紅線 4 條 | grep = 3（實質 CLOSED） | ✓ |
| ADV-COMPOSER-15 | 同 ADV-CODEX-5 | `BLOCKING.*或.*ID:` = 1 | ✓ |
| ADV-COMPOSER-16 | manifest [C-3] 三條 | `三條` = 1 | ✓ |
| ADV-COMPOSER-17 | 同 12 | 同 12 | ✓ |
| ADV-COMPOSER-18 | 頭尾狀態一致 | `Internal Frozen` = 0 | ✓ |
| ADV-COMPOSER-19 | 頭注已生成 | `待生成` = 0 | ✓ |
| ADV-COMPOSER-20 | --mutate 契約 | `--mutate` = 6 | ✓ |
| ADV-COMPOSER-21 | [D-3]/[F-3] 邊界 | `可先行部分僅限` = 1 | ✓ |
| ADV-COMPOSER-22 | delta 基線 60 | `before=60`=1；`≤ 75`=0 | ✓ |
| ADV-COMPOSER-23 | WARN 句回寫 | `僅 WARN 不拒發` = 1 | ✓ |
| ADV-COMPOSER-24 | 四處 gate fixture 改 5（Composer 確認義務） | `四例\|4 gate fixture\|gate fixture 4` = 0 | ✓ |

## ② body_hash

`bash scripts/reconcile_body_hash.sh handoffs/2026-07-04-TGF-TODO-ADV-RECONCILE.md` → `88d3078f252eb4ea46a18a39f4ccd07f14a02b5dc8b17e708d9c630de27bc5b5`（與預期一致）

## ③ 戳記

已 append canonical 戳記至 `## 戳記` 區（codex r4 行之後）。
