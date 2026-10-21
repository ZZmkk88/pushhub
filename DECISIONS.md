# 决策记录（DECISIONS）

这里记录推翻直觉、或与外部建议不同、或由用户拍板的产品决策。
外部审查（Grok 等）给出的建议若与这里冲突，以这里为准。

## D1：首次登录只提示改密、不强制（用户统一口径，2026-10-21）

- 用户拍板：所有复刻项目的首次改密都是**只提示、不强制**。审查若再报"强制改密"
  项，一律按已定决策处理，不改回强制。
- 依据：pushhub 定位是单用户自托管工具，强制改密属于过度打扰；
  登录页、改密弹窗和账号设置都保留"建议改掉默认密码"的提示。
- 对应实现：`must_change_password=1` 时前端只弹窗提醒，有"稍后再说"按钮；
  后端不拦截任何业务接口。

## D2：默认监听本机 + PH_HOST 可放开（TASK-015 P1-1，2026-10-21）

- Grok 审查指出默认 `host="0.0.0.0"` 会把服务暴露到全部网卡，建议默认只听本机。
- 决定采纳：`uvicorn.run(host=os.environ.get("PH_HOST", "127.0.0.1"))`。
  要对局域网开放时，显式设置 `PH_HOST=0.0.0.0`。环境变量表见 README。

## D3：SSE 会话令牌只认 Authorization: Bearer（TASK-015 P1-2，2026-10-21）

- Grok 审查指出 `/api/stream` 接受 URL 查询参数里的会话令牌，
  令牌会进访问日志/浏览器历史，建议只认请求头。
- 落实前核对过前端实现：前端用 `fetch("/api/stream", {headers:{"Authorization":"Bearer "+TOKEN}})`
  流式读取，**从未用过 `?token=`**，改为 Bearer-only 不会卡死前端。
- 决定采纳：去掉查询参数分支，无效/缺失令牌返回 401。
- 附带回归测试：`test_stream_query_token_rejected`（有效令牌走查询参数也 401）。

## D4：改密时作废其他会话、保留当前（TASK-015 P1-3，2026-10-21）

- Grok 审查指出改密后旧会话仍有效，建议改密时清掉其他会话。
- 决定采纳：同一事务里 `DELETE FROM sessions WHERE user_id = ? AND token != ?`，
  保留发起改密的这一次登录；取不到当前令牌时不删，避免把自己踢掉。
- 附带回归测试：`test_change_password_revokes_other_sessions`（旧会话 401、当前会话 200）。

## D5：初始用户只在 users 表为空时创建（TASK-022 P1-4，2026-10-21）

- Grok 审查指出：`init_db` 按"该用户名不存在"就 INSERT，运维换 `PH_INITIAL_USERNAME`
  再启动会多出一个全权限账号。
- 决定采纳：改成 `SELECT COUNT(*)`，只有表为空才创建。已有用户后换变量
  既不新增账号、也不改写已有密码。README 环境变量表已同步口径。
- 附带回归测试：`test_init_db_seeds_only_when_empty`（换用户名再 init 仍只有首个账号）。

## D6：纯 ASGI 中间件加安全响应头，不用 BaseHTTPMiddleware（TASK-022 P1-5，2026-10-21）

- Grok 审查指出页面可被外站 iframe 嵌套（点击劫持），建议加响应头。
- 决定采纳：`SecurityHeadersMiddleware` 只改 `http.response.start` 的头，
  不读、不缓冲响应体——`BaseHTTPMiddleware` 会把流式响应攒起来再发，
  会把 SSE 长连接吃掉，所以不能用它。加的四个头：
  X-Frame-Options: DENY、X-Content-Type-Options: nosniff、
  Referrer-Policy: no-referrer、Content-Security-Policy: frame-ancestors 'none'。
- 附带回归测试：`test_security_headers`（首页/健康检查/401 响应都带头）；
  SSE 用例 `test_stream_receives_pushed_message` 与自测脚本全程走中间件，
  证明流没被打断。

## D7：自动文档页直接关闭（TASK-022 P2-2，2026-10-21）

- Grok 审查列为 P2：`/docs` 未登录可访问。按团队口径（quicklink 同轮已关），
  pushhub 直接 `docs_url=None, redoc_url=None, openapi_url=None` 关闭三入口。
- 附带回归测试：`test_docs_endpoints_disabled`（三入口均为 404）。

## D8：Grok 独立复现的 P1-1~P1-3 不重复合入（TASK-022 对账，2026-10-21）

- `grok/TASK-022-pushhub` 分支基于旧 main（比当前 main 少我方 18:42 的
  `fix(TASK-015)`），它独立重新实现了 P1-1（PH_HOST）、P1-2（SSE Bearer-only）、
  P1-3（改密清其他会话），与 main 现有修复**同义**。
- 决定：该分支的 P1-1~P1-3 部分**不合并、不 cherry-pick**，只合入真正新增的
  P1-4、P1-5。直接 merge 整个分支会把旧代码盖回来，还会丢掉我方 18:42 的测试
  与 README 变更，故采用手工搬运（rebase 思路）。
