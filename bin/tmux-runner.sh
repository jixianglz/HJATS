#!/bin/bash
# tmux-runner.sh - Cline 后台命令执行器
# 解决 Cline 在 code-server 中 WebSocket 断连导致命令卡 pending 的问题
#
# Cline 用法:
#   tmux-runner.sh <命令>              # 启动后台命令（最常用）
#   tmux-runner.sh status [标签]       # 检查状态
#   tmux-runner.sh log <标签>          # 查看完整日志
#   tmux-runner.sh attach <标签>       # 附着到终端（仅 code-server 终端可用）
#   tmux-runner.sh list                # 列出活跃任务
#
# 示例:
#   tmux-runner.sh "cd /home/ubuntu/HJATS && python3 backtest.py --symbol ETHUSDT"
#   tmux-runner.sh status 1782474321

CMD_B64=""
_do_run() {
    local CMD="$*"
    local TAG="$(date +%s)"
    local SESSION="cline-run-${TAG}"
    local LOG="/tmp/tmux-runner-${TAG}.log"
    
    if [ -z "$CMD" ]; then
        echo "用法: tmux-runner.sh <命令>"
        echo "       tmux-runner.sh status [标签]"
        echo "       tmux-runner.sh log <标签>"
        echo "       tmux-runner.sh list"
        exit 1
    fi
    
    # Base64 编码命令，避免引用问题
    local CMD_B64=$(echo "$CMD" | base64 -w0)
    
    # 创建临时执行脚本
    cat > "/tmp/tmux-cmd-${TAG}.sh" << 'SCRIPT'
#!/bin/bash
CMD_B64=""
LOG=""
echo "[$(date '+%H:%M:%S')] 开始执行..."
CMD=$(echo "$CMD_B64" | base64 -d)
eval "$CMD"
EXIT_CODE=$?
echo "[$(date '+%H:%M:%S')] 退出码: $EXIT_CODE"
SCRIPT
    
    # 注入 BASE64 指令和日志路径
    sed -i "s|CMD_B64=\"\"|CMD_B64=\"${CMD_B64}\"|" "/tmp/tmux-cmd-${TAG}.sh"
    sed -i "s|LOG=\"\"|LOG=\"${LOG}\"|" "/tmp/tmux-cmd-${TAG}.sh"
    chmod +x "/tmp/tmux-cmd-${TAG}.sh"
    
    # 在 tmux 中运行
    tmux new-session -d -s "$SESSION" "/tmp/tmux-cmd-${TAG}.sh > '${LOG}' 2>&1"
    
    echo "✅ 命令已后台启动"
    echo "   标签: $TAG"
    echo "   会话: tmux attach -t $SESSION"
    echo "   日志: tail -f $LOG"
    echo "   状态: tmux-runner.sh status $TAG"
}

_do_status() {
    local TAG="$1"
    if [ -z "$TAG" ]; then
        echo "当前活跃:"
        tmux ls 2>/dev/null | grep '^cline-run-' | awk '{print "   → " $1}'
        echo ""
        echo "最近日志:"
        ls -1t /tmp/tmux-runner-*.log 2>/dev/null | head -5 | while read f; do
            echo "   → $(basename "$f" .log | sed 's/tmux-runner-//')"
        done
        exit 0
    fi
    
    local LOG="/tmp/tmux-runner-${TAG}.log"
    if tmux has-session -t "cline-run-${TAG}" 2>/dev/null; then
        echo "⏳ 运行中..."
        tail -5 "$LOG" 2>/dev/null
        echo "   跟踪: tail -f $LOG"
    else
        echo "✅ 已完成"
        tail -20 "$LOG" 2>/dev/null || echo "(日志为空)"
        echo "   完整日志: cat $LOG"
    fi
}

_do_log() {
    local TAG="$1"
    local LOG="/tmp/tmux-runner-${TAG}.log"
    if [ -f "$LOG" ]; then
        cat "$LOG"
    else
        echo "日志文件不存在: $LOG"
    fi
}

_do_attach() {
    local TAG="$1"
    tmux attach -t "cline-run-${TAG}" 2>/dev/null || echo "会话不存在: cline-run-${TAG}"
}

_do_list() {
    echo "后台任务:"
    tmux ls 2>/dev/null | grep '^cline-run-' || echo "(无)"
    echo ""
    echo "最近日志:"
    ls -1t /tmp/tmux-runner-*.log 2>/dev/null | head -5 || echo "(无)"
}

# Main dispatch
case "${1:-}" in
    status|check) shift; _do_status "$@" ;;
    log)           shift; _do_log "$@" ;;
    attach)        shift; _do_attach "$@" ;;
    list)          _do_list ;;
    help|--help)   head -15 "$0" ;;
    *)             _do_run "$@" ;;
esac
