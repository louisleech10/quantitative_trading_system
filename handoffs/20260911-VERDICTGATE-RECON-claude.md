# VERDICTGATE 偵察 — 主委自產版（2026-09-11）

票：`VERDICTGATE`（治理，大；RISK b 跨模組共用路徑、c 多階段難回退）。
使用者裁定：「為了文檔品質，先把治理票做完，再開始量化主線項目」。
本檔＝主委獨立偵察版；三家平行偵察後互審（`feedback_recon_joint_with_committee`）。

## 一、要解的問題（全部有實證）

| # | 事實 | 證據 |
|---|---|---|
| F1 | 批次之間唯一的閘 `review_quorum_check.sh` 只在 `task_id` 匹配 `*-impl-b<N>-<家族>` 時觸發 | `scripts/gate.sh:783-803`（`case "${task_id}" in *-impl-b[0-9]*-*)`） |
| F2 | 主委自任實作（ORCH §1 現行分工，2026-08-17 起）從不派 impl ⇒ **F1 之閘一次都沒跑** | `git log`：SPLITUNIFY 全部 commit 由主委直寫；audit.log 無 `-impl-b` 派工 |
| F3 | F1 之閘只驗「有無 ≥2 非實作者家族之 review 派工留痕」，**不讀裁決** | `review_quorum_check.sh` 檔頭 |
| F4 | SPLITUNIFY 8 輪程式碼審查，**每個批次邊界**都在至少一家寫「不可進」下跨過，且無原提出方確認 | `handoffs/run_receipts/splitunify-attribution-audit-20260911.txt`、`scratchpad/verdict_table.py` 輸出（B1→B2b codex 不可進；B2b R3→B2c codex+grok；B2c→B3 codex+grok；B3→B4 codex） |
| F5 | 委員的 Verdict **不是機械可解析的**：14 份寫 `## Verdict` 空標題、結論在下一行；字面五花八門（`可進 B2c`／`可进 B3`／`不可收票`／`已全數閉合`）；範本規定的三值（可派工／需修補後派工／有根本缺陷需重作）**沒有任何一份照用** | `grep -rhoE "^(## )?Verdict" handoffs/20260911-splitunify-*` |
| F6 | Verdict 從未寫進 `audit.log` ⇒ 閘就算想讀也沒有地方讀 | `grep '"verdict' .claude/gate/audit.log` → 0 |
| F7 | `completeness_check.sh` 只驗「來源 heading ID 皆在綜合檔」，而 `reconcile_build.sh` 之附錄**逐字保留全部原文** ⇒ 永遠通過 | 本票 8 輪皆 PASS，仍漏 3 條 |
| F8 | `reconcile_cluster_attribution_check.sh` 恆 rc=0（檔頭明寫「掛了也是白掛」），且 `cut -c` 對中文按位元組截斷 ⇒ `Illegal byte sequence` ⇒ 大量「附錄斷言：（找不到）」 | 實跑 `/tmp/att_b1.log` |
| F9 | 收斂檔寫「列入 Bx」延後即消失（H6 → 投影把使用者 `tier_min_test_events` 靜默換成 1） | `539431fc` |
| F10 | 委員 Finding 閉合確認（`feedback_finding_closure_reverify`：原提出方重跑反例）只有記憶，無機制 | 本票直到 B7 才第一次做 |

## 二、使用者已給的設計約束（逐字或明確）

- 「**不論哪家執行都要觸發**」——含主委自任。
- 「95% 就收」全專案廢止；停輪只能因「findings 全部閉合且可證偽」。
- 殘留只准「已定義在其他 Phase」或「現階段完全不可能」。
- 治理擴建凍結（`CLAUDE.md:138`）——本票是使用者明示開的例外。

## 三、主委提案（供三家打）

### G-1 Verdict 契約（機械可讀；F5、F6 之根治）
委員產出**必須**含一行 `VERDICT: <值>`，值集封閉、住 `scripts/governance_verdicts.json`：
`proceed`｜`blocked:<ID,ID>`｜`closed`｜`open:<ID,ID>`。`register-output` 時解析並寫入 audit（`committee_output.verdict`）；
解析失敗 ⇒ **register-output 拒收**（fail-closed）。範本同步。

### G-2 批次閘改讀裁決＋改觸發點（F1–F4 之根治）
- 觸發點由「派 impl」改為**兩處必經**：①`gate.sh dispatch` 派**下一批 review**時；②**pre-commit**（見 G-3）。
- 判定：前一批之最新 review 輪，**任一家 `blocked:` 且該家尚無後續 `closed`**（原提出方確認）⇒ 拒。
- 前一批識別：沿用既有 `<root>-b<N>` 命名回溯（gate.sh 既有邏輯），不新造。

### G-3 主委也要領實作權限；pre-commit 最後一道（使用者「不論哪家」之落實）
- 中／大票開新批前主委須 `gate.sh dispatch --impl-self --task-id <root>-impl-b<N>-claude`（走同一條 F1 路徑）；
- pre-commit：commit 訊息帶 `Ticket-Batch: <root>/b<N>` trailer 時 ⇒ 驗該批 token 存在且 fresh；
  含生產碼（`momentum/ api/ frontend/src/`）卻**無** trailer ⇒ 須帶 `Ticket-Batch: small`（小任務路徑，已有 a–d 判準）——**兩者皆無 ⇒ 拒 commit**。

### G-4 收斂完整性改為「處置對得上」（F7、F8）
- `completeness_check`：每個 finding ID 必須出現在**群集表列**（`| … | <ID> … |`）而非任意處；
- 決議列必須含該 finding **斷言首 20 字之逐字引用**（`attribution_check` 從報表改成閘，rc≠0 擋 `debt_clear`）；
- `cut -c` → Python UTF-8 處理。

### G-5 「延後」必須落地為可追蹤項（F9）
收斂檔中 `延後|列入 B[0-9]|另票` 字樣 ⇒ 該列**必須**同時出現在 TODO §E 殘留表（三值理由）或指名之 Task；`debt_clear` 前機檢。

### G-6 閉合確認輪制度化（F10）
任一輪有 `blocked:` ⇒ 修補後**必須**派閉合輪（brief-kind `closure`，只給原提出方），
其 `VERDICT: closed` 才解除 G-2 之阻擋。

## 四、我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| 其他票（GAP-3／EVTLABEL）是否也有「不可進卻跨批」 | 若也有，G-2 上線會讓那些票的既有狀態全部變紅（需基準） | cost |
| pre-commit 加 trailer 檢查對**委員**執行端的 commit 流程是否相容（cx_run 是否會擋） | 委員 commit 被擋 ⇒ 全部派工失敗 | 未查 |
| `Ticket-Batch` 與既有 `Governance-Scope` trailer 之解析共存 | G-7 只解析最末段；兩個 trailer 需同段 | 未查 |

## 五、範圍外（具名）
- 語意層級的「決議是否真的處理了 finding」——現階段不可能機械化；G-4 之逐字引用是能做到的上限。
