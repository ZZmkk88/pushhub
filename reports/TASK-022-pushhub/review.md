# pushhub 验收报告

结论：仓库能在本机 Python 3.11.9 上装好、测完、把服务拉起来。pytest 23 项通过，live_selftest 25 项通过，8000 端口的 `/health` 与首页都是 200。没有 P0。有 5 条 P1（监听面、登录令牌进 URL、改密不废掉其他会话、环境变量能再造一个全权限账号、页面可被嵌进外站 iframe），都在 `app.py`，本轮按清单修。

## 本地跑通记录

环境：Windows，`python --version` 为 Python 3.11.9。虚拟环境在 `E:\muse-bridge\work\TASK-022-pushhub\venv`，没有写进仓库。测试用的临时库通过 `TEMP`/`TMP` 指到同一工作目录。命令全文和输出在 `run.md`。

`py -3 --version` 失败，原文：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

这是本机 `py` 启动器指向无效的 `E:\python.exe`，标为环境限制，不算仓库缺陷。后面的步骤改用 `python`。

依赖（exit 0）：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-022-pushhub\requirements-dev.txt
```

装上的钉版本包括 fastapi==0.156.4、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1。

全量测试（exit 0，2.13s）：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
.......................                                                  [100%]
23 passed, 1 warning in 2.13s
```

警告原文是 Starlette 提示 `httpx` 与 `starlette.testclient` 的搭配已弃用、建议装 `httpx2`。测试仍然通过。不改 `requirements` 里已有版本号。

真实流程脚本（exit 0，端口 8137，脚本自己关掉进程）：

```
[PASS] 01 服务启动 + 健康检查
...
[PASS] 25 删除应用成功
ALL PASS（共 25 项检查）
```

按 README 起 `app.py`（`PH_PORT=8000`，`PH_DB_PATH` 改到工作目录，避免在仓库里留下无法删除的 `data/pushhub.db`）。结果：

```
HEALTH_STATUS 200
HEALTH_BODY {"status":"ok","app":"pushhub","subscribers":0}
INDEX_STATUS 200
INDEX_HAS_PUSHHUB True
LOGIN_STATUS 200
LOGIN_USER admin
LOGIN_MUST_CHANGE True
```

随后进程已 terminate。`STOPPED 1` 是终止后的退出码，不是启动失败。

没有用浏览器点页面。首页只核对了 HTTP 200 和 HTML 里含 `pushhub`。没有访问外网页面。没有需要抓标题的测试，因此没有「环境限制」导致的失败项。

## README 与实际不符处

以下差异按修复前的代码核对。已经改掉的行为在条目里注明，改后行号见 `fix-report.md`。

1. 修复前 `app.py:575` 是 `uvicorn.run(app, host="0.0.0.0", ...)`。`README.md:45` 只让用户打开 `http://127.0.0.1:8000`，没有写监听地址。本机用 127.0.0.1 访问是通的（见上面的 HEALTH 200），但当时进程听的是全部网卡。已按 P1-1 改为默认 `127.0.0.1`（现 `app.py:616`）。
2. `README.md:24-25` 写可用 `PH_INITIAL_USERNAME` / `PH_INITIAL_PASSWORD`「覆盖初始账号密码」。修复前 `app.py:87-96` 只在「这个用户名还不存在」时 `INSERT`，不会更新已有用户的密码；换成一个新用户名会多插一个全权限账号。P1-4 已改成 `users` 表为空才插入（现 `app.py:87-94`）。已有用户的密码仍然不会被环境变量改写。
3. `README.md:11` 和 `README.md:24` 写「首次登录提示改密」。`app.py:91-92` 插入用户时把 `must_change_password` 设为 1，`static/index.html:245` 在该标志仍为真时每次 `enterApp` 都弹窗。跳过之后，下次登录还会提示，不是只提示一次。
4. `README.md:16` 写消息「按时间倒序」。`app.py:517` 和 `app.py:523` 是 `ORDER BY m.id DESC`。单进程顺序插入时和入库时间一致；系统时钟回拨时，展示顺序跟 `created_at` 不一致。
5. `NOTES.md:20` 写「令牌 27 字符随机部分」。`app.py:277` 是 `"ph_" + secrets.token_urlsafe(24)`。本机实测 `token_urlsafe(24)` 长度为 32，加前缀后 35（`token_len.py` 输出 `token_urlsafe_24_len 32` / `app_token_len 35`）。
6. `static/index.html:153` 的输入框标题是「优先级 0-10」。`app.py:482` 对 `priority` 只做 `int(...)`，没有限制上下界。接口接受 0–10 以外的整数。

以下 README 表述和代码一致，本次跑通也覆盖到了：默认账号 `admin` / `admin123`（`app.py:28-29`）、令牌头 `X-App-Token`、`message` 必填、缺省优先级 5、成功 201、错令牌 401、`PH_PORT` / `PH_DB_PATH`（`app.py:26`、`app.py:617`）、删应用连消息一起删（`app.py:79` 的 `ON DELETE CASCADE`）、页面优先级三档（`static/index.html:214-218`）、live_selftest 使用 8137（`tests/live_selftest.py:20`）。

## 许可证与署名核查

对照的是仓库里的文件，没有访问 GitHub。

