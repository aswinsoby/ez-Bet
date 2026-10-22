"""EZ Bet — daily football value picks + bet tracker.   Run:  streamlit run app.py"""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import config as C
import main as core
import tracker as T
from model import PoissonModel

st.set_page_config(page_title="EZ Bet", page_icon="⚽", layout="wide")


# ---------- cached data ----------
@st.cache_data(ttl=3 * 3600, show_spinner=False)
def get_fixtures():
    return core.read_csv(f"{core.BASE}/fixtures.csv")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def get_history(div, day):
    return core.load_history(div, day)


@st.cache_resource(ttl=12 * 3600, show_spinner=False)
def get_model(div, day):
    hist = get_history(div, day)
    return PoissonModel(C.TIME_DECAY).fit(hist) if not hist.empty else None


def bets():
    if "bets" not in st.session_state:
        st.session_state.bets = T.load()
    return st.session_state.bets


# ---------- sidebar ----------
st.sidebar.title("⚙️ Settings")
leagues = st.sidebar.multiselect("Leagues", list(C.LEAGUES), default=list(C.LEAGUES),
                                 format_func=lambda k: C.LEAGUES[k])
days = st.sidebar.slider("Days ahead", 1, 7, 1)
risk = st.sidebar.radio("Risk level", ["Low", "Medium", "High"], index=0, horizontal=True)
preset = {"Low": (0.60, 1.30, 2.00), "Medium": (0.55, 1.30, 2.50), "High": (0.45, 1.50, 3.50)}[risk]
C.MIN_PROB, C.MIN_ODDS, C.MAX_ODDS = preset
C.MIN_EDGE = st.sidebar.slider("Min edge (%)", 0, 15, int(C.MIN_EDGE * 100)) / 100
start_bank = st.sidebar.number_input("Starting bankroll (£)", 10.0, 100000.0, C.BANKROLL, step=10.0)
C.MAX_PICKS = st.sidebar.slider("Max picks", 1, 10, C.MAX_PICKS)
st.sidebar.caption(f"Min chance {preset[0]:.0%} · odds {preset[1]}–{preset[2]}")

stt = T.stats(bets())
C.BANKROLL = max(start_bank + stt["profit"], 1.0)   # stakes follow your current bankroll
st.sidebar.metric("Current bankroll", f"£{C.BANKROLL:.2f}", f"{stt['profit']:+.2f}")

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.cache_resource.clear()

# ---------- header ----------
st.title("⚽ EZ Bet")
st.caption("Daily value picks: team-strength model vs bookmaker odds. 18+ · BeGambleAware.org")
today = date.today()
end = today + timedelta(days=days - 1)

tab_picks, tab_bets, tab_all = st.tabs(["🎯 Picks", "📒 My Bets", "📊 Full analysis"])

# ---------- analyse ----------
full, picks, load_error = pd.DataFrame(), pd.DataFrame(), None
try:
    fx = get_fixtures()
    fx = fx[fx.Div.isin(leagues) & fx.Date.dt.date.between(today, end)]
    frames = []
    with st.spinner("Analysing matches..."):
        for div, games in fx.groupby("Div"):
            model = get_model(div, today)
            if model is not None:
                frames.append(core.analyse(games, model))
    full = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    picks = core.pick(full)
except Exception as e:
    load_error = str(e)

