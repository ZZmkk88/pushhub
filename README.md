# pushhub · 推送中心

一句话定位：一个轻量、可自托管的消息推送中心——给每个「应用」发一个令牌，
任何程序拿令牌 POST 一条消息进来，打开着的网页端立刻实时收到。

设计学习了开源社区同类工具的通行思路（应用、令牌、消息、优先级），
代码为独立实现（溯源见 UPSTREAM.md）。

## 功能清单

- 单用户登录（Token 24 小时有效，首次登录提示改密）
- 应用管理：新建/改名/删除应用；每个应用自动生成发消息令牌，可查看、复制、
  重新生成、吊销；删应用会连同它的消息一起删除
- 发消息接口：`POST /message`，请求头带应用令牌，正文支持标题、正文、优先级
  （整数，默认 5；令牌缺失或错误返回 401）
- 消息中心：按创建时间倒序（同一秒内再按 id 倒序），显示来源应用、标题、正文与优先级档位
  （≥8 紧急红色 / 5–7 普通 / ≤4 低），可按应用筛选、单条删除、按范围清空。
  列表默认返回最近 200 条，查询参数 `limit` 取值 1–500
- 实时推送：页面打开时通过 SSE 长连接接收新消息，不刷新即冒出新卡片，
  断线自动重连，顶栏有连接状态灯
- 单页前端：建应用、拿令牌、发测试消息、看消息、删消息都在一个页面完成

## 快速开始

默认账号：`admin` / `admin123`（首次登录会提示改密；可用环境变量
`PH_INITIAL_USERNAME` / `PH_INITIAL_PASSWORD` 覆盖初始账号密码）。

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows（PowerShell）

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

启动后打开 http://127.0.0.1:8000 ，用默认账号登录即可。

| 环境变量 | 说明 | 默认值 |
|---|---|---|
| `PH_HOST` | 服务监听地址。默认只听本机；要对局域网开放时显式设为 `0.0.0.0` | `127.0.0.1` |
| `PH_PORT` | 服务端口 | `8000` |
| `PH_DB_PATH` | SQLite 数据库文件位置 | 相对 `app.py` 所在目录的 `data/pushhub.db` |
| `PH_INITIAL_USERNAME` / `PH_INITIAL_PASSWORD` | 初始账号密码（只在 users 表为空、即首次启动时写入；之后再改这两个变量也不会新增账号或改写密码） | `admin` / `admin123` |

## 发消息接口

```bash
curl -X POST http://127.0.0.1:8000/message \
  -H "Content-Type: application/json" \
  -H "X-App-Token: ph_xxxxxxxxxxxx" \
  -d '{"title":"备份完成","message":"数据库备份成功","priority":5}'
```

- `message` 必填，`title` 可空，`priority` 可空（默认 5）。
- 成功返回 201 和这条消息的完整记录；令牌缺失或错误返回 401。

## 跑测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python tests/live_selftest.py   # 脚本会自己在 8137 端口起一个临时服务，跑完整流程（含 SSE 实时推送验证）
```

## 技术栈

Python + FastAPI + SQLite，单文件后端 + 原生单页前端，无构建步骤。
