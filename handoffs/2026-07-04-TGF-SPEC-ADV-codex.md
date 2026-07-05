# TEMPLATE_GATE_FIX_SPEC adversarial review — Codex

SPEC_FILE=docs/TEMPLATE_GATE_FIX_SPEC.md
TODO_FILE=N/A
PLAN_FILE=handoffs/2026-07-04-template-review-RECONCILE.md
REVIEW_FOCUS=完整審查

## Verdict：需修補後派工

SPEC 大方向忠實落實 reconcile：U1/U2/U3/CL-2/U9/U11/Q3/Q4/三方簽核下沉都有落點，且 `coverage_check` 對 manifest 全覆蓋通過。阻擋點不是漏大項，而是三個新繞過/不可執行面會讓防線修補後仍給過度安全感。

## Findings

### [BLOCKING] High — ID:(ADV-C1) §A FACT-RECEIPT 修法仍會漏掉 canonical「已驗證事實」子 bullet

證據：SPEC Task 2.1 把 W1 觸發定義為「觸發行條件從『含已確認』擴為『含已確認或已驗證』」（docs/TEMPLATE_GATE_FIX_SPEC.md:53），但現行 SPEC_TEMPLATE 的 canonical §A 是單行欄位「已驗證事實」後接內容（templates/SPEC_TEMPLATE.md:24）；本 SPEC 自己也用「已驗證事實」標題行，真正 fact 在下一層 bullet（docs/TEMPLATE_GATE_FIX_SPEC.md:11-19）。

VERIFY:
```bash
tmpdir=$(mktemp -d /tmp/tgf_adv_heading2.XXXXXX)
cat > "$tmpdir/spec_heading_verified_bypass.md" <<'EOF'
# Probe SPEC
## §RISK
- **命中高風險原則**：不命中 (a)/(d)。
## §A
- **已驗證事實 1 條**（附驗證方式）：
  - raw_data dtype 是 int64，DataFrame shape 已驗證。
- **待使用者確認**：待確認：無
## §C
- 約束：grep rc=0
## §G
- 行為 golden：exit == 0
## §P
### Phase 1
**Task 1.1**
- **驗證**：`grep x y; echo rc=0`
- **邊界**：空輸入；缺檔
- 不可做：不可放寬
## §V
- 測試：exit == 0
## §R
- revert commit
## §N
- 無
EOF
bash scripts/template_check.sh spec "$tmpdir/spec_heading_verified_bypass.md"; echo rc=$?
```
輸出：
```text
TEMPLATE PASS (spec): /tmp/tgf_adv_heading2.yO6xVQ/spec_heading_verified_bypass.md 含全部必填錨點，且無明顯空殼。
rc=0
```

會怎麼失敗：實作者照 Task 2.1 做「含已驗證的行」檢查，會檢查到標題行而非 fact bullet；只要 fact 寫在「已驗證事實」區塊下方，仍可無 FACT-RECEIPT PASS。

修法：Task 2.1 必須改成 §A state machine：進入「已驗證事實」小段後，該小段內含資料結構/命令/輸出詞的 bullet 均需同/鄰行 FACT-RECEIPT，直到下一個同級 §A 小段。Phase 1 fixture 必須新增 `spec_heading_verified_bypass.md`，修前 PASS、修後 FAIL。

RECHECK:
```bash
bash scripts/template_check.sh spec tests/gate_fixtures/spec_heading_verified_bypass.md; echo $?
```
預期修後 `rc=1`，且輸出點名缺 FACT-RECEIPT 的 fact bullet。

### [MAJOR] High — ID:(ADV-C2) §RISK↔§G token oracle 從 manifest 的 numeric/hash golden 被放寬成 `exit|==`

證據：manifest A-3 要求高風險 (a)/(d) 的 §G 含「atol/rtol/sha256 任一」（docs/TEMPLATE_GATE_FIX_MANIFEST.md:9）；SPEC Task 2.2 寫成 `atol|rtol|sha256|exit|==` 任一 token（docs/TEMPLATE_GATE_FIX_SPEC.md:60）。reconcile U2 的目標是防高風險逃 Golden，不是允許用 shell exit code 代替數值/ML golden。

