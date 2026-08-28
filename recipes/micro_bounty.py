"""Micro-bounty decomposition — split big work into competitive parts.

The recursive WorkerKit loop:
  1. Big bounty comes in
  2. Agent decomposes into micro-bounties
  3. Other WorkerKit agents compete on each part
  4. Original agent assembles and submits
  5. Gets paid on the big bounty

This gives the employer:
  - Quality competition on each part
  - Parallel execution
  - Risk distribution
  - Lowest cost per quality unit
"""
from get_me_money.employer import decompose_task, format_micro_bounty_post, find_micro_bounties

def decompose_bounty(reward: float, max_parts: int = 10) -> dict:
    """Analyze a bounty and determine if decomposition is worth it."""
    cost_per_part = reward / max_parts
    overhead = reward * 0.3  # assembly cost
    net = reward - overhead

    return {
        "reward": reward,
        "parts": max_parts,
        "cost_per_part": round(cost_per_part, 2),
        "overhead": round(overhead, 2),
        "net_after_assembly": round(net, 2),
        "recommendation": "decompose" if net > reward * 0.5 else "do directly",
    }

def estimate_competition(micro_tasks: list) -> dict:
    """Estimate competition for micro-bounties."""
    total = len(micro_tasks)
    independent = sum(1 for mt in micro_tasks if not mt.depends_on)
    return {
        "total_parts": total,
        "independent": independent,
        "parallelizable": independent == total,
        "estimated_agents_needed": independent if independent > 1 else total,
    }
