#!/usr/bin/env bash
# audit_append.sh — P1-6 Task 1.1：債務 audit 唯一寫入點
#
# 職責：
#   1. 以 mkdir 原子鎖保護「讀尾端序號 → +1 → append」單一臨界區（禁 flock）
#   2. producer 由本腳本強制填入（呼叫端指定即忽略）
#   3. 事件名／必填欄位讀 scripts/audit_events.json，缺欄 fail-closed
#   4. 陣列欄位以 --field k=@<json> 傳入，非法 JSON 拒寫
#   5. legacy 事件（non_debt_legacy_events）不受序號規則管、不參與連續性掃描
#   6. --require-absent-session <name>：鎖內一次完成「掃 session 唯一性 + append」
#
# 命名契約（不可省）：
#   *_locked()  = 假設鎖已被呼叫端持有，函式內一律不得再 _acquire_lock
#   無後綴者     = 自行取鎖的對外入口，不得被 *_locked() 內部呼叫
#
# 用法：
#   bash scripts/audit_append.sh --event <name> --field k=v [--field k=@json] ...
#   bash scripts/audit_append.sh --require-absent-session <name> --event committee_round_open ...
#
# 環境：
#   DEBT_AUDIT_OVERRIDE  — 測試隔離 audit 路徑；必須 GOVERNANCE_TEST_HARNESS=1，否則 fail-closed
#   AUDIT_APPEND_MAX_RETRY / AUDIT_APPEND_RETRY_INTERVAL — 僅 GOVERNANCE_TEST_HARNESS=1 時生效
#   GOVERNANCE_TEST_HARNESS — 測試 harness 旗標
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY="${SCRIPT_DIR}/audit_events.json"
PRODUCER="audit_append.sh"

# 取鎖重試上限（有限等待，不得無限）
# 反 bypass：AUDIT_APPEND_MAX_RETRY / AUDIT_APPEND_RETRY_INTERVAL 僅在
# GOVERNANCE_TEST_HARNESS=1 時生效；未綁 harness 若有設定 → fail-closed
# （與 DEBT_AUDIT_OVERRIDE 同型；production 一律用下方預設）
if [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ]; then
  MAX_RETRY="${AUDIT_APPEND_MAX_RETRY:-100}"
  RETRY_INTERVAL="${AUDIT_APPEND_RETRY_INTERVAL:-0.05}"
else
  if [ -n "${AUDIT_APPEND_MAX_RETRY:-}" ] || [ -n "${AUDIT_APPEND_RETRY_INTERVAL:-}" ]; then
    echo "ERROR: AUDIT_APPEND_MAX_RETRY/RETRY_INTERVAL 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
    exit 1
  fi
  MAX_RETRY=100
  RETRY_INTERVAL=0.05
fi

# 執行期狀態
AUDIT_PATH=""
LOCKDIR=""
_LOCK_HELD=0
EVENT_NAME=""
# 旗標「有沒有出現」與「值」分離（CODEX-R2-P1-01）：
# 不可用 [ -n "$值" ] 代替「旗標出現」——空字串必須 fail-closed 拒寫，不可整段跳過守衛。
REQUIRE_ABSENT_SET=0
REQUIRE_ABSENT_SESSION=""
# 以 RS(\x1e) 分隔的 field 鍵值（k=v / k=@json）；禁 NUL（env 傳不過）
FIELD_RS=$'\x1e'
FIELD_PAIRS=""

