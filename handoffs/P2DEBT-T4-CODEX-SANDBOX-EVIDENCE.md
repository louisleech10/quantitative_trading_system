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

## 建議處置(二選一,委員會/使用者裁)
- **A 固化繞法入 ORCH(建議)**:派工合約加一條——「codex 任務中 shell 管線/repo bash 腳本卡 >60s:改由編排端(Claude)代跑該驗證命令並附 receipt,codex 只交代碼與 Python 級驗證」;成本低,立即止血。
- **B 回報 OpenAI**:樣本尚少(n=4)且無最小重現(卡死非確定性);建議累積至 n≥8 或找到穩定重現組合再報,避免無效工單。

## 本票狀態(CLOSED 2026-07-12)
裁定=採建議 **A**:DELEGATED-TO-ORCHESTRATOR 繞法已固化入 `docs/MULTI_AGENT_ORCHESTRATION.md` §8 派工管線踩坑(含「不得自報他方代跑」provenance 條款);同處順修 `| tail` 遮 rc 反教訓(票2 C-1)。**B(回報 OpenAI)延後**:n=4 未達 n≥8 門檻且無穩定最小重現;後續 codex 派工順手累積樣本,達門檻再開子任務。小任務 Claude 自收,不派工。