# ---------- picks tab ----------
with tab_picks:
    if load_error:
        st.error(f"Couldn't load data: {load_error}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Matches analysed", full["match"].nunique() if not full.empty else 0)
    c2.metric("Picks", len(picks))
    c3.metric("Total stake", f"£{picks.stake_gbp.sum():.2f}" if not picks.empty else "£0")

    if picks.empty:
        st.success("No picks pass your filters. Skipping a day is a win too.")
    else:
        tracked = set(bets().id)
        if st.button("➕ Track all picks", type="primary"):
            n = 0
            for _, p in picks.iterrows():
                st.session_state.bets, ok = T.add(bets(), p)
                n += ok
            st.toast(f"Added {n} bets to My Bets")
            st.rerun()
        for k, p in picks.reset_index(drop=True).iterrows():
            bid = f"{p['date']}_{p['div']}_{p['home']}_{p['away']}_{p['market']}"
            with st.container(border=True):
                a, b, c, d = st.columns([3, 1, 1, 1])
                a.markdown(f"**{p.pick}**  \n{p.match} · {p.league} · {p.date} {p.time}")
                b.metric("Best odds", f"{p.best_odds:.2f}")
                c.metric("Chance", f"{p.prob:.0%}")
                d.metric("Stake", f"£{p.stake_gbp:.2f}", f"+{p.edge:.0%} EV")
                if bid in tracked:
                    st.caption("✅ Tracked")
                else:
                    s1, s2 = st.columns([1, 1])
                    stake = s1.number_input("Your stake £", 0.0, 10000.0, float(p.stake_gbp),
                                            step=0.5, key=f"stk{k}")
                    if s2.button("➕ Track", key=f"trk{k}"):
                        st.session_state.bets, _ = T.add(bets(), p, stake)
                        st.rerun()

# ---------- my bets tab ----------
with tab_bets:
    df = bets()
    if st.button("⚡ Settle finished matches"):
        divs = df.loc[df.status == "Pending", "div"].dropna().unique()
        res = {d: get_history(d, today) for d in divs}
        st.session_state.bets, n = T.settle(df, res)
        st.toast(f"Settled {n} bets" if n else "No new results yet (data updates a few times a week)")
        st.rerun()

    s = T.stats(df)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bets", s["bets"], f"{s['pending']} pending", delta_color="off")
    m2.metric("Win rate", f"{s['win_rate']:.0%}")
    m3.metric("Profit", f"£{s['profit']:.2f}")
    m4.metric("ROI", f"{s['roi']:+.1%}")

    if df.empty:
        st.info("No bets yet. Track picks from the Picks tab.")
    else:
        done = df[df.status.isin(["Won", "Lost"])].sort_values("date")
        if len(done) > 1:
            st.line_chart(done.assign(n=range(1, len(done) + 1)).set_index("n").profit.cumsum(),
                          y_label="Profit £", x_label="Bet #")
        st.caption("Edit status/stake if needed (e.g. settle manually or mark Void), then save.")
        edited = st.data_editor(
            df.sort_values("date", ascending=False)[["id", "date", "match", "pick", "odds", "stake",
                                                     "status", "result", "profit"]],
            column_config={"id": None,
                           "status": st.column_config.SelectboxColumn(options=T.STATUSES),
                           "profit": st.column_config.NumberColumn(disabled=True, format="£%.2f")},
            disabled=["date", "match", "pick", "odds"], hide_index=True, width="stretch", key="editor")
        b1, b2, b3 = st.columns(3)
        if b1.button("💾 Save changes"):
            upd = df.set_index("id")
            e = edited.set_index("id")
            upd.loc[e.index, ["stake", "status", "result"]] = e[["stake", "status", "result"]]
            st.session_state.bets = T.save(upd.reset_index())
            st.toast("Saved")
            st.rerun()
        b2.download_button("⬇️ Backup bets", df.to_csv(index=False), "ezbet_bets.csv", "text/csv")
        if b3.button("🗑️ Delete pending"):
            st.session_state.bets = T.save(df[df.status != "Pending"])
            st.rerun()

    up = st.file_uploader("Restore from backup (ezbet_bets.csv)", type="csv")
    if up is not None and st.button("Restore"):
        st.session_state.bets = T.save(pd.read_csv(up, dtype={"date": str}))
        st.toast("Restored")
        st.rerun()

# ---------- full analysis tab ----------
with tab_all:
    if full.empty:
        st.info("Nothing to show.")
    else:
        st.dataframe(full.drop(columns=["div", "home", "away", "market"])
                         .assign(prob=(full.prob * 100).round(1), edge=(full.edge * 100).round(1))
                         .rename(columns={"prob": "chance %", "edge": "edge %"}),
                     width="stretch", hide_index=True)

st.caption("Odds update a few times a week. Check live odds, injuries and lineups before betting.")
