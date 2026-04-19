import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

# --- KONFIGURACE A STYL ---
st.set_page_config(page_title="My Wealth Tracker", layout="wide")

st.markdown("""
    <style>
    /* Pozadí a hlavní font */
    .main { background-color: #0d1117; color: #c9d1d9; }
    
    /* Styl pro karty s metrikami */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Nadpisy */
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Úprava tabulek */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 10px;
    }
    
    /* Skrytí menu Streamlitu pro čistý look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'

def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=['ticker', 'pocet', 'cena_usd', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ovládací panel")
with st.sidebar.expander("➕ Přidat nový nákup", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        t_input = st.text_input("Ticker").upper().strip()
        n_input = st.number_input("Počet kusů", min_value=0.0, step=0.1)
        p_input = st.number_input("Nákupní cena za kus ($)", min_value=0.0, step=0.1)
        submit = st.form_submit_button("Uložit do portfolia")
        if submit and t_input:
            new_row = pd.DataFrame([[t_input, n_input, p_input, pd.Timestamp.now().date()]], 
                                   columns=['ticker', 'pocet', 'cena_usd', 'datum'])
            new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.rerun()

if st.sidebar.button("🗑️ Smazat všechna data"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        st.rerun()

# --- VÝPOČTY ---
if not df.empty:
    try:
        # Agregace dat pro výpočet průměrné ceny a počtu kusů
        summary = df.groupby('ticker').agg({
            'pocet': 'sum',
            'cena_usd': 'mean' # Průměrná nákupka
        }).reset_index()
        
        tickers = summary['ticker'].tolist()
        
        with st.spinner('Aktualizuji data z burzy...'):
            kurz = yf.Ticker("USDCZK=X").history(period="1d")['Close'].iloc[-1]
            
            res_list = []
            div_calendar = {i: 0 for i in range(1, 13)}
            mesice_nazvy = {1:'Led', 2:'Úno', 3:'Bře', 4:'Dub', 5:'Kvě', 6:'Čer', 7:'Čvc', 8:'Srp', 9:'Zář', 10:'Říj', 11:'Lis', 12:'Pro'}
            now = pd.Timestamp.now(tz=None)

            for t in tickers:
                stock = yf.Ticker(t)
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    total_ks = summary[summary['ticker'] == t]['pocet'].values[0]
                    avg_buy = summary[summary['ticker'] == t]['cena_usd'].values[0]
                    
                    hodnota_czk = total_ks * curr_p * kurz
                    profit_pct = ((curr_p - avg_buy) / avg_buy) * 100
                    
                    # Dividendy
                    divs = stock.dividends
                    annual_div_czk = 0
                    if not divs.empty:
                        divs.index = divs.index.tz_localize(None)
                        last_year = divs[divs.index > (now - pd.DateOffset(years=1))]
                        for date, amount in last_year.items():
                            val = amount * total_ks * kurz
                            div_calendar[date.month] += val
                            annual_div_czk += val

                    res_list.append({
                        'Ticker': t, 
                        'Kusy': total_ks,
                        'Aktuální cena': f"{curr_p:.2f} $",
                        'Profit/Loss': f"{profit_pct:+.2f} %",
                        'Hodnota (CZK)': hodnota_czk, 
                        'Dividendy (rok)': annual_div_czk
                    })

            res_df = pd.DataFrame(res_list)
            
            # --- ZOBRAZENÍ ---
            st.title("📈 Investiční Dashboard")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Celková hodnota", f"{res_df['Hodnota (CZK)'].sum():,.0f} Kč")
            total_div = res_df['Dividendy (rok)'].sum()
            col2.metric("Roční dividendy", f"{total_div:,.0f} Kč", f"{(total_div/res_df['Hodnota (CZK)'].sum()*100):.2f}% výnos")
            col3.metric("Kurz USD/CZK", f"{kurz:.2f} Kč")

            st.markdown("---")

            t1, t2, t3 = st.tabs(["📊 Portfolio", "📅 Dividendový kalendář", "📝 Seznam akcií"])
            
            with t1:
                c_left, c_right = st.columns([1, 1])
                with c_left:
                    fig_pie = px.pie(res_df, values='Hodnota (CZK)', names='Ticker', hole=0.6,
                                     color_discrete_sequence=px.colors.sequential.Blues_r)
                    fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c_right:
                    st.subheader("Aktuální stav")
                    st.dataframe(res_df[['Ticker', 'Hodnota (CZK)', 'Profit/Loss']], hide_index=True, use_container_width=True)

            with t2:
                divi_df = pd.DataFrame([{'Měsíc': mesice_nazvy[m], 'Kč': v} for m, v in div_calendar.items()])
                fig_bar = px.bar(divi_df, x='Měsíc', y='Kč', text_auto='.0f')
                fig_bar.update_traces(marker_color='#58a6ff', marker_line_color='#30363d', opacity=0.8)
                st.plotly_chart(fig_bar, use_container_width=True)

            with t3:
                st.subheader("Všechny pozice v detailu")
                st.table(res_df)

    except Exception as e:
        st.error(f"Chyba při zpracování: {e}")
else:
    st.title("Vítej!")
    st.info("Tvůj tracker je připraven. V levém panelu přidej své první akcie.")
