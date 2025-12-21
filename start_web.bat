@echo off
REM SJT Agent Web 应用启动脚本 (Windows)

echo ======================================
echo    SJT Agent Web 应用启动
echo ======================================
echo.

REM 检查 .env 文件是否存在
if not exist .env (
    echo 警告: .env 文件不存在
    echo 请创建 .env 文件并配置必要的 API 密钥
    echo.
)

REM 检查 outputs 目录
if not exist outputs (
    echo 创建 outputs 目录...
    mkdir outputs
    echo √ outputs 目录已创建
)

echo 正在启动 Flask 应用...
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止应用
echo.
echo ======================================
echo.

REM 启动 Flask 应用
python app.py

pause
