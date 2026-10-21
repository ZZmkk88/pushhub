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
