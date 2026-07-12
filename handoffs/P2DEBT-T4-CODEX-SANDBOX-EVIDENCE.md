# P2 債票 4:codex 沙箱間歇卡死蒐證(2026-07-11 session 樣本)
Task-id: p2debt-t4 | 蒐證人: Claude(觀察債,小任務自做) | CLI: codex 0.144.1, model gpt-5.6-sol high, sandbox workspace-write

## 樣本清單(本 session,全部有 receipt 檔可稽)
| # | 時點 | 場景 | 卡死命令類型 | 出處 |
|---|------|------|-------------|------|
| 1-2 | T1 TODO 複驗 | `bash scripts/template_check.sh` 真實 replay | repo shell 腳本(hung twice) | handoffs/P2DEBT-T1-TODO-REVERIFY-codex.md L18 |
| 3 | T1 實作 scope 輪 1 | 合併驗收管線(porcelain+comm+diff 串接) | 複合 shell 管線,>3min 無輸出 terminated | handoffs/P2DEBT-T1-IMPL-RESULT-codex.md L16 |
| 4 | T1 實作 scope 輪 2 | `comm -13`/sort/diff 單獨執行 | coreutils 管線,>60s terminated | 同上 L17 |
| 5 | T2 TODO R2 複驗派工 | (非卡死)quota 上限,19:07 恢復 | ERROR: usage limit | tasks/b3s7j329x.output |

## 對照組(同 session 正常完成)
- docsync 補腿審查/SPEC R1 審/R2-R3 複驗/R4 換手改稿/實作主體(pytest 151 passed 經 run_with_receipt)——**Python/pytest/rg/讀寫檔全正常**。
- 歷史樣本:2026-07-11 前 HANDOFF 已記「CLI 0.144.1 重運算命令偶發停滯」。

## 模式歸納(初步,樣本 n=4 卡死)
1. 卡死集中在**外部 shell 工具鏈**(bash 腳本 replay、coreutils 管線 comm/sort/diff),非 Python/pytest 路徑。
2. 同命令 Claude 本機/Grok/Composer 沙箱皆瞬時完成(票 1 scope gate 我 <1s 跑完)→ 環境特異,非命令本身。
3. 疑似方向:codex 沙箱(Seatbelt/landlock)對某些 pipe/subprocess 組合的 IO 攔截死鎖;與運算量無關(comm 兩個 32 行檔也卡)。
4. quota 事件獨立於卡死,但同影響派工可用性,列動態選層依據。

## 根因強候選(2026-07-12 web 研究,主委查 GitHub — 症狀吻合,版本時間線未證)
> ⚠️ 誠實修正(使用者 2026-07-12 質疑):此為**症狀吻合的強候選**,非「實錘」。#7852 機制與我方現象吻合,
> 但**未確認版本時間線**——使用者記得「之前順利」。兩假設未分辨:
> **H1 工作負載改變**(長期 bug,本 session 才大量跑 shell 管線驗證 comm/bash 腳本才踩到;以前多為寫碼+pytest 單進程)
> vs **H2 版本退化**(升級 0.144.1 後才壞,同管線舊版能跑)。分辨需:同管線命令在舊版 codex 是否卡(資料未取)。
> 另:gpt-5.6-sol **模型非死鎖主因**——pipe deadlock 是 CLI 層 spawn/wait 子進程行為,與推理模型無關;變數是 CLI 版本。
> A′ mitigation 與 DELEGATED 繞法**不受此不確定性影響**(避開管線在兩假設下皆有效),故處置照舊。

### 歸因修正(Grok X/web recon 2026-07-12,handoffs/T4-GROK-XSEARCH-RECON.md)
**#7852 很可能不是我方 bug**:issue 收斂 repro(ghul0)=`codex exec --full-auto`+asyncio.to_thread 特有;
**無 --full-auto 的純 codex exec 正常**。我方派工用 `-s workspace-write` **且 auto 模式擋 --full-auto**(見 reference_dispatch_cli_invocation)→ 對不上。
**更吻合=macOS 專屬族(皆 OPEN)**:#18243(macOS workspace-write/read-only shell 卡,danger-full-access 才行)、#19020(macOS 0.122.0 workspace-write hang)。
**版本時間線**:Grok 查 0.66→0.144 **無官方「已修」/「安全版本區間」,無乾淨退化分界**;2025-11 已有 process-group 修補(#5258/#6575)但問題跨版本未清。
→ 我方「之前順利」偏向 H1(以前沒跑管線)但無硬證。處置(A′ 首選/DELEGATED fallback)不變;danger-full-access 可繞但棄隔離(不採)。

**症狀吻合的 upstream 族(候選,非單一定論)**:
- **openai/codex#7852**(2025-12-11 開,**至今 OPEN 未修**):`--sandbox workspace-write`/`--full-auto` 下命令無限卡、
  子進程 orphan 於 sleeping 態。根因=process group 管理缺陷:子進程未 `setpgid(0,0)` 隔離、
  signal 只打直接子 PID 非 process group、**孫進程 orphan 後 keep pipe open → codex 等 EOF → pipe deadlock**。
- 完美對應我方現象:多進程 shell 管線(comm/sort/diff、bash 腳本)才卡(pipe 多進程易留 orphan)、
  Python/pytest 不卡(單進程)、與運算量無關(32 行 comm 也卡=pipe 死鎖非算太久)。
- 相關:#7846(process substitution 同根因)、#4337(shell-wrapped timeout 卡死)、
  #18243(macOS workspace-write/read-only shell 卡,只有 danger-full-access 能跑)。

### 處置修正(取代原 A/B)
- **A′ 根治性 mitigation(新,已入 ORCH)**:codex 派工命令**避開多進程管線/process substitution**——
  改單命令寫檔→再讀檔(而非 `comm`/`diff <()`/長 `|` 串接)→ 繞過 pipe-orphan 觸發點,多數任務即可「順利運作」不必 delegate。
- **A(繞法)保留為 fallback**:真需 shell 管線且無法拆 → DELEGATED-TO-ORCHESTRATOR(已入 ORCH §8)。
- **B 改寫**:**不需另開新工單**——#7852 已由他人回報且根因精確;可選擇在 #7852 補一則 macOS Seatbelt repro
  (comm 兩 32 行檔即卡)增加訊號,但屬對外發文=需使用者核可,非自動執行。

## 建議處置(二選一,委員會/使用者裁)
- **A 固化繞法入 ORCH(建議)**:派工合約加一條——「codex 任務中 shell 管線/repo bash 腳本卡 >60s:改由編排端(Claude)代跑該驗證命令並附 receipt,codex 只交代碼與 Python 級驗證」;成本低,立即止血。
- **B 回報 OpenAI**:樣本尚少(n=4)且無最小重現(卡死非確定性);建議累積至 n≥8 或找到穩定重現組合再報,避免無效工單。

## 本票狀態(CLOSED 2026-07-12)
裁定=採建議 **A**:DELEGATED-TO-ORCHESTRATOR 繞法已固化入 `docs/MULTI_AGENT_ORCHESTRATION.md` §8 派工管線踩坑(含「不得自報他方代跑」provenance 條款);同處順修 `| tail` 遮 rc 反教訓(票2 C-1)。**B(回報 OpenAI)延後**:n=4 未達 n≥8 門檻且無穩定最小重現;後續 codex 派工順手累積樣本,達門檻再開子任務。小任務 Claude 自收,不派工。
