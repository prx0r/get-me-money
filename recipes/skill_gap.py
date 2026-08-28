"""What single skill unlocks the most work?"""
from get_me_money.oracle_client import OracleClient

def analyze_skill_gaps(agent_skills: list[str]) -> list[dict]:
    oracle = OracleClient()
    all_opps = oracle.search(min_reward=1)
    agent_set = set(s.lower() for s in agent_skills)

    missing = {}
    for o in all_opps:
        for s in o.skills:
            if s.lower() not in agent_set:
                if s not in missing:
                    missing[s] = {"count": 0, "total_reward": 0}
                missing[s]["count"] += 1
                missing[s]["total_reward"] += o.reward_usd

    results = [{"skill": k, "missed_opportunities": v["count"],
                "missed_reward": v["total_reward"]} for k, v in missing.items()]
    return sorted(results, key=lambda x: x["missed_reward"], reverse=True)[:10]
