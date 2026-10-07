#!/bin/bash
S=/private/tmp/claude-501/-Users-louis-Desktop-quantitative-trading-system/929a358b-897c-4786-82fe-c60c3cf83d65/scratchpad
awk '{c+=$1; if (c<=1100) print $2}' "$S/govfiles.txt" > "$S/chunk1.txt"
awk '{c+=$1; if (c>1100) print $2}' "$S/govfiles.txt" > "$S/chunk2.txt"
wc -l "$S/chunk1.txt" "$S/chunk2.txt"
cd /Users/louis/Desktop/quantitative_trading_system && git status --porcelain | wc -l
