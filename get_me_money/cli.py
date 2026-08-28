"""Production CLI. Real marketplace writes require an explicit --execute flag."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
import click

from get_me_money.config import Config


def _cfg() -> Config:
    c = Config(); c.load(); return c


@click.group()
@click.option("--log-level", default="INFO")
def main(log_level: str):
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")


@main.command()
def scan():
    """Read live earning surfaces. No submissions or financial writes."""
    from get_me_money.main import scan_all
    click.echo(json.dumps(asyncio.run(scan_all(_cfg())), indent=2, default=str))


@main.command()
@click.option("--execute", is_flag=True, help="Perform real Hermes work and marketplace submission. Without this: dry-run only.")
def run(execute: bool):
    """Run one scan/evaluate/attempt cycle."""
    from get_me_money.main import earn_cycle
    click.echo(json.dumps(asyncio.run(earn_cycle(_cfg(), execute=execute)), indent=2, default=str))


@main.command()
@click.option("--execute", is_flag=True, help="Required for real submissions.")
def daemon(execute: bool):
    """Run continuously on the VPS."""
    from get_me_money.daemon import run as daemon_run
    asyncio.run(daemon_run(execute))


@main.command()
def reconcile():
    """Refresh pending submissions and record real payouts/rejections."""
    from get_me_money.main import reconcile_pending
    click.echo(json.dumps(asyncio.run(reconcile_pending(_cfg())), indent=2))


@main.command()
def dashboard():
    """Print current P&L."""
    from get_me_money.dashboard import get_dashboard_data
    click.echo(json.dumps(get_dashboard_data(), indent=2))


@main.command("mark-paid")
@click.argument("attempt_id")
@click.option("--amount", type=float, required=True)
@click.option("--fee", type=float, default=0.0)
@click.option("--reference", default="")
def mark_paid(attempt_id: str, amount: float, fee: float, reference: str):
    """Human reconciliation for a payout source without an official result-read API."""
    from get_me_money.ledger import get_attempt, save_attempt
    from get_me_money.models import Outcome
    a = get_attempt(attempt_id)
    if not a: raise click.ClickException("attempt not found")
    a.finalize(Outcome.SUCCEEDED, reward=amount, fees=fee)
    if reference: a.metadata["settlement_reference"] = reference
    save_attempt(a); click.echo(json.dumps({"ok": True, "attempt_id": a.id, "net": a.net}, indent=2))


@main.command("superteam-register")
@click.argument("name")
def superteam_register(name: str):
    """Register an official Superteam agent identity. Human payout claim remains separate."""
    from get_me_money.platforms.superteam import SuperteamAdapter
    data = asyncio.run(SuperteamAdapter.register(name))
    click.echo(json.dumps(data, indent=2))
    click.echo("\nStore apiKey as SUPERTEAM_KEY in your private EnvironmentFile. Keep claimCode for the human payout-claim flow.", err=True)


@main.command()
def doctor():
    """Production preflight. Does not accept terms or change accounts."""
    c = _cfg(); rows=[]
    def add(name, ok, detail): rows.append((name, bool(ok), str(detail)))

    hermes = shutil.which(c.hermes.binary)
    add("hermes binary", hermes, hermes or "not found")
    if hermes:
        try:
            r=subprocess.run([hermes,"--version"],capture_output=True,text=True,timeout=20); add("hermes version", r.returncode==0,(r.stdout or r.stderr).strip())
            env=os.environ.copy()
            if c.hermes.home: env["HERMES_HOME"]=c.hermes.home
            d=subprocess.run([hermes,"dump"],capture_output=True,text=True,timeout=30,env=env)
            dump=(d.stdout or d.stderr)
            terminal_line=next((x.strip() for x in dump.splitlines() if x.strip().startswith("terminal:")), "terminal: unknown")
            add("Hermes isolated profile", bool(c.hermes.home), c.hermes.home or "set GMM_HERMES_HOME; do not expose controller credentials to marketplace work")
            add("Hermes terminal isolation", "docker" in terminal_line.lower(), terminal_line + " (Docker recommended)")
        except Exception as e: add("hermes diagnostics",False,e)

    tm=shutil.which("taskmarket"); add("taskmarket CLI", tm, tm or "install @lucid-agents/taskmarket")
    if tm:
        for label,args in (("taskmarket identity",["identity","status"]),("taskmarket legal",["legal","status"]),("taskmarket read",["task","list","--status","open","--limit","1"])):
            try:
                r=subprocess.run([tm,*args],capture_output=True,text=True,timeout=30); text=(r.stdout or r.stderr).strip(); ok=r.returncode==0
                if label=="taskmarket legal" and ok:
                    try: ok=bool(json.loads(text).get("data",{}).get("accepted"))
                    except Exception: ok=False
                add(label,ok,text[:500])
            except Exception as e: add(label,False,e)

    if c.platforms.superteam_enabled:
        add("Superteam API key", bool(c.platforms.superteam_key), "configured" if c.platforms.superteam_key else "optional; discovery disabled until SUPERTEAM_KEY is set")

    for name,ok,detail in rows:
        click.echo(f"{'OK  ' if ok else 'FAIL'} {name:28s} {detail}")
    if any(not ok for _,ok,_ in rows):
        raise SystemExit(1)


@main.command("human-tasks")
@click.option("--list", "list_tasks", is_flag=True, help="List pending human tasks")
@click.option("--add", "add_title", help="Add a new human task")
@click.option("--description", default="", help="Task description")
@click.option("--complete", "complete_id", help="Mark task as completed")
def human_tasks_cmd(list_tasks: bool, add_title: str, description: str, complete_id: str):
    """Manage human task queue — actions the agent needs you to do."""
    from get_me_money.human_tasks import get_pending, get_all, create_task, complete_task

    if add_title:
        task = create_task(add_title, description)
        click.echo(json.dumps(task, indent=2))
        return

    if complete_id:
        task = complete_task(complete_id)
        if task:
            click.echo(f"Completed: {task['title']}")
        else:
            click.echo("Task not found")
        return

    # Default: list pending
    tasks = get_pending()
    if not tasks:
        click.echo("No pending human tasks.")
        return

    click.echo(f"\n  PENDING HUMAN TASKS ({len(tasks)}):\n")
    for t in tasks:
        age = time.time() - t.get("created_at", 0)
        age_str = f"{age/3600:.1f}h" if age > 3600 else f"{age/60:.0f}m"
        click.echo(f"  [{t['id']}] {t['title']}")
        click.echo(f"    type: {t.get('type', 'action')}  priority: {t.get('priority', 'normal')}  age: {age_str}")
        if t.get("description"):
            click.echo(f"    {t['description'][:100]}")
        click.echo()


if __name__ == "__main__": main()
