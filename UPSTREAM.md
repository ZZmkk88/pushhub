# 上游溯源（UPSTREAM）

本项目在设计阶段学习了开源社区消息推送工具的通行思路，按接力规范记录上游信息如下：

- **source_url**: https://github.com/gotify/server
- **source_commit**: f4de6199f080c670f45d9821578d7e37e8024619
- **license**: MIT
- **attribution**: Copyright (c) 2018 jmattheis

## 说明

- `source_commit` 是 2026-10-21 通过 GitHub 接口实查的上游默认分支 HEAD 提交
  （提交说明 "Merge pull request #1075 ..."，提交时间 2026-10-18）；当日做设计
  调研时查阅的上游内容正是这一提交，包括 README、`model/application.go`、
  `model/message.go`、`model/client.go`、`api/message.go` 与 LICENSE 原文。
- `attribution` 的版权行逐字复制自上游仓库 `LICENSE` 原文，未做任何改动。
- 上游 LICENSE 末尾另注明其 logo 按 CC BY 4.0 单独授权；本项目不使用上游
  logo，界面与名称均为自研。
- 本项目代码为独立重写（Python + FastAPI + SQLite），未复制上游（Go）源码；
  借鉴的是「应用 + 令牌 + 消息 + 优先级」这类核心概念，具体调研记录见 NOTES.md。
