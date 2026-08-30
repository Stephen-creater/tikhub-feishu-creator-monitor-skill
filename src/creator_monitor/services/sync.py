from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from creator_monitor.budget import BudgetGuard
from creator_monitor.config import Settings
from creator_monitor.domain.dedup import deduplicate_latest
from creator_monitor.domain.identity import bucket_time, snapshot_key
from creator_monitor.domain.models import Content, MetricSnapshot, Platform
from creator_monitor.feishu.mappers import (
    account_pending,
    comment_pending,
    content_pending,
    prepare_account_update,
    prepare_content_update,
    snapshot_pending,
)
from creator_monitor.feishu.records import FeishuRecordStore, PendingRecord
from creator_monitor.tikhub import douyin, xiaohongshu
from creator_monitor.tikhub.client import TikHubClient


def _git_version() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "unknown"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_scheduled_sync(
    *,
    settings: Settings,
    manifest_path: Path,
    accounts_path: Path,
    include_comments: bool = False,
    use_cache: bool = False,
) -> dict[str, object]:
    started = datetime.now(UTC)
    run_id = f"sync-{started.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
    manifest = _load_json(manifest_path)
    account_config = _load_json(accounts_path)
    guard = BudgetGuard(
        ledger_path=settings.state_dir / "budget.json",
        run_id=run_id,
        max_total_usd=settings.max_usd,
        max_requests_per_run=settings.max_requests_per_run,
    )
    client = TikHubClient(
        api_key=settings.require_tikhub(),
        budget=guard,
        cache_dir=settings.state_dir / "cache",
        max_attempts=2,
    )

    accounts = []
    contents: list[Content] = []
    failures: list[dict[str, str]] = []
    for configured in account_config["accounts"]:
        if not configured.get("enabled", True):
            continue
        platform = Platform(configured["platform"])
        account_id = str(configured["account_id"])
        try:
            if platform is Platform.DOUYIN:
                profile = client.get(
                    douyin.PROFILE, {"sec_user_id": account_id}, use_cache=use_cache
                )
                posts = client.get(
                    douyin.POSTS,
                    {
                        "sec_user_id": account_id,
                        "max_cursor": 0,
                        "count": 20,
                        "sort_type": 0,
                        "channel": "normal",
                    },
                    use_cache=use_cache,
                )
                accounts.append(douyin.normalize_profile(profile, fetched_at=started))
                normalized, _ = douyin.normalize_posts(posts, fetched_at=started)
            else:
                profile = client.get(
                    xiaohongshu.PROFILE, {"user_id": account_id}, use_cache=use_cache
                )
                notes = client.get(
                    xiaohongshu.NOTES,
                    {"user_id": account_id, "cursor": ""},
                    use_cache=use_cache,
                )
                accounts.append(xiaohongshu.normalize_profile(profile, fetched_at=started))
                normalized, _ = xiaohongshu.normalize_notes(notes, fetched_at=started)
            contents.extend(normalized)
        except Exception as exc:  # noqa: BLE001 - one account must not abort the batch.
            failures.append(
                {
                    "object_key": f"{platform.value}:{account_id}",
                    "stage": "fetch",
                    "error_type": type(exc).__name__,
                    "message": str(exc)[:500],
                }
            )

    deduped = deduplicate_latest(contents)
    contents = deduped.records
    store = FeishuRecordStore(base_token=manifest["base_token"])
    account_result = store.sync(
        table_id=manifest["tables"]["账号库"],
        key_field="内部账号键",
        hash_field="数据哈希",
        records=[account_pending(account) for account in accounts],
        select_fields=["粉丝数", "启用监控", "监控状态", "抓取频率小时", "首次发现时间"],
        prepare_update=prepare_account_update,
    )
    nicknames = {account.business_key: account.nickname for account in accounts}
    pending_contents: list[PendingRecord] = []
    for content in contents:
        pending = content_pending(content, now=started)
        fields = dict(pending.fields)
        fields["账号昵称"] = (
            nicknames.get(f"{content.platform.value}:{content.account_id}") or content.account_id
        )
        pending_contents.append(PendingRecord(pending.business_key, pending.raw_hash, fields))
    content_result = store.sync(
        table_id=manifest["tables"]["内容库"],
        key_field="内部内容键",
        hash_field="数据哈希",
        records=pending_contents,
        select_fields=[
            "播放数",
            "点赞数",
            "收藏数",
            "评论数",
            "分享数",
            "状态",
            "内容方向",
            "账号地区",
            "数据来源",
            "本周排名",
            "推荐理由",
            "采用时间",
            "拆解文档",
            "ASR文案",
            "跟进建议",
            "首次发现时间",
        ],
        prepare_update=prepare_content_update,
    )

    bucket = bucket_time(started, bucket_minutes=60)
    snapshots = [
        MetricSnapshot(
            snapshot_id=snapshot_key(content.business_key, started, bucket_minutes=60),
            content_key=content.business_key,
            captured_at=started,
            bucket_time=bucket,
            metrics=content.metrics,
            run_id=run_id,
        )
        for content in contents
    ]
    snapshot_result = store.sync(
        table_id=manifest["tables"]["指标快照"],
        key_field="快照键",
        hash_field="快照键",
        records=[snapshot_pending(snapshot) for snapshot in snapshots],
    )

    comment_result = None
    if include_comments:
        sampled_comments = []
        for platform in Platform:
            candidates = [content for content in contents if content.platform is platform]
            if not candidates:
                continue
            candidate = max(candidates, key=lambda item: item.likes or 0)
            if platform is Platform.DOUYIN:
                payload = client.get(
                    douyin.COMMENTS,
                    {"aweme_id": candidate.content_id, "cursor": 0, "count": 20},
                    use_cache=use_cache,
                )
                comments, _ = douyin.normalize_comments(payload, fetched_at=started)
            else:
                payload = client.get(
                    xiaohongshu.COMMENTS,
                    {
                        "note_id": candidate.content_id,
                        "cursor": "",
                        "index": 0,
                        "pageArea": "UNFOLDED",
                        "sort_strategy": "latest_v2",
                    },
                    use_cache=use_cache,
                )
                comments, _ = xiaohongshu.normalize_comments(payload, fetched_at=started)
            sampled_comments.extend(comments)
        comments = deduplicate_latest(sampled_comments).records
        comment_result = store.sync(
            table_id=manifest["tables"]["评论库"],
            key_field="内部评论键",
            hash_field="数据哈希",
            records=[comment_pending(comment) for comment in comments],
        )

    finished = datetime.now(UTC)
    budget = guard.snapshot()
    run_budget = budget.get("runs", {}).get(run_id, {"requests": 0, "usd": "0"})
    status = "partial" if failures else "success"
    inserted = account_result.inserted + content_result.inserted + snapshot_result.inserted
    updated = account_result.updated + content_result.updated + snapshot_result.updated
    unchanged = account_result.unchanged + content_result.unchanged + snapshot_result.unchanged
    if comment_result:
        inserted += comment_result.inserted
        updated += comment_result.updated
        unchanged += comment_result.unchanged
    run_fields = {
        "运行ID": run_id,
        "任务名称": "Codex Skill 定时同步",
        "状态": [status],
        "开始时间": started.astimezone().strftime("%Y-%m-%d %H:%M"),
        "结束时间": finished.astimezone().strftime("%Y-%m-%d %H:%M"),
        "平台": "抖音,小红书",
        "抓取数": len(accounts) + len(contents),
        "批内去重数": deduped.duplicate_count,
        "新增数": inserted,
        "更新数": updated,
        "未变化数": unchanged,
        "失败数": len(failures),
        "TikHub请求数": run_budget["requests"],
        "TikHub费用USD": float(run_budget["usd"]),
        "错误类型": ",".join(sorted({item["error_type"] for item in failures})) or None,
        "错误摘要": json.dumps(failures, ensure_ascii=False)[:2000] if failures else None,
        "代码版本": _git_version(),
        "Schema版本": str(manifest.get("schema_version", "0.1.0")),
    }
    run_fields = {key: value for key, value in run_fields.items() if value is not None}
    store.sync(
        table_id=manifest["tables"]["运行日志"],
        key_field="运行ID",
        hash_field="运行ID",
        records=[PendingRecord(run_id, run_id, run_fields)],
    )
    summary = {
        "ok": not failures,
        "run_id": run_id,
        "status": status,
        "accounts": len(accounts),
        "contents": len(contents),
        "comments": len(sampled_comments) if include_comments else 0,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "failures": failures,
        "tikhub_requests": run_budget["requests"],
        "tikhub_reserved_usd": run_budget["usd"],
    }
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "latest-normalized.json").write_text(
        json.dumps(
            {
                "accounts": [account.model_dump(mode="json") for account in accounts],
                "contents": [content.model_dump(mode="json") for content in contents],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (settings.state_dir / "last-run.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
