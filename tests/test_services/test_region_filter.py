"""Tests for the region_filter service."""

import pytest
from fastapi import HTTPException

from app.schemas.common import Region
from app.services.region_filter import (
    filter_response_bookmakers,
    get_allowed_bookmakers,
    get_bookmakers_for_region,
    validate_bookmaker_access,
)


class TestGetAllowedBookmakers:
    """Tests for get_allowed_bookmakers function."""

    def test_returns_brazil_bookmakers(self):
        """Brazil region returns expected bookmakers."""
        result = get_allowed_bookmakers(Region.BR)
        assert "betano" in result
        assert "pixbet" in result
        assert "betclic" in result
        assert "winamax" in result
        assert len(result) >= 5

    def test_returns_uk_bookmakers(self):
        """UK region returns expected bookmakers."""
        result = get_allowed_bookmakers(Region.UK)
        assert "bet365" in result
        assert "william_hill" in result
        assert "betfair" in result

    def test_returns_france_bookmakers(self):
        """France region returns expected bookmakers."""
        result = get_allowed_bookmakers(Region.FR)
        assert "betclic" in result
        assert "winamax" in result


class TestGetBookmakersForRegion:
    """Tests for get_bookmakers_for_region function."""

    def test_no_requested_returns_all_allowed(self):
        """Without requested bookmakers, returns all allowed for region."""
        result = get_bookmakers_for_region(Region.BR, None)
        assert len(result) >= 5
        assert "betano" in result

    def test_valid_requested_bookmakers(self):
        """Valid requested bookmakers are returned."""
        result = get_bookmakers_for_region(Region.BR, ["betano", "pixbet"])
        assert result == ["betano", "pixbet"]

    def test_invalid_bookmaker_raises_error(self):
        """Invalid bookmaker raises HTTPException 400."""
        with pytest.raises(HTTPException) as exc:
            get_bookmakers_for_region(Region.BR, ["bet365"])
        assert exc.value.status_code == 400
        assert "bet365" in exc.value.detail
        assert "not available" in exc.value.detail

    def test_mixed_valid_invalid_raises_error(self):
        """Mix of valid and invalid bookmakers raises error."""
        with pytest.raises(HTTPException) as exc:
            get_bookmakers_for_region(Region.BR, ["betano", "bet365"])
        assert exc.value.status_code == 400
        assert "bet365" in exc.value.detail

    def test_empty_requested_returns_all(self):
        """Empty list returns all allowed bookmakers."""
        result = get_bookmakers_for_region(Region.UK, [])
        # Empty list is falsy, so all allowed are returned
        assert len(result) >= 5


class TestValidateBookmakerAccess:
    """Tests for validate_bookmaker_access function."""

    def test_valid_bookmaker_passes(self):
        """Valid bookmaker does not raise."""
        # Should not raise
        validate_bookmaker_access("betano", Region.BR)
        validate_bookmaker_access("bet365", Region.UK)

    def test_invalid_bookmaker_raises(self):
        """Invalid bookmaker raises HTTPException 400."""
        with pytest.raises(HTTPException) as exc:
            validate_bookmaker_access("bet365", Region.BR)
        assert exc.value.status_code == 400
        assert "bet365" in exc.value.detail


class TestFilterResponseBookmakers:
    """Tests for filter_response_bookmakers function."""

    def test_filters_to_allowed_only(self):
        """Filters response to only allowed bookmakers."""
        data = [
            {"key": "betano", "name": "Betano", "odds": 1.5},
            {"key": "bet365", "name": "Bet365", "odds": 1.6},
            {"key": "pixbet", "name": "Pixbet", "odds": 1.55},
        ]
        result = filter_response_bookmakers(data, Region.BR)
        assert len(result) == 2
        keys = [b["key"] for b in result]
        assert "betano" in keys
        assert "pixbet" in keys
        assert "bet365" not in keys

    def test_empty_list_returns_empty(self):
        """Empty input returns empty list."""
        result = filter_response_bookmakers([], Region.BR)
        assert result == []

    def test_custom_bookmaker_key(self):
        """Custom bookmaker key field works."""
        data = [
            {"bookmaker_id": "betano", "name": "Betano"},
            {"bookmaker_id": "bet365", "name": "Bet365"},
        ]
        result = filter_response_bookmakers(data, Region.BR, bookmaker_key="bookmaker_id")
        assert len(result) == 1
        assert result[0]["bookmaker_id"] == "betano"


class TestAllRegions:
    """Verify all regions have proper configuration."""

    @pytest.mark.parametrize(
        "region",
        [Region.BR, Region.FR, Region.UK, Region.ES, Region.IT, Region.DE, Region.MX, Region.AR, Region.CO],
    )
    def test_region_has_bookmakers(self, region):
        """Each region should have at least one bookmaker configured."""
        result = get_allowed_bookmakers(region)
        assert len(result) >= 1, f"Region {region.value} has no bookmakers configured"
