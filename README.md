# ⚽ EZ Bet

Daily football value picks + bet tracker. Free data from football-data.co.uk (no API key).

## Files
| File | What it does |
|---|---|
| `app.py` | The EZ Bet app (Streamlit) |
| `main.py` | Data loading + match analysis + pick filter (also runs as a command-line script) |
| `model.py` | Poisson team-strength model (attack/defence, home advantage, recent form) |
| `tracker.py` | Saves your bets to `bets.csv`, auto-settles them, works out profit/ROI |
| `config.py` | Default leagues, filters, staking |
| `requirements.txt` | Python packages |

## 1. Install (once)
```
cd ez-bet
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

## 2. Run
```
streamlit run app.py
```
Opens at http://localhost:8501. First load takes ~30s (downloads 2 seasons per league); after that it's cached.

## 3. Daily routine (2 minutes)
1. Open EZ Bet → **Picks** tab.
2. Check each pick on FotMob (lineups, injuries) and check the odds at your bookie are still close to "Best odds".
3. Place the bet yourself, then hit **➕ Track** (edit the stake first if you bet a different amount).
4. Next day(s): **My Bets** → **⚡ Settle finished matches**. Wins/losses fill in automatically.
   - Results data updates a few times a week, so some bets stay Pending for 1–3 days. You can also set the status yourself in the table and hit **💾 Save changes**.
5. Weekends: set **Days ahead** to 3 on Friday.

## Settings (sidebar)
- **Risk level**: Low = ≥60% chance, odds 1.30–2.00 · Medium = ≥55%, 1.30–2.50 · High = ≥45%, 1.50–3.50
- **Min edge**: how much better than fair the odds must be (3% default)
- **Starting bankroll**: stakes use quarter-Kelly, capped at 2% of your *current* bankroll (starting + profit)

## 4. Use it on your phone
**Same Wi-Fi:** run it on your laptop, open the *Network URL* Streamlit prints (e.g. `http://192.168.1.20:8501`) on your phone.

**Anywhere (free hosting):**
1. Put the folder in a **private** GitHub repo.
2. Go to share.streamlit.io → New app → pick the repo → main file `app.py` → Deploy.
3. On your phone open the link → browser menu → **Add to Home Screen**. Now it opens like an app.

⚠️ On Streamlit Cloud, `bets.csv` is wiped when the app restarts or sleeps. Hit **⬇️ Backup bets** after tracking/settling, and use **Restore** to load it back. (Running on your own laptop keeps it permanently.)

## Good habits
- Track every bet, including losers. The ROI number only means something after 100+ bets.
- If ROI is negative after ~150 bets, raise **Min edge** or use **Low** risk.
- Only bet money you're fine losing. 18+ · BeGambleAware.org
