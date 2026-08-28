"""Which marketplace actually pays?"""
from get_me_money.oracle_client import OracleClient

def check_liquidity() -> list[dict]:
    oracle = OracleClient()
    stats = oracle.stats()
    return [{"metric": k, "value": v} for k, v in stats.items()]
