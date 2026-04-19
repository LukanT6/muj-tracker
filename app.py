import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import os

# --- 1. ZABEZPEČENÍ ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "heslo123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; color: #d4af37; font-weight: 300;'>Vítej zpět.</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Pro přístup ke svému majetku zadej svůj osobní PIN.</p>", unsafe_allow_html=True)
        st.text_input("", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if not check_password(): st.stop()

# --- 2. KONFIGURACE A STYL ---
st.set_page_config(page_title="Můj Trezor", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #f0f0f0; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #1a1a1a; }
    [data-testid="stMetric"] { background-color: #0a0a0a; border: 1px solid #2a2200; border-radius: 16px; padding: 24px !important; border-left: 4px solid #d4af37; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    h1 { color: #d4af37 !important; font-family: 'Inter', sans-serif; font-weight: 300; letter-spacing: -1px; }
    h2, h3 { color: #e0e0e0 !important; font-weight: 400; }
    .stTabs [data-baseweb="tab-list"] { background-color: #000000; }
    .stButton>button { border-radius: 20px; background-color: #d4af37; color: black; font-weight: 600; width: 100%; border: none; transition: all 0.2s; }
    .stButton>button:hover { background-color: #fff; transform: translateY(-2px); }
    .stProgress > div > div > div > div { background-color: #d4af37 !important; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'portfolium_v4.csv'

def load_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=['ticker', 'typ', 'pocet', 'cena', 'mena', 'dan', 'datum'])
    return pd.read_csv(DB_FILE)

df = load_data()

# --- 3. NAVIGACE ---
st.sidebar.markdown("<h2 style='color: #d4af37; text-align: center;'>Zlatý Řez</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("", ["🏠 Můj majetek", "📊 Pod kapotou", "💰 Stroj na peníze", "📜 Účetní deník", "🧮 Rychlý AI Audit"])
st.sidebar.markdown("---")

# --- 4. FUNKCE ---
def get_holdings(df_data):
    if df_data.empty: return pd.DataFrame()
    df_data['pocet_adj'] = df_data.apply(lambda x: x['pocet'] if x['typ'] == 'Nákup' else -x['pocet'], axis=1)
    holdings = df_data.groupby(['ticker', 'mena', 'dan']).agg({'pocet_adj': 'sum', 'cena': 'mean'}).reset_index()
    holdings = holdings[holdings['pocet_adj'] > 0]
    holdings.rename(columns={'pocet_adj': 'pocet'}, inplace=True)
    return holdings

# --- PŘIDÁNÍ TRANSAKCE ---
with st.sidebar.expander("✍️ Zapsat do deníku"):
    with st.form("trans_form", clear_on_submit=True):
        st.caption("Každá investice se počítá. Co přidáme dnes?")
        t_type = st.selectbox("Co se stalo?", ["Nákup", "Prodej"])
        t_ticker = st.text_input("Jaká akcie? (Ticker)").upper().strip()
        t_qty = st.number_input("Kolik kusů?", min_value=0.0, step=0.01)
        t_px = st.number_input("Za jakou cenu?", min_value=0.0)
        t_curr = st.selectbox("V jaké měně?", ["USD", "CZK", "EUR"])
        t_tax = st.slider("Jakou daň ti strhnou? (%)", 0, 35, 15)
        if st.form_submit_button("Uložit do trezoru"):
            new_row = pd.DataFrame([[t_ticker, t_type, t_qty, t_px, t_curr, t_tax, pd.Timestamp.now().date()]], 
                                   columns=['ticker', 'typ', 'pocet', 'cena', 'mena', 'dan', 'datum'])
            new_row.to_csv(DB_FILE, mode='a', header=not os.path.exists(DB_FILE), index=False)
            st.rerun()

if st.sidebar.button("⚠️ Začít s čistým štítem"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE); st.rerun()

# --- HLAVNÍ LOGIKA ---
if menu == "🏠 Můj majetek":
    st.title("Tady tvé peníze pracují.")
    goal = st.sidebar.number_input("Tvoje vysněná měsíční renta (Kč)", value=10000, step=1000)
    
    if not df.empty:
        holdings = get_holdings(df)
        if not holdings.empty:
            with st.spinner('Zjišťuji aktuální ceny na trhu...'):
                kurzy = yf.download(["USDCZK=X", "EURCZK=X"], period="1d", progress=False)['Close']
                u_czk, e_czk = kurzy["USDCZK=X"].iloc[-1], kurzy["EURCZK=X"].iloc[-1]
                get_rate = {"CZK": 1.0, "USD": u_czk, "EUR": e_czk}
                
                total_val, total_div_net = 0, 0
                
                for _, row in holdings.iterrows():
                    s = yf.Ticker(row['ticker'])
                    px_hist = s.history(period="1d")
                    px_now = px_hist['Close'].iloc[-1] if not px_hist.empty else row['cena']
                    r_czk = get_rate.get(s.info.get('currency', 'USD'), 1.0)
                    total_val += row['pocet'] * px_now * r_czk
                    
                    d_annual = s.info.get('dividendRate', 0)
                    if d_annual:
                        net = (d_annual * row['pocet'] * r_czk) * (1 - (row['dan']/100))
                        total_div_net += net

                c1, c2, c3 = st.columns(3)
                c1.metric("Hodnota tvého impéria", f"{total_val:,.0f} Kč")
                c2.metric("Čisté dividendy za rok", f"{total_div_net:,.0f} Kč")
                c3.metric("Z toho měsíčně", f"{(total_div_net/12):,.0f} Kč")
                
                st.markdown("<br>", unsafe_allow_html=True)
                current_monthly = total_div_net / 12
                progress = min(current_monthly / goal, 1.0)
                st.markdown(f"**Cesta k rentě {goal:,.0f} Kč měsíčně:**")
                st.progress(progress)
                if progress >= 1:
                    st.success("Cíl splněn! Gratuluji, jsi finančně svobodný. Čas nastavit si vyšší laťku?")
                else:
                    st.caption(f"Skvělá práce. Už jsi ušel **{progress*100:.1f} %** cesty. Jen tak dál!")
        else: 
            st.info("Tvůj trezor zatím zeje prázdnotou. Co takhle si udělat radost a něco přikoupit?")
    else: 
        st.info("Vítej na začátku své cesty. Vlevo v menu přidej svou úplně první investici.")

elif menu == "📊 Pod kapotou":
    st.title("Rozložení tvého bohatství.")
    st.write("Dobrý investor nedává všechna vajíčka do jednoho košíku. Jak jsi na tom ty?")
    if not df.empty:
        holdings = get_holdings(df)
        if not holdings.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Jednotlivé pozice")
                fig_tree = px.treemap(holdings, path=['ticker'], values='pocet', color_discrete_sequence=['#d4af37', '#ffffff', '#555555'])
                fig_tree.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(t=0, l=0, r=0, b=0))
                st.plotly_chart(fig_tree, use_container_width=True)
            with c2:
                st.markdown("### Zastoupené sektory")
                sectors = [yf.Ticker(t).info.get('sector', 'Ostatní') for t in holdings['ticker']]
                holdings['Sektor'] = sectors
                fig_sec = px.pie(holdings, values='pocet', names='Sektor', hole=0.7, color_discrete_sequence=['#d4af37', '#ffffff', '#888888'])
                fig_sec.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(t=0, l=0, r=0, b=0))
                st.plotly_chart(fig_sec, use_container_width=True)

elif menu == "💰 Stroj na peníze":
    st.title("Tvé pasivní příjmy.")
    st.write("Tady je přesně rozepsáno, kolik ti firmy pošlou na účet poté, co si stát vezme svůj díl.")
    if not df.empty:
        holdings = get_holdings(df)
        div_data = []
        with st.spinner('Počítám čisté zisky...'):
            for _, row in holdings.iterrows():
                s = yf.Ticker(row['ticker'])
                d_rate = s.info.get('dividendRate', 0)
                if d_rate:
                    gross = d_rate * row['pocet']
                    net = gross - (gross * (row['dan']/100))
                    div_data.append({
                        'Společnost': row['ticker'],
                        'Hrubá odměna (Rok)': f"{gross:,.2f} {row['mena']}",
                        'Daň': f"{row['dan']} %",
                        'Čistá radost (Rok)': f"{net:,.2f} {row['mena']}"
                    })
        if div_data:
            st.dataframe(pd.DataFrame(div_data), use_container_width=True, hide_index=True)
        else: st.info("Zatím nevlastníš žádné společnosti, které by ti vyplácely dividendu.")

elif menu == "📜 Účetní deník":
    st.title("Historie tvých rozhodnutí.")
    st.write("Každý nákup a prodej, pěkně pohromadě. Dobré pro sebereflexi (nebo pro daňové přiznání).")
    if not df.empty:
        st.dataframe(df.sort_values('datum', ascending=False), use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Stáhnout data do Excelu/CSV", csv, "muj_investicni_denik.csv", "text/csv")

elif menu == "🧮 Rychlý AI Audit":
    st.title("Než něco koupíš, zeptej se.")
    st.write("Napiš sem jakoukoliv akcii a já ti na základě matematických modelů řeknu, jestli není zbytečně drahá.")
    t_val = st.text_input("", "AAPL").upper()
    if st.button("Zjistit férovou cenu"):
        with st.spinner('Hledám v datech na Wall Street...'):
            s = yf.Ticker(t_val)
            eps = s.info.get('forwardEps', 0)
            growth = s.info.get('earningsGrowth', 0.1) * 100
            curr = s.info.get('currentPrice', 1)
            
            if eps and curr:
                fair = eps * (8.5 + 2 * growth)
                diff = ((fair/curr)-1)*100
                st.metric(f"Odhahovaná férová cena vs. aktuální cena na trhu", f"{fair:.2f} {s.info.get('currency', 'USD')}")
                if diff > 0: 
                    st.success(f"Dobrý úlovek! Akcie vypadá podhodnoceně o zhruba {diff:.1f} %.")
                else: 
                    st.error(f"Opatrně. Podle čísel je na trhu aktuálně předražená o {abs(diff):.1f} %.")
            else:
                st.warning("Promiň, ale k této firmě se mi nepodařilo najít dostatek dat pro spolehlivý výpočet.")
