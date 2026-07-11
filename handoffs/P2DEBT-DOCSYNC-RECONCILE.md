# P2DEBT-DOCSYNC 主委 reconcile
Task-id: p2debt-docsync | Date: 2026-07-11 | Chair: Claude
腿:claude 自產版 + grok(BLOCK) + composer(APPROVE 附條件) + codex(BLOCK)

## 裁決一:文件同步——三方一致,執行
- D-1(殘留清單過時)成立;採 Codex 修正:untracked 計數依快照時點浮動,清單以檔名列舉不釘數字;本輪稽核工作檔(P2DEBT-DOCSYNC-*)一併入版。
- D-2(tsc 10→11)成立;票面改「清掉全部既存 feature-factory 測試型別錯誤(實測 11)」,不釘死數字(codex)。
- D-3(ROADMAP 1e+1b「重簽中」落後)成立;改三方閉合;「B1-B5 全入版 cfcf08e」改 cfcf08e+e433500(codex)。
- 漏列項採納:ROADMAP 內嵌 tsc 10(grok/composer/codex 三家同抓)、ROADMAP 文首日期(grok)、ROADMAP L51 grouped 止血矛盾(codex)、HANDOFF RULEIMPL R3/R5 分叉收斂到 R5(grok)。
- composer 誤報一處:frontend/handoffs 實為 2 檔(json+log),`find` 實測駁回;不影響其 verdict。

## 裁決二:golden 4 檔——2 BLOCK,不入版,拆票
共識維持 working tree 不 commit,拆為 P2 債票 5「1a cut1 golden provenance 閉合」,綁定項:
1. 恢復並改寫 `rebaseline_reason`/`rebaselined_at`:保留 1-align B2 史+追加 2026-07-11 unlock 鏈(BLOCKED-1A/original_regen/B5 F5)(grok §3-1)。
2. reuse guard 補 fail-closed integrity 校驗(input/meta digest+selected features)+generator 對應測試(codex)。
3. 禁以 suite 現綠自證;須獨立重放 receipt(command+sha 鏈+解鎖決策檔交叉引用)(grok §3-3)。
4. payload 處置策略寫死(gitignore+外部 sha 歸檔 或 納版)(grok §3-2)。
5. 與票 2(legacy 測試 data_cache redirect)相鄰施工,避免二次動 meta(grok #6);閉合須原提出方 Grok+Codex 複驗(章程§B8)。

## 裁決三:殘留處置(一致項照辦)
.gitignore 入版;scripts/ic1eb_*.py 獨立 commit 入版;gate audit logs 隨 commit;frontend/handoffs/run_receipts 2 檔搬根目錄 handoffs/run_receipts/ 後刪空殼(搬入不覆蓋,205101Z≠205126Z 兩輪並存);settings.json 維持不 commit。

## 新制度(使用者 2026-07-11 直接裁定)
每次開新 session 讀 HANDOFF 時,先稽核 HANDOFF+相關文件(ROADMAP 等)vs repo 實況,過時先修正再開工。入 CLAUDE.md。
