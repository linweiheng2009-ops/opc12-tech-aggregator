#!/bin/bash
# OPC12 · 每日 render 启动脚本（launchd 调度）
# 工作目录：~/Documents/OPC/12_科技聚合_科技资讯5源
# 流程：git pull → 跑 render → 日志

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG="$ROOT/logs/render.log"
echo "" >> "$LOG"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') launchd 触发 render =====" >> "$LOG"

# 1. 从 GitHub 拉最新 data（GitHub Actions 每天 UTC 00:00 跑 fetch）
echo "[1/2] git pull..." >> "$LOG"
git pull origin main --rebase --autostash >> "$LOG" 2>&1

# 2. 跑 render 生成多尺寸卡片（3:4 / 1:1 / 16:9 / 2.35:1）
echo "[2/2] render multi-size cards..." >> "$LOG"
/usr/bin/python3 scripts/02_render_multi.py >> "$LOG" 2>&1

echo "===== 完成 =====" >> "$LOG"