# TASK-015-pushhub 执行记录

开工时间：2026-10-21。工作目录：E:\muse-bridge\in\TASK-015-pushhub。本文件随步骤追加，不攒到最后。

## 环境探测

### 命令：`py -3 --version`
退出码 1。原文：
```
Unable to create process using 'E:\python.exe --version': ???????????
```
README Windows 段写的是 `py -m venv .venv`。本机 `py` 启动器指向不存在的 `E:\python.exe`，按 README 原样建虚拟环境失败。这是本机启动器损坏，不计入项目缺陷。改用 PATH 上的 `python`。

### 命令：`python --version`
```
Python 3.11.9
```

### 命令：`where.exe python`
```
E:\muse-bridge\env\TASK-015-pushhub\Scripts\python.exe
C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe
C:\Users\xzm\AppData\Local\Microsoft\WindowsApps\python.exe
```

### 命令：`python -c "import sys; print(sys.executable); print(sys.version)"`
```
E:\muse-bridge\env\TASK-015-pushhub\Scripts\python.exe
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
```

### 命令：`git status --porcelain`
输出为空（工作区干净）。`git rev-parse --show-toplevel` = `E:/muse-bridge/in/TASK-015-pushhub`。

### 命令：`python -m pip show fastapi uvicorn python-multipart httpx pytest`
运行时依赖已在该解释器里，版本与 requirements.txt 一致：
- fastapi 0.156.4
- uvicorn 0.54.0
- python-multipart 0.0.32
httpx、pytest 未安装（`WARNING: Package(s) not found: httpx, pytest`）。下一步按 README 安装 requirements-dev.txt。

## 安装依赖

### 命令：`python -m pip install -r requirements-dev.txt`
工作目录：E:\muse-bridge\in\TASK-015-pushhub。退出码 0。耗时约 36.5 秒。

摘要：
- fastapi==0.156.4、uvicorn==0.54.0、python-multipart==0.0.32 已满足
- 新装 httpx==0.28.1、pytest==9.1.1，以及 httpcore、certifi、pluggy、iniconfig、packaging、pygments、colorama
- 末行：`Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1`

未改 requirements 里的版本号。

## 跑测试

### 命令：`python -m pytest tests/ -q`
工作目录：E:\muse-bridge\in\TASK-015-pushhub。退出码 0。耗时 2.46 秒。

```
.......................                                                  [100%]
============================== warnings summary ===============================
..\..\env\TASK-015-pushhub\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\env\TASK-015-pushhub\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
23 passed, 1 warning in 2.46s
```

23 项全部通过。警告来自 FastAPI/Starlette 对 httpx 的弃用提示，不是测试失败。

### 命令：`python tests/live_selftest.py`
退出码 0。脚本自己在 8137 端口起临时服务，跑完自行关掉。

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

## 按 README 起服务

### 8000 端口被其他任务占用（环境限制，不是本仓库缺陷）

命令：`netstat -ano | findstr :8000`

```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       29612
```

命令：`tasklist /FI "PID eq 29612"` 显示 `python.exe 29612`。
命令：`Get-CimInstance Win32_Process -Filter "ProcessId = 29612"` 的 CommandLine：

```
"C:\Users\xzm\AppData\Local\Programs\Python\Python311\python.exe" E:\muse-bridge\work\TASK-014-weblens\start_server.py
```

未结束该进程（禁止 taskkill，且不属于本任务）。README 允许 `PH_PORT` 改端口，故用 18765。数据库放到工作目录，避免在仓库生成 `data/pushhub.db`。

### 命令：`python E:\muse-bridge\work\TASK-015-pushhub\start_server.py`

该脚本设置 `PH_DB_PATH=E:\muse-bridge\work\TASK-015-pushhub\pushhub.db`、`PH_PORT=18765` 后以 `__main__` 执行仓库 `app.py`。启动日志：

```
INFO:     Started server process [8380]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:18765 (Press CTRL+C to quit)
```

命令：`netstat -ano | findstr :18765`

```
TCP    0.0.0.0:18765          0.0.0.0:0              LISTENING       8380
```

监听的是 `0.0.0.0`，不是只绑 127.0.0.1。

### 命令：`python E:\muse-bridge\work\TASK-015-pushhub\probe_server.py`

```
HEALTH 200 {"status":"ok","app":"pushhub","subscribers":0}
INDEX 200 pushhub_in_body True bytes 22064
DOCS 200
OPENAPI 200
LOGIN 200
MUST_CHANGE True
LOGIN2 200 tokens_differ True
STREAM_NONE 401
STREAM_QUERY_STATUS 200 text/event-stream; charset=utf-8
STREAM_QUERY_LINE event: ready
CREATE_APP 201
APP_TOKEN_LEN 35 PREFIX ph_
POST_MESSAGE 201 {"id":1,"app_id":1,"app_name":"probe","title":"备份完成","message":"数据库备份成功","priority":5,"created_at":"2026-10-21T09:42:33Z"}
CHANGE_PW 200 {"ok":true}
OLD_SESSION_AFTER_PW 200 {"username":"admin","must_change_password":false}
CURRENT_SESSION_AFTER_PW 200 {"username":"admin","must_change_password":false}
```

未使用 curl（任务禁止）。README 的发消息示例改用 httpx POST `/message`，返回 201。

### 命令：`python -c "import secrets; print(len(secrets.token_urlsafe(24))); print(len(secrets.token_urlsafe(20)))"`

```
32
27
```

### 命令：`python E:\muse-bridge\work\TASK-015-pushhub\probe_sse.py`

```
SENT 40 SSE_DATA_LINES 40 UNIQUE_TITLES 40
MISSING [] COUNT 0 HAS_DONE True
```

本次 40 条连续推送没有丢。

### 关闭服务

用会话的进程停止接口结束 `start_server.py`（未使用 taskkill）。随后 `netstat -ano | findstr :18765` 不再有 LISTENING 行，只剩若干 `127.0.0.1:* -> 127.0.0.1:18765 TIME_WAIT`（PID 0）。服务已停止。

## P1-1 修复后复查监听地址

改完 `app.py` 后再次 `python E:\muse-bridge\work\TASK-015-pushhub\start_server.py`。日志：

```
INFO:     Uvicorn running on http://127.0.0.1:18765 (Press CTRL+C to quit)
```

`netstat -ano | findstr :18765`：

```
TCP    127.0.0.1:18765        0.0.0.0:0              LISTENING       14436
```

`check_health.py`：`HEALTH 200`，`INDEX 200 pushhub True`。
`python -m pytest tests/test_app.py::test_health tests/test_app.py::test_index_page -q`：`2 passed, 1 warning in 0.84s`。
服务已停止。细节见 fix-report.md 的 P1-1。

## P1-2 修复后复查 SSE 鉴权

`python -m pytest tests/test_app.py::test_stream_requires_auth tests/test_app.py::test_stream_receives_pushed_message -q`：

```
2 passed, 1 warning in 0.87s
```

`python E:\muse-bridge\work\TASK-015-pushhub\check_p1_2.py`：

```
LOGIN 200
QUERY_VALID 401
NO_AUTH 401
QUERY_BAD 401
HEADER 200
HEADER_LINE event: ready
```

## P1-3 与全量回归

`python -m pytest tests/test_app.py::test_change_password_flow -q`：`1 passed, 1 warning in 1.33s`。

`python E:\muse-bridge\work\TASK-015-pushhub\check_p1_3.py`：

```
TWO_TOKENS True
CHANGE 200 {"ok":true}
OLD_SESSION 401 {"detail":"登录已过期，请重新登录"}
CURRENT_SESSION 200 {"username":"admin","must_change_password":false}
OLD_PASSWORD 401
NEW_PASSWORD 200
```

全量：`python -m pytest tests/ -q` → `23 passed, 1 warning in 1.91s`。
`python tests/live_selftest.py` → `ALL PASS（共 25 项检查）`。没有失败项。









