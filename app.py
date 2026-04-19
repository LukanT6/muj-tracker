import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

# Konfigurace
st.set_page_config(page_title="Invest Tracker Pro", layout="wide")

# Styl
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    h1, h2, h3 { color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'

# Načtení dat se základní kontrolou
def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=['ticker', 'pocet', 'cena_usd', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("➕ Správa")
with st.sidebar.form("add_form", clear_on_submit=True):
    t_input = st.text_input("Ticker (např. AAPL, O)").upper().strip()
    n_input = st.number_input("Počet kusů", min_value=0.0, step=0.1)
    p_input = st.number_input("Nákupní cena ($)", min_value=0.0, step=0.1)
    submit = st.form_submit_button("Uložit")
    if submit and t_input:
        new_row = pd.DataFrame([[t_input, n_input, p_input, pd.Timestamp.now().date()]], 
                               columns=['ticker', 'pocet', 'cena_usd', 'datum'])
        new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
        st.sidebar.success(f"Uloženo!")
        st.rerun()

if st.sidebar.button("🗑️ Vymazat vše"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        st.rerun()

# --- HLAVNÍ ČÁST ---
if not df.empty:
    try:
        st.title("📈 Můj Dashboard")
        portfolio_summary = df.groupby('ticker').agg({'pocet': 'sum'}).reset_index()
        tickers = portfolio_summary['ticker'].tolist()
        
        with st.spinner('Stahuji data...'):
            # Stáhneme kurz koruny
            kurz_data = yf.Ticker("USDCZK=X").history(period="1d")
            kurz = kurz_data['Close'].iloc[-1]
            
            res_list = []
            div_calendar = {i: 0 for i in range(1, 13)}
            mesice_nazvy = {1:'Led', 2:'Úno', 3:'Bře', 4:'Dub', 5:'Kvě', 6:'Čer', 7:'Čvc', 8:'Srp', 9:'Zář', 10:'Říj', 11:'Lis', 12:'Pro'}

            for t in tickers:
                stock = yf.Ticker(t)
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    hodnota_czk = portfolio_summary[portfolio_summary['ticker'] == t]['pocet'].values[0] * curr_p * kurz
                    
                    # Dividendy (jen pokud existují)
                    divs = stock.dividends
                    annual_div_czk = 0
                    if not divs.empty:
                        last_year = divs[divs.index > (datetime.now() - pd.DateOffset(years=1))]
                        for date, amount in last_year.items():
                            val = amount * portfolio_summary[portfolio_summary['ticker'] == t]['pocet'].values[0] * kurz
                            div_calendar[date.month] += val
                            annual_div_czk += val

                    res_list.append({'Ticker': t, 'Hodnota (CZK)': hodnota_czk, 'Roční Divi': annual_div_czk})

            res_df = pd.DataFrame(res_list)
            
            # Zobrazení
            c1, c2 = st.columns(2)
            c1.metric("Celková hodnota", f"{res_df['Hodnota (CZK)'].sum():,.0f} Kč")
            c2.metric("Roční dividendy", f"{res_df['Roční Divi'].sum():,.0f} Kč")

            t1, t2 = st.tabs(["Složení", "Dividendy"])
            with t1:
                st.plotly_chart(px.pie(res_df, values='Hodnota (CZK)', names='Ticker', hole=0.4), use_container_width=True)
            with t2:
                divi_df = pd.DataFrame([{'Měsíc': mesice_nazvy[m], 'Kč': v} for m, v in div_calendar.items()])
                st.plotly_chart(px.bar(divi_df, x='Měsíc', y='Kč'), use_container_width=True)

    except Exception as e:
        st.error(f"Něco se pokazilo: {e}")
else:
    st.info("Portfolio je prázdné. Přidej akcii vlevo.")
