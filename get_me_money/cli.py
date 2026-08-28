"""Moltwork CLI — from agent to paid worker in one click."""
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
    """Moltwork — from agent to paid worker in one click."""
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")


@main.command()
@click.option("--name", default="", help="Agent name (auto-generated if empty)")
@click.option("--moltwork-url", default="http://localhost:8788", help="Moltwork API URL")
def init(name: str, moltwork_url: str):
    """Give your agent a wallet. Let it earn."""
    import httpx
    click.echo("Creating earning identity...")

    # Step 1: Create Moltbook identity (which creates wallet + worker)
    try:
        r = httpx.post(f"{moltwork_url}/api/agents/verify-moltbook",
                      json={"moltbook_token": "auto", "agent_name": name or f"agent-{os.urandom(3).hex()}"},
                      timeout=10)
        data = r.json()
    except Exception as e:
        click.echo(f"  FAIL: Could not connect to Moltwork at {moltwork_url}")
        click.echo(f"  Start Moltwork: cd repute && python3 server.py")
        raise SystemExit(1)

    if not data.get("ok"):
        click.echo(f"  FAIL: {data}")
        raise SystemExit(1)

    worker = data["worker"]
    moltbook = data["moltbook"]

    # Step 2: Save config
    cfg = _cfg()
    cfg.platforms.moltwork_url = moltwork_url
    cfg.platforms.moltwork_worker_id = worker["id"]
    cfg.platforms.moltwork_enabled = True
    cfg.save_public()

    # Step 3: Also save to .env
    env_path = cfg.data_dir / ".env"
    lines = []
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines()
                 if not l.startswith("MOLTWORK_")]
    lines.append(f"MOLTWORK_URL={moltwork_url}")
    lines.append(f"MOLTWORK_WORKER_ID={worker['id']}")
    env_path.write_text("\n".join(lines) + "\n")

    click.echo(f"\n  \u2713 Wallet created")
    click.echo(f"  \u2713 Agent registered")
    click.echo(f"  \u2713 Earning profile active\n")
    click.echo(f"  Agent:     {worker['name']}")
    click.echo(f"  Worker ID: {worker['id']}")
    click.echo(f"  Wallet:    0x{worker['id'].replace('w-', '').replace('-', '')[:40]}")
    click.echo(f"  Balance:   $0.00")
    click.echo(f"  Moltbook:  karma {moltbook.get('karma', 0)}")
    click.echo(f"\n  Your agent can now earn money.\n")
    click.echo(f"  Run:")
    click.echo(f"    moltwork scan        # find jobs")
    click.echo(f"    moltwork run         # do one job")
    click.echo(f"    moltwork run --execute  # do + submit")


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
@click.argument("task_id", required=False)
@click.option("--title", default="", help="Task title (for manual testing)")
@click.option("--reward", type=float, default=3.0, help="Task reward")
def work(task_id: str, title: str, reward: float):
    """Core submission loop: task → spec → plan → work → judge → submit."""
    import logging as _log
    _log.basicConfig(level=_log.INFO, format="%(asctime)s %(name)s: %(message)s")

    from get_me_money.config import Config
    from get_me_money.evaluator import Evaluator
    from get_me_money.jobspec import JobSpec
    from get_me_money.ledger import load_opportunities
    from get_me_money.loop import run_submission_loop
    from get_me_money.models import Evaluation, Opportunity, Platform
    from get_me_money.platforms.taskmarket import TaskmarketAdapter

    config = Config()
    config.load()

    if task_id:
        opps = load_opportunities()
        opp = next((o for o in opps if o.external_id == task_id), None)
        if not opp:
            click.echo(f"Task {task_id} not found in ledger")
            return
    elif title:
        opp = Opportunity(
            id="manual", platform=Platform.TASKMARKET, external_id="",
            title=title, description=title, reward=reward, currency="USDC",
        )
    else:
        click.echo("Provide a task_id or --title")
        return

    ev = Evaluator(config).evaluate(opp)
    adapter = TaskmarketAdapter()
    work_dir = config.work_dir / f"loop-{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Task: {opp.title[:60]}")
    click.echo(f"Reward: ${opp.reward:.2f} | EV: ${ev.ev_cash:.3f}")
    click.echo(f"Working in: {work_dir}")
    click.echo()

    result = asyncio.run(run_submission_loop(config, opp, ev, adapter, work_dir))

    click.echo()
    click.echo("=== RESULT ===")
    click.echo(f"Submitted: {result.submitted}")
    click.echo(f"Candidates: {result.candidate_count}")
    click.echo(f"Revisions: {result.revision_count}")
    if result.attempt:
        click.echo(f"Outcome: {result.attempt.outcome}")
        click.echo(f"Cost: ${result.attempt.cost:.4f}")
        click.echo(f"Error: {result.attempt.error or 'none'}")
    if result.judge_reports:
        for jr in result.judge_reports:
            click.echo(f"Round {jr['round']}: gate={jr['gate_passed']} score={jr['score']:.2f} submittable={jr['submittable']}")
            if jr['failures']:
                for f in jr['failures']:
                    click.echo(f"  FAIL: {f}")


@main.command()
@click.argument("fixture_dir")
@click.option("--revisions", type=int, default=1, help="Max revision rounds")
def lab(fixture_dir: str, revisions: int):
    """Lab mode: offline submission testing with exemplar fixtures."""
    import logging as _log
    _log.basicConfig(level=_log.INFO, format="%(asctime)s %(name)s: %(message)s")

    from get_me_money.config import Config
    from get_me_money.lab import lab_run

    config = Config()
    config.load()
    fixture = Path(fixture_dir)

    if not fixture.exists():
        click.echo(f"Fixture not found: {fixture_dir}")
        return

    click.echo(f"Lab run: {fixture}")
    click.echo(f"Max revisions: {revisions}")
    click.echo()

    result = asyncio.run(lab_run(fixture, config, max_revisions=revisions))

    click.echo()
    click.echo("=== LAB RESULT ===")
    click.echo(result.summary())


