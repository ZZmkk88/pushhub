# pushhub 验收报告

结论：仓库能装、能测、能起。`pytest` 23 项通过，`live_selftest.py` 25 项通过，服务首页和 `/health` 返回 200。没有 P0。有 3 条已复现的 P1（全网卡监听、SSE 用查询参数收会话令牌、改密不作废其他会话），本次只改这 3 条，都在 `app.py`。许可证在仓库内部自洽；上游 commit 与版权原文未联网核实。

## 本地跑通记录

解释器：`E:\muse-bridge\env\TASK-015-pushhub\Scripts\python.exe`，Python 3.11.9。运行时依赖事先已在该环境中，版本与 `requirements.txt` 一致（fastapi 0.156.4、uvicorn 0.54.0、python-multipart 0.0.32）。

### 环境限制（不计入项目缺陷）

命令 `py -3 --version` 退出码 1，原文：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

README.md:39 的 `py -m venv .venv` 因此没按字面执行。改用 PATH 上的 `python`。

8000 端口已被其他任务占用。`netstat -ano | findstr :8000`：

```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       29612
```

PID 29612 的命令行是 `E:\muse-bridge\work\TASK-014-weblens\start_server.py`。未结束该进程。本次用 README 写明的 `PH_PORT` 改到 18765。

### 安装开发依赖

命令：`python -m pip install -r requirements-dev.txt`（仓库根目录）。退出码 0，约 36.5 秒。新装 httpx 0.28.1、pytest 9.1.1。末行：

```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

### 全量测试

命令：`python -m pytest tests/ -q`。退出码 0。

```
23 passed, 1 warning in 2.46s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 测试没有失败。

命令：`python tests/live_selftest.py`。退出码 0。脚本在 8137 端口起临时服务并自己关掉。末行：

```
ALL PASS（共 25 项检查）
```

其中 `[PASS] 01 服务启动 + 健康检查`、`[PASS] 14 SSE 连接实时收到新消息推送`。

### 起服务

命令：`python E:\muse-bridge\work\TASK-015-pushhub\start_server.py`（设置 `PH_DB_PATH` 到工作目录、`PH_PORT=18765`，再执行仓库 `app.py`）。日志：

```
INFO:     Uvicorn running on http://0.0.0.0:18765 (Press CTRL+C to quit)
```

`netstat -ano | findstr :18765`：

```
TCP    0.0.0.0:18765          0.0.0.0:0              LISTENING       8380
```

探针 `probe_server.py`（httpx，未使用 curl）：

```
HEALTH 200 {"status":"ok","app":"pushhub","subscribers":0}
INDEX 200 pushhub_in_body True bytes 22064
DOCS 200
OPENAPI 200
POST_MESSAGE 201 {"id":1,"app_id":1,"app_name":"probe","title":"备份完成","message":"数据库备份成功","priority":5,"created_at":"2026-10-21T09:42:33Z"}
STREAM_QUERY_STATUS 200 text/event-stream; charset=utf-8
STREAM_QUERY_LINE event: ready
OLD_SESSION_AFTER_PW 200 {"username":"admin","must_change_password":false}
```

服务已停止。之后 `netstat` 上 18765 不再有 LISTENING，只剩 TIME_WAIT。

另：`len(secrets.token_urlsafe(24))` 输出 `32`，`len(secrets.token_urlsafe(20))` 输出 `27`。探针里应用令牌长度为 35（`ph_` + 32）。

SSE 连续 40 条（`probe_sse.py`）：`SENT 40 SSE_DATA_LINES 40`，`MISSING COUNT 0`。

## README 与实际不符处

对照过且与代码一致、此处不单列的说法：24 小时会话（app.py:27）、默认账号与 `PH_INITIAL_USERNAME` / `PH_INITIAL_PASSWORD`（app.py:28-29，仅在用户不存在时插入，app.py:87-96）、数据库默认 `data/pushhub.db` 与 `PH_DB_PATH`（app.py:26）、`PH_PORT`（app.py:575）、`POST /message` 成功 201、缺令牌或错令牌 401（app.py:435-461，探针 POST 返回 201）、优先级默认 5、页面分档 ≥8 / 5–7 / ≤4（static/index.html:214-218）、删应用级联删消息、测试命令与 8137 端口（tests/live_selftest.py:20）。

不符：

1. README.md:45 写启动后打开 `http://127.0.0.1:8000`。app.py:575 实际是 `host="0.0.0.0"`。本次启动日志是 `Uvicorn running on http://0.0.0.0:18765`，netstat 为 `0.0.0.0:18765 LISTENING`。本机用 127.0.0.1 能访问，进程同时监听全部 IPv4 网卡。
2. README.md:54 示例令牌写成 `ph_xxxxxxxxxxxx`（`ph_` 后 12 个 x）。app.py:248 是 `"ph_" + secrets.token_urlsafe(24)`。`token_urlsafe(24)` 实测长度 32，探针中的令牌总长 35。示例不能当成真实长度。

NOTES 与代码不符（不是 README 正文，一并记录）：

