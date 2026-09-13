# DOCROT consult-r3 收斂 — RECONCILE 戳記輪 R1

brief-kind: stamp
task-id: `20260912-DOCROT-X-STAMP-R1`
findings-round: R1
stamp-target: handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md

## 範本
findings 用 canonical ID：`## <FAMILY>-R1-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。無問題→零 findings sentinel 形態。

## 任務
核可或退回 `handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` 之「群集 / 處置」段（`## 附錄` 之前）。
判準只有一條：**該收斂是否如實反映你們三家 consult-r3 原文**，特別檢查本 epic 反覆出現的三種形態——
「宣稱大於實作」「三家一致但實為多數決」「摘要時把某家講過的限制整條掉了」。

🔴 **本輪不受理新 finding**（`round-kind: stamp`）。超出戳記範圍的意見寫在 verdict 之後、標「非本輪範圍」，不因此拒絕戳記。
🔴 **本輪不動任何碼**；主委在三家 APPROVED ＋ 使用者放行前不動碼。

## 🔴 主委在收斂裡做的擇取（請逐條確認或推翻；推翻＝直接 REJECTED 並寫理由）
依 brief 硬約束「三家意見不同時取**最窄**能過三問者，不取聯集」，主委沒有寫任何折衷，只在下列處擇一家原文：
1. **C6 Task 1.5**（三家共同結論背書閘）：採 grok 版（封閉字面＋同 task-id `committee_family_result` 家數 ≥ roster＋允許 `VERIFY-EXEMPT`）；**不採** codex 之 audit `output_path`／`output_sha256` 逐項對證與「commit_msg 不接受 EXEMPT」。codex：請確認你能接受較窄版，或 REJECTED。
2. **C7 Task 1.6**（碼證指向碼／架構）：採 grok 逐字句（`path:符號`／`doc-literal-only` ≤P3）＋`new_brief.sh` 必答骨架加一句；**不採** codex 之 `CODE-ANCHOR`／`ARCH-EDGE`／`MUTATION` 三必填＋`completeness_check --single` fail-closed；**不採** composer 之 `COMMITTEE_FINDING_TEMPLATE.md` 規則 2 逐字改法（同目的、取一家）。codex／composer：請確認或 REJECTED。
3. **C8**：駁回 codex P1-07「先開 `docs/DOCROT_X_SPEC.md`＋`TODO.md`」（2:1；grok 論證另開 SPEC 複製 D1）；codex 所要之 allowed files／stop gate 改由收斂「定案 TODO」段承載。codex：請確認或 REJECTED。
4. **C9 Task 1.8**：只收窄文案；**不採** codex 之改成 generator 欄位完整行比對＋允許 quoted/fenced；「合法引用會誤拒」登記具名殘留。
5. **D4**：取最窄＝不做（composer 主張 ROADMAP 加一句停輪條）。composer：請確認或 REJECTED。
6. **成效判準**：採 grok `doc_friction_ratio` 版（review-r1／r2 均 ≤0.30 且每輪 ≤20 條）；codex「首輪 heading ≤13」與 composer「關鍵字占比 ≤56%」未採。
7. **測試落點**（grok 表未指定檔名）：取 codex 之既有檔名；Task 1.5 取 composer 之 `tests/governance/test_docrot_claim_committee_backing.py`（codex 指 `test_verify_gate.py`，該檔 CLAUDE.md 已具名為探針空心假綠）。
8. **定案 TODO 本體＝`handoffs/20260912-docrot-x-consult-r3-grok.md` 必答 2 表 Task 1.1–1.8 逐字**，收斂檔只留指標不複述（D1 自指）。

## 前提
fact-verified: 收斂 body 雜湊 `ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307` → 實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md`。戳記行請用**這個值**。
fact-verified: 19/19 finding 全在群集表、completeness PASS、`debt_clear` rc=0 → `bash scripts/reconcile_cluster_attribution_check.sh <synth>`；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260912-docrot-x-consult-r3/sources.lock --synth <synth>`。
assumed: 「取最窄」在 C6／C7 沒有掉任何一家的**硬限制**（只掉了較寬的機制）。請直接攻這條：若你認為被掉的是限制而非機制，REJECTED 並指明哪一條。

## 產出
1. 交件檔（canonical heading 或零 findings sentinel）＋ `VERDICT`。
2. 在 stamp-target 之 `## 戳記` 區 **append 一行**：
   `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307 task:20260912-DOCROT-X-STAMP-R1`
   或 `RECONCILE-STAMP: <family> REJECTED 2026-09-13 — <理由>`。
   🔴 只 append 到 `## 戳記` 區之後，**不得**改動該區以上任何一字（會破 body 雜湊）。
收尾清 /tmp workdir（保留 claude-501）。
