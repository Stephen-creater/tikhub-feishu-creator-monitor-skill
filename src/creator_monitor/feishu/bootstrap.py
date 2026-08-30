from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from creator_monitor.feishu.cli import LarkCLI


@dataclass(frozen=True)
class TableSpec:
    name: str
    fields: list[dict[str, object]]


@dataclass(frozen=True)
class ViewSpec:
    name: str
    view_type: str


@dataclass(frozen=True)
class BootstrapPlan:
    base_name: str
    time_zone: str
    tables: list[TableSpec]
    view_table: str
    views: list[ViewSpec]

    @classmethod
    def from_templates(cls, schema_path: Path, views_path: Path) -> "BootstrapPlan":
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        view_config = json.loads(views_path.read_text(encoding="utf-8"))
        return cls(
            base_name=str(schema["base_name"]),
            time_zone=str(schema.get("time_zone", "Asia/Shanghai")),
            tables=[
                TableSpec(name=str(item["name"]), fields=list(item["fields"]))
                for item in schema["tables"]
            ],
            view_table=str(view_config["table"]),
            views=[
                ViewSpec(name=str(item["name"]), view_type=str(item.get("type", "grid")))
                for item in view_config["views"]
            ],
        )

    def base_create_command(self, *, dry_run: bool = False) -> list[str]:
        first_table = self.tables[0]
        command = [
            "lark-cli",
            "base",
            "+base-create",
            "--name",
            self.base_name,
            "--time-zone",
            self.time_zone,
            "--table-name",
            first_table.name,
            "--fields",
            json.dumps(first_table.fields, ensure_ascii=False, separators=(",", ":")),
            "--as",
            "user",
        ]
        if dry_run:
            command.append("--dry-run")
        return command

    def table_create_commands(self, base_token: str, *, dry_run: bool = False) -> list[list[str]]:
        commands: list[list[str]] = []
        for table in self.tables[1:]:
            command = [
                "lark-cli",
                "base",
                "+table-create",
                "--base-token",
                base_token,
                "--name",
                table.name,
                "--fields",
                json.dumps(table.fields, ensure_ascii=False, separators=(",", ":")),
                "--as",
                "user",
            ]
            if dry_run:
                command.append("--dry-run")
            commands.append(command)
        return commands

    def view_create_commands(self, base_token: str, *, dry_run: bool = False) -> list[list[str]]:
        commands: list[list[str]] = []
        for view in self.views:
            command = [
                "lark-cli",
                "base",
                "+view-create",
                "--base-token",
                base_token,
                "--table-id",
                self.view_table,
                "--json",
                json.dumps(
                    {"name": view.name, "type": view.view_type},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "--as",
                "user",
            ]
            if dry_run:
                command.append("--dry-run")
            commands.append(command)
        return commands


def _find_first(value: object, keys: Iterable[str]) -> str | None:
    if isinstance(value, dict):
        for key in keys:
            found = value.get(key)
            if isinstance(found, str) and found:
                return found
        for child in value.values():
            found = _find_first(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first(child, keys)
            if found:
                return found
    return None


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def execute_bootstrap(
    plan: BootstrapPlan,
    *,
    manifest_path: Path,
    cli: LarkCLI | None = None,
    existing_base_token: str | None = None,
) -> dict[str, object]:
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    runner = cli or LarkCLI()
    if existing_base_token:
        base_token = existing_base_token
        base_result: dict[str, object] = {}
    else:
        base_result = runner.run(plan.base_create_command())
        base_token = _find_first(base_result, ("base_token", "app_token"))
        if not base_token:
            raise ValueError("lark-cli base creation returned no base_token")

    table_list_result = runner.run(
        [
            "lark-cli",
            "base",
            "+table-list",
            "--base-token",
            base_token,
            "--as",
            "user",
        ]
    )
    table_ids = _named_id_map(table_list_result, collection="tables")
    if not table_ids:
        initial_table_id = _find_first(base_result, ("table_id", "id"))
        if initial_table_id:
            table_ids[plan.tables[0].name] = initial_table_id

    table_commands = dict(
        zip(
            (table.name for table in plan.tables[1:]),
            plan.table_create_commands(base_token),
            strict=True,
        )
    )
    for table in plan.tables:
        if table.name in table_ids:
            continue
        command = table_commands.get(table.name)
        if command is None:
            raise ValueError(f"initial table {table.name} was not returned by lark-cli")
        result = runner.run(command)
        table_id = _find_first(result, ("table_id", "id"))
        if not table_id:
            raise ValueError(f"lark-cli returned no table id for {table.name}")
        table_ids[table.name] = table_id

    view_list_result = runner.run(
        [
            "lark-cli",
            "base",
            "+view-list",
            "--base-token",
            base_token,
            "--table-id",
            table_ids[plan.view_table],
            "--as",
            "user",
        ]
    )
    view_ids = _named_id_map(view_list_result, collection="views")
    for view, command in zip(plan.views, plan.view_create_commands(base_token), strict=True):
        if view.name in view_ids:
            continue
        command[command.index("--table-id") + 1] = table_ids[plan.view_table]
        result = runner.run(command)
        view_id = _find_first(result, ("view_id", "id"))
        if view_id:
            view_ids[view.name] = view_id

    manifest: dict[str, object] = {
        "schema_version": "0.1.0",
        "base_name": plan.base_name,
        "base_token": base_token,
        "tables": table_ids,
        "views": view_ids,
    }
    _write_manifest(manifest_path, manifest)
    return manifest


def _named_id_map(payload: dict[str, object], *, collection: str) -> dict[str, str]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}
    items = data.get(collection)
    if not isinstance(items, list):
        return {}
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        identifier = item.get("id") or item.get(f"{collection[:-1]}_id")
        if isinstance(name, str) and isinstance(identifier, str):
            result[name] = identifier
    return result
