# 委員蓋章 Pipeline 完整性盤查 + 加固設計(v3;三家對抗+UNION 閉環後重寫)

> 2026-07-22 Claude 起草。v1/v2 被三家對抗審查對碼證偽**多處現況事實錯**;本 v3 據閉環後 UNION(`handoffs/20260722-pipeline-design-review-UNION.md` A–G)重寫。
> **狀態:草稿,三家 verdict 一致「不得直接動工」**;本 v3 待**第二輪對抗**。
> **來源誠實**:節點強制色/家數/觸發條件皆已對碼(三家 verify:gate.sh/gate_check.sh/review_quorum_check.sh/reconcile_stamps_check.sh/verify_task_provenance.py/settings.json/.github/workflows)。
> 圖例:🟢機器強制 | 🟡紀律(可靜默跳) | 🔴無守 | 🅿️提案未實作(prev v1/v2 誤寫成現況)

## ⚠️ 現行「活洞」——不是文件錯,是現在就在漏(對碼三家一致)
| 洞 | 事實 | 影響 |
|----|------|------|
| **H1** | `gate_check.sh:47` 分類器只認 `codex\|cursor-agent\|agy`+`claude -p`;**無 grok**;`timeout codex/cursor` 亦 rc=0 | grok(現行主力實作)+ timeout 包裝派工**完全不被 PreToolUse gate** |
| **H2** | `reconcile_stamps_check.sh:27` 預設 `codex,composer`;`gate.sh` 不傳第三參;`gate.sh:185-193` 未識別 grok 時**預設記 composer** | **機器戳記/quorum 永不要求 grok**——「grok 正式委員」在機檢層是空的 |
| **H3** | `gate.sh` `--risk low` / `waived:` / `stamped-waived:` 字串**整段跳過** adversarial+stamp;無 a–d 機檢;高風險 waiver 無獨立批准 | 自標 low/編 waiver 理由 → 中/大鐵律機檢層可繞 |
| **H4** | `gate_check.sh:30` 無 jq → **fail-open(exit 0)** | jq 缺失/parse error 時 gate 形同關閉 |
| **H5** | token 是 **kind 級非 intent 級**(`gate_check.sh:64-69` 只驗同類 token mtime≤900s,不綁 path/task/risk) | 一次 low dispatch token,15min 內任意 Task/Bash 派工放行 |
| **H6** | `verify_task_provenance.py:21` ADV 路徑只認 `ADV-CODEX\|COMPOSER`;grok finding 對齊機檢=0 | grok adversarial finding 不進 provenance 硬路徑 |
| **H7** | `pytest tests/governance` 現有 **5 紅**(sync drift×2/gitignore receipt×1/B5 fixture×2) | 治理 suite 本身未綠 |
> H1–H3 建議與本設計脫鉤,當獨立 bug 儘早修(現在就在漏 grok)。

## 一、全流程節點盤查(據 UNION;~24 節點,取代 v1 的 12)
> 完整清單見 UNION §C(N1–N24)+ §A/§B。此處列**強制色最需注意**者;每格指向 UNION 錨。
> **家數規則(四套,勿混——UNION C21)**:①資料正確性簽核=Claude+Codex+Composer ②SPEC/TODO 對抗審=3 家 CLI(codex+composer+grok;Claude 起草非實作者) ③實作 code review=2 家(實作者那家排除) ④stamp 機檢家數=**現碼 2 家(codex,composer),不含 grok**。②③是制度要求、④是機器現況 → 分裂,須拆欄單一化。

