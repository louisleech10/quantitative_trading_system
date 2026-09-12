# Reconcile — 20260912-docrot-x-consult-r1

**來源** 20260912-docrot-x-consult-r1-codex.md, 20260912-docrot-x-consult-r1-composer.md, 20260912-docrot-x-consult-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

🔴 **主委自產版之處置**：主委依自產一版之規約另寫 `handoffs/20260912-docrot-x-consult-r1-claude.md`（兩條），
**刻意不供三家閱讀**以免錨定，亦**不納入本輪 roster**（派工名單為三家，roster 須與之相等）。
其內容已被三家推翻，逐條記於 D1 與 D4 之處置欄，供追溯。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **D1 主因：同一決定手寫進多個無索引落點（三家獨立撞題）**——「同一lifecyclestate被多份可」「`docs/SPLITUNIFY_SPE」「D-002活文把同一決策手寫進多個落點（」 | P0 | CODEX-R1-P1-01, COMPOSER-R1-P0-01, GROK-R1-P0-01 | 採納（三家各自量到同一結構：一個決定在活文複述五處以上且無索引。碼證彼此獨立且一致——Task 9.2b 活文 19 次、metadata.split_unify 11 處、validate_split_pair_integrity 5 處、數字字面 27 處。🔴 **此群推翻主委自產版之排序**：主委把「正文混入歷史」列為主因，三家一致判其為次因，主因是多落點複述） |
| **D2 次因：修訂考古寫進活義務（codex＋主委自產版同向）**——「現行reviewinput把supers」 | P1 | CODEX-R1-P1-02 | 採納（活文 109 個版本標記、沿革段占 25%；委員重讀時撞到已取代敘述而誤把歷史當現行。處置＝活文只留現行契約，版本標記與作廢敘述一律移出。codex 另主張審查時只餵當前段落＋本輪 diff，一併採納。主委自產版之診斷落在本群，方向相同但排序錯誤） |
| **D3 三閘同時 rc=0 之狀態不足以推出規格無語意互斥（三家獨立撞題）**——「現有docgates能對格式與token」「`obligation_block_ch」「現行產出端閘（`spec_xref_ch」 | P1 | CODEX-R1-P1-03, COMPOSER-R1-P1-02, GROK-R1-P1-01 | 採納（三閘同時 rc=0 之狀態下，規格仍可能存在 Task 與驗收段互斥；xref 腳本檔頭自白「只驗存在，不驗語意等價」。🔴 codex 另揭一項另兩家未提：Bash 與生成器寫檔**不觸發** Edit 與 Write 的文件 hook ⇒ 產出端覆蓋有洞。**處置**：判定採計數式、強制掛既有檢查鏈（見下方路線裁定）；Bash 寫檔繞過一項具名登記為殘留。REF:handoffs/20260912-docrot-x-consult-r1-codex.md） |
| **D4 輪數診斷與停輪判準（兩家；含對主委陳述之駁回）**——「b9十二輪審查finding總數**16」「使用者「文檔問題浪費大部分輪數」對**R」 | P1 | COMPOSER-R1-P1-01, GROK-R1-P1-02 | 部分採納（**採納**：finding 曲線無下降、末輪全打上一版修法、停輪判準應寫死為機械條款。🔴 **駁回主委原陳述之外推**：grok 指出「七成浪費」對 R8 之後成立，但外推到全部 164 條會抹掉 R1 至 R6 的真架構收益（末五輪 73/164 約 45%）。主委自產版亦自承該判斷未驗證，本群以 grok 之限縮為準） |
| **D5 狀態複寫跨檔（兩家撞題）**——「施工狀態（v13、十二輪、164條、29」「`白話說明/`對GAP-3存在**8**」「同病在`白話說明/`與`HANDOFF.」 | P2 | COMPOSER-R1-P2-01, COMPOSER-R1-P2-02, GROK-R1-P1-03 | 採納（同一狀態寫在 30 份檔；白話說明 22 份中 GAP-3 佔 8 份共 5404 行。處置＝狀態只寫單一權威檔、其餘改指標。🔴 **合併與否屬使用者看板偏好，不由主委決定**——已在交接文件具名為待裁定） |
| **D6 收斂檔不屬病灶（範圍限縮）＋收斂無機械背書**——「`handoffs/reconcile/」「十二份b9synth的`RECONCIL」 | P2 | GROK-R1-P2-01, COMPOSER-R1-P3-01 | 採納（收斂檔為輪次歸檔，逐字保留是審計契約，清理它無效且傷回溯 ⇒ 範圍排除，只收縮活規格與交接文件與白話。另十二輪戳記數為 0 與「十二輪收斂」敘述並存會製造假安全感 ⇒ 敘述改為「功能停輪」並明確區分於「已核可」；是否補派一輪只蓋章的輪次列為待裁定） |