- `LICENSE:1-3`：MIT，`Copyright (c) 2026 pushhub contributors`。这是本仓库自己的许可证，版权行没有写成 gotify 或 jmattheis。
- `README.md:6-7`：写明代码为独立实现，溯源见 `UPSTREAM.md`。
- `UPSTREAM.md:5-8`：上游 `https://github.com/gotify/server`，commit `f4de6199f080c670f45d9821578d7e37e8024619`，许可证 MIT，署名 `Copyright (c) 2018 jmattheis`。
- `NOTES.md:5` 与 `NOTES.md:22-23` 的仓库、commit、版权行和 `UPSTREAM.md` 一致。`UPSTREAM.md:16` 说这行版权是从上游 LICENSE 逐字复制的。
- 仓库里没有 Go 源码，也没有上游 logo 文件。`static/index.html` 是自写页面。接口头用的是 `X-App-Token`，不是上游常见的 `X-Gotify-Key`。就本仓库内容看，没有发现把上游源码整段抄进来的痕迹。

自洽结论：在「独立重写、不携带上游源码」这个前提下，本仓库用自己的 MIT 与「2026 pushhub contributors」，同时在 `UPSTREAM.md` 里单独记下上游 MIT 和 jmattheis，两套声明不互相顶牛。`NOTES.md` 与 `UPSTREAM.md` 对上游版权行的转述也一致。

未核实（任务禁止抓取外网，本机没有上游检出）：

- commit `f4de6199f080c670f45d9821578d7e37e8024619` 是不是 2026-10-18 的默认分支 HEAD，提交说明是不是「Merge pull request #1075 ...」（`UPSTREAM.md:12-15`）。
- 上游 LICENSE 原文是不是逐字 `Copyright (c) 2018 jmattheis`，以及 logo 是否另按 CC BY 4.0 授权（`UPSTREAM.md:16-18`、`NOTES.md:22-23`）。

没有确凿反证，所以不改 `LICENSE` 和 `UPSTREAM.md`。

## 分级修复清单

P1 已改完，行号是当前文件里的改动位置。验证输出在 `fix-report.md`。P2 未改。

### P0

无。pytest、live_selftest、8000 端口健康检查和首页都已跑通。

### P1

1. **P1-1 默认监听全部网卡，且带默认口令。** `app.py:616`。修法：默认 `host` 改为 `127.0.0.1`，需要对外时用环境变量 `PH_HOST` 显式打开。
2. **P1-2 登录令牌可以放在 URL 查询参数里。** `app.py:568-575`。修法：`/api/stream` 只认 `Authorization: Bearer`，不再读 `?token=`。
3. **P1-3 改密后其他登录会话仍然有效。** `app.py:340-365`。修法：密码更新成功后，删掉该用户除当前这次请求以外的 `sessions` 行。
4. **P1-4 单用户设计下，换一个初始用户名会再插入全权限账号。** `app.py:87-94`。应用和消息都没有 `user_id`（`app.py:69-84`），新账号能看见全部令牌和消息。修法：只在 `users` 表为空时插入初始用户。
5. **P1-5 已登录页面可以被别的网站嵌进 iframe。** `app.py:106-137`。页面能删应用、看令牌（`static/index.html:330-333`）。修法：用不缓冲响应体的 ASGI 中间件加上 `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`、`Content-Security-Policy: frame-ancestors 'none'`。不用会吃掉 SSE 正文的 `BaseHTTPMiddleware`。

### P2

1. **P2-1 SSE 广播从同步接口的线程池里直接 `put_nowait`。** `app.py:156-159` 被 `app.py:499` 调用。`asyncio.Queue` 不是线程安全的；当前请求返回时事件循环会被唤醒，所以现有测试能过，空闲时推送可能要等到保活超时。修法：在 lifespan 里记下运行中的循环，`publish` 改走 `call_soon_threadsafe`。
2. **P2-2 `/docs`、`/redoc`、`/openapi.json` 默认开着。** `app.py:136`。修法：三个文档地址设为 `None`。
3. **P2-3 登录没有失败次数限制。** `app.py:294-300`。修法：同一用户名连续失败后短时间返回 429。
4. **P2-4 用户不存在时跳过口令哈希，哈希比较用的是 `!=`。** `app.py:300`。修法：缺用户也算一次哈希，并用 `hmac.compare_digest`。
5. **P2-5 过期会话只判断、不删除。** `app.py:182`、`app.py:200`。修法：查出过期行时顺手 `DELETE`。
6. **P2-6 应用名、标题、正文、优先级都没有上限。** `app.py:386`、`app.py:482`。修法：限制字符串长度，优先级收成约定范围。
7. **P2-7 前端「隐藏」令牌时仍把全文放进 `title`。** `static/index.html:283`。修法：隐藏状态下不要把完整令牌写入 DOM。
8. **P2-8 健康检查返回当前订阅数。** `app.py:289-290`。修法：对外只留 `status`。
9. **P2-9 `NOTES.md:20` 的令牌长度与 `app.py:277` 不符。** 修法：把「27 字符」改成 `token_urlsafe(24)` 的 32 字符（加前缀 `ph_` 共 35）。本轮不改 P2，因此不动 `NOTES.md`。
