import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os

# Soubor pro uložení dat
DB_FILE = 'portfolium.csv'

# Inicializace souboru
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=['ticker', 'pocet', 'cena_usd', 'datum'])
    df_init.to_csv(DB_FILE, index=False)

st.set_page_config(page_title="Invest Tracker Pro", layout="wide")

# --- BOČNÍ PANEL ---
st.sidebar.header("➕ Nový nákup")
with st.sidebar.form("add_form", clear_on_submit=True):
    t_input = st.text_input("Ticker (např. AAPL, TSLA, CEZ.PR)").upper()
    n_input = st.number_input("Počet kusů", min_value=0.0, step=0.1)
    p_input = st.number_input("Nákupní cena za kus ($)", min_value=0.0, step=0.1)
    submit = st.form_submit_button("Uložit nákup")

    if submit and t_input:
        new_row = pd.DataFrame([[t_input, n_input, p_input, pd.Timestamp.now().date()]], 
                               columns=['ticker', 'pocet', 'cena_usd', 'datum'])
        new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
        st.sidebar.success(f"Akcie {t_input} uložena!")

# --- VÝPOČTY ---
df = pd.read_csv(DB_FILE)

if not df.empty:
    st.title("📈 Můj Investiční Dashboard")
    
    # Seskupení nákupů podle tickeru
    portfolio_summary = df.groupby('ticker').agg({'pocet': 'sum'}).reset_index()
    tickers = portfolio_summary['ticker'].tolist()
    
    with st.spinner('Stahuji čerstvá data z burzy...'):
        # Stáhneme ceny + kurz koruny
        data = yf.download(tickers + ["USDCZK=X"], period="1d")['Close']
        kurz = data["USDCZK=X"].iloc[-1]
        
        results = []
        for t in tickers:
            curr_p = data[t].iloc[-1]
            total_ks = portfolio_summary[portfolio_summary['ticker'] == t]['pocet'].values[0]
            val_czk = total_ks * curr_p * kurz
            results.append({
                'Ticker': t, 
                'Kusy': total_ks, 
                'Aktuální cena ($)': round(curr_p, 2), 
                'Hodnota (CZK)': round(val_czk, 2)
            })

    res_df = pd.DataFrame(results)
    
    # Zobrazení metrik
    total_val = res_df['Hodnota (CZK)'].sum()
    st.metric("Celková hodnota portfolia", f"{total_val:,.2f} CZK", f"Kurz: {kurz:.2f} CZK/USD")
    
    # Grafy
    col1, col2 = st.columns([1, 1])
    with col1:
        fig = px.pie(res_df, values='Hodnota (CZK)', names='Ticker', hole=0.4, title="Rozložení majetku")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Přehled pozic")
        st.dataframe(res_df, use_container_width=True, hide_index=True)
        
    if st.sidebar.button("🗑️ Vymazat všechna data"):
        os.remove(DB_FILE)
        st.rerun()
else:
    st.title("Vítej v Trackeru! 👋")
    st.info("Tvé portfolio je zatím prázdné. Použij formulář vlevo a přidej svou první akcii (např. ticker AAPL).")
