#!/bin/zsh

# 直接启动 FastAPI 服务
  # uv run 自动进入虚拟环境
  # 用 uvicorn 运行 app/main.py 里的 app
  # 对外开放访问（0.0.0.0）
  # 端口 8000
  # 关闭服务时立刻退出，不等待 timeout-graceful-shutdown 0
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 0