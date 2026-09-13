# DOCROT X-REVIEW R1 — grok

task-id: 20260912-DOCROT-X-REVIEW-R1  
family: grok  
findings-round: R1  
brief: handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md  
note: 唯讀審已 commit 實作（`44bbd8d3..HEAD`）；禁改碼。synth／HANDOFF 為診斷輸入，非 gating。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 證據 |
|---|---|---|---|
| 本輪實作 commit 範圍 `44bbd8d3..HEAD` 共 8 筆 | fact-verified | **成立** | `git log --oneline 44bbd8d3..HEAD` → 8 |
| 兩支 DOCROT 測試 15 passed | fact-verified | **成立** | `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_f2_total_items_count.py -q` → 15 passed |
| docs 200；觸發名 132／不命中 68 | fact-verified | **成立** | 本輪重數 `docs/*.md`＝200；名含 SPEC\|TODO\|PLAN\|RECON＝132 |
| 「併進既有 hook ⇒ 一般寫檔零成本」 | assumed | **部分不成立** | 非觸發路徑確不跑 `--dupes`；觸發路徑本輪測得 `--dupes` median≈34.7ms、hook e2e≈315ms（事前未測）→ P2-01 |
| 「沿革段略過不會漏真缺陷」 | assumed | **不成立（結構）** | `dupes()` 在首個 `HISTORY-BEGIN` **break**；HISTORY 後仍有活文時雙落點沉默（Case A 實跑 stderr 空）→ P1-01 |
| 「F1 只做 D-002 足以在下一張中大票驗成效」 | assumed | **不成立** | 下一票若非 D-002 系列，本輪未收縮之 SPEC（如 GAP3 仍 `共 8 條`×2）測不到 F1 成效 → P1-03 |
| 「骨架佔位對手寫 brief 零誤擋」 | assumed | **語料成立／洞仍在** | 本輪 replay：652 份 `*BRIEF*.md` 封閉字面命中＝**0**；但腳本自白擋不住手寫「整份檔」，且 E3 要的 completeness 歷史 anchor 拒收仍為 0 命中 → P0-02／P2-02 |

## 被當成事實的未驗證假設（§0）

- 「落地三家共同結論」涵蓋本輪五項機制細節 → **assumption 當 fact**；R2 原文無佔位字面／`--dupes`／HISTORY break／併 hook／單檔 F1（P0-01）。
- 「E3 已完成」→ **部分 fact**：範本＋`new_brief` 輸入邊界有改；**completeness 拒收歷史 anchor**（E3／E8 Phase A 逐字）`grep` 於 `scripts/completeness_check.sh` 命中數＝**0**（P0-02）。
- 「第一期只 warn」仍足以約束主因 D1 → **assumption**；主委已自證警告擋不住自己（P1-02）。

---

## 必答總覽（1–6）

### 1. 自創五項是否「非任一家原文之折衷」？跳過 consult 是否違程序？哪幾項應推翻／改寫？

| # | 機制 | 是否非原文折衷 | 與 R2 關係 | 處置建議 |
|---|---|---|---|---|
| 1 | 骨架佔位字面硬擋 | **是**（機制自創） | 目標對齊 E3；E3／E8A 指定的是**派工契約＋completeness 拒歷史 anchor**，不是封閉佔位集 | **改寫**：保留佔位作輔助；補 completeness anchor 拒收；開 consult 核機制 |
| 2 | `spec_count_audit --dupes` | **是**（形態擴張） | 窄 F2＝只數「共 N 條」入 `--list`／`--check`；多行重複偵測無委員文字 | **改寫或 consult**：可留作觀測，不得宣稱＝窄 F2 本體 |
| 3 | `dupes()` 遇 `HISTORY-BEGIN` 即 break | **是**（純自訂） | 無委員文字；Case A 證偽「略過無害」 | **推翻 break、改寫為 BEGIN–END 區間跳過** |
| 4 | 警告層併入 `spec_xref_hook` | **部分是** | E2 要三層；E6 反对第 9 支全域 hook——「不新增 settings 條目」有同向理由，但「併入哪一支」是主委成本拍板 | **consult 追認**或改掛 `narrow_check_router` 一列 |
| 5 | F1 只收縮 D-002 即「到收斂點」 | **是**（範圍單方收窄） | 執行優先序第 2 項未限單檔 | **推翻「DOCROT F1 已收斂」表述**；改標「D-002 單檔試點」 |