usage() {
  cat <<'EOF'
用法:
  bash scripts/audit_append.sh --event <name> --field k=v [--field k=@json] ...
  bash scripts/audit_append.sh --require-absent-session <name> --event <name> ...

選項:
  --event <name>                 事件名（須在 registry debt_events 或 non_debt_legacy_events）
  --field k=v | k=@<json>        欄位；@ 前綴表示 JSON 值（陣列/物件）
  --require-absent-session <n>   鎖內掃描：若已有同 session_name 的 committee_round_open 則拒寫

producer / event_id 由本腳本強制填入（event_id=UUID v4）；
呼叫端傳 producer=... 或 event_id=... 會被忽略覆寫。
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

# 序列化欄位共用字元驗證（通則：凡會進入 FIELD_PAIRS / 落地 JSON 的外部輸入
# 一律套用；不得只在其中一條入口把關）。
#
# 拒絕集合 ≡ 消費端行界全集，不得自訂黑名單：
#   本檔 JSONL 由 Python 以 str.splitlines() 切行
#   ⇒ 拒 {c | len(("a"+c+"b").splitlines()) > 1}
# 來源：Python 文件 str.splitlines() 定義（非人工列舉，避免漏字元）：
#   https://docs.python.org/3/library/stdtypes.html#str.splitlines
# 實測等價集合（0x110000 掃過一次）：
#   \n \r \v(\x0b) \f(\x0c) \x1c \x1d \x1e \x85 U+2028 U+2029
# 其中 \x1e 同時為 FIELD_PAIRS 的 RS 分隔符（注入可使 predicate ≠ 落地欄位）。
# 非 ASCII 以 UTF-8 位元組比對（bash 字串為 byte；U+0085=c2 85 等）。
_reject_serialized_control_chars() {
  # $1=標籤（錯誤訊息用） $2=待驗字串
  local label="$1"
  local val="$2"
  # RS 單獨訊息（既有測試／除錯慣例）
  case "${val}" in
    *"$FIELD_RS"*) die "${label} 不得含 RS(\\x1e) 字元" ;;
  esac
  # \n/\r：常見換行，沿用既有訊息
  case "${val}" in
    *$'\n'* | *$'\r'*) die "${label} 不得含換行字元" ;;
  esac
  # 其餘 splitlines 行界（與上列合 = 全集；閹割本 case = F1 mutation 靶）
  # U+0085 NEL = utf-8 c2 85；U+2028 LS = e2 80 a8；U+2029 PS = e2 80 a9
  case "${val}" in
    *$'\v'* | *$'\f'* | *$'\x1c'* | *$'\x1d'* | *$'\xc2\x85'* | *$'\xe2\x80\xa8'* | *$'\xe2\x80\xa9'*)
      die "${label} 不得含 Python splitlines() 行界字元"
      ;;
  esac
}

# ── 路徑解析 ──────────────────────────────────────────────
_resolve_audit_path() {
  if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
    if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
      echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
      return 1
    fi
    printf '%s\n' "${DEBT_AUDIT_OVERRIDE}"
    return 0
  fi
  python3 - "${REGISTRY}" "${REPO}" <<'PY'
import json
import os
import sys

reg_path, repo = sys.argv[1], sys.argv[2]
try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(1)
rel = reg.get("audit_log_path")
if not isinstance(rel, str) or not rel:
    print("ERROR: registry 缺 audit_log_path", file=sys.stderr)
    sys.exit(1)
print(os.path.join(repo, rel))
PY
}

# ── 鎖（mkdir 原子；禁 flock）────────────────────────────
_acquire_lock() {
  local i=0
  [ -n "${LOCKDIR}" ] || {
    echo "ERROR: LOCKDIR 未設定" >&2
    return 2
  }
  mkdir -p "$(dirname "${LOCKDIR}")" 2>/dev/null || true
  until mkdir "${LOCKDIR}" 2>/dev/null; do
    i=$((i + 1))
    if [ "${i}" -ge "${MAX_RETRY}" ]; then
      echo "ERROR: 取鎖逾時 (${LOCKDIR})" >&2
      return 1
    fi
    sleep "${RETRY_INTERVAL}"
  done
  _LOCK_HELD=1
  return 0
}

_release_lock() {
  if [ "${_LOCK_HELD}" = "1" ] && [ -n "${LOCKDIR}" ]; then
    rmdir "${LOCKDIR}" 2>/dev/null || true
    _LOCK_HELD=0
  fi
  return 0
}

_cleanup_on_exit() {
  _release_lock
}
trap '_cleanup_on_exit' EXIT INT TERM

# ── lock-held 內部 API（一律不得 _acquire_lock）──────────

