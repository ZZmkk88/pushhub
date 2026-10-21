# pushhub 修复记录

只改 review.md 清单里的 P1-1、P1-2、P1-3。没有 P0。

## P1-1 默认监听全部网卡

- 问题编号：P1-1
- 文件:行号：`app.py:585-590`（原 app.py:575 的 `host="0.0.0.0"`。后面改密函数变长，行号下移到这里）
- 改法：`uvicorn.run` 的 host 改为 `os.environ.get("PH_HOST", "127.0.0.1")`。不设置 `PH_HOST` 时只听 127.0.0.1；要对局域网开放时显式设 `PH_HOST=0.0.0.0`。

### 验证

命令：`python E:\muse-bridge\work\TASK-015-pushhub\start_server.py`（`PH_PORT=18765`，未设置 `PH_HOST`）

```
INFO:     Uvicorn running on http://127.0.0.1:18765 (Press CTRL+C to quit)
```

命令：`netstat -ano | findstr :18765`

```
TCP    127.0.0.1:18765        0.0.0.0:0              LISTENING       14436
```

没有 `0.0.0.0:18765` 的 LISTENING 行。

命令：`python E:\muse-bridge\work\TASK-015-pushhub\check_health.py`

```
HEALTH 200 {"status":"ok","app":"pushhub","subscribers":0}
INDEX 200 pushhub True
```

命令：`python -m pytest tests/test_app.py::test_health tests/test_app.py::test_index_page -q`

```
2 passed, 1 warning in 0.84s
```

服务已停止。

## P1-2 SSE 不再接受 URL 里的会话令牌

- 问题编号：P1-2
- 文件:行号：`app.py:541-546`（去掉查询参数 `token`）；注释 `app.py:164`。原位置是 app.py:530-534，改密函数变长后下移
- 改法：`/api/stream` 只从 `Authorization: Bearer` 取会话令牌。查询参数即使带了有效令牌也不再使用。

### 验证

命令：`python -m pytest tests/test_app.py::test_stream_requires_auth tests/test_app.py::test_stream_receives_pushed_message -q`

```
2 passed, 1 warning in 0.87s
```

命令：`python E:\muse-bridge\work\TASK-015-pushhub\check_p1_2.py`（独立数据库 `p1-2.db`）

```
LOGIN 200
QUERY_VALID 401
NO_AUTH 401
QUERY_BAD 401
HEADER 200
HEADER_LINE event: ready
```

修复前同一请求 `GET /api/stream?token=<有效令牌>` 是 `STREAM_QUERY_STATUS 200`。现在是 401。请求头方式仍收到 `event: ready`。

## P1-3 改密后作废其他会话

- 问题编号：P1-3
- 文件:行号：`app.py:312-341`，删除语句在 `app.py:333-337`
- 改法：改密成功时，在同一事务里执行 `DELETE FROM sessions WHERE user_id = ? AND token != ?`。当前请求的 Bearer 令牌保留，其他会话删除。取不到当前令牌时不删，避免把这次登录也清掉。

### 验证

命令：`python -m pytest tests/test_app.py::test_change_password_flow -q`

```
1 passed, 1 warning in 1.33s
```

命令：`python E:\muse-bridge\work\TASK-015-pushhub\check_p1_3.py`（独立数据库 `p1-3.db`）

```
TWO_TOKENS True
CHANGE 200 {"ok":true}
OLD_SESSION 401 {"detail":"登录已过期，请重新登录"}
CURRENT_SESSION 200 {"username":"admin","must_change_password":false}
OLD_PASSWORD 401
NEW_PASSWORD 200
```

修复前旧会话的 `/api/me` 是 `OLD_SESSION_AFTER_PW 200`。现在是 401。当前会话和测试用的原令牌仍然有效。

## 全量回归

命令：`python -m pytest tests/ -q`

```
.......................                                                  [100%]
============================== warnings summary ===============================
..\..\env\TASK-015-pushhub\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-015-pushhub\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
23 passed, 1 warning in 1.91s
```

23 项通过。警告仍是 FastAPI/Starlette 对 httpx 的弃用提示，没有失败项。

命令：`python tests/live_selftest.py`

```
[PASS] 01 服务启动 + 健康检查 
[PASS] 02 首页返回 200 且是前端页 
[PASS] 03 错误密码登录 401 
[PASS] 04 默认账号登录成功 
[PASS] 05 首次登录提示改密 
[PASS] 06 未带登录 Token 拉应用列表 401 
[PASS] 07 新建应用 201 
[PASS] 08 应用自动生成令牌 
[PASS] 09 无令牌发消息 401 
[PASS] 10 错令牌发消息 401 
[PASS] 11 SSE 连接建立并收到 ready 
[PASS] 12 带令牌发消息 201 priority=8
[PASS] 13 消息优先级记录正确 
[PASS] 14 SSE 连接实时收到新消息推送 
[PASS] 15 消息列表能查到刚发的消息 
[PASS] 16 再发一条消息 201 
[PASS] 17 按应用筛选返回 2 条 
[PASS] 18 按不存在的应用筛选返回空 
[PASS] 19 单条删除消息成功 
[PASS] 20 删除后剩 1 条 
[PASS] 21 重新生成令牌成功 
[PASS] 22 旧令牌发消息 401 
[PASS] 23 清空全部消息 
[PASS] 24 清空后列表为空 
[PASS] 25 删除应用成功 

ALL PASS（共 25 项检查）
```

没有失败项。

## 收尾 git status

命令：`git status --porcelain`

```
 M app.py
```

工作区只改了 `app.py`。改动仍在，未提交。


