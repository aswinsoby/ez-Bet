# ---- Leagues (football-data.co.uk codes) ----
LEAGUES = {
    "E0": "Premier League",
    "E1": "Championship",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
}

# ---- Risk filters ("best odds, less risk") ----
MIN_PROB = 0.55          # only picks the model thinks win >= 55% of the time
MIN_EDGE = 0.03          # expected value must be >= +3%
MIN_ODDS = 1.30          # skip tiny-return picks
MAX_ODDS = 2.50          # skip long shots
MODEL_WEIGHT = 0.5       # blend model with market (0.5 = half/half) -> fewer overconfident picks
MIN_GAMES = 5            # team must have played this many games in the data

# ---- Staking ----
BANKROLL = 100.0         # your bankroll in GBP
KELLY_FRACTION = 0.25    # quarter-Kelly
MAX_STAKE_PCT = 0.02     # never more than 2% of bankroll on one pick
MAX_PICKS = 5            # max picks per day

# ---- Model ----
TIME_DECAY = 0.0019      # recent matches count more (~1 year half-life)
