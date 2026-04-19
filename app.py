import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

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

# --- 2. FUNKCE PRO AI ANALÝZU ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        eps = info.get('forwardEps') or info.get('trailingEps')
        growth_rate = info.get('earningsGrowth', 0.10)
        curr_price = info.get('currentPrice')
        if not eps or not curr_price: return "Nedostatek dat."
        fair_value = eps * (8.5 + 2 * (growth_rate * 100))
        upside = ((fair_value / curr_price) - 1) * 100
        return {"name": info.get('shortName'), "curr": curr_price, "fair": fair_value, "upside": upside, "currency": info.get('currency')}
    except: return None

# --- 3. KONFIGURACE A STYL ---
st.set_page_config(page_title="Monery Wealth", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: #000000; }
    [data-testid="stMetric"] { background-color: #111111; border: 1px solid #222222; border-radius: 16px; padding: 20px !important; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222222; }
    .stTabs [data-baseweb="tab-list"] { background-color: #000000; }
    h1, h2, h3 { color: #ffffff !important; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #ffffff; color: black; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'
def load_data():
    if not os.path.exists(DB_FILE): return pd.DataFrame(columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- 4. SIDEBAR ---
st.sidebar.title("💎 Monery AI")
with st.sidebar.expander("🔍 AI ANALYZÁTOR", expanded=True):
    search_t = st.text_input("Ticker pro analýzu", value="AAPL").upper()
    if st.button("Analyzovat"):
        res = analyze_stock(search_t)
        if isinstance(res, dict):
            st.write(f"**{res['name']}**")
            st.write(f"Cena: {res['curr']} {res['currency']}")
            st.write(f"Férová: {res['fair']:.2f}")
            if res['upside'] > 0: st.success(f"PODHODNOCENO o {res['upside']:.1f}% ✅")
            else: st.error(f"PŘEDRAŽENO o {abs(res['upside']):.1f}% ❌")

with st.sidebar.expander("➕ Přidat nákup"):
    with st.form("add_form", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        n_in = st.number_input("Kusy", min_value=0.0)
        p_in = st.number_input("Cena", min_value=0.0)
        m_in = st.selectbox("Měna", ["USD", "CZK", "EUR"])
        if st.form_submit_button("Uložit"):
            new_r = pd.DataFrame([[t_in, n_in, p_in, m_in, pd.Timestamp.now().date()]], columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
            new_r.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.rerun()

if st.sidebar.button("🗑️ Resetovat portfolio"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE); st.rerun()

# --- 5. HLAVNÍ ČÁST (VÝPOČTY A GRAFY) ---
if not df.empty:
    try:
        summary = df.groupby(['ticker', 'mena']).agg({'pocet': 'sum', 'cena': 'mean'}).reset_index()
        tickers = summary['ticker'].unique().tolist()
        
        with st.spinner('Aktualizuji...'):
            kurzy = yf.download(["USDCZK=X", "EURCZK=X"], period="1d")['Close']
            usd_czk, eur_czk = kurzy["USDCZK=X"].iloc[-1], kurzy["EURCZK=X"].iloc[-1]
            get_rate = {"CZK": 1.0, "USD": usd_czk, "EUR": eur_czk}

            res_list = []
            div_calendar_sum = {i: 0 for i in range(1, 13)}
            div_details = [] # Seznam pro detailní rozpis
            mesice = {1:'LED', 2:'ÚNO', 3:'BŘE', 4:'DUB', 5:'KVĚ', 6:'ČER', 7:'ČVC', 8:'SRP', 9:'ZÁŘ', 10:'ŘÍJ', 11:'LIS', 12:'PRO'}

            for t in tickers:
                stock = yf.Ticker(t)
                hist = stock.history(period="2d")
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    rate_czk = get_rate.get(stock.info.get('currency', 'USD'), 1.0)
                    for _, row in summary[summary['ticker'] == t].iterrows():
                        v_czk = row['pocet'] * curr_p * rate_czk
                        divs = stock.dividends
                        a_div = 0
                        if not divs.empty:
                            divs.index = divs.index.tz_localize(None)
                            last_yr = divs[divs.index > (pd.Timestamp.now() - pd.DateOffset(years=1))]
                            for date, amount in last_yr.items():
                                d_czk = amount * row['pocet'] * rate_czk
                                div_calendar_sum[date.month] += d_czk
                                a_div += d_czk
                                # Uložíme informaci o konkrétní výplatě
                                div_details.append({
                                    'Měsíc': mesice[date.month],
                                    'Akcie': t,
                                    'Částka (Kč)': d_czk
                                })
                        res_list.append({'Ticker': t, 'Hodnota': v_czk, 'Dividenda': a_div})

            res_df = pd.DataFrame(res_list)
            st.title("Moje Jmění")
            c1, c2 = st.columns(2)
            c1.metric("Celková hodnota", f"{res_df['Hodnota'].sum():,.0f} Kč")
            c2.metric("Roční dividendy", f"{res_df['Dividenda'].sum():,.0f} Kč")

            t1, t2 = st.tabs(["💰 Portfolio", "📅 Kalendář"])
            with t1:
                fig = px.pie(res_df, values='Hodnota', names='Ticker', hole=0.7, color_discrete_sequence=['#ffffff', '#222222', '#444444', '#666666'])
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(res_df, hide_index=True, use_container_width=True)
            with t2:
                # Graf měsíčních příjmů
                d_plot = pd.DataFrame([{'Měsíc': mesice[m], 'Kč': v} for m, v in div_calendar_sum.items()])
                fig_b = px.bar(d_plot, x='Měsíc', y='Kč')
                fig_b.update_traces(marker_color='#ffffff').update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_b, use_container_width=True)
                
                # NOVINKA: Detailní rozpis akcií podle měsíců
                if div_details:
                    st.markdown("### Detail výplat")
                    detail_df = pd.DataFrame(div_details)
                    # Seskupíme podle měsíce a akcie (kdyby jedna akcie platila vícekrát za měsíc)
                    detail_df = detail_df.groupby(['Měsíc', 'Akcie']).sum().reset_index()
                    # Seřadíme podle pořadí měsíců
                    mesice_order = list(mesice.values())
                    detail_df['Měsíc'] = pd.Categorical(detail_df['Měsíc'], categories=mesice_order, ordered=True)
                    detail_df = detail_df.sort_values('Měsíc')
                    
                    st.dataframe(detail_df, hide_index=True, use_container_width=True)
                else:
                    st.info("Žádné dividendy k zobrazení.")
                    
    except Exception as e: st.error(f"Chyba: {e}")
else:
    st.title("Vítejte v Monery")
    st.info("Přidejte nákup vlevo.")
