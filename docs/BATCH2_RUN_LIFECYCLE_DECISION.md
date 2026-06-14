# 第 2 批決策簡述（給使用者）｜2026-06-13

## 一句話
Run 生命週期 UX 經 Codex adversarial（6 BLOCKING/10 MAJOR）後**升大型**：不可逆刪除必須建立在「per-run 跨進程鎖 + registry 交易」之上，否則會刪到正在生成的 run、rerun 會吃掉你的命名。

## 你已確認的產品決策（兩輪 AskUserQuestion）
保留最近 5 個未命名（**per symbol+週期各 5**）；跑完提示+列表管理都要；命名 run 永不自動清；刪除=features+對應 cgsa_work；**並發刪除=直接 409**。

## 我替你做的技術決策（可否決）
| # | 決策 | 理由 |
|---|---|---|
| 14 | 分級升大：Codex 實作+Composer review+雙家族 adversarial | 命中 (b) 跨層共用路徑+(c) 多 phase/不可逆刪除 |
| 15 | registry `add` 改 merge-preserve（rerun 不清掉 alias/created_at）+ 全 mutation 走檔案鎖交易 + corrupt 時清理 fail-closed | Codex B2/B6/M12：現行 add 整筆替換會讓重跑同 config 後你的命名消失、舊版多實例會 lost update |
| 16 | 生成入口掛 per-run 鎖：**同 config 並發生成第二個會直接失敗**（之前行為未定義、實際會互踩） | Codex B5；行為改進，記錄於此供否決 |
| 17 | cgsa_work 刪除前用 work manifest 的完整 config_hash 核對所有權；`FFACT_CGSA_WORK_DIR` 設定時不刪 cgsa 側並明示 | Codex M13/M8：hash 前 8 碼可能碰撞；override 目錄不在白名單 |
| 18 | pass2 瀏覽任務 ID 加 hash 後綴（同幣種+週期多 run 各自可見，舊行為只留第一個） | Codex B7 |
| 19 | API 錯誤碼寫死（409 run_busy/422 alias_conflict/500 delete_partial 禁回 200）；時間一律 ISO-8601 UTC | Codex M14/M15 |
| 20 | run 大小在生成完成時算一次存 registry，列表不現掃 8.3GB | Codex m11 |

## 風險與回退
- P0-P4 各自 commit 可單獨 revert；lease 接線若致生成回歸可單獨退 P2。
- 安全底線不變：白名單雙根、逐層 lstat 拒 symlink、永不碰 kline_cache/feature_klines/d* cache。

## V3 增補決策（雙家族 round2 後）
| # | 決策 | 來源 |
|---|---|---|
| 21 | （V5 終局）鎖改 **fcntl.flock**：kernel 互斥+進程死亡自動釋放——崩潰後**零等待**自動解鎖，無任何 stale/接管協定（V3 rename/V4 mutex 兩版自製協定均被 Codex 證明有 race 後轉向）；前提=data_cache 本機磁碟 | Codex N1 r3/r4 |
| 22 | 命名（set_alias）也要取 run 鎖：刪除/清理進行中不能命名（409），反之亦然 | Codex N2、Composer #5 |
| 23 | warmup 期間鎖不落手：factory 經 lease_sink 介面把鎖交給 service，warmup 完才釋放（無空窗） | Codex N3、Composer #2 |
| 24 | batch resume 啟動時驗 completed 項的 manifest，被刪的自動重排隊重生成（checkpoint 格式不變） | Codex N4 |
| 25 | 瀏覽任務 ID 用完整 config_hash（pass2+register_hdf5_for_browse+batch adapter 全鏈） | Codex #7、Composer #3 |
| 26 | registry 損毀時生成登記只進記憶體不覆寫檔案，原檔保留 .corrupt-時戳 副本供救援 | Codex #12 |

## 你需要做的
- 無阻塞事項。若反對 #16（同 config 並發生成改為失敗）或 #21 的 1 小時 stale 門檻請說，其餘照走。
