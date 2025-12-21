#!/bin/bash
# SJT Agent Web 应用启动脚本

echo "======================================"
echo "   SJT Agent Web 应用启动"
echo "======================================"
echo ""

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在"
    echo "请创建 .env 文件并配置必要的 API 密钥"
    echo ""
fi

# 检查 outputs 目录
if [ ! -d outputs ]; then
    echo "创建 outputs 目录..."
    mkdir -p outputs
    echo "✓ outputs 目录已创建"
fi

echo "正在启动 Flask 应用..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止应用"
echo ""
echo "======================================"
echo ""

# 启动 Flask 应用
python app.py
