import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os
import numpy as np

# --- 1. ZABEZPEČENÍ ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "heslo123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; color: #d4af37; font-weight: 300;'>Wealth Terminal</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Pro vstup do privátní zóny zadejte autorizační kód.</p>", unsafe_allow_html=True)
        st.text_input("", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if not check_password(): st.stop()

# --- 2. DESIGN A STYLING (ALOCANO INSPIRED) ---
st.set_page_config(page_title="Investment Terminal", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #f0f0f0; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #1a1a1a; }
    [data-testid="stMetric"] { background-color: #0a0a0a; border: 1px solid #222; border-radius: 12px; padding: 20px !important; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Inter', sans-serif; font-weight: 300; }
    .stButton>button { border-radius: 8px; background-color: #d4af37; color: black; font-weight: 600; border: none; height: 45px; }
    .stDataFrame { border: 1px solid #1a1a1a; border-radius: 8px; }
    .status-safe { color: #2ecc71; font-weight: bold; }
    .status-warning { color: #f1c40f; font-weight: bold; }
    .status-danger { color: #e74c3c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'terminal_data.csv'
WATCHLIST_FILE = 'watchlist.csv'

def load_data(file):
    if not os.path.exists(file): return pd.DataFrame()
    return pd.read_csv(file)

df = load_data(DB_FILE)
df_watch = load_data(WATCHLIST_FILE)

# --- 3. NAVIGACE ---
st.sidebar.markdown("<h2 style='text-align: center;'>TERMINAL</h2>", unsafe_allow_html=True)
menu = st.sidebar.selectbox("", ["📱 Dashboard", "📈 Analýza Portfolia", "💸 Dividendový Kalendář", "🔍 Stock Screener & Watchlist", "📜 Historie"])

# --- 4. FUNKCE PRO VÝPOČTY ---
def get_holdings(df_data):
    if df_data.empty: return pd.DataFrame()
    df_data['pocet_adj'] = df_data.apply(lambda x: x['pocet'] if x['typ'] == 'Nákup' else -x['pocet'], axis=1)
    holdings = df_data.groupby(['ticker', 'mena', 'dan']).agg({'pocet_adj': 'sum', 'cena': 'mean'}).reset_index()
    holdings = holdings[holdings['pocet_adj'] > 0]
    holdings.rename(columns={'pocet_adj': 'pocet', 'cena': 'avg_price'}, inplace=True)
    return holdings

# --- HLAVNÍ LOGIKA STRÁNEK ---

if menu == "📱 Dashboard":
    st.title("Souhrn tvého impéria")
    if not df.empty:
        holdings = get_holdings(df)
        if not holdings.empty:
            with st.spinner('Aktualizuji data z burzy...'):
                kurzy = yf.download(["USDCZK=X", "EURCZK=X"], period="1d", progress=False)['Close']
                u_czk, e_czk = kurzy["USDCZK=X"].iloc[-1], kurzy["EURCZK=X"].iloc[-1]
                rates = {"CZK": 1.0, "USD": u_czk, "EUR": e_czk}
                
                total_val, total_cost, total_div = 0, 0, 0
                
                for _, row in holdings.iterrows():
                    s = yf.Ticker(row['ticker'])
                    px_now = s.history(period="1d")['Close'].iloc[-1]
                    rate = rates.get(s.info.get('currency', 'USD'), 1.0)
                    
                    total_val += row['pocet'] * px_now * rate
                    total_cost += row['pocet'] * row['avg_price'] * rates.get(row['mena'], 1.0)
                    
                    div_yield = s.info.get('dividendRate', 0)
                    if div_yield:
                        total_div += (div_yield * row['pocet'] * rate) * (1 - (row['dan']/100))

                # Metriky jako v profesionální appce
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Celková hodnota", f"{total_val:,.0f} Kč")
                gain = total_val - total_cost
                gain_pct = (gain / total_cost) * 100 if total_cost > 0 else 0
                c2.metric("Celkový zisk/ztráta", f"{gain:,.0f} Kč", f"{gain_pct:.2f} %")
                c3.metric("Čisté dividendy (Rok)", f"{total_div:,.0f} Kč")
                c4.metric("Měsíční renta", f"{(total_div/12):,.0f} Kč")
                
                st.markdown("---")
                st.subheader("Struktura majetku")
                fig = px.pie(holdings, values='pocet', names='ticker', hole=0.8, color_discrete_sequence=px.colors.sequential.Gold_r)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        else: st.info("Zatím nemáš žádné aktivní pozice.")
    else: st.info("Tvůj deník je prázdný. Začni přidáním prvního nákupu v Historii.")

elif menu == "📈 Analýza Portfolia":
    st.title("Hloubková analýza")
    if not df.empty:
        holdings = get_holdings(df)
        analysis_data = []
        for t in holdings['ticker']:
            s = yf.Ticker(t)
            inf = s.info
            analysis_data.append({
                'Ticker': t,
                'Sektor': inf.get('sector', 'Neznámé'),
                'Země': inf.get('country', 'Neznámé'),
                'P/E': inf.get('forwardPE', 'N/A'),
                'Div. Yield': f"{inf.get('dividendYield', 0)*100:.2f} %" if inf.get('dividendYield') else "0 %",
                'Payout Ratio': f"{inf.get('payoutRatio', 0)*100:.1f} %" if inf.get('payoutRatio') else "N/A"
            })
        st.dataframe(pd.DataFrame(analysis_data), use_container_width=True, hide_index=True)
        
        # Heatmapa jako na Alocanu
        st.subheader("Sektorové zastoupení")
        fig_sec = px.sunburst(pd.DataFrame(analysis_data), path=['Sektor', 'Ticker'], color_discrete_sequence=px.colors.sequential.Amber)
        fig_sec.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sec, use_container_width=True)

elif menu == "🔍 Stock Screener & Watchlist":
    st.title("Hledání příležitostí")
    
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("Prověřit novou akcii")
        t_search = st.text_input("Ticker (např. AAPL, O, CEZ.PR)").upper()
        if st.button("Spustit AI Audit"):
            s = yf.Ticker(t_search)
            inf = s.info
            curr = inf.get('currentPrice', 0)
            eps = inf.get('forwardEps', 0)
            
            # Modely ocenění
            graham = np.sqrt(22.5 * eps * (inf.get('bookValue', 0))) if eps > 0 else 0
            pe_avg = inf.get('trailingPE', 20) # Zjednodušeně
            
            st.write(f"### {inf.get('shortName')}")
            c_a, c_b = st.columns(2)
            c_a.metric("Aktuální cena", f"{curr} {inf.get('currency')}")
            c_b.metric("Grahamovo číslo (Férová cena)", f"{graham:.2f}")
            
            if graham > curr: st.success(f"Akcie vypadá podhodnoceně o {((graham/curr)-1)*100:.1f} %")
            else: st.warning("Akcie se zdá být nadhodnocená vůči Grahamovu číslu.")
            
            # Bezpečnost dividendy
            payout = inf.get('payoutRatio', 0)
            if payout > 0.8: st.error(f"⚠️ Pozor: Payout ratio je {payout*100:.1f} %. Dividenda může být v ohrožení.")
            elif payout > 0: st.success(f"✅ Dividenda je bezpečná (Payout: {payout*100:.1f} %)")

    with col_r:
        st.subheader("Můj Watchlist")
        new_w = st.text_input("Přidat na watchlist (Ticker)").upper()
        if st.button("Sledovat"):
            new_watch = pd.DataFrame([[new_w]], columns=['ticker'])
            new_watch.to_csv(WATCHLIST_FILE, mode='a', header=not os.path.exists(WATCHLIST_FILE), index=False)
            st.rerun()
        
        if not df_watch.empty:
            st.table(df_watch)

elif menu == "💸 Dividendový Kalendář":
    st.title("Tok hotovosti")
    if not df.empty:
        holdings = get_holdings(df)
        st.write("Tady uvidíš přehled svých budoucích příjmů upravených o tvou daň.")
        # Zjednodušený seznam pro přehlednost
        div_list = []
        for _, row in holdings.iterrows():
            s = yf.Ticker(row['ticker'])
            rate = s.info.get('dividendRate', 0)
            if rate:
                div_list.append({'Firma': row['ticker'], 'Roční čistý příjem': f"{rate * row['pocet'] * (1-row['dan']/100):,.2f}"})
        st.table(pd.DataFrame(div_list))

elif menu == "📜 Historie":
    st.title("Správa transakcí")
    with st.expander("📝 Přidat nový záznam"):
        with st.form("main_form"):
            c_1, c_2, c_3 = st.columns(3)
            t_typ = c_1.selectbox("Typ", ["Nákup", "Prodej"])
            t_tick = c_2.text_input("Ticker").upper()
            t_qty = c_3.number_input("Počet kusů", min_value=0.0)
            c_4, c_5, c_6 = st.columns(3)
            t_px = c_4.number_input("Cena za kus")
            t_curr = c_5.selectbox("Měna", ["USD", "CZK", "EUR"])
            t_tax = c_6.slider("Srážková daň (%)", 0, 35, 15)
            if st.form_submit_button("Uložit transakci"):
                new_data = pd.DataFrame([[t_tick, t_typ, t_qty, t_px, t_curr, t_tax, pd.Timestamp.now().date()]], 
                                       columns=['ticker', 'typ', 'pocet', 'cena', 'mena', 'dan', 'datum'])
                new_data.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
                st.rerun()
    
    if not df.empty:
        st.dataframe(df.sort_values('datum', ascending=False), use_container_width=True)