**🔴 三家路線分歧（具名記載，主委裁定；🔴 本裁定經使用者當面指正後改寫，原裁定作廢）**：composer 之 P0 主張新建決定落點 YAML 與新 checker 腳本；grok **明確反對新建任何工具**（引主委自定之不再擴建治理工具）；codex 介於兩者之間（主張 registry 但未強制新腳本）。

🔴 **原裁定（採 grok 較窄版、不建任何強制機制）已作廢**，作廢理由逐條：
①grok 之 F1 至 F3 雖標「可機械驗證」，但**無任何機制強制執行該驗證**——跑不跑取決於主委是否記得，與主委既有之自證七條同型，而自證七條在 R12 仍中六條 ⇒ 屬**紀律型**，使用者 2026-09-12 逐字指正「靠紀律你絕對失敗」。
②主委原駁回理由「D3 已證明既有語意閘不可行」為**誤用**：D3 指的是現有 xref 閘只驗存在不驗語意；composer 之方案為**結構閘**（比對 pattern 命中數），非語意判斷，技術上可行。
③主委原駁回理由「不再擴建治理工具」係**主委自定、非使用者裁定**，且主委已於交接文件自標為未驗證假設 ⇒ 不得用以駁回唯一具強制力之方案。

**新裁定＝兩家各取一半**：**判定**採 grok 之 F1 至 F3（純計數，零維護，**不需** composer 之 YAML registry）——活文版本標記歸零、數字字面恰一處、單一決定活文計數降至三以下；**強制**採 composer 之主張，但掛在**既有** `PostToolUse` 之文件檢查鏈（現已有八支），不新開 epic、不建 registry、不新增 brief-kind。三條判定皆為可數量之 grep，違反即寫檔當下報。

**成效判定（下一張中大票驗收）**：若下一票仍出現「改了一處漏另一處」型 finding 且占比未下降，則本裁定失敗，屆時重新評估 composer 之機械方案。

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R1-P0-01

**斷言**: `docs/SPLITUNIFY_SPEC.D-002.md` 將單一決定複製到 ≥5 個無交叉引用索引的區段，是十二輪「修了 A 漏 B」的**結構主因**，非單純紀律問題。

**碼證**: `rg -n 'validate_split_pair_integrity' docs/SPLITUNIFY_SPEC.D-002.md` → **5** 命中（Task 9.2b、§V、mutation 等）；`rg -n 'metadata\.split_unify' docs/SPLITUNIFY_SPEC.D-002.md` → **11** 命中；R12 synth O3 逐字：Task「**不在 derive 內呼叫**」vs §V「**derive 路徑確實呼叫**」。RECHECK: 對讀 `handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md` 群集 O1/O3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#9de6da3ca5b8;handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md

[BLOCKING] 信心度=High。每次修訂必漏一處 ⇒ 輪數膨脹、實作延後。**修法**：必答 4 之決定落點 YAML＋`decision_coverage_check.sh`；SPEC 內非 canonical 處改為 `見 DEC-<id>`。**可行性**：YAML＋rg 計數為現有工具可實作；試跑邏輯＝對 `validate_split_pair_integrity` 五處抽取動詞片語，不一致即 exit 1。

---

## COMPOSER-R1-P1-01

**斷言**: b9 十二輪審查 finding 總數 **164**、末輪 **13**，曲線**無下降**，邊際主要消耗在修文檔一致性而非新架構缺陷。

**碼證**: 各輪 synth 計數 15/11/15/8/11/16/15/14/21/13/12/13；R11 synth L20「本輪 12 條**首度全為我上一版修法本身的缺陷**」；R12 synth L19「**無一為新面向**」。`git log --oneline -- docs/SPLITUNIFY_SPEC.D-002.md` 最近三條 commit message 含「打我上一版」「兩個條數同時活在文件裡」。RECHECK: `for r in $(seq 1 12); do rg -c '## (CODEX|COMPOSER|GROK)-R'"$r"'-P' handoffs/reconcile/20260911-splitunify-b9-review-r"$r"/synth.md; done`

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md;docs/SPLITUNIFY_SPEC.D-002.md#9de6da3ca5b8

