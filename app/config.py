import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default bookmakers per region (can be overridden via env vars)
DEFAULT_REGION_BOOKMAKERS: dict[str, list[str]] = {
    "br": ["betano", "pixbet", "kto", "betclic", "winamax"],
    "fr": ["betclic", "winamax", "unibet", "pmu", "zebet"],
    "uk": ["bet365", "william_hill", "ladbrokes", "paddy_power", "betfair"],
    "es": ["bet365", "betway", "codere", "sportium", "888sport"],
    "it": ["bet365", "sisal", "snai", "goldbet", "lottomatica"],
    "de": ["bet365", "tipico", "bwin", "betway", "unibet"],
    "mx": ["caliente", "betway", "bet365", "codere", "1xbet"],
    "ar": ["bet365", "betsson", "betway", "codere", "bwin"],
    "co": ["betplay", "wplay", "bet365", "betsson", "1xbet"],
}


def load_region_bookmakers() -> dict[str, list[str]]:
    """Load region bookmakers from env vars, falling back to defaults."""
    result = {}
    for region, defaults in DEFAULT_REGION_BOOKMAKERS.items():
        env_key = f"REGION_BOOKMAKERS_{region.upper()}"
        env_val = os.getenv(env_key)
        if env_val:
            result[region] = [b.strip() for b in env_val.split(",") if b.strip()]
        else:
            result[region] = defaults
    return result


REGION_BOOKMAKERS: dict[str, list[str]] = load_region_bookmakers()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/odds_data"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Odds-API.io
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.odds-api.io/v3"

    # Static files
    static_files_path: str = "static"

    # Bookmakers (comma-separated, default fallback)
    default_bookmakers: str = "betano,sportingbet,betfair,bet365"

    # Cache TTL (seconds)
    cache_ttl_sports: int = 86400  # 24h
    cache_ttl_events: int = 300  # 5min
    cache_ttl_odds: int = 60  # 1min
    cache_ttl_upcoming: int = 3600  # 1h

    # Data retention
    retention_days_ended: int = 7  # Keep ended events for 7 days
    clean_data_token: str = ""  # Token for /clean-data endpoint (optional)

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "60/minute"  # General endpoints
    rate_limit_heavy: str = "10/minute"  # Heavy endpoints (generate, value-bets)
    rate_limit_search: str = "30/minute"  # Search endpoints

    # CORS
    cors_origins: str = "*"  # Comma-separated origins or "*" for all

    # API Key authentication
    api_key: str = ""  # If set, requires X-API-Key header
    api_key_enabled: bool = False

    # League whitelist filtering
    whitelist_enabled: bool = True  # Toggle global league filtering

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Major leagues for upcoming events (Odds-API.io league names)
    major_leagues: list[str] = [
        "England - Premier League",
        "Germany - Bundesliga",
        "Italy - Serie A",
        "France - Ligue 1",
        "Spain - LaLiga",
        "Netherlands - Eredivisie",
        "Portugal - Liga Portugal",
        "Brazil - Brasileiro Serie A",
        "International Clubs - UEFA Champions League",
        "International Clubs - UEFA Europa League",
        "International Clubs - UEFA Conference League",
    ]

    @property
    def bookmakers_list(self) -> list[str]:
        return [b.strip() for b in self.default_bookmakers.split(",") if b.strip()]


settings = Settings()
