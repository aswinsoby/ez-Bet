"""Daily football value picks.

Usage:
    python main.py            # today's matches
    python main.py --days 3   # next 3 days
Data: football-data.co.uk (free, no API key). Results + upcoming fixtures with odds.
"""
import argparse
from datetime import date, timedelta

import pandas as pd

import config as C
from model import PoissonModel

BASE = "https://www.football-data.co.uk"
MARKETS = {  # market -> (best odds col, avg odds col, group for de-margining)
    "H": ("MaxH", "AvgH", "1X2"), "D": ("MaxD", "AvgD", "1X2"), "A": ("MaxA", "AvgA", "1X2"),
    "O2.5": ("Max>2.5", "Avg>2.5", "OU"), "U2.5": ("Max<2.5", "Avg<2.5", "OU"),
}
FALLBACK = {"MaxH": "B365H", "MaxD": "B365D", "MaxA": "B365A",
            "Max>2.5": "B365>2.5", "Max<2.5": "B365<2.5"}


def read_csv(url):
    df = pd.read_csv(url, encoding="latin-1", on_bad_lines="skip")
    df.columns = df.columns.str.replace("ï»¿", "").str.strip()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    return df.dropna(subset=["Date", "HomeTeam", "AwayTeam"])


def season_codes(today):
    start = today.year if today.month >= 7 else today.year - 1
    return [f"{(start - k) % 100:02d}{(start - k + 1) % 100:02d}" for k in (0, 1)]


def load_history(div, today):
    frames = []
    for s in season_codes(today):
        try:
            frames.append(read_csv(f"{BASE}/mmz4281/{s}/{div}.csv"))
        except Exception as e:
            print(f"  ! couldn't load {div} {s}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def odds(row, col):
    v = row.get(col)
    if pd.isna(v) and col in FALLBACK:
        v = row.get(FALLBACK[col])
    return float(v) if pd.notna(v) else None


def market_fair_probs(row):
    """Remove bookmaker margin from average odds -> market's true probability."""
    out = {}
    for grp in ("1X2", "OU"):
        keys = [k for k, v in MARKETS.items() if v[2] == grp]
        inv = {k: 1 / odds(row, MARKETS[k][1]) for k in keys if odds(row, MARKETS[k][1])}
        if len(inv) == len(keys):
            s = sum(inv.values())
            out.update({k: v / s for k, v in inv.items()})
    return out


def analyse(fixtures, model):
    rows = []
    for _, f in fixtures.iterrows():
        if not (model.knows(f.HomeTeam, C.MIN_GAMES) and model.knows(f.AwayTeam, C.MIN_GAMES)):
            continue
        p = model.predict(f.HomeTeam, f.AwayTeam)
        mkt = market_fair_probs(f)
        for m, (best_col, _, _) in MARKETS.items():
            o = odds(f, best_col)
            if not o:
                continue
            prob = C.MODEL_WEIGHT * p[m] + (1 - C.MODEL_WEIGHT) * mkt.get(m, p[m])
            edge = prob * o - 1
            rows.append({
                "date": f.Date.date(), "time": f.get("Time", ""), "league": C.LEAGUES[f.Div],
                "div": f.Div, "home": f.HomeTeam, "away": f.AwayTeam, "market": m,
                "match": f"{f.HomeTeam} v {f.AwayTeam}",
                "pick": {"H": f.HomeTeam + " win", "D": "Draw", "A": f.AwayTeam + " win",
                         "O2.5": "Over 2.5", "U2.5": "Under 2.5"}[m],
                "best_odds": o, "prob": prob, "edge": edge,
                "xG": f"{p['xG_home']:.1f}-{p['xG_away']:.1f}",
            })
    return pd.DataFrame(rows)


def pick(df):
    if df.empty:
        return df
    df = df[(df.prob >= C.MIN_PROB) & (df.edge >= C.MIN_EDGE)
            & df.best_odds.between(C.MIN_ODDS, C.MAX_ODDS)].copy()
    # one pick per match: keep the safest-good-value one
    df["score"] = df.edge * df.prob
    df = df.sort_values("score", ascending=False).drop_duplicates("match").head(C.MAX_PICKS)
    kelly = (df.edge / (df.best_odds - 1)) * C.KELLY_FRACTION
    df["stake_gbp"] = (kelly.clip(upper=C.MAX_STAKE_PCT) * C.BANKROLL).round(2)
    return df.drop(columns="score")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    args = ap.parse_args()
    today = date.today()
    end = today + timedelta(days=args.days - 1)

    fx = read_csv(f"{BASE}/fixtures.csv")
    fx = fx[fx.Div.isin(C.LEAGUES) & fx.Date.dt.date.between(today, end)]
    if fx.empty:
        print("No fixtures in selected leagues for that window.")
        return

    allrows = []
    for div, games in fx.groupby("Div"):
        print(f"Modelling {C.LEAGUES[div]} ({len(games)} games)...")
        hist = load_history(div, today)
        if hist.empty:
            continue
        model = PoissonModel(C.TIME_DECAY).fit(hist)
        allrows.append(analyse(games, model))

    full = pd.concat(allrows, ignore_index=True) if allrows else pd.DataFrame()
    picks = pick(full)
    tag = today.isoformat()
    full.to_csv(f"all_analysis_{tag}.csv", index=False)

    if picks.empty:
        print("\nNo picks pass the risk filters today. That's normal; skip the day.")
        return
    picks.to_csv(f"picks_{tag}.csv", index=False)
    show = picks.assign(prob=(picks.prob * 100).round(1).astype(str) + "%",
                        edge=(picks.edge * 100).round(1).astype(str) + "%")
    print("\n=== TODAY'S PICKS ===")
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