3. NOTES.md:20 写「令牌 27 字符随机部分」。对应代码是 app.py:248 的 `secrets.token_urlsafe(24)`，实测随机部分 32 字符。`token_urlsafe(20)` 才是 27。
4. NOTES.md:30 写浏览器端用 Authorization 头，「不用把 token 塞进 URL」。app.py:530-534 在没有 Bearer 头时改读查询参数 `token`。探针 `GET /api/stream?token=<登录令牌>` 返回 200，并收到 `event: ready`。前端 static/index.html:400 确实只带头，不走查询参数。

## 许可证与署名核查

仓库内三份声明互相一致，没有改 LICENSE / UPSTREAM。

- LICENSE:1-3 是 MIT，版权行 `Copyright (c) 2026 pushhub contributors`。正文是常见 MIT 许可文本。
- README.md:6-7 写设计学习了同类工具的思路，代码为独立实现，溯源见 UPSTREAM.md。
- UPSTREAM.md:5-8 记录上游 `https://github.com/gotify/server`，commit `f4de6199f080c670f45d9821578d7e37e8024619`，许可证 MIT，署名 `Copyright (c) 2018 jmattheis`。UPSTREAM.md:16 说该版权行逐字来自上游 LICENSE。UPSTREAM.md:19-20 说本项目是 Python 独立重写，未复制上游 Go 源码。
- NOTES.md:5、NOTES.md:22 与 UPSTREAM 的仓库、commit、版权行相同。NOTES.md:22-23 写不使用上游 logo。

在仓库内检索 `gotify` 与 `jmattheis`：只出现在 NOTES.md 与 UPSTREAM.md。`app.py`、`static/index.html`、`tests/` 没有这些字样，也没有 Go 源码片段。这与「未复制上游源码」的声明一致。MIT 要求在软件副本中保留版权声明；独立重写不把上游版权行放进 LICENSE，和上述声明不冲突。

未联网核对 GitHub 上的 commit 是否存在、版权行是否与上游 LICENSE 逐字相同（本任务禁止抓取外部页面）。这两句维持「未核实」，不据此改 LICENSE 或 UPSTREAM。

## 分级修复清单

### P0

无。测试与服务均已跑通。`py` 启动器损坏、8000 端口被 TASK-014 占用，记为环境限制。

### P1（本次修复，共 3 项）

1. P1-1 全网卡监听加默认口令。文件 app.py:575。`uvicorn.run(..., host="0.0.0.0", ...)`，同时 app.py:29 默认密码 `admin123`，static/index.html:114 把该口令写在登录页上。探针见到进程监听 `0.0.0.0`。修法：默认改为 `127.0.0.1`，需要对外时用环境变量 `PH_HOST` 显式指定。
2. P1-2 会话令牌可放进 URL。文件 app.py:530-534。`/api/stream` 在 Authorization 不是 Bearer 时使用查询参数 `token`。探针带有效 `?token=` 得到 200 和 `event: ready`。修法：只接受 Authorization 头里的 Bearer 令牌，不再读取查询参数。
3. P1-3 改密后其他会话仍有效。文件 app.py:322-326。改密只更新 `users` 的口令字段。探针用令牌 2 改密后，令牌 1 访问 `/api/me` 仍是 200。修法：同一事务内删除该用户除当前会话以外的 `sessions` 行，当前这次请求的令牌保留（tests/test_app.py:303 改密后仍用原令牌访问 `/api/me`）。

### P2（本次不改）

1. app.py:259-261 `/health` 无鉴权且返回 `subscribers`；探针 `/docs` 与 `/openapi.json` 均为 200。修法：健康检查只返回 status，生产关闭文档路由。P1-1 把监听收回到本机后，暴露面已经缩小。
2. app.py:443 不限制 `priority` 范围；static/index.html:153 输入框是 0–10。修法：越界返回 400。
3. app.py:188-191 在正文校验之前就写入 `last_used_at`。空正文走 app.py:441 的 400 时，最近使用时间仍会被改掉。修法：正文合法后再更新该字段。
4. app.py:271 用 `!=` 比较口令哈希；用户不存在时不做 PBKDF2。修法：用 `hmac.compare_digest`，不存在的用户也算一次等长哈希。
5. app.py:127-133 的 `publish` 由同步路由 app.py:460 调用，直接 `asyncio.Queue.put_nowait`。本次 40 条压测全部收到，没有观测到丢消息。修法：改到事件循环线程里入队。未复现失败，本次不动推送路径。
6. NOTES.md:20 令牌随机段写成 27，实际 32；NOTES.md:58-59 已说明令牌明文存 SQLite。修法：更正 NOTES 的长度。明文存储是页面复制令牌所依赖的行为，测试要读 `token` 字段，不改。
7. 默认口令 `admin123` 被 tests/test_app.py:23 与 README.md:24 写死。改默认值会让现有测试失败。本次不改口令。
8. FastAPI 0.156 的 TestClient 对 httpx 0.28.1 发出弃用警告。测试仍通过，且不许改已钉死的依赖版本。不改 requirements。
