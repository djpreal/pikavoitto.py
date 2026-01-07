import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Krypto botti", layout="centered")

BTC_SYMBOL = "BTCUSDT"
PRICE_API = f"https://api.binance.com/api/v3/ticker/price?symbol={BTC_SYMBOL}"
REFRESH_MS = 2000  # 2s

# Automaattinen refresh
st_autorefresh(interval=REFRESH_MS, key="price_refresh")

# Session state
if "last_price" not in st.session_state:
    st.session_state.last_price = 0.0
if "prev_price" not in st.session_state:
    st.session_state.prev_price = 0.0
if "position" not in st.session_state:
    st.session_state.position = 0.0
if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0.0
if "last_trade_pnl" not in st.session_state:
    st.session_state.last_trade_pnl = 0.0
if "last_trade_side" not in st.session_state:
    st.session_state.last_trade_side = "-"
if "pnl_percent" not in st.session_state:
    st.session_state.pnl_percent = 0.0


def fetch_btc_price() -> float:
    try:
        r = requests.get(PRICE_API, timeout=3)
        r.raise_for_status()
        data = r.json()
        return float(data["price"])
    except Exception:
        return st.session_state.last_price


st.title("📈 Krypto botti (BTC)")

# Päivitä hinta joka ajolla
st.session_state.prev_price = st.session_state.last_price
price = fetch_btc_price()
st.session_state.last_price = price

col_price, col_change = st.columns(2)
with col_price:
    st.markdown(f"**Hinta nyt**: {price:,.2f} USDT")
with col_change:
    if st.session_state.prev_price > 0:
        diff = price - st.session_state.prev_price
        diff_pct = diff / st.session_state.prev_price * 100
        color = "green" if diff >= 0 else "red"
        st.markdown(
            f"<span style='color:{color};'>Δ {diff:,.2f} ({diff_pct:+.2f} %)</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("Δ 0.00 (0.00 %)")

st.divider()

# PANOS = määrä BTC
amount = st.number_input(
    "Määrä (BTC)", min_value=0.0, value=0.001, step=0.001, format="%.6f"
)

# Napit vierekkäin (mobiili)
c1, c2 = st.columns(2)
with c1:
    buy_clicked = st.button("🟢 OSTA", use_container_width=True)
with c2:
    sell_clicked = st.button("🔴 MYY", use_container_width=True)


def execute_buy(qty: float, price: float):
    pos = st.session_state.position
    if pos <= 0:
        st.session_state.position = qty
        st.session_state.entry_price = price
    else:
        new_pos = pos + qty
        st.session_state.entry_price = (
            pos * st.session_state.entry_price + qty * price
        ) / new_pos
        st.session_state.position = new_pos


def execute_sell(qty: float, price: float):
    pos = st.session_state.position
    if pos > 0:
        qty = min(qty, pos)
        pnl = (price - st.session_state.entry_price) * qty
        st.session_state.last_trade_pnl = pnl
        st.session_state.last_trade_side = "MYY"
        if pos - qty <= 0:
            st.session_state.position = 0.0
            st.session_state.entry_price = 0.0
        else:
            st.session_state.position = pos - qty


if buy_clicked and amount > 0:
    execute_buy(amount, price)
    st.session_state.last_trade_pnl = 0.0
    st.session_state.last_trade_side = "OSTA"

if sell_clicked and amount > 0:
    execute_sell(amount, price)

# Voittohinta + mittari
st.subheader("Positio & PnL")

col_pos, col_entry = st.columns(2)
with col_pos:
    st.metric("Positio (BTC)", f"{st.session_state.position:.6f}")
with col_entry:
    ep = st.session_state.entry_price
    st.metric("Entry-hinta", f"{ep:,.2f} USDT" if ep > 0 else "-")

pnl = st.session_state.last_trade_pnl
side = st.session_state.last_trade_side
if side != "-":
    color = "green" if pnl >= 0 else "red"
    st.markdown(
        f"**Viimeisin kauppa**: {side} @ {price:,.2f} USDT – "
        f"<span style='color:{color};'>PnL: {pnl:,.2f} USDT</span>",
        unsafe_allow_html=True,
    )
else:
    st.write("Ei kauppoja vielä.")

if st.session_state.position > 0 and st.session_state.entry_price > 0:
    upnl = (price - st.session_state.entry_price) * st.session_state.position
    upnl_pct = (price / st.session_state.entry_price - 1) * 100
else:
    upnl = 0.0
    upnl_pct = 0.0

st.session_state.pnl_percent = upnl_pct

st.markdown("**Mittari (uPnL %)**")

gauge_min = -10
gauge_max = 10
clamped = max(gauge_min, min(gauge_max, upnl_pct))
normalized = (clamped - gauge_min) / (gauge_max - gauge_min)

st.progress(normalized)
st.caption(
    f"uPnL: {upnl:,.2f} USDT ({upnl_pct:+.2f} %)  |  mittarin alue: {gauge_min} % ... {gauge_max} %"
)
