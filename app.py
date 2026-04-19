import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Konfigurace stránky
st.set_page_config(page_title="Investment Dashboard", layout="wide")

# Digrin-like stylizace
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; box-shadow: 2px 2px 5px rgba(0,0,0,0.3); }
    div[data-testid="stExpander"] { border: none; background-color: #161b22; border-radius: 10px; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    h1, h2, h3 { color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['ticker', 'pocet', 'cena_usd', 'datum']).to_csv(DB_FILE, index=False)

# --- SIDEBAR ---
st.sidebar.header("➕ Správa portfolia")
with st.sidebar.form("add_form", clear_on_submit=True):
    t_input = st.text_input("Ticker (např. O, KO, AAPL)").upper()
    n_input = st.number_input("Počet kusů", min_value=0.0, step=0.1)
    p_input = st.number_input("Nákupní cena ($)", min_value=0.0, step=0.1)
    submit = st.form_submit_button("Přidat pozici")
    if submit and t_input:
        pd.DataFrame([[t_input, n_input, p_input, pd.Timestamp.now().date()]], 
                    columns=['ticker', 'pocet', 'cena_usd', 'datum']).to_csv(DB_FILE, mode='a', header=False, index=False)
        st.sidebar.success(f"{t_input} přidán!")

if st.sidebar.button("🗑️ Vymazat vše"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        st.rerun()

# --- VÝPOČTY ---
df = pd.read_csv(DB_FILE)

if not df.empty:
    portfolio_summary = df.groupby('ticker').agg({'pocet': 'sum'}).reset_index()
    tickers = portfolio_summary['ticker'].tolist()
    
    with st.spinner('Načítám data z trhu...'):
        # Ceny a Kurz
        market_data = yf.download(tickers + ["USDCZK=X"], period="2d")['Close']
        kurz = market_data["USDCZK=X"].iloc[-1]
        
        res_list = []
        div_calendar = {i: 0 for i in range(1, 13)}
        mesice_nazvy = {1:'Led', 2:'Úno', 3:'Bře', 4:'Dub', 5:'Kvě', 6:'Čer', 7:'Čvc', 8:'Srp', 9:'Zář', 10:'Říj', 11:'Lis', 12:'Pro'}

        for t in tickers:
            stock = yf.Ticker(t)
            curr_p = market_data[t].iloc[-1]
            prev_p = market_data[t].iloc[-2] if len(market_data[t]) > 1 else curr_p
            change = ((curr_p - prev_p) / prev_p) * 100
            
            total_ks = portfolio_summary[portfolio_summary['ticker'] == t]['pocet'].values[0]
            hodnota_czk = total_ks * curr_p * kurz
            
            # Dividendy
            divs = stock.dividends
            annual_div_czk = 0
            if not divs.empty:
                last_year = divs[divs.index > (datetime.now() - pd.DateOffset(years=1))]
                for date, amount in last_year.items():
                    div_val = amount * total_ks * kurz
                    div_calendar[date.month] += div_val
                    annual_div_czk += div_val

            res_list.append({
                'Ticker': t,
                'Kusy': total_ks,
                'Cena ($)': curr_p,
                'Změna (%)': change,
                'Hodnota (CZK)': hodnota_czk,
                'Roční Divi (CZK)': annual_div_czk
            })

    res_df = pd.DataFrame(res_list)
    
    # --- ZOBRAZENÍ ---
    st.title("📈 Můj Digrin Dashboard")
    
    # Horní řada metrik
    c1, c2, c3 = st.columns(3)
    c1.metric("Celková hodnota", f"{res_df['Hodnota (CZK)'].sum():,.0f} Kč")
    c2.metric("Roční dividendy", f"{res_df['Roční Divi (CZK)'].sum():,.0f} Kč", 
              f"{(res_df['Roční Divi (CZK)'].sum() / res_df['Hodnota (CZK)'].sum() * 100):.2f}% výnos")
    c3.metric("Kurz USD/CZK", f"{kurz:.2f} Kč")

    # Hlavní plocha - Grafy
    tab1, tab2 = st.tabs(["📊 Přehled & Grafy", "📅 Dividendový kalendář"])
    
    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = px.pie(res_df, values='Hodnota (CZK)', names='Ticker', hole=0.5, 
                             title="Rozložení portfolia", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            st.subheader("Moje pozice")
            st.dataframe(res_df.style.format({
                'Cena ($)': '{:.2f}',
                'Změna (%)': '{:+.2f}%',
                'Hodnota (CZK)': '{:,.0f}',
                'Roční Divi (CZK)': '{:,.0f}'
            }), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Očekávané dividendy (CZK)")
        divi_data = pd.DataFrame([{'Měsíc': mesice_nazvy[m], 'Kč': v} for m, v in div_calendar.items()])
        fig_div = px.bar(divi_data, x='Měsíc', y='Kč', text_auto='.0f', title="Měsíční příjmy")
        fig_div.update_traces(marker_color='#58a6ff')
        st.plotly_chart(fig_div, use_container_width=True)
        
        st.info("💡 Výpočet vychází z dividend vyplacených v posledních 12 měsících.")

else:
    st.title("Vítej v tvém trackeru!")
    st.info("Vlevo přidej svou první akcii (např. ticker 'O' pro Realty Income).")
