"""League filtering helpers for events."""

from app.schemas.events import EventResponse, LiveEventResponse
from app.services.league_whitelist_service import is_league_allowed


def filter_events_by_whitelist(
    events: list[EventResponse],
    exact_matches: set[str],
    patterns: list[str],
) -> list[EventResponse]:
    """Filter events by allowed leagues (whitelist)."""
    if not exact_matches and not patterns:
        return events
    return [
        e
        for e in events
        if is_league_allowed(e.league.slug, exact_matches, patterns)
    ]


def filter_live_events_by_whitelist(
    events: list[LiveEventResponse],
    exact_matches: set[str],
    patterns: list[str],
) -> list[LiveEventResponse]:
    """Filter live events by allowed leagues (whitelist)."""
    if not exact_matches and not patterns:
        return events
    return [
        e
        for e in events
        if is_league_allowed(e.league.slug, exact_matches, patterns)
    ]
