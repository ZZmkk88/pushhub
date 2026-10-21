# pushhub 修复记录

只修了审查清单里的 P1-1。P0 没有。P2 未改。

## P1-1 作废后的 SSE 仍能收到新消息

问题：握手之后不再查 `sessions`。改密或登出把令牌从表里删掉后，已经打开的流还在收广播。

文件：`app.py:163-175` 新增 `session_alive`；`app.py:543-582` 的 `stream` 在 `app.py:563`、`app.py:574` 写出业务消息前复查令牌，不在或已过期就结束生成器，`app.py:582` 退订。

改法：从 `Authorization: Bearer` 取出当前令牌。每轮循环先查会话；从队列拿到一条消息后再查一次，通过才 `yield`。保活注释 `: ping` 不含消息正文。登出、改密作废、过期都走同一条查询。

验证命令：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-037-pushhub\probe_revoke.py
```

真实输出：

```
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

退出码 0。还有效的会话收到了 `AFTER_REVOKE`，被作废的会话没有收到，订阅数从 2 降到 1。

修复前同一场景的输出是 `ME_TOKEN2 401`、`SSE_GOT_AFTER_REVOKE True`（见 `run.md` 第 5 节）。

## 全量重跑

pytest：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest E:\muse-bridge\in\TASK-037-pushhub\tests -q -p no:cacheprovider
```

```
.........................                                                [100%]
============================== warnings summary ===============================
..\..\work\TASK-037-pushhub\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-037-pushhub\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
25 passed, 1 warning in 2.52s
```

退出码 0。没有失败项。警告仍是依赖里的 Starlette 弃用提示，不是本次改动引入的失败。

live_selftest：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-037-pushhub\tests\live_selftest.py
```

```
[PASS] 01 服务启动 + 健康检查
[PASS] 11 SSE 连接建立并收到 ready
[PASS] 14 SSE 连接实时收到新消息推送
[PASS] 25 删除应用成功
ALL PASS（共 25 项检查）
```

退出码 0。01 到 25 全部是 PASS，上面只摘了和本次改动直接相关的几行，中间没有 FAIL。

## git status --porcelain

命令：

```
git status --porcelain
```

输出：

```
 M app.py
```
