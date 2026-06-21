# FF 一致性整併 — 任務分級 + 批次 (Claude 提案)

依 FINAL 的 6 項(Q5/#1/E-normalize/Q3/Q2-A/Q2-B)。原則:**同子系統 + 同風險級 + 有依賴鏈**的合批;大型不再塞更多。

## 分級理由(對 CLAUDE.md a-d)
- Q5 access_log env:小。純 API 啟動 config,無數值,風險極低。
- #1 worker logging+smoke:中。碰 batch worker(b 共用路徑),logging infra,無數值。
- E progress-normalize 函式+parity:中。跨單/多兩路徑(b),但只組 payload,無數值。
- Q3 單補RSS+分欄+WS/TS/Zustand:中。跨後端+前端(b),無數值。
- Q2-A retention(非阻塞+背壓+staging+checkpoint狀態機+resume+前端):**大**。碰 persist/checkpoint/resume 一致性(b)(c 難回退)+磁碟+前端。
- Q2-B 交易式 bulk-delete endpoint:**大**。多子系統一致性失效(checkpoint/RunManager/quality/磁碟)+tombstone(b)(c)。

## 批次(6 項 → 4 批,減 SPEC/派工/review 重複成本)
**B1〔中〕log/terminal 觀測**:Q5 + #1 + smoke。理由:都 logging infra、無數值、可一起驗(重啟後端看 terminal 乾淨+batch log 進檔)。走中型管線。
**B2〔中〕進度統一**:E progress-normalize 函式 + parity(progress 部分) + Q3(單補RSS/分欄/WS/TS/Zustand)。理由:**Q3 是 normalize 函式的第一個消費者**,committee 定「E 隨首次 payload 改同 PR」→ 兩者天然同批,免先做 Q3 再重構。走中型管線。
**B3〔大〕Q2-A 批次保留**:retention-normalize 函式 + retention parity + 非阻塞 + 磁碟背壓 + staging(register後移) + checkpoint 狀態機 + resume + 前端 completionQueue/Dialog 擴展。理由:大型不再合併;retention 的 E-normalize 在此首次用故含於此。走大型管線(決策簡述+雙家族 adversarial)。
**B4〔大/中-大〕Q2-B**:交易式 bulk-delete endpoint(失效 checkpoint/RunManager/quality/磁碟+tombstone)。依賴 B3 狀態機。走大型管線。

## 不合併的理由
- B3/B4 各自已大,合併會超出可審範圍 + 難回退。分開可獨立 revert。
- B1(logging) 與 B2(progress) 不混:不同子系統,且 B2 要等 normalize 函式設計,B1 可先獨立落地(最快讓 terminal/log 乾淨)。

## 執行順序(依 FINAL P0a→P2.5)
B1(P0a+P0b) → B2(P0c+P1) → B3(P2) → B4(P2.5)。每批:中=SPEC/TODO+一家 adversarial+Composer 實作+Codex review;大=決策簡述+雙家族 adversarial+Composer 實作+Codex review。

## 待委員會評
① 分級對嗎(尤其 #1/E/Q3 是中還是小;Q2-A/B 是大還是中-大)?② B1(Q5+#1)、B2(E+Q3) 合併恰當,還是該拆/該再併?③ 有無依賴順序錯置?