**程序**：R2 程序修正（synth L31，主委已接受）＝凡非任一家原文之折衷須自動開 consult。上表 1–5 皆未開 ⇒ **構成違反**。不得以「方向大致對」事後豁免。

### 2. 對主因 D1 的實際覆蓋率（可證偽）

定義 D1＝同一決定／同一計數字面手寫進多個無索引活文落點。

| 路徑 | 對 D1 作用 | 實測 |
|---|---|---|
| `brief_conformance` 佔位硬擋 | **不針對 D1**（只逼骨架填 current block／diff） | 主委直接 `Edit` docs ⇒ 完全繞過 |
| `spec_xref_hook`／`gov_check` 之 `--dupes` | 能**看見**多落點 | 一律 rc=0（warn-only）；`>/dev/null \|\| true` 不進 `_docbad` |
| 派工以外之 Bash／生成器寫檔 | PostToolUse 不觸發（既有洞） | E2 已採納之事實 |

**硬擋覆蓋率（寫入當下能以 rc≠0 擋住 D1）＝0%。**  
觀測覆蓋：觸發名集合內檔案在 Edit／`gov_check` 改動掃描時可得 stderr 警告。反例：`docs/GAP3_EVENT_UX_SPEC.md` 本輪 `--dupes` 仍報 `共 8 條 @ 117,3591` 與 `五維度` 19 處——警告在、無人被擋。

### 3. 「第一期只 warn」是否仍成立？最小擋門形態？

**對主委自身：不成立。** 本輪 brief 已載「警告擋不住自己」；warn-only 對該 actor 的約束力＝0。  
**對閾值未校準的誤擋風險：遷移序理由仍部分成立**——但不得再把「只 warn」說成已治理 D1。

**最小可行擋門（不新 epic、不新腳本檔）**：在既有 `scripts/gov_check.sh` 段 1b 迴圈，對**本次改動的 docs** 呼叫既有 `spec_count_audit.py --dupes`，若活文區（建議：跳過 `HISTORY-BEGIN`…`HISTORY-END` 區間，而非 break）出現同一計數字面 ≥2 行 ⇒ 計入既有 `_docbad`（與 `doc_format_precheck` 同級 fail）。可行性證據：`--dupes` 與段 1b 迴圈已存在；本輪 GAP3／Case C 已證明偵測有輸出；既有測試 `test_hook_emits_dupes_warning_without_blocking` 轉紅即強迫顯式遷移，符合腳本註解自述。

### 4. D3／D4／E8 Phase B — 下一張中大票應先做哪一項？

| 序 | 項 | 理由 | 可驗收判準 |
|---|---|---|---|
| 1 | **E8 Phase B**（單檔決定表＋`narrow_check_router` 一列） | 給 D1 真正可 fail-closed 的 token／落點集合；無表則 F3／密度閘繼續空轉 | 下一張票之目標 SPEC 存在機械表；改一決定漏一落點 ⇒ router 列紅；表外決定不得宣稱已受 F3 保護 |
| 2 | **D4**（停輪判準機械化） | D-002 十二輪 findings 數不降；無機械停輪會重演 | 連續兩輪「無新面向」可機檢（面向集合∩本輪 ID＝∅）⇒ 拒再發 review token |
| 3 | **D3**（三閘 rc=0≠無語意互斥） | 最深、需語意／對照裝置；在 B／D4 前做易變新治理巨石 | 至少一對互斥句有機檢或強制委員題；不得以三閘全綠代替 |

### 5. commit「三家共同結論」是否同型不實宣稱？能否機械閘？

**是同型背書宣稱。** `3e009126` 主旨「落地三家共同結論前兩項」，內文卻寫入佔位偵測／誠實邊界等**委員未審**機制；本輪亦無任何 `RECONCILE-STAMP`／委員 review 產出覆蓋這些 diff。

`venv/bin/python scripts/verification_claim_check.py --commit-msg <該 commit body>` → **rc=0**（現行閘對「三家共同結論」類歸屬盲目）。

**需要且能做機械閘（改既有檔即可）**：擴 `verification_claim_check.py` 的 `commit_msg` 路徑——若訊息匹配 `三家共同結論|依.*CODEX-R\d|委員.*落地` 等背書語，則要求同 task-id 在 audit 有對應 `committee_output`（或明示 `VERIFY-EXEMPT:…`）。不新腳本、不新 epic。