VERIFY:
```bash
rg -n "atol\\|rtol\\|sha256\\|exit\\|==|atol/rtol/sha256|§RISK↔§G" \
  docs/TEMPLATE_GATE_FIX_SPEC.md docs/TEMPLATE_GATE_FIX_MANIFEST.md handoffs/2026-07-04-template-review-RECONCILE.md
```
輸出摘要：
```text
docs/TEMPLATE_GATE_FIX_SPEC.md:60:... §G 段含 `atol|rtol|sha256|exit|==` 任一 token ...
docs/TEMPLATE_GATE_FIX_MANIFEST.md:9:... 可證偽 token（atol/rtol/sha256 任一）...
handoffs/2026-07-04-template-review-RECONCILE.md:20:U2 §RISK↔§G 脫鉤...
```

會怎麼失敗：高風險數值/ML SPEC 可寫「§G：跑 pytest，exit == 0」，滿足 `exit|==`，但沒有 value hash、NaN mask、容差或 reference。這是 U2 的新變體。

修法：Task 2.2 與 fixture EXPECTED 對齊 manifest：高風險 (a)/(d) 至少要求 `atol|rtol|sha256|value hash|NaN mask` 等真正 golden token；`exit` 只能作為行為型非 (a)/(d) 任務的 §G token，不能滿足 (a)/(d) golden。

RECHECK:
```bash
rg -n "§G 段含 .*exit|§G 段含 .*==" docs/TEMPLATE_GATE_FIX_SPEC.md
```
預期無輸出，或明確寫「exit/== 不可滿足 (a)/(d) §G」。

### [MAJOR] High — ID:(ADV-C3) gate/reconcile 閉合規則說「同目錄或指定」，但沒有指定 reconcile 的 CLI/API

證據：Task 6.1 要求 gate 檢查「對應 reconcile 檔（--adversarial 同目錄或指定）」含每個 `ADV-<n>` 的處置行（docs/TEMPLATE_GATE_FIX_SPEC.md:120）。現行 `gate.sh` 參數解析只有 `--adversarial`、`--spec`、`--todo` 等，沒有 `--reconcile` 或等價欄位（scripts/gate.sh:134-145）。同時現行 high-risk implementation dispatch 已把 `--adversarial` 當 reconcile-stamp 輸入使用（scripts/gate.sh:219-224），語義已混在同一參數。

VERIFY:
```bash
rg -n -- "--adversarial|--reconcile|reconcile檔|對應 reconcile|ADV-<n>" \
  docs/TEMPLATE_GATE_FIX_SPEC.md scripts/gate.sh templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
```
輸出摘要：
```text
docs/TEMPLATE_GATE_FIX_SPEC.md:120:... 對應 reconcile 檔（--adversarial 同目錄或指定）...
scripts/gate.sh:141:    --adversarial) adversarial="${2:-}"; shift 2 ;;
scripts/gate.sh:219-224: --adversarial 指向的 reconcile 須獲委員戳記
```
`--reconcile` 無匹配。

會怎麼失敗：實作者只能猜「同目錄」命名規則，或把 adversarial/reconcile 都塞進 `--adversarial`。多委員多檔時 gate 無法知道哪個 reconcile 對應哪個 findings 檔；測試也無法穩定覆蓋「有 BLOCKING 無處置」。

修法：SPEC 必須明確新增 `gate.sh dispatch --reconcile <path>` 或定死 deterministic path derivation，並更新 Task 6.1 驗證命令。若保留單參數，需明確區分「adversarial findings 檔」與「reconcile stamped 檔」的階段與輸入。

RECHECK:
```bash
rg -n -- "--reconcile|reconcile_path|reconcile=\"\"" scripts/gate.sh docs/TEMPLATE_GATE_FIX_SPEC.md
```
預期可看到明確 CLI/變數與對應 fixture 測試。

### [MINOR] Medium — ID:(ADV-C4) adversarial ID 格式未忠實落到本輪 Q1/補充要求的可歸屬格式

