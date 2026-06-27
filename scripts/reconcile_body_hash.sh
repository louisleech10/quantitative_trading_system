#!/usr/bin/env bash
# reconcile_body_hash.sh — 計算 reconcile「本體」的 canonical sha256(委員與 checker 共用,避免換行慣例不一致致假失敗)。
# 本體 = 「## 戳記」標題之前的所有行(戳記區不計入,否則互相 append 會改雜湊)。
# 委員 append 戳記前:bash scripts/reconcile_body_hash.sh <file> → 取得 hash 填入戳記 sha256:<hash>。
# checker 用同一腳本算 → 保證一致。
set -u
file="${1:-}"
[ -n "${file}" ] && [ -f "${file}" ] || { echo "用法: reconcile_body_hash.sh <reconcile_file>" >&2; exit 1; }
ml="$(grep -nE '^##[[:space:]]*戳記' "${file}" | head -1 | cut -d: -f1)"
[ -n "${ml}" ] || { echo "ERROR: 缺『## 戳記』區段標題" >&2; exit 1; }
# canonical:取本體行,shasum;統一用 head | shasum(含尾換行),委員與 checker 同法。
head -n "$((ml-1))" "${file}" | shasum -a 256 | awk '{print $1}'
