"""Region-based bookmaker filtering service.

Filters bookmakers based on region/country compliance requirements.
Each region only allows certain licensed bookmakers.
"""

from fastapi import HTTPException

from app.config import REGION_BOOKMAKERS
from app.schemas.common import Region


def get_allowed_bookmakers(region: Region) -> list[str]:
    """Get the list of allowed bookmakers for a region.

    Args:
        region: The target region code

    Returns:
        List of allowed bookmaker keys for the region

    Raises:
        HTTPException: If region is not configured
    """
    allowed = REGION_BOOKMAKERS.get(region.value)
    if allowed is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown region: {region.value}. Supported: {list(REGION_BOOKMAKERS.keys())}",
        )
    return allowed


def get_bookmakers_for_region(
    region: Region,
    requested: list[str] | None = None,
) -> list[str]:
    """Get bookmakers to query, filtered by region.

    If specific bookmakers are requested, validates they're allowed in the region.
    Otherwise returns all allowed bookmakers for the region.

    Args:
        region: The target region code
        requested: Optional list of specifically requested bookmakers

    Returns:
        List of bookmaker keys to use

    Raises:
        HTTPException: If any requested bookmaker is not allowed in the region
    """
    allowed = get_allowed_bookmakers(region)

    if not requested:
        return allowed

    # Validate requested bookmakers are allowed
    invalid = [b for b in requested if b not in allowed]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Bookmakers not available in region '{region.value}': {invalid}. "
            f"Allowed: {allowed}",
        )

    return requested


def validate_bookmaker_access(bookmaker: str, region: Region) -> None:
    """Validate a single bookmaker is allowed in a region.

    Args:
        bookmaker: The bookmaker key to validate
        region: The target region code

    Raises:
        HTTPException: If bookmaker is not allowed in the region
    """
    allowed = get_allowed_bookmakers(region)
    if bookmaker not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Bookmaker '{bookmaker}' not available in region '{region.value}'. "
            f"Allowed: {allowed}",
        )


def filter_response_bookmakers(
    bookmakers_data: list[dict],
    region: Region,
    bookmaker_key: str = "key",
) -> list[dict]:
    """Filter a list of bookmaker data to only include allowed bookmakers.

    Provides double-safety by filtering response data even if the upstream
    API returns bookmakers that weren't requested.

    Args:
        bookmakers_data: List of bookmaker dicts from API response
        region: The target region code
        bookmaker_key: Key in dict that contains the bookmaker identifier

    Returns:
        Filtered list containing only allowed bookmakers
    """
    allowed = REGION_BOOKMAKERS.get(region.value, [])
    return [b for b in bookmakers_data if b.get(bookmaker_key) in allowed]
