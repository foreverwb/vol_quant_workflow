#!/bin/bash
# 安装脚本 - 设置可执行权限并配置 PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 波动率分析系统 v2.0 安装"
echo "================================"

# 1. 设置可执行权限
echo "设置可执行权限..."
chmod +x "$SCRIPT_DIR/cmd"
chmod +x "$SCRIPT_DIR/create"
chmod +x "$SCRIPT_DIR/update"
chmod +x "$SCRIPT_DIR/main.py"

# 2. 添加到 PATH
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    # 检查是否已添加
    if ! grep -q "vol_analyzer_v2" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# 波动率分析系统" >> "$SHELL_RC"
        echo "export PATH=\"$SCRIPT_DIR:\$PATH\"" >> "$SHELL_RC"
        echo "✅ 已添加到 PATH ($SHELL_RC)"
        echo ""
        echo "⚠️  请运行以下命令使配置生效:"
        echo "   source $SHELL_RC"
    else
        echo "✅ PATH 已配置"
    fi
else
    echo "⚠️  未找到 shell 配置文件，请手动添加:"
    echo "   export PATH=\"$SCRIPT_DIR:\$PATH\""
fi

echo ""
echo "================================"
echo "✅ 安装完成!"
echo ""
echo "使用方式:"
echo "  cmd AAPL              # 生成命令"
echo "  cmd AAPL -v 18.5      # 带 VIX"
echo "  create AAPL           # 完整分析"
echo "  update AAPL           # 快速更新"