### 6. 可以進下一步嗎？

**否。** 在 P0-01／P0-02 未處置前，不得把 DOCROT 五項機制寫成「三家已審已落地」，亦不得以本輪閘狀態為下一張中大票的 D1 防線。

---

## GROK-R1-P0-01

**斷言**: 本輪至少五項實作機制屬「非任一家原文之折衷」，主委未開 consult 即落地，直接違反 R2 已接受之程序修正。

**碼證**: R2 synth L31 程序修正逐字「凡主委產出『非任一家原文』之折衷，自動開一輪 consult」。對照：(1) 佔位封閉集＝`brief_conformance_check.sh` L337-346，R2 E3 原文要的是 completeness 歷史 anchor 檢查（synth L17）；(2) `--dupes`＝`spec_count_audit.py` L102-126，超出「只數共 N 條」（synth L26）；(3) HISTORY break＝L117-118；(4) 併入 `spec_xref_hook.sh` L58-66 為主委成本拍板（commit `68a70342` 自白）；(5) F1 單檔收斂＝只改 `docs/SPLITUNIFY_SPEC.D-002.md`（`git diff --stat 44bbd8d3..HEAD -- docs/*.md`）。`handoffs/reconcile/` 無對這五項的後續 consult synth。RECHECK：重讀 synth L17-31；`git log --oneline 44bbd8d3..HEAD`；`grep -n PLACEHOLDERS\|def dupes\|HISTORY-BEGIN\|warn-only scripts/brief_conformance_check.sh scripts/spec_count_audit.py scripts/spec_xref_hook.sh`。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;scripts/brief_conformance_check.sh#55d4b8162804;scripts/spec_count_audit.py#0a36491036cd;scripts/spec_xref_hook.sh#c1fecd2ccd96

[BLOCKING] 信心度=High。會怎麼失敗：機制細節以「三家共同結論」對外流通，下輪委員／使用者以為已審；異議被「已落地」話術封口。**修法**：對五項開一輪 consult（可合併）；未 APPROVED 前 HANDOFF／commit 不得用「三家共同結論」涵蓋這五項機制，改標「主委試點、待追認」。**可行性**：consult 管線與 brief-kind 已存在；本 brief 即補審入口。

---

## GROK-R1-P0-02

**斷言**: R2 E3／E8 Phase A 指定的「completeness 拒收落在歷史區之 finding anchor」未實作；現況以骨架佔位字面硬擋替代，E3 只完成輸入契約的一半。

**碼證**: synth L17「只改派工契約與 completeness 之 anchor 檢查」；L22 E8A「completeness 拒收 anchor 落在歷史區之 finding」。本輪：`grep -c 'HISTORY\|歷史段\|沿革' scripts/completeness_check.sh` → **0**。已做：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 輸入邊界、`new_brief.sh` current block／diff、`brief_conformance_check.sh` L318-352 佔位集。佔位測 6 passed；completeness 歷史 anchor 測不存在。RECHECK：重跑上列 grep；讀 synth L17／L22；確認無新 completeness 測試指向 HISTORY。

**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7;scripts/brief_conformance_check.sh#55d4b8162804;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#976f11c084b2

[BLOCKING] 信心度=High。會怎麼失敗：手寫 brief 寫「整份檔」或委員仍把 source anchor 指進 HISTORY ⇒ 考古再審复發；佔位閘自以為已做完 E3。**修法**：在既有 `completeness_check.sh` 對 finding 的路徑:行／章節做 HISTORY-BEGIN..END 區間判定，命中 ⇒ FAIL；佔位集降為輔助。**可行性**：E8A 自述零新腳本；區間標記在 D-002 已存在（L329）。

---

## GROK-R1-P1-01

**斷言**: `dupes()` 在首個 `HISTORY-BEGIN`（或 `## 沿革`）處 `break`，會漏掉標記之後的活文多落點；「沿革略過無害」已被構造反例否證。

**碼證**: `spec_count_audit.py` L117-118。構造 A（HISTORY 後兩處 `共 29 條`）→ `--dupes` stderr **空**；構造 C（HISTORY 前兩處）→ 報 `1,2` 形落點。D-002 現把 HISTORY 放檔末故倖免；規則卻是「此後永遠不掃」。RECHECK：重跑 `/tmp` Case A／C 或本審查附錄等價 fixture。

