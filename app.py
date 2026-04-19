import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

# --- 1. ZABEZPEČENÍ (HESLO) ---
def check_password():
    """Vrací True, pokud uživatel zadal správné heslo."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Odstraní heslo ze stavu
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # První spuštění, zobrazíme formulář
        st.markdown("<h2 style='text-align: center;'>🔒 Soukromé Portfolio</h2>", unsafe_allow_html=True)
        st.text_input("Zadejte přístupový kód", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Špatné heslo
        st.text_input("Zadejte přístupový kód", type="password", on_change=password_entered, key="password")
        st.error("❌ Neplatné heslo")
        return False
    else:
        # Heslo je správně
        return True

if not check_password():
    st.stop() # Zastaví vykonávání kódu, dokud není heslo OK

# --- 2. KONFIGURACE A MONERY DESIGN ---
st.set_page_config(page_title="Monery Tracker", layout="wide")

st.markdown("""
    <style>
    /* Monery Style: Pitch Black & Soft Grey */
    .main { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: #000000; }
    
    /* Karty s metrikami */
    [data-testid="stMetric"] {
        background-color: #111111;
        border: 1px solid #222222;
        border-radius: 16px;
        padding: 25px !important;
    }
    
    /* Custom tabulky a okraje */
    .stDataFrame { border: 1px solid #222222; border-radius: 12px; }
    
    /* Fonty */
    html, body, [class*="css"]  {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    h1, h2, h3 { font-weight: 700; letter-spacing: -1px; color: #ffffff !important; }
    
    /* Vylepšení bočního panelu */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222222; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'

def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- SIDEBAR (Správa) ---
st.sidebar.markdown("### 🛠️ Nastavení")
with st.sidebar.expander("➕ Přidat pozici"):
    with st.form("add_form", clear_on_submit=True):
        t_input = st.text_input("Ticker").upper().strip()
        n_input = st.number_input("Kusy", min_value=0.0)
        p_input = st.number_input("Nákupní cena", min_value=0.0)
        m_input = st.selectbox("Měna", ["CZK", "USD", "EUR"])
        if st.form_submit_button("Uložit"):
            if t_input:
                new_row = pd.DataFrame([[t_input, n_input, p_input, m_input, pd.Timestamp.now().date()]], 
                                       columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
                new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
                st.rerun()

if st.sidebar.button("🗑️ Resetovat data"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE); st.rerun()

# --- VÝPOČTY (Jádro zůstává stejné) ---
if not df.empty:
    try:
        summary = df.groupby(['ticker', 'mena']).agg({'pocet': 'sum', 'cena': 'mean'}).reset_index()
        tickers = summary['ticker'].unique().tolist()
        
        with st.spinner('Aktualizuji...'):
            kurzy = yf.download(["USDCZK=X", "EURCZK=X"], period="1d")['Close']
            usd_czk = kurzy["USDCZK=X"].iloc[-1]
            eur_czk = kurzy["EURCZK=X"].iloc[-1]
            get_rate = {"CZK": 1.0, "USD": usd_czk, "EUR": eur_czk}

            res_list = []
            div_calendar = {i: 0 for i in range(1, 13)}
            mesice_nazvy = {1:'LED', 2:'ÚNO', 3:'BŘE', 4:'DUB', 5:'KVĚ', 6:'ČER', 7:'ČVC', 8:'SRP', 9:'ZÁŘ', 10:'ŘÍJ', 11:'LIS', 12:'PRO'}
            now = pd.Timestamp.now(tz=None)

            for t in tickers:
                stock = yf.Ticker(t)
                hist = stock.history(period="2d")
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    market_curr = stock.info.get('currency', 'USD')
                    rate_to_czk = get_rate.get(market_curr, 1.0)
                    
                    t_rows = summary[summary['ticker'] == t]
                    for _, row in t_rows.iterrows():
                        val_czk = row['pocet'] * curr_p * rate_to_czk
                        # Výpočet dividend
                        divs = stock.dividends
                        annual_div = 0
                        if not divs.empty:
                            divs.index = divs.index.tz_localize(None)
                            last_year = divs[divs.index > (now - pd.DateOffset(years=1))]
                            for date, amount in last_year.items():
                                d_czk = amount * row['pocet'] * rate_to_czk
                                div_calendar[date.month] += d_czk
                                annual_div += d_czk

                        res_list.append({
                            'Ticker': t, 'Hodnota': val_czk, 'Dividenda': annual_div
                        })

            res_df = pd.DataFrame(res_list)

            # --- VIZUALIZACE ---
            st.title("My Wealth")
            
            c1, c2 = st.columns(2)
            c1.metric("Total Balance", f"{res_df['Hodnota'].sum():,.0f} Kč")
            c2.metric("Est. Yearly Income", f"{res_df['Dividenda'].sum():,.0f} Kč")

            st.markdown("### Allocation")
            fig = px.pie(res_df, values='Hodnota', names='Ticker', hole=0.7,
                         color_discrete_sequence=['#ffffff', '#333333', '#555555', '#777777', '#999999'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                              font_color='white', margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### Dividend Flow")
            divi_plot = pd.DataFrame([{'Month': mesice_nazvy[m], 'CZK': v} for m, v in div_calendar.items()])
            fig_bar = px.bar(divi_plot, x='Month', y='CZK')
            fig_bar.update_traces(marker_color='#ffffff')
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.title("Wealth Tracker")
    st.info("No assets found. Add your first position in the sidebar.")
