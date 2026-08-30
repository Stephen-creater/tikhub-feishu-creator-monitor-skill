# TikHub × Feishu Creator Monitor Skill

一个面向 Codex 的开源 Skill：通过 TikHub 追踪抖音和小红书对标账号，将账号、作品、评论与指标快照幂等同步到飞书多维表格，并生成爆款战报、拆解文档和仪表盘。

项目处于可验证 MVP 阶段。当前实现以小额 API 预算、公开账号和本地 Codex 定时任务为边界，不承诺生产级吞吐或平台 SLA。

## 设计原则

- 一个总控 Skill，内部拆分账号同步、内容同步、附件转存、增量战报和拆解建档。
- Skill 负责理解和调度，版本化 Python 代码负责确定性抓取、去重、计算和重试。
- 飞书 Base 是协作与数据产品层，不承担爬虫分页和幂等控制。
- 所有密钥仅保存在本机环境，不进入仓库、日志、fixture 或飞书文档。

## 当前状态

详细实施与验收路径见 [实施计划](docs/plans/2026-08-30-creator-monitor-skill.md)。功能将按测试驱动方式逐项落地。

## 目标命令

```bash
creator-monitor doctor
creator-monitor bootstrap
creator-monitor account-sync
creator-monitor content-sync
creator-monitor metrics-refresh
creator-monitor content-analyze
creator-monitor scheduled-sync
creator-monitor daily-report
```

## License

MIT

