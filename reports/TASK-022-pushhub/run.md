# TASK-022-pushhub 本地跑通记录

开工时间：2026-10-21。工作目录：E:\muse-bridge\in\TASK-022-pushhub。先审查再修 P0/P1。

## 步骤 0：检查 Python

命令：

```
py -3 --version
python --version
```

输出：

```
py -3 --version
exit: 1
Unable to create process using 'E:\python.exe --version': ???????????

python --version
exit: 0
Python 3.11.9
```

说明：本机 `py` 启动器指向无效的 `E:\python.exe`（环境问题，不是仓库缺陷）。后续改用 `python` 3.11.9。虚拟环境放在 `E:\muse-bridge\work\TASK-022-pushhub\venv`，不写进仓库。

命令：

```
python -m venv E:\muse-bridge\work\TASK-022-pushhub\venv
```

输出：exit 0，无报错。

## 步骤 1：安装依赖

命令（2026-10-21）：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-022-pushhub\requirements-dev.txt
```

输出摘要（exit 0）：

```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 certifi-2026.10.19 click-8.5.0 colorama-0.4.6 fastapi-0.156.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 idna-3.20 iniconfig-2.3.1 opentelemetry-api-1.45.1 packaging-26.3 pluggy-1.7.0 pydantic-2.14.1 pydantic-core-2.50.1 pygments-2.21.0 pytest-9.1.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

requirements.txt 与 requirements-dev.txt 的版本钉都能装上（fastapi==0.156.4、uvicorn==0.54.0、python-multipart==0.0.32、httpx==0.28.1、pytest==9.1.1）。

## 步骤 2：全量 pytest

辅助脚本：`E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py`（把 TEMP/TMP 指到工作目录，避免测试库落到系统 TEMP）。

命令：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_pytest.py
```

实际执行的 pytest：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
CWD: E:\muse-bridge\in\TASK-022-pushhub
```

输出（exit 0）：

```
.......................                                                  [100%]
============================== warnings summary ===============================
..\..\work\TASK-022-pushhub\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-022-pushhub\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
23 passed, 1 warning in 2.13s
```

## 步骤 3：live_selftest（8137）

辅助脚本：`E:\muse-bridge\work\TASK-022-pushhub\run_live.py`。

命令：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_live.py
```

实际执行：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-022-pushhub\tests\live_selftest.py
CWD: E:\muse-bridge\in\TASK-022-pushhub
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

脚本在 finally 里 terminate 掉临时进程。未单独计时；单次调用在 90 秒上限内返回。

## 步骤 4：按 README 起服务，检查 8000 端口后关掉

未使用仓库内 `data/pushhub.db`（任务禁止 del/rm，避免在仓库留下删不掉的库文件）。数据库改到工作目录。端口仍是 README 的 8000，进程入口仍是 `app.py`。

辅助脚本：`E:\muse-bridge\work\TASK-022-pushhub\run_server_check.py`。

命令：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\run_server_check.py
```

输出（exit 0）：

```
CMD: E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-022-pushhub\app.py
CWD: E:\muse-bridge\in\TASK-022-pushhub
PH_DB_PATH: E:\muse-bridge\work\TASK-022-pushhub\server-check.db
PH_PORT: 8000
HEALTH_STATUS 200
HEALTH_BODY {"status":"ok","app":"pushhub","subscribers":0}
INDEX_STATUS 200
INDEX_LEN 20661
INDEX_HAS_PUSHHUB True
INDEX_HEAD <!DOCTYPE html> <html lang="zh-CN"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>pushhub · 推送中心</title>
LOGIN_STATUS 200
LOGIN_USER admin
LOGIN_MUST_CHANGE True
LOGIN_TOKEN_LEN 43
STOPPED 1
```

`STOPPED 1` 是进程被 terminate 之后的退出码，出现在健康检查、首页和登录都已成功之后。检查结束时服务已停。

## 步骤 5：令牌长度对照（给文档核查用）

命令：

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\work\TASK-022-pushhub\token_len.py
```

输出（exit 0）：

```
token_urlsafe_24_len 32
app_token_len 35
prefix ph_
```

## 步骤 6：修复前的 git 状态

命令：

```
git -C E:\muse-bridge\in\TASK-022-pushhub status --porcelain
```

输出：空（exit 0）。仓库在修复前是干净的，测试没有往仓库里留下 `__pycache__` 或 `data/`。

## 步骤 7：五项 P1 修完后的全量重跑

命令与逐项验证写在 `fix-report.md`。这里只记最后一次全量结果。

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe -m pytest tests/ -q --tb=short
23 passed, 1 warning in 1.82s
```

```
E:\muse-bridge\work\TASK-022-pushhub\venv\Scripts\python.exe E:\muse-bridge\in\TASK-022-pushhub\tests\live_selftest.py
ALL PASS（共 25 项检查）
```

两条都是 exit 0。

