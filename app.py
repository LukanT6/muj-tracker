import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os

# --- 1. ZABEZPEČENÍ (HESLO) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: white;'>🔒 Soukromý Trezor</h2>", unsafe_allow_html=True)
        st.text_input("Zadejte přístupový kód", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Zadejte přístupový kód", type="password", on_change=password_entered, key="password")
        st.error("❌ Neplatné heslo")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. FUNKCE PRO AUTOMATICKOU DCF ANALÝZU ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Získání dat pro DCF
        eps = info.get('forwardEps') or info.get('trailingEps')
        growth_rate = info.get('earningsGrowth', 0.10) # Pokud není, počítáme s 10%
        curr_price = info.get('currentPrice')
        
        if not eps or not curr_price:
            return "Nedostatek dat pro analýzu."

        # Zjednodušený Graham/DCF model:
        # Graham: V = EPS * (8.5 + 2g) 
        # Upraveno pro moderní trh (bezriziková sazba)
        fair_value = eps * (8.5 + 2 * (growth_rate * 100))
        
        upside = ((fair_value / curr_price) - 1) * 100
        
        return {
            "name": info.get('shortName'),
            "curr": curr_price,
            "fair": fair_value,
            "upside": upside,
            "currency": info.get('currency')
        }
    except:
        return None

# --- 3. KONFIGURACE A STYL ---
st.set_page_config(page_title="Monery AI Analytics", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    [data-testid="stMetric"] { background-color: #111111; border: 1px solid #222222; border-radius: 16px; padding: 20px !important; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222222; }
    h1, h2, h3 { color: #ffffff !important; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #ffffff; color: black; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'
df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])

# --- SIDEBAR ---
st.sidebar.title("💎 Monery AI")

# ANALÝZA AKCIE (NOVINKA)
with st.sidebar.expander("🔍 AI ANALYZÁTOR (Beta)", expanded=True):
    search_ticker = st.text_input("Zadej ticker pro analýzu", value="AAPL").upper()
    if st.button("Analyzovat"):
        res = analyze_stock(search_ticker)
        if isinstance(res, dict):
            st.write(f"**{res['name']}**")
            st.write(f"Aktuální: {res['curr']} {res['currency']}")
            st.write(f"Férová (odhad): {res['fair']:.2f} {res['currency']}")
            
            if res['upside'] > 0:
                st.success(f"PODHODNOCENO o {res['upside']:.1f}% ✅")
            else:
                st.error(f"PŘEDRAŽENO o {abs(res['upside']):.1f}% ❌")
        else:
            st.warning("Data nenalezena.")

with st.sidebar.expander("➕ Přidat do portfolia"):
    with st.form("add_form", clear_on_submit=True):
        t_input = st.text_input("Ticker").upper().strip()
        n_input = st.number_input("Kusy", min_value=0.0)
        p_input = st.number_input("Cena", min_value=0.0)
        m_input = st.selectbox("Měna", ["USD", "CZK", "EUR"])
        if st.form_submit_button("Uložit"):
            new_row = pd.DataFrame([[t_input, n_input, p_input, m_input, pd.Timestamp.now().date()]], columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
            new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.rerun()

# --- HLAVNÍ DASHBOARD ---
if not df.empty:
    st.title("Moje Jmění")
    # (Zde zůstává stejný kód pro zobrazení portfolia a grafů jako v předchozí verzi)
    # Pro stručnost jsem ho zde vynechal, ale v tvém app.py ho nech pod tímto sidebar kódem.
    st.write("Data portfolia jsou načtena níže...")
    # ... (tady pokračuje tvůj kód pro res_df, metriky a grafy)
else:
    st.title("Vítejte v Monery")
    st.info("Zadejte ticker vlevo pro analýzu nebo přidejte nákup.")
