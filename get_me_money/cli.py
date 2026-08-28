"""CLI + Dashboard server entry point."""

from __future__ import annotations

import json
import logging
import sys

import click

from get_me_money.config import Config


@click.group()
@click.option("--log-level", default="INFO")
def main(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


@main.command()
def scan() -> None:
    """Scan all platforms for new opportunities."""
    import asyncio
    from get_me_money.main import scan_all
    config = Config()
    config.load()
    results = asyncio.run(scan_all(config))
    click.echo(json.dumps(results, indent=2, default=str))


@main.command()
@click.option("--dry-run", is_flag=True, help="Evaluate but don't execute")
def run(dry_run: bool) -> None:
    """Run the full earn cycle: scan → evaluate → attempt → record."""
    import asyncio
    from get_me_money.main import earn_cycle
    config = Config()
    config.load()
    result = asyncio.run(earn_cycle(config, dry_run=dry_run))
    click.echo(json.dumps(result, indent=2, default=str))


@main.command()
def dashboard() -> None:
    """Show current P&L and strategy summary."""
    from get_me_money.dashboard import get_dashboard_data
    data = get_dashboard_data()

    click.echo("\n" + "=" * 50)
    click.echo("  GET-ME-MONEY — P&L Dashboard")
    click.echo("=" * 50)
    click.echo(f"  Opportunities attempted: {data.get('opportunities_attempted', 0)}")
    click.echo(f"  Successes:               {data.get('successes', 0)}")
    click.echo(f"  Failures:                {data.get('failures', 0)}")
    click.echo(f"  Gross earned:            ${data.get('gross_earned', 0):.2f}")
    click.echo(f"  Compute/API costs:       ${data.get('total_cost', 0):.2f}")
    click.echo(f"  Fees:                    ${data.get('total_fees', 0):.2f}")
    click.echo(f"  Net earned:              ${data.get('net_earned', 0):.2f}")
    click.echo(f"  ROI:                     {data.get('roi_pct', 0):.1f}%")
    click.echo(f"  Best platform:           {data.get('best_platform', 'n/a')}")
    click.echo(f"  Best category:           {data.get('best_category', 'n/a')}")

    strategies = data.get("strategies", {})
    if strategies:
        click.echo("\n  STRATEGIES:")
        for cat, s in sorted(strategies.items(), key=lambda x: x[1].get("avg_net", 0), reverse=True):
            click.echo(
                f"    {cat:20s}  "
                f"EV/attempt: ${s.get('avg_net', 0):+.2f}  "
                f"win: {s.get('win_rate', 0):.0%}  "
                f"n={s.get('attempts', 0)}"
            )
    click.echo("")


@main.command()
def strategies() -> None:
    """Show learned strategies."""
    from get_me_money.memory import Memory
    mem = Memory()
    mem.load()
    summary = mem.summary()

    click.echo("\n  BEST STRATEGIES (learned from history):")
    for s in summary.get("best_strategies", []):
        click.echo(
            f"    {s['cat']:20s} on {s['platform']:12s}  "
            f"net: ${s['net']:+.2f}  win: {s['win_rate']:.0%}  n={s['n']}"
        )

    click.echo("\n  WORST STRATEGIES (avoid these):")
    for s in summary.get("worst_strategies", []):
        click.echo(
            f"    {s['cat']:20s} on {s['platform']:12s}  "
            f"net: ${s['net']:+.2f}  win: {s['win_rate']:.0%}  n={s['n']}"
        )
    click.echo("")


@main.command()
def health() -> None:
    """Check health of all platform adapters."""
    import asyncio
    from get_me_money.main import get_adapters
    config = Config()
    config.load()
    adapters = get_adapters(config)

    async def _check():
        for name, adapter in adapters.items():
            ok = await adapter.health_check()
            status = "OK" if ok else "DOWN"
            click.echo(f"  {name:15s} [{status}]")

    asyncio.run(_check())


@main.command()
def auth() -> None:
    """Show auth status for all platforms."""
    from get_me_money.identity import IdentityManager
    mgr = IdentityManager()
    summary = mgr.status_summary()

    click.echo("\n  PLATFORM AUTH STATUS:")
    click.echo("  " + "-" * 55)
    for platform, info in sorted(summary.items()):
        status = "VALID" if info["valid"] else "NEEDS AUTH"
        if info["needs_human"]:
            status = f"HUMAN REQUIRED: {info['reason']}"
        click.echo(f"  {platform:15s}  {info['auth_type']:15s}  {status}")
    click.echo("")


@main.command()
@click.argument("platform")
@click.argument("api_key")
def register_key(platform: str, api_key: str) -> None:
    """Register an API key for a platform."""
    from get_me_money.identity import IdentityManager
    mgr = IdentityManager()
    mgr.register_api_key(platform, api_key)
    click.echo(f"  Registered API key for {platform}")


if __name__ == "__main__":
    main()