證據：使用者本輪要求每條 finding 附 `ID:(ADV-C<n>)`；SPEC Task 4.1/6.1 則定為通用 `ADV-<n>`（docs/TEMPLATE_GATE_FIX_SPEC.md:97,120）。現行 gate 另以 filename 判斷 `ADV-CODEX`/`ADV-COMPOSER`（scripts/gate.sh:167-168），但 finding ID 本身不帶 reviewer family。

VERIFY:
```bash
rg -n -- "ADV-<n>|ADV-C|ADV-CODEX|ADV-COMPOSER" docs/TEMPLATE_GATE_FIX_SPEC.md scripts/gate.sh
```
輸出摘要：
```text
docs/TEMPLATE_GATE_FIX_SPEC.md:97:ID:`ADV-<n>`
docs/TEMPLATE_GATE_FIX_SPEC.md:120:每個 `ADV-<n>`
scripts/gate.sh:167-168:*ADV-CODEX* / *ADV-COMPOSER*
```

會怎麼失敗：reconcile 對映表在雙家族 review 下可能出現 `ADV-1`/`ADV-1` collision，或需要靠檔名才能歸屬。這不一定阻塞實作，但會削弱 U9「可對號銷帳」的機械性。

修法：prompt 輸出格式定為 family-scoped，例如 Codex `ADV-C<n>`、Composer `ADV-M<n>`，或完整 `ADV-CODEX-<n>` / `ADV-COMPOSER-<n>`；gate/reconcile regex 同步。

RECHECK:
```bash
rg -n -- "ADV-C<n>|ADV-CODEX-<n>|ADV-COMPOSER-<n>" templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md docs/TEMPLATE_GATE_FIX_SPEC.md
```

## 10 類掃描摘要

1. 矛盾/互斥：ADV-C2、ADV-C3。
2. 漏項/端到端：ADV-C1、ADV-C3。
3. 不可測驗收：ADV-C1、ADV-C2。
4. 可疑 quant 假設：ADV-C2；不得把 high-risk numeric/ML golden 退化成 exit code。
5. 過度工程：無。
6. OOM/並行：無。
7. Cache 正確性：無。
8. API/型別/相容：ADV-C3（CLI contract）。
9. 測試品質：ADV-C1、ADV-C2。
10. Agent 可執行性：ADV-C3、ADV-C4。

## 被當成事實的未驗證假設（§0）

- 「治理文件殘留舊錨點共 6 處」已重跑驗證，成立。
  VERIFY: `grep -n "§1.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md` → `CLAUDE.md:41`, `scripts/gate.sh:9,254`, `docs/MULTI_AGENT_ORCHESTRATION.md:69,101,212,308`。
- 「待使用者確認：本任務無」現行 regex 會誤擋，已重跑驗證，成立。
  VERIFY: `printf ...; grep -qE ...` → `regex NO MATCH(會被誤擋)`。
- 「三個繞過探針 PASS、facts-unresolved FAIL」已用 /tmp 同構 fixture 重跑，成立。
  VERIFY: `template_check.sh` 對 `spec_verified_bypass/spec_highrisk_no_g/todo_bad/spec_pending_unresolved` → `rc=0/0/0/1`。
- 「copilot/TEST_DESIGN_CHARTER/ARCHITECTURE/DEVELOPMENT_GUIDE 存在，執行端合約為 AGENTS.md/.cursorrules」已重跑驗證，成立。
  VERIFY: `ls ...` → 4 檔存在；`rg "其他 agent|Codex 讀|Cursor 讀" CLAUDE.md` → `Codex 讀 AGENTS.md，Cursor 讀 .cursorrules`。

## 附加機檢

```text
bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md; echo rc=$?
=> TEMPLATE PASS ... rc=0

bash scripts/coverage_check.sh docs/TEMPLATE_GATE_FIX_MANIFEST.md docs/TEMPLATE_GATE_FIX_SPEC.md; echo rc=$?
=> COVERAGE PASS ... 全部 28 項。rc=0
```

STATUS: DONE
