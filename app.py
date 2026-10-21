"""pushhub - 自托管消息推送中心（单用户）。

后端：FastAPI + SQLite。功能：登录、应用与发消息令牌管理、
POST /message 发消息接口、消息中心（筛选/删除/清空）、
SSE 实时推送（页面开着就能即时收到新消息）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("PH_DB_PATH", str(BASE_DIR / "data" / "pushhub.db"))
TOKEN_TTL_SECONDS = 24 * 60 * 60
INITIAL_USERNAME = os.environ.get("PH_INITIAL_USERNAME", "admin")
INITIAL_PASSWORD = os.environ.get("PH_INITIAL_PASSWORD", "admin123")
DEFAULT_PRIORITY = 5
SSE_KEEPALIVE_SECONDS = 20


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


# 与 users.salt（secrets.token_hex(16)）等长。用户不存在时用来做一次等代价 PBKDF2。
_DUMMY_PASSWORD_SALT = "00" * 16


def init_db() -> None:
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                token TEXT UNIQUE,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
                title TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 5,
                created_at TEXT NOT NULL
            );
            """
        )
        # P1-4：只有 users 表完全为空（首次启动）才创建初始用户。
        # 已有用户后，哪怕换了 PH_INITIAL_USERNAME，也不会再插入一个全权限账号。
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        if count["n"] == 0:
            salt = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, must_change_password)"
                " VALUES (?, ?, ?, 1)",
                (INITIAL_USERNAME, hash_password(INITIAL_PASSWORD, salt), salt),
            )
        conn.commit()
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    broadcaster.bind_loop(asyncio.get_running_loop())
    yield