# 讀尾端序號（只認 debt 事件的 sequence）；回 stdout 為下一號
_next_seq_locked() {
  python3 - "${REGISTRY}" "${AUDIT_PATH}" <<'PY'
import json
import sys
from pathlib import Path

reg_path, audit_path = sys.argv[1], sys.argv[2]
try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 壞: {exc}", file=sys.stderr)
    sys.exit(2)

debt_events = set(reg.get("debt_events", {}) or {})
legacy = set(reg.get("non_debt_legacy_events", []) or [])
max_seq = 0
path = Path(audit_path)
if path.is_file():
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: 讀 audit 失敗: {exc}", file=sys.stderr)
        sys.exit(2)
    for line in raw.splitlines():
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            # 以 { 開頭但壞 JSON：連續性掃描路徑 fail-closed（寫入端不吞）
            print(f"ERROR: audit 含無法解析的 JSON 行", file=sys.stderr)
            sys.exit(2)
        if not isinstance(rec, dict):
            continue
        ev = rec.get("event")
        if ev in legacy:
            continue
        if ev not in debt_events:
            continue
        seq = rec.get("sequence")
        if isinstance(seq, int) and not isinstance(seq, bool) and seq > max_seq:
            max_seq = seq
        elif isinstance(seq, str) and seq.isdigit():
            n = int(seq)
            if n > max_seq:
                max_seq = n
print(max_seq + 1)
PY
}

# 掃 session_name 是否已有「開債事件」（事件名由 registry opens_debt 推導，禁硬編）
# 回傳：0=找到  1=確認不存在  2+=掃描錯誤
# 契約：假設持鎖；函式內不得 _acquire_lock；registry 讀取在鎖內（靜態 SoT，非 audit）
_scan_session_locked() {
  local session="$1"
  python3 - "${AUDIT_PATH}" "${session}" "${REGISTRY}" <<'PY'
import json
import sys
from pathlib import Path

audit_path, session, reg_path = sys.argv[1], sys.argv[2], sys.argv[3]
# 開債事件名：唯一 SoT = debt_events[*].opens_debt == true（與 reconcile_build/write_sources_lock 同型）
try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(2)

events = reg.get("debt_events") or {}
if not isinstance(events, dict):
    print("ERROR: registry debt_events 非 object", file=sys.stderr)
    sys.exit(2)
# 嚴格布林：僅 JSON true（Python True）算開債；字串/數字/null 一律非開債
open_events = [
    name
    for name, spec in events.items()
    if isinstance(spec, dict) and spec.get("opens_debt") is True
]
if len(open_events) != 1:
    print("ERROR: registry 的 opens_debt 事件不是恰一筆", file=sys.stderr)
    sys.exit(2)
open_event = open_events[0]

path = Path(audit_path)
if not path.is_file():
    sys.exit(1)  # 不存在 → 確認沒有
try:
    raw = path.read_text(encoding="utf-8")
except OSError as exc:
    print(f"ERROR: 讀 audit 失敗: {exc}", file=sys.stderr)
    sys.exit(2)

found = False
for line in raw.splitlines():
    s = line.strip()
    if not s.startswith("{"):
        continue
    try:
        rec = json.loads(s)
    except json.JSONDecodeError:
        print("ERROR: audit 含無法解析的 JSON 行", file=sys.stderr)
        sys.exit(2)
    if not isinstance(rec, dict):
        continue
    if rec.get("event") == open_event and rec.get("session_name") == session:
        found = True
        break
sys.exit(0 if found else 1)
PY
}

