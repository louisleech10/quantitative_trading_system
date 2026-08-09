#!/usr/bin/env bash
# doc_format_precheck.sh — 治理文件「產出端」格式檢查（GOV-DOC-CHECK-AT-WRITE，2026-08-02）。
#
# 病根：格式檢查點在**消費端**（派工／freeze）不在**產出端**（寫檔當下）。
#   實證代價：本 session 4 輪、B4 批次 5 輪（該批 38%）純燒在「寫完 → 派工被擋 → 重寫 → 重派」。
#   （`GOV-FORMAT-SSOT` 症狀 B；記憶 feedback_tools_must_enforce「檢查點放產出端非消費端」）
#
# 強制機制（使用者定死第 3 條：工具必須自帶強制使用機制，不准靠紀律和記憶）——**三層**：
#   ① `.claude/settings.json` 的 **PostToolUse `Edit|Write`**：寫檔當下自動跑，exit 2 回灌 context
#   ② `scripts/gov_check.sh` 1b 段：對**本次改動的 docs/*.md** 全掃（pre-push hook 也呼叫）
#   ③ `gate.sh` / `cx_run.sh` / `committee_run.sh`：派工與 freeze 時 fail-closed 硬擋
#
# 誠實邊界（**逐條講清楚，不誇大**；CODEX-R1-P1-02／P1-03 已指出第一版宣稱過寬）：
#   1. 這是**早期警告**，不是硬閘。PostToolUse 在寫入**之後**跑，擋不掉已落地的內容。
#      真正的 fail-closed 是第 ③ 層，一律保留（defense-in-depth）。
#   2. **第 ① 層只涵蓋 Edit|Write 工具**。經 Bash 重導寫出的檔（例如 `new_brief.sh` 自己產骨架）、
#      外部編輯器改的檔、本機制上線前就存在的檔，**都不會觸發 hook** —— 那是第 ② ③ 層在接。
#   3. 檔案編到一半必然不合規，本腳本會報紅；預期行為，訊息已標明「編輯中可續寫」。
#   4. **只認 `.md`，且只認路徑型別判得出來的**。判不出型別即靜默放行（rc=0），不亂擋非治理文件。
#      已知不涵蓋：非 `.md` 的治理檔（如 `docs/plan/**/*.yaml`）、`handoffs/` 外的 brief。
#      前者本來就沒有對應範本可驗；後者由 committee_run/cx_run 的 brief 閘接手。
#   5. `handoffs/*` 在 `.git/info/exclude` 被整包排除 ⇒ 第 ② 層看不到 brief。
#      brief 的強制點是第 ③ 層，且已修為**開債前**就跑完整檢查（CODEX-R1-P1-01）。
#
# 用法：
#   bash scripts/doc_format_precheck.sh <file>      # 直接檢查某檔
#   bash scripts/doc_format_precheck.sh             # hook 模式：從 stdin 的 JSON 取 file_path
# rc: 0=合規/不適用；2=不合規（訊息在 stderr，hook 會回灌 context）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

target="${1:-}"

# hook 模式：PostToolUse 以 stdin 餵 JSON，取 tool_input.file_path。
# 取不到就靜默放行——hook 絕不能因為自己解析失敗而擋住使用者工作。
if [ -z "${target}" ]; then
  if [ -t 0 ]; then
    exit 0
  fi
  target="$(python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
ti = d.get("tool_input") or {}
p = ti.get("file_path") or ti.get("path") or ""
print(p if isinstance(p, str) else "")' 2>/dev/null || true)"
fi

[ -n "${target}" ] || exit 0
[ -f "${target}" ] || exit 0

# 正規化為 repo 相對路徑（hook 給的是絕對路徑）
rel="${target}"
case "${rel}" in
  "${REPO_ROOT}/"*) rel="${rel#"${REPO_ROOT}/"}" ;;
esac

# 只管 .md
case "${rel}" in
  *.md) : ;;
  *) exit 0 ;;
esac