**來源摘要**: scripts/spec_count_audit.py#0a36491036cd;handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md#554fd32867f1

[MAJOR] 信心度=High。會怎麼失敗：誤植／提早寫入的 HISTORY 標記讓其後活文雙真相源永久靜默。**修法**：改為區間 skip（見 BEGIN 則跳過直到 END），禁止 break 出迴圈。**可行性**：同函式內狀態機兩行級；既有 `test_dupes_*` 可加「HISTORY 後活文仍報」mutation。

---

## GROK-R1-P1-02

**斷言**: 主因 D1 的寫入時硬擋覆蓋率為 0%；「第一期只 warn」對主委自身已否證，不能再當 D1 防線。

**碼證**: `gov_check.sh` L269-273／`spec_xref_hook.sh` L65-66 皆 `|| true` 且不改 rc。`python3 scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md` → 警告含 `共 8 條 @ 117,3591` 等，rc=0。佔位硬擋只掛 `cx_run` 派工路徑（`cx_run.sh` 呼叫 brief_conformance），與「多落點寫入」正交。RECHECK：對 GAP3 重跑 `--dupes`；對一段含雙「共 N 條」的 docs 改動跑 `gov_check` 看 `_docbad` 是否仍 0。

**來源摘要**: scripts/gov_check.sh#4b333ce050ff;scripts/spec_xref_hook.sh#c1fecd2ccd96;docs/GAP3_EVENT_UX_SPEC.md#30bb5ab0aa28

[MAJOR] 信心度=High。會怎麼失敗：下張票主委繼續改一處漏一處，stderr 有字、流程不停。**修法**：見必答 3——段 1b 將活文區 `--dupes` 命中計入 `_docbad`（不新檔）。**可行性**：迴圈與腳本皆在；測試會刻意轉紅逼遷移。

---

## GROK-R1-P1-03

**斷言**: F1 活文收縮只落在 `SPLITUNIFY_SPEC.D-002.md` 卻被寫成 DOCROT 收斂點；若下一張中大票非 D-002 系列，本輪 F1 成效判準測不到。

**碼證**: `git diff --stat 44bbd8d3..HEAD -- docs/*.md` → 實質收縮僅 D-002（另 ROADMAP 2 行）。`docs/` 內含「共 N 條」之檔 ≥10；GAP3 活文仍雙落點（上條）。HANDOFF 表述「F1 活文收縮已到收斂點」。RECHECK：重跑 diff --stat；對非 D-002 SPEC 跑考古行／`--dupes`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#30bb5ab0aa28;handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md#554fd32867f1

[MAJOR] 信心度=High。會怎麼失敗：下一票審 GAP／GOV SPEC 時考古再審與雙計數依舊，卻以為 F1 已驗收。**修法**：對外改標「D-002 試點」；成效判準改為「下一張中大票目標 SPEC 的活文多落點／考古行相對基線下降」，或在該票開場先做同型收縮。**可行性**：只改表述／驗收句，不需新工具。

---

## GROK-R1-P1-04

**斷言**: 以「三家共同結論」為 commit 主旨背書未經委員審之實作細節，屬 verification_claim 同型的不實歸屬；現行 `--commit-msg` 路徑抓不到。

**碼證**: `git log -1 --format=%B 3e009126` 首行「落地三家共同結論前兩項」，內文含佔位偵測等自創機制。`venv/bin/python scripts/verification_claim_check.py --commit-msg <該 body 檔>` → **rc=0**。本輪無委員 stamp／review 產出覆蓋 `44bbd8d3..HEAD` 之 scripts／templates diff。RECHECK：重跑上列 claim-check；查 audit 有無對應 committee_output。

**來源摘要**: handoffs/20260912-DOCROT-X-REVIEW-R1-BRIEF.md#554fd32867f1;handoffs/reconcile/20260912-docrot-x-consult-r2/synth.md#955ac9458ed7

[MAJOR] 信心度=High。會怎麼失敗：git 史上留下「委員已審」假 provenance，後人／閘都當真。**修法**：改既有 `verification_claim_check.py` commit_msg 路徑——背書語需 audit 佐證或 EXEMPT；並回寫後續 commit 訊息勿再籠統掛「三家共同結論」於未審機制。**可行性**：檔案已有 `commit_msg` source_context（約 L795）；擴 regex＋audit 查詢即可。

