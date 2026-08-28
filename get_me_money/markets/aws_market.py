"""AWS Marketplace — SaaS, containers, ML models, data, agents."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class AWSMarketAdapter(MarketAdapter):
    name = "aws_market"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=False, analytics=True,
        requires_auth=True,
    )
    def __init__(self, role_arn: str = ""):
        self.role_arn = role_arn
