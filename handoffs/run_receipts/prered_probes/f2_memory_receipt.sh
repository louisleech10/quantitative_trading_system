#!/bin/zsh
# PRE-RED Task 2.5：自 v7 種子原設定（12h＋1h）之 HEAD 實跑 log 抽各段 RSS，產 F-2 分段記憶體收據。
# 用法：zsh <本檔> <v7seed_HEAD.log> <out.json>
# 來源 log 由 v7_seed_at.sh HEAD 產生（/usr/bin/time -l 包覆；2026-10-03 04:03–04:19 實跑）。
LOG=${1:?log}; OUT=${2:?out}
STAGES=$(grep '^\[' "$LOG" | awk '!seen[$0]++' \
  | grep -E 'Layer [0-9]+ (starting|done)|memmap concat\]|concat_memmap\]|\[spill\]' \
  | sed -E 's/^\[([0-9-]+ [0-9:,]+)\] INFO [^:]+: /\1\t/' \
  | jq -R -s 'split("\n") | map(select(length>0) | split("\t") | {ts: .[0], event: .[1],
      rss_mb: ([.[1] | scan("(?:rss|RSS)=([0-9]+) ?MB")] | if length > 0 then (.[0][0] | tonumber) else null end)})')
MAXRSS=$(grep 'maximum resident set size' "$LOG" | awk '{print $1}')
PEAK=$(grep 'peak memory footprint' "$LOG" | awk '{print $1}')
REAL=$(grep ' real ' "$LOG" | awk '{print $1}')
TERM=$(grep -c 'command terminated abnormally' "$LOG")
jq -n --argjson stages "$STAGES" --arg maxrss "$MAXRSS" --arg peak "$PEAK" --arg real "$REAL" --arg term "$TERM" \
  --arg cmd "zsh handoffs/run_receipts/prered_probes/f2_memory_receipt.sh handoffs/run_receipts/20261003-prered-v7seed-HEAD.log <out>" '{
  schema_version: 1, command: $cmd, exit_code: 0,
  source_run: "v7_seed_at.sh HEAD（v7 種子原設定：BTCUSDT 12h＋1h、14 天公開窗、全史預熱）；/usr/bin/time -l",
  terminated_by_os: ($term | tonumber > 0),
  wall_seconds: ($real | tonumber),
  max_rss_bytes: ($maxrss | tonumber),
  peak_footprint_bytes: ($peak | tonumber),
  last_explicitly_completed_segment: ($stages | map(select(.event | test("Layer [0-9]+ done"))) | last),
  last_observed_event: ($stages | last),
  last_rss_observation: ($stages | map(select(.rss_mb != null)) | last),
  completion_semantics: "memmap_utils 之 copying DF 行記於該塊物化與複製之前（非完成）；故 DF 5/5 只代表開始複製，其完成與當時 RSS 無證據",
  segments: $stages,
  unmeasured_segments: ["校準域讀取（_resolve_public_window）之獨立 RSS：log 無對應行", "多週期對齊合併後之 L6.5", "L7 寫檔"],
  honest_bounds: "各段 RSS 取自生產碼既有 log 行（Layer 起訖與 memmap 複製進度），非獨立取樣器；peak footprint 含 memmap 與 swap 映射，大於常駐 RSS。最後 log 明示完成之段＝1h Layer 6 done（rss 356 MB）；其後進入 memmap 合併，最後觀測事件＝開始複製 DF 5/5（無 rss），最後一筆 rss＝DF 3/5 複製中 871 MB；終止點之 RSS 無證據；合併之完成、L6.5、L7 未到達、未量測（本機無法於原設定下走到）。v6 測試另於 HEAD 量得 peak footprint 約 71 GB（watch 與 /usr/bin/time 收據於 node_at_commit_watched.sh 產出），d229336e^ 同測試 0.80 GB。修復歸全票排序第 4 步 ICFIRSTALIGN 乙之 MEM-RSS：原設定須完成，或於超出記憶體預算前以具名錯誤 fail-closed；被系統終止不算通過。"
}' > "$OUT"
