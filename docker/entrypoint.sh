#!/usr/bin/env bash
# ISUP 告警平台 —— 容器启动入口
set -euo pipefail

APP_DIR="${ISUP_APP_DIR:-/app}"
cd "$APP_DIR"

log()  { printf '\033[36m[entrypoint]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[entrypoint][WARN]\033[0m %s\n' "$*"; }
err()  { printf '\033[31m[entrypoint][ERROR]\033[0m %s\n' "$*" >&2; }

log "=============================================================="
log "  ISUP 告警平台 —— Docker 启动"
log "=============================================================="

if [ -z "${ISUP_SERVER_IP:-}" ]; then
    err "环境变量 ISUP_SERVER_IP 未设置（设备回连地址）"
    exit 1
fi
if [ -z "${ISUP_KEY:-}" ]; then
    err "环境变量 ISUP_KEY 未设置（须与设备 ISUP 登录密钥一致）"
    exit 1
fi

log "准备运行期目录..."
mkdir -p \
    "$APP_DIR/data" \
    "$APP_DIR/storage" \
    "$APP_DIR/media/video" \
    "$APP_DIR/media/hls" \
    "$APP_DIR/IsupSDKLog" \
    "$APP_DIR/outputFiles"

for d in data storage media IsupSDKLog outputFiles; do
    if ! touch "$APP_DIR/$d/.probe" 2>/dev/null; then
        err "目录不可写: $APP_DIR/$d"
        exit 1
    fi
    rm -f "$APP_DIR/$d/.probe"
done
log "目录检查通过"

log "渲染 ISUP 配置 (服务器IP=${ISUP_SERVER_IP})..."
python3 - <<'PYEOF'
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app/docker")
from conf_template import check_ports_available, render_template, validate_isup_conf

APP_DIR = Path("/app")
template = APP_DIR / "docker" / "templates" / "isupConf.json.template"
output = APP_DIR / "resources" / "conf" / "isupConf.json"

try:
    conf = render_template(template, output, dict(os.environ))
except Exception as exc:
    print(f"\033[31m[entrypoint][ERROR] 配置渲染失败: {exc}\033[0m", file=sys.stderr)
    sys.exit(1)

problems = validate_isup_conf(conf)
if problems:
    print("\033[31m[entrypoint][ERROR] 配置校验未通过:\033[0m", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    sys.exit(1)
print("[entrypoint] 配置校验通过")

ports = [
    ("tcp", int(conf["cms"]["CmsServerPort"])),
    ("tcp", int(conf["ss"]["PicServerListenPort"])),
    ("tcp", int(conf["ams"]["AlarmServerListenTCPPort"])),
    ("udp", int(conf["ams"]["AlarmServerListenUDPPort"])),
    ("tcp", int(conf["sms"]["SmsServerListenPort"])),
    ("tcp", int(conf["sms"]["SmsBackServerListenPort"])),
    ("tcp", int(os.environ.get("ISUP_PORT", "8088"))),
]
occupied = check_ports_available(ports)
if occupied:
    print("\033[33m[entrypoint][WARN] 以下端口已被占用:\033[0m")
    for o in occupied:
        print(f"  - {o}")
else:
    print("[entrypoint] 端口检查通过")
PYEOF

HOST="${ISUP_HOST:-0.0.0.0}"
PORT="${ISUP_PORT:-8088}"
WORKERS="${ISUP_WORKERS:-1}"
if [ "$WORKERS" != "1" ]; then
    warn "ISUP_WORKERS=$WORKERS，强制改为 1（SDK 回调是进程内状态）"
    WORKERS=1
fi

log "启动: uvicorn server.serve_web:app --host $HOST --port $PORT"
log "=============================================================="

exec python3 -m uvicorn server.serve_web:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "${ISUP_LOG_LEVEL:-info}" \
    --no-access-log
