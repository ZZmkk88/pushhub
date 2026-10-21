# pushhub 调研与设计笔记（NOTES）

## 动手前查了什么（2026-10-21，通过 GitHub 接口通读上游原文）

上游：gotify/server（HEAD `f4de6199f080c670f45d9821578d7e37e8024619`，2026-10-18）。

- **README**：定位是「可自托管、通过 REST 接口发消息、实时接收消息」的服务端，
  核心三件套是 users / applications / clients 的管理 + 发消息接口 + 实时通道。
- **model/application.go**：应用字段 = id、token（唯一索引）、name、description、
  defaultPriority（应用级默认优先级）、createdAt、lastUsed（令牌最近使用时间）。
  本项目采纳 name / description / token / created_at / last_used_at；
  defaultPriority 砍掉（MVP 里单条消息自带优先级，未给时用全局默认 5，
  少一个概念，页面更简单）。
- **model/message.go**：消息字段 = id、applicationid、message（必填）、title、
  priority（可空，空则用应用默认值）、extras、date。本项目采纳
  title / message / priority / created_at；extras（插件式扩展字段）砍掉。
- **api/message.go**：发消息成功后走 Notifier.Notify 把消息推给已连接的接收端；
  本项目用同样的「入库 + 广播」两步，只是实时通道换成 SSE。
- **auth/token.go**：上游 v3 的令牌是带签名的增强令牌（工程量大）；MVP 采用
  随机长字符串令牌 + 数据库唯一约束的朴素方案，令牌 27 字符随机部分，
  碰撞时重试生成，够单用户自托管场景使用。
- **LICENSE 原文**：MIT，版权行 `Copyright (c) 2018 jmattheis`；文件末尾注明
  其 logo 单独按 CC BY 4.0 授权——本项目不使用其 logo、名称与界面素材。

## 砍掉的东西（及理由）

- 多用户与权限分级：单用户自用，砍。
- Client（接收端设备）概念：网页端就是接收端，不再单设一层，砍。
- WebSocket：改用 SSE（单向推送足够；浏览器端用 fetch 流式读取，
  还能带 Authorization 头，不用把 token 塞进 URL）。
- 插件系统、extras 扩展字段、应用图标上传：MVP 不做。
- Markdown 渲染：正文按纯文本展示（转义后输出），不引渲染库，防 XSS 靠转义。

## 本项目的设计决定

- **一张应用表 + 一张消息表**：删应用时消息级联删除（外键 ON DELETE CASCADE），
  与「删除应用连同消息一起没了」的产品预期一致，页面删除前有确认。
- **令牌吊销** = token 置 NULL：吊销后旧令牌查不到应用，发消息返回 401；
  重新生成则写入新随机令牌，旧的立即失效。
- **优先级口径**：整数，默认 5；页面按 ≥8「紧急」红色、5–7「普通」琥珀色、
  ≤4「低」灰色三档展示，左侧色条同步。
- **SSE 实现**：进程内 Broadcaster，每个订阅者一个 asyncio.Queue（上限 100，
  满了丢弃不阻塞发消息接口）；20 秒无消息发一行注释保活；断开自动清理队列。
  单进程部署下足够，多进程部署不在 MVP 范围。
- **改密**：首次登录只提示不强制（弹窗可跳过），口径与 PMC 项目 P1-9 的决定一致。

## 资源核对（动手前实测）

- 云端实测：2 核 CPU、内存约 7.7G、无 GPU。pushhub 是单进程
  FastAPI + SQLite 文件库，无常驻后台任务，SSE 连接每条只占一个内存队列，
  资源占用远低于云端上限，结论：绰绰有余。
- 本地开发/自测同样只需 Python 3 环境，无额外系统依赖。

## 已知取舍（如实记录）

- SSE 广播是进程内的，多 worker / 多实例部署时跨进程收不到推送；
  单进程启动（`python app.py`）是本项目的预期用法。
- 令牌在页面上可明文显示/复制（单用户自用场景的便利取舍），
  令牌只存明文于本地 SQLite，请勿把 data 目录外传。
