# _gate_lex.sh — GOVB0 Task 2.0/2.1 詞法契約（由 gate_check.sh Bash 路徑 source）
# 勿直接執行；單一實作供 2.1–2.4 共用。

# ─────────────────────────────────────────────────────────────
# GOVB0 Task 2.0／2.1 詞法契約（單一實作，供 2.1–2.4 共用）
# 契約 11 項：1 引號內分隔符／1b 跨行剝引號／2 命令位置／3 -c·eval 遞迴／
#   4 引號路徑／5 路徑正規化（2.4 完整）／6 未閉合 fail-closed／7 unquoted -c／
#   8 遞迴≤3／9 跳脫引號／10 heredoc 七條機械規則。
# 緊急回退：GATE_LEGACY_DECISION=1 → 舊一線性判定（僅供緊急，非預設）。
# 熱路徑：純 shell／sed／awk，禁 python。
# ─────────────────────────────────────────────────────────────
_GATE_LEX_MAX_DEPTH=3

# 詞法前處理：heredoc body 視為 span（不掃描）＋跨行引號狀態機。
# 引號內的 ; & | 中性化為空白；引號內空白改成 US(\037) 以保留「帶空白路徑」為單一 token。
# stdout＝可掃描文字；rc=0 成功；rc=1 fail-closed（未閉合／無法解析 heredoc／跳脫邊界不明）。
_gate_lex_preprocess() {
  # LC_ALL=C：逐位元組掃描，避免 macOS awk towc 在中文/多位元組上失敗
  printf '%s' "${1-}" | LC_ALL=C awk '
    function fail() { print "FAILCLOSED"; exit 1 }

    # 允許清單 (c)：完整 token 邊界
    function is_allow_delim(s) {
      return (s ~ /^[A-Za-z0-9_.:+=,%@^~{}[\]!*?-]+$/)
    }

    # 自 pos 起解析 <<[-]? 後的 delimiter；成功回 delimiter 字串並設 RSTART 後的 end_pos 到 global _dend
    function parse_heredoc_delim(s, pos,    rest, m, q, i, c, tok, n) {
      rest = substr(s, pos)
      # (a) '\''...'\'' 
      if (match(rest, /^<<[-]?[[:space:]]*'\''([^'\'']*)'\''/)) {
        tok = rest
        sub(/^<<[-]?[[:space:]]*'\''/, "", tok)
        sub(/'\''.*$/, "", tok)
        _dend = pos + RLENGTH - 1
        _hdash = (rest ~ /^<<-/)
        return tok
      }
      # (b) "..."
      if (match(rest, /^<<[-]?[[:space:]]*"/)) {
        i = pos + RLENGTH
        tok = ""
        n = length(s)
        while (i <= n) {
          c = substr(s, i, 1)
          if (c == "\"") { _dend = i; _hdash = (substr(s, pos, 3) ~ /^<<-/); return tok }
          if (c == "\\" && i < n) { tok = tok substr(s, i+1, 1); i += 2; continue }
          tok = tok c; i++
        }
        fail()
      }
      # (c) 允許清單 token
      if (match(rest, /^<<[-]?[[:space:]]*/)) {
        i = pos + RLENGTH
        tok = ""
        n = length(s)
        while (i <= n) {
          c = substr(s, i, 1)
          if (c ~ /[A-Za-z0-9_.:+=,%@^~{}[\]!*?-]/) { tok = tok c; i++; continue }
          break
        }
        if (tok == "" || !is_allow_delim(tok)) fail()
        # 完整 token 邊界：其後須為空白／換行／字串結尾
        if (i <= n) {
          c = substr(s, i, 1)
          if (c != " " && c != "\t" && c != "\n" && c != "\r") fail()
        }
        _dend = i - 1
        _hdash = (substr(s, pos, 3) ~ /^<<-/)
        return tok
      }
      fail()
    }

    BEGIN {
      # 讀入全部（保留換行）
      src = ""
      while ((getline line) > 0) {
        if (src != "") src = src "\n"
        src = src line
      }
      # 若最後有資料但無換行，getline 已含；空輸入
      n = length(src)
      if (n == 0) { print ""; exit 0 }

      # Pass 1：heredoc — 把 body 換成等長空白（保留換行），無法解析 → fail-closed
      out = ""
      i = 1
      while (i <= n) {
        c = substr(src, i, 1)
        # 偵測 <<（非 <<<）
        if (c == "<" && i < n && substr(src, i+1, 1) == "<") {
          # <<< 不是 heredoc
          if (i+2 <= n && substr(src, i+2, 1) == "<") {
            out = out "<<<"
            i += 3
            continue
          }
          delim = parse_heredoc_delim(src, i)
          # 起點 = delimiter 後的下一個換行
          j = _dend + 1
          while (j <= n && substr(src, j, 1) != "\n") {
            out = out substr(src, j, 1)
            j++
          }
          if (j > n) fail()  # 無換行 → 未閉合
          out = out "\n"     # 保留起點換行
          j++                # body 起
          # 消耗 body 直到行首 delimiter
          body_closed = 0
          while (j <= n) {
            # 行首
            line_start = j
            line = ""
            while (j <= n && substr(src, j, 1) != "\n") {
              line = line substr(src, j, 1)
              j++
            }
            # 比對 delimiter
            check = line
            if (_hdash) sub(/^\t+/, "", check)
            if (check == delim) {
              # 終點行：輸出為空白（不掃描），保留結構
              out = out "\n"
              if (j <= n && substr(src, j, 1) == "\n") { out = out; j++ }
              body_closed = 1
              break
            }
            # body 行：換成空白（保留換行）
            for (k = 1; k <= length(line); k++) out = out " "
            if (j <= n && substr(src, j, 1) == "\n") { out = out "\n"; j++ }
          }
          if (!body_closed) fail()
          i = j
          continue
        }
        out = out c
        i++
      }
      src = out
      n = length(src)

      # Pass 2：跨行引號狀態機 — 剝引號、中性化引號內分隔符、空白→US
      out = ""
      inq = 0
      q = ""
      i = 1
      while (i <= n) {
        c = substr(src, i, 1)
        if (inq) {
          if (q == "\"") {
            if (c == "\\") {
              if (i >= n) fail()
              # 跳脫下一字：保留字面（合約 9：不終止 span）
              nxt = substr(src, i+1, 1)
              if (nxt == "\n") { out = out " "; i += 2; continue }  # 續行
              if (nxt == ";" || nxt == "&" || nxt == "|") { out = out " "; i += 2; continue }
              if (nxt == " ") { out = out "\037"; i += 2; continue }
              out = out nxt
              i += 2
              continue
            }
            if (c == "\"") { inq = 0; q = ""; i++; continue }
            if (c == ";" || c == "&" || c == "|") { out = out " "; i++; continue }
            if (c == " " || c == "\t") { out = out "\037"; i++; continue }
            out = out c; i++; continue
          }
          # single quote：無跳脫，只靠 '\'' 終止
          if (c == "'\''") { inq = 0; q = ""; i++; continue }
          if (c == ";" || c == "&" || c == "|") { out = out " "; i++; continue }
          if (c == " " || c == "\t") { out = out "\037"; i++; continue }
          out = out c; i++; continue
        }
        # not in quote
        if (c == "\"" || c == "'\''") { inq = 1; q = c; i++; continue }
        out = out c
        i++
      }
      if (inq) fail()
      print out
    }
  '
}

# 對已前處理的掃描字串做命令位置家族／claude 判定（契約 2；claude 子字串仍為現行，2.2 再收窄）。
# 命中 → rc=0；未命中 → rc=1。
# 錨點字面保留 (codex|cursor-agent|grok|agy)[[:space:]] 與 claude[^|]*(-p|--print) 供覆蓋斷言機械導出。
_gate_lex_match_scan() {
  local s="${1-}"
  # 命令位置：行首 / ; & | ( ` $( && || / eval後 / xargs後；可選路徑前綴（\S*/）
  # 契約 2 擴充（E-3）：含 ( ` $( && || eval xargs
  # 契約 7：家族名後允許 EOS（bash -c codex 無尾空白）——([[:space:]]|$)
  # 錨點字面（覆蓋斷言）：(codex|cursor-agent|grok|agy)[[:space:]] 仍出現於下方 alternation 左枝
  # 家族命中：路徑前綴可選；名後空白或 EOS（契約 7）。
  # 字面 (codex|cursor-agent|grok|agy)[[:space:]] 保留供 family_registry _DRIFT 釘死。
  if printf '%s' "$s" | grep -Eq \
    '(^|[;&|(`]|\$\()[[:space:]]*((eval|xargs)[[:space:]]+)?((\S*/)?)((codex|cursor-agent|grok|agy)[[:space:]]|(codex|cursor-agent|grok|agy)$)'; then
    return 0
  fi
  # 現行 claude 段（Task 2.2 才收窄）；保留字面 claude[^|]*(-p|--print)
  if printf '%s' "$s" | grep -Eq 'claude[^|]*(-p|--print)'; then
    return 0
  fi
  return 1
}

# 自原始 cmd 抽取 (bash|sh|zsh) -c 與 eval 的引數字串（契約 3／7）。
# stdout：每行一個 inner；無則空。
_gate_lex_extract_inners() {
  printf '%s' "${1-}" | LC_ALL=C awk '
    function emit(s) { if (s != "") print s }
    {
      n = length($0); i = 1
      while (i <= n) {
        rest = substr($0, i)
        if (match(rest, /(bash|sh|zsh)[[:space:]]+-c[[:space:]]+/)) {
          j = i + RLENGTH
          if (j > n) break
          ch = substr($0, j, 1)
          if (ch == "\"") {
            j++; tok = ""
            while (j <= n) {
              c = substr($0, j, 1)
              if (c == "\\" && j < n) { tok = tok substr($0, j+1, 1); j += 2; continue }
              if (c == "\"") { emit(tok); i = j + 1; break }
              tok = tok c; j++
            }
            if (j > n && ch == "\"") break
            continue
          }
          if (ch == "'\''") {
            j++; tok = ""
            while (j <= n) {
              c = substr($0, j, 1)
              if (c == "'\''") { emit(tok); i = j + 1; break }
              tok = tok c; j++
            }
            if (j > n) break
            continue
          }
          # unquoted -c（契約 7）
          tok = ""
          while (j <= n) {
            c = substr($0, j, 1)
            if (c == " " || c == "\t" || c == "\n" || c == ";" || c == "&" || c == "|") break
            tok = tok c; j++
          }
          emit(tok)
          i = j
          continue
        }
        # eval 在命令位置（行首或分隔後）
        if (match(rest, /(^|[;&|(`[:space:]]|\$\()eval[[:space:]]+/)) {
          j = i + RLENGTH
          if (j > n) break
          ch = substr($0, j, 1)
          if (ch == "\"") {
            j++; tok = ""
            while (j <= n) {
              c = substr($0, j, 1)
              if (c == "\\" && j < n) { tok = tok substr($0, j+1, 1); j += 2; continue }
              if (c == "\"") { emit(tok); i = j + 1; break }
              tok = tok c; j++
            }
            if (j > n) break
            continue
          }
          if (ch == "'\''") {
            j++; tok = ""
            while (j <= n) {
              c = substr($0, j, 1)
              if (c == "'\''") { emit(tok); i = j + 1; break }
              tok = tok c; j++
            }
            if (j > n) break
            continue
          }
        }
        i++
      }
    }
  '
}

# 抽取 $()／反引號命令替換內容（C3：雙引號內亦會執行，須遞迴判定）。
# 單引號 span 內不抽取（字面）。stdout：每行一個 inner。
_gate_lex_extract_cmdsubs() {
  printf '%s' "${1-}" | LC_ALL=C awk '
    function emit(s) { if (s != "") print s }
    {
      n = length($0); i = 1
      in_sq = 0; in_dq = 0
      while (i <= n) {
        c = substr($0, i, 1)
        if (in_sq) {
          if (c == "'\''") in_sq = 0
          i++; continue
        }
        if (in_dq) {
          if (c == "\\") {
            if (i >= n) break
            i += 2; continue
          }
          if (c == "\"") { in_dq = 0; i++; continue }
          # 雙引號內繼續偵測 $() / backtick（會執行）
        } else {
          if (c == "'\''") { in_sq = 1; i++; continue }
          if (c == "\"") { in_dq = 1; i++; continue }
        }
        # 不在單引號內
        if (c == "$" && i < n && substr($0, i + 1, 1) == "(") {
          j = i + 2; depth = 1; tok = ""
          while (j <= n && depth > 0) {
            cc = substr($0, j, 1)
            if (cc == "(") { depth++; tok = tok cc; j++; continue }
            if (cc == ")") {
              depth--
              if (depth == 0) break
              tok = tok cc; j++; continue
            }
            tok = tok cc; j++
          }
          if (depth == 0) emit(tok)
          i = j + 1
          continue
        }
        if (c == "`") {
          j = i + 1; tok = ""
          while (j <= n) {
            cc = substr($0, j, 1)
            if (cc == "\\") {
              if (j < n) { tok = tok substr($0, j + 1, 1); j += 2; continue }
              break
            }
            if (cc == "`") { emit(tok); break }
            tok = tok cc; j++
          }
          i = j + 1
          continue
        }
        i++
      }
    }
  '
}

# D-1：整條是否為 gate 自呼叫（命令位置；非子字串嵌入）。
# 命中 → rc=0（應 ALLOW）；未命中 → rc=1。
# 形態：可選 bash|sh|zsh + 可選路徑前綴 + scripts/gate.sh|gate_check.sh + 參數；
# 整條不得含未引號命令分隔符 ;|& 或換行（避免 `gate…; codex` 被誤當自呼叫）。
_gate_cmd_is_self_gate() {
  local s="${1-}"
  # 禁複合命令（分隔符／換行）——自呼叫必須是單一簡單命令
  if printf '%s' "$s" | grep -Eq '[;&|`]|\$\(|\n'; then
    return 1
  fi
  # 命令位置：行首可選 interpreter，後接 scripts/gate(_check)?.sh
  printf '%s' "$s" | grep -Eq \
    '^(bash|sh|zsh)[[:space:]]+([^[:space:]]*/)?scripts/gate(_check)?\.sh([[:space:]]|$)|^([^[:space:]]*/)?scripts/gate(_check)?\.sh([[:space:]]|$)'
}

# 完整判定：cmd 是否為 dispatch 通道（命中 → rc=0）。
# depth 從 0 起；逾 _GATE_LEX_MAX_DEPTH → fail-closed 視同命中。
# D-2／C1：無字元長硬頂。O(n) 路徑＝
#   (1) 無引號／heredoc／反引號時略過 awk 前處理（避免 O(n²) 拼接），直接 grep 掃 raw；
#   (2) 有特殊字元才走 _gate_lex_preprocess（含 heredoc fail-closed）；
#   (3) -c／eval／cmdsub 僅在結構字樣存在時抽取（避 MB 級空轉）。
# 家族名判定只在 _gate_lex_match_scan（已 pin SoT）；此處不另寫家族清單。
# 禁子字串型「gate 逃生口」與長度截斷 ALLOW。
_gate_cmd_is_dispatch() {
  local cmd="${1-}"
  local depth="${2:-0}"
  local scan inner inners raw cmdsubs

  # 契約 8：遞迴上限 3；逾限 fail-closed（BLOCK）
  if [ "$depth" -gt "$_GATE_LEX_MAX_DEPTH" ]; then
    return 0
  fi

  raw="$cmd"

  # 引號／heredoc／反引號 → 需詞法前處理（中性化引號內分隔符；heredoc 無法解析 → FAILCLOSED）
  if printf '%s' "$raw" | grep -Eq "['\"\`]" || printf '%s' "$raw" | grep -Fq '<<'; then
    scan="$(_gate_lex_preprocess "$raw" 2>/dev/null)" || return 0
    case "$scan" in
      FAILCLOSED*) return 0 ;;
    esac
  else
    scan="$raw"
  fi

  if _gate_lex_match_scan "$scan"; then
    return 0
  fi

  # 契約 3／7：-c 與 eval 引數遞迴（僅在有 -c／eval 結構字樣時抽取）
  if printf '%s' "$raw" | grep -Eq '(bash|sh|zsh)[[:space:]]+-c|(^|[[:space:];&|(`])eval[[:space:]]'; then
    inners="$(_gate_lex_extract_inners "$raw")"
    if [ -n "$inners" ]; then
      while IFS= read -r inner; do
        [ -n "$inner" ] || continue
        if _gate_cmd_is_dispatch "$inner" "$((depth + 1))"; then
          return 0
        fi
      done <<GATE_INNER_EOF_7f3a
$inners
GATE_INNER_EOF_7f3a
    fi
  fi

  # C3：雙引號內 $()／反引號會執行 → 抽取後遞迴（僅在有 $()/` 時）
  if printf '%s' "$raw" | grep -Eq '\$\(|`'; then
    cmdsubs="$(_gate_lex_extract_cmdsubs "$raw")"
    if [ -n "$cmdsubs" ]; then
      while IFS= read -r inner; do
        [ -n "$inner" ] || continue
        if _gate_cmd_is_dispatch "$inner" "$((depth + 1))"; then
          return 0
        fi
      done <<GATE_CMDSUB_EOF_9c2b
$cmdsubs
GATE_CMDSUB_EOF_9c2b
    fi
  fi

  return 1
}