---

## GROK-R1-P2-01

**斷言**: 「併進既有 hook 故一般寫檔零成本」在新增 `--dupes` 路徑上事前未實測；本輪測得觸發路徑仍付可見延遲。

**碼證**: brief assumed 自白只有 codex R2 對既有八支 4.39–4.97s。本輪：`python3 scripts/spec_count_audit.py --dupes docs/SPLITUNIFY_SPEC.D-002.md`×10 → median **34.7ms**；`GOVERNANCE_TEST_HARNESS=1 SPEC_XREF_HOOK_TARGET=docs/SPLITUNIFY_SPEC.D-002.md bash scripts/spec_xref_hook.sh`×5 → median **315.1ms**。非觸發名之 `.md` 在 case 過濾前仍付既有 `grep -l` synth 成本（預存），但**不**跑 `--dupes`。RECHECK：重跑上列 timing。

**來源摘要**: scripts/spec_xref_hook.sh#c1fecd2ccd96;scripts/spec_count_audit.py#0a36491036cd

[MINOR] 信心度=High。相對既有 ~5s 鏈，+35ms 不大，但「零成本」事前無數據＝過程病。**修法**：宣稱成本必附新增路徑 receipt；表述改「非觸發路徑不加 `--dupes`；觸發路徑 +~35ms」。

---

## GROK-R1-P2-02

**斷言**: 「骨架佔位對手寫 brief 零誤擋」事前未做 corpus replay；事後 replay 顯示歷史 BRIEF 字面 FP＝0，但手寫「整份檔」繞過仍在，不能代替 E3 的 completeness 半邊。

**碼證**: `find handoffs -maxdepth 1 -name '*BRIEF*.md'` → 652；對封閉八字面 `grep -qF` → **hit_any_placeholder=0**。腳本 L328 自白「擋不住手寫 brief 把審查標的寫成整份檔」。RECHECK：重跑字面掃描；抽一手寫「整份檔」brief 確認佔位閘 rc=0。

**來源摘要**: scripts/brief_conformance_check.sh#55d4b8162804;tests/governance/test_docrot_e3_brief_placeholder.py#2c350f092373

[MINOR] 信心度=High。語料 FP 攻擊未成立；過程攻擊成立；覆蓋洞指向 P0-02。**修法**：保留佔位集；補 completeness；宣稱改為「對 new_brief 骨架字面拒派；不宣稱涵蓋所有手寫 brief」。

---

## §1 必查（11 類）

1. 矛盾／互斥：有——「E3 已完成／三家共同結論」vs 未做 completeness anchor、五項未 consult（P0）。
2. 漏項／端到端：有——E3 半套；`--dupes` 無改動路徑 e2e（HANDOFF 已具名殘留，本輪確認）。
3. 不可測驗收：「到收斂點」無可遷移的跨票判準（P1-03）。
4. 可疑 quant 假設：無（本輪非特徵／回測數值）。
5. 過度工程：`--dupes` 形態擴張屬小幅過度；併 hook 反而是抑止第 9 支的同向選擇（待 consult）。
6. OOM／並行：無。
7. Cache：無。
8. API／型別：無。
9. 測試品質：單元／mutation 有（15 passed）；缺 completeness 歷史 anchor 測、缺 gov_check 改動路徑 e2e。
10. Agent 可執行性：N/A（審實作非審 TODO）。
11. 必要性／短命工：佔位集若補上 completeness 後可能部分重疊——應在 consult 裁是否雙掛。

---

ASSUMPTIONS_VERIFIED: brief 四條 assumed 均已用 shell 重判（latency／HISTORY Case A／F1 範圍／BRIEF 652 replay）；fact-verified 四條重跑相符；completeness 歷史 anchor 命中數＝0；claim-check 對樣本 commit rc=0  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_f2_total_items_count.py -q` → 15 passed；交件前 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-review-r1-grok.md --family grok`（見下）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀；僅本產出＋交接檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: blocked
BLOCKED-BY: GROK-R1-P0-01,GROK-R1-P0-02,GROK-R1-P1-01,GROK-R1-P1-02,GROK-R1-P1-03,GROK-R1-P1-04
CLOSED:
STATUS: DONE
