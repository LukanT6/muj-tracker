import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

# --- KONFIGURACE A STYL ---
st.set_page_config(page_title="Pro Wealth Tracker", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px 10px; }
    h1, h2, h3 { color: #58a6ff !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #0d1117; border-radius: 4px 4px 0px 0px; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium.csv'

def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Nastavení")
with st.sidebar.expander("➕ Přidat nákup", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        t_input = st.text_input("Ticker (AAPL, CEZ.PR)").upper().strip()
        n_input = st.number_input("Počet kusů", min_value=0.0, step=0.1)
        p_input = st.number_input("Nákupní cena za kus", min_value=0.0, step=0.1)
        m_input = st.selectbox("Měna nákupu", ["CZK", "USD", "EUR"])
        submit = st.form_submit_button("Uložit")
        if submit and t_input:
            new_row = pd.DataFrame([[t_input, n_input, p_input, m_input, pd.Timestamp.now().date()]], 
                                   columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
            new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.sidebar.success(f"Uloženo: {t_input}")
            st.rerun()

if st.sidebar.button("🗑️ Smazat celé portfolio"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE); st.rerun()

# --- VÝPOČTY ---
if not df.empty:
    try:
        summary = df.groupby(['ticker', 'mena']).agg({'pocet': 'sum', 'cena': 'mean'}).reset_index()
        tickers = summary['ticker'].unique().tolist()
        
        with st.spinner('Aktualizuji data z trhů...'):
            # Kurzy
            kurzy = yf.download(["USDCZK=X", "EURCZK=X"], period="1d")['Close']
            usd_czk = kurzy["USDCZK=X"].iloc[-1]
            eur_czk = kurzy["EURCZK=X"].iloc[-1]
            get_rate = {"CZK": 1.0, "USD": usd_czk, "EUR": eur_czk}

            res_list = []
            div_calendar = {i: 0 for i in range(1, 13)}
            mesice_nazvy = {1:'Led', 2:'Úno', 3:'Bře', 4:'Dub', 5:'Kvě', 6:'Čer', 7:'Čvc', 8:'Srp', 9:'Zář', 10:'Říj', 11:'Lis', 12:'Pro'}
            now = pd.Timestamp.now(tz=None)

            for t in tickers:
                stock = yf.Ticker(t)
                info = stock.info
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    market_curr = info.get('currency', 'USD')
                    rate_to_czk = get_rate.get(market_curr, 1.0)
                    
                    t_rows = summary[summary['ticker'] == t]
                    for _, row in t_rows.iterrows():
                        val_czk = row['pocet'] * curr_p * rate_to_czk
                        buy_czk = row['pocet'] * row['cena'] * get_rate.get(row['mena'], 1.0)
                        profit_czk = val_czk - buy_czk
                        profit_pct = (profit_czk / buy_czk) * 100 if buy_czk != 0 else 0
                        
                        # VÝPOČET DIVIDEND
                        divs = stock.dividends
                        annual_div_czk = 0
                        if not divs.empty:
                            divs.index = divs.index.tz_localize(None)
                            last_year = divs[divs.index > (now - pd.DateOffset(years=1))]
                            for date, amount in last_year.items():
                                div_val = amount * row['pocet'] * rate_to_czk
                                div_calendar[date.month] += div_val
                                annual_div_czk += div_val

                        res_list.append({
                            'Ticker': t,
                            'Kusy': row['pocet'],
                            'Cena': f"{curr_p:.2f} {market_curr}",
                            'Hodnota (CZK)': val_czk,
                            'Zisk/Ztráta %': profit_pct,
                            'Roční Divi (Kč)': annual_div_czk
                        })

            res_df = pd.DataFrame(res_list)

            # --- ZOBRAZENÍ ---
            st.title("📊 Můj Investiční Dashboard")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Celková hodnota", f"{res_df['Hodnota (CZK)'].sum():,.0f} Kč")
            total_divi = res_df['Roční Divi (Kč)'].sum()
            divi_yield = (total_divi / res_df['Hodnota (CZK)'].sum() * 100) if res_df['Hodnota (CZK)'].sum() > 0 else 0
            m2.metric("Roční dividendy", f"{total_divi:,.0f} Kč", f"{divi_yield:.2f}% výnos")
            m3.metric("Kurz USD/CZK", f"{usd_czk:.2f} Kč")

            st.markdown("---")
            t1, t2, t3 = st.tabs(["📈 Portfolio", "📅 Dividendový kalendář", "📋 Podrobnosti"])
            
            with t1:
                col_l, col_r = st.columns([1, 1])
                with col_l:
                    fig = px.pie(res_df, values='Hodnota (CZK)', names='Ticker', hole=0.6,
                                 color_discrete_sequence=px.colors.qualitative.Bold)
                    st.plotly_chart(fig, use_container_width=True)
                with col_r:
                    st.subheader("Výkonnost akcií")
                    # Formátování tabulky pro hezčí barvy zisku
                    styled_df = res_df[['Ticker', 'Hodnota (CZK)', 'Zisk/Ztráta %']].copy()
                    st.dataframe(styled_df.style.format({'Zisk/Ztráta %': '{:+.2f}%', 'Hodnota (CZK)': '{:,.0f}'}), 
                                 hide_index=True, use_container_width=True)

            with t2:
                st.subheader("Očekávaný měsíční příjem (Kč)")
                divi_plot_data = pd.DataFrame([{'Měsíc': mesice_nazvy[m], 'Kč': v} for m, v in div_calendar.items()])
                fig_bar = px.bar(divi_plot_data, x='Měsíc', y='Kč', text_auto='.0f')
                fig_bar.update_traces(marker_color='#58a6ff')
                st.plotly_chart(fig_bar, use_container_width=True)

            with t3:
                st.subheader("Kompletní přehled dat")
                st.dataframe(res_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Chyba: {e}")
else:
    st.title("Vítej v Trackeru!")
    st.info("Portfolio je prázdné. Přidej nákup v levém panelu.")
