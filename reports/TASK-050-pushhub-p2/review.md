# pushhub 第二轮 P2 审查

结论：基线与收口后的全量 pytest 都是 **28 passed**。没有 P0。上一轮 P1（作废会话后 SSE 仍能收消息）的补丁不在本仓库 HEAD `7b7957d` 里，本轮不重做。P2 十条里，第 6 条文档页已经关掉，第 9 条不动依赖，其余 8 条已按原顺序改完。最终 `28 passed, 1 warning in 2.79s`（退出码 0）。工作区仍有 4 个已改文件，见 fix-report.md 末尾的 `git status --porcelain`。

## 基线

- 虚拟环境沿用 `E:\muse-bridge\work\TASK-037-pushhub\venv`，没有重装依赖。
- 命令与输出见 `run.md` 第 1 节。pytest：`28 passed, 1 warning in 3.01s`，退出码 0。
- 开工时 `git status --porcelain` 为空。HEAD：`7b7957d`。

`token_urlsafe(24)` 实测随机部分长度 32，加前缀 `ph_` 后总长 35（`E:\muse-bridge\work\TASK-050-pushhub-p2\token_len.py`，退出码 0）。

## 上一轮 P1 为何不在本轮改

`E:\muse-bridge\in\TASK-037-pushhub\app.py:163` 有 `session_alive`。本仓库 `app.py` 全文没有这个函数；`app.py:590` 的 `stream` 只在握手时走 `current_user`，写出消息前不再查 `sessions`。该补丁停在上一轮工作区，没有进 `7b7957d`。任务写明 P0/P1 上一轮已修、本轮只处理 P2，所以这里只记录，不重做。

## P2 核对（行号是动手前的；改完后的行号见 fix-report.md）

1. **要改。** `app.py:516`、`app.py:522` 都是 `ORDER BY m.id DESC`。`README.md:16` 写「按时间倒序」。`created_at` 格式是 `app.py:35` 的 `%Y-%m-%dT%H:%M:%SZ`，文本倒序等于时间倒序。修法：两处改为 `ORDER BY m.created_at DESC, m.id DESC`，README 改成同一口径。`tests/test_app.py:201` 断言 id 严格倒序；同一秒内用 id 做次序，顺序插入时与现有断言一致。
2. **要改。** `app.py:507` 默认 `limit=200`，最大 500。`README.md:16` 与 `static/index.html:351`（请求不带 `limit`）都没写上限。修法：README 和消息流面板写明默认 200、最大 500。不加翻页。
3. **要改。** `README.md:51` 把默认库写成 `data/pushhub.db`。`app.py:25-26` 实际是 `Path(__file__).resolve().parent / "data" / "pushhub.db"`，跟着源码目录，不跟 cwd。修法：默认值改成「相对 `app.py` 所在目录的 `data/pushhub.db`」。
4. **要改。** `NOTES.md:20` 写随机部分 27 字符。`app.py:272` 是 `secrets.token_urlsafe(24)`，实测 32 字符。修法：NOTES 改为 32 字符。
5. **要改。** `static/index.html:153` 的输入框是 `min="0" max="10"`，提示「优先级 0-10」。`app.py:481` 不校验范围。`README.md:15`、`README.md:63` 写整数、默认 5。修法：去掉 0–10 限制和提示，不给接口加校验。
6. **不改。已经做完。** 动手前 `app.py:139-145` 已是 `docs_url=None, redoc_url=None, openapi_url=None`（改完后在 `app.py:144-150`）。`DECISIONS.md:57-61`（D7）记录了这个决定。回归在 `tests/test_app.py:391-395`，本轮不许改测试。
7. **要改。** `app.py:473` 的 `post_message` 是同步函数。已安装的 `starlette/routing.py:55` 对非 async 端点使用 `run_in_threadpool`。`app.py:166-172` 在该线程里对 `asyncio.Queue.put_nowait`。修法：启动时记下事件循环，`publish` 用 `call_soon_threadsafe` 回到循环线程再入队。
8. **要改。** `app.py:295` 在用户不存在时短路，不调用 `app.py:46-49` 的 PBKDF2（20 万次）。修法：用户不存在时用等长盐再算一次，错误文案不变。
9. **不改。** `requirements.txt:3` 的 `python-multipart==0.0.32` 在 `app.py` 里没有引用。任务禁止改已有依赖的版本号，除非是依赖冲突；这条能装上，不是冲突。不删依赖。
10. **要改。** `app.py:283-285` 的 `/health` 不鉴权，并返回 `subscribers`。`tests/test_app.py:46-49` 只断言 `status == ok`。修法：响应去掉 `subscribers`，保留 `status` 与 `app`。`subscriber_count` 属性留着，避免顺手删代码。

许可证与署名：本轮不联网，没有新的、可以改 `LICENSE` / `UPSTREAM.md` 的证据，这两份文件不动。

## 分级修复清单

### P0

无。基线 28 项通过。

### P1

无本轮修复项。上一轮 SSE 会话复查未进入本 HEAD，见上文，本轮不重做。

### P2（本轮修，编号沿用上一轮）

1. `app.py:516`、`app.py:522`，`README.md:16`。排序改为 `created_at DESC, id DESC`，README 写明同一秒再按 id。
2. `README.md:16`，`static/index.html:351` 附近。写明默认 200 条、最多 500 条。
3. `README.md:51`。默认库路径改为相对 `app.py` 所在目录。
4. `NOTES.md:20`。27 改为 32（`token_urlsafe(24)`）。
5. `static/index.html:153`。去掉 0–10 限制与提示。
7. `app.py:166-172`、`app.py:102-105`。广播改到事件循环线程里 `put_nowait`。
8. `app.py:295`。用户不存在时补一次等代价 PBKDF2。
10. `app.py:285`。`/health` 不再返回订阅数。

### 不修

- 上一轮 P2-6：文档三入口已关闭（现 `app.py:148-150`）。
- 上一轮 P2-9：不改 `requirements.txt` 里已能安装的依赖。
