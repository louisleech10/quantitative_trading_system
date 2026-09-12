# DOCROT 文檔問題偵察諮詢 R1 — codex
brief-kind: consult; task-id: 20260912-DOCROT-X-CONSULT-R1; findings-round: R1
## §0 反前提與量測
fact-verified: `git log --follow -- docs/SPLITUNIFY_SPEC.D-002.md` 顯示 14 commits；review synth headings 可重算 15/11/15/8/11/16/15/14/21/13/12/13，合計 164。
assumed: 這些計數只能證明 review churn，不能證明使用者「7 成時間」的時間分母；否證：repo 無可靠 wall-clock／人時分母，故本報告不宣稱 7 成。
量測(可重跑): `git log --follow --format= --numstat -- docs/SPLITUNIFY_SPEC.D-002.md | awk ...` → additions=577 deletions=226 churn=803 net=351；`awk ... 白話說明/*.md` → direct_white_docs=22，unique_repeated_lines=60，repeated_line_occurrences=164；`for f in handoffs/reconcile/.../r{1..12}/synth.md; do rg -c '^## (CODEX|COMPOSER|GROK)-R[0-9]+-P[0-3]-[0-9]{2}$' "$f"; done` → 15/11/15/8/11/16/15/14/21/13/12/13。
範圍判定: HANDOFF=有（同一狀態多次敘述且 47 行）；SPLITUNIFY_TODO=有（與 D-002 對同一 residual 給相反狀態）；reconcile synth=有症狀但附錄保留是審計需求；白話=有（22 份直接檔、60 條長行跨檔重複）；VERDICTGATE SPEC/TODO=有（自身也內嵌 v2–v9 歷史，且 E-6 明列語意等價未解）。
## CODEX-R1-P1-01
**斷言**: 同一 lifecycle state 被多份可操作文檔各自複寫，能在同一工作區同時呈現相反狀態，讀者因此沒有可機械選擇的權威。
**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:323-324` 寫 `SU-RESID-2` 已落實，`docs/SPLITUNIFY_TODO.md:470` 仍是 `needs-research`＋selected-only；`find 白話說明 -maxdepth 1 -name '*.md' | wc -l` → 22。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24; docs/SPLITUNIFY_TODO.md#56d2bb3ff222; 白話說明/SPLITUNIFY施工進度.md#3910c919a12b
[MAJOR] 信心度=High；這不是翻譯本身的問題，而是狀態值沒有 registry/phase tag，跨檔讀取會把「待戳記的過渡差異」當成永久矛盾。修法：建立一個 machine-readable lifecycle/fact registry，SPEC/TODO/HANDOFF/白話/synth 只引用 key＋anchor；checker 對同 key 的值與 phase 做 fail-closed equality。驗證：以 `SU-RESID-2`、版本、round、register_count 回放，矛盾 key 數=0 且 transition 只在 registry 定義；不需自然語言推理，沿用現有 audit/JSON registry 模式可行。
## CODEX-R1-P1-02
**斷言**: 現行 review input 把 superseded revision prose 與 normative text 放在同一文件，會讓下一輪重新閱讀已作廢主張並把上一輪修法再審一次。
**碼證**: `D-002` 有 `HISTORY-BEGIN/END` 內嵌 13 條完整修訂敘事（`:331-347`），`VERDICTGATE_SPEC.md:4-11` 直接內嵌 v2–v9；topic scan：`producer`=12/12、`metadata`=6/12、`mutation`=12/12 synth rounds；R11=12、R12=13 條均針對前版修法。**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24; docs/VERDICTGATE_SPEC.md#d723f42d71945; handoffs/reconcile/20260911-splitunify-b9-review-r11/synth.md#b98eb1d9665c; handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989
[MAJOR] 信心度=High；history marker 只是排版，不是 review parser 的輸入邊界，且 VERDICTGATE header 沒有同等隔離；結果是 14 次 D-002 commit／803 churn 仍換來不下降的 round load。修法：把歷史搬成 append-only audit/決策檔，normative 文件只留 current contract；review command 只餵 current block＋本輪 diff，finding 以 fact-key/anchor 指向現行段落。驗證：回放 R1–R12，任何 finding 的 source anchor 不得落在 history；同型「上一版修法缺陷」不再由全文重讀產生，歷史仍可追溯。
## CODEX-R1-P1-03
**斷言**: 現有 doc gates 能對格式與 token 存在給綠燈，但不能檢出跨文件語意漂移，且 Bash/生成器寫檔不會觸發 Edit|Write 的文件 hook。
**碼證**: `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md`→rc=0；`bash scripts/spec_xref_check.sh --synth ...r12/synth.md docs/SPLITUNIFY_SPEC.D-002.md`→PASS/rc=0；`obligation_block_check`、`template_check dext`→rc=0；`scripts/spec_xref_check.sh:18` 明載「只驗存在，不驗語意等價」，`.claude/settings.json:189-193` matcher 為 `Edit|Write`。**來源摘要**: scripts/spec_xref_check.sh#7073db9808bd6; scripts/completeness_check.sh#c76692e041da; scripts/doc_format_precheck.sh#e39ce0d21db0; .claude/settings.json#77cb54336328
[MAJOR] 信心度=High；所以「結構全綠」不能推出同一 fact 已同步，Bash 重導/外部生成還可繞過產出端早期檢查。修法：在所有 doc producers 的產出/commit/dispatch 邊界掛 registry equality checker（包含 Bash 生成檔），保留 xref 作 token 檢查；測試必含 A→A' drift、Bash-created file、transition state 三個反例。可行性：checker 只比結構化 fact-key，不做開放式 NLP，與現有 shell/JSON gates 相容。
必查類別: 1矛盾=有(P1-01)；2端到端=有(P1-01)；3不可測=有(P1-03)；4 quant=無新增；5過度工程=無新增；6 OOM=不適用；7 cache=不適用；8 API=無新增；9測試品質=有(P1-03)；10 Agent=有(P1-02)；11短命工=有(P1-02)。
§2/§3: D-002 具 RISK/A/C/G/P/V/R/N 且高風險有 Golden；既有結構閘均可跑過，但沒有語意 equality；不主張弱化任何資料品質或量化 gate。
是否值得解: 值得解「唯一 fact registry＋歷史/現行輸入隔離＋產出端 equality gate」這個窄核心；不值得為所有白話文造 NLP 蘊涵器或整套替換文檔體系。成效判準：下一輪同型跨檔狀態/歷史誤讀 finding=0，且 drift fixture 必紅。
ASSUMPTIONS_VERIFIED: 上述 git/rg/awk/既有 gate 命令均已實跑；主委版本未讀未引用。 TESTS_RUN: doc_format=0; synth_xref=0; obligation=0; template=dext=0; completeness(single,family=codex)=0。
FAILURES_SEEN: 首次合併唯讀命令被 PreToolUse debt gate 擋，拆成最小唯讀命令後完成；未改碼。 SCOPE_CHANGES: 僅新增指定產出檔，root HANDOFF、data_cache 與其他文檔未改。
NUMERIC_OR_SCHEMA_IMPACT: 無；僅量測既有文件/歷史，未改輸出 schema。 OUTPUT: handoffs/20260912-docrot-x-consult-r1-codex.md。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03
CLOSED:
STATUS: DONE