| 節點 | 需委員/簽核 | 現行強制(對碼) | UNION |
|------|------------|---------------|-------|
| 任務大小/risk/owner 自判 | 使用者否決 | 🔴 純自陳,gate 只記字串 | N1 |
| 決策文件+使用者 facts/scope/waiver signoff | 使用者 | 🟡 `--facts-asked` 只記不驗真 | N2/C24 |
| manifest+coverage | 使用者 | 🟡 `--manifest` 可選,未附則 coverage_check 不跑 | N3/C18 |
| discovery 派工 | 是 | 🟢 dispatch token;**不驗派幾家/未回裁決** | N4 |
| **discovery reconcile(Claude 綜合)** | 是 | 🔴 **無守**(stamp 只 --spec 觸發) | #3/C4 |
| **reconcile-verify 完整性複驗(IC 事故本體)** | 是 | 🔴 **無機檢**(HANDOFF 教訓) | N5 |
| SPEC/TODO 起草 | — | 🟢 artifact gate 但 🟡 Edit/handoffs/非 SPEC 檔名可閃 | #4/C11 |
| **SPEC/TODO 對抗審(3 家)** | 是 | 🔴 **零機檢家數**(quorum 只掛 impl-bN) | C2 |
| SPEC/TODO **freeze+修訂後重審重 stamp** | 是 | 🟡 無獨立 freeze gate | N6 |
| 多輪 adversarial R2/R3 閉合 | 是 | 🟡 只驗含 `ADV-*-N →` 行,不驗幾輪 | N7 |
| **SPEC-review reconcile(Claude 綜合審意見)** | 是 | 🟡 stamp 有 hash 但**只 2 家、不驗 finding 全集**(C25) | #6/C25 |
| stamp-review 派工+落地 | 是 | 🟡 provenance;ADV 檔只認 CODEX\|COMPOSER | N8/C8 |
| TODO-ADV reconcile(與 SPEC-ADV 分離) | 是 | 🔴 同 reconcile 病 | N22 |
| 實作派工(逐批) | 是 | 🟢 --spec/--todo+前批 quorum;但 **grok 繞 gate(H1)** | #8 |
| **每批 Claude 獨立驗收** | 是 | 🔴 合約+memory 無腳本 | N24 |
| 實作 code review(2 家) | 是 | 🟢 quorum floor=2(僅 impl-bN;命名耦合可跳,C13) | #9/C13 |
| agy 實習 review | 否(不計 quorum) | 🔴 無 gate | N13 |
| **DATA-CORRECT 三方簽核** | 是 | 🔴 無 gate 接入,實務手跑 | N9 |
| golden/baseline freeze+mutation | 條件是 | 🟡 腳本存在,不在咽喉 | N10 |
| preflight/postflight | 硬閘 | 🟡 不在 gate.sh | N11 |
| register-output 入帳 | provenance | 🟡 不自動 | N12 |
| **Finding remediation+原提出方 CLOSURE 重跑** | 是 | 🔴 無機檢 receipt | N23/#10 |
| **宏觀斷路器 ≤2 輪→委員會** | 是 | 🔴 無機檢 | N15 |
| 膨脹 5 訊號→升中/大 | 是 | 🔴 | N16 |
| T-D 執行端資格/寫入/model identity/prompt 獨立性 | 是 | 🔴 文件閘無 runtime | N17 |
| **小任務繞管線** | — | 🔴 無 SPEC/adversarial/quorum | N18 |
| 接回假綠 diff | — | 🟡 無 diff-assert gate | C19 |
| verify_pretooluse(claim hook) | — | 🟢 PreToolUse(settings:76-82)但不驗 finding 全集/無 claim 不攔 | C23 |
| commit/CI verify_claim | — | 🟢 掃變更 md;code-only push no-op;**無 completeness/stamp/引用遞移** | C5/#12 |
| merge/PR required checks+branch protection+deploy/canary | — | 🔴/🟡 | N19 |
| HANDOFF/ROADMAP 完工可見性 | — | 🟡 屢漏記 | N20 |

## 二、逃脫點總覽(UNION §B C9–C20 + G 補;對碼)
token kind 級(C9)、risk/waived 旁路(C10)、Edit/Bash/handoffs/改名寫檔繞 artifact(C11/C26)、無 jq fail-open(C12)、quorum 命名耦合+只數 dispatch 不驗審過(C13)、grandfather 舊 adversarial 不強制 reconcile(C14)、Claude 自寫 stamp+自算 sha256(C15)、settings 同信任域可改 hook(C16)、O3 豁免(C17)、manifest 可選(C18)、假綠測試(C19)、機械 union 只字串比漏語意(C20)、四套家數語義未拆(C21)、ORCH 雙家/三家自矛盾(C22)、非 Claude Code 終端直呼 executor 繞 PreToolUse(C26)。