# 寫入一筆（假設已持鎖）。stdin 不使用；參數經 env/argv 傳 python。
# $1 = 下一序號（debt 用；legacy 傳 0 表示不寫 sequence）
# $2 = is_debt (1/0)
# 其餘透過環境變數 AUDIT_APPEND_FIELDS（NUL 分隔 k=v）與 EVENT_NAME
_append_event_locked() {
  local next_seq="$1"
  local is_debt="$2"
  AUDIT_APPEND_FIELDS="${FIELD_PAIRS}" \
  EVENT_NAME="${EVENT_NAME}" \
  PRODUCER="${PRODUCER}" \
  NEXT_SEQ="${next_seq}" \
  IS_DEBT="${is_debt}" \
  REGISTRY="${REGISTRY}" \
  AUDIT_PATH="${AUDIT_PATH}" \
  python3 <<'PY'
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

reg_path = os.environ["REGISTRY"]
audit_path = Path(os.environ["AUDIT_PATH"])
event_name = os.environ["EVENT_NAME"]
producer = os.environ["PRODUCER"]
is_debt = os.environ.get("IS_DEBT", "1") == "1"
next_seq = int(os.environ.get("NEXT_SEQ", "0"))
raw_fields = os.environ.get("AUDIT_APPEND_FIELDS", "")
field_rs = "\x1e"

try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 缺檔或 JSON 壞: {exc}", file=sys.stderr)
    sys.exit(1)

debt_events = reg.get("debt_events") or {}
legacy_events = set(reg.get("non_debt_legacy_events") or [])
required_common = list(reg.get("debt_event_required_fields") or [])
required_per = (reg.get("required_fields_per_event") or {}).get(event_name, [])
enums = reg.get("enums") or {}
allowed_origin = set(reg.get("allowed_origin_scripts") or [])
schema_version = reg.get("schema_version", 1)
# field_name → registry 鍵路徑；落地前守衛用來點名違規來源（非「來源可信」豁免）
registry_sourced = {}

# 行界字元：≡ Python str.splitlines() 消費端定義（非人工黑名單）。
# 等價於任何 c 使 len(("a"+c+"b").splitlines()) > 1；與 bash 守衛同一集合。
def _has_splitlines_break(s: str) -> bool:
    for ch in s:
        if len(("a" + ch + "b").splitlines()) > 1:
            return True
    return False


def _reject_registry_landed_string(value, registry_key: str) -> None:
    """registry 讀入且將落地的字串：違規則 fail-closed 並點名 registry 鍵。

    「可信」= 已被驗過，不是「來自 registry」。schema_version / 預設
    origin_script 皆為 runtime 可變輸入。
    """
    if not isinstance(value, str):
        return
    if _has_splitlines_break(value):
        print(
            f"ERROR: registry 鍵 {registry_key} 不得含 Python splitlines() 行界字元",
            file=sys.stderr,
        )
        sys.exit(1)


def _reject_json_string_values(obj, path: str) -> None:
    """json.loads 後遞迴驗所有字串值（含巢狀 object/array）；違反 fail-closed。

    繞過面：CLI 字元守衛只看 raw 字串；JSON \\uXXXX 轉義在 loads 後才成行界字元。
    """
    if isinstance(obj, str):
        if _has_splitlines_break(obj):
            print(
                f"ERROR: JSON 字串值不得含 Python splitlines() 行界字元 ({path})",
                file=sys.stderr,
            )
            sys.exit(1)
        return
    if isinstance(obj, dict):
        for kk, vv in obj.items():
            # 鍵亦為字串；若含行界會寫進 JSONL 同行破壞切行
            if isinstance(kk, str) and _has_splitlines_break(kk):
                print(
                    f"ERROR: JSON 鍵不得含 Python splitlines() 行界字元 ({path})",
                    file=sys.stderr,
                )
                sys.exit(1)
            child = f"{path}.{kk}" if path else str(kk)
            _reject_json_string_values(vv, child)
        return
    if isinstance(obj, list):
        for i, vv in enumerate(obj):
            _reject_json_string_values(vv, f"{path}[{i}]")
        return


def _reject_all_landed_strings(obj, path: str = "", field_root: str = "") -> None:
    """落地前最終防線：凡會進 JSONL 的字串（無論來源）一律驗 splitlines。

    registry 衍生欄位優先以 registry 鍵路徑報錯，便於修 registry 而非誤判 CLI。
    """
    if isinstance(obj, str):
        if _has_splitlines_break(obj):
            root = field_root or path.split(".", 1)[0].split("[", 1)[0]
            if root in registry_sourced:
                print(
                    f"ERROR: registry 鍵 {registry_sourced[root]} "
                    f"不得含 Python splitlines() 行界字元",
                    file=sys.stderr,
                )
            else:
                print(
                    f"ERROR: 落地欄位不得含 Python splitlines() 行界字元 ({path})",
                    file=sys.stderr,
                )
            sys.exit(1)
        return
    if isinstance(obj, dict):
        for kk, vv in obj.items():
            if isinstance(kk, str) and _has_splitlines_break(kk):
                print(
                    f"ERROR: 落地鍵不得含 Python splitlines() 行界字元 ({path})",
                    file=sys.stderr,
                )
                sys.exit(1)
            child = f"{path}.{kk}" if path else str(kk)
            root = field_root if field_root else (kk if isinstance(kk, str) else path)
            _reject_all_landed_strings(vv, child, root)
        return
    if isinstance(obj, list):
        for i, vv in enumerate(obj):
            _reject_all_landed_strings(vv, f"{path}[{i}]", field_root)
        return


# 解析 --field 對（RS \x1e 分隔；env 不可含 NUL）
fields = {}
if raw_fields:
    for pair in raw_fields.split(field_rs):
        if not pair:
            continue
        if "=" not in pair:
            print(f"ERROR: 非法 --field（缺 =）: {pair!r}", file=sys.stderr)
            sys.exit(1)
        k, v = pair.split("=", 1)
        if not k:
            print("ERROR: 空欄位名", file=sys.stderr)
            sys.exit(1)
        # 重複欄位 → 歧義拒寫（predicate 與落地值不得分離）
        if k in fields:
            print(f"ERROR: 重複欄位: {k}", file=sys.stderr)
            sys.exit(1)
        if v.startswith("@"):
            jtxt = v[1:]
            try:
                parsed = json.loads(jtxt)
            except json.JSONDecodeError as exc:
                print(f"ERROR: --field {k}=@... 非法 JSON: {exc}", file=sys.stderr)
                sys.exit(1)
            # F2：解析後遞迴驗字串值（JSON 轉義繞過 CLI 字元守衛）
            _reject_json_string_values(parsed, k)
            fields[k] = parsed
        else:
            fields[k] = v

# producer 強制覆寫（呼叫端指定即忽略）
fields["producer"] = producer

# 事件合法性
if is_debt:
    if event_name not in debt_events:
        print(f"ERROR: 未知 debt 事件: {event_name}", file=sys.stderr)
        sys.exit(1)
    meta = debt_events[event_name]
    # origin_script：呼叫端可傳；若缺則用 registry 預設；若傳則須合白名單且建議對齊 meta
    origin = fields.get("origin_script")
    if origin is None or origin == "":
        origin = meta.get("origin_script")
        if origin:
            # registry 預設是 runtime 輸入，落地前必須 guard（點名 registry 鍵）
            reg_origin_key = f"debt_events.{event_name}.origin_script"
            _reject_registry_landed_string(origin, reg_origin_key)
            fields["origin_script"] = origin
            registry_sourced["origin_script"] = reg_origin_key
    if fields.get("origin_script") not in allowed_origin:
        print(
            f"ERROR: origin_script 不在 allowed_origin_scripts: {fields.get('origin_script')!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    expected_origin = meta.get("origin_script")
    if expected_origin and fields.get("origin_script") != expected_origin:
        # expected 本身若含行界，先點名 registry（避免誤報「須為 …」）
        _reject_registry_landed_string(
            expected_origin, f"debt_events.{event_name}.origin_script"
        )
        print(
            f"ERROR: origin_script 須為 {expected_origin!r}（事件 {event_name}）",
            file=sys.stderr,
        )
        sys.exit(1)

    # 必填：common（除 event/schema_version/event_id/sequence/producer/ts 由腳本填）+ per-event
    script_owned = {
        "event",
        "schema_version",
        "event_id",
        "sequence",
        "producer",
        "ts",
    }
    missing = []
    for key in required_common:
        if key in script_owned:
            continue
        if key not in fields or fields[key] in (None, ""):
            missing.append(key)
    for key in required_per:
        # 必填＝鍵必須存在。空字串預設視為缺欄；
        # 唯一契約例外（收窄至三者同時成立，P16-B3-FIX 群集 D）：
        #   event == committee_family_result
        #   AND result_state == failed
        #   AND key == output_sha256
        # 理由：避免未來其他事件若也宣告 required output_sha256 時誤吃同一例外。
        # （與 success 的非空 sha 互斥；銷帳只比對 success）。
        if key not in fields or fields[key] is None:
            missing.append(key)
            continue
        if fields[key] == "":
            if (
                event_name == "committee_family_result"
                and key == "output_sha256"
                and fields.get("result_state") == "failed"
            ):
                continue
            missing.append(key)
    # 去重保序
    seen = set()
    missing_u = []
    for m in missing:
        if m not in seen:
            seen.add(m)
            missing_u.append(m)
    if missing_u:
        print(f"ERROR: 缺必填欄: {','.join(missing_u)}", file=sys.stderr)
        sys.exit(1)

    # 枚舉
    for ek, allowed in enums.items():
        if ek in fields and fields[ek] not in allowed:
            print(
                f"ERROR: 欄位 {ek}={fields[ek]!r} 不在枚舉 {allowed}",
                file=sys.stderr,
            )
            sys.exit(1)

    # 腳本擁有欄：event_id 一律由本腳本 mint UUID v4（呼叫端指定即忽略）
    fields["event"] = event_name
    # schema_version 來自 registry：字串型亦可能含行界；int 無字元問題
    _reject_registry_landed_string(schema_version, "schema_version")
    fields["schema_version"] = schema_version
    registry_sourced["schema_version"] = "schema_version"
    fields["sequence"] = next_seq
    fields["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fields["event_id"] = str(uuid.uuid4())
    try:
        uuid.UUID(fields["event_id"])
    except (ValueError, AttributeError, TypeError):
        print(f"ERROR: event_id 非 UUID: {fields['event_id']!r}", file=sys.stderr)
        sys.exit(1)
else:
    if event_name not in legacy_events:
        print(f"ERROR: 未知事件（非 debt 亦非 legacy）: {event_name}", file=sys.stderr)
        sys.exit(1)
    fields["event"] = event_name
    if "ts" not in fields or not fields["ts"]:
        fields["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # legacy 不寫 sequence / 不強制 debt 共用欄

# event_id 全域唯一（debt）
if is_debt:
    eid = fields["event_id"]
    if audit_path.is_file():
        try:
            raw = audit_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: 讀 audit 失敗: {exc}", file=sys.stderr)
            sys.exit(1)
        for line in raw.splitlines():
            s = line.strip()
            if not s.startswith("{"):
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError:
                print("ERROR: audit 含無法解析的 JSON 行", file=sys.stderr)
                sys.exit(1)
            if isinstance(rec, dict) and rec.get("event_id") == eid:
                print(f"ERROR: event_id 重複: {eid}", file=sys.stderr)
                sys.exit(1)

# 落地前最終防線：所有字串無論來源（CLI / JSON / registry / 腳本自填）一律 guard
# （「可信」= 已驗過，不是來源標籤）
_reject_all_landed_strings(fields)

# 確保目錄與檔案
audit_path.parent.mkdir(parents=True, exist_ok=True)
if not audit_path.exists():
    audit_path.touch()

line = json.dumps(fields, ensure_ascii=False, sort_keys=True)
try:
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
except OSError as exc:
    print(f"ERROR: append 失敗: {exc}", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PY
}

# ── 對外入口：原子 predicate+append ──────────────────────
_append_with_absent_guard() {
  # $1=session_name, 其餘未使用（事件欄位已在全域 FIELD_PAIRS）
  local session="$1"
  shift || true

  _acquire_lock || return 2

  _scan_session_locked "${session}"
  case $? in
    0)
      _release_lock
      echo "ERROR: session_name 已存在: ${session}" >&2
      return 1
      ;;
    1) : ;;
    *)
      _release_lock
      return 2
      ;;
  esac

  local next_seq
  next_seq="$(_next_seq_locked)" || {
    local rc=$?
    _release_lock
    return "${rc}"
  }

  _append_event_locked "${next_seq}" 1
  local rc=$?
  _release_lock
  return "${rc}"
}

# ── 一般 append（自行取鎖）────────────────────────────────
_append_normal() {
  local is_debt="$1"
  _acquire_lock || return 2
  local next_seq=0
  if [ "${is_debt}" = "1" ]; then
    next_seq="$(_next_seq_locked)" || {
      local rc=$?
      _release_lock
      return "${rc}"
    }
  fi
  _append_event_locked "${next_seq}" "${is_debt}"
  local rc=$?
  _release_lock
  return "${rc}"
}

# ── 參數解析 ────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --event)
      [ $# -ge 2 ] || die "--event 需要參數"
      # event 名會落地為 JSON 的 event 欄；套用同一套控制字元驗證
      _reject_serialized_control_chars "--event" "$2"
      EVENT_NAME="$2"
      shift 2
      ;;
    --require-absent-session)
      [ $# -ge 2 ] || die "--require-absent-session 需要參數"
      # 旗標一出現即標記；值可為空（稍後 fail-closed），不得以值非空推斷旗標
      # 非空值會進 FIELD_PAIRS / 掃描 predicate，必須與 --field 同一驗證（RS 注入繞唯一性）
      REQUIRE_ABSENT_SET=1
      if [ -n "$2" ]; then
        _reject_serialized_control_chars "--require-absent-session" "$2"
      fi
      REQUIRE_ABSENT_SESSION="$2"
      shift 2
      ;;
    --field)
      [ $# -ge 2 ] || die "--field 需要參數"
      _reject_serialized_control_chars "--field" "$2"
      if [ -n "${FIELD_PAIRS}" ]; then
        FIELD_PAIRS="${FIELD_PAIRS}${FIELD_RS}$2"
      else
        FIELD_PAIRS="$2"
      fi
      shift 2
      ;;
    *)
      die "未知參數: $1"
      ;;
  esac
done

[ -n "${EVENT_NAME}" ] || die "必須指定 --event"
[ -f "${REGISTRY}" ] || die "registry 缺檔: ${REGISTRY}"

# registry JSON 合法
python3 -c 'import json,sys; json.load(open(sys.argv[1],encoding="utf-8"))' "${REGISTRY}" \
  || die "registry JSON 壞: ${REGISTRY}"

AUDIT_PATH="$(_resolve_audit_path)" || exit 1
LOCKDIR="${AUDIT_PATH}.lock"

# 判定 debt vs legacy
IS_DEBT=0
if python3 - "${REGISTRY}" "${EVENT_NAME}" <<'PY'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
name = sys.argv[2]
if name in (reg.get("debt_events") or {}):
    sys.exit(0)
if name in (reg.get("non_debt_legacy_events") or []):
    sys.exit(1)
print(f"ERROR: 未知事件: {name}", file=sys.stderr)
sys.exit(2)
PY
then
  IS_DEBT=1
else
  rc=$?
  if [ "${rc}" -eq 1 ]; then
    IS_DEBT=0
  else
    exit 1
  fi
fi

# --require-absent-session：以 REQUIRE_ABSENT_SET 判定「旗標出現」，不用值非空
# （空字串若用 [ -n ] 會整段跳過唯一性守衛 = CODEX-R2-P1-01）
if [ "${REQUIRE_ABSENT_SET}" = "1" ]; then
  if [ -z "${REQUIRE_ABSENT_SESSION}" ]; then
    die "--require-absent-session 值不可為空（旗標出現即須生效；空值 fail-closed）"
  fi
  if [ "${IS_DEBT}" != "1" ]; then
    die "--require-absent-session 僅適用 debt 事件"
  fi
  # 若呼叫端未帶 session_name，注入；若有則必須一致。
  # 重複 session_name → 歧義拒寫（predicate 與落地值不得分離；CODEX-R1-P1-01）
  _sn_lines="$(printf '%s' "${FIELD_PAIRS}" | tr '\036' '\n' | grep '^session_name=' || true)"
  _sn_count=0
  if [ -n "${_sn_lines}" ]; then
    _sn_count="$(printf '%s\n' "${_sn_lines}" | grep -c .)"
  fi
  if [ "${_sn_count}" -gt 1 ]; then
    die "重複 session_name 欄位（歧義拒寫）"
  fi
  if [ "${_sn_count}" -eq 1 ]; then
    existing="$(printf '%s\n' "${_sn_lines}" | sed 's/^session_name=//')"
    if [ "${existing}" != "${REQUIRE_ABSENT_SESSION}" ]; then
      die "--require-absent-session (${REQUIRE_ABSENT_SESSION}) 與 --field session_name=${existing} 不一致"
    fi
  else
    if [ -n "${FIELD_PAIRS}" ]; then
      FIELD_PAIRS="${FIELD_PAIRS}${FIELD_RS}session_name=${REQUIRE_ABSENT_SESSION}"
    else
      FIELD_PAIRS="session_name=${REQUIRE_ABSENT_SESSION}"
    fi
  fi
  _append_with_absent_guard "${REQUIRE_ABSENT_SESSION}"
  exit $?
fi

_append_normal "${IS_DEBT}"
exit $?
