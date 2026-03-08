#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run/dev"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"
LIVE_BACKEND_PID=""
LIVE_FRONTEND_PID=""

mkdir -p "$RUN_DIR"

is_pid_running() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

read_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    tr -d '[:space:]' < "$pid_file"
  fi
}

port_in_use() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

port_pids() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

stop_pid_gracefully() {
  local pid="$1"

  if ! is_pid_running "$pid"; then
    return
  fi

  kill "$pid" >/dev/null 2>&1 || true
  for _ in {1..20}; do
    if ! is_pid_running "$pid"; then
      break
    fi
    sleep 0.2
  done

  if is_pid_running "$pid"; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
}

stop_external_on_port() {
  local name="$1"
  local port="$2"
  local match_regex="$3"
  local force_any="${4:-0}"
  local found=0

  while IFS= read -r pid; do
    [[ -z "${pid:-}" ]] && continue
    found=1

    local cmd
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"

    if [[ "$force_any" == "1" ]] || [[ "$cmd" =~ $match_regex ]]; then
      echo "[$name] stopping external process on port $port (pid=$pid)"
      stop_pid_gracefully "$pid"
    else
      echo "[$name] external process on port $port not matched, keep running (pid=$pid)"
      echo "[$name] command: $cmd"
      echo "[$name] tip: use ./dev_stack stop-force to force stop all listeners on managed ports"
    fi
  done < <(port_pids "$port")

  if [[ "$found" == "0" ]]; then
    echo "[$name] no external process on port $port"
  fi
}

start_backend() {
  local pid
  pid="$(read_pid "$BACKEND_PID_FILE" || true)"
  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    echo "[backend] already running (pid=$pid)"
    return
  fi

  if port_in_use 8000; then
    echo "[backend] port 8000 is already in use, skip start"
    return
  fi

  echo "[backend] starting..."
  (
    cd "$ROOT_DIR"
    nohup "$ROOT_DIR/venv/bin/python" "$ROOT_DIR/run_api.py" > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
  )

  sleep 1
  pid="$(read_pid "$BACKEND_PID_FILE" || true)"
  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    echo "[backend] started (pid=$pid, log=$BACKEND_LOG)"
    echo "[backend] tip: use ./dev_stack logs-back-live to follow live logs"
  else
    echo "[backend] failed to start, check log: $BACKEND_LOG"
  fi
}

start_frontend() {
  local pid
  pid="$(read_pid "$FRONTEND_PID_FILE" || true)"
  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    echo "[frontend] already running (pid=$pid)"
    return
  fi

  if port_in_use 3000; then
    echo "[frontend] port 3000 is already in use, skip start"
    return
  fi

  echo "[frontend] starting..."
  (
    cd "$ROOT_DIR/frontend"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )

  sleep 1
  pid="$(read_pid "$FRONTEND_PID_FILE" || true)"
  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    echo "[frontend] started (pid=$pid, log=$FRONTEND_LOG)"
    echo "[frontend] tip: use ./dev_stack logs-front-live to follow live logs"
  else
    echo "[frontend] failed to start, check log: $FRONTEND_LOG"
  fi
}

stop_by_pid_file() {
  local name="$1"
  local pid_file="$2"
  local pid
  pid="$(read_pid "$pid_file" || true)"

  if [[ -z "${pid:-}" ]]; then
    echo "[$name] not running (no pid file)"
    return
  fi

  if is_pid_running "$pid"; then
    echo "[$name] stopping (pid=$pid)..."
    kill "$pid" >/dev/null 2>&1 || true

    for _ in {1..20}; do
      if ! is_pid_running "$pid"; then
        break
      fi
      sleep 0.2
    done

    if is_pid_running "$pid"; then
      echo "[$name] force killing (pid=$pid)..."
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  else
    echo "[$name] stale pid file found (pid=$pid), cleaning up"
  fi

  rm -f "$pid_file"
  echo "[$name] stopped"
}

status_one() {
  local name="$1"
  local pid_file="$2"
  local port="$3"
  local pid
  pid="$(read_pid "$pid_file" || true)"

  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    echo "[$name] running (pid=$pid)"
  elif port_in_use "$port"; then
    echo "[$name] running on port $port (external process, no pid file)"
  else
    echo "[$name] stopped"
  fi
}

show_logs() {
  local target="${1:-all}"
  case "$target" in
    backend)
      tail -n 60 "$BACKEND_LOG"
      ;;
    frontend)
      tail -n 60 "$FRONTEND_LOG"
      ;;
    all)
      echo "===== backend log (tail -n 40) ====="
      tail -n 40 "$BACKEND_LOG" 2>/dev/null || true
      echo
      echo "===== frontend log (tail -n 40) ====="
      tail -n 40 "$FRONTEND_LOG" 2>/dev/null || true
      ;;
    *)
      echo "Usage: $0 logs [backend|frontend|all]"
      exit 1
      ;;
  esac
}

