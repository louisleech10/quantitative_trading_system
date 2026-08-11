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
          c = CH(i)
          if (c == "\"") { _dend = i; _hdash = (substr(s, pos, 3) ~ /^<<-/); return tok }
          if (c == "\\" && i < n) { tok = tok CH(i+1); i += 2; continue }
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
          c = CH(i)
          if (c ~ /[A-Za-z0-9_.:+=,%@^~{}[\]!*?-]/) { tok = tok c; i++; continue }
          break
        }
        if (tok == "" || !is_allow_delim(tok)) fail()
        # 完整 token 邊界：其後須為空白／換行／字串結尾
        if (i <= n) {
          c = CH(i)
          if (c != " " && c != "\t" && c != "\n" && c != "\r") fail()
        }
        _dend = i - 1
        _hdash = (substr(s, pos, 3) ~ /^<<-/)
        return tok
      }
      fail()
    }

    # ── O(n) 累加輔助（B3R C-5；E-2 之修法）────────────────────────────
    # 病：`s = s c` 逐字元累加，awk 每次都重配置並複製整條字串 ⇒ O(n²)。
    #     實測（本機）：引號內 100K → 1s、200K → 5s、500K → 逾時。
    # 解：兩層 chunk。先累到 _cb（≤ _CHUNK），滿了推進 _parts[]；取值時才一次接起來。
    #     單次 append 成本 O(1) 攤銷；最終 join 為 O(n · parts) 但 parts ≈ n/_CHUNK，
    #     500K → 61 段，join 約 1500 萬字元複製，實測仍在毫秒級。
    # 🔴 語義逐字不變：呼叫端只是把 `x = x y` 換成 `ACC_ADD(name, y)`。
    function ACC_RESET(a) { _cb[a] = ""; _pn[a] = 0; _tl[a] = 0 }
    function ACC_ADD(a, s) {
      _cb[a] = _cb[a] s
      _tl[a] += length(s)
      if (length(_cb[a]) >= 128) { _parts[a, ++_pn[a]] = _cb[a]; _cb[a] = "" }
    }
    # 已累加的總長度。存在的唯一理由：讓呼叫端能問「到目前為止是不是還是空的」，
    # 而不必先把整條字串接出來（接出來就是 O(n²)，正是要避免的事）。
    function ACC_LEN(a) { return _tl[a] + 0 }
    # 🔴 取值採**兩兩合併**（log 深度），不可改回線性 for 迴圈串接：
    #    線性串接是 O(n · parts)；parts ≈ n/C 時又變成 O(n²/C)。
    #    C 取小（128）壓低 append 的複製量，合併深度靠 log 補回來。
    #    500K：parts ≈ 3900，深度 ≈ 12，總複製 ≈ 6M 字元（線性版是 ≈ 10 億）。
    function ACC_GET(a,   i, m, np) {
      np = _pn[a]
      if (_cb[a] != "") { _parts[a, ++np] = _cb[a]; _cb[a] = ""; _pn[a] = np }
      if (np == 0) return ""
      while (np > 1) {
        m = 0
        for (i = 1; i + 1 <= np; i += 2) _parts[a, ++m] = _parts[a, i] _parts[a, i + 1]
        if (i == np) _parts[a, ++m] = _parts[a, np]
        np = m
      }
      _pn[a] = 1
      return _parts[a, 1]
    }

    # ── 視窗存取 ＋ 批次跳躍（B3R Phase 3；C-5 之修法）────────────────────
    #
    # 🔴 Phase 2 收據把瓶頸判成「每字元一次 awk 函式呼叫」，**本輪實測推翻**。
    #    真正的根因是 substr 本身。決定性實驗 probe_substr.sh：
    #      **固定 5 萬次** substr(s, i, 1)，只改來源長度
    #        50K → 0.10s ／ 100K → 0.21s ／ 200K → 0.61s ／ 400K → 2.02s
    #      同樣 5 萬次但改對 1KB 小視窗切 ⇒ 與來源長度**無關**
    #    ⇒ BWK awk 的 substr() 成本正比於**來源字串總長**（內含一次 strlen）。
    #      逐字掃一個 n 字元字串，光 substr 就是 O(n²)，與字串累加無關。
    #      算術對得上：250K 次 × 500KB ≈ 125GB ÷ ~10GB/s ≈ 12.5s，實測 12.79s。
    #      Phase 2 把 29s→11s 歸功於 ACC_*，其實只換掉了另一半的 O(n²)。
    #
    # 兩件事合起來才夠：
    #   ① **視窗**：一次切 _wsz 位元組，其後只對小字串 substr（CH/SLICE/NEXT_OF）。
    #      _wsz 取 ≈sqrt(n)：逐字成本 n·W 與換窗成本 n²/W 在此平衡。
    #   ② **批次跳躍**：一次跳到「下一個真的需要逐字決策的字元」，中間整段搬移。
    #      只有 ① 沒有 ②，全無趣的 500K 仍要跑 50 萬次迭代。
    #
    # 🔴 用 index() 而非 match()＋動態 regex：字面搜尋，順帶免掉 bracket 內反斜線的
    #    跳脫層數問題（那個假設本輪已實測踩過一次）。
    #    ⚠️ 但**單獨改成 index() 對效能毫無幫助**（對抗性語料 12.79s → 12.88s）。
    #    主委原先猜「動態 regex 每次重編譯」，實測直接推翻——記在這裡是為了
    #    讓下一手不要再走這條死路。
    #
    # 🔴 視窗綁定**全域 src**（非參數）：任何對 src 的再賦值後**必須** WIN_RESET()，
    #    否則會讀到上一個字串的殘影。全檔只有 Pass 1→Pass 2 之交界會改 src。
    #    （mutation `no_win_reset` 就在釘死這一條。）
    function WIN_RESET() { _wbase = 0; _wlen = 0; _win = "" }
    function WIN_AT(pos) {
      if (pos < _wbase || pos >= _wbase + _wlen) {
        _wbase = pos
        _win = substr(src, pos, _wsz)
        _wlen = length(_win)
      }
    }
    # 取 src 的第 pos 個字元（1-based）；pos 超界回空字串，與 substr 語義一致。
    function CH(pos) {
      if (pos < 1 || pos > n) return ""
      WIN_AT(pos)
      return substr(_win, pos - _wbase + 1, 1)
    }
    # 取 src[from .. from+len-1]，同樣經視窗組出，避免對整條 src 做 substr。
    # 🔴 直接寫 substr(src, from, len) 會付一次 O(n) strlen；heredoc 逐行切片
    #    在「多行短 body」上就會退回 O(n²)。
    # 語義恆等於 substr(src, from, len)；差別只在「短切片走視窗、不付 O(n) strlen」。
    function SLICE(from, len,    take) {
      if (len <= 0 || from > n) return ""
      # 一次性大切片：直接切。單次 O(n) 不是問題——要避免的是**逐字／逐行重複付費**。
      if (len > _wsz) return substr(src, from, len)
      WIN_AT(from)
      take = _wbase + _wlen - from
      if (take >= len) return substr(_win, from - _wbase + 1, len)
      return substr(src, from, len)   # 跨視窗邊界（每次換窗至多一次）
    }
    # 回傳：pos 起（含）第一個命中 c1/c2/c3 的位置；其後全無趣則回 0。c2/c3 可留空。
    function NEXT_OF(pos, c1, c2, c3,    chunk, r, p) {
      while (pos <= n) {
        WIN_AT(pos)
        chunk = substr(_win, pos - _wbase + 1)
        r = index(chunk, c1)
        if (c2 != "") { p = index(chunk, c2); if (p > 0 && (r == 0 || p < r)) r = p }
        if (c3 != "") { p = index(chunk, c3); if (p > 0 && (r == 0 || p < r)) r = p }
        if (r > 0) return pos + r - 1
        pos = _wbase + _wlen
        if (_wlen < _wsz) break
      }
      return 0
    }

    # 引號 span 內的**無狀態**字元映射——**本函式是這個映射的唯一定義**
    # （批次快路徑餵整段、逐字分支餵單一字元，兩邊都呼叫它）：
    #   ; & |          → 單一空白（中性化分隔符）
    #   SP TAB LF      → US(\037)（保留「帶空白路徑」為單一 token）
    #   其餘（含 CR）  → 原樣
    #
    # B7：引號內換行亦為**引數內的空白**，與空白/tab 同樣中性化為 US。
    # 不這麼做的話 grep 逐行比對會把同一個指令拆到兩行，
    # 使「名稱＋旗標」兩 token 規則（claude 段）漏放真派工。
    # 🔴 順序不可對調：先做空白→US，再做 ;&|→空白。
    #    反過來會把剛換成空白的 ;&| 再換成 US，與逐字分支不符（; 應得真空白）。
    # 🔴 呼叫端**必須分段**餵（每段 ≤ _wsz）：實測 awk 的 gsub 是 O(m²)
    #    （probe_gsub.sh：100K→0.12s、200K→0.5s、400K→1.6s、800K→6.4s，長度加倍耗時 4 倍）。
    #    整段引號 span 一次做，500K 要 2.9s、4MB 會退化到分鐘級。
    function XFORM_Q(t) {
      gsub(/[ \t\n]/, "\037", t)
      gsub(/[;&|]/, " ", t)
      return t
    }

    BEGIN {
      SQ = sprintf("%c", 39)
      # 讀入全部（保留換行）——同樣走 chunk 累加，避免 `src = src line` 的 O(n²)
      # 🔴 條件必須是「已累加的內容非空」，**不可**改成「不是第一行」。
      #    HEAD 版寫的是 `if (src != "") src = src "\n"`：輸入以空行開頭時
      #    src 一直是空的 ⇒ 前導換行會被**丟掉**。Phase 2 的機械改寫換成 _first 旗標，
      #    等於偷偷改了語義（前導換行變成保留）。
      #    12000 例 fuzz 差分抓到 233 例（判定 rc 全同、只有前處理文字不同）。
      #    本批是效能重構 ⇒ 一律還原成與 HEAD 逐位元組相同；
      #    「舊行為丟掉前導換行是否本身就該修」另立票，不在本批夾帶。
      ACC_RESET("src")
      while ((getline line) > 0) {
        if (ACC_LEN("src") != 0) ACC_ADD("src", "\n")
        ACC_ADD("src", line)
      }
      src = ACC_GET("src")
      # 若最後有資料但無換行，getline 已含；空輸入
      n = length(src)
      if (n == 0) { print ""; exit 0 }
      # 視窗大小取 ≈sqrt(n)（逐字成本 n·W 與換窗成本 n²/W 的平衡點），夾在 [256, 65536]
      _wsz = int(sqrt(n)) + 128
      if (_wsz < 256) _wsz = 256
      if (_wsz > 65536) _wsz = 65536
      WIN_RESET()

      # Pass 1：heredoc — 把 body 換成等長空白（保留換行），無法解析 → fail-closed
      ACC_RESET("out")
      i = 1
      while (i <= n) {
        # 批次跳過：非 < 的字元在本 pass 一律走最下方的「原樣輸出並 i++」，
        # 不分狀態、無例外 ⇒ 可整段搬移。（唯一分支條件就是 c == "<"。）
        np = NEXT_OF(i, "<", "", "")
        if (np == 0) { ACC_ADD("out", SLICE(i, n - i + 1)); break }
        if (np > i) { ACC_ADD("out", SLICE(i, np - i)); i = np }
        c = CH(i)
        # 偵測 <<（非 <<<）
        if (c == "<" && i < n && CH(i+1) == "<") {
          # <<< 不是 heredoc
          if (i+2 <= n && CH(i+2) == "<") {
            ACC_ADD("out", "<<<")
            i += 3
            continue
          }
          delim = parse_heredoc_delim(src, i)
          # 起點 = delimiter 後的下一個換行
          # delimiter 之後、換行之前的殘餘（原樣輸出）——整段搬移，不逐字
          j = _dend + 1
          eol = NEXT_OF(j, "\n", "", "")
          if (eol == 0) fail()  # 無換行 → 未閉合
          if (eol > j) ACC_ADD("out", SLICE(j, eol - j))
          j = eol
          ACC_ADD("out", "\n")     # 保留起點換行
          j++                # body 起
          # 消耗 body 直到行首 delimiter
          body_closed = 0
          while (j <= n) {
            # 行首
            line_start = j
            eol = NEXT_OF(j, "\n", "", "")
            j = (eol == 0) ? n + 1 : eol
            line = SLICE(line_start, j - line_start)
            # 比對 delimiter
            check = line
            if (_hdash) sub(/^\t+/, "", check)
            if (check == delim) {
              # 終點行：輸出為空白（不掃描），保留結構
              ACC_ADD("out", "\n")
              if (j <= n && CH(j) == "\n") { j++ }
              body_closed = 1
              break
            }
            # body 行：換成空白（保留換行）
            # body 行 → 等長空白：一次配置，不逐字（sprintf 寬度 0 得空字串）
            if (length(line) > 0) ACC_ADD("out", sprintf("%*s", length(line), ""))
            if (j <= n && CH(j) == "\n") { ACC_ADD("out", "\n"); j++ }
          }
          if (!body_closed) fail()
          i = j
          continue
        }
        ACC_ADD("out", c)
        i++
      }
      src = ACC_GET("out")
      n = length(src)
      # 🔴 src 換了一條字串 ⇒ 視窗必須作廢，否則 CH()/NEXT_OF() 會讀到 Pass 1 的殘影。
      WIN_RESET()

      # Pass 2：跨行引號狀態機 — 剝引號、中性化引號內分隔符、空白→US
      ACC_RESET("out")
      inq = 0
      q = ""
      i = 1
      while (i <= n) {
        # ── 批次跳過本狀態下**不需逐字決策**的區段 ──────────────────────
        # 三種狀態各自只有下列字元會改變控制流；其餘字元的處理是**無狀態映射**：
        #   引號外  ：雙引號、單引號、反斜線（其餘一律原樣輸出並 i++）
        #   雙引號內：雙引號、反斜線      （其餘走 XFORM_Q 的映射表）
        #   單引號內：單引號              （同上；單引號無跳脫）
        # ⇒ 可一次跳到下一個上述字元，中間整段搬移＋一次 gsub 映射。
        # 🔴 下方逐字分支**一行未動**：本區塊是純新增的快路徑，
        #    狀態機語義仍以下方分支為準（差分驗證＋fuzz 對照即在證明兩者等價）。
        if (inq) {
          if (q == "\"") np = NEXT_OF(i, "\"", "\\", "")
          else           np = NEXT_OF(i, SQ, "", "")
        } else           np = NEXT_OF(i, "\"", SQ, "\\")
        if (np == 0) np = n + 1
        if (np > i) {
          # 🔴 每段 ≤ _wsz：XFORM_Q 的 gsub 是 O(m²)，整段一次做會在大 span 上退化。
          while (i < np) {
            seg = np - i
            if (seg > _wsz) seg = _wsz
            run = SLICE(i, seg)
            if (inq) run = XFORM_Q(run)
            ACC_ADD("out", run)
            i += seg
          }
          if (i > n) break
        }
        c = CH(i)
        if (inq) {
          if (q == "\"") {
            if (c == "\\") {
              if (i >= n) fail()
              # 跳脫下一字：保留字面（合約 9：不終止 span）
              nxt = CH(i+1)
              if (nxt == "\n") { ACC_ADD("out", " "); i += 2; continue }  # 續行
              if (nxt == ";" || nxt == "&" || nxt == "|") { ACC_ADD("out", " "); i += 2; continue }
              if (nxt == " ") { ACC_ADD("out", "\037"); i += 2; continue }
              ACC_ADD("out", nxt)
              i += 2
              continue
            }
            if (c == "\"") { inq = 0; q = ""; i++; continue }
            # 🔴 引號內的字元映射**只有 XFORM_Q 一個定義**，單字元也走它。
            #   原本這裡有三行 if 與 XFORM_Q 內容重複；重複＝兩處會漂，
            #   而且 mutation 只改一處就測不出東西（本輪 MUT-g 實際發生：
            #   把逐字分支的 \n 拿掉，快路徑仍照常中性化 ⇒ 該 mutation 失去鑑別力）。
            ACC_ADD("out", XFORM_Q(c)); i++; continue
          }
          # single quote：無跳脫，只靠 '\'' 終止
          if (c == "'\''") { inq = 0; q = ""; i++; continue }
          ACC_ADD("out", XFORM_Q(c)); i++; continue
        }
        # not in quote
        # B7：反斜線續行 —— bash 直接移除 \<LF>（`claude \`+LF+`-p x` 等同 `claude -p x`）。
        # 保留原樣會讓兩個 token 落在不同 grep 行而漏放。
        if (c == "\\" && i < n && CH(i+1) == "\n") { i += 2; continue }
        # B7〔CODEX-STAMP-R1 NEW-P0-02b〕：引號外的 \X 依 bash 語意「去掉反斜線、保留 X」。
        # 不這麼做的話 `clau\de -p x` 會逃掉——它執行起來就是 claude。
        # 代價：`echo \; codex exec x` 這種被跳脫的分隔符會被當成真分隔符 ⇒ 誤擋（fail-closed）。
        if (c == "\\" && i < n) { ACC_ADD("out", CH(i+1)); i += 2; continue }
        if (c == "\"" || c == "'\''") { inq = 1; q = c; i++; continue }
        ACC_ADD("out", c)
        i++
      }
      if (inq) fail()
      print ACC_GET("out")
    }
  '
}

