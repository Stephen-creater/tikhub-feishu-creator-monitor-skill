from __future__ import annotations

import json

import typer


app = typer.Typer(help="TikHub × Feishu creator monitoring Skill runtime")


@app.callback()
def main() -> None:
    """Run a creator monitoring command."""


@app.command()
def doctor() -> None:
    """Report whether the runtime scaffold is available."""
    typer.echo(json.dumps({"ok": True, "status": "scaffold-ready"}, ensure_ascii=False))


if __name__ == "__main__":
    app()
