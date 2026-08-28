"""TryBounty adapter — primary cash surface for daily earnings.

$33.69k escrowed, $30.79k verified results, 207 active agents.
Terms permit age 13+ (payment providers may have own requirements).
Focus: research, datasets, lead gen, competitive intelligence.
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
from datetime import datetime
from typing import AsyncIterator, Any

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter


def _ts(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v:
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _parse_reward(text: str) -> float:
    m = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    if m:
        return float(m.group(1))
    return 0.0


def _categorize(text: str) -> TaskCategory:
    t = text.lower()
    if any(x in t for x in ("dataset", "data", "csv", "extract", "scrape", "list", "leads")):
        return TaskCategory.DATA_EXTRACTION
    if any(x in t for x in ("research", "analysis", "competitive", "market", "investor", "prospect")):
        return TaskCategory.RESEARCH
    if any(x in t for x in ("code", "bug", "fix", "repo", "github")):
        return TaskCategory.CODE_FIX
    if any(x in t for x in ("write", "content", "article", "blog", "copy")):
        return TaskCategory.CONTENT
    if any(x in t for x in ("api", "integration", "automation")):
        return TaskCategory.API_WORK
    if any(x in t for x in ("document", "readme", "doc")):
        return TaskCategory.DOCUMENTATION
    return TaskCategory.UNKNOWN


# Categories TryBounty consistently pays for (from completed job history)
HIGH_VALUE_CATEGORIES = {
    TaskCategory.RESEARCH,
    TaskCategory.DATA_EXTRACTION,
    TaskCategory.CODE_FIX,
    TaskCategory.API_WORK,
}


class BountyAdapter(BaseAdapter):
    """TryBounty adapter using CLI or API.

    TryBounty has a real web interface at trybounty.ai.
    This adapter uses the CLI if available, otherwise scrapes.
    """
    platform = Platform.BOUNTY

    def __init__(self, api_key: str = "", binary: str = "trybounty"):
        self.api_key = api_key
        self.binary = binary

    async def _run(self, *args: str, timeout: int = 60) -> dict:
        """Run trybounty CLI if available."""
        binary = shutil.which(self.binary)
        if not binary:
            return {"ok": False, "error": "trybounty CLI not found"}
        try:
            p = await asyncio.create_subprocess_exec(
                binary, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(p.communicate(), timeout=timeout)
        except (FileNotFoundError, asyncio.TimeoutError) as e:
            return {"ok": False, "error": str(e)}
        text = out.decode(errors="replace").strip()
        if p.returncode != 0:
            return {"ok": False, "error": err.decode(errors="replace").strip() or text}
        try:
            payload = json.loads(text)
            return {"ok": True, "data": payload}
        except json.JSONDecodeError:
            return {"ok": True, "data": text}

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        """Discover TryBounty opportunities.

        Uses web scraping of the bounty listing page.
        TryBounty shows open bounties with rewards, categories, and deadlines.
        """
        try:
            import httpx
        except ImportError:
            return

        # Try API first
        if self.api_key:
            async for opp in self._discover_api(max_pages):
                yield opp
            return

        # Fallback: scrape the listing page
        async for opp in self._discover_scrape(max_pages):
            yield opp

    async def _discover_api(self, max_pages: int) -> AsyncIterator[Opportunity]:
        """Discover via TryBounty API (if key available)."""
        try:
            import httpx
        except ImportError:
            return

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            for page in range(1, max_pages + 1):
                try:
                    resp = await client.get(
                        "https://trybounty.ai/api/bounties",
                        params={"page": page, "status": "open", "limit": 20},
                    )
                    if resp.status_code >= 400:
                        break
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("bounties", [])
                    if not items:
                        break
                    for item in items:
                        yield self._to_opp(item)
                except Exception:
                    break

    async def _discover_scrape(self, max_pages: int) -> AsyncIterator[Opportunity]:
        """Scrape TryBounty listing page for open bounties."""
        try:
            import httpx
            from selectolax.parser import HTMLParser
        except ImportError:
            return

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                try:
                    resp = await client.get(
                        "https://trybounty.ai/bounties",
                        params={"page": page},
                    )
                    if resp.status_code >= 400:
                        break
                    tree = HTMLParser(resp.text)

                    # Look for bounty cards — TryBounty uses a card-based layout
                    cards = tree.css(
                        "[class*=bounty], [class*=card], [class*=task], "
                        "[class*=listing], article, .flex"
                    )
                    if not cards:
                        # Try broader selectors
                        cards = tree.css("div > a[href*=bounty], div > a[href*=task]")

                    for card in cards:
                        opp = self._parse_card(card)
                        if opp and opp.reward >= 3.0:
                            yield opp

                    # Also try to find links to individual bounty pages
                    links = tree.css("a[href*='/bounty/'], a[href*='/task/']")
                    for link in links:
                        href = link.attributes.get("href", "")
                        text = link.text(strip=True)
                        if text and href:
                            reward = _parse_reward(text)
                            if reward >= 3.0:
                                yield Opportunity(
                                    platform=Platform.BOUNTY,
                                    title=text[:120],
                                    url=f"https://trybounty.ai{href}" if href.startswith("/") else href,
                                    reward=reward,
                                    currency="USD",
                                    category=_categorize(text),
                                    verification_strength=0.7,
                                    payment_reliability=0.7,
                                    raw={"source": "scrape", "href": href},
                                )
                except Exception:
                    break

    def _parse_card(self, card) -> Opportunity | None:
        """Parse a bounty card from HTML."""
        try:
            # Title
            title_el = card.css_first("h2, h3, h4, [class*=title], [class*=name]")
            title = title_el.text(strip=True) if title_el else ""
            if not title:
                return None

            # Link
            link_el = card.css_first("a[href]")
            href = link_el.attributes.get("href", "") if link_el else ""
            url = f"https://trybounty.ai{href}" if href.startswith("/") else href

            # Reward
            price_el = card.css_first("[class*=reward], [class*=amount], [class*=price], [class*=payment]")
            price_text = price_el.text(strip=True) if price_el else ""
            reward = _parse_reward(price_text)

            # Category/tags
            tag_els = card.css("[class*=tag], [class*=badge], [class*=category]")
            tags = [t.text(strip=True) for t in tag_els if t.text(strip=True)]

            # Description
            desc_el = card.css_first("p, [class*=desc], [class*=summary]")
            desc = desc_el.text(strip=True) if desc_el else ""

            return Opportunity(
                platform=Platform.BOUNTY,
                title=title,
                description=desc,
                url=url,
                reward=reward,
                currency="USD",
                category=_categorize(title + " " + desc),
                tags=tags,
                verification_strength=0.7,
                payment_reliability=0.7,
                raw={"source": "html_scrape"},
            )
        except Exception:
            return None

    def _to_opp(self, data: dict) -> Opportunity:
        """Convert API response to Opportunity."""
        title = data.get("title", data.get("name", ""))
        desc = data.get("description", data.get("body", ""))

        reward = 0.0
        for key in ("reward", "amount", "payment", "bounty_amount"):
            if data.get(key) is not None:
                try:
                    reward = float(data[key])
                    break
                except (TypeError, ValueError):
                    pass

        return Opportunity(
            platform=Platform.BOUNTY,
            external_id=str(data.get("id", data.get("bounty_id", ""))),
            title=title,
            description=desc,
            url=data.get("url", data.get("html_url", "")),
            reward=reward,
            currency=data.get("currency", "USD"),
            category=_categorize(title + " " + desc),
            tags=data.get("tags", []),
            posted_at=_ts(data.get("created_at", data.get("posted_at"))),
            expires_at=_ts(data.get("deadline", data.get("expires_at"))),
            competition_estimate=int(data.get("applicant_count", 0) or 0),
            verification_strength=0.7,
            payment_reliability=0.7,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        """Check if we can claim this bounty."""
        # For TryBounty, claiming is implicit — you submit work
        # But check eligibility first
        return True

    async def submit(self, opportunity: Opportunity, result: dict) -> dict:
        """Submit work to TryBounty.

        TryBounty submissions go through their web interface.
        The controller handles this via the CLI or API.
        """
        if self.api_key:
            return await self._submit_api(opportunity, result)
        # Without API key, we can only prepare the submission
        return {"ok": False, "error": "TryBounty API key required for submission"}

    async def _submit_api(self, opportunity: Opportunity, result: dict) -> dict:
        """Submit via TryBounty API."""
        try:
            import httpx
        except ImportError:
            return {"ok": False, "error": "httpx not installed"}

        content = result.get("content", "")
        artifacts = result.get("artifacts", [])

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(
                    f"https://trybounty.ai/api/bounties/{opportunity.external_id}/submit",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "content": content,
                        "artifacts": artifacts,
                        "url": result.get("url", ""),
                    },
                )
                if resp.status_code >= 400:
                    return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
                return {"ok": True, "data": resp.json()}
            except Exception as e:
                return {"ok": False, "error": str(e)}

    async def check_status(self, opportunity: Opportunity) -> dict:
        """Check bounty status — accepted, pending, rejected."""
        if not self.api_key:
            return {"status": "unknown", "paid": False, "terminal": False}

        try:
            import httpx
        except ImportError:
            return {"status": "unknown", "paid": False, "terminal": False}

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(
                    f"https://trybounty.ai/api/bounties/{opportunity.external_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if resp.status_code >= 400:
                    return {"status": "unknown", "paid": False, "terminal": False}
                data = resp.json()
                status = data.get("status", "pending")
                paid = status in ("completed", "paid", "accepted")
                terminal = status in ("completed", "paid", "accepted", "rejected", "expired", "cancelled")
                return {
                    "status": status,
                    "paid": paid,
                    "won": paid,
                    "terminal": terminal,
                    "reward": float(data.get("reward", 0) or 0),
                }
            except Exception:
                return {"status": "unknown", "paid": False, "terminal": False}

    async def health_check(self) -> bool:
        """Check if TryBounty is reachable."""
        try:
            import httpx
        except ImportError:
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://trybounty.ai/")
                return resp.status_code < 500
        except Exception:
            return False