# 對已前處理的掃描字串做命令位置家族／claude 判定（契約 2）。
# 命中 → rc=0；未命中 → rc=1。
# 錨點字面保留 (codex|cursor-agent|grok|agy)[[:space:]] 供覆蓋斷言機械導出。
# claude 段自 GOVB0 Task 2.2／GOVB1 Task 3.2 起改為命令位置判定，見該段註解。
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
  # claude 段收窄 — GOVB0 Task 2.2 ＝ GOVB1 Task 3.2（同一件工作的兩個編號，票 B-26）。
  #
  # 舊式 claude[^|]*(-p|--print) 是**子字串比對**：`.claude/` 治理目錄與
  # /private/tmp/claude-501/ scratchpad 只要同句出現 rev-parse／--porcelain／-print，
  # 其中的 -p／--p 就被當成旗標 ⇒ 四種現場唯讀指令被誤擋（TEST-2.2-FP4）。
  #
  # 收窄後兩個條件同時成立才命中：
  #   ① claude 須在**命令位置**（可帶路徑前綴 (\S*/)?；與家族名同一套位置定義）
  #   ② -p／--print 須為**獨立 token 起始**，且在 claude **之後**、
  #      **同一分隔符區段內**（[^;&|]* 不跨 ; & |）
  #
  # 🔴 ② 為何是「token 起始」而非 TODO 實作要點的 grep -qx 全等：
  #   全等會使 `claude -p"do it"`（shell 併為單一 token -pdo…）由現行 BLOCK 退化為 ALLOW
  #   ＝ 收窄型修法造成「該擋的從此不受檢」，硬規矩 9 明文禁止。
  #   TODO 該處 _has_flag() 屬參考實作；其**目標**（不得命中 rev-parse／--porcelain／
  #   -print 子字串）在本式下仍成立：三者皆非 token 起始的 -p／--print
  #   （--porcelain 起始為 --po；rev-parse 之 -p 前接 v；-print 僅在 claude
  #   不在命令位置的指令中出現，永遠到不了 ② 這一關）。
  #
  # 🔴 長短旗標的**不對稱**是可導出的，不是任意收放〔CODEX-R1-P1-03：--printable 不應命中〕：
  #   · 短旗標 `-p`：POSIX 短選項的值**可直接併寫**（`-pfoo`）⇒ 必須 prefix-open，
  #     否則 `claude -p"do it"` 漏放（硬規矩 9）。代價＝`-print` 這種同前綴 token 亦命中，
  #     但那只在 claude 已位於命令位置時才判，屬 fail-closed 且無實際誤擋。
  #   · 長旗標 `--print`：GNU 長選項的值只能以 `=` 或另一個 token 給
  #     ⇒ 後面必須是 `=`／空白／行尾，`--printable`／`--printer` 一律不命中。
  if printf '%s' "$s" | grep -Eq \
    '(^|[;&|(`]|\$\()[[:space:]]*((eval|xargs)[[:space:]]+)?((\S*/)?)claude([[:space:]][^;&|]*)?[[:space:]](-p|--print([[:space:]=]|$))'; then
    return 0
  fi
  # 🔴 fail-closed 網 — 命令名由**展開**產生時，靜態詞法決定不了真正的 argv[0]。
  # 〔出處 CODEX-R1-P0-01：`$(printf claude) -p x` 與 `claude${IFS}-p x` 在收窄前
  #   被舊式子字串比對**偶然擋住**，只靠命令位置判定會使兩者由 BLOCK 退化為 ALLOW
  #   ＝ 硬規矩 9 禁止的回歸。〕
  # 判準（stamp-r1 收窄）：**命令位置的那個 token** 含展開／萬用字元 metachar
  # ⇒ argv[0] 無法靜態決定 ⇒ 退回舊式子字串比對，寧誤擋不漏放。
  #
  # 🔴 為何是「命令位置的 token」而非「整條指令」〔CODEX-STAMP-R1 NEW-P2-04c〕：
  #   初版用「整條含 $ 或反引號」當觸發，有兩個病：
  #   ① 太窄——`!claude -p x` 不含 $／反引號，卻在收窄前被舊式擋住 ⇒ **回歸**。
  #   ② 太寬——`echo "$(cat .claude/tmp/x)"; git rev-parse HEAD` 這種
  #      命令名明明是 echo／git 的唯讀指令被誤擋。
  #   改判「命令位置 token 是否可能被展開」後兩病同時消失：只有 argv[0] 會變成別的東西時才退回。
  #
  # metachar 集合＝可改變 argv[0] 的展開／萬用字元（封閉集合，非黑名單式列舉）：
  #   $ (參數/命令替換)　` (命令替換)　! (history)　* ? [ (glob)　~ (tilde)
  #   反斜線不在此列——它已在前處理被依 bash 語意消掉。
  if printf '%s' "$s" | grep -Eq \
      '(^|[;&|(`]|\$\()[[:space:]]*((eval|xargs)[[:space:]]+)?[^[:space:];&|]*[$`!*?~[]' \
    && printf '%s' "$s" | grep -Eq 'claude[^|]*(-p|--print)'; then
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
  # 🔴 RS="\001" ⇒ 整份輸入視為**單一 record**，命令替換得以跨行抽取
  # 〔CODEX-STAMP-R1 NEW-P0-01：`cat <<EOF\n$(claude "a\nb" -p x)\nEOF` 原本因逐行掃描
  #   找不到右括號而整條漏放；heredoc body 在 Pass 1 被遮蔽，這裡是唯一還看得到它的地方〕。
  # emit 時把換行換成 `;` 而非空白：`;` 保留命令位置語意，
  # 空白會把 `$(echo hi\ncodex exec x)` 的第二行降級為引數而漏放。
  printf '%s' "${1-}" | LC_ALL=C awk -v RS='\001' '
    function emit(s) { if (s != "") { gsub(/\n/, ";", s); print s } }
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
  # 🔴 控制字元（含換行、CR）必須在 grep 之外判〔CODEX-R1-P0-01，主委獨立複驗〕：
  #   前版寫 `grep -Eq '…|\n'`，宣稱「禁換行」但**完全沒有作用**——兩個獨立原因：
  #     ① grep 逐「行」比對，換行永遠不可能出現在一行之內；ERE 的 `\n` 也不是換行
  #     ② 下方 `^…` 錨點同樣是逐行 ⇒ 只要**任何一行**長得像 gate 自呼叫就整條放行
  #   合起來的後果是真旁路：`bash scripts/gate.sh` ⏎ `<家族> exec …` ⇒ gate rc=0（放行）。
  #   對照組（無前綴／改 `;` 分隔）皆 rc=2，證明缺口專屬於換行路徑。
  #   CR（\r）不切行且屬 [[:space:]]；**實測 bash 不把 CR 當命令分隔符**
  #   （`printf 'echo A\recho B\n' | bash` → 單一引數），故非旁路，但一併拒以免歧義。
  #   ⇒ 一律逐 byte 拒 C0 控制字元（保留 tab）與 DEL；非 ASCII（如中文 --intent）不受影響。
  #   🔴 用 `wc -c` 數位元組，**不可**寫成 `[ -n "$(… tr -dc …)" ]`：
  #   命令替換會吃掉尾端換行，而這裡殘留的唯一字元往往正是換行 ⇒ 判成空 ⇒ 放行。
  #   （主委第一版修法就是這樣寫的，探針照樣 rc=0，改用位元組計數才真的擋住。）
  if [ "$(printf '%s' "$s" | LC_ALL=C tr -dc '\1-\10\12-\37\177' | wc -c | tr -d ' ')" != "0" ]; then
    return 1
  fi
  # 禁複合命令（分隔符）——自呼叫必須是單一簡單命令
  if printf '%s' "$s" | grep -Eq '[;&|`]|\$\('; then
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

  # 引號／heredoc／反引號／**反斜線** → 需詞法前處理
  # （中性化引號內分隔符；heredoc 無法解析 → FAILCLOSED）
  # 🔴 反斜線加入觸發條件〔CODEX-STAMP-R1 NEW-P0-02b／NEW-P0-03〕：
  #   `clau\de -p x` 與 `claude \<CR><LF>-p x` 都不含引號，原本整個跳過前處理，
  #   跳脫語意就永遠沒被解過 ⇒ 逃掉。
  if printf '%s' "$raw" | grep -Eq "['\"\`\\\\]" || printf '%s' "$raw" | grep -Fq '<<'; then
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
