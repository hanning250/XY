# 本机 Docker 部署（192.168.1.221）

## 一键启动

```bash
cd /home/sy304/isup-alarm
mkdir -p runtime/{data,storage,media,logs,outputFiles}
docker compose -f docker/docker-compose.yml --env-file docker/deploy.env up -d --build
```

## 访问

- 看板：http://192.168.1.221:8088
- 健康检查：http://192.168.1.221:8088/openapi/v1/health

## 设备侧配置

设备网页 → ISUP：平台 IP `192.168.1.221`，端口 `7661`，密钥与 `ISUP_KEY` 一致（默认 `STSXY304`）。

## 常用命令

```bash
docker compose -f docker/docker-compose.yml logs -f
docker compose -f docker/docker-compose.yml restart
docker compose -f docker/docker-compose.yml down
```