class SecurityHeadersMiddleware:
    """P1-5：补点击劫持防护头。只改 ASGI 起始消息里的响应头，
    不读取、不缓冲响应体，所以 SSE 长连接不会被打断。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                existing = {name.lower() for name, _ in headers}
                extra = (
                    (b"x-frame-options", b"DENY"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"frame-ancestors 'none'"),
                )
                for name, value in extra:
                    if name not in existing:
                        headers.append((name, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


# P2-2：未登录可访问的自动文档页（/docs、/redoc、/openapi.json）直接关闭。
app = FastAPI(
    title="pushhub",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(SecurityHeadersMiddleware)


# ---------- SSE 订阅者管理（进程内广播） ----------

class Broadcaster:
    """每个打开的流页面持有一个队列，新消息进来时广播给所有队列。"""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def _enqueue(self, payload: dict) -> None:
        for queue in list(self._queues):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # 慢消费者队列满了就丢这一条，不阻塞发消息接口
                pass

    def publish(self, payload: dict) -> None:
        # post_message 是同步端点，会在线程池里跑。Queue 只能在事件循环线程入队。
        snapshot = dict(payload)
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._enqueue, snapshot)
            return
        self._enqueue(snapshot)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)


broadcaster = Broadcaster()


# ---------- 认证 ----------

def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.removeprefix("Bearer ").strip()
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (token, time.time()),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return row


def app_by_token(token: str | None) -> sqlite3.Row:
    if not token:
        raise HTTPException(status_code=401, detail="缺少应用令牌（请求头 X-App-Token）")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM apps WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="应用令牌无效或已被吊销")
        conn.execute(
            "UPDATE apps SET last_used_at = ? WHERE id = ?",
            (utcnow_iso(), row["id"]),
        )
        conn.commit()
        return row
    finally:
        conn.close()


# ---------- 请求体 ----------

class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class AppIn(BaseModel):
    name: str
    description: str = ""


class MessageIn(BaseModel):
    title: str = ""
    message: str
    priority: int | None = None


# ---------- 序列化 ----------

def app_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "token": row["token"],
        "created_at": row["created_at"],
        "last_used_at": row["last_used_at"],
    }


def message_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "app_id": row["app_id"],
        "app_name": row["app_name"],
        "title": row["title"],
        "message": row["message"],
        "priority": row["priority"],
        "created_at": row["created_at"],
    }


def new_app_token(conn: sqlite3.Connection) -> str:
    for _ in range(20):
        token = "ph_" + secrets.token_urlsafe(24)
        exists = conn.execute(
            "SELECT 1 FROM apps WHERE token = ?", (token,)
        ).fetchone()
        if exists is None:
            return token
    raise HTTPException(status_code=500, detail="令牌生成失败，请重试")


# ---------- 登录 / 账号 ----------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "pushhub"}


@app.post("/api/login")
def login(body: LoginIn) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username.strip(),)
        ).fetchone()
        if row is None:
            hash_password(body.password, _DUMMY_PASSWORD_SALT)
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        if row["password_hash"] != hash_password(body.password, row["salt"]):
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, row["id"], time.time() + TOKEN_TTL_SECONDS),
        )
        conn.commit()
        return {
            "token": token,
            "username": row["username"],
            "must_change_password": bool(row["must_change_password"]),
        }
    finally:
        conn.close()


@app.post("/api/logout")
def logout(
    authorization: str | None = Header(default=None),
    user: sqlite3.Row = Depends(current_user),
) -> dict:
    token = authorization.removeprefix("Bearer ").strip()  # type: ignore[union-attr]
    conn = get_db()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(current_user)) -> dict:
    return {
        "username": user["username"],
        "must_change_password": bool(user["must_change_password"]),
    }


@app.post("/api/change-password")
def change_password(
    body: ChangePasswordIn,
    user: sqlite3.Row = Depends(current_user),
    authorization: str | None = Header(default=None),
) -> dict:
    if user["password_hash"] != hash_password(body.current_password, user["salt"]):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    # P1-3：改密成功时作废同一用户的所有其他会话，只保留当前这一次登录。
    # 取不到当前令牌时不删，避免把自己也踢掉。
    current_token = (
        authorization.removeprefix("Bearer ").strip()
        if authorization and authorization.startswith("Bearer ")
        else None
    )
    salt = secrets.token_hex(16)
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0"
            " WHERE id = ?",
            (hash_password(body.new_password, salt), salt, user["id"]),
        )
        if current_token:
            conn.execute(
                "DELETE FROM sessions WHERE user_id = ? AND token != ?",
                (user["id"], current_token),
            )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


# ---------- 应用管理 ----------

@app.get("/api/apps")
def list_apps(user: sqlite3.Row = Depends(current_user)) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM apps ORDER BY id ASC").fetchall()
        return [app_out(r) for r in rows]
    finally:
        conn.close()


@app.post("/api/apps", status_code=201)
def create_app(body: AppIn, user: sqlite3.Row = Depends(current_user)) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="应用名不能为空")
    conn = get_db()
    try:
        token = new_app_token(conn)
        cur = conn.execute(
            "INSERT INTO apps (name, description, token, created_at) VALUES (?, ?, ?, ?)",
            (name, body.description.strip(), token, utcnow_iso()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM apps WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return app_out(row)
    finally:
        conn.close()


@app.put("/api/apps/{app_id}")
def update_app(
    app_id: int, body: AppIn, user: sqlite3.Row = Depends(current_user)
) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="应用名不能为空")
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="应用不存在")
        conn.execute(
            "UPDATE apps SET name = ?, description = ? WHERE id = ?",
            (name, body.description.strip(), app_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
        return app_out(row)
    finally:
        conn.close()


@app.delete("/api/apps/{app_id}")
def delete_app(app_id: int, user: sqlite3.Row = Depends(current_user)) -> dict:
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM apps WHERE id = ?", (app_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="应用不存在")
        conn.execute("DELETE FROM apps WHERE id = ?", (app_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.post("/api/apps/{app_id}/regenerate-token")
def regenerate_token(app_id: int, user: sqlite3.Row = Depends(current_user)) -> dict:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="应用不存在")
        token = new_app_token(conn)
        conn.execute("UPDATE apps SET token = ? WHERE id = ?", (token, app_id))
        conn.commit()
        row = conn.execute("SELECT * FROM apps WHERE id = ?", (app_id,)).fetchone()
        return app_out(row)
    finally:
        conn.close()


@app.delete("/api/apps/{app_id}/token")
def revoke_token(app_id: int, user: sqlite3.Row = Depends(current_user)) -> dict:
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM apps WHERE id = ?", (app_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="应用不存在")
        conn.execute("UPDATE apps SET token = NULL WHERE id = ?", (app_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


# ---------- 发消息接口（给外部程序调用，凭应用令牌） ----------

@app.post("/message", status_code=201)
def post_message(
    body: MessageIn, x_app_token: str | None = Header(default=None)
) -> dict:
    app_row = app_by_token(x_app_token)
    text = (body.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="消息正文不能为空")
    priority = DEFAULT_PRIORITY if body.priority is None else int(body.priority)
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO messages (app_id, title, message, priority, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (app_row["id"], (body.title or "").strip(), text, priority, utcnow_iso()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT m.*, a.name AS app_name FROM messages m"
            " JOIN apps a ON a.id = m.app_id WHERE m.id = ?",
            (cur.lastrowid,),
        ).fetchone()
    finally:
        conn.close()
    payload = message_out(row)
    broadcaster.publish(payload)
    return payload


# ---------- 消息中心 ----------

@app.get("/api/messages")
def list_messages(
    app_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    user: sqlite3.Row = Depends(current_user),
) -> list[dict]:
    conn = get_db()
    try:
        if app_id is not None:
            rows = conn.execute(
                "SELECT m.*, a.name AS app_name FROM messages m"
                " JOIN apps a ON a.id = m.app_id WHERE m.app_id = ?"
                " ORDER BY m.created_at DESC, m.id DESC LIMIT ?",
                (app_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT m.*, a.name AS app_name FROM messages m"
                " JOIN apps a ON a.id = m.app_id"
                " ORDER BY m.created_at DESC, m.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [message_out(r) for r in rows]
    finally:
        conn.close()


@app.delete("/api/messages/{message_id}")
def delete_message(
    message_id: int, user: sqlite3.Row = Depends(current_user)
) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="消息不存在")
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.delete("/api/messages")
def clear_messages(
    app_id: int | None = Query(default=None),
    user: sqlite3.Row = Depends(current_user),
) -> dict:
    conn = get_db()
    try:
        if app_id is not None:
            cur = conn.execute("DELETE FROM messages WHERE app_id = ?", (app_id,))
        else:
            cur = conn.execute("DELETE FROM messages")
        conn.commit()
        return {"ok": True, "deleted": cur.rowcount}
    finally:
        conn.close()


# ---------- SSE 实时推送 ----------

@app.get("/api/stream")
async def stream(request: Request, user: sqlite3.Row = Depends(current_user)):
    # P1-2：会话令牌只从 Authorization: Bearer 请求头读取，
    # 不再接受 URL 查询参数里的令牌（即使有效也会返回 401）。
    # 前端用 fetch 流式读取并带头，不走查询参数，不受影响。

    queue = broadcaster.subscribe()

    async def event_gen():
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(
                        queue.get(), timeout=SSE_KEEPALIVE_SECONDS
                    )
                    yield "event: message\ndata: " + json.dumps(
                        payload, ensure_ascii=False
                    ) + "\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                if await request.is_disconnected():
                    break
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- 首页 ----------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


if __name__ == "__main__":
    import uvicorn

    # P1-1：默认只监听本机（127.0.0.1）。要对局域网开放时，显式设置 PH_HOST=0.0.0.0。
    uvicorn.run(
        app,
        host=os.environ.get("PH_HOST", "127.0.0.1"),
        port=int(os.environ.get("PH_PORT", "8000")),
    )
