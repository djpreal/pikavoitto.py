import time
import requests
import streamlit as st

# --- SIMULAATIO-STATE ---

if "wallet_usdc" not in st.session_state:
    st.session_state.wallet_usdc = 2000.0
    st.session_state.position_btc = 0.0
    st.session_state.entry_price = None
    st.session_state.current_price = 30000.0
    st.session_state.realized_pnl = 0.0
    st.session_state.stake_presets = [100, 500, 1000, 1500, 2000]
    st.session_state.stake_index = 0
    st.session_state.current_stake_usdc = st.session_state.stake_presets[0]
    st.session_state.locked_stake_usdc = None

# --- API ---

def update_price_from_api():
    try:
        resp = requests.get(
            "https://api.mexc.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            price = float(data["price"])
            if price > 0:
                st.session_state.current_price = price
    except Exception as e:
        st.warning(f"API error: {e}")

# --- LOGIIKKA ---

def on_stake_button():
    s = st.session_state
    s.stake_index = (s.stake_index + 1) % len(s.stake_presets)
    s.current_stake_usdc = s.stake_presets[s.stake_index]

def on_buy(fraction: float):
    s = st.session_state
    if s.wallet_usdc <= 0 or s.current_price <= 0:
        return

    if s.position_btc == 0 or s.entry_price is None:
        s.locked_stake_usdc = s.current_stake_usdc

    stake = s.locked_stake_usdc if s.locked_stake_usdc is not None else s.current_stake_usdc
    amount_usdc = min(stake * fraction, s.wallet_usdc)
    if amount_usdc <= 0:
        return

    btc_amount = amount_usdc / s.current_price

    if s.position_btc == 0 or s.entry_price is None:
        s.entry_price = s.current_price
    else:
        total_value_old = s.position_btc * s.entry_price
        total_value_new = total_value_old + amount_usdc
        s.entry_price = total_value_new / (s.position_btc + btc_amount)

    s.position_btc += btc_amount
    s.wallet_usdc -= amount_usdc

def on_sell(fraction: float):
    s = st.session_state
    if s.position_btc <= 0 or s.entry_price is None or s.current_price <= 0:
        return

    stake = s.locked_stake_usdc if s.locked_stake_usdc is not None else s.current_stake_usdc
    btc_for_full_stake = stake / s.current_price
    btc_to_sell = min(btc_for_full_stake * fraction, s.position_btc)
    if btc_to_sell <= 0:
        return

    usdc_got = btc_to_sell * s.current_price
    realized = (s.current_price - s.entry_price) * btc_to_sell
    s.realized_pnl += realized

    s.position_btc -= btc_to_sell
    s.wallet_usdc += usdc_got

    if s.position_btc <= 1e-8:
        s.position_btc = 0.0
        s.entry_price = None
        s.locked_stake_usdc = None

def on_reset():
    s = st.session_state
    s.realized_pnl = 0.0

def compute_pnl():
    s = st.session_state
    if s.position_btc == 0 or s.entry_price is None:
        return 0.0
    return (s.current_price - s.entry_price) * s.position_btc

# --- UI ---

st.set_page_config(page_title="BTC/USDC Kryptobotti", layout="centered")

st.title("BTC/USDC Kryptobotti (Streamlit)")

# Hinta
update_price_from_api()
st.metric("BTC/USDC hinta", f"{st.session_state.current_price:,.2f} USDC")

# VOITTO-mittari
pnl = compute_pnl()
pnl_color = "white"
pnl_text = f"VOITTO 0.00 USDC"
if pnl > 0:
    pnl_color = "lime"
    pnl_text = f"VOITTO +{pnl:,.2f} USDC"
elif pnl < 0:
    pnl_color = "red"
    pnl_text = f"VOITTO {pnl:,.2f} USDC"

st.markdown(
    f"<h3 style='text-align:center;color:{pnl_color};'>{pnl_text}</h3>",
    unsafe_allow_html=True,
)

# Mittari progressbarilla (skaalataan -100..100 -> 0..100)
sensitivity = 0.40
if pnl != 0:
    step_per_0_40 = 5
    value = int((pnl / sensitivity) * step_per_0_40)
else:
    value = 0
value = max(-100, min(100, value))
bar_val = int((value + 100) / 2)  # 0..100

st.progress(bar_val)

# Lompakko + panos
col1, col2 = st.columns(2)
with col1:
    st.write(
        f"**Lompakko:** {st.session_state.wallet_usdc:,.2f} USDC | "
        f"{st.session_state.position_btc:.6f} BTC"
    )
with col2:
    st.write(f"**Panos:** {st.session_state.current_stake_usdc:,.2f} USDC")
    if st.button("PANOS"):
        on_stake_button()
        st.experimental_rerun()

# OSTA / MYY napit
col_buy, col_sell = st.columns(2)

with col_buy:
    st.subheader("OSTA")
    if st.button("OSTA 100%"):
        on_buy(1.0)
        st.experimental_rerun()
    if st.button("OSTA 50%"):
        on_buy(0.5)
        st.experimental_rerun()
    if st.button("OSTA 10%"):
        on_buy(0.1)
        st.experimental_rerun()

with col_sell:
    st.subheader("MYY")
    if st.button("MYY 100%"):
        on_sell(1.0)
        st.experimental_rerun()
    if st.button("MYY 50%"):
        on_sell(0.5)
        st.experimental_rerun()
    if st.button("MYY 10%"):
        on_sell(0.1)
        st.experimental_rerun()

# Session voitot
sess = st.session_state.realized_pnl
sess_color = "white"
sess_text = "VOITOT: 0.00 USDC"
if sess > 0:
    sess_color = "#FFD700"
    sess_text = f"VOITOT: +{sess:,.2f} USDC"
elif sess < 0:
    sess_color = "#FF4C4C"
    sess_text = f"VOITOT: {sess:,.2f} USDC"

st.markdown(
    f"<h3 style='text-align:center;color:{sess_color};'>{sess_text}</h3>",
    unsafe_allow_html=True,
)

if st.button("RESET"):
    on_reset()
    st.experimental_rerun()
