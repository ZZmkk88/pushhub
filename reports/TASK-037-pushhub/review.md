# pushhub 验收审查

结论：依赖能装上，pytest 25 项通过，live_selftest 25 项通过，默认端口上的首页和 `/health` 正常。没有 P0。有 1 个 P1：会话作废后，已经打开的 SSE 仍会收到新消息。许可证与署名在仓库内部自洽；上游 commit 未联网核实。

## 本地跑通记录

环境：Python 3.11.9。`where.exe py` 得到 `C:\Windows\py.exe`。虚拟环境放在 `E:\muse-bridge\work\TASK-037-pushhub\venv`，没有写进仓库。`requirements-dev.txt` 含 `-r requirements.txt`，一次安装覆盖运行和测试。

安装命令与结果（退出码 0）：

```
python -m venv E:\muse-bridge\work\TASK-037-pushhub\venv
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-037-pushhub\requirements-dev.txt
Successfully installed ... fastapi-0.156.4 ... uvicorn-0.54.0 ... python-multipart-0.0.32 ... httpx-0.28.1 ... pytest-9.1.1
```

pytest（退出码 0）：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest E:\muse-bridge\in\TASK-037-pushhub\tests -q -p no:cacheprovider
25 passed, 1 warning in 2.95s
```

警告原文是 Starlette 的 `Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 测试没有失败。

live_selftest（退出码 0，端口 8137，脚本自己关掉进程）：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-037-pushhub\tests\live_selftest.py
[PASS] 01 服务启动 + 健康检查
[PASS] 14 SSE 连接实时收到新消息推送
ALL PASS（共 25 项检查）
```

按 README 起 `app.py`，不设 `PH_HOST` / `PH_PORT`。数据库改到工作目录 `serve.db`。

```
HEALTH 200 {"status":"ok","app":"pushhub","subscribers":0}
INDEX 200 len=20661 ctype=text/html; charset=utf-8
INDEX_HAS_PUSHHUB True
INDEX_SNIP <title>pushhub · 推送中心</title>
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

随后 `terminate()`。Windows 上退出码是 1，日志没有启动错误。服务已停。没有浏览器点选，页面行为只做到 HTTP 返回和 HTML 内容检查。

和 README 对得上、并且这次跑通了的部分：默认账号 `admin` / `admin123`、首次 `must_change_password`、`POST /message` 用 `X-App-Token`、错误令牌 401、优先级默认 5、删应用后消息不见、SSE 能收到推送。对应代码在 `app.py:28-29`、`app.py:94`、`app.py:450`、`app.py:30`、`app.py:79`、`app.py:604`。行号按修复后的文件计。

## README 与实际不符处

1. `README.md:51` 把 `PH_DB_PATH` 默认写成 `data/pushhub.db`，像是相对当前工作目录。`app.py:26` 实际是 `Path(__file__).resolve().parent / "data" / "pushhub.db"`，跟着源码文件走，不跟启动时的 cwd 走。
2. `README.md:16` 写消息中心按时间倒序。`app.py:492` 和 `app.py:498` 是 `ORDER BY m.id DESC`，不是 `created_at`。平时和插入顺序一致；系统时间回拨时会和「按时间」不一致。
3. `README.md:16` 没有写条数上限。`app.py:483` 默认 `limit=200`，最大 500。`static/index.html:351` 请求消息列表时不带 `limit`，更早的消息不会出现在页面上，也没有翻页。
4. `README.md:11` 写 Token 24 小时有效。普通接口在 `app.py:153` 用 `expires_at` 判断。审查时 SSE 只在握手时鉴权，生成器不复查会话；改密（现 `app.py:338`）和登出（现 `app.py:296`）只删表里的令牌。修复前探针：`ME_TOKEN2 401` 且 `SSE_GOT_AFTER_REVOKE True`。这一条已修，复查在 `app.py:563` 和 `app.py:574`。
5. `README.md:15` 和 `app.py:457` 把优先级当成任意整数，默认 5。`static/index.html:153` 的输入框写着 0–10。探针 `PRIORITY_-3 201 -3`、`PRIORITY_100 201 100`。README 和接口一致，和页面提示不一致。
6. `NOTES.md:20` 写令牌随机部分 27 字符。`app.py:248` 是 `"ph_" + secrets.token_urlsafe(24)`。探针 `TOKEN_LEN 35`、`RAND_LEN 32`。这是 NOTES 和代码不符，不是 README。

`README.md:59` 的 `ph_xxxxxxxxxxxx` 是示例占位，不单列成缺陷。

## 许可证与署名核查

仓库内部是对齐的，上游事实未核实。

