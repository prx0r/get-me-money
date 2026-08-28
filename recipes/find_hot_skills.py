"""Find skills with rising demand + low supply."""
from get_me_money.oracle_client import OracleClient

def find_hot_skills(min_reward: float = 10, window: str = "30d") -> list[dict]:
    oracle = OracleClient()
    trending = oracle.trending_skills(window=window)
    opps = oracle.search(min_reward=min_reward)

    skill_demand = {}
    for o in opps:
        for s in o.skills:
            skill_demand[s] = skill_demand.get(s, 0) + 1

    results = []
    for skill_info in trending:
        skill = skill_info.get("skill", "")
        demand = skill_demand.get(skill, 0)
        reward = skill_info.get("total_reward", 0)
        if demand > 0:
            results.append({
                "skill": skill,
                "demand": demand,
                "total_reward": reward,
                "supply_ratio": demand / max(1, reward),
            })

    return sorted(results, key=lambda x: x["total_reward"], reverse=True)
