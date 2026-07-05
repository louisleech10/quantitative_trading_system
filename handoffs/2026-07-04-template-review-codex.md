# SPEC/TODO/Adversarial Template Review — Codex

Scope read: `HANDOFF.md`, `CLAUDE.md`, `handoffs/2026-07-04-template-review-BRIEF.md`, 4 templates, 2 checker scripts. Other `handoffs/2026-07-04-template-review-*.md` review outputs were not read.

## Answers to the Three Questions

1. **合適性**：方向正確。V13 從超長 prose 改成錨點 + 分層 + adversarial 補語義，是合理取捨；SPEC 的 §A/§G/§V、TODO 的 per-Task depth、adversarial 的挑戰前提都對準真事故。但目前「制度宣稱」強於「機檢實作」，尤其 §A fact receipt、TODO per-Task 欄位、RESULT receipt 規則，會讓 gate 給出過度安全感。
2. **冗長度**：四份 template 本身不冗長，`wc` 顯示 60/75/58/28 行，值得保留。真 token 熱點是 TODO prompt 每次要求讀 `.github/copilot-instructions.md`、`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUIDE.md`，再加中/大型雙家族 review；這是可控但應分級快取/摘要化的成本。
3. **遺漏/瑕疵**：主要缺口不是多寫幾欄，而是欄位與 checker 的契約不閉合：高風險 §G 不按 §RISK 條件判定、§A receipt 條件錯綁「已確認」、TODO 每 Task 只做全文件 grep、RESULT 不驗 JSON/receipt/DONE 極性。另有三方數據正確性流程未被 SPEC template 顯式掛鉤，容易在 Feature Factory 任務被漏。

## Findings

[C1] [BLOCKING] §A FACT-RECEIPT 機檢綁錯欄位，無法擋「已驗證事實」無實測證據  
Evidence: `CLAUDE.md` says `§A「已驗證事實」凡涉及資料結構的型別/形狀/單位，必須附「實際跑了什麼、印出什麼」`; `SPEC_TEMPLATE.md` has `- **已驗證事實**（附驗證方式）`; `template_check.sh` only checks lines containing `已確認` plus data-structure tokens before requiring `FACT-RECEIPT:`.  
Failure mode: A SPEC can write `已驗證事實：raw_data.index 是 DatetimeIndex（讀碼推論）` without `FACT-RECEIPT:` and still pass, because the line does not contain `已確認`. This recreates the timestamp accident the rule was designed to prevent.  
Fix: In `template_check.sh`, scan the entire §A section for both `已驗證事實` lines and following bullets containing data-structure tokens; require `FACT-RECEIPT:` on same/neighbor line. Update `SPEC_TEMPLATE.md` to show the exact syntax, e.g. `FACT-RECEIPT: command=... stdout=...`.

[C2] [BLOCKING] §A facts-resolved can be satisfied by the label `已確認結果` rather than an actual confirmation  
Evidence: `SPEC_TEMPLATE.md` includes the label `- **已確認結果**`; `template_check.sh` accepts any `grep -q "已確認"` in §A.  
Failure mode: A filled SPEC can leave unresolved user-only facts but include the normal label `已確認結果：待回覆` or `已確認結果：N/A` and pass the facts-resolved gate. The mechanism meant to prevent "沒問到答案就在錯前提上寫 SPEC" becomes a string-presence check.  
Fix: Require either `待確認：無` or a structured confirmation line matching date/source, e.g. `已確認結果：YYYY-MM-DD 使用者確認 ...`; reject `待回覆|未確認|N/A|無法確認` on that line.

[C3] [MAJOR] 高風險 §G 條件未被機檢判定，低風險與高風險都同一套寬鬆規則  
Evidence: `SPEC_TEMPLATE.md` says `命中 (a) 或 (d) → §G Golden 必填`; `template_check.sh` only checks `## §G` exists or any `§G.*N/A|N/A.*§G`; it does not parse §RISK.  
Failure mode: A high-risk SPEC can mark `§G：N/A` in §N and pass, even if §RISK says it touches ML/data correctness. Conversely, a low-risk task can carry a placeholder §G and pass without a meaningful baseline.  
Fix: Parse §RISK for `(a)` or `(d)`/`數值`/`ML`/`回測`; if present, require `## §G` and reject `§G N/A`. If absent, allow explicit §N N/A with reason.

