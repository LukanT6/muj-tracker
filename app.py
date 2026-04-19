import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
from datetime import datetime

# --- 1. ZABEZPEČENÍ (HESLO) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "heslo123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #d4af37;'>🔒 Premium Trezor</h2>", unsafe_allow_html=True)
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

# --- 3. KONFIGURACE A LUXUSNÍ STYL ---
st.set_page_config(page_title="Monery Ultimate", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    [data-testid="stHeader"] { background-color: #000000; }
    [data-testid="stMetric"] { background-color: #0a0a0a; border: 1px solid #332a00; border-radius: 12px; padding: 20px !important; border-left: 5px solid #d4af37; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #332a00; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Playfair Display', serif; }
    .stButton>button { border-radius: 30px; background-color: #d4af37; color: black; font-weight: bold; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #ffffff; transform: scale(1.05); }
    /* Běžící text */
    .ticker-wrap { width: 100%; overflow: hidden; background: #111; padding: 10px 0; border-bottom: 1px solid #332a00; margin-bottom: 20px; }
    .ticker { white-space: nowrap; animation: ticker 30s linear infinite; display: inline-block; color: #d4af37; font-weight: bold; }
    @keyframes ticker { 0% { transform: translate(100%, 0); } 100% { transform: translate(-100%, 0); } }
    </style>
    """, unsafe_allow_html=True)

GOLD_PALETTE = ['#d4af37', '#ffffff', '#c0c0c0', '#8b6508', '#444444', '#b5952f']

DB_FILE = 'portfolium.csv'
def load_data():
    if not os.path.exists(DB_FILE): return pd.DataFrame(columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- 4. SIDEBAR ---
st.sidebar.title("💎 Monery Ultimate")

# Ticker Tape Simulace
if not df.empty:
    tickers_string = "  •  ".join(df['ticker'].unique().tolist())
    st.markdown(f"<div class='ticker-wrap'><div class='ticker'>AKTUÁLNĚ VE VAŠEM TREZORU: {tickers_string}</div></div>", unsafe_allow_html=True)

with st.sidebar.expander("🔍 AI ANALYZÁTOR", expanded=False):
    search_t = st.text_input("Ticker pro analýzu", value="AAPL").upper()
    if st.button("Prozkoumat"):
        res = analyze_stock(search_t)
        if isinstance(res, dict):
            st.write(f"**{res['name']}**")
            st.write(f"Férová cena: {res['fair']:.2f} {res['currency']}")
            if res['upside'] > 0: st.success(f"PODHODNOCENO o {res['upside']:.1f}% ✅")
            else: st.error(f"PŘEDRAŽENO o {abs(res['upside']):.1f}% ❌")

with st.sidebar.expander("➕ Nová investice"):
    with st.form("add_form", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        n_in = st.number_input("Kusy", min_value=0.0)
        p_in = st.number_input("Nákupní cena", min_value=0.0)
        m_in = st.selectbox("Měna", ["USD", "CZK", "EUR"])
        if st.form_submit_button("Uložit"):
            new_r = pd.DataFrame([[t_in, n_in, p_in, m_in, pd.Timestamp.now().date()]], columns=['ticker', 'pocet', 'cena', 'mena', 'datum'])
            new_r.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.rerun()

if st.sidebar.button("🗑️ Vymazat historii"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE); st.rerun()

# --- 5. VÝPOČTY ---
if not df.empty:
    try:
        summary = df.groupby(['ticker', 'mena']).agg({'pocet': 'sum', 'cena': 'mean'}).reset_index()
        
        with st.spinner('Synchronizuji s Wall Street...'):
            kurzy = yf.download(["USDCZK=X", "EURCZK=X", "^GSPC", "^VIX"], period="1d")['Close']
            usd_czk = kurzy["USDCZK=X"].iloc[-1]
            eur_czk = kurzy["EURCZK=X"].iloc[-1]
            vix = kurzy["^VIX"].iloc[-1]
            get_rate = {"CZK": 1.0, "USD": usd_czk, "EUR": eur_czk}

            res_list, div_calendar = [], {i: 0 for i in range(1, 13)}
            mesice = {1:'LED', 2:'ÚNO', 3:'BŘE', 4:'DUB', 5:'KVĚ', 6:'ČER', 7:'ČVC', 8:'SRP', 9:'ZÁŘ', 10:'ŘÍJ', 11:'LIS', 12:'PRO'}

            for t in summary['ticker'].unique():
                stock = yf.Ticker(t)
                info = stock.info
                hist = stock.history(period="2d")
                
                if not hist.empty:
                    curr_p = hist['Close'].iloc[-1]
                    rate_czk = get_rate.get(info.get('currency', 'USD'), 1.0)
                    sector = info.get('sector', 'Ostatní')
                    country = info.get('country', 'Neznámé')
                    
                    for _, row in summary[summary['ticker'] == t].iterrows():
                        v_czk = row['pocet'] * curr_p * rate_czk
                        # Yield on Cost (Výnos k nákupní ceně)
                        divs = stock.dividends
                        a_div_czk = 0
                        if not divs.empty:
                            divs.index = divs.index.tz_localize(None)
                            last_yr = divs[divs.index > (pd.Timestamp.now() - pd.DateOffset(years=1))]
                            for date, amount in last_yr.items():
                                val = amount * row['pocet'] * rate_czk
                                div_calendar[date.month] += val
                                a_div_czk += val
                        
                        yoc = (a_div_czk / (row['pocet'] * row['cena'] * get_rate.get(row['mena'], 1.0)) * 100) if row['cena'] > 0 else 0
                        
                        res_list.append({
                            'Ticker': t, 'Sektor': sector, 'Země': country, 
                            'Hodnota': v_czk, 'Dividenda': a_div_czk, 'YoC %': yoc
                        })

            res_df = pd.DataFrame(res_list)
            
            # --- DASHBOARD ---
            st.title("Elite Portfolio Dashboard")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Celkový majetek", f"{res_df['Hodnota'].sum():,.0f} Kč")
            m2.metric("Pasivní příjem (rok)", f"{res_df['Dividenda'].sum():,.0f} Kč")
            avg_yoc = res_df['YoC %'].mean()
            m3.metric("Výnos k nákupu (YoC)", f"{avg_yoc:.2f} %")
            m4.metric("Index strachu (VIX)", f"{vix:.1f}")

            st.markdown("---")
            t1, t2, t3, t4 = st.tabs(["💰 Složení", "🌍 Geografie", "📅 Cashflow", "📊 Výkon vs Trh"])
            
            with t1:
                c_a, c_b = st.columns(2)
                with c_a:
                    st.plotly_chart(px.pie(res_df, values='Hodnota', names='Ticker', hole=0.7, color_discrete_sequence=GOLD_PALETTE).update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white'), use_container_width=True)
                with c_b:
                    st.plotly_chart(px.pie(res_df, values='Hodnota', names='Sektor', hole=0.7, color_discrete_sequence=GOLD_PALETTE).update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white'), use_container_width=True)

            with t2:
                st.markdown("### Původ vašich peněz")
                fig_geo = px.pie(res_df, values='Hodnota', names='Země', hole=0.7, color_discrete_sequence=GOLD_PALETTE)
                fig_geo.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_geo, use_container_width=True)

            with t3:
                d_plot = pd.DataFrame([{'Měsíc': mesice[m], 'Kč': v} for m, v in div_calendar.items()])
                st.plotly_chart(px.bar(d_plot, x='Měsíc', y='Kč').update_traces(marker_color='#d4af37').update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white'), use_container_width=True)

            with t4:
                st.markdown("### Srovnání s S&P 500 (1 rok)")
                # Simulované srovnání (v reálu by se musela počítat equity curve)
                sp500 = yf.Ticker("^GSPC").history(period="1y")
                sp500_pct = (sp500['Close'] / sp500['Close'].iloc[0]) - 1
                st.line_chart(sp500_pct)
                st.info("Tip: Pokud vaše portfolio roste rychleji než tato čára, porážíte trh!")

    except Exception as e: st.error(f"Systémová chyba: {e}")
else:
    st.title("Vítejte v Monery Ultimate")
    st.info("Trezor je připraven. Vložte první aktiva.")
