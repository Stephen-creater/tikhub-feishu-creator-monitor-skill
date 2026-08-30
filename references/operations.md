# 运行手册

## 推荐顺序

1. `doctor`
2. `bootstrap --dry-run`
3. `bootstrap`
4. `account-sync`
5. `content-sync`
6. 再次运行 `content-sync` 验证幂等
7. `metrics-refresh`
8. `content-analyze`
9. `daily-report`

## 成本保护

- `CREATOR_MONITOR_MAX_USD` 控制 MVP 累计预算。
- `CREATOR_MONITOR_MAX_REQUESTS_PER_RUN` 控制单次最大请求数。
- 相同端点和参数的测试响应优先读本地缓存。
- 评论默认只取一页，且只处理新内容、爆款候选或人工标记内容。

## 恢复规则

- 429、5xx、连接超时：有界指数退避。
- 401、403、参数错误、Schema 错误：快速失败并记录。
- 单条内容失败：记录到系统维护区，继续处理本批次的其他内容。
- 飞书写入部分失败：不推进 TikHub 游标。
- 上一次任务仍在运行：记录 `skipped_overlap`，不并发执行。