[MAJOR] 信心度=High。使用者「7 成浪費」以輪數分母**可量化支持**。**修法**：採必答 6 停輪判準寫入 `docs/ROADMAP.md` 機械條款；連兩輪 doc-sync 占比 ≥80% 自動停審。**可行性**：`awk` 掃 synth 群集表關鍵字占比即可腳本化。

---

## COMPOSER-R1-P1-02

**斷言**: `obligation_block_check`、`doc_format_precheck`、`spec_xref_check --synth` 三閘全 **rc=0** 時，SPEC 仍可有 Task↔§V **互斥**——閘驗格式與 xref token，不驗跨區段語意。

**碼證**: `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`bash scripts/spec_xref_check.sh --synth handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md docs/SPLITUNIFY_SPEC.D-002.md` → rc=0。但 R12 O3 證實 derive／validator 三處互斥在修訂前存在。RECHECK: 重跑三命令＋讀 R12 synth O3。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#9de6da3ca5b8;scripts/spec_xref_check.sh

[MAJOR] 信心度=High。假綠閘放大「又浪費一輪才發現」。**修法**：必答 4 之 `spec_section_coupling_check.sh`（同 commit Task+§V+mutation 聯動）。**可行性**：僅比對 git diff 路徑與行號集合，無需 NLP。

---

## COMPOSER-R1-P2-01

**斷言**: 施工狀態（v13、十二輪、164 條、29 register）同時寫在 **≥30** 份非 handoff 文檔，任一處漏改即製造「前幾輪修過又重修」體感。

**碼證**: `rg -l 'v13|十二輪|164 條|29 條' docs/ HANDOFF.md 白話說明/` → **30** 檔；`白話說明/SPLITUNIFY施工進度.md` L50/L74 自記 164／29，與 SPEC register 表標題雙源。RECHECK: 重跑 rg；改 HANDOFF 一處數字後 grep 白話是否仍舊值。

**來源摘要**: HANDOFF.md#390c9d87e933;白話說明/SPLITUNIFY施工進度.md

[MINOR] 信心度=High。**修法**：狀態只寫 HANDOFF anchor；白話只留指標。**成效**：`rg` 白話不含 `見 HANDOFF` 的數字句 → 0。

---

## COMPOSER-R1-P2-02

**斷言**: `白話說明/` 對 GAP-3 存在 **8** 份平行看板，放大同一 epic 的多處同步成本。

**碼證**: `ls 白話說明/GAP-3*.md | wc -l` → **8**；`ls 白話說明/*.md | wc -l` → **22**。HANDOFF L34 已具名六份重疊但未合併。RECHECK: `ls 白話說明/GAP-3*.md`

**來源摘要**: HANDOFF.md#390c9d87e933

[MINOR] 信心度=High。**修法**：使用者選定唯一看板檔，其餘改 stub 指標；`scripts/whitelist_single_board.sh` 拒絕向非白名單 GAP-3 檔新增行。**紀律成分**：白名單需使用者裁定（HANDOFF 已記）。

---

## COMPOSER-R1-P3-01

**斷言**: 十二份 b9 synth 的 `RECONCILE-STAMP APPROVED` 計數為 **0**，與「十二輪收斂」敘述並存，使「已修完」無機械 stamp 可稽核。

**碼證**: `grep -c 'RECONCILE-STAMP.*APPROVED' handoffs/reconcile/20260911-splitunify-b9-review-r*/synth.md` → 每檔 0、合計 0。RECHECK: 同上 grep。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md

[MINOR] 信心度=Medium。不阻實作但增加「到底收沒收斂」摩擦。**修法**：停輪後單次 `reconcile_build --mode review`＋stamp；或敘述改「功能停輪」≠「stamp APPROVED」。

---

ASSUMPTIONS_VERIFIED: brief §0 三條 fact-verified 均已重跑；commit 分類、finding 計數、synth 群集主題、閘 rc、多落點 rg 均附命令  
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r1-composer.md --family composer`（交件前自檢）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀偵察）  
NUMERIC_OR_SCHEMA_IMPACT: none

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R1-P0-01,COMPOSER-R1-P1-01,COMPOSER-R1-P1-02  
CLOSED:  
STATUS: DONE
## GROK-R1-P0-01

**斷言**: D-002 活文把同一決策手寫進多個落點（例：`Task 9.2b` 在沿革前出現 19 次），使「改一處漏一處」成為結構產物而非偶發疏忽；此結構直接驅動 R11–R12「全打上一版修法」閉環。