- `LICENSE:1-3`：MIT，`Copyright (c) 2026 pushhub contributors`。这是本仓库自己的许可证。
- `README.md:6-7` 写明代码独立实现，溯源见 UPSTREAM。
- `UPSTREAM.md:5-8`：上游 `https://github.com/gotify/server`，commit `f4de6199f080c670f45d9821578d7e37e8024619`，MIT，`Copyright (c) 2018 jmattheis`。
- `UPSTREAM.md:16-20` 与 `NOTES.md:22-23` 都说版权行抄自上游 LICENSE，本项目不使用其 logo（上游另有 CC BY 4.0 的说法写在 NOTES 里），也没有复制 Go 源码。
- 在 `app.py`、`static/index.html`、`tests/` 里搜 `gotify` 和 `jmattheis`，没有命中。实现是 Python + FastAPI + SQLite，看不到粘贴的 Go 源码。
- 独立重写的前提下，本仓库 `LICENSE` 不写入上游版权人，而把上游版权记在 `UPSTREAM.md:8`，和「未复制实质代码」的声明一致。MIT 对副本才要求附带上游版权声明。源码文件没有逐文件版权头，根目录有 `LICENSE`，对 MIT 足够。

未核实（任务禁止抓取外网，没有对照 GitHub）：commit 是否存在、是否为 2026-10-18 的默认分支 HEAD、说明是否为 “Merge pull request #1075”、版权行是否与上游 LICENSE 逐字相同、logo 是否另按 CC BY 4.0 授权。这些只作为仓库自述，不当作已核对事实。没有发现可以据此改 `LICENSE` 或 `UPSTREAM.md` 的确凿错误，所以这两份文件不动。

`DECISIONS.md:6-13` 规定首次登录只提示改密、不强制。`static/index.html:180` 有「稍后再说」，后端不拦截业务接口。这和 README 的「提示改密」一致，不列为缺陷。`DECISIONS.md` 里已经落地的默认只听本机、SSE 不读查询令牌、改密删除其他会话行，和当前代码一致；本次 P1 是第 3 条没有覆盖到已经建立的 SSE。

## 分级修复清单

### P0

无。服务能起，测试能过。

### P1

1. **作废后的会话仍能从 SSE 收消息。已修，见 fix-report.md。** 审查时 `stream` 只在握手时鉴权，生成器不复查 `sessions`。改密（`app.py:338`）和登出（`app.py:296`）只删表里的令牌。修复前探针：另一个会话已经 401，SSE 仍收到新消息。修法：`app.py:163-175` 增加 `session_alive`；`app.py:563` 与 `app.py:574` 在写出业务消息前复查，失败则结束流，`app.py:582` 退订。

### P2

不修。每条都只写修法，本轮不动代码。

1. `app.py:492`、`app.py:498` 按 `m.id` 排序。修法：改成 `ORDER BY m.created_at DESC, m.id DESC`，并改 README 的相应句子。
2. `app.py:483` 默认最多 200 条，`README.md:16` 和 `static/index.html:351` 都没说。修法：在 README 和页面写明上限，或给列表加「加载更早」并传更大的 offset/limit。
3. `README.md:51` 的默认库路径容易理解成相对 cwd。修法：改成「相对 `app.py` 所在目录的 `data/pushhub.db`」。
4. `NOTES.md:20` 的 27 字符与 `app.py:248` 不符。修法：改成 32 字符（`token_urlsafe(24)`）。
5. `static/index.html:153` 写优先级 0–10，`app.py:457` 不校验。修法：要么接口拒绝区间外的值并改 README，要么去掉输入框上的 0–10 提示。现在 README 允许任意整数，所以不把它当成接口缺陷来改。
6. 未登录可以打开 `/docs`（探针 `DOCS 200`）。入口在 `app.py:108` 的 `FastAPI()` 默认值。修法：`docs_url=None, redoc_url=None, openapi_url=None`，或给文档加登录。默认只听本机，先记 P2。
7. `app.py:450` 的 `post_message` 是同步函数，Starlette 会放进线程池（已安装包 `starlette/routing.py:55`），再调用 `app.py:130` 的 `asyncio.Queue.put_nowait`。这不符合 asyncio 的线程约定。本次真实进程在普通模式和 `PYTHONASYNCIODEBUG=1` 下都是 20/20 收到，没有丢消息，所以不升到 P1。修法：在事件循环线程里 `call_soon_threadsafe` 再 `put_nowait`。
8. `app.py:271` 在用户不存在时短路，不做 PBKDF2。探针里不存在的用户名即使用 20000 字密码也只要 0.003 秒，存在的用户名约 0.070 秒。修法：用户不存在时也做一次等长的伪哈希。登录页已经公开默认用户名，实际价值低。
9. `requirements.txt:3` 的 `python-multipart` 在 `app.py` 里没有表单或上传用途。修法：从依赖里删掉。本轮不改已能安装的依赖。
10. `app.py:260-261` 的 `/health` 不鉴权，并返回当前订阅数。修法：健康检查只留 `status`。