# ── 路徑 → 型別判定 ──
# 順序有意義：D 延伸檔的檔名也含 SPEC（例：P16_COMMITTEE_DEBT_SPEC.D-001.md），必須先判 dext。
#
# ⚠️ 用 basename 判，**不得**用 `docs/*.D-NNN.md` 這種樣式（CODEX-R1-P2-04，2026-08-02 實跑證實）：
#   shell 的 `*` **會跨 `/`**，故 `docs/sub/nested.D-001.md` 也會命中，
#   但凍結程序 §2 規定的是 `docs/<原檔 basename>.D-<NNN>.md`＝**docs/ 正下方一層**。
#   誤判的後果是拿較窄的 dext 檢查取代該有的 spec 檢查。
kind=""
case "${rel}" in
  docs/*/*) : ;;   # docs 子目錄不在 §2 規範內，交後面的一般規則
  docs/*)
    _base="${rel#docs/}"
    case "${_base}" in
      *.D-[0-9][0-9][0-9].md) kind="dext" ;;
    esac
    ;;
esac
if [ -z "${kind}" ]; then
  case "${rel}" in
    docs/*SPEC*.md) kind="spec" ;;
    docs/*TODO*.md) kind="todo" ;;
  esac
fi

# ⚠️ 收斂檔路由**必須在「判不出型別即放行」之前**。
#   第一版把它放在那行之後 ⇒ `synth.md` 沒有 `brief-kind:` ⇒ kind 為空 ⇒ 提早 exit 0，
#   整段收斂檔檢查形同未掛（實測兩個反例皆 rc=0 才發現）。
if [ -z "${kind}" ]; then
  case "${rel}" in
    handoffs/reconcile/*/synth.md) kind="synth" ;;
    handoffs/reconcile/*)          exit 0 ;;   # sources/ 逐字副本、sources.lock 不由本腳本管
  esac
fi

# brief：不看檔名看內容（brief 檔名無固定樣式），行首 brief-kind: 是唯一可靠標記
if [ -z "${kind}" ]; then
  case "${rel}" in
    handoffs/*)
      if grep -qE '^brief-kind:' "${target}" 2>/dev/null; then
        kind="brief"
      fi
      ;;
  esac
fi

# findings 檔：handoffs/ 下沒有 brief-kind:、但**含 canonical finding heading** 的 .md
#
# 〔GOVB1 Task 4.3 要點 3；B10 review-r2 必答 1，codex＋composer **兩家核准 (A)**〕
# 病根（摩擦帳事件 18）：主委自己的 `**來源摘要**` 寫行號而非 12 位雜湊，4 個 P0/P1 全 FAIL。
#   `票 B-31` 的自檢只進了**委員 prompt**，而主委產物**不流經 cx_run 派工路徑**
#   ⇒ 本腳本原本對這類檔判不出型別、走下面那行**靜默 exit 0**。那個靜默放行就是機械根因。
#
# ⚠️ 順序：必須在「判不出型別即放行」**之前**（與收斂檔路由同一個坑，見上方註解）。
#   `handoffs/reconcile/*` 已於上方分流（synth 走 verdict 檢查、sources/ 放行），不會落到這裡。
if [ -z "${kind}" ]; then
  case "${rel}" in
    handoffs/*.md)
      if LC_ALL=C grep -qE '^#{2,6}[[:space:]]+[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}' "${target}" 2>/dev/null; then
        kind="findings"
      fi
      ;;
  esac
fi

# 判不出型別 → 不適用，放行
[ -n "${kind}" ] || exit 0

# findings：走**與委員交件完全同一支**檢查（cx_run.sh --selfcheck → completeness_check --single）。
#
# 家族名由**檔內第一條 canonical heading 的前綴**導出（封閉規則，非猜測）。
#   🔴 誠實限制：家族名這樣導出後，`--family` 的 family-binding 檢查對本路徑**恆真**
#   ——本路徑的價值不在 binding，而在空殼欄位／必填欄／sentinel 形態／重複 ID／
#   **P0/P1 來源摘要須為 12 位雜湊**（`completeness_check.sh:263,352`）這些檢查，
#   而事件 18 正是最後那一項。改用檔名後綴導出會對 `*-BACKLOG.md` 這種非家族後綴誤判，
#   為了一個恆真的 binding 換來偽陽性，不划算。
#
# 誠實邊界（與檔頭第 1、2 點一致，不誇大）：PostToolUse 在寫入**之後**跑 ⇒ 早期警告非硬閘；
#   經 Bash 重導寫出的檔不觸發。codex（`CODEX-R2-P1-01`）要求的 fail-closed 強制路徑**另立票**。
if [ "${kind}" = "findings" ]; then
  fam="$(LC_ALL=C grep -oE '^#{2,6}[[:space:]]+[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}' "${target}" 2>/dev/null \
    | head -1 | sed -E 's/^#+[[:space:]]+([A-Z]+)-R.*$/\1/' | tr '[:upper:]' '[:lower:]')"
  # 導不出家族 ⇒ 放行（與本腳本「判不出即放行」一致，不亂擋）
  [ -n "${fam}" ] || exit 0
  sc_out="$(bash "${SCRIPT_DIR}/cx_run.sh" --selfcheck "${target}" --family "${fam}" 2>&1)"
  sc_rc=$?
  [ "${sc_rc}" -eq 0 ] && exit 0
  {
    echo "【文件格式產出端檢查未過】${rel}（判定型別：findings，家族=${fam}）"
    echo "${sc_out}"
    echo "---"
    echo "這是**寫檔當下**的早期警告：檔案已寫入，續寫即可；"
    echo "但**收斂/銷帳時會硬擋**，且與委員交件跑的是同一支檢查同一組參數，現在補可省一整輪。"
  } >&2
  exit 2
fi

# ⚠️ **不得再排除收斂檔**（2026-08-03 使用者定位「檢驗審查放在錯誤的地方」）。
#
# 初版此處寫 `handoffs/reconcile/*) exit 0`，理由是「走 completeness 那條線」。
#   但那條線在 **`debt_clear` 銷帳時**才跑 ⇒ 主委填完 `synth.md` 到銷帳之間，
#   Verdict 未填／格式錯誤**全程無紅燈**。這正是「檢查放在消費端」的實例，而且是主委親手加的。
#   T2 的 fail-open 事故起因即為 synth 的 Verdict 行放了佔位符（`CODEX-R2-P1-13`）。
# ⇒ 改為：收斂檔在**寫檔當下**即檢查其 Verdict 是否已填實（與 `gate.sh` D-1 同判準，見下）。
#   跨檔完整性（來源 ID 是否全在綜合）仍由 `completeness_check --lock` 負責——
#   那需要 lock 與全部來源，寫單一檔時本來就無法判定，屬**合理**的消費端檢查。
# （實際路由已上移至「判不出型別即放行」之前，見上方。）

# 收斂檔：寫檔當下只驗「Verdict 已填實」（與 gate.sh D-1 **同一份實作**）。
# 跨檔完整性交 completeness_check --lock —— 那需要 lock 與全部來源，寫單一檔時無法判定。
# ⚠️ 這段刻意放在 `$( )` **外面**：把多行 echo 塞進命令替換會踩到引號解析問題
#    （實測 runtime 報 `syntax error near unexpected token`，而 `bash -n` 抓不到）。
if [ "${kind}" = "synth" ]; then
  if bash "${SCRIPT_DIR}/verdict_filled_check.sh" "${target}"; then
    exit 0
  fi
  {
    echo "【文件格式產出端檢查未過】${rel}（判定型別：synth）"
    echo "收斂檔的 Verdict 未填實，或格式不符 gate.sh D-1 判準。"
    echo "  需要：行首 Verdict（可帶括號補充）+ 冒號 + 實質結論"
    echo "  不接受：範本佔位、待填、未填、空結論、散文中順口提及"
    echo "---"
    echo "未填實會在 debt_clear 銷帳時被擋 —— 現在補比那時省一輪。"
  } >&2
  exit 2
fi

out="$(
  if [ "${kind}" = "brief" ]; then
    bash "${SCRIPT_DIR}/brief_conformance_check.sh" "${target}" 2>&1
  else
    bash "${SCRIPT_DIR}/template_check.sh" "${kind}" "${target}" 2>&1
  fi
)"
rc=$?

[ "${rc}" -eq 0 ] && exit 0

{
  echo "【文件格式產出端檢查未過】${rel}（判定型別：${kind}）"
  echo "${out}"
  echo "---"
  echo "這是**寫檔當下**的早期警告（GOV-DOC-CHECK-AT-WRITE），不是硬閘：檔案已寫入。"
  echo "若仍在編輯中，續寫即可；但**派工/freeze 時 gate 會硬擋**，現在補齊可省一輪。"
} >&2
exit 2