**碼證**: `MEASURE-B` → `Task_9.2b_live=19`、`live_vN=109`；R12 synth 停輪句：「十三條無一為新面向…剩餘七群全是字面同步」。RECHECK：重跑 `MEASURE-B`；`grep -n '停輪判斷' handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#64d64dfe6e24；handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[BLOCKING] 信心度=High。會怎麼失敗：實作者／委員各自抓住不同落點 → 互斥指示（R12 O3 形態）或假完成。**修法**：F1+F3（活文去考古、決策單述）；可行性＝純刪併與搬移，不需新閘；成效指標＝`Task 9.2b` 活文計數 ≤3 且 `live_vN=0`。

---

## GROK-R1-P1-01

**斷言**: 現行產出端閘（`spec_xref_check`）明確不驗語意等價，因此「閘全綠」不能否定多落點漂移；把綠閘當成文檔健康信號會誤判。

**碼證**: `scripts/spec_xref_check.sh` 檔頭：「誠實邊界：只驗『存在』，不驗語意等價（synth 寫 A、SPEC 寫 A' 抓不到）」。RECHECK：`sed -n '1,25p' scripts/spec_xref_check.sh | grep -n '語意'`。

**來源摘要**: scripts/spec_xref_check.sh#7073db9808bd

[MAJOR] 信心度=High。會怎麼失敗：主委以 xref／obligation／format 全綠結束修訂，委員下一輪仍用語義對讀打穿。**修法**：不新開閘；改以 F1–F2 減少需要語意對齊的表面積。若強行加「語意 xref」→ 違反「不再擴建治理工具」，本家標為**不採**。

---

## GROK-R1-P1-02

**斷言**: 使用者「文檔問題浪費大部分輪數」對 **R8 之後**成立，且 R11–R12 為極端型；但把「7 成」外推到 **全部 164 條 finding／整個 epic** 會抹掉 R1–R6 的真架構收益。

**碼證**: finding 序列 15/11/15/8/11/16/15/14/21/13/12/13（無單調下降）；R1 synth 含同側／mutation 覆蓋等架構群；R11／R12 停輪句自承「全為上一版修法／字面同步」。粗代理：末 5 輪（R8–R12）finding=14+21+13+12+13=**73／164≈45%** 輪次份額，若加計同日 14 次修訂與派工開銷，wall-clock 體感可逼近使用者所說；但 **非**「七成 finding 無價值」。RECHECK：重跑 `MEASURE-A`；對讀 r1 與 r12 synth 群集表。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md#849e2869746a；handoffs/reconcile/20260911-splitunify-b9-review-r11/synth.md#b98eb1d9665c；handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MAJOR] 信心度=High。會怎麼失敗：若修法目標設成「消滅審查」，會連早期真缺陷一起關掉。**修法**：F4 停輪判準（已在 R12 觸發）寫進編排慣例；保留早期架構審查，切斷晚期字面閉環。

---

## GROK-R1-P1-03

**斷言**: 同病在 `白話說明/` 與 `HANDOFF.md` 以「進度複寫」形態存在；GAP-3 八檔 5404 行平行敘事，使「現況數字」有多個可漂移副本。

**碼證**: `wc -l 白話說明/GAP-3*.md` → 8 檔／5404 行；`grep -l '29 條' HANDOFF.md docs/SPLITUNIFY_SPEC.D-002.md 白話說明/*.md` 多檔命中。RECHECK：同上命令。

**來源摘要**: 白話說明/GAP-3施工進度.md#8209ea221c00；HANDOFF.md#101a5e0c449b

[MAJOR] 信心度=High。會怎麼失敗：SPEC 改了條數，白話／HANDOFF 仍引用舊數 → 下一輪審查或人類讀板被舊數錨定。**修法**：進度類白話只留一份權威、其餘改指標（合併與否交使用者）；HANDOFF 對條數／輪次只留 `見 SPEC:(5.6)`。成效：`grep -l '29 條' …` 命中集縮到單一權威檔。

---

## GROK-R1-P2-01

**斷言**: `handoffs/reconcile/*/synth.md` 不應被當成與 SPEC 同類的「活文病灶」；它們是輪次歸檔。把清理歷史 synth 當修法會無效且傷審計。

**碼證**: 十二份 synth 皆含「附錄：findings 逐字保留（byte-faithful）」契約；刪改會破壞 completeness／attribution 回溯。RECHECK：`grep -n 'byte-faithful' handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md`。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MINOR] 信心度=High。修法：範圍上排除歷史 synth；只收縮活 SPEC／HANDOFF／白話。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P0-01,GROK-R1-P1-01,GROK-R1-P1-02,GROK-R1-P1-03
CLOSED:
STATUS: DONE
