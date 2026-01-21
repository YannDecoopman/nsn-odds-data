"""Default league whitelist data.

Note: League slugs are based on Odds-API.io naming conventions.
Patterns with wildcards (*) are supported for matching multiple leagues.
"""

DEFAULT_WHITELIST: list[dict] = [
    # ==========================================================================
    # FOOTBALL - Major European Leagues
    # ==========================================================================
    {"sport": "football", "league_slug": "england-premier-league", "league_name": "England - Premier League"},
    {"sport": "football", "league_slug": "england-championship", "league_name": "England - Championship"},
    {"sport": "football", "league_slug": "england-fa-cup", "league_name": "England - FA Cup"},
    {"sport": "football", "league_slug": "england-efl-cup", "league_name": "England - EFL Cup"},
    {"sport": "football", "league_slug": "spain-la-liga", "league_name": "Spain - La Liga"},
    {"sport": "football", "league_slug": "spain-segunda-division", "league_name": "Spain - Segunda Division"},
    {"sport": "football", "league_slug": "spain-copa-del-rey", "league_name": "Spain - Copa del Rey"},
    {"sport": "football", "league_slug": "germany-bundesliga", "league_name": "Germany - Bundesliga"},
    {"sport": "football", "league_slug": "germany-2-bundesliga", "league_name": "Germany - 2. Bundesliga"},
    {"sport": "football", "league_slug": "germany-dfb-pokal", "league_name": "Germany - DFB Pokal"},
    {"sport": "football", "league_slug": "italy-serie-a", "league_name": "Italy - Serie A"},
    {"sport": "football", "league_slug": "italy-serie-b", "league_name": "Italy - Serie B"},
    {"sport": "football", "league_slug": "italy-coppa-italia", "league_name": "Italy - Coppa Italia"},
    {"sport": "football", "league_slug": "france-ligue-1", "league_name": "France - Ligue 1"},
    {"sport": "football", "league_slug": "france-ligue-2", "league_name": "France - Ligue 2"},
    {"sport": "football", "league_slug": "france-coupe-de-france", "league_name": "France - Coupe de France"},
    {"sport": "football", "league_slug": "portugal-primeira-liga", "league_name": "Portugal - Primeira Liga"},
    {"sport": "football", "league_slug": "netherlands-eredivisie", "league_name": "Netherlands - Eredivisie"},
    {"sport": "football", "league_slug": "belgium-pro-league", "league_name": "Belgium - Pro League"},
    {"sport": "football", "league_slug": "scotland-premiership", "league_name": "Scotland - Premiership"},
    {"sport": "football", "league_slug": "turkey-super-lig", "league_name": "Turkey - Super Lig"},
    # ==========================================================================
    # FOOTBALL - UEFA Competitions
    # ==========================================================================
    {"sport": "football", "league_slug": "uefa-champions-league", "league_name": "UEFA Champions League"},
    {"sport": "football", "league_slug": "uefa-europa-league", "league_name": "UEFA Europa League"},
    {"sport": "football", "league_slug": "uefa-conference-league", "league_name": "UEFA Conference League"},
    {"sport": "football", "league_slug": "uefa-super-cup", "league_name": "UEFA Super Cup"},
    {"sport": "football", "league_slug": "uefa-nations-league", "league_name": "UEFA Nations League"},
    {"sport": "football", "league_slug": "uefa-euro*", "league_name": "UEFA Euro (all)"},
    # ==========================================================================
    # FOOTBALL - South America
    # ==========================================================================
    {"sport": "football", "league_slug": "brazil-serie-a", "league_name": "Brazil - Serie A"},
    {"sport": "football", "league_slug": "brazil-serie-b", "league_name": "Brazil - Serie B"},
    {"sport": "football", "league_slug": "brazil-copa-do-brasil", "league_name": "Brazil - Copa do Brasil"},
    {"sport": "football", "league_slug": "argentina-primera-division", "league_name": "Argentina - Primera Division"},
    {"sport": "football", "league_slug": "conmebol-copa-libertadores", "league_name": "CONMEBOL Copa Libertadores"},
    {"sport": "football", "league_slug": "conmebol-copa-sudamericana", "league_name": "CONMEBOL Copa Sudamericana"},
    # ==========================================================================
    # FOOTBALL - North America
    # ==========================================================================
    {"sport": "football", "league_slug": "usa-mls", "league_name": "USA - MLS"},
    {"sport": "football", "league_slug": "mexico-liga-mx", "league_name": "Mexico - Liga MX"},
    {"sport": "football", "league_slug": "concacaf-champions*", "league_name": "CONCACAF Champions (all)"},
    # ==========================================================================
    # FOOTBALL - International
    # ==========================================================================
    {"sport": "football", "league_slug": "fifa-world-cup*", "league_name": "FIFA World Cup (all)"},
    {"sport": "football", "league_slug": "fifa-club-world-cup", "league_name": "FIFA Club World Cup"},
    {"sport": "football", "league_slug": "international-friendlies", "league_name": "International Friendlies"},
    # ==========================================================================
    # TENNIS - ATP
    # ==========================================================================
    {"sport": "tennis", "league_slug": "atp-australian-open", "league_name": "ATP Australian Open"},
    {"sport": "tennis", "league_slug": "atp-roland-garros", "league_name": "ATP Roland Garros"},
    {"sport": "tennis", "league_slug": "atp-wimbledon", "league_name": "ATP Wimbledon"},
    {"sport": "tennis", "league_slug": "atp-us-open", "league_name": "ATP US Open"},
    {"sport": "tennis", "league_slug": "atp-masters-1000*", "league_name": "ATP Masters 1000 (all)"},
    {"sport": "tennis", "league_slug": "atp-500*", "league_name": "ATP 500 (all)"},
    {"sport": "tennis", "league_slug": "atp-250*", "league_name": "ATP 250 (all)"},
    {"sport": "tennis", "league_slug": "atp-tour-finals", "league_name": "ATP Tour Finals"},
    # ==========================================================================
    # TENNIS - WTA
    # ==========================================================================
    {"sport": "tennis", "league_slug": "wta-australian-open", "league_name": "WTA Australian Open"},
    {"sport": "tennis", "league_slug": "wta-roland-garros", "league_name": "WTA Roland Garros"},
    {"sport": "tennis", "league_slug": "wta-wimbledon", "league_name": "WTA Wimbledon"},
    {"sport": "tennis", "league_slug": "wta-us-open", "league_name": "WTA US Open"},
    {"sport": "tennis", "league_slug": "wta-1000*", "league_name": "WTA 1000 (all)"},
    {"sport": "tennis", "league_slug": "wta-500*", "league_name": "WTA 500 (all)"},
    {"sport": "tennis", "league_slug": "wta-finals", "league_name": "WTA Finals"},
    # ==========================================================================
    # BASKETBALL
    # ==========================================================================
    {"sport": "basketball", "league_slug": "nba", "league_name": "NBA"},
    {"sport": "basketball", "league_slug": "nba-playoffs", "league_name": "NBA Playoffs"},
    {"sport": "basketball", "league_slug": "euroleague", "league_name": "EuroLeague"},
    {"sport": "basketball", "league_slug": "ncaa-basketball*", "league_name": "NCAA Basketball (all)"},
    {"sport": "basketball", "league_slug": "fiba-world-cup*", "league_name": "FIBA World Cup (all)"},
    # ==========================================================================
    # HOCKEY
    # ==========================================================================
    {"sport": "hockey", "league_slug": "nhl", "league_name": "NHL"},
    {"sport": "hockey", "league_slug": "nhl-playoffs", "league_name": "NHL Playoffs"},
    {"sport": "hockey", "league_slug": "khl", "league_name": "KHL"},
    {"sport": "hockey", "league_slug": "iihf-world-championship*", "league_name": "IIHF World Championship (all)"},
    # ==========================================================================
    # AMERICAN FOOTBALL
    # ==========================================================================
    {"sport": "american_football", "league_slug": "nfl", "league_name": "NFL"},
    {"sport": "american_football", "league_slug": "nfl-playoffs", "league_name": "NFL Playoffs"},
    {"sport": "american_football", "league_slug": "super-bowl", "league_name": "Super Bowl"},
    {"sport": "american_football", "league_slug": "ncaa-football*", "league_name": "NCAA Football (all)"},
    # ==========================================================================
    # BASEBALL
    # ==========================================================================
    {"sport": "baseball", "league_slug": "mlb", "league_name": "MLB"},
    {"sport": "baseball", "league_slug": "mlb-playoffs", "league_name": "MLB Playoffs"},
    {"sport": "baseball", "league_slug": "world-series", "league_name": "World Series"},
]
