from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol, TypeVar

from creator_monitor.feishu.cli import LarkCLI


class CommandRunner(Protocol):
    def run(self, command: list[str]) -> dict: ...


@dataclass(frozen=True)
class PendingRecord:
    business_key: str
    raw_hash: str
    fields: dict[str, object]


@dataclass(frozen=True)
class ExistingRecord:
    record_id: str
    fields: dict[str, object]


@dataclass(frozen=True)
class SyncResult:
    inserted: int
    updated: int
    unchanged: int
    record_ids_by_key: dict[str, str]


UpdateTransform = Callable[[PendingRecord, ExistingRecord], PendingRecord]


T = TypeVar("T")


def _chunks(items: list[T], size: int) -> Iterable[list[T]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


class FeishuRecordStore:
    def __init__(
        self,
        *,
        base_token: str,
        cli: CommandRunner | None = None,
        consistency_attempts: int = 3,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_token = base_token
        self.cli = cli or LarkCLI()
        self.consistency_attempts = max(1, consistency_attempts)
        self.sleeper = sleeper

    def find_by_keys(
        self,
        *,
        table_id: str,
        key_field: str,
        keys: list[str],
        select_fields: list[str] | None = None,
    ) -> dict[str, ExistingRecord]:
        found: dict[str, ExistingRecord] = {}
        requested_fields = list(dict.fromkeys([key_field, *(select_fields or [])]))
        for key_batch in _chunks(list(dict.fromkeys(keys)), 20):
            filter_payload = {
                "logic": "or",
                "conditions": [[key_field, "==", key] for key in key_batch],
            }
            command = [
                "lark-cli",
                "base",
                "+record-list",
                "--base-token",
                self.base_token,
                "--table-id",
                table_id,
                "--filter-json",
                json.dumps(filter_payload, ensure_ascii=False, separators=(",", ":")),
                "--limit",
                "200",
                "--format",
                "json",
                "--as",
                "user",
            ]
            for field in requested_fields:
                command.extend(["--field-id", field])
            records: list[dict[str, object]] = []
            for attempt in range(self.consistency_attempts):
                payload = self.cli.run(command)
                records = _records_from_payload(payload)
                if records or attempt + 1 == self.consistency_attempts:
                    break
                self.sleeper(0.5 * (attempt + 1))
            for raw in records:
                fields = raw.get("fields", {})
                key = fields.get(key_field)
                if not isinstance(key, str) or not key:
                    continue
                if key in found:
                    raise ValueError(f"duplicate business key already exists in Base: {key}")
                found[key] = ExistingRecord(record_id=str(raw["record_id"]), fields=fields)
        return found

    def sync(
        self,
        *,
        table_id: str,
        key_field: str,
        hash_field: str,
        records: list[PendingRecord],
        select_fields: list[str] | None = None,
        prepare_update: UpdateTransform | None = None,
    ) -> SyncResult:
        keys = [record.business_key for record in records]
        if len(keys) != len(set(keys)):
            raise ValueError("pending records contain duplicate business keys")
        existing = self.find_by_keys(
            table_id=table_id,
            key_field=key_field,
            keys=keys,
            select_fields=[hash_field, *(select_fields or [])],
        )

        creates: list[PendingRecord] = []
        updates: dict[str, PendingRecord] = {}
        unchanged = 0
        record_ids_by_key = {key: value.record_id for key, value in existing.items()}
        for record in records:
            current = existing.get(record.business_key)
            if current is None:
                creates.append(record)
                continue
            if current.fields.get(hash_field) == record.raw_hash:
                unchanged += 1
                continue
            updates[current.record_id] = (
                prepare_update(record, current) if prepare_update else record
            )

        for batch in _chunks(creates, 200):
            payload = {"create_records": [record.fields for record in batch]}
            result = self.cli.run(
                [
                    "lark-cli",
                    "base",
                    "+record-batch-create",
                    "--base-token",
                    self.base_token,
                    "--table-id",
                    table_id,
                    "--json",
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    "--as",
                    "user",
                ]
            )
            ids = result.get("data", {}).get("record_id_list", [])
            for record, record_id in zip(batch, ids, strict=False):
                record_ids_by_key[record.business_key] = str(record_id)

        update_items = list(updates.items())
        for batch in _chunks(update_items, 200):
            payload = {
                "update_records": {
                    record_id: pending.fields for record_id, pending in batch
                }
            }
            self.cli.run(
                [
                    "lark-cli",
                    "base",
                    "+record-batch-update",
                    "--base-token",
                    self.base_token,
                    "--table-id",
                    table_id,
                    "--json",
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    "--as",
                    "user",
                ]
            )

        return SyncResult(
            inserted=len(creates),
            updated=len(updates),
            unchanged=unchanged,
            record_ids_by_key=record_ids_by_key,
        )


def _records_from_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    envelope = payload.get("data")
    if not isinstance(envelope, dict):
        return []
    object_records = envelope.get("records")
    if isinstance(object_records, list):
        return [record for record in object_records if isinstance(record, dict)]

    names = envelope.get("fields")
    rows = envelope.get("data")
    record_ids = envelope.get("record_id_list")
    if not isinstance(names, list) or not isinstance(rows, list) or not isinstance(record_ids, list):
        return []
    records: list[dict[str, object]] = []
    for record_id, row in zip(record_ids, rows, strict=False):
        if not isinstance(row, list):
            continue
        fields = {str(name): value for name, value in zip(names, row, strict=False)}
        records.append({"record_id": str(record_id), "fields": fields})
    return records
