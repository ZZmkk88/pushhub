"""pushhub 真实流程自测：起真 uvicorn 进程，走完整用户流程。

用法：python tests/live_selftest.py（需要 httpx，即 requirements-dev.txt）
脚本会自己在 8137 端口起一个用临时数据库的服务，跑完自动关掉。
重点验证：SSE 连接开着时 POST 一条消息，连接必须实时收到推送。
"""

import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PORT = 8137
BASE = f"http://127.0.0.1:{PORT}"

checks = 0


def ok(name, cond, extra=""):
    global checks
    checks += 1
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {checks:02d} {name} {extra}")
    if not cond:
        raise AssertionError(name)


def wait_health(proc, timeout=20):
    # trust_env=False：不读环境里的代理设置（云端 no_proxy 含 [::1] 等条目，
    # httpx 解析会报 InvalidURL，与 dailymemo 当时踩的坑相同）
    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            raise RuntimeError("服务进程提前退出")
        try:
            r = httpx.get(BASE + "/health", timeout=2, trust_env=False)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError("等服务启动超时")


def main():
    tmp = Path(tempfile.mkdtemp())
    env = dict(os.environ)
    env["PH_DB_PATH"] = str(tmp / "live.db")
    env["PH_PORT"] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, "app.py"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_health(proc)
        ok("服务启动 + 健康检查", True)

        c = httpx.Client(base_url=BASE, timeout=10, trust_env=False)

        r = c.get("/")
        ok("首页返回 200 且是前端页", r.status_code == 200 and "pushhub" in r.text)

        r = c.post("/api/login", json={"username": "admin", "password": "wrong"})
        ok("错误密码登录 401", r.status_code == 401)

        r = c.post("/api/login", json={"username": "admin", "password": "admin123"})
        ok("默认账号登录成功", r.status_code == 200)
        data = r.json()
        ok("首次登录提示改密", data["must_change_password"] is True)
        auth = {"Authorization": "Bearer " + data["token"]}

        r = c.get("/api/apps")
        ok("未带登录 Token 拉应用列表 401", r.status_code == 401)

        r = c.post("/api/apps", json={"name": "备份脚本", "description": "每晚备份"},
                   headers=auth)
        ok("新建应用 201", r.status_code == 201)
        app1 = r.json()
        ok("应用自动生成令牌", bool(app1["token"]) and app1["token"].startswith("ph_"))
        app_token = app1["token"]

        r = c.post("/message", json={"message": "没令牌的"})
        ok("无令牌发消息 401", r.status_code == 401)
        r = c.post("/message", json={"message": "错令牌的"},
                   headers={"X-App-Token": "ph_xxx"})
        ok("错令牌发消息 401", r.status_code == 401)

        # --- SSE 实时推送：先开连接，确认 ready，再发消息 ---
        lines: "queue.Queue[str]" = queue.Queue()

        def sse_reader():
            with httpx.stream("GET", BASE + "/api/stream", headers=auth,
                              timeout=30, trust_env=False) as resp:
                for line in resp.iter_lines():
                    lines.put(line)
                    if "夜间备份完成" in line:
                        return

        t = threading.Thread(target=sse_reader, daemon=True)
        t.start()
        ready = False
        start = time.time()
        while time.time() - start < 10:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                continue
            if "ready" in line:
                ready = True
                break
        ok("SSE 连接建立并收到 ready", ready)

        r = c.post("/message",
                   json={"title": "夜间备份完成", "message": "数据库备份成功，耗时 42 秒",
                         "priority": 8},
                   headers={"X-App-Token": app_token})
        ok("带令牌发消息 201", r.status_code == 201, f"priority={r.json()['priority']}")
        ok("消息优先级记录正确", r.json()["priority"] == 8)

        got = False
        start = time.time()
        while time.time() - start < 10:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                continue
            if "夜间备份完成" in line:
                got = True
                break
        ok("SSE 连接实时收到新消息推送", got)
        t.join(timeout=2)

        r = c.get("/api/messages", headers=auth)
        msgs = r.json()
        ok("消息列表能查到刚发的消息",
           len(msgs) == 1 and msgs[0]["app_name"] == "备份脚本")
        msg_id = msgs[0]["id"]

        r = c.post("/message", json={"title": "第二条", "message": "给筛选和删除用"},
                   headers={"X-App-Token": app_token})
        ok("再发一条消息 201", r.status_code == 201)
        r = c.get("/api/messages", params={"app_id": app1["id"]}, headers=auth)
        ok("按应用筛选返回 2 条", len(r.json()) == 2)
        r = c.get("/api/messages", params={"app_id": 99999}, headers=auth)
        ok("按不存在的应用筛选返回空", r.json() == [])

        r = c.delete(f"/api/messages/{msg_id}", headers=auth)
        ok("单条删除消息成功", r.status_code == 200)
        r = c.get("/api/messages", headers=auth)
        ok("删除后剩 1 条", len(r.json()) == 1)

        r = c.post(f"/api/apps/{app1['id']}/regenerate-token", headers=auth)
        ok("重新生成令牌成功", r.status_code == 200 and r.json()["token"] != app_token)
        r = c.post("/message", json={"message": "旧令牌应失效"},
                   headers={"X-App-Token": app_token})
        ok("旧令牌发消息 401", r.status_code == 401)

        r = c.request("DELETE", "/api/messages", headers=auth)
        ok("清空全部消息", r.status_code == 200 and r.json()["deleted"] == 1)
        r = c.get("/api/messages", headers=auth)
        ok("清空后列表为空", r.json() == [])

        r = c.delete(f"/api/apps/{app1['id']}", headers=auth)
        ok("删除应用成功", r.status_code == 200)

        print(f"\nALL PASS（共 {checks} 项检查）")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