[C4] [MAJOR] TODO per-Task required fields are promised but only checked globally  
Evidence: `TODO_GENERATION_PROMPT.md` says `每 ### Task 內含「驗證」「邊界」「不可做」`; `template_check.sh` uses global `need "驗證"`, `need "邊界"`, `need "不可做"`.  
Failure mode: A TODO with five tasks where only one task has the three fields passes. Execution agents then guess on the incomplete tasks, while gate reports compliance.  
Fix: Split TODO by `^### Task` and check each block for `驗證`, `邊界`, `不可做`; optionally require `實作要點`, `修改檔案`, and `SPEC ref` per block because the prompt makes those depth requirements operational.

[C5] [MAJOR] RESULT template states receipt/DONE rules, checker only validates enum strings  
Evidence: `RESULT_TEMPLATE.md` says `RUNTIME_CHECK=PASS 時 RECEIPTS 不得為空` and `MUTATION_CHECK=NOT_RUN 時，同 task 不得宣稱「已驗 / DONE / 全綠」`; `template_check.sh` result branch only checks field presence and enum values.  
Failure mode: An executor can submit `RUNTIME_CHECK=PASS`, `RECEIPTS=[]`, and a natural-language `STATUS: DONE`; the checker passes even though the template explicitly forbids treating that as verified.  
Fix: Add result checks: if `RUNTIME_CHECK=PASS`, require non-empty JSON-ish `RECEIPTS`; if `MUTATION_CHECK=NOT_RUN`, grep below fields for operational polarity (`已驗|DONE|全綠|passed|通過`) and fail unless the text is clearly quoted failure context. Validate `RECEIPTS`/`OPEN_PENDING` are arrays.

[C6] [MAJOR] TODO prompt creates heavy per-run token load by requiring full constitution docs every time  
Evidence: `TODO_GENERATION_PROMPT.md` says `無條件讀：.github/copilot-instructions.md、docs/ARCHITECTURE.md、docs/DEVELOPMENT_GUIDE.md`; `CLAUDE.md` already carries the central dispatch rules and project constraints.  
Failure mode: For every TODO generation, a large architecture/development-guide reread competes with actual SPEC/TODO reasoning budget. The stated reason for V13 was that long documents exceeded reliable instruction budget; this reintroduces that pressure at generation time.  
Fix: Keep "read constitution" for medium/large, but replace full-doc reread with a short canonical `docs/AGENT_CONSTITUTION.md` or machine-extracted summary plus targeted reads only when the SPEC touches a domain. Make the prompt say which sections to read, not whole large docs unconditionally.

[C7] [MAJOR] Three-party data correctness rule is not first-class in SPEC/TODO templates   〔REF:handoffs/2026-07-04-template-review-RECONCILE.md〕 〔SUPERSEDED:早期紅燈紀錄已由 TGF epic 修復+stamped reconcile 取代〕
Evidence: `CLAUDE.md` says Feature Factory data correctness passes only when `Claude + GPT-5.5(Codex) + Composer 2.5` independently sign off and must use real `data_cache/feature_klines/kline_cache.h5`; `SPEC_TEMPLATE.md` only has generic §G Golden and §V tests.  
Failure mode: A Feature Factory or multi-TF merge SPEC can satisfy §G with a baseline but omit the mandatory three-party independent data-correctness signoff and real-kline requirement. Adversarial may catch it, but the template does not force authors to surface it.  
Fix: Add a compact conditional line to §RISK/§G: if task touches Feature Factory data generation/calculation/merge/split/leakage, list required signoff artifacts and real-kline validation plan; otherwise mark N/A.

[C8] [MAJOR] `coverage_check.sh` only proves manifest IDs appear, not that SPEC IDs flow into TODO as claimed  
Evidence: `TODO_GENERATION_PROMPT.md` says `每個 SPEC ID → TODO 對應位置`; `coverage_check.sh` accepts only `<manifest_file> <target_doc>` and greps `[ID]` in the target.  
Failure mode: If a SPEC creates new Task/Test IDs not present in the original manifest, or TODO omits SPEC-internal IDs while covering manifest IDs, coverage passes but SPEC→TODO traceability is incomplete.  
Fix: Either define that all SPEC IDs must originate from the manifest, or add a second mode `coverage_check.sh spec-to-todo <spec> <todo>` that extracts `[X-N]` IDs from SPEC and requires them in TODO.

