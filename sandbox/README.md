[//]: # (命令备忘录)

```shell
uvicorn app.main:app --host 0.0.0.0 --port 9999 --reload

docker-compose -f .devops/docker-compose.yml up -d --build

docker-compose -f .devops/docker-compose.yml build --no-cache && docker-compose -f .devops/docker-compose.yml up -d

/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

docker rm -f sandbox-dev

docker build -t sandbox-dev . 

docker run -d -p 8080:8080 -p 5900:5900 -p 5901:5901 -p 9222:9222 --name sandbox-dev sandbox-dev

docker logs -f sandbox-dev

docker run -d -v /Users/ysz/YS/Code/demo/mas/manus/sandbox:/sandbox -p 8080:8080 -p 5900:5900 -p 5901:5901 -p 9222:9222 --name sandbox-dev sandbox-dev

```

[//]: # (先装python3-pip)

```shell
apt update && apt install -y python3-pip
```

[//]: # (pip全局安装supervisor -Ubuntu22.04 新版源不再自带 supervisor 原生 apt 包，用 pip 安装。)

```shell
pip3 install supervisor
```

[//]: # (-c supervisord.config 手动指定读取当前目录 supervisord.config 作为配置 -n：前台运行（非守护进程)

[//]: # (apt 安装会自动生成/etc/supervisor/配置目录 + systemd 启动文件；pip 安装不会自动生成 systemd 服务，需要手动)

```shell
supervisord -c supervisord.conf -n
```