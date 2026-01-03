#!/bin/bash
# cmd - 生成 gexbot 命令清单
# 
# 用法:
#   cmd AAPL              # 基本用法
#   cmd AAPL -v 18.5      # 带 VIX
#   cmd AAPL -t 2026-01-03 # 指定日期
#   cmd AAPL NVDA META    # 批量

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/main.py" cmd "$@"
