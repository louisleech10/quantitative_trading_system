# CGSA cgsa_work 磁碟 footprint — 委員會調查 brief

> 角色:獨立架構審查者,挑戰 Claude 假設、找反例/更簡解。read-only,只寫 handoff。
> 觸發:真實事故 2026-06-19 ETH L3 `Failed to persist-shard ... free_before=0.18 GiB`(磁碟撐爆)。

## 事故事實(實測)
- CGSA wide 產 **437,781 特徵**;cgsa_work L3 shard 持久化為 **float32**(`column_group_registry.py:747 data_fp32`;`multi_tf_generator.py:20 normalize_npy_persistence_float32`)。437781×20352×4 = **35.6GB/symbol**。
- T2 layer_metrics 實測:RSS 峰值僅 ~1.2GB → **是磁碟非記憶體**。
- 時序(`multi_tf_generator.py:204-212`):L3→persist、L4→persist、L5、L6 各生成即 persist 到 cgsa_work;**釋放(release_storage)在 L6 之後的 L7_raw streaming 階段**。
- 失敗發生在 **L3 持久化中途**(L3 是 46741 L2 特徵 × rolling 展開,佔 437K 大宗)。
- L3 磁碟預檢(`column_group_registry.py:1543`)**只檢單一 shard(~25MB)**,非累積總量 → 預檢過、實際寫到一半才爆。
- 使用者反映:以前 28GB 能跑完同類 run(待證;若一直 float32×437K 則理論需 35GB)。

## Claude 假設(待你挑戰)
**cgsa_work 在 L3-L6 累積全部 npy shards(~35GB float32),L7 streaming 才釋放 → 峰值 > 28GB。** 失敗即 L3 累積階段撐爆。

## 請各委員獨立調查 + 裁決
- **T-A cgsa_work 串流釋放**(使用者指定):cgsa_work 是否真累積到 ~35GB 才在 L7 釋放?**能否邊 L3 生成邊 consume+release_storage 釋放**(bound 峰值遠低於 35GB),還是 L7(cross/meta/L6.5)必須一次看到全部 group 故無法增量釋放?給可行性 + 最小改法 + 風險(正確性/resume)。
- **T-B float16 cgsa 暫存**:cgsa_work npy 改 float16 可砍半(17.8GB,放得進)。`normalize_npy_persistence_float32` 為何強制 float32?float16 暫存對下游(L6.5 fracdiff/ADF/IC)精度的真實影響?(HANDOFF 有「float16 strict 讀升 float32」待辦脈絡)。值不值、哪些欄不可降?
- **T-C 累積磁碟預檢 + 提早 abort**:L3 預檢只檢單 shard。應否在 L3(或生成前)估「整批 L3 累積 footprint vs 可用磁碟」,不夠就**提早 abort 給清楚訊息**(別跑一小時才在 L3 中途失敗)?像 L7 的 Disk pre-check。
- **T-D 為何以前 28GB 夠**:437K×float32=35.6GB 理論上 28GB 不夠。是 (a)以前 run 規模較小 (b)cgsa_work 其實有串流釋放峰值較低 (c)其他?用 git/code 判斷,別猜。

各委員寫 handoffs/20260619-cgsa-disk-{你的代號}.md(≤60行):T-A..T-D 各裁決+證據+最小改法+優先序。
