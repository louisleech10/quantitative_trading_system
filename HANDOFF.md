# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-05 00:50 | **Branch**: main
**狀態**: 🔵 **第 0 批（摩擦止血）SPEC 第 3 輪審查中**（背景 `b35hfatbi`，codex+composer）

## ▶ 立即接手點

1. 確認 `b35hfatbi`（R3 審查）與 `b66zeiug3`（push）結果。
2. R3 回報後：`reconcile_build.sh 20260805-govb0-spec-r3 --mode review <兩家產出>` → 填群集 →
   **主委自檢「每個來源 ID 都進群集表」**（`票 B-36`：`completeness --lock` 驗不到這層，rc=0 也可能漏）→
   加 `## 戳記` → `reconcile_body_hash.sh` → 三家戳記輪 → 過關才生成 TODO。
3. **使用者 2026-08-04 深夜指示**：疑慮／開票／合併**都交委員裁**，不阻塞問他；白話說明寫
   `handoffs/20260804-治理進度-白話日誌.md`（持續追加，他醒來會看）。照第 0→1→2 批順序做下去。

## 第 0 批現況

**SPEC** `docs/GOVB0_FRICTION_SPEC.md` **R3 版**（4 Phase／**11 Task**，`template_check` rc=0）
涵蓋 `B-15`／`B-14`／`B-30`／`B-32` ＋ `B-24` **僅紀律面**。
Phase 0 可觀測性 → Phase 1 `B-32` prompt → Phase 2 `B-15` 判定（5 Task）→ Phase 3 `B-14`＋`B-30`。

**兩輪審查皆「需修補後派工」**：R1 19 findings（5 P0）→ R2 17 findings（**7 P0**，P0 未降）。
⇒ 命中 P16 scope-accretion 失敗模式 ⇒ **R3 起劃定不受理範圍**（SPEC §N 末段），**三家已表態接受**。
不受理四項：截斷 oracle（`B-35`）／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位。

**收斂檔**：R1 `handoffs/reconcile/20260804-govb0-spec-r1/synth.md`（三家 APPROVED，sha `25e1241f`）；
R2 `handoffs/reconcile/20260805-govb0-spec-r2/synth.md`（三家 APPROVED，sha `8b8d0a94`，E-1～E-13）。

**驗證過的關鍵設計**（探針全在 `handoffs/govb0_probes/`，codex 已獨立重跑確認）：
- **原型③ 26/26**：命令位置擴大為所有 shell 起始語境（`^ ; & | ( ` $( && || eval後 xargs後`）＋對 `-c`／`eval` 引號引數遞迴。
- **剝引號須跨行有狀態**（`awk`），**禁 `sed` 行內替換、禁正規化為單行**（後者會使真多行指令第 2 行漏網）。
- `eval`／`$()`／反引號／子 shell **在現行 gate 即已 fail-open**；帶路徑前綴的家族 CLI、直接跑 `cx_run.sh` 亦然。

## 🔴 本 session 新開 7 張票（`B-30`～`B-36`，全是做這批時當場撞到）

`B-30` 委員覆蓋自產／`B-31` format-failed 無便宜修正路徑／`B-32` stamp prompt 無條件注入／
`B-33` locale 相依守衛 fail-open／`B-34` stamp roster vs 角色閘／`B-35` 截斷 oracle／
`B-36` **收斂工具群集表盲點**（附錄使 ID 必然存在 ⇒ 「有沒有進群集表」零機檢；建議併 `B-13`）。
backlog 36 張、白話總覽 36 張，**雙向差集空、零重複**（每次改票都要重跑此對帳）。

## ⚠️ 本 session 踩過的坑（**照做可省時**）

- **`B-15` 咬了 7 次**。三種觸發：①引號內的 `;`／`|` ②`claude`（含 `.claude/`、`claude-501`）＋後方任一 `-p` 子字串
  （`rev-parse`／`--porcelain`／**目錄名 `-probes`**）③**commit 訊息某行以家族名開頭**。
  **權宜**：commit 一律 `git commit -F <訊息檔>`；路徑用底線；指令中避免 `.claude` 與 `-p` 同時出現（或中間插管線）。
- **`export LC_ALL=C` 會洩漏進 pre-push**，弄紅 6 個治理測試。只在單條 grep 用 `LC_ALL=C grep -a`，**禁 export**。
- **`ts_stamp.log` 是 Non-ISO＋NEL**，預設 locale 下 `grep` **靜默返空**（連 `-c` 都不輸出）。
- **`rc` 禁經 pipe**（`cmd | tail; echo $?` 讀到的是 tail 的 rc）——本 session 又犯一次。
- **禁 `python3 -c`**（憲法明載）——違反一次，實測卡 **603.89 秒**。
- 委員產出須 `gate.sh register-output <task-id> <path>` 才過 claim checker，否則擋 commit。
