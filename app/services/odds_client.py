import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.exceptions import (
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from app.services.metrics import metrics_service
from app.schemas import (
    AsianHandicapBookmaker,
    AsianHandicapLine,
    AsianHandicapOutput,
    BookmakerOdds,
    BTTSBookmaker,
    BTTSOdds,
    BTTSOutput,
    CorrectScoreBookmaker,
    CorrectScoreOdds,
    CorrectScoreOutput,
    DoubleChanceBookmaker,
    DoubleChanceOdds,
    DoubleChanceOutput,
    EventData,
    EventResponse,
    EventStatus,
    LeagueInfo,
    LiveEventResponse,
    OddsMetadata,
    OddsOutput,
    OddsValues,
    ScoreInfo,
    SportInfo,
    TotalsBookmaker,
    TotalsLine,
    TotalsOutput,
)
from app.schemas.arbitrage import (
    ArbitrageBet,
    ArbitrageEvent,
    ArbitrageLeg,
    ArbitrageResponse,
    OptimalStake,
)
from app.schemas.odds_movements import OddsMovementsResponse, OddsSnapshot
from app.schemas.value_bets import (
    ConsensusOdds,
    ValueBet,
    ValueBetEvent,
    ValueBetOdds,
    ValueBetsResponse,
)
from app.services.cache import cache_service

logger = logging.getLogger(__name__)


class OddsAPIClient:
    """HTTP client for Odds-API.io with caching."""

    def __init__(self):
        self.base_url = settings.odds_api_base_url
        self.api_key = settings.odds_api_key

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Make an HTTP request with optional caching."""
        # Check cache first
        if cache_key:
            cached = await cache_service.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached

        # Build request
        url = f"{self.base_url}{endpoint}"
        request_params = {"apiKey": self.api_key}
        if params:
            request_params.update(params)

        try:
            # Track external API call
            await metrics_service.track_api_call()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                data = response.json()

                # Cache if key provided
                if cache_key and cache_ttl:
                    await cache_service.set(cache_key, data, cache_ttl)

                return data
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                f"Request to {endpoint} timed out",
                timeout_seconds=30.0,
                endpoint=endpoint,
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = e.response.text[:500]

            if status == 429:
                raise RateLimitError(
                    "Odds-API.io rate limit exceeded",
                    retry_after=int(e.response.headers.get("Retry-After", 60)),
                )

            raise ProviderError(
                f"HTTP {status} from Odds-API.io",
                status_code=status,
                response_body=body,
                endpoint=endpoint,
            )
        except httpx.RequestError as e:
            raise ProviderError(
                f"Network error: {e}",
                endpoint=endpoint,
            )

    async def get_sports(self) -> list[dict[str, Any]]:
        """GET /sports - List available sports."""
        data = await self._request(
            "/sports",
            cache_key="sports:all",
            cache_ttl=settings.cache_ttl_sports,
        )
        return data if isinstance(data, list) else []

    async def get_bookmakers(self) -> list[dict[str, Any]]:
        """GET /bookmakers - List available bookmakers."""
        data = await self._request(
            "/bookmakers",
            cache_key="bookmakers:all",
            cache_ttl=settings.cache_ttl_sports,
        )
        return data if isinstance(data, list) else []

    async def get_event(self, event_id: str) -> EventResponse | None:
        """GET /events/{id} - Get a single event by ID."""
        cache_key = f"event:{event_id}"
        data = await self._request(
            f"/events/{event_id}",
            cache_key=cache_key,
            cache_ttl=settings.cache_ttl_events,
        )

        if not data or not isinstance(data, dict):
            return None

        try:
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            item_status = data.get("status", "not_started")
            if item_status == "live":
                event_status = EventStatus.IN_PROGRESS
            elif item_status in ["ended", "settled", "completed"]:
                event_status = EventStatus.ENDED
            else:
                event_status = EventStatus.NOT_STARTED

            return EventResponse(
                id=str(data.get("id", "")),
                home=data.get("home", data.get("home_team", "")),
                away=data.get("away", data.get("away_team", "")),
                date=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
                status=event_status,
                sport=SportInfo(
                    name=sport_data.get("name", "Football") if isinstance(sport_data, dict) else "Football",
                    slug=sport_data.get("slug", "football") if isinstance(sport_data, dict) else "football",
                ),
                league=LeagueInfo(
                    name=league_data.get("name", "") if isinstance(league_data, dict) else (data.get("league") or ""),
                    slug=league_data.get("slug", "") if isinstance(league_data, dict) else "",
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to parse event {event_id}: {e}")
            return None

    async def get_events(
        self,
        sport: str | None = None,
        league: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[EventResponse], int]:
        """GET /events - Get events with filters.

        Returns: (events, total_count)
        """
        params: dict[str, Any] = {}
        if sport:
            params["sport"] = sport
        if league:
            params["league"] = league
        if status:
            params["status"] = status
        # API expects RFC3339 format (e.g. 2025-10-28T10:00:00Z)
        if date_from:
            # Add time if only date provided
            if "T" not in date_from:
                date_from = f"{date_from}T00:00:00Z"
            params["from"] = date_from
        if date_to:
            if "T" not in date_to:
                date_to = f"{date_to}T23:59:59Z"
            params["to"] = date_to

        cache_key = f"events:{':'.join(f'{k}={v}' for k, v in sorted(params.items()) if v)}"
        data = await self._request(
            "/events",
            params=params,
            cache_key=cache_key,
            cache_ttl=settings.cache_ttl_events,
        )

        if not data or not isinstance(data, list):
            return [], 0

        events = []
        for item in data:
            try:
                # Handle nested sport/league objects
                sport_data = item.get("sport", {})
                league_data = item.get("league", {})

                # Get date field (API uses "date" not "commence_time")
                date_str = item.get("date", item.get("commence_time", ""))

                # Determine status
                item_status = item.get("status", "not_started")
                if item_status == "live":
                    event_status = EventStatus.IN_PROGRESS
                elif item_status in ["ended", "settled", "completed"]:
                    event_status = EventStatus.ENDED
                else:
                    event_status = EventStatus.NOT_STARTED

                events.append(
                    EventResponse(
                        id=str(item.get("id", "")),
                        home=item.get("home", item.get("home_team", "")),
                        away=item.get("away", item.get("away_team", "")),
                        date=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
                        status=event_status,
                        sport=SportInfo(
                            name=sport_data.get("name", "Football") if isinstance(sport_data, dict) else "Football",
                            slug=sport_data.get("slug", sport or "football") if isinstance(sport_data, dict) else (sport or "football"),
                        ),
                        league=LeagueInfo(
                            name=league_data.get("name", "") if isinstance(league_data, dict) else (item.get("league") or ""),
                            slug=league_data.get("slug", "") if isinstance(league_data, dict) else "",
                        ),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
                continue
        return events, len(events)

    async def get_live_events(
        self,
        sport: str | None = None,
    ) -> list[LiveEventResponse]:
        """GET /events/live - Get live events with scores."""
        # Fetch ALL live events (odds-api.io doesn't support sport filter param)
        # Filter locally after parsing if sport is specified
        cache_key = "events:live:all"
        data = await self._request(
            "/events/live",
            params={},
            cache_key=cache_key,
            cache_ttl=30,  # 30s cache for live data
        )

        if not data or not isinstance(data, list):
            return []

        events = []
        for item in data:
            try:
                sport_data = item.get("sport", {})
                league_data = item.get("league", {})
                date_str = item.get("date", "")
                scores = item.get("scores")

                events.append(
                    LiveEventResponse(
                        id=str(item.get("id", "")),
                        home=item.get("home", ""),
                        away=item.get("away", ""),
                        date=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
                        status=EventStatus.IN_PROGRESS,
                        scores=ScoreInfo(home=scores.get("home", 0), away=scores.get("away", 0)) if scores else None,
                        sport=SportInfo(
                            name=sport_data.get("name", "Football") if isinstance(sport_data, dict) else "Football",
                            slug=sport_data.get("slug", sport or "football") if isinstance(sport_data, dict) else (sport or "football"),
                        ),
                        league=LeagueInfo(
                            name=league_data.get("name", "") if isinstance(league_data, dict) else "",
                            slug=league_data.get("slug", "") if isinstance(league_data, dict) else "",
                        ),
                        minute=item.get("minute"),
                        period=item.get("period"),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse live event: {e}")
                continue

        # Filter by sport locally if requested
        if sport:
            events = [e for e in events if e.sport.slug == sport]

        return events

    async def get_leagues(
        self,
        sport: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /leagues - Get available leagues."""
        params: dict[str, Any] = {}
        if sport:
            params["sport"] = sport

        cache_key = f"leagues:{sport or 'all'}"
        data = await self._request(
            "/leagues",
            params=params,
            cache_key=cache_key,
            cache_ttl=settings.cache_ttl_sports,  # 24h cache
        )

        if not data or not isinstance(data, list):
            return []
        return data

    async def get_odds(
        self,
        event_id: str,
        bookmakers: list[str],
        market: str = "1x2",
    ) -> OddsOutput | AsianHandicapOutput | TotalsOutput | BTTSOutput | CorrectScoreOutput | DoubleChanceOutput | None:
        """GET /odds - Get odds for a specific event."""
        # Map internal market names to API market names
        market_mapping = {
            "1x2": "ML",
            "asian_handicap": "Asian Handicap",
            "totals": "Totals",
            "btts": "Both Teams to Score",
            "correct_score": "Correct Score",
            "double_chance": "Double Chance",
        }
        api_market = market_mapping.get(market, market)

        params = {
            "eventId": event_id,
            "bookmakers": ",".join(bookmakers),
            "markets": api_market,
        }

        # Don't cache odds (they change frequently)
        data = await self._request("/odds", params=params)

        if not data:
            return None

        # Route to appropriate transformer based on market
        transformers = {
            "asian_handicap": self._transform_asian_handicap,
            "totals": self._transform_totals,
            "btts": self._transform_btts,
            "correct_score": self._transform_correct_score,
            "double_chance": self._transform_double_chance,
        }
        transformer = transformers.get(market)
        if transformer:
            return transformer(data)
        return self._transform_odds(data, market)

    def _transform_odds(self, data: dict[str, Any], market: str) -> OddsOutput | None:
        """Transform API response to OddsOutput format.

        API format:
        {
            "id": "...",
            "home": "Team A",
            "away": "Team B",
            "date": "2026-01-15T20:00:00Z",
            "sport": {"slug": "football", ...},
            "league": {"name": "Liga", ...},
            "bookmakers": {
                "Bet365": [{"name": "ML", "odds": [{"home": "1.5", "draw": "3.0", "away": "4.0"}], "updatedAt": "..."}],
                "Betano": [...]
            }
        }
        """
        try:
            # Extract event info - handle nested sport/league
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            event = EventData(
                id=str(data.get("id", "")),
                sport=sport_data.get("slug", "football") if isinstance(sport_data, dict) else str(sport_data),
                league=league_data.get("name") if isinstance(league_data, dict) else data.get("league"),
                league_id=league_data.get("id") if isinstance(league_data, dict) else data.get("leagueId"),
                home_team=data.get("home", data.get("home_team", "")),
                away_team=data.get("away", data.get("away_team", "")),
                commence_time=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
            )

            # Extract bookmaker odds - API returns dict, not list
            bookmakers_data = data.get("bookmakers", {})
            bookmaker_odds = []

            # Handle dict format: {"Bet365": [...], "Betano": [...]}
            if isinstance(bookmakers_data, dict):
                for bm_name, markets in bookmakers_data.items():
                    if not isinstance(markets, list):
                        continue

                    # Find ML (Match Line / 1x2) market
                    ml_market = next(
                        (m for m in markets if m.get("name") in ["ML", "1x2", "h2h"]),
                        None,
                    )

                    if not ml_market:
                        continue

                    odds_list = ml_market.get("odds", [])
                    if not odds_list:
                        continue

                    # Get first odds entry (most recent)
                    odds_entry = odds_list[0] if odds_list else {}

                    # Parse odds values (API returns strings)
                    try:
                        home_odds = float(odds_entry.get("home", 0))
                        draw_odds = float(odds_entry.get("draw", 0))
                        away_odds = float(odds_entry.get("away", 0))
                    except (ValueError, TypeError):
                        continue

                    if home_odds and draw_odds and away_odds:
                        updated_str = ml_market.get("updatedAt", "")
                        bookmaker_odds.append(
                            BookmakerOdds(
                                key=bm_name.lower().replace(" ", "_"),
                                name=bm_name,
                                odds=OddsValues(home=home_odds, draw=draw_odds, away=away_odds),
                                updated_at=datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(),
                            )
                        )

            # Handle list format (fallback for different API versions)
            elif isinstance(bookmakers_data, list):
                for bm in bookmakers_data:
                    markets = bm.get("markets", [])
                    h2h_market = next(
                        (m for m in markets if m.get("key") in ["h2h", "1x2", "ML"]),
                        None,
                    )
                    if not h2h_market:
                        continue

                    outcomes = h2h_market.get("outcomes", [])
                    if len(outcomes) < 3:
                        continue

                    odds_map = {
                        "home": float(outcomes[0].get("price", 0)),
                        "draw": float(outcomes[1].get("price", 0)),
                        "away": float(outcomes[2].get("price", 0)),
                    }

                    if all(v > 0 for v in odds_map.values()):
                        bookmaker_odds.append(
                            BookmakerOdds(
                                key=bm.get("key", ""),
                                name=bm.get("title", bm.get("key", "")),
                                odds=OddsValues(**odds_map),
                                updated_at=datetime.fromisoformat(
                                    h2h_market.get("last_update", "").replace("Z", "+00:00")
                                ) if h2h_market.get("last_update") else datetime.now(),
                            )
                        )

            if not bookmaker_odds:
                return None

            return OddsOutput(
                event=event,
                market=market,
                bookmakers=bookmaker_odds,
                metadata=OddsMetadata(
                    generated_at=datetime.now(),
                    is_ended=data.get("completed", False),
                    hash="",  # Will be computed by service
                ),
            )
        except Exception as e:
            logger.error(f"Failed to transform odds: {e}")
            return None

    def _transform_asian_handicap(self, data: dict[str, Any]) -> AsianHandicapOutput | None:
        """Transform API response to AsianHandicapOutput format.

        API format for Asian Handicap:
        {
            "bookmakers": {
                "Bet365": [{
                    "name": "Asian Handicap",
                    "updatedAt": "2026-01-13T20:45:00Z",
                    "odds": [
                        {"hdp": -0.5, "home": "1.85", "away": "2.05"},
                        {"hdp": -1.0, "home": "2.10", "away": "1.80"},
                        {"hdp": -1.5, "home": "2.45", "away": "1.58"}
                    ]
                }]
            }
        }
        """
        try:
            # Extract event info
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            event = EventData(
                id=str(data.get("id", "")),
                sport=sport_data.get("slug", "football") if isinstance(sport_data, dict) else str(sport_data),
                league=league_data.get("name") if isinstance(league_data, dict) else data.get("league"),
                league_id=league_data.get("id") if isinstance(league_data, dict) else data.get("leagueId"),
                home_team=data.get("home", data.get("home_team", "")),
                away_team=data.get("away", data.get("away_team", "")),
                commence_time=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
            )

            # Extract Asian Handicap odds
            bookmakers_data = data.get("bookmakers", {})
            bookmaker_odds = []

            if isinstance(bookmakers_data, dict):
                for bm_name, markets in bookmakers_data.items():
                    if not isinstance(markets, list):
                        continue

                    # Find Asian Handicap market
                    ah_market = next(
                        (m for m in markets if m.get("name") in ["Asian Handicap", "AH", "asian_handicap"]),
                        None,
                    )

                    if not ah_market:
                        continue

                    odds_list = ah_market.get("odds", [])
                    if not odds_list:
                        continue

                    # Parse all handicap lines
                    lines = []
                    for odds_entry in odds_list:
                        try:
                            hdp = float(odds_entry.get("hdp", 0))
                            home_odds = float(odds_entry.get("home", 0))
                            away_odds = float(odds_entry.get("away", 0))

                            if home_odds > 0 and away_odds > 0:
                                lines.append(
                                    AsianHandicapLine(
                                        hdp=hdp,
                                        home=home_odds,
                                        away=away_odds,
                                    )
                                )
                        except (ValueError, TypeError):
                            continue

                    if lines:
                        # Sort lines by handicap value
                        lines.sort(key=lambda x: x.hdp)

                        updated_str = ah_market.get("updatedAt", "")
                        bookmaker_odds.append(
                            AsianHandicapBookmaker(
                                key=bm_name.lower().replace(" ", "_"),
                                name=bm_name,
                                lines=lines,
                                updated_at=datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(),
                            )
                        )

            if not bookmaker_odds:
                return None

            return AsianHandicapOutput(
                event=event,
                market="asian_handicap",
                bookmakers=bookmaker_odds,
                metadata=OddsMetadata(
                    generated_at=datetime.now(),
                    is_ended=data.get("completed", False),
                    hash="",  # Will be computed by service
                ),
            )
        except Exception as e:
            logger.error(f"Failed to transform asian handicap odds: {e}")
            return None

    def _transform_totals(self, data: dict[str, Any]) -> TotalsOutput | None:
        """Transform API response to TotalsOutput format.

        API format for Totals:
        {
            "bookmakers": {
                "Bet365": [{
                    "name": "Totals",
                    "updatedAt": "2026-01-13T20:45:00Z",
                    "odds": [
                        {"line": 2.5, "over": "1.90", "under": "1.95"},
                        {"line": 3.5, "over": "2.50", "under": "1.55"}
                    ]
                }]
            }
        }
        """
        try:
            # Extract event info
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            event = EventData(
                id=str(data.get("id", "")),
                sport=sport_data.get("slug", "football") if isinstance(sport_data, dict) else str(sport_data),
                league=league_data.get("name") if isinstance(league_data, dict) else data.get("league"),
                league_id=league_data.get("id") if isinstance(league_data, dict) else data.get("leagueId"),
                home_team=data.get("home", data.get("home_team", "")),
                away_team=data.get("away", data.get("away_team", "")),
                commence_time=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
            )

            # Extract Totals odds
            bookmakers_data = data.get("bookmakers", {})
            bookmaker_odds = []

            if isinstance(bookmakers_data, dict):
                for bm_name, markets in bookmakers_data.items():
                    if not isinstance(markets, list):
                        continue

                    # Find Totals market
                    totals_market = next(
                        (m for m in markets if m.get("name") in ["Totals", "Over/Under", "totals"]),
                        None,
                    )

                    if not totals_market:
                        continue

                    odds_list = totals_market.get("odds", [])
                    if not odds_list:
                        continue

                    # Parse all totals lines
                    lines = []
                    for odds_entry in odds_list:
                        try:
                            line = float(odds_entry.get("line", odds_entry.get("hdp", 0)))
                            over_odds = float(odds_entry.get("over", 0))
                            under_odds = float(odds_entry.get("under", 0))

                            if over_odds > 0 and under_odds > 0:
                                lines.append(
                                    TotalsLine(
                                        line=line,
                                        over=over_odds,
                                        under=under_odds,
                                    )
                                )
                        except (ValueError, TypeError):
                            continue

                    if lines:
                        # Sort lines by line value
                        lines.sort(key=lambda x: x.line)

                        updated_str = totals_market.get("updatedAt", "")
                        bookmaker_odds.append(
                            TotalsBookmaker(
                                key=bm_name.lower().replace(" ", "_"),
                                name=bm_name,
                                lines=lines,
                                updated_at=datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(),
                            )
                        )

            if not bookmaker_odds:
                return None

            return TotalsOutput(
                event=event,
                market="totals",
                bookmakers=bookmaker_odds,
                metadata=OddsMetadata(
                    generated_at=datetime.now(),
                    is_ended=data.get("completed", False),
                    hash="",  # Will be computed by service
                ),
            )
        except Exception as e:
            logger.error(f"Failed to transform totals odds: {e}")
            return None

    def _transform_btts(self, data: dict[str, Any]) -> BTTSOutput | None:
        """Transform API response to BTTSOutput format."""
        try:
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            event = EventData(
                id=str(data.get("id", "")),
                sport=sport_data.get("slug", "football") if isinstance(sport_data, dict) else str(sport_data),
                league=league_data.get("name") if isinstance(league_data, dict) else data.get("league"),
                league_id=league_data.get("id") if isinstance(league_data, dict) else data.get("leagueId"),
                home_team=data.get("home", data.get("home_team", "")),
                away_team=data.get("away", data.get("away_team", "")),
                commence_time=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
            )

            bookmakers_data = data.get("bookmakers", {})
            bookmaker_odds = []

            if isinstance(bookmakers_data, dict):
                for bm_name, markets in bookmakers_data.items():
                    if not isinstance(markets, list):
                        continue

                    btts_market = next(
                        (m for m in markets if m.get("name") in ["Both Teams to Score", "BTTS", "btts"]),
                        None,
                    )

                    if not btts_market:
                        continue

                    odds_data = btts_market.get("odds", {})
                    if isinstance(odds_data, list) and odds_data:
                        odds_data = odds_data[0]

                    if not odds_data:
                        continue

                    try:
                        yes_odds = float(odds_data.get("yes", 0))
                        no_odds = float(odds_data.get("no", 0))

                        if yes_odds > 0 and no_odds > 0:
                            updated_str = btts_market.get("updatedAt", "")
                            bookmaker_odds.append(
                                BTTSBookmaker(
                                    key=bm_name.lower().replace(" ", "_"),
                                    name=bm_name,
                                    odds=BTTSOdds(yes=yes_odds, no=no_odds),
                                    updated_at=datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(),
                                )
                            )
                    except (ValueError, TypeError):
                        continue

            if not bookmaker_odds:
                return None

            return BTTSOutput(
                event=event,
                market="btts",
                bookmakers=bookmaker_odds,
                metadata=OddsMetadata(
                    generated_at=datetime.now(),
                    is_ended=data.get("completed", False),
                    hash="",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to transform BTTS odds: {e}")
            return None

    def _transform_correct_score(self, data: dict[str, Any]) -> CorrectScoreOutput | None:
        """Transform API response to CorrectScoreOutput format."""
        try:
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            event = EventData(
                id=str(data.get("id", "")),
                sport=sport_data.get("slug", "football") if isinstance(sport_data, dict) else str(sport_data),
                league=league_data.get("name") if isinstance(league_data, dict) else data.get("league"),
                league_id=league_data.get("id") if isinstance(league_data, dict) else data.get("leagueId"),
                home_team=data.get("home", data.get("home_team", "")),
                away_team=data.get("away", data.get("away_team", "")),
                commence_time=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
            )

            bookmakers_data = data.get("bookmakers", {})
            bookmaker_odds = []

            if isinstance(bookmakers_data, dict):
                for bm_name, markets in bookmakers_data.items():
                    if not isinstance(markets, list):
                        continue

                    cs_market = next(
                        (m for m in markets if m.get("name") in ["Correct Score", "correct_score"]),
                        None,
                    )

                    if not cs_market:
                        continue

                    odds_list = cs_market.get("odds", [])
                    if not isinstance(odds_list, list):
                        continue

                    scores = []
                    for score_entry in odds_list:
                        try:
                            score = score_entry.get("score", "")
                            odds_val = float(score_entry.get("odds", 0))
                            if score and odds_val > 0:
                                scores.append(CorrectScoreOdds(score=score, odds=odds_val))
                        except (ValueError, TypeError):
                            continue

                    if scores:
                        updated_str = cs_market.get("updatedAt", "")
                        bookmaker_odds.append(
                            CorrectScoreBookmaker(
                                key=bm_name.lower().replace(" ", "_"),
                                name=bm_name,
                                scores=scores,
                                updated_at=datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(),
                            )
                        )

            if not bookmaker_odds:
                return None

            return CorrectScoreOutput(
                event=event,
                market="correct_score",
                bookmakers=bookmaker_odds,
                metadata=OddsMetadata(
                    generated_at=datetime.now(),
                    is_ended=data.get("completed", False),
                    hash="",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to transform correct score odds: {e}")
            return None

    def _transform_double_chance(self, data: dict[str, Any]) -> DoubleChanceOutput | None:
        """Transform API response to DoubleChanceOutput format."""
        try:
            sport_data = data.get("sport", {})
            league_data = data.get("league", {})
            date_str = data.get("date", data.get("commence_time", ""))

            event = EventData(
                id=str(data.get("id", "")),
                sport=sport_data.get("slug", "football") if isinstance(sport_data, dict) else str(sport_data),
                league=league_data.get("name") if isinstance(league_data, dict) else data.get("league"),
                league_id=league_data.get("id") if isinstance(league_data, dict) else data.get("leagueId"),
                home_team=data.get("home", data.get("home_team", "")),
                away_team=data.get("away", data.get("away_team", "")),
                commence_time=datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now(),
            )

            bookmakers_data = data.get("bookmakers", {})
            bookmaker_odds = []

            if isinstance(bookmakers_data, dict):
                for bm_name, markets in bookmakers_data.items():
                    if not isinstance(markets, list):
                        continue

                    dc_market = next(
                        (m for m in markets if m.get("name") in ["Double Chance", "double_chance"]),
                        None,
                    )

                    if not dc_market:
                        continue

                    odds_data = dc_market.get("odds", {})
                    if isinstance(odds_data, list) and odds_data:
                        odds_data = odds_data[0]

                    if not odds_data:
                        continue

                    try:
                        # API may use different keys: 1X, X2, 12 or home_draw, draw_away, home_away
                        home_draw = float(odds_data.get("1X", odds_data.get("home_draw", 0)))
                        draw_away = float(odds_data.get("X2", odds_data.get("draw_away", 0)))
                        home_away = float(odds_data.get("12", odds_data.get("home_away", 0)))

                        if home_draw > 0 and draw_away > 0 and home_away > 0:
                            updated_str = dc_market.get("updatedAt", "")
                            bookmaker_odds.append(
                                DoubleChanceBookmaker(
                                    key=bm_name.lower().replace(" ", "_"),
                                    name=bm_name,
                                    odds=DoubleChanceOdds(
                                        home_draw=home_draw,
                                        draw_away=draw_away,
                                        home_away=home_away,
                                    ),
                                    updated_at=datetime.fromisoformat(updated_str.replace("Z", "+00:00")) if updated_str else datetime.now(),
                                )
                            )
                    except (ValueError, TypeError):
                        continue

            if not bookmaker_odds:
                return None

            return DoubleChanceOutput(
                event=event,
                market="double_chance",
                bookmakers=bookmaker_odds,
                metadata=OddsMetadata(
                    generated_at=datetime.now(),
                    is_ended=data.get("completed", False),
                    hash="",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to transform double chance odds: {e}")
            return None

    async def get_value_bets_for_bookmaker(
        self,
        bookmaker: str,
    ) -> list[dict[str, Any]]:
        """Fetch value bets for a single bookmaker (cached 2min)."""
        data = await self._request(
            "/value-bets",
            params={
                "bookmaker": bookmaker,
                "includeEventDetails": "true",
            },
            cache_key=f"value_bets:{bookmaker}",
            cache_ttl=120,  # 2 minutes
        )
        return data if isinstance(data, list) else []

    async def get_value_bets(
        self,
        bookmakers: list[str],
        sport: str | None = None,
        league: str | None = None,
        min_ev: float = 2.0,
        limit: int = 10,
    ) -> ValueBetsResponse:
        """Fetch value bets from multiple bookmakers in parallel.

        Args:
            bookmakers: List of bookmaker keys to query
            sport: Filter by sport slug
            league: Filter by league slug
            min_ev: Minimum expected value threshold
            limit: Maximum results to return

        Returns:
            ValueBetsResponse with filtered and sorted value bets
        """
        # Parallel fetch for all bookmakers
        tasks = [self.get_value_bets_for_bookmaker(bm) for bm in bookmakers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge all results
        all_bets: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                all_bets.extend(result)
            # Silently ignore exceptions (bookmaker might not have value bets)

        # Transform and filter
        value_bets: list[ValueBet] = []
        for raw_bet in all_bets:
            try:
                bet = self._transform_value_bet(raw_bet)
                if bet is None:
                    continue

                # Apply filters
                if bet.expected_value < min_ev:
                    continue
                if sport and bet.event.sport.slug.lower() != sport.lower():
                    continue
                if league and bet.event.league.slug.lower() != league.lower():
                    continue

                value_bets.append(bet)
            except Exception as e:
                logger.warning(f"Failed to parse value bet: {e}")
                continue

        # Sort by EV descending and limit
        value_bets.sort(key=lambda x: x.expected_value, reverse=True)

        return ValueBetsResponse(data=value_bets[:limit])

    def _transform_value_bet(self, raw: dict[str, Any]) -> ValueBet | None:
        """Transform raw API response to ValueBet schema.

        API format example:
        {
            "id": "64051699-Spread-home-Bet365--3",
            "expectedValue": 100.64,
            "expectedValueUpdatedAt": "2026-01-14T18:38:38.408Z",
            "betSide": "home",
            "market": {"name": "Spread", "hdp": -3, "home": "1.888", ...},
            "bookmaker": "Bet365",
            "bookmakerOdds": {"home": "1.90", "away": "1.90", "hdp": "-3", "href": "..."},
            "eventId": 64051699,
            "event": {
                "home": "Team A", "away": "Team B",
                "date": "2026-01-15T00:30:00Z",
                "sport": "Basketball",  # String, not object!
                "league": "USA - NCAA"   # String, not object!
            }
        }
        """
        try:
            event_data = raw.get("event", {})
            if not isinstance(event_data, dict):
                return None

            # Sport and league are strings in the API response
            sport_str = event_data.get("sport", "")
            league_str = event_data.get("league", "")

            bm_odds = raw.get("bookmakerOdds", {})
            if not isinstance(bm_odds, dict):
                bm_odds = {}

            # Market contains consensus odds
            market_data = raw.get("market", {})
            if not isinstance(market_data, dict):
                market_data = {}

            # Parse timestamp
            ev_updated_str = raw.get("expectedValueUpdatedAt", "")
            ev_updated = (
                datetime.fromisoformat(ev_updated_str.replace("Z", "+00:00"))
                if ev_updated_str
                else datetime.now()
            )

            # Parse event date
            event_date_str = event_data.get("date", "")
            event_date = (
                datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                if event_date_str
                else datetime.now()
            )

            # Parse market name
            market_name = market_data.get("name", "ML") if isinstance(market_data, dict) else "ML"

            # Helper functions
            def to_slug(s: str) -> str:
                return s.lower().replace(" ", "-").replace(",", "").replace(".", "")

            def safe_float(val: Any, default: float = 0.0) -> float:
                """Safely convert to float, handling 'N/A' and other invalid values."""
                if val is None or val == "N/A" or val == "":
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            return ValueBet(
                id=raw.get("id", f"vb_{raw.get('eventId', '')}_{raw.get('bookmaker', '')}"),
                eventId=str(raw.get("eventId", "")),
                bookmaker=raw.get("bookmaker", ""),
                market=market_name,
                betSide=raw.get("betSide", ""),
                expectedValue=safe_float(raw.get("expectedValue"), 0),
                expectedValueUpdatedAt=ev_updated,
                bookmakerOdds=ValueBetOdds(
                    home=safe_float(bm_odds.get("home")),
                    draw=safe_float(bm_odds.get("draw")) if bm_odds.get("draw") and bm_odds.get("draw") != "N/A" else None,
                    away=safe_float(bm_odds.get("away")),
                    homeDirectLink=bm_odds.get("href"),
                ),
                consensusOdds=ConsensusOdds(
                    home=safe_float(market_data.get("home")),
                    draw=safe_float(market_data.get("draw")) if market_data.get("draw") and market_data.get("draw") != "N/A" else None,
                    away=safe_float(market_data.get("away")),
                ),
                event=ValueBetEvent(
                    home=event_data.get("home", ""),
                    away=event_data.get("away", ""),
                    date=event_date,
                    sport=SportInfo(
                        name=sport_str if isinstance(sport_str, str) else "",
                        slug=to_slug(sport_str) if isinstance(sport_str, str) else "",
                    ),
                    league=LeagueInfo(
                        name=league_str if isinstance(league_str, str) else "",
                        slug=to_slug(league_str) if isinstance(league_str, str) else "",
                    ),
                ),
            )
        except Exception as e:
            logger.error(f"Transform value bet error: {e}")
            return None

    async def get_arbitrage_bets(
        self,
        bookmakers: list[str],
        sport: str | None = None,
        min_profit: float = 1.0,
        limit: int = 5,
    ) -> ArbitrageResponse:
        """Fetch arbitrage opportunities across multiple bookmakers.

        Args:
            bookmakers: List of bookmaker keys to compare
            sport: Filter by sport slug
            min_profit: Minimum profit margin threshold
            limit: Maximum results to return
        """
        # Arbitrage API takes comma-separated bookmakers
        bookmakers_str = ",".join(bookmakers)

        data = await self._request(
            "/arbitrage-bets",
            params={
                "bookmakers": bookmakers_str,
                "includeEventDetails": "true",
                "limit": str(min(limit * 3, 100)),  # Fetch more for filtering
            },
            cache_key=f"arbitrage:{bookmakers_str}",
            cache_ttl=120,  # 2 minutes
        )

        if not isinstance(data, list):
            return ArbitrageResponse(data=[])

        # Transform and filter
        arb_bets: list[ArbitrageBet] = []
        for raw_bet in data:
            try:
                bet = self._transform_arbitrage_bet(raw_bet)
                if bet is None:
                    continue

                # Apply filters
                if bet.profit_margin < min_profit:
                    continue
                if sport and bet.event.sport.slug.lower() != sport.lower():
                    continue

                arb_bets.append(bet)
            except Exception as e:
                logger.warning(f"Failed to parse arbitrage bet: {e}")
                continue

        # Sort by profit descending
        arb_bets.sort(key=lambda x: x.profit_margin, reverse=True)

        return ArbitrageResponse(data=arb_bets[:limit])

    def _transform_arbitrage_bet(self, raw: dict[str, Any]) -> ArbitrageBet | None:
        """Transform raw API response to ArbitrageBet schema."""
        try:
            event_data = raw.get("event", {})
            if not isinstance(event_data, dict):
                return None

            # Sport and league are strings in the API response
            sport_str = event_data.get("sport", "")
            league_str = event_data.get("league", "")

            def to_slug(s: str) -> str:
                return s.lower().replace(" ", "-").replace(",", "").replace(".", "")

            def safe_float(val: Any, default: float = 0.0) -> float:
                if val is None or val == "N/A" or val == "":
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            # Parse timestamp
            detected_str = raw.get("detectedAt", raw.get("createdAt", ""))
            detected_at = (
                datetime.fromisoformat(detected_str.replace("Z", "+00:00"))
                if detected_str
                else datetime.now()
            )

            # Parse event date
            event_date_str = event_data.get("date", "")
            event_date = (
                datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                if event_date_str
                else datetime.now()
            )

            # Parse market
            market_data = raw.get("market", {})
            market_name = market_data.get("name", "ML") if isinstance(market_data, dict) else "ML"

            # Parse legs
            legs_data = raw.get("legs", [])
            legs = []
            for leg in legs_data:
                if isinstance(leg, dict):
                    legs.append(
                        ArbitrageLeg(
                            side=leg.get("side", ""),
                            bookmaker=leg.get("bookmaker", ""),
                            odds=safe_float(leg.get("odds")),
                            directLink=leg.get("directLink", leg.get("href")),
                        )
                    )

            # Parse optimal stakes
            stakes_data = raw.get("optimalStakes", [])
            optimal_stakes = []
            for stake in stakes_data:
                if isinstance(stake, dict):
                    optimal_stakes.append(
                        OptimalStake(
                            side=stake.get("side", ""),
                            bookmaker=stake.get("bookmaker", ""),
                            stake=safe_float(stake.get("stake")),
                            potentialReturn=safe_float(stake.get("potentialReturn")),
                        )
                    )

            return ArbitrageBet(
                id=raw.get("id", f"arb_{raw.get('eventId', '')}"),
                eventId=str(raw.get("eventId", "")),
                market=market_name,
                profitMargin=safe_float(raw.get("profitMargin")),
                impliedProbability=safe_float(raw.get("impliedProbability"), 100.0),
                totalStake=safe_float(raw.get("totalStake"), 100.0),
                legs=legs,
                optimalStakes=optimal_stakes,
                event=ArbitrageEvent(
                    home=event_data.get("home", ""),
                    away=event_data.get("away", ""),
                    date=event_date,
                    sport=SportInfo(
                        name=sport_str if isinstance(sport_str, str) else "",
                        slug=to_slug(sport_str) if isinstance(sport_str, str) else "",
                    ),
                    league=LeagueInfo(
                        name=league_str if isinstance(league_str, str) else "",
                        slug=to_slug(league_str) if isinstance(league_str, str) else "",
                    ),
                ),
                detectedAt=detected_at,
            )
        except Exception as e:
            logger.error(f"Transform arbitrage bet error: {e}")
            return None

    async def get_odds_movements(
        self,
        event_id: str,
        bookmaker: str,
        market: str = "ML",
    ) -> OddsMovementsResponse | None:
        """Fetch historical odds movements for an event.

        Args:
            event_id: Event identifier
            bookmaker: Bookmaker to get movements from
            market: Market type (ML, Totals, etc.)
        """
        data = await self._request(
            "/odds/movements",
            params={
                "eventId": event_id,
                "bookmaker": bookmaker,
                "market": market,
            },
            cache_key=f"movements:{event_id}:{bookmaker}:{market}",
            cache_ttl=300,  # 5 minutes
        )

        if not data or not isinstance(data, dict):
            return None

        return self._transform_odds_movements(data, event_id, bookmaker, market)

    def _transform_odds_movements(
        self,
        raw: dict[str, Any],
        event_id: str,
        bookmaker: str,
        market: str,
    ) -> OddsMovementsResponse | None:
        """Transform raw API response to OddsMovementsResponse."""
        try:

            def safe_float(val: Any, default: float = 0.0) -> float:
                if val is None or val == "N/A" or val == "":
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            def parse_timestamp(ts: Any) -> datetime:
                if isinstance(ts, (int, float)):
                    return datetime.fromtimestamp(ts)
                if isinstance(ts, str):
                    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return datetime.now()

            def parse_snapshot(data: dict[str, Any]) -> OddsSnapshot:
                return OddsSnapshot(
                    home=safe_float(data.get("home")),
                    draw=safe_float(data.get("draw")) if data.get("draw") else None,
                    away=safe_float(data.get("away")),
                    timestamp=parse_timestamp(data.get("timestamp", data.get("time"))),
                )

            # Parse opening odds
            opening_data = raw.get("opening", {})
            opening = parse_snapshot(opening_data) if opening_data else None

            # Parse latest odds
            latest_data = raw.get("latest", {})
            latest = parse_snapshot(latest_data) if latest_data else None

            # Parse movements array
            movements_data = raw.get("movements", [])
            movements = []
            for m in movements_data:
                if isinstance(m, dict):
                    movements.append(parse_snapshot(m))

            # If no opening/latest, use first/last movement
            if not opening and movements:
                opening = movements[0]
            if not latest and movements:
                latest = movements[-1]

            # Need at least opening and latest
            if not opening or not latest:
                return None

            return OddsMovementsResponse(
                eventId=str(raw.get("eventId", event_id)),
                bookmaker=raw.get("bookmaker", bookmaker),
                market=raw.get("market", market),
                opening=opening,
                latest=latest,
                movements=movements,
            )
        except Exception as e:
            logger.error(f"Transform odds movements error: {e}")
            return None

    async def get_odds_multi(
        self,
        event_ids: list[str],
        bookmakers: list[str],
        market: str = "1x2",
    ) -> list[OddsOutput | AsianHandicapOutput | TotalsOutput | BTTSOutput | CorrectScoreOutput | DoubleChanceOutput]:
        """GET /odds with multiple events - Batch odds request.

        Fetches odds for multiple events in parallel to reduce quota usage.

        Args:
            event_ids: List of event IDs (max 10)
            bookmakers: List of bookmaker keys
            market: Market type

        Returns:
            List of odds results (one per event)
        """
        # Limit to 10 events max
        event_ids = event_ids[:10]

        # Fetch odds in parallel
        tasks = [self.get_odds(eid, bookmakers, market) for eid in event_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors and None results
        odds_list = []
        for result in results:
            if result is not None and not isinstance(result, Exception):
                odds_list.append(result)

        return odds_list

    async def get_odds_updated(
        self,
        since: int,
        bookmaker: str | None = None,
        sport: str | None = None,
        market: str = "ML",
    ) -> list[dict[str, Any]]:
        """GET /odds/updated - Get odds that changed since a timestamp.

        Useful for efficient polling without fetching all odds.

        Args:
            since: Unix timestamp (seconds) - only return odds updated after this time
            bookmaker: Optional bookmaker filter
            sport: Optional sport filter
            market: Market type filter

        Returns:
            List of updated odds entries
        """
        params: dict[str, Any] = {
            "since": since,
            "market": market,
        }
        if bookmaker:
            params["bookmaker"] = bookmaker
        if sport:
            params["sport"] = sport

        # Short cache for updated odds (30 seconds)
        cache_key = f"odds_updated:{since}:{bookmaker or 'all'}:{sport or 'all'}:{market}"
        data = await self._request(
            "/odds/updated",
            params=params,
            cache_key=cache_key,
            cache_ttl=30,
        )

        if not data or not isinstance(data, list):
            return []

        return data

    async def get_participants(
        self,
        sport: str,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /participants - List teams/participants.

        Args:
            sport: Sport slug (required)
            search: Optional search query for team name

        Returns:
            List of participants
        """
        params: dict[str, Any] = {"sport": sport}
        if search:
            params["search"] = search

        cache_key = f"participants:{sport}:{search or 'all'}"
        data = await self._request(
            "/participants",
            params=params,
            cache_key=cache_key,
            cache_ttl=settings.cache_ttl_sports,  # 24h cache
        )

        if not data or not isinstance(data, list):
            return []

        return data

    async def get_participant(self, participant_id: str) -> dict[str, Any] | None:
        """GET /participants/{id} - Get a single participant by ID.

        Args:
            participant_id: Participant identifier

        Returns:
            Participant data or None if not found
        """
        cache_key = f"participant:{participant_id}"
        data = await self._request(
            f"/participants/{participant_id}",
            cache_key=cache_key,
            cache_ttl=settings.cache_ttl_sports,  # 24h cache
        )

        if not data or not isinstance(data, dict):
            return None

        return data


odds_client = OddsAPIClient()
