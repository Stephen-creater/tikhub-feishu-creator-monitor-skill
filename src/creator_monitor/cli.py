from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer

from creator_monitor.config import Settings
from creator_monitor.feishu.bootstrap import BootstrapPlan, execute_bootstrap
from creator_monitor.services.report import send_daily_report
from creator_monitor.services.sync import run_scheduled_sync

app = typer.Typer(help="TikHub × Feishu creator monitoring Skill runtime")


@app.callback()
def main() -> None:
    """Run a creator monitoring command."""


@app.command()
def doctor() -> None:
    """Check local dependencies, secrets, manifest, and budget state."""
    settings = Settings.from_env()
    checks = {
        "lark_cli": bool(shutil.which("lark-cli")),
        "tikhub_key": settings.tikhub_api_key is not None,
        "manifest": settings.config_path.exists(),
        "accounts": (settings.state_dir / "accounts.json").exists(),
    }
    typer.echo(
        json.dumps(
            {"ok": all(checks.values()), "checks": checks, "config": settings.safe_summary()},
            ensure_ascii=False,
        )
    )


@app.command("bootstrap")
def bootstrap(dry_run: bool = typer.Option(False, "--dry-run")) -> None:
    """Create or reuse the Feishu Base schema."""
    settings = Settings.from_env()
    root = Path(__file__).resolve().parents[2]
    plan = BootstrapPlan.from_templates(
        root / "templates" / "base-schema.json", root / "templates" / "views.json"
    )
    if dry_run:
        typer.echo(json.dumps({"ok": True, "command": plan.base_create_command(dry_run=True)}, ensure_ascii=False))
        return
    manifest = execute_bootstrap(plan, manifest_path=settings.config_path)
    typer.echo(
        json.dumps(
            {
                "ok": True,
                "base_name": manifest["base_name"],
                "tables": len(manifest["tables"]),
                "views": len(manifest["views"]),
            },
            ensure_ascii=False,
        )
    )


@app.command("scheduled-sync")
def scheduled_sync(
    include_comments: bool = typer.Option(False, "--include-comments"),
    use_cache: bool = typer.Option(False, "--use-cache"),
) -> None:
    """Run the deterministic scheduled synchronization pipeline."""
    settings = Settings.from_env()
    result = run_scheduled_sync(
        settings=settings,
        manifest_path=settings.config_path,
        accounts_path=settings.state_dir / "accounts.json",
        include_comments=include_comments,
        use_cache=use_cache,
    )
    typer.echo(json.dumps(result, ensure_ascii=False))
    if not result["ok"]:
        raise typer.Exit(code=2)


@app.command("daily-report")
def daily_report() -> None:
    """Send the latest interactive report card via the configured Feishu bot."""
    result = send_daily_report(settings=Settings.from_env())
    typer.echo(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    app()
