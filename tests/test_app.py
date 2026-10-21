"""pushhub 自动化测试：登录 / 应用与令牌 / 发消息 / 消息中心 / 改密 / SSE。"""

import os
import sys
import tempfile
from pathlib import Path

os.environ["PH_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import app as ph


@pytest.fixture(scope="module")
def client():
    with TestClient(ph.app) as c:
        yield c


def login(client, username="admin", password="admin123"):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def token(client):
    return login(client)


def make_app(client, token, name="测试应用"):
    r = client.post("/api/apps", json={"name": name, "description": "pytest"}, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()


# ---------- 健康检查与登录 ----------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "pushhub" in r.text


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_login_ok_must_change(client, token):
    r = client.get("/api/me", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["username"] == "admin"
    assert r.json()["must_change_password"] is True


def test_unauthenticated_401(client):
    assert client.get("/api/apps").status_code == 401
    assert client.get("/api/messages").status_code == 401
    assert client.post("/api/apps", json={"name": "x"}).status_code == 401
    assert client.get("/api/apps", headers=auth("bad-token")).status_code == 401


# ---------- 应用与令牌 ----------

def test_create_app_generates_token(client, token):
    a = make_app(client, token, "备份脚本")
    assert a["name"] == "备份脚本"
    assert a["token"] and a["token"].startswith("ph_")
    assert a["created_at"]


def test_create_app_empty_name_400(client, token):
    r = client.post("/api/apps", json={"name": "  "}, headers=auth(token))
    assert r.status_code == 400


def test_rename_app(client, token):
    a = make_app(client, token, "旧名字")
    r = client.put(f"/api/apps/{a['id']}", json={"name": "新名字", "description": "d2"},
                   headers=auth(token))
    assert r.status_code == 200
    assert r.json()["name"] == "新名字"
    assert r.json()["description"] == "d2"


def test_regenerate_token_invalidates_old(client, token):
    a = make_app(client, token, "换令牌应用")
    old = a["token"]
    r = client.post(f"/api/apps/{a['id']}/regenerate-token", headers=auth(token))
    assert r.status_code == 200
    new = r.json()["token"]
    assert new and new != old
    # 旧令牌发消息应 401，新令牌应成功
    assert client.post("/message", json={"message": "hi"},
                       headers={"X-App-Token": old}).status_code == 401
    assert client.post("/message", json={"message": "hi"},
                       headers={"X-App-Token": new}).status_code == 201


def test_revoke_token(client, token):
    a = make_app(client, token, "吊销应用")
    old = a["token"]
    r = client.request("DELETE", f"/api/apps/{a['id']}/token", headers=auth(token))
    assert r.status_code == 200
    apps = client.get("/api/apps", headers=auth(token)).json()
    mine = [x for x in apps if x["id"] == a["id"]][0]
    assert mine["token"] is None
    assert client.post("/message", json={"message": "hi"},
                       headers={"X-App-Token": old}).status_code == 401


def test_delete_app_cascades_messages(client, token):
    a = make_app(client, token, "待删应用")
    client.post("/message", json={"message": "将被连带删除"},
                headers={"X-App-Token": a["token"]})
    r = client.delete(f"/api/apps/{a['id']}", headers=auth(token))
    assert r.status_code == 200
    msgs = client.get("/api/messages", headers=auth(token)).json()
    assert all(m["app_id"] != a["id"] for m in msgs)
    assert client.delete(f"/api/apps/{a['id']}", headers=auth(token)).status_code == 404


# ---------- 发消息接口 ----------

def test_post_message_ok_defaults(client, token):
    a = make_app(client, token, "发信应用")
    r = client.post("/message", json={"message": "只有正文"},
                    headers={"X-App-Token": a["token"]})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["message"] == "只有正文"
    assert body["title"] == ""
    assert body["priority"] == 5  # 默认优先级
    assert body["app_id"] == a["id"]
    assert body["app_name"] == "发信应用"


def test_post_message_full_fields(client, token):
    a = make_app(client, token, "全字段应用")
    r = client.post("/message",
                    json={"title": "磁盘告警", "message": "根分区 95%", "priority": 9},
                    headers={"X-App-Token": a["token"]})
    assert r.status_code == 201
    assert r.json()["title"] == "磁盘告警"
    assert r.json()["priority"] == 9


def test_post_message_no_token_401(client):
    assert client.post("/message", json={"message": "x"}).status_code == 401


def test_post_message_wrong_token_401(client):
    r = client.post("/message", json={"message": "x"},
                    headers={"X-App-Token": "ph_nonexistent"})
    assert r.status_code == 401


def test_post_message_empty_body_400(client, token):
    a = make_app(client, token, "空正文应用")
    r = client.post("/message", json={"message": "   "},
                    headers={"X-App-Token": a["token"]})
    assert r.status_code == 400


# ---------- 消息中心 ----------

def test_message_list_and_filter(client, token):
    a1 = make_app(client, token, "筛选甲")
    a2 = make_app(client, token, "筛选乙")
    client.post("/message", json={"title": "甲一", "message": "a1"},
                headers={"X-App-Token": a1["token"]})
    client.post("/message", json={"title": "乙一", "message": "a2"},
                headers={"X-App-Token": a2["token"]})
    all_msgs = client.get("/api/messages", headers=auth(token)).json()
    titles = [m["title"] for m in all_msgs]
    assert "甲一" in titles and "乙一" in titles
    only_a1 = client.get("/api/messages", params={"app_id": a1["id"]},
                         headers=auth(token)).json()
    assert len(only_a1) == 1 and only_a1[0]["title"] == "甲一"
    # 倒序：后发的在前面
    ids = [m["id"] for m in all_msgs]
    assert ids == sorted(ids, reverse=True)


def test_delete_single_message(client, token):
    a = make_app(client, token, "删消息应用")
    m = client.post("/message", json={"message": "删我"},
                    headers={"X-App-Token": a["token"]}).json()
    r = client.delete(f"/api/messages/{m['id']}", headers=auth(token))
    assert r.status_code == 200
    msgs = client.get("/api/messages", params={"app_id": a["id"]},
                      headers=auth(token)).json()
    assert msgs == []
    assert client.delete(f"/api/messages/{m['id']}",
                         headers=auth(token)).status_code == 404


def test_clear_messages_scoped_and_all(client, token):
    a = make_app(client, token, "清空应用")
    b = make_app(client, token, "保留应用")
    for who, appobj in (("a1", a), ("a2", a), ("b1", b)):
        client.post("/message", json={"message": who},
                    headers={"X-App-Token": appobj["token"]})
    r = client.request("DELETE", "/api/messages", params={"app_id": a["id"]},
                       headers=auth(token))
    assert r.status_code == 200 and r.json()["deleted"] == 2
    rest = client.get("/api/messages", headers=auth(token)).json()
    assert all(m["app_id"] == b["id"] for m in rest if m["app_id"] in (a["id"], b["id"]))
    r = client.request("DELETE", "/api/messages", headers=auth(token))
    assert r.status_code == 200
    assert client.get("/api/messages", headers=auth(token)).json() == []


# ---------- SSE ----------

def test_stream_requires_auth(client):
    assert client.get("/api/stream").status_code == 401
    assert client.get("/api/stream", params={"token": "bad"}).status_code == 401


def test_stream_receives_pushed_message(client, token):
    """开着 SSE 连接发一条消息，断言连接真的收到推送。"""
    import queue
    import threading

    a = make_app(client, token, "SSE应用")
    received: "queue.Queue[str]" = queue.Queue()

    def reader():
        with client.stream("GET", "/api/stream", headers=auth(token)) as r:
            assert r.status_code == 200
            for line in r.iter_lines():
                received.put(line)
                if "SSE探针标题" in line:
                    return

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    # 等 ready 事件，确认连接已建立再发消息
    deadline = 10
    ready = False
    import time as _time
    start = _time.time()
    seen = []
    while _time.time() - start < deadline:
        try:
            line = received.get(timeout=1)
        except queue.Empty:
            continue
        seen.append(line)
        if "ready" in line:
            ready = True
            break
    assert ready, f"没收到 ready 事件，已收到：{seen}"

    client.post("/message", json={"title": "SSE探针标题", "message": "实时推送验证"},
                headers={"X-App-Token": a["token"]})
    start = _time.time()
    got = False
    while _time.time() - start < deadline:
        try:
            line = received.get(timeout=1)
        except queue.Empty:
            continue
        if "SSE探针标题" in line:
            got = True
            break
    assert got, "SSE 连接没有收到新消息推送"
    t.join(timeout=2)


# ---------- 改密 ----------

def test_change_password_flow(client):
    tok = login(client)  # 初始密码登录
    r = client.post("/api/change-password",
                    json={"current_password": "wrong", "new_password": "newpass1"},
                    headers=auth(tok))
    assert r.status_code == 400
    r = client.post("/api/change-password",
                    json={"current_password": "admin123", "new_password": "newpass1"},
                    headers=auth(tok))
    assert r.status_code == 200
    me = client.get("/api/me", headers=auth(tok)).json()
    assert me["must_change_password"] is False
    assert client.post("/api/login",
                       json={"username": "admin", "password": "admin123"}).status_code == 401
    tok2 = login(client, password="newpass1")
    assert tok2
    # 改回初始密码，避免影响其他测试（模块级共享库，按声明顺序执行到这里已是末尾）
    r = client.post("/api/change-password",
                    json={"current_password": "newpass1", "new_password": "admin123"},
                    headers=auth(tok2))
    assert r.status_code == 200


# ---------- P1-2 回归：SSE 会话令牌只认请求头 ----------

def test_stream_query_token_rejected(client, token):
    """P1-2：即使带的是有效登录令牌，走查询参数也要 401。"""
    r = client.get("/api/stream", params={"token": token})
    assert r.status_code == 401


# ---------- P1-3 回归：改密作废其他会话 ----------

def test_change_password_revokes_other_sessions(client):
    """P1-3：改密后其他会话 401、当前会话保持有效。"""
    t1 = login(client)
    t2 = login(client)
    assert t1 != t2
    r = client.post(
        "/api/change-password",
        json={"current_password": "admin123", "new_password": "tmpnew99"},
        headers=auth(t1),
    )
    assert r.status_code == 200
    assert client.get("/api/me", headers=auth(t1)).status_code == 200
    assert client.get("/api/me", headers=auth(t2)).status_code == 401
    # 改回初始密码，用当前有效的会话
    r = client.post(
        "/api/change-password",
        json={"current_password": "tmpnew99", "new_password": "admin123"},
        headers=auth(t1),
    )
    assert r.status_code == 200
    assert client.get("/api/me", headers=auth(t1)).status_code == 200


# ---------- P1-4 回归：初始用户只在 users 表为空时创建 ----------

def test_init_db_seeds_only_when_empty(monkeypatch):
    """P1-4：已有用户后，换 PH_INITIAL_USERNAME 再 init 不应插入新账号。"""
    import sqlite3

    import app as ph

    fresh = str(Path(tempfile.mkdtemp()) / "seed.db")
    monkeypatch.setattr(ph, "DB_PATH", fresh)
    monkeypatch.setattr(ph, "INITIAL_USERNAME", "seededuser")
    ph.init_db()
    rows = sqlite3.connect(fresh).execute(
        "SELECT username, must_change_password FROM users"
    ).fetchall()
    assert len(rows) == 1 and rows[0][0] == "seededuser" and rows[0][1] == 1

    monkeypatch.setattr(ph, "INITIAL_USERNAME", "intruder")
    ph.init_db()
    names = [r[0] for r in sqlite3.connect(fresh).execute("SELECT username FROM users")]
    assert names == ["seededuser"]


# ---------- P1-5 回归：安全响应头，且 SSE 流不被打断 ----------

def test_security_headers(client):
    """P1-5：普通响应带齐 4 个安全头；SSE 用例本身走中间件证明流没被吃掉。"""
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("referrer-policy") == "no-referrer"
    assert r.headers.get("content-security-policy") == "frame-ancestors 'none'"
    r = client.get("/health")
    assert r.headers.get("x-frame-options") == "DENY"
    r = client.get("/api/apps")  # 未登录 401 也要带头
    assert r.status_code == 401
    assert r.headers.get("x-frame-options") == "DENY"


# ---------- P2-2 回归：自动文档页关闭 ----------

def test_docs_endpoints_disabled(client):
    """P2-2：/docs、/redoc、/openapi.json 未登录不可见（直接关闭）。"""
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
