"""Poisson team-strength model (attack/defence + home advantage, time-weighted)."""
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson


class PoissonModel:
    def __init__(self, time_decay=0.0019):
        self.xi = time_decay

    def fit(self, df):
        """df columns: Date, HomeTeam, AwayTeam, FTHG, FTAG"""
        df = df.dropna(subset=["FTHG", "FTAG"])
        teams = sorted(set(df.HomeTeam) | set(df.AwayTeam))
        self.idx = {t: i for i, t in enumerate(teams)}
        self.games = (df.HomeTeam.value_counts().add(df.AwayTeam.value_counts(), fill_value=0)).to_dict()
        n = len(teams)
        h = df.HomeTeam.map(self.idx).values
        a = df.AwayTeam.map(self.idx).values
        hg, ag = df.FTHG.values.astype(float), df.FTAG.values.astype(float)
        w = np.exp(-self.xi * (df.Date.max() - df.Date).dt.days.values)

        def nll(p):
            att, de, home = p[:n], p[n:2 * n], p[-1]
            lh = np.exp(att[h] + de[a] + home)
            la = np.exp(att[a] + de[h])
            ll = w * (hg * np.log(lh) - lh + ag * np.log(la) - la)
            return -ll.sum() + 10 * att.sum() ** 2 + 0.01 * (p ** 2).sum()

        res = minimize(nll, np.zeros(2 * n + 1), method="L-BFGS-B")
        self.att, self.de, self.home = res.x[:n], res.x[n:2 * n], res.x[-1]
        return self

    def knows(self, team, min_games=5):
        return team in self.idx and self.games.get(team, 0) >= min_games

    def predict(self, home, away, max_goals=10):
        i, j = self.idx[home], self.idx[away]
        lh = np.exp(self.att[i] + self.de[j] + self.home)
        la = np.exp(self.att[j] + self.de[i])
        g = np.arange(max_goals + 1)
        m = np.outer(poisson.pmf(g, lh), poisson.pmf(g, la))
        tot = np.add.outer(g, g)
        return {
            "H": np.tril(m, -1).sum(),
            "D": np.trace(m),
            "A": np.triu(m, 1).sum(),
            "O2.5": m[tot > 2].sum(),
            "U2.5": m[tot <= 2].sum(),
            "xG_home": lh,
            "xG_away": la,
        }
