import time
import requests
import streamlit as st

# -------------------------
# Asetukset
# -------------------------
st.set_page_config(page_title="Krypto botti", layout="centered")

BTC_SYMBOL = "BTCUSDT"  # vaihda omaan pörssi-symboliin
PRICE_API = (
    "https://api.binance.com/api/v3/ticker/price?symbol=" + BTC_SYMBOL
)

REFRESH_SECONDS = 2  # hinnan päivitysväli

# -------------------------
# Session state
# -------------------------
if "last_price" not in st.session_state:
    st.session_state.last_price = 0.0
if "prev_price" not in st.session_state:
    st.session_state.prev_price = 0.0
if "position" not in st.session_state:
    st.session_state.position = 0.0  # BTC määrä
if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0.0
if "last_trade_pnl" not in st.session_state:
    st.session_state.last_trade_pnl = 0.0
if "last_trade_side" not in st.session_state:
    st.session_state.last_trade_side = "-"
if "pnl_percent" not in st.session_state:
    st.session_state.pnl_percent = 0.0


# -------------------------
# Hinnan hakufunktio
# -------------------------
def fetch_btc_price() -> float:
    try:
        r = requests.get(PRICE_API, timeout=3)
        r.raise_for_status()
        data = r.json()
        return float(data["price"])
    except Exception:
        return st.session_state.last_price


# -------------------------
# Pää-UI
# -------------------------
st.title("📈 Krypto botti (BTC)")

# Nopea hinnan päivitys
placeholder_price = st.empty()
placeholder_prev = st.empty()

# Pollaa hinta kerran "sivun ajon" aikana
st.session_state.prev_price = st.session_state.last_price
current_price = fetch_btc_price()
st.session_state.last_price = current_price

col_price, col_change = st.columns(2)
with col_price:
    placeholder_price.markdown(
        f"**Hinta nyt**: {current_price:,.2f} USDT"
    )
with col_change:
    if st.session_state.prev_price > 0:
        diff = current_price - st.session_state.prev_price
        diff_pct = diff / st.session_state.prev_price * 100
        color = "green" if diff >= 0 else "red"
        placeholder_prev.markdown(
            f"<span style='color:{color};'>Δ {diff:,.2f} ({diff_pct:+.2f} %)</span>",
            unsafe_allow_html=True,
        )
    else:
        placeholder_prev.markdown("Δ 0.00 (0.00 %)")

st.divider()

# -------------------------
# Osta / Myy napit vierekkäin (mobiili)
# -------------------------
amount = st.number_input(
    "Määrä (BTC)", min_value=0.0, value=0.001, step=0.001, format="%.6f"
)

c1, c2 = st.columns(2)
with c1:
    buy_clicked = st.button("🟢 OSTA", use_container_width=True)
with c2:
    sell_clicked = st.button("🔴 MYY", use_container_width=True)

# Yksinkertainen mock "orderi" – tähän omat API‑kutsut pörssille
def execute_buy(qty: float, price: float):
    # Päivitä position ja entry_price yksinkertaisella logiikalla
    pos = st.session_state.position
    if pos <= 0:
        # Uusi long
        st.session_state.position = qty
        st.session_state.entry_price = price
    else:
        # Lisää longia: painotettu keskihinta
        new_pos = pos + qty
        st.session_state.entry_price = (pos * st.session_state.entry_price + qty * price) / new_pos
        st.session_state.position = new_pos

def execute_sell(qty: float, price: float):
    pos = st.session_state.position
    if pos > 0:
        qty = min(qty, pos)
        # Laske PnL tälle kauppalle
        pnl = (price - st.session_state.entry_price) * qty
        st.session_state.last_trade_pnl = pnl
        st.session_state.last_trade_side = "MYY"
        if pos - qty <= 0:
            st.session_state.position = 0.0
            st.session_state.entry_price = 0.0
        else:
            st.session_state.position = pos - qty
    else:
        # Short‑logiikan voi lisätä tarvittaessa
        pass

# Käsittele nappipainallukset
if buy_clicked and amount > 0:
    execute_buy(amount, current_price)
    st.session_state.last_trade_pnl = 0.0
    st.session_state.last_trade_side = "OSTA"

if sell_clicked and amount > 0:
    execute_sell(amount, current_price)

# -------------------------
# Voittohinta & mittari
# -------------------------
st.subheader("Positio & PnL")

col_pos, col_entry = st.columns(2)
with col_pos:
    st.metric("Positio (BTC)", f"{st.session_state.position:.6f}")
with col_entry:
    ep = st.session_state.entry_price
    st.metric("Entry-hinta", f"{ep:,.2f} USDT" if ep > 0 else "-")

st.write("---")

# Viimeisin kauppa
pnl = st.session_state.last_trade_pnl
side = st.session_state.last_trade_side
if side != "-":
    color = "green" if pnl >= 0 else "red"
    st.markdown(
        f"**Viimeisin kauppa**: {side} @ {current_price:,.2f} USDT – "
        f"<span style='color:{color};'>PnL: {pnl:,.2f} USDT</span>",
        unsafe_allow_html=True,
    )
else:
    st.write("Ei kauppoja vielä.")

# Reaaliaikainen "mittari" – unrealized PnL %
if st.session_state.position > 0 and st.session_state.entry_price > 0:
    upnl = (current_price - st.session_state.entry_price) * st.session_state.position
    upnl_pct = (current_price / st.session_state.entry_price - 1) * 100
else:
    upnl = 0.0
    upnl_pct = 0.0

st.session_state.pnl_percent = upnl_pct

st.markdown("**Mittari (uPnL %)**")

# Skalaa mittari välille 0–100 %
gauge_min = -10
gauge_max = 10
clamped = max(gauge_min, min(gauge_max, upnl_pct))
normalized = (clamped - gauge_min) / (gauge_max - gauge_min)

st.progress(normalized)

st.caption(
    f"uPnL: {upnl:,.2f} USDT ({upnl_pct:+.2f} %)  |  mittarin alue: {gauge_min} % ... {gauge_max} %"
)

# -------------------------
# Automaattinen refresh Streamlitissä
# -------------------------
# Tämä tekee nopeamman hinnan päivityksen ilman manuaalista re