follow_logs() {
  local target="${1:-all}"
  case "$target" in
    backend)
      echo "[logs] following backend log (Ctrl+C to stop)"
      tail -n 60 -f "$BACKEND_LOG"
      ;;
    frontend)
      echo "[logs] following frontend log (Ctrl+C to stop)"
      tail -n 60 -f "$FRONTEND_LOG"
      ;;
    all)
      echo "[logs] following backend + frontend logs (Ctrl+C to stop)"
      tail -n 40 -f "$BACKEND_LOG" "$FRONTEND_LOG"
      ;;
    *)
      echo "Usage: $0 logs-live [backend|frontend|all]"
      exit 1
      ;;
  esac
}

watch_status() {
  echo "[status] watching backend/frontend status (Ctrl+C to stop)"
  while true; do
    if [[ -t 1 ]]; then
      printf "\033c"
    fi
    date '+%Y-%m-%d %H:%M:%S'
    status_one "backend" "$BACKEND_PID_FILE" "8000"
    status_one "frontend" "$FRONTEND_PID_FILE" "3000"
    if [[ -t 1 ]]; then
      echo
      echo "(press Ctrl+C to stop)"
    fi
    sleep 1
  done
}

cleanup_live_processes() {
  if [[ -n "${LIVE_FRONTEND_PID:-}" ]] && is_pid_running "$LIVE_FRONTEND_PID"; then
    kill "$LIVE_FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${LIVE_BACKEND_PID:-}" ]] && is_pid_running "$LIVE_BACKEND_PID"; then
    kill "$LIVE_BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

run_live_stack() {
  if port_in_use 8000; then
    echo "[backend] port 8000 is already in use, please stop it first"
    exit 1
  fi
  if port_in_use 3000; then
    echo "[frontend] port 3000 is already in use, please stop it first"
    exit 1
  fi

  echo "[dev] running in foreground mode (Ctrl+C to stop both services)"
  echo "[dev] backend: $ROOT_DIR/run_api.py"
  echo "[dev] frontend: npm run dev"

  trap 'cleanup_live_processes; exit 0' INT TERM

  (
    cd "$ROOT_DIR"
    PYTHONUNBUFFERED=1 "$ROOT_DIR/venv/bin/python" "$ROOT_DIR/run_api.py" 2>&1 \
      | sed -u 's/^/[backend] /'
  ) &
  LIVE_BACKEND_PID=$!

  (
    cd "$ROOT_DIR/frontend"
    npm run dev 2>&1 | sed -u 's/^/[frontend] /'
  ) &
  LIVE_FRONTEND_PID=$!

  # If either side exits unexpectedly, stop the other side as well.
  wait -n "$LIVE_BACKEND_PID" "$LIVE_FRONTEND_PID" || true
  echo "[dev] one process exited, stopping remaining services..."
  cleanup_live_processes
}

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  dev        Run backend and frontend in foreground with live logs
  start      Start backend and frontend
  stop       Stop backend and frontend
  stop-force Stop backend and frontend (force kill any listeners on 8000/3000)
  restart    Restart backend and frontend
  status     Show process status
  watch      Watch process status in real time
  logs       Show logs (both)
  logs-live  Follow both logs in real time
  logs-back  Show backend log
  logs-back-live  Follow backend log in real time
  logs-front Show frontend log
  logs-front-live Follow frontend log in real time
EOF
}

command="${1:-}"

case "$command" in
  dev)
    run_live_stack
    ;;
  start)
    start_backend
    start_frontend
    echo "[start] running in background mode. For live output use: ./dev_stack dev"
    echo "[start] or follow logs with: ./dev_stack logs-live"
    ;;
  stop)
    stop_by_pid_file "frontend" "$FRONTEND_PID_FILE"
    stop_by_pid_file "backend" "$BACKEND_PID_FILE"
    stop_external_on_port "frontend" "3000" "(next dev|npm run dev|node.*next|next-server)" "0"
    stop_external_on_port "backend" "8000" "(run_api\.py|uvicorn|python.*api\.main)" "0"
    ;;
  stop-force)
    stop_by_pid_file "frontend" "$FRONTEND_PID_FILE"
    stop_by_pid_file "backend" "$BACKEND_PID_FILE"
    stop_external_on_port "frontend" "3000" ".*" "1"
    stop_external_on_port "backend" "8000" ".*" "1"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    status_one "backend" "$BACKEND_PID_FILE" "8000"
    status_one "frontend" "$FRONTEND_PID_FILE" "3000"
    ;;
  watch)
    watch_status
    ;;
  logs)
    show_logs all
    ;;
  logs-live)
    follow_logs all
    ;;
  logs-back)
    show_logs backend
    ;;
  logs-back-live)
    follow_logs backend
    ;;
  logs-front)
    show_logs frontend
    ;;
  logs-front-live)
    follow_logs frontend
    ;;
  *)
    usage
    exit 1
    ;;
esac
