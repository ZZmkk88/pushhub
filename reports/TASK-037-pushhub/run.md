# TASK-037-pushhub 执行记录

开工：2026-10-21 本地验收 pushhub 仓库。

## 0. 环境探查

命令：`python --version`

```
Python 3.11.9
```

命令：`Get-ChildItem -Force -Name`；`git status --porcelain`

```
.git
static
tests
.gitignore
app.py
DECISIONS.md
LICENSE
NOTES.md
README.md
requirements-dev.txt
requirements.txt
UPSTREAM.md
---GIT---
（porcelain 空，工作区干净）
```

README Windows 步骤使用 `py -m venv .venv`。`where.exe py` 输出 `C:\Windows\py.exe`，启动器存在。为避免把虚拟环境写进待审仓库，venv 放到 `E:\muse-bridge\work\TASK-037-pushhub\venv`。依赖仍按仓库 requirements 安装。

## 1. 安装依赖

命令：

```
python -m venv E:\muse-bridge\work\TASK-037-pushhub\venv
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-037-pushhub\requirements-dev.txt
```

`requirements-dev.txt` 第一行是 `-r requirements.txt`，所以运行时依赖和测试依赖一次装齐。退出码 0。摘要：

```
Successfully installed ... fastapi-0.156.4 ... uvicorn-0.54.0 ... python-multipart-0.0.32 ... httpx-0.28.1 ... pytest-9.1.1 ... starlette-1.9.0 pydantic-2.14.1
```

版本与 requirements 锁定一致，没有依赖冲突。

## 2. 全量 pytest

命令：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest E:\muse-bridge\in\TASK-037-pushhub\tests -q -p no:cacheprovider
```

输出：

```
.........................                                                [100%]
============================== warnings summary ===============================
..\..\work\TASK-037-pushhub\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-037-pushhub\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
25 passed, 1 warning in 2.95s
```

退出码 0。25 项通过。警告来自依赖（Starlette 提示 httpx 测试客户端将弃用），测试本身没有失败。

## 3. 真实流程自测 live_selftest

命令：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-037-pushhub\tests\live_selftest.py
```

退出码 0。脚本自己占用 8137，结束时 `proc.terminate()`。摘要：

```
[PASS] 01 服务启动 + 健康检查
[PASS] 02 首页返回 200 且是前端页
[PASS] 11 SSE 连接建立并收到 ready
[PASS] 14 SSE 连接实时收到新消息推送
[PASS] 25 删除应用成功
ALL PASS（共 25 项检查）
```

中间 03–10、12–13、15–24 也全部是 PASS，输出里没有 FAIL。

## 4. 按 README 起服务（默认主机和端口）

命令：`E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-037-pushhub\serve_check.py`

该脚本用仓库里的 `app.py` 起子进程，未设置 `PH_HOST` / `PH_PORT`（走默认值）。`PH_DB_PATH` 指到 `E:\muse-bridge\work\TASK-037-pushhub\serve.db`，避免在仓库里生成数据库。请求用 httpx，没有用 curl。查完后 `proc.terminate()`。

输出片段：

```
HEALTH 200 {"status":"ok","app":"pushhub","subscribers":0}
INDEX 200 len=20661 ctype=text/html; charset=utf-8
INDEX_HAS_PUSHHUB True
INDEX_HAS_LOGIN True
INDEX_SNIP <title>pushhub · 推送中心</title>
DOCS 200 len=1006
STOPPED 1
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:52184 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:56356 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:56357 - "GET /docs HTTP/1.1" 200 OK
```

`STOPPED 1` 是 Windows 上 `terminate()` 的退出码，日志里没有启动错误。服务已关掉。

## 5. 额外探针（测试没覆盖的行为）

命令：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-037-pushhub\probe.py
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-037-pushhub\probe_thread.py
```

`probe.py` 关键输出：

```
SQLI_LOGIN 401 {"detail":"用户名或密码不正确"}
TOKEN_LEN 35 PREFIX ph_ RAND_LEN 32
PRIORITY_0 201 0
PRIORITY_-3 201 -3
PRIORITY_100 201 100
BIG_MSG 201 bytes_approx 20000 sec=0.010
LONG_PW_LOGIN 401 sec=0.078 pwlen 20000
SHORT_PW_LOGIN 401 sec=0.070
UNKNOWN_LONG_PW 401 sec=0.003
ME_TOKEN1 200
ME_TOKEN2 401
POST_AFTER_REVOKE 201
SSE_GOT_AFTER_REVOKE True
SUB_AFTER_REVOKE_STREAM_STILL_OPEN {'status': 'ok', 'app': 'pushhub', 'subscribers': 1}
```

改密后另一个会话的 `/api/me` 已是 401，但它开着的 SSE 仍收到 `title: AFTER_REVOKE`。

`probe_thread.py`：真实 uvicorn，各发 20 条。`nodebug` 与 `PYTHONASYNCIODEBUG=1` 都是 `POST_STATUSES [201]` 且 `SSE_UNIQUE 20 missing []`。结尾的 WinError 10054 是探测脚本 `terminate()` 关掉服务时，读流线程被断开，不是业务失败。

`probe_debug.py`（TestClient + `PYTHONASYNCIODEBUG=1`）在打印 deprecation 警告后没有再输出，已用任务终止接口停掉。同一环境变量下真实 uvicorn 能收齐 20 条，所以这次挂起算测试客户端互锁，不记成服务缺陷。

## 6. 修复 P1-1 之后的验证

只改了 `app.py`。针对作废会话的探针：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-037-pushhub\probe_revoke.py
READY1 True READY2 True
SUB_OPEN 2
CHANGE 200
ME1 200
ME2 401
POST 201
LIVE_GOT True
REVOKED_GOT False
SUB_AFTER 1
```

退出码 0。

全量 pytest（退出码 0）：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest E:\muse-bridge\in\TASK-037-pushhub\tests -q -p no:cacheprovider
25 passed, 1 warning in 2.52s
```

live_selftest（退出码 0）：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-037-pushhub\tests\live_selftest.py
ALL PASS（共 25 项检查）
```

收尾：

```
git status --porcelain
 M app.py
```
