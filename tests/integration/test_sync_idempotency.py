from __future__ import annotations

import json

from creator_monitor.feishu.records import FeishuRecordStore, PendingRecord


class FakeCLI:
    def __init__(self, existing: list[dict] | None = None) -> None:
        self.existing = existing or []
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> dict:
        self.commands.append(command)
        operation = command[2]
        if operation == "+record-list":
            return {"ok": True, "data": {"records": self.existing, "has_more": False}}
        if operation == "+record-batch-create":
            body = json.loads(command[command.index("--json") + 1])
            return {
                "ok": True,
                "data": {"record_id_list": [f"rec-{i}" for i in range(len(body["create_records"]))]},
            }
        if operation == "+record-batch-update":
            return {"ok": True, "data": {}}
        raise AssertionError(f"unexpected command: {command}")


class ColumnarFakeCLI(FakeCLI):
    def run(self, command: list[str]) -> dict:
        self.commands.append(command)
        if command[2] == "+record-list":
            return {
                "ok": True,
                "data": {
                    "fields": ["内容键", "数据哈希", "点赞数"],
                    "data": [["douyin:1", "hash-1", 10]],
                    "record_id_list": ["rec-1"],
                    "has_more": False,
                },
            }
        return super().run(command)


class EventuallyConsistentCLI(FakeCLI):
    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    def run(self, command: list[str]) -> dict:
        if command[2] == "+record-list":
            self.commands.append(command)
            self.reads += 1
            if self.reads == 1:
                return {"ok": True, "data": {"data": [], "fields": [], "record_id_list": []}}
            return {
                "ok": True,
                "data": {
                    "fields": ["内容键", "数据哈希"],
                    "data": [["douyin:1", "hash-1"]],
                    "record_id_list": ["rec-1"],
                },
            }
        return super().run(command)


def _pending(key: str, digest: str, likes: int) -> PendingRecord:
    return PendingRecord(
        business_key=key,
        raw_hash=digest,
        fields={"内容键": key, "数据哈希": digest, "点赞数": likes},
    )


def test_first_sync_creates_records_in_one_batch() -> None:
    fake = FakeCLI()
    store = FeishuRecordStore(base_token="bas_demo", cli=fake)

    result = store.sync(
        table_id="tbl_content",
        key_field="内容键",
        hash_field="数据哈希",
        records=[_pending("douyin:1", "hash-1", 10), _pending("douyin:2", "hash-2", 20)],
    )

    assert result.inserted == 2
    assert result.updated == 0
    assert result.unchanged == 0
    create_commands = [cmd for cmd in fake.commands if cmd[2] == "+record-batch-create"]
    assert len(create_commands) == 1


def test_second_sync_is_unchanged_and_writes_nothing() -> None:
    fake = FakeCLI(
        existing=[
            {
                "record_id": "rec-1",
                "fields": {"内容键": "douyin:1", "数据哈希": "hash-1", "点赞数": 10},
            }
        ]
    )
    store = FeishuRecordStore(base_token="bas_demo", cli=fake)

    result = store.sync(
        table_id="tbl_content",
        key_field="内容键",
        hash_field="数据哈希",
        records=[_pending("douyin:1", "hash-1", 10)],
    )

    assert result.unchanged == 1
    assert all("batch" not in cmd[2] for cmd in fake.commands)


def test_changed_record_uses_record_id_batch_update() -> None:
    fake = FakeCLI(
        existing=[
            {
                "record_id": "rec-1",
                "fields": {"内容键": "douyin:1", "数据哈希": "old-hash", "点赞数": 10},
            }
        ]
    )
    store = FeishuRecordStore(base_token="bas_demo", cli=fake)

    result = store.sync(
        table_id="tbl_content",
        key_field="内容键",
        hash_field="数据哈希",
        records=[_pending("douyin:1", "new-hash", 20)],
    )

    assert result.updated == 1
    update = next(cmd for cmd in fake.commands if cmd[2] == "+record-batch-update")
    body = json.loads(update[update.index("--json") + 1])
    assert body["update_records"] == {
        "rec-1": {"内容键": "douyin:1", "数据哈希": "new-hash", "点赞数": 20}
    }


def test_duplicate_existing_business_key_fails_closed() -> None:
    fake = FakeCLI(
        existing=[
            {"record_id": "rec-1", "fields": {"内容键": "douyin:1", "数据哈希": "a"}},
            {"record_id": "rec-2", "fields": {"内容键": "douyin:1", "数据哈希": "b"}},
        ]
    )
    store = FeishuRecordStore(base_token="bas_demo", cli=fake)

    try:
        store.sync(
            table_id="tbl_content",
            key_field="内容键",
            hash_field="数据哈希",
            records=[_pending("douyin:1", "new", 20)],
        )
    except ValueError as error:
        assert "duplicate business key" in str(error)
    else:
        raise AssertionError("duplicate existing keys must fail closed")


def test_current_lark_cli_columnar_response_is_parsed() -> None:
    fake = ColumnarFakeCLI()
    store = FeishuRecordStore(base_token="bas_demo", cli=fake)

    result = store.sync(
        table_id="tbl_content",
        key_field="内容键",
        hash_field="数据哈希",
        records=[_pending("douyin:1", "hash-1", 10)],
    )

    assert result.unchanged == 1
    assert result.inserted == 0


def test_candidate_lookup_retries_feishu_eventual_consistency() -> None:
    fake = EventuallyConsistentCLI()
    store = FeishuRecordStore(
        base_token="bas_demo", cli=fake, consistency_attempts=2, sleeper=lambda _: None
    )

    result = store.sync(
        table_id="tbl_content",
        key_field="内容键",
        hash_field="数据哈希",
        records=[_pending("douyin:1", "hash-1", 10)],
    )

    assert result.unchanged == 1
    assert fake.reads == 2