## 三、加固提案(🅿️全部未實作;每項封什麼/擋不到什麼;三家評)
> **v1/v2 曾把下列寫成現況=錯(C6)**;此處全標🅿️提案。落地順序見末。
- **①機械 union 聚合**🅿️:改手抄為腳本先全收錨點進骨架,刪除留 diff。**條件真封** EP1 字面掉項;**假封**=來源清單由綜合者提供可縮減、只字串比漏語意(C20)。**codex 前置**:canonical finding ID + 來源+sha + 嚴格 parser + unknown/dup fail + 刪除 disposition。
- **②completeness_check.sh**🅿️(檔不存在):吃綜合+N 來源列漏錨。擋字面掉項;**擋不到**語意降級(本次 coverage 錯它會放行)。
- **③PreToolUse hook 雙向**🅿️:檔名(Reconcile/SPEC/TODO)OR 內容特徵觸發。**擋不到** shell/rename/chunked Edit/設定竄改(C26/C16);且 hook→completeness→stamp 與 DRAFT 生成互卡 → 需 **DRAFT/REVIEWED/FROZEN 狀態機**(codex)。
- **⑤階段入口 gate+引用遞移+closure receipt**🅿️:掛 gate.sh 咽喉。**現況非**:discovery 無 --spec 不觸發 stamp(同 C4 洞);引用遞移未實作、需 **DAG/parent hash 防環**;receipt 須同 stamp 級 task-id+hash 否則假 receipt。
- **⑥CI/server 硬後盾**🅿️(不存在):唯一擋「連 hook 都被改」。需 **required protected status + PR/push 同檢 + 無 continue-on-error 全覆蓋治理腳本/settings/audit**;現僅 verify_claim(掃 md)。push 後 CI 擋不住 session 內先執行。
- **④便宜模型全項忠實度覆議**🅿️:弱;與原委員同 prompt 易共盲;不可替代 ②。

**落地順序(codex/grok 建議)**:先把①②合併成 **typed finding ledger/immutable manifest** → 以其建 **stage DAG + action-bound token**(修 H5)→ family registry 單一化(修 H1/H2/H6,納 grok+agy)→ 才接 ③hook/⑥CI required。④最後且 advisory。

## 四、分層總表(每層擋什麼/擋不到什麼)
```
A 偵察 多家frontier(貴)          → 擋單家盲點｜擋不到共同盲點
B 聚合 ①②(🅿️)                  → 擋字面掉項｜擋不到語意降級
C 忠實 ④Haiku/單家(🅿️)          → 部分擋語意降級｜易共盲
強制1 ③hook(🅿️)                → 擋跳過+改名｜擋不到shell/rename/設定竄改
強制2 ⑤gate.sh階段入口(🅿️)      → 擋建在未驗上階段｜擋不到分類器盲區(H1)/waiver(H3)
閉合 ⑤receipt(🅿️)              → 擋假綠閉合｜需task-id+hash
硬後盾 ⑥CI(🅿️,不存在)          → 擋連hook被改｜擋不到CI本身被停(需repo權限=你)
兜底 使用者+稽核日誌            → 擋以上全部殘留(本 epic 全程即靠此)
```

## 五、誠實邊界 + verdict
- 現況所有🟢層都在我寫入範圍內(settings/gate/腳本)→ 有 meta 逃脫;唯一硬層=⑥CI(未落地)+ 你。
- 本 v3 據**閉環後 UNION**重寫,但 UNION 分群仍是 Claude 語意步驟(G-4:理論可有殘漏)。
- 三家 verdict:**不得直接動工**;本 v3 應過**第二輪對抗**(找重寫後仍錯/漏)再定案。
- 產物鏈:三家審=`…-pipeline-design-review-{codex,composer,grok}.md`;UNION+補正=`…-UNION.md`(A–G);複驗=`…-union-verify-*.md`。
