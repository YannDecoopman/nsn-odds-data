"""CLI for managing API keys.

Usage:
    python -m app.cli create-api-key --name "topoffshorebets.com"
    python -m app.cli list-api-keys
    python -m app.cli revoke-api-key --key "nsn_xxx"
"""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from app.db import async_session_maker
from app.services import api_key_service

app = typer.Typer(help="NSN Odds Data API Key Management")
console = Console()


async def _create_api_key(name: str) -> None:
    async with async_session_maker() as session:
        api_key = await api_key_service.create_key(session, name)
        console.print(f"\n[green]✓[/green] API Key created for [bold]{name}[/bold]")
        console.print(f"\n  [cyan]{api_key.key}[/cyan]\n")
        console.print("[yellow]⚠[/yellow] Store this key securely. It cannot be retrieved later.\n")


@app.command("create-api-key")
def create_api_key(
    name: str = typer.Option(..., "--name", "-n", help="Site name (e.g., topoffshorebets.com)")
):
    """Create a new API key for a site."""
    asyncio.run(_create_api_key(name))


async def _list_api_keys() -> None:
    async with async_session_maker() as session:
        keys = await api_key_service.list_keys(session)

        if not keys:
            console.print("\n[yellow]No API keys found.[/yellow]\n")
            return

        table = Table(title="API Keys")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Key (truncated)", style="green")
        table.add_column("Active", style="magenta")
        table.add_column("Created", style="blue")
        table.add_column("Last Used", style="yellow")

        for key in keys:
            key_preview = f"{key.key[:12]}...{key.key[-4:]}" if len(key.key) > 16 else key.key
            active = "✓" if key.is_active else "✗"
            created = key.created_at.strftime("%Y-%m-%d %H:%M") if key.created_at else "-"
            last_used = key.last_used_at.strftime("%Y-%m-%d %H:%M") if key.last_used_at else "Never"

            table.add_row(
                str(key.id),
                key.name,
                key_preview,
                active,
                created,
                last_used,
            )

        console.print()
        console.print(table)
        console.print()


@app.command("list-api-keys")
def list_api_keys():
    """List all API keys."""
    asyncio.run(_list_api_keys())


async def _revoke_api_key(key: str) -> None:
    async with async_session_maker() as session:
        success = await api_key_service.revoke_key(session, key)
        if success:
            console.print(f"\n[green]✓[/green] API key revoked successfully.\n")
        else:
            console.print(f"\n[red]✗[/red] API key not found.\n")


@app.command("revoke-api-key")
def revoke_api_key(
    key: str = typer.Option(..., "--key", "-k", help="Full API key to revoke")
):
    """Revoke an API key (set inactive)."""
    asyncio.run(_revoke_api_key(key))


async def _delete_api_key(key: str) -> None:
    async with async_session_maker() as session:
        success = await api_key_service.delete_key(session, key)
        if success:
            console.print(f"\n[green]✓[/green] API key deleted permanently.\n")
        else:
            console.print(f"\n[red]✗[/red] API key not found.\n")


@app.command("delete-api-key")
def delete_api_key(
    key: str = typer.Option(..., "--key", "-k", help="Full API key to delete")
):
    """Permanently delete an API key."""
    if typer.confirm("Are you sure you want to permanently delete this API key?"):
        asyncio.run(_delete_api_key(key))
    else:
        console.print("\n[yellow]Cancelled.[/yellow]\n")


if __name__ == "__main__":
    app()
