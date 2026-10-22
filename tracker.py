"""EZ Bet results tracker — stores your bets in bets.csv and settles them from real results."""
import os
from datetime import datetime

import pandas as pd

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bets.csv")
COLS = ["id", "date", "div", "league", "home", "away", "match", "market", "pick",
        "odds", "stake", "prob", "edge", "status", "profit", "result", "added"]
STATUSES = ["Pending", "Won", "Lost", "Void"]


def load():
    if os.path.exists(FILE):
        df = pd.read_csv(FILE, dtype={"date": str})
        for c in COLS:
            if c not in df:
                df[c] = None
        return df[COLS]
    return pd.DataFrame(columns=COLS)


def save(df):
    df = recalc(df)
    df.to_csv(FILE, index=False)
    return df


def recalc(df):
    df = df.copy()
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    df["stake"] = pd.to_numeric(df["stake"], errors="coerce").fillna(0)
    df["profit"] = 0.0
    won, lost = df.status == "Won", df.status == "Lost"
    df.loc[won, "profit"] = (df.stake * (df.odds - 1))[won]
    df.loc[lost, "profit"] = -df.stake[lost]
    df["profit"] = df["profit"].round(2)
    return df


def add(df, p, stake=None):
    bid = f"{p['date']}_{p['div']}_{p['home']}_{p['away']}_{p['market']}"
    if bid in set(df.id):
        return df, False
    row = {"id": bid, "date": str(p["date"]), "div": p["div"], "league": p["league"],
           "home": p["home"], "away": p["away"], "match": p["match"], "market": p["market"],
           "pick": p["pick"], "odds": round(float(p["best_odds"]), 2),
           "stake": round(float(stake if stake is not None else p["stake_gbp"]), 2),
           "prob": round(float(p["prob"]), 3), "edge": round(float(p["edge"]), 3),
           "status": "Pending", "profit": 0.0, "result": "",
           "added": datetime.now().strftime("%Y-%m-%d %H:%M")}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return save(df), True


def won(market, hg, ag):
    return {"H": hg > ag, "D": hg == ag, "A": hg < ag,
            "O2.5": hg + ag > 2, "U2.5": hg + ag <= 2}[market]


def settle(df, results_by_div):
    """results_by_div: {div: DataFrame with Date, HomeTeam, AwayTeam, FTHG, FTAG}"""
    n = 0
    for i, b in df[df.status == "Pending"].iterrows():
        res = results_by_div.get(b["div"])
        if res is None or res.empty:
            continue
        r = res[(res.Date.dt.strftime("%Y-%m-%d") == str(b["date"]))
                & (res.HomeTeam == b["home"]) & (res.AwayTeam == b["away"])].dropna(subset=["FTHG", "FTAG"])
        if r.empty:
            continue
        hg, ag = int(r.iloc[0].FTHG), int(r.iloc[0].FTAG)
        df.loc[i, "status"] = "Won" if won(b["market"], hg, ag) else "Lost"
        df.loc[i, "result"] = f"{hg}-{ag}"
        n += 1
    return save(df), n


def stats(df):
    s = df[df.status.isin(["Won", "Lost"])]
    staked = s.stake.sum()
    return {
        "bets": len(df), "settled": len(s), "pending": int((df.status == "Pending").sum()),
        "win_rate": (s.status == "Won").mean() if len(s) else 0.0,
        "profit": s.profit.sum(), "staked": staked,
        "roi": s.profit.sum() / staked if staked else 0.0,
    }
