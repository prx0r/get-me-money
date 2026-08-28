"""Rank next jobs for an agent based on capabilities + EV."""
from get_me_money.oracle_client import OracleClient

def route_opportunities(skills: list[str], min_reward: float = 5, max_competition: int = 50) -> list[dict]:
    oracle = OracleClient()
    opps = oracle.search(skills=skills, min_reward=min_reward)

    results = []
    for o in opps:
        if o.competition > max_competition:
            continue
        ev = o.reward_usd * 0.5 / max(1, o.competition * 0.1)
        results.append({
            "id": o.id,
            "title": o.title[:60],
            "source": o.source,
            "reward": o.reward_usd,
            "competition": o.competition,
            "ev": round(ev, 2),
            "skills": o.skills,
        })

    return sorted(results, key=lambda x: x["ev"], reverse=True)[:10]
