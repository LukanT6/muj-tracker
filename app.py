import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

# --- KONFIGURACE A STYL ---
st.set_page_config(page_title="Multi-Currency Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px 10px; }
    h1, h2, h3 { color: #58a6ff !important; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'

def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Správa")
with st.sidebar.expander("➕ Přidat nákup", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        t_input = st.text_input("Ticker (např. CEZ.PR, AAPL, MC.PA)").upper().strip()
        n_input = st.number_input("Počet kusů", min_value=0.0, step=0.1)
        p_input = st.number_input("Nákupní cena za kus", min_value=0.0, step=0.1)
        m_input = st.selectbox("Měna nákupu", ["CZK", "USD", "EUR"])
        submit = st.form_submit_button("Uložit")
        if submit and t_input:
            new_row = pd.DataFrame([[t_input, n_input, p_input, m_input, pd.Timestamp.now().date()]], 
                                   columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
            new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.rerun()

if st.sidebar.button("🗑️ Smazat vše"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE); st.rerun()

# --- VÝPOČTY ---
if not df.empty:
    try:
        # Agregace (bereme průměrnou cenu nákupu)
        summary = df.groupby(['ticker', 'mena']).agg({'pocet': 'sum', 'cena': 'mean'}).reset_index()
        tickers = summary['ticker'].unique().tolist()
        
        with st.spinner('Aktualizuji kurzy a ceny...'):
            # Získání kurzů
            kurzy = yf.download(["USDCZK=X", "EURCZK=X"], period="1d")['Close']
            usd_czk = kurzy["USDCZK=X"].iloc[-1]
            eur_czk = kurzy["EURCZK=X"].iloc[-1]
            get_rate = {"CZK": 1.0, "USD": usd_czk, "EUR": eur_czk}

            res_list = []
            now = pd.Timestamp.now(tz=None)

            for t in tickers:
                stock = yf.Ticker(t)
                info = stock.info
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    # V jaké měně se akcie obchoduje na burze?
                    market_curr = info.get('currency', 'USD') 
                    
                    # Data pro tento ticker z naší tabulky
                    t_rows = summary[summary['ticker'] == t]
                    for _, row in t_rows.iterrows():
                        # Přepočet aktuální hodnoty do CZK
                        val_czk = row['pocet'] * curr_p * get_rate.get(market_curr, 1.0)
                        
                        # Přepočet nákupní ceny do CZK (pro výpočet zisku)
                        buy_czk = row['pocet'] * row['cena'] * get_rate.get(row['mena'], 1.0)
                        profit_czk = val_czk - buy_czk
                        profit_pct = (profit_czk / buy_czk) * 100 if buy_czk != 0 else 0

                        res_list.append({
                            'Ticker': t,
                            'Kusy': row['pocet'],
                            'Tržní cena': f"{curr_p:.2f} {market_curr}",
                            'Hodnota (CZK)': val_czk,
                            'Zisk/Ztráta': f"{profit_pct:+.2f} %",
                            'Měna nákupu': row['mena']
                        })

            res_df = pd.DataFrame(res_list)

            # --- ZOBRAZENÍ ---
            st.title("📈 Multi-Currency Portfolio")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Celková hodnota", f"{res_df['Hodnota (CZK)'].sum():,.0f} Kč")
            c2.metric("Kurz USD", f"{usd_czk:.2f} Kč")
            c3.metric("Kurz EUR", f"{eur_czk:.2f} Kč")

            st.markdown("---")
            t1, t2 = st.tabs(["📊 Přehled", "📝 Detailní data"])
            
            with t1:
                col_left, col_right = st.columns([1, 1])
                with col_left:
                    fig = px.pie(res_df, values='Hodnota (CZK)', names='Ticker', hole=0.6,
                                 color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig, use_container_width=True)
                with col_right:
                    st.subheader("Výkonnost")
                    st.dataframe(res_df[['Ticker', 'Zisk/Ztráta', 'Hodnota (CZK)']], hide_index=True, use_container_width=True)

            with t2:
                st.dataframe(res_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Chyba: {e}. Zkontrolujte, zda jsou tickery správně (např. CEZ.PR pro ČEZ).")
else:
    st.info("Portfolio je prázdné. Přidejte první nákup.")
