# TikHub 端点选择

核对日期：2026-08-30。实现优先使用 TikHub 当前 App V3 / App V2 系列，不使用需要自行维护 Cookie 的旧 Web 方案。

## 抖音 App V3

- 账号信息：`GET /api/v1/douyin/app/v3/handler_user_profile`
  - 参数：`sec_user_id`
  - 文档：https://docs.tikhub.io/186826222e0
- 用户作品：`GET /api/v1/douyin/app/v3/fetch_user_post_videos`
  - 参数：`sec_user_id`, `max_cursor=0`, `count=20`, `sort_type=0`, `channel=normal`
  - `count` 不超过 20；必要时才切换 `channel=lite`。
  - 文档：https://docs.tikhub.io/186826223e0
- 视频评论：`GET /api/v1/douyin/app/v3/fetch_video_comments`
  - 参数：`aweme_id`, `cursor=0`, `count=20`
  - 官方提示保持默认 count，否则可能出现错误。
  - 文档：https://docs.tikhub.io/186826225e0

## 小红书 App V2

- 账号信息：`GET /api/v1/xiaohongshu/app_v2/get_user_info`
  - 参数：`user_id`，也可用 `share_text`；优先稳定 ID。
  - 文档：https://docs.tikhub.io/420136395e0
- 用户笔记：`GET /api/v1/xiaohongshu/app_v2/get_user_posted_notes`
  - 参数：`user_id`, `cursor`
  - 文档：https://docs.tikhub.io/420136396e0
- 笔记评论：`GET /api/v1/xiaohongshu/app_v2/get_note_comments`
  - 参数：`note_id`, `cursor`, `index=0`, `pageArea=UNFOLDED`, `sort_strategy=latest_v2`
  - `default` 排序可能在分页时漏评论或重复，默认使用 `latest_v2`。
  - 文档：https://docs.tikhub.io/420136394e0

## 计费与失败

TikHub 公示通用价格区间为每请求 USD 0.001–0.01。本 MVP 在无法查询端点精确价格时按 USD 0.01 预留，宁可提前停止，也不低估消费。小红书文档明确说明错误或不存在的用户、笔记 ID 仍可能正常计费，因此调用评论和详情前必须先从已成功的列表响应取得稳定 ID。
