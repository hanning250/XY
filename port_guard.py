# -*- coding: utf-8 -*-
"""启动前检查端口占用，避免重复运行 main.py 导致 10048 错误。"""
import re
import subprocess
import sys


def _run_netstat():
    result = subprocess.run(
        ["netstat", "-ano"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="ignore",
        check=False,
    )
    return result.stdout or ""


def get_listening_pids(port: int) -> set[int]:
    pattern = re.compile(rf":{port}\s+.*LISTENING\s+(\d+)", re.IGNORECASE)
    pids = set()
    for line in _run_netstat().splitlines():
        match = pattern.search(line.replace("\t", " "))
        if match:
            try:
                pids.add(int(match.group(1)))
            except ValueError:
                continue
    return pids


def find_port_conflicts(ports: list[int]) -> dict[int, set[int]]:
    conflicts = {}
    for port in ports:
        pids = get_listening_pids(port)
        safe_pids = {pid for pid in pids if pid > 4}
        if safe_pids:
            conflicts[port] = safe_pids
    return conflicts


def kill_pids(pids: set[int]) -> list[int]:
    killed = []
    for pid in sorted(pids):
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="ignore",
            check=False,
        )
        if result.returncode == 0:
            killed.append(pid)
    return killed


def ensure_ports_available(ports: list[int], force: bool = False) -> bool:
    conflicts = find_port_conflicts(ports)
    if not conflicts:
        return True

    if force:
        all_pids = set()
        for pids in conflicts.values():
            all_pids.update(pids)
        killed = kill_pids(all_pids)
        if killed:
            print(f"[port-guard] 已结束占用端口的进程: {', '.join(map(str, killed))}")
        remaining = find_port_conflicts(ports)
        if not remaining:
            return True
        conflicts = remaining

    print("[port-guard] 以下端口已被占用，请勿重复启动 main.py：")
    for port, pids in sorted(conflicts.items()):
        pid_text = ", ".join(str(pid) for pid in sorted(pids))
        print(f"  - 端口 {port} -> PID {pid_text}")
    print("[port-guard] 处理方式：")
    print("  1) 回到已运行的终端，按 Ctrl+C 停止旧服务")
    print("  2) 或执行: taskkill /PID <进程号> /F")
    print("  3) 或强制重启: python main.py --force")
    return False


def collect_required_ports(config, api_only: bool) -> list[int]:
    ports = [int(config.get("api", {}).get("port", 8080))]
    if config.get("isup", {}).get("enabled", True) and not api_only:
        isup = config.get("isup", {})
        ams = isup.get("ams", {})
        ports.append(int(isup.get("cms", {}).get("port", 7660)))
        ports.append(int(ams.get("port", 7200)))
        if ams.get("use_cms_port", True):
            ports.append(int(ams.get("route_port") or ams.get("port", 7200)))
    return sorted(set(ports))
