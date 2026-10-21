# pushhub P2 修复记录

编号沿用 `E:\muse-bridge\out\TASK-037-pushhub\review.md` 的 P2 清单。每条改完跑一次全量 pytest。

## P2-1 消息列表按 id 排序，README 写的是按时间

文件：

- `app.py:537`：`ORDER BY m.id DESC` 改为 `ORDER BY m.created_at DESC, m.id DESC`
- `app.py:543-544`：同样改为 `ORDER BY m.created_at DESC, m.id DESC`（语句拆成两行）
- `README.md:16`：「按时间倒序」改为「按创建时间倒序（同一秒内再按 id 倒序）」

改法：排序与 README 的「按时间」对齐。`created_at` 是 `YYYY-MM-DDTHH:MM:SSZ`，同一秒再用 id 倒序，现有「id 严格倒序」断言在顺序插入时仍然成立。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 2.71s
```

退出码 0。警告仍是 Starlette 弃用 httpx，不是失败。

## P2-2 默认最多 200 条，README 和页面都没写

文件：

- `README.md:18`：补上「列表默认返回最近 200 条，查询参数 `limit` 取值 1–500」
- `static/index.html:166`：消息流工具栏下增加「列表默认显示最近 200 条（单次最多 500 条）。」

改法：只补充说明。`app.py:507` 的默认值和上限不动，页面请求仍然不传 `limit`，走默认 200。没有加「加载更早」。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 2.61s
```

退出码 0。

## P2-3 README 把默认库路径写成像相对 cwd

文件：`README.md:52`。

改法：默认值从 `` `data/pushhub.db` `` 改为「相对 `app.py` 所在目录的 `data/pushhub.db`」。代码 `app.py:25-26` 不动，本来就是 `Path(__file__).resolve().parent / "data" / "pushhub.db"`。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 3.10s
```

退出码 0。

## P2-4 NOTES 写令牌随机部分 27 字符

文件：`NOTES.md:20-21`。

改法：改成「令牌随机部分 32 字符（`secrets.token_urlsafe(24)`）」。依据是 `app.py:272` 和实测 `RAND_LEN 32`（见 `run.md` 第 1 节）。代码没改。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 3.03s
```

退出码 0。

## P2-5 页面把优先级限制成 0–10，接口不校验

文件：`static/index.html:153`。

改法：去掉 `min="0"`、`max="10"` 和 title「优先级 0-10」。改为 `step="1"`，title「优先级，整数，默认 5」。`app.py:481` 不加范围校验，与 `README.md:15`、`README.md:63` 的「整数，默认 5」一致。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 3.63s
```

退出码 0。

## P2-6 未登录可以打开 /docs

不改。`app.py:144-150` 已经 `docs_url=None, redoc_url=None, openapi_url=None`。`DECISIONS.md:57-61` 记了这条。`tests/test_app.py:391-395` 断言三个入口都是 404。没有新的代码改动，所以这一条没有单独再跑 pytest。

## P2-7 同步 post_message 在线程池里 put_nowait

文件：

- `app.py:109`：`lifespan` 里 `broadcaster.bind_loop(asyncio.get_running_loop())`
- `app.py:162-190`：`Broadcaster` 记下循环；`publish`（`app.py:183`）复制 payload 后用 `call_soon_threadsafe` 调 `_enqueue`；`_enqueue`（`app.py:175-181`）才 `put_nowait`

改法：`post_message` 仍是同步函数。入队改到事件循环线程。循环还没绑上或已停时，退回直接入队。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 3.47s
```

退出码 0。其中包含 `test_stream_receives_pushed_message`。

## P2-8 用户不存在时不做 PBKDF2

文件：

- `app.py:52-53`：增加 `_DUMMY_PASSWORD_SALT = "00" * 16`（与 `secrets.token_hex(16)` 等长）
- `app.py:313-317`：用户不存在时先 `hash_password(body.password, _DUMMY_PASSWORD_SALT)`，再返回原来的 401 文案

改法：拆开原来的短路 `or`。密码错误的路径仍用该用户的盐做哈希。错误信息不区分用户名是否存在。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 3.09s
```

退出码 0。

## P2-9 删掉未使用的 python-multipart

不改。`requirements.txt:3` 是 `python-multipart==0.0.32`。`app.py` 没有引用它。任务禁止改已有依赖的版本号，除非是依赖冲突；这一条能装上，不是冲突。上一轮也写了不改已能安装的依赖。

## P2-10 /health 不鉴权却返回订阅数

文件：`app.py:303`。

改法：去掉 `subscribers`。响应保留 `{"status": "ok", "app": "pushhub"}`。`Broadcaster.subscriber_count` 属性留着，没有顺手删。

验证：

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 3.06s
```

退出码 0。

## 全部改完后的全量 pytest

没有再改仓库文件。命令同上，工作目录为仓库根。

```
28 passed, 1 warning in 2.79s
```

退出码 0。警告仍是已安装 Starlette 对 httpx 的弃用提示，没有失败项。没有改 `tests/`，没有加 skip 或 xfail。

## git status --porcelain

命令（仓库根）：

```
git status --porcelain
```

输出：

```
 M NOTES.md
 M README.md
 M app.py
 M static/index.html
```
