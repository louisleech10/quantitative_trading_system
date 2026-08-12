# fixture 宿主檔（非真實文件）

本檔只為 WL-03 之 governance-mechanism 投影而存在。

<!-- BEGIN GENERATED: governance-mechanism -->
| 機制ID | 平台機制 | 適用範圍 | 證據 | 實跑結論 | 狀態 |
|---|---|---|---|---|---|
| M-001 | setsid | ASSERT 逐行執行後之程序群終止 | receipt:handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md | 本機不可用——不在 PATH（command -v 非零）；以 set -m 使背景 job 自成 pgid 取代 | 現行 |
| M-002 | ulimit | fork bomb 之第二道防線（壓低 per-user 程序上限） | receipt:handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md | 硬上限不可降——Invalid argument；只降 soft 必被子程序抬回，故不作為防線 | 現行 |
| M-003 | timeout | ASSERT 逐行逾時包裹 | receipt:docs/GOV_ASSERT_PATHA_NOTE.md | 可用，已上線於寫檔路徑之零執行改法 | 現行 |
| M-004 | flock | gate token 之併發互斥 | assumed:僅出現於敘事段落，尚未被任一改法採用，故未實跑 | 未實跑——列此以示 assumed 是顯式標記而非省略 | 現行 |
<!-- END GENERATED: governance-mechanism -->
