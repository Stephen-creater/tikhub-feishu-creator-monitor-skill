---
name: creator-monitor
description: Track public Douyin and Xiaohongshu competitor accounts with TikHub, keep a user-friendly 飞书 Feishu Base updated, and surface content rankings, real covers, trends, comment needs, and a two-state idea pipeline. Use when the user asks to monitor creator accounts, refresh creator intelligence, build a 飞书 content dashboard, or run the scheduled creator-monitor sync.
---

# Creator Monitor

Use this Skill to operate a creator intelligence workspace built from Codex, TikHub and Feishu Base.

## User outcome

The user should see:

- an account library with recognizable names, avatars, positioning, region and performance;
- a content library with each work's real cover, readable metrics and recommendation reason;
- one ranked list whose Top 1, Top 2 and Top 3 match the dashboard;
- a gallery for cover and topic inspiration;
- one board with only `待处理` and `已采用`;
- a dense dashboard for accounts, content, rankings, distribution and trends.

Do not expose maintenance metadata in default views, reports or tutorials. Keep it in the maintenance area only when required for correct synchronization.

## Commands

Run from the Skill root:

```bash
scripts/creator-monitor doctor
scripts/creator-monitor bootstrap
scripts/creator-monitor scheduled-sync
scripts/creator-monitor daily-report
```

Use `scheduled-sync --use-cache` only for a zero-cost scheduling check. Use `--include-comments` only when the user needs comment insight and the budget allows it.

## Operating rules

1. Read local configuration and run `doctor` before the first live operation.
2. Keep TikHub secrets in the environment or OS key store; never write them to Git, Feishu or logs.
3. Keep stable internal identity out of user-facing views.
4. Preserve user decisions such as `状态`, `推荐理由`, `采用时间` and analysis links during refreshes.
5. A work's cover must come from that public work. Download it and store it as a Feishu attachment; never substitute generated artwork.
6. Use the fixed ranking formula documented in `references/data-contract.md` unless the user explicitly changes it.
7. Stop before a TikHub request would exceed the configured request or dollar limit.
8. Verify the real Base after writes: record counts, blank covers, state distribution, ranking consistency and dashboard results.

## Data presentation

- Default business views contain only readable business fields.
- The only workflow states are `待处理` and `已采用`.
- Real crawled records and simulated historical snapshots must be labelled separately.
- Keep system maintenance tables under a maintenance folder.

Read `references/operations.md` for failure handling and `references/data-contract.md` for the maintained data contract.
