# get-me-money LIVE v0

This overlay turns the current prototype into a deliberately narrow live system.

## What is live in v0

- **Taskmarket:** discovery, eligibility/pre-submit checks, file submission, wallet-based payout reconciliation through the official `taskmarket` CLI.
- **Superteam Earn:** official agent-API discovery. Submission is disabled by default (`SUPERTEAM_AUTOSUBMIT=0`) because many listings require a public deployment/link or human payout fields. Turn it on only after you have verified the exact listing flow.
- **Hermes:** actual worker. Every attempt is a fresh one-shot run; `SUBMISSION.md` must exist before the controller will submit anything. Hermes' `--usage-file` is used for measured model cost.
- **Ledger:** append-only JSONL, but readers use the latest record for each attempt. Pending payouts can be reconciled later without double-counting.
- **Dashboard:** localhost-only HTTP dashboard at `127.0.0.1:8787` by default.
- **Notifications:** optional `hermes send` target after you configure Hermes messaging.

Everything else (guessed TryBounty/Algora/Opire/Clustly write endpoints) stays disabled until its contract is independently verified.

## Why main was not safe to run

The old workers returned `success=True` and `status=completed` without doing any work. The evaluator also multiplied a per-1K-token rate by raw token count without dividing by 1,000, persisted enums came back as strings, `Attempt.metadata` disappeared after restart, `gmm-serve` pointed at a file that did not exist, and a submission was checked once immediately with no later payout reconciliation.

## VPS install

Assuming your existing checkout is `~/get-me-money`:

```bash
cd ~/get-me-money
# Back up your current branch first.
git status
git switch -c backup/pre-live-v0

# Unzip the overlay into this repository root.
unzip -o /path/to/get-me-money-live-v0.zip -d ~/get-me-money

python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

### 1. Install/initialize Taskmarket

Use the official CLI because it owns wallet keys, signatures and marketplace writes:

```bash
npm install -g @lucid-agents/taskmarket@latest
taskmarket init
taskmarket identity status
taskmarket legal status
```

Before any real marketplace write, review the current platform terms/eligibility and only proceed if the authorized operator is allowed to use the service. Do **not** automate or fake age/KYC/legal acceptance. If authorized after reviewing the current bundle:

```bash
taskmarket legal accept
```

The controller only checks the resulting receipt; it never runs `legal accept` itself.

### 2. Create an isolated Hermes worker profile

Do not point untrusted marketplace work at a Hermes profile containing GitHub, marketplace, wallet, email, or other write-capable credentials.

```bash
mkdir -p ~/.hermes-gmm
HERMES_HOME=$HOME/.hermes-gmm hermes setup --portal
HERMES_HOME=$HOME/.hermes-gmm hermes config set terminal.backend docker
HERMES_HOME=$HOME/.hermes-gmm hermes config set terminal.docker_mount_cwd_to_workspace true
HERMES_HOME=$HOME/.hermes-gmm hermes config set terminal.docker_run_as_host_user true
```

Verify Docker and Hermes:

```bash
docker version
HERMES_HOME=$HOME/.hermes-gmm hermes doctor
HERMES_HOME=$HOME/.hermes-gmm hermes dump
```

The Docker profile should show `terminal: docker`. Keep `terminal.docker_forward_env` empty for this worker unless you intentionally need a specific non-controller credential.

### 3. Configure get-me-money

```bash
cd ~/get-me-money
cp .env.example .env
chmod 600 .env
$EDITOR .env
```

Replace `YOU` in `GMM_DATA_DIR` and `GMM_HERMES_HOME`. Start with the included low-risk budget: `$1/day`, `$0.25/attempt`, `$5 lifetime`.

If you want Telegram/Discord/etc notifications, configure that target in your normal Hermes gateway/profile and set `GMM_NOTIFY_TARGET`. If you do not want notifications yet, leave it blank.

### 4. Prove the whole path before daemon mode

```bash
. .venv/bin/activate
gmm doctor
gmm scan
gmm run                  # DRY RUN — ranks work, submits nothing
gmm dashboard
```

Read the top-ranked task yourself. If it looks sane, make exactly one real attempt:

```bash
gmm run --execute
gmm dashboard
gmm reconcile
```

`gmm run` is deliberately dry by default. A missing `--execute` can never accidentally submit work.

### 5. Run continuously

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/get-me-money*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now get-me-money.service get-me-money-dashboard.service
loginctl enable-linger "$USER"   # optional: keep user services alive after logout; may require host policy to permit it
```

Observe it:

```bash
journalctl --user -u get-me-money -f
systemctl --user status get-me-money get-me-money-dashboard
curl http://127.0.0.1:8787/healthz
```

For the dashboard from your laptop, tunnel it rather than opening an unauthenticated public port:

```bash
ssh -L 8787:127.0.0.1:8787 YOUR_VPS
```

Then open `http://127.0.0.1:8787` locally.

## First-dollar operating policy

For v0, let the system **observe everything but autonomously execute only Taskmarket bounty-mode work**. The current market is competitive, so do not confuse gross reward with EV. The controller estimates `P(win) × net reward - estimated compute cost`, records the actual Hermes cost, and later replaces the prior with your own observed win rate.

A first payout is the milestone. Only after a few real outcomes should you widen daily/lifetime caps or enable additional marketplace writes.

## Superteam

Register an official agent identity with:

```bash
gmm superteam-register your-agent-name
```

Store the returned `apiKey` as `SUPERTEAM_KEY` in `.env`. Keep the `claimCode` for the platform's human payout-claim flow. Discovery will then run automatically. Auto-submit remains disabled until you deliberately set:

```bash
SUPERTEAM_AUTOSUBMIT=1
```

Do not turn that on until you have a reliable public-artifact/deployment path and have verified the required fields for the listings you want the agent to enter.

## Recovery commands

```bash
gmm reconcile          # update pending Taskmarket outcomes/payouts
gmm dashboard          # recompute ledger P&L
gmm doctor             # platform/Hermes preflight
```

If an external source pays you but does not yet expose an official result-read endpoint, reconcile the already-recorded attempt manually rather than fabricating a new attempt:

```bash
gmm mark-paid ATTEMPT_ID --amount 5.00 --fee 0 --reference 'platform receipt / tx / result id'
```

## Remaining production work after first real payout

1. Persist explicit execution stages and add crash-safe idempotency around the tiny submit/write boundary.
2. Add per-platform historical acceptance calibration rather than a category-only beta prior.
3. Add artifact-specific validators (HTML render/test, repo test command, CSV schema, citation checker).
4. Add a proper public-artifact publisher for Superteam rather than giving the worker GitHub/deployment credentials.
5. Add Clustly through its official CLI/MCP/agent package, not guessed raw endpoints.
6. Add Algora/Opire only after verifying current official discovery/submission contracts; GitHub PR tasks need a sandbox-to-PR publication boundary.
7. Move JSONL to SQLite/Postgres after the experiment has enough traffic to need concurrent writers/queries.
