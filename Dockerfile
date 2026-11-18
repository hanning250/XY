# ISUP 告警平台 —— 本机 Docker 镜像
# 使用本机已有镜像，避免拉取 docker.io 超时：
#   node:18-bookworm-slim / python:3.10.16-slim-bookworm
#
# 构建：docker compose -f docker/docker-compose.yml --env-file docker/deploy.env build
# 运行：必须 network_mode: host

ARG NODE_IMAGE=node:18-bookworm-slim
ARG BASE_IMAGE=python:3.10.16-slim-bookworm

# ---------- 前端构建 ----------
FROM ${NODE_IMAGE} AS web-builder
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY web/ ./
RUN npm run build

# ---------- 运行镜像 ----------
FROM ${BASE_IMAGE}

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LD_LIBRARY_PATH=/app/lib:/app/lib/HCAapSDKCom

RUN set -eux; \
    sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g; s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates tzdata curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/requirements.lock.txt /app/requirements.lock.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.lock.txt

COPY server     /app/server
COPY src        /app/src
COPY resources  /app/resources
COPY lib        /app/lib
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/conf_template.py /app/docker/conf_template.py
COPY docker/templates/isupConf.json.template /app/docker/templates/isupConf.json.template
COPY --from=web-builder /web/dist /app/web/dist

RUN chmod +x /usr/local/bin/entrypoint.sh \
    && find /app/lib -name "*.so*" -exec chmod +x {} \; \
    && mkdir -p /app/data /app/storage /app/media/video /app/media/hls \
               /app/IsupSDKLog /app/outputFiles \
    && chmod -R 777 /app/data /app/storage /app/media /app/IsupSDKLog /app/outputFiles

# 构建期 SDK 加载自检
RUN set -eux; \
    for so in libHCISUPCMS.so libHCISUPAlarm.so libHCISUPSS.so libHCISUPStream.so; do \
        MISSING=$(ldd "/app/lib/$so" 2>/dev/null | grep "not found" || true); \
        if [ -n "$MISSING" ]; then echo "[FAIL] $so:"; echo "$MISSING"; exit 1; fi; \
        echo "[OK] $so"; \
    done; \
    python -c "import ctypes; ctypes.CDLL('/app/lib/libHCISUPCMS.so', mode=ctypes.RTLD_GLOBAL); print('CMS ok')"

EXPOSE 8088 7661 7662/udp 7663 6011 7665 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8088/openapi/v1/health || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
