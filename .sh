#!/bin/zsh

# 启动 Postgres
# 215ede5c038f00c1f95af42fa328287ddd1aa537092fb4131ffcbc259fde0a7e
docker run -d \
  --name manus-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=manus \
  -v manus_postgres_data:/var/lib/postgresql/data \
  postgres:16

# 启动 Redis
# 0292dc633d58cf2537c29dfecd2b217f48fb93880bd2e81b37fe27f5c56eb184
# Redis 默认：无密码、无用户、直接连接
# Redis 的设计是轻量缓存，默认安全策略非常宽松：
# 默认没有密码
# 默认没有用户名
# 默认直接 localhost 就能连
# 默认只允许本地访问
docker run -d \
  --name manus-redis \
  -p 6379:6379 \
  -v manus_redis_data:/data \
  redis:7


docker stop manus-postgres
docker rm manus-postgres
docker volume rm manus_postgres_data


# 现在我们已经有了两个正在运行的容器(QQ)，你还需要学会如何管理它们。
# 1. docker stop <container_name> :停止一个正在运行的容器。
# 2. docker start <container_name> :启动一个已经停止的容器。
# 3. docker logs -f <container_name> :查看容器的实时日志， f 代表follow，在排查问题时非常 有用!
# 4. docker rm <container_name> :删除一个容器。注意:删除前必须先停止它。
# 5. docker volume ls :查看所有的数据卷。
# 6. docker volume rm <volume_name> :删除一个数据卷，这将永久删除你的数据!