# pushhub 修复记录

只改 `review.md` 清单里的 P1。P0 没有。每条修完立刻验证。测试文件、依赖版本、LICENSE、UPSTREAM 都没动。

## P1-1 默认监听全部网卡

- 问题编号：P1-1
- 文件：`app.py:614-617`
- 改法：`uvicorn.run` 的 `host` 从写死的 `0.0.0.0` 改为 `os.environ.get("PH_HOST", "127.0.0.1")`。不设 `PH_HOST` 时只听回环；需要给局域网用时显式设 `PH_HOST`。

验证 1：全量 pytest

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

输出（exit 0）：

```
23 passed, 1 warning in 1.84s
```

验证 2：不设 `PH_HOST`，端口 8011，回环与其他本机 IPv4 对照（`verify_p1_1.py`，exit 0）

```
LOOPBACK_STATUS 200
LOOPBACK_BODY {"status":"ok","app":"pushhub","subscribers":0}
HOST_IPV4 100.69.58.124,192.168.31.86
OTHER_REFUSED 100.69.58.124 ConnectTimeout
OTHER_REFUSED 192.168.31.86 ConnectTimeout
STOPPED 1
```

`127.0.0.1:8011/health` 返回 200。同一进程对 `192.168.31.86` 和 `100.69.58.124` 的 8011 端口连接超时，说明没有在这两块网卡上接请求。`STOPPED 1` 是 terminate 的退出码。

## P1-2 登录令牌可以放在 URL 里

- 问题编号：P1-2
- 文件：`app.py:192-193`（注释）、`app.py:568-575`（`/api/stream`）
- 改法：去掉查询参数 `token`。没有 `Authorization: Bearer` 时会话令牌按空字符串处理，`?token=` 里即使放了有效登录令牌也不再认。

验证 1：全量 pytest

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

输出（exit 0）：

```
23 passed, 1 warning in 1.81s
```

验证 2：`verify_p1_2.py`（exit 0）。有效查询参数被拒绝，请求头里的同一令牌仍能建立 SSE。

```
LOGIN 200
BAD_QUERY 401
VALID_QUERY 401
HEADER_STATUS 200
HEADER_READY True
```

## P1-3 改密不使其他会话失效

- 问题编号：P1-3
- 文件：`app.py:340-369`（`change_password`）
- 改法：更新口令哈希的同一事务里执行 `DELETE FROM sessions WHERE user_id = ? AND token != ?`，只保留这次请求的 Bearer 令牌。

验证 1：全量 pytest（里面的 `test_change_password_flow` 仍用改密前的那个令牌访问 `/api/me`）

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

输出（exit 0）：

```
23 passed, 1 warning in 1.81s
```

验证 2：`verify_p1_3.py`（exit 0）。两个会话都登录成功；用 A 改密后 A 仍是 200，B 变为 401；旧密码 401，新密码 200。

```
LOGIN_A 200
LOGIN_B 200
CHANGE 200
CURRENT_SESSION 200 False
OTHER_SESSION 401
OLD_PASSWORD 401
NEW_PASSWORD 200
```

## P1-4 换初始用户名会再插入全权限账号

- 问题编号：P1-4
- 文件：`app.py:87-94`（`init_db`）
- 改法：原来按「该用户名不存在」就 `INSERT`。改成 `SELECT COUNT(*)`，只有 `users` 表为空才创建初始用户。首次启动仍使用 `PH_INITIAL_USERNAME` / `PH_INITIAL_PASSWORD`。库里已经有用户时，再改这两个环境变量不会多出一个账号，也不会改已有密码。

验证 1：全量 pytest

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

输出（exit 0）：

```
23 passed, 1 warning in 1.90s
```

验证 2：`verify_p1_4.py`（exit 0）。同一数据库先以 `admin` 启动，再以 `PH_INITIAL_USERNAME=intruder` 启动。

```
ATTEMPT_USER admin
ATTEMPT_STATUS 200
ADMIN_STATUS 200
COUNT 1
NAMES admin
ATTEMPT_USER intruder
ATTEMPT_STATUS 401
ADMIN_STATUS 200
COUNT 1
NAMES admin
```

第二次启动没有插入 `intruder`，`intruder` / `intruderpass` 登录 401，原来的 `admin` / `admin123` 仍是 200。

## P1-5 页面可被外站 iframe 嵌套

- 问题编号：P1-5
- 文件：`app.py:106-137`（`SecurityHeadersMiddleware`，并在 `app.py:137` `add_middleware`）
- 改法：加了一层只改 ASGI `http.response.start` 头、不读取响应体的中间件。响应带 `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`、`Content-Security-Policy: frame-ancestors 'none'`。没有用 `BaseHTTPMiddleware`，避免把 SSE 流缓冲掉。

验证 1：全量 pytest（含 SSE 用例）

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

输出（exit 0）：

```
23 passed, 1 warning in 1.84s
```

验证 2：`verify_p1_5.py`（exit 0）。首页、健康检查、未登录 401、SSE 都带上这四个头，SSE 仍收到 ready。

```
PATH / 200
x-frame-options DENY
x-content-type-options nosniff
referrer-policy no-referrer
content-security-policy frame-ancestors 'none'
PATH /health 200
x-frame-options DENY
x-content-type-options nosniff
referrer-policy no-referrer
content-security-policy frame-ancestors 'none'
PATH /api/apps 401
x-frame-options DENY
x-content-type-options nosniff
referrer-policy no-referrer
content-security-policy frame-ancestors 'none'
SSE 200
sse-x-frame-options DENY
sse-x-content-type-options nosniff
sse-referrer-policy no-referrer
sse-content-security-policy frame-ancestors 'none'
SSE_READY True
```

## 全量重跑

五项都落地之后重跑 README 里的两步。没有失败项。Starlette 关于 `httpx2` 的弃用警告还在，测试是通过的。没有改测试，也没有改依赖版本。

命令：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

输出（exit 0）：

```
23 passed, 1 warning in 1.82s
```

命令：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_live.py
```

输出（exit 0）：

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

P2 九项没有改。P0 没有。

## git status

收尾命令：

```
git -C E:\muse-bridge\in\TASK-022-pushhub status --porcelain
```

输出：

```
 M app.py
```
