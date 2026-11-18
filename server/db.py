# -*- coding: utf-8 -*-
"""数据库会话管理（async SQLAlchemy 2.0 + aiosqlite）。"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.config import PROJECT_ROOT, ensure_dirs, get_settings
from server.models import Base

_settings = get_settings()

# ---------------------------------------------------------------------------
# ★ 连接池配置（2026-09-30 修复）
#
# 踩过的坑：原来直接用 create_async_engine 默认值
# （pool_size=5, max_overflow=10 → 最多 15 个连接），
# 结果甲方「多车间并发拉取」时直接打爆连接池：
#
#     sqlalchemy.exc.TimeoutError:
#       QueuePool limit of size 5 overflow 10 reached,
#       connection timed out, timeout 30.00
#
# 实测：20 个并发请求 → 100% 失败（超时 + HTTP 500）。
#
# 为什么会爆：**一个请求要占 2 个连接**
#     · 审计中间件  → 1 个（SessionLocal）
#     · 路由依赖    → 1 个（get_session）
#   20 并发 × 2 = 40 > 15 上限。
#
# SQLite 是本地文件、连接很廉价（不像 PG 有服务端连接数上限），
# 所以这里把池子放大，并拉长等待时间，让突发并发排队而不是直接失败。
# ---------------------------------------------------------------------------
_POOL_SIZE = getattr(_settings, "db_pool_size", 20)
_MAX_OVERFLOW = getattr(_settings, "db_max_overflow", 40)
_POOL_TIMEOUT = getattr(_settings, "db_pool_timeout", 60)

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
    # SQLite 默认禁止跨线程复用连接；aiosqlite 下需要放开
    # timeout: sqlite3 层的 busy timeout（秒）——WAL 模式下多写者仍会
    # 互相等锁，默认 5s 偏短，高并发写入时偶发 "database is locked"，
    # 放宽到 30s 让写入排队而不是直接报错。
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    pool_timeout=_POOL_TIMEOUT,
    # 回收空闲连接，避免长期运行后句柄堆积
    pool_recycle=1800,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# ★ SQLite 临时目录（2026-10-22 修复「启动清理报 unable to open database file」）
#
# 现象：批量 UPDATE（25 行）、VACUUM 报 `sqlite3.OperationalError: unable to
# open database file`，而单行 UPDATE 正常。数据库 integrity_check 是 ok。
#
# 根因：SQLite 在以下场景要创建**临时文件**（溢出排序、VACUUM 重建、WAL 扩容）：
#     · 大结果集排序/分组超出缓存 → 落临时文件
#     · VACUUM 需要临时 DB
#   这些都开在 `TEMP/TMP` 指向的目录。若该目录不可写（受限账户、被安全软件
#   锁、沙箱环境），报错就是 "unable to open database file" ——
#   看起来像"数据库坏了"，实际是"临时目录不可写"。
#
# 修法：显式把 SQLite 的临时目录指到项目内**确定可写**的 runtime 目录。
#   优先 PRAGMA temp_store_directory（老接口），现代 SQLite 已弃用，
#   因此改用**环境变量 SQLITE_TMPDIR**（必须在连接前设置）+
#   项目内 .tmp 目录兜底。
# ---------------------------------------------------------------------------
def _ensure_sqlite_tmpdir() -> Path:
    """确保 SQLite 有可写的临时目录，并把它设进环境变量。

    必须在任何连接建立**之前**调用（sqlite3 会读 SQLITE_TMPDIR）。
    """
    candidates = [
        PROJECT_ROOT / "data" / ".sqlite-tmp",
        PROJECT_ROOT / ".sqlite-tmp",
    ]
    last_err: Exception | None = None
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".write_probe"
            probe.write_bytes(b"ok")
            probe.unlink()
            os.environ["SQLITE_TMPDIR"] = str(d)
            return d
        except OSError as exc:
            last_err = exc
            continue
    raise RuntimeError(
        f"SQLite 临时目录不可用（已尝试 {[str(c) for c in candidates]}）：{last_err}"
    )


_SQLITE_TMPDIR = _ensure_sqlite_tmpdir()


# ★ 每个**新建连接**都要设，不能只在 init_db 里设一次 ——
#   连接池会不断新建/回收连接，新建的连接默认不带 PRAGMA。
#   temp_store=MEMORY：临时表/排序溢出走内存，不依赖系统临时目录。
from sqlalchemy import event  # noqa: E402


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_on_connect(dbapi_conn, _record) -> None:  # noqa: ANN001
    """每条新连接建立时立刻做的设置。"""
    try:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA temp_store=MEMORY")
        # 死锁兜底：写冲突时最多等 30 秒再报错（与 connect_args 的 timeout 呼应）
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()
    except Exception:  # pragma: no cover - 驱动差异时不影响主流程
        pass


SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """建表 + 打开 SQLite 的性能相关 pragma。"""
    ensure_dirs()
    async with engine.begin() as conn:
        # WAL 模式：读写不互相阻塞，告警持续写入 + 前端持续查询的场景必需
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        # ★ 2026-10-22：临时数据放内存，避免依赖系统临时目录。
        #   见文件上方 _ensure_sqlite_tmpdir() 的说明 ——
        #   临时目录不可写时，SQLite 会报 "unable to open database file"，
        #   表现为批量 UPDATE / VACUUM 莫名失败，极易误判成"数据库损坏"。
        await conn.exec_driver_sql("PRAGMA temp_store=MEMORY")
        await conn.run_sync(Base.metadata.create_all)
        # ★ create_all 只建新表，不会给已存在的表加列 —— 这里做轻量迁移
        await conn.run_sync(_migrate_add_columns)


def _migrate_add_columns(conn) -> None:
    """对已存在的表补齐新增列（SQLite 的 ALTER TABLE ADD COLUMN）。

    只做「加列」这种向后兼容的迁移；SQLite 不支持改列类型/删列，
    真需要时再上 Alembic。
    """
    from sqlalchemy import inspect

    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    migrations: dict[str, list[tuple[str, str]]] = {
        "alarm": [
            ("media_expired", "BOOLEAN DEFAULT 0"),
            ("media_expired_at", "DATETIME"),
            # ★ 人工处置状态（前端左侧红点 = 未处理数）
            ("handled", "BOOLEAN DEFAULT 0"),
            ("handled_at", "DATETIME"),
            ("handled_by", "VARCHAR(64)"),
            # ★ 多车间隔离：归属车间 + 判定依据留痕
            ("workshop", "VARCHAR(32)"),
            ("workshop_rule", "VARCHAR(32)"),
            # ★ 视频抓取失败原因（前端展示用）
            ("video_error", "VARCHAR(512)"),
        ],
        "user": [
            # ★ 跨车间账号（admin 可看全部车间）
            ("is_superuser", "BOOLEAN DEFAULT 0"),
            # ★ 密码版本号：改密 +1，JWT pwdv 比对实现改密即吊销
            ("password_version", "INTEGER DEFAULT 0"),
        ],
    }

    for table, columns in migrations.items():
        if table not in existing_tables:
            continue
        have = {c["name"] for c in inspector.get_columns(table)}
        for name, ddl in columns:
            if name in have:
                continue
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")

    # ★ 补索引：create_all 只建表，不会给已存在的表加索引。
    #   车间隔离的查询会大量走 (workshop, alarm_time)，缺索引会全表扫描。
    for idx_name, table, cols in (
        ("idx_alarm_workshop_time", "alarm", "(workshop, alarm_time)"),
        ("idx_alarm_handled", "alarm", "(handled)"),
    ):
        if table not in existing_tables:
            continue
        conn.exec_driver_sql(
            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {cols}"
        )


async def dispose_db() -> None:
    await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的会话。"""
    async with SessionLocal() as session:
        yield session
