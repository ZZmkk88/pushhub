# TASK-050-pushhub-p2 执行记录

开工：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-050-pushhub-p2`。先只读上一轮 `E:\muse-bridge\out\TASK-037-pushhub\review.md`，本轮只处理其中 P2。

## 1. 基线：令牌长度 + 全量 pytest

已有虚拟环境：`E:\muse-bridge\work\TASK-037-pushhub\venv`（上一轮装好的 Python 3.11，本轮不重装依赖）。工作目录为仓库根。`PYTHONDONTWRITEBYTECODE=1`，pytest 加 `-p no:cacheprovider`。

命令：

```
$env:PYTHONDONTWRITEBYTECODE='1'
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -c "import secrets; t=secrets.token_urlsafe(24); print('RAND_LEN', len(t))"
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

令牌长度（退出码 0）：

```
RAND_LEN 32
FULL_LEN 35
```

pytest（退出码 0，工作目录为仓库根，pytest 自报 3.01s）：

```
............................                                             [100%]
28 passed, 1 warning in 3.01s
```

警告原文：`Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自已安装的 Starlette，不是失败。

开工时 `git status --porcelain` 无输出。`git log -1 --oneline` 为 `7b7957d fix(TASK-022): 初始用户只在表空时创建、安全响应头中间件、关闭自动文档页`。

## 2. P2-1 之后的全量 pytest

改了 `app.py` 两处 `ORDER BY` 和 `README.md:16`。命令同上，工作目录为仓库根。

```
28 passed, 1 warning in 2.71s
```

退出码 0。

## 3. P2-2 之后的全量 pytest

改了 `README.md:18` 和 `static/index.html:166`，写明列表默认 200 条、最多 500 条。

```
28 passed, 1 warning in 2.61s
```

退出码 0。

## 4. P2-3 之后的全量 pytest

改了 `README.md:52` 的 `PH_DB_PATH` 默认值说明。

```
28 passed, 1 warning in 3.10s
```

退出码 0。

## 5. P2-4 之后的全量 pytest

改了 `NOTES.md:20-21`，令牌随机部分由 27 改为 32。

```
28 passed, 1 warning in 3.03s
```

退出码 0。

## 6. P2-5 之后的全量 pytest

改了 `static/index.html:153`，去掉优先级 0–10 的输入限制。

```
28 passed, 1 warning in 3.63s
```

退出码 0。

## 6b. P2-6

未改代码。文档三入口在 `app.py:148-150` 已关闭。跳过单独 pytest。

## 7. P2-7 之后的全量 pytest

`app.py` 的 `publish` 改为 `call_soon_threadsafe`。

```
28 passed, 1 warning in 3.47s
```

退出码 0。

## 8. P2-8 之后的全量 pytest

`app.py:313-316` 对不存在的用户补了一次 PBKDF2。

```
28 passed, 1 warning in 3.09s
```

退出码 0。

## 8b. P2-9

未改 `requirements.txt`。

## 9. P2-10 之后的全量 pytest

`app.py:303` 的 `/health` 去掉 `subscribers`。

```
28 passed, 1 warning in 3.06s
```

退出码 0。

## 10. 全部改完后的全量 pytest

没有再改仓库源码。

```
E:\muse-bridge\work\TASK-037-pushhub\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

```
28 passed, 1 warning in 2.79s
```

退出码 0。

`git diff --stat`：

```
 NOTES.md          |  4 ++--
 README.md         |  7 ++++---
 app.py            | 32 +++++++++++++++++++++++++++-----
 static/index.html |  3 ++-
 4 files changed, 35 insertions(+), 11 deletions(-)
```

`tests/`、`LICENSE`、`UPSTREAM.md`、`requirements.txt` 不在 diff 里。

## 11. git status --porcelain

```
git status --porcelain
```

```
 M NOTES.md
 M README.md
 M app.py
 M static/index.html
```