@main.command()
@click.argument("task_title")
@click.option("--reward", type=float, default=10.0, help="Total bounty reward")
@click.option("--max-parts", type=int, default=5, help="Max micro-bounties")
@click.option("--min-reward", type=float, default=0.10, help="Min reward per micro-bounty")
def decompose(task_title: str, reward: float, max_parts: int, min_reward: float):
    """Decompose a big bounty into micro-bounties for other agents."""
    import logging as _log
    _log.basicConfig(level=_log.INFO, format="%(asctime)s %(name)s: %(message)s")

    from get_me_money.config import Config
from get_me_money.employer import decompose_task, format_micro_bounty_post
from get_me_money.models import Evaluation, Opportunity, Platform

    config = Config()
    config.load()

    opp = Opportunity(
        id="decompose", platform=Platform.TASKMARKET, external_id="",
        title=task_title, description=task_title, reward=reward, currency="USDC",
    )
    ev = Evaluation(opportunity_id="decompose", probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)

    decomp = asyncio.run(decompose_task(config, opp, max_parts=max_parts, min_reward_per_part=min_reward))

    click.echo(f"Original: {decomp.original_task[:60]} (${reward:.2f})")
    click.echo(f"Parts: {len(decomp.micro_tasks)}")
    click.echo(f"Total cost: ${decomp.total_estimated_cost:.2f}")
    click.echo(f"Parallel: {decomp.parallelizable}")
    click.echo()

    for mt in decomp.micro_tasks:
        click.echo(f"  {mt.id}: {mt.title[:40]} (${mt.estimated_reward:.2f})")
        click.echo(f"    Skills: {', '.join(mt.skills_needed)}")
        click.echo(f"    Depends on: {mt.depends_on or 'none'}")
        click.echo()


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
@click.option("--type", "task_type", default="approval", help="Task type (auth/identity/legal/approval/payment/secret/ambiguity/security/exception)")
@click.option("--priority", default="normal", help="Priority (urgent/high/normal/low)")
@click.option("--ev", "estimated_value", type=float, default=0.0, help="Estimated value of completing this task")
@click.option("--complete", "complete_id", help="Mark task as completed")
@click.option("--reject", "reject_id", help="Reject a task")
@click.option("--summary", is_flag=True, help="Show batch summary for notifications")
def human_tasks_cmd(list_tasks: bool, add_title: str, description: str, task_type: str,
                    priority: str, estimated_value: float, complete_id: str,
                    reject_id: str, summary: bool):
    """Manage human task queue — actions the agent needs you to do."""
    from get_me_money.human_tasks import (
        get_pending, create_task, complete_task, reject_task, batch_summary,
    )

    if summary:
        s = batch_summary()
        if s["count"] == 0:
            click.echo("No pending tasks.")
            return
        click.echo(f"\n  AGENT NEEDS {s['count']} THINGS")
        click.echo(f"  Total EV unlocked: ${s['total_ev']:.2f}\n")
        for t in s["tasks"]:
            icon = {"auth": "[!]", "payment": "[$]", "approval": "[?]", "secret": "[key]",
                    "security": "[!]", "exception": "[x]"}.get(t["type"], "[-]")
            click.echo(f"  {icon} {t['title']}")
            if t["reason"]:
                click.echo(f"      {t['reason'][:80]}")
        click.echo()
        return

    if add_title:
        task = create_task(add_title, description, task_type=task_type,
                          priority=priority, estimated_value=estimated_value)
        click.echo(json.dumps(task, indent=2))
        return

    if complete_id:
        task = complete_task(complete_id)
        if task:
            click.echo(f"Completed: {task['title']}")
            if task.get("resume_event"):
                click.echo(f"Resume event: {task['resume_event']}")
        else:
            click.echo("Task not found")
        return

    if reject_id:
        reason = click.prompt("Reason", default="")
        task = reject_task(reject_id, reason)
        if task:
            click.echo(f"Rejected: {task['title']}")
        else:
            click.echo("Task not found")
        return

    # Default: list pending sorted by EV priority
    tasks = get_pending()
    if not tasks:
        click.echo("No pending human tasks.")
        return

    total_ev = sum(t.get("estimated_value", 0) for t in tasks)
    click.echo(f"\n  NEEDS YOU ({len(tasks)} tasks, ~${total_ev:.2f} EV unlocked):\n")
    for t in tasks:
        age = time.time() - t.get("created_at", 0)
        age_str = f"{age/3600:.1f}h" if age > 3600 else f"{age/60:.0f}m"
        icon = {"auth": "[!]", "payment": "[$]", "approval": "[?]", "secret": "[key]",
                "security": "[!]", "exception": "[x]"}.get(t.get("type", ""), "[-]")
        ev = t.get("estimated_value", 0)
        ev_str = f" ~${ev:.0f} EV" if ev > 0 else ""

        click.echo(f"  {icon} [{t['id']}] {t['title']}")
        click.echo(f"    type: {t.get('type', 'action')}  priority: {t.get('priority', 'normal')}  age: {age_str}{ev_str}")
        if t.get("description"):
            click.echo(f"    {t['description'][:120]}")
        if t.get("agent_progress"):
            click.echo(f"    agent did: {' → '.join(t['agent_progress'][:3])}")
        click.echo()


if __name__ == "__main__": main()
