import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.schemas import (
    AsianHandicapBookmaker,
    AsianHandicapLine,
    AsianHandicapOutput,
    BookmakerOdds,
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=request_params)
                response.raise_for_status()
                data = response.json()

                # Cache if key provided
                if cache_key and cache_ttl:
                    await cache_service.set(cache_key, data, cache_ttl)

                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

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
        if date_from:
            params["from"] = date_from
        if date_to:
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
        params: dict[str, Any] = {}
        if sport:
            params["sport"] = sport

        cache_key = f"events:live:{sport or 'all'}"
        data = await self._request(
            "/events/live",
            params=params,
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
    ) -> OddsOutput | AsianHandicapOutput | TotalsOutput | None:
        """GET /odds - Get odds for a specific event."""
        # Map internal market names to API market names
        api_market = (
            "ML"
            if market == "1x2"
            else "Asian Handicap"
            if market == "asian_handicap"
            else "Totals"
            if market == "totals"
            else market
        )

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
        if market == "asian_handicap":
            return self._transform_asian_handicap(data)
        elif market == "totals":
            return self._transform_totals(data)
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


odds_client = OddsAPIClient()
