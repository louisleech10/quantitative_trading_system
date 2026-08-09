# Handoff

REF:handoffs/reconcile/20260809-govb1-b6-review-r1/synth.md
REF:handoffs/reconcile/20260809-govb1-b5-review-r2/synth.md
REF:handoffs/reconcile/20260809-govb1-x-review-r3/synth.md
REF:handoffs/reconcile/20260809-govb1-x-consult-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main | **閘**: `govb1_final_gate` **12/12 PASS**

## 🔴 接手第一件事：**B7 實作**（Task 3.1 + 3.2 / `票 B-15`）

歸屬＝`scripts/govb1_task_tickets.tsv` 第 `7` 批兩列。規格＝`docs/GOVB1_INPUT_QUALITY_TODO.md` Phase 3（**唯讀**）。
🔴 **開工前稽核尚未做**——先驗五件事再動手：標的檔是否存在／是否在 `govb1_scope.manifest` allow 內／
既有 caller／TODO 宣稱的行為是否與現況相符／有無同型地雷。

🔴 **實作端＝主委（Opus）自任**（使用者 2026-08-09 授權）；review＝codex+composer 兩家。

## ✅ B6 收案（`票 B-25` 事實單一來源）

commit `11ea47a`(OOE) `030c9cf` `266e6b8` `87aeb8c`；兩家戳記 APPROVED；測試 50→**56**。
交付＝`scripts/fact_keys.json` ＋ `gen_fact_key_blocks.sh`（emit/`--check`/`--write`）＋
`gov_check.sh` 第 5 段 ＋ 段號現算（原 10 處分母全寫死）。

🔴 **本批兩個必須傳下去的教訓**：
1. **`govb1_scope.manifest` 的 `allow` 是凍結 TODO 宣告集的機械鏡像，不是主委的宣告欄。**
   往裡面加路徑＝聲稱 TODO 宣告過 ⇒ `test_t01_f5_manifest_matches_task_decl` 等 **7 條立刻紅**。
   凍結 TODO 沒宣告的路徑，唯一通道是 `Governance-Scope: out-of-epic`（兩家裁定 (A)，
   但**兩家都承認語意 laundering 疑慮成立**＝已知代價，非已解決）。
2. 規格自身可能矛盾。B6 的宿主檔同時被標「唯一 fact-key 宿主」與「只讀」⇒ 兩個方向都是死路。
   處置走延伸檔 `docs/GOV_B6_SCOPE_AMENDMENT.md`（**不就地改凍結文件**），由委員裁決。

## 🔴 待辦與具名殘留

| 代號 | 內容 | 何時解 |
|---|---|---|
| — | **B7–B10 未開工**（B7=`B-15`／B8=Task 4.1／B9=`B-38`／B10=`B-31`）；**B4 階段 2** scope 錯配須另立票 | 依序 |
| — | 🔴 **新**：戳記類派工單**沒有要求委員寫 P3-00 sentinel** ⇒ 零 findings 的戳記輪仍得走 `--abandon` 逃生口。`票 B-38` 機制已存在但產出端沒接上 | 併 `B-38`／B9 |
| — | B6 殘留：fence 內標記仍被接受／`LC_ALL=C jq` 釘子今日無鑑別力（保留＋明載無覆蓋）／locale 貧瘠 runner 上只剩來源斷言 | 見收斂檔 C3、C4 |
| `B-50` | 執行端**兩次**把工作區留在壞狀態，**皆無機制通知**（本輪兩家皆已正確還原） | 見 backlog |
| `B-49` | roles SoT 表達不了「編排端自任實作」＋ `test_stamp_taskid_inject.py:769` 靜默 skip。**修它須動 `_B45_HARNESS` ⇒ 凍結期間做不到** | 🔴 **有定時炸彈**：凍結一解除即紅 |
| `B-48` | `debt_clear --abandon --kind` **不查核事實** | 見 backlog |
| `R-15` | `scripts/governance_families.json` **不可 commit** ⇒ 走 ambient M | epic 結束後 |
| — | `docs/ROADMAP.md` **不在 manifest** ⇒ epic 期間更新它須走 out-of-epic；本輪未更新 | epic 結束後補 |
| — | B3 十檔 ambient M、`.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 皆**不得 commit** | — |

## ⚠ 踩過就別再踩

`grok` 額度用罄（403）⇒ `active_stampers=["codex","composer"]`，2/2 即滿足，**不是缺額殘留**。
session 名須 `<日期>-<epic>-<batch>-<kind>-r<N>`。`reconcile_build` 之 `sources.lock` 預設 `mode=discovery`，
`debt_clear` 要 `mode=review` ⇒ 先 `reconcile_build <session> --mode review --rebuild`（**不得再帶委員檔**）。
`cx_run.sh` **不可直呼**（缺 `ROUND_ID`），一律走 `committee_run.sh --session ... -- <gate flags>`。
`gate.sh dispatch --adversarial` 要的是**已完成的**對抗審結果；派對抗審本身用 `--risk low`。
🔴 `cmd | tail; echo rc=$?` 讀到的是 **tail 的 rc**——本輪主委又犯一次（誤讀 `plain_docs_sync` 為綠）。
