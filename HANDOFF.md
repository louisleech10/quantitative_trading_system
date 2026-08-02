# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-02 | **Branch**: **main** | **狀態**: **票 `GOV-STAMP-TASKID-INJECT` 完工；線 C 未開（前提已被實測推翻，需重新裁定）**

## ✅ 本 session 完成：`GOV-STAMP-TASKID-INJECT`

**做了什麼**：`cx_run.sh` 從 audit 導出 `task_id` 注入 prompt（消除委員手抄）；
`brief-kind=stamp` 於戳記落地後自動 `register-output`（消除人工補記）；
`stamp-target` 驗證上移到 `committee_run.sh` **gate dispatch 之前**（失敗時 audit 逐位元組零新增）。

**驗收**（主委獨立複跑，非引用實作端自報）：

- `pytest tests/governance -q` → **512 passed / 0 failed**；`gov_check.sh` rc=0 `REF:docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`
- 新檔 `test_stamp_taskid_inject.py` **65 passed**、21 mutation probes rc=0 `REF:docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`
- 親手證偽：拿掉 `task_id` ERE 跳脫 → 2 failed；`brief-kind` 改回前綴擷取 → 5 failed；復原皆全綠 `REF:docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`
- `test_debt_emit.py` 僅 fixture 改動，零斷言被刪改、無 `skip`/`xfail`、函式數 78→78 `REF:docs/P16_COMMITTEE_DEBT_SPEC.D-001.md`

**流程**：D-001 延伸檔（R1 對抗審 9 findings → R2 codex REJECTED → R3 三家 APPROVED）
→ 實作 TODO（對抗審 5 findings → 三家 APPROVED）→ 實作 7 輪
→ code review 3 輪（CR1 7 條含 regex fail-open／CR2 1 條 P1／CR3 零活缺陷）→ 閉合輪三家判可 commit。
**五份收斂檔 `reconcile_stamps_check.sh` 全數 rc=0**；帳本 `--has-open` rc=0。

## ▶ 下一步：線 C —— **原前提已被實測推翻，需使用者重新裁定**

| 實測（2026-08-02） | 值 |
|---|---|
| `debt_ledger --has-open`（3 萬行） | 46–64ms（SPEC 要求 <100ms，早已達標） |
| 30,960 行中真正被解析的 JSON | 2,448 |
| 92% 散文的來源 | `gate.sh:616-625` 每次發 token 寫 15 行，且含 JSON 沒有的 intent／risk／facts_asked 等欄，不可刪 |

⇒ 效能不是問題；`gate_deny` 僅 366 行（1.2%），單搬它收益趨近於零。
唯一站得住的版本＝**B′：15 行散文壓成 1 行 JSON（欄位一字不減）＋歸檔既有散文**，
但它**只買到衛生與成長率，不買效能也不買正確性**。詳見 `handoffs/20260802-LINEC-AUDIT-SPLIT-SPEC-DRAFT.md`。
**開工前須先讓使用者裁定要不要花這個工。**

## ⚠️ 本 session 新開的票（`handoffs/20260801-GOV-AMEND-BACKLOG.md` B-9/B-10）

- **`GOV-DOCS-STAMP-PROVENANCE`**：`docs/` 內 D 延伸檔拿不到可過機檢的戳記
  （`register-output` 只收 `handoffs/`）；程序 §3.2 與 §3.1／§2 自相矛盾。修法須走 §5 的 R。
- **`GOV-DEXT-TEMPLATE-KIND`**：`template_check.sh` 無 D 延伸檔 kind ⇒
  `gate.sh dispatch --spec <D延伸檔>` 永遠拒發 token。現行繞法：`--spec` 傳底本 SPEC。

兩者皆為 `FROZEN_DOC_AMENDMENT_PROCEDURE.md` v1.0 首次實戰才現形，各燒一輪派工，皆 fail-closed 未誤放行。

## 📌 開工前必做

1. 稽核本檔／ROADMAP vs repo 實況（本檔數據為 2026-08-02 實跑）
2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`；收集節點用 `reconcile_build.sh`
4. **stamp brief 現在必須帶 `stamp-target:` 欄**（本票新增的閘已生效）