[C9] [MINOR] `coverage_check.sh` can be gamed by mentioning IDs in comments or irrelevant text  
Evidence: The script comment says `任一處出現該 [A-1] 字樣即算覆蓋`; implementation is `grep -qF "[${id}]"`.  
Failure mode: A TODO can include a dumped "covered IDs" list while omitting actual task content. This is acceptable as an honest boundary, but the output phrase `COVERAGE PASS` can be overread as semantic coverage.  
Fix: Rename output to `ID PRESENCE PASS` or require ID occurrence under headings/task lines for TODO mode. Keep current grep as a cheap first gate if renamed honestly.

[C10] [MINOR] SPEC template says old V12 per-Task depth is "全保留", but current SPEC only has one sample task skeleton  
Evidence: `SPEC_TEMPLATE.md` says `per-Task 偽碼/函式名、Golden、邊界測試、人工確認）全保留`; the actual task skeleton has `改法` and `檔案：精確到函式名`, but no explicit task IDs/test IDs convention.  
Failure mode: Authors may produce prose phases without stable IDs, making TODO traceability and coverage checks weaker.  
Fix: Add a one-line convention in §P: each Task/Test/Gate must carry stable IDs if a manifest exists, e.g. `[P1-2] Task 1.2`, `[T1-2a]`.

[C11] [SUGGESTION] Adversarial prompt is strong but does not require checking checker outputs  
Evidence: `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` checks template anchors and hollow content, but does not tell reviewer to run or inspect `template_check.sh`/`coverage_check.sh` output.  
Failure mode: Reviewers may do semantic review while the artifact would fail gate, or may trust "gate passed" without seeing exact failures.  
Fix: Add an optional preface: "If local shell access exists, run template_check/coverage_check and include outputs; otherwise state NOT_RUN." This keeps read-only reviewers functional.

[C12] [SUGGESTION] `STRICTNESS` variable is declared but unused  
Evidence: Adversarial prompt variables include `{{STRICTNESS|MAXIMUM}}`; no later branch references strictness.  
Failure mode: Callers may think they can tune strictness, but all runs are the same.  
Fix: Remove the variable or define `MAXIMUM` as the only supported value for this governance path.

## Template ↔ Checker Drift Summary

- SPEC says §A verified structural facts need real command/output; checker only enforces `FACT-RECEIPT` on `已確認` lines.
- SPEC says §G required when §RISK hits (a)/(d); checker does not parse §RISK and accepts `§G N/A`.
- TODO says every Task must have `驗證/邊界/不可做`; checker only requires those words somewhere in the file.
- RESULT says PASS requires receipts and NOT_RUN cannot coexist with DONE-like claims; checker does not enforce either.
- Coverage prose says traceability; script only checks ID string presence.

## Token Economy

Worth paying:
- The four V13 templates are short enough to keep always in the pipeline.
- The adversarial prompt's 10 failure classes are worth their tokens for medium/large tasks because they encode expensive prior incidents.
- §G value/NaN-mask hash language is worth keeping; it prevents aggregate-only false confidence.

Can reduce:
- Replace unconditional full reads of `.github/copilot-instructions.md`, `docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_GUIDE.md` in TODO generation with a short canonical constitution plus targeted domain reads.
- Avoid copying long constitutional bullets into every TODO; require references plus only task-specific constraints.
- For small inline tasks, keep the existing bypass path; do not force full SPEC/TODO/adversarial unless scope expands.

## 明確不建議改的地方

- Do not remove §A challenge/confirmation discipline; it directly targets repeated wrong-premise incidents.
- Do not remove §G value hash + NaN mask hash; aggregate-only golden is not enough.
- Do not remove "author model cannot self-review" and cross-family adversarial review for medium/large/high-risk tasks.
- Do not remove fake-green protections around test assertion diffs.
- Do not weaken real-kline / real-path requirements for Feature Factory data correctness.

## Overall Verdict

Verdict: **需修補後繼續使用，不需推翻 V13 設計**. The compact-template strategy is sound, but the gate/checker implementation must be tightened or the governance docs should explicitly downgrade their claims. The highest-value fixes are C1-C5 because they close concrete template↔machine drift where the current gate can pass artifacts that violate the written contract.

STATUS: DONE
