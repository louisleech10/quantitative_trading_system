# GAP-2a／2b TODO adversarial 審查 R11（TODO DRAFT R5 收斂確認輪；窄範圍）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 執行，但本輪為**收斂確認**：範圍限「R10 W1 一行寫回是否成立」＋「你上一輪（R10）判定是否維持」。findings 用 canonical ID `## <FAMILY>-R11-P<0-3>-<NN>`；0 finding 寫 sentinel `## <FAMILY>-R11-P3-00`（**預期三家 sentinel ⇒ TODO FROZEN**）。勿為湊數捏造 finding；若真有新 BLOCKING／MAJOR 仍必列。

## 審查標的
- **TODO**：`docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R5**；與 R4 之差＝Phase B4「測試＋Gate」小節改為與 §B「B4→B5」列同文逐字＋版本行）
- **SPEC（R7 FROZEN）**：`docs/GAP2_MARGINAL_IC_SPEC.md`＋延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-6；A1-5 決策行加一句 pointer 指向補正、內容未變）
- **R10 收斂檔**：`handoffs/reconcile/20260818-gap2-x-review-r10/synth.md`（W1／W2；三家戳記 stamp r11）；你 R10 的 review：`handoffs/20260818-gap2-todoadv-r10-<你的家族>.md`
- 收斂檔（皆三家戳記）：`handoffs/reconcile/20260818-gap2-x-review-r{1..9}/synth.md`

## 本 brief 前提（逐條標）
fact-verified: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS；`bash scripts/todo_spec_crosscheck.sh <SPEC> <TODO>` → SMOKE PASS（Claude 實跑 2026-08-18，DRAFT R5）
fact-verified: `grep -n 'mutation_probe_check.sh\`' docs/GAP2_MARGINAL_IC_TODO.md` → rc=1（W1 exact gate；**codex 請重跑**）
fact-verified: R10 synth 三家 RECONCILE-STAMP APPROVED（stamp r11，sha 72bf9378c846…）
assumed: `git diff HEAD~1 -- docs/GAP2_MARGINAL_IC_TODO.md` 只動兩處（版本行、Phase B4 小節）且 AMENDMENTS 只加 A1-5 一句 pointer，無其他漂移 ← 請實核 diff
assumed: R5 相對 R4 之改動不影響你 R10 之判定（composer／grok 可 Frozen 維持；codex 待修項已關）← 請明答
## 必答
1. W1 寫回成立？（Phase B4 小節與 §B L35 同文；exact grep rc=1）
2. 你 R10 的判定（可 Frozen／待修）在 R5 上是否維持／轉為可 Frozen？
3. `git diff` 是否只含宣稱之兩處＋A1-5 pointer 一句？有無夾帶。
4. 可以 Frozen 進 B1 實作嗎？BLOCKING 清單（無 → 明寫「可 Frozen」＋sentinel）。

## 不受理範圍
重開 R8／R9／R10 已收斂項；治理流程；前端樣式；ML 選型；GAP-3；重議使用者裁決。禁改碼、禁改 SPEC／TODO。收尾清 /tmp workdir（保留 claude-501）。
