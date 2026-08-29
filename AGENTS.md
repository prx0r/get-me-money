# AGENTS.md — What to do

**You are an agent. Here is exactly what to do.**

## Step 1: Install

```bash
pip install -e .
echo "OPENCODE_GO_API_KEY=sk-your-key" > data/.env
```

## Step 2: Find work

```python
from get_me_money.oracle_feeds import OracleFeeds
feeds = OracleFeeds()
work = feeds.work(min_reward=1, limit=10)
```

This returns bounties with real rewards. Pick one you can do.

## Step 3: Find tools

```python
tools = feeds.resolve_capabilities(job.skills)
```

This finds Apify actors, x402 services, MCPs that help with the job.

## Step 4: Find transformation

```python
from get_me_money.transformations import find_transformation
recipe = find_transformation(job.category, [t.name for t in tools])
```

This tells you the production process: search → verify → analyze → write.

## Step 5: Do the work

Follow the transformation steps. Use the tools. Produce the deliverable.

## Step 6: Submit

```python
from get_me_money.loop import run_submission_loop
result = await run_submission_loop(config, job, ev, adapter, work_dir)
```

## Step 7: Get paid

Wait for outcome. Record everything. Improve next time.

## What NOT to do

- Don't create accounts without checking human_gates
- Don't spend more than the reward
- Don't submit without verifying quality
- Don't lie about what you produced

## Files to read

- `README.md` — architecture overview
- `get_me_money/oracle_feeds.py` — query the oracle
- `get_me_money/transformations.py` — find production processes
- `get_me_money/loop.py` — execute and submit
