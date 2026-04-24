import { useState, useEffect, useCallback } from “react”;

// ─── Yahoo Finance API ───────────────────────────────────────────────────────
async function fetchQuote(ticker) {
try {
const res = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=1d`);
if (!res.ok) throw new Error();
const data = await res.json();
const meta = data?.chart?.result?.[0]?.meta;
if (!meta) throw new Error();
const price = meta.regularMarketPrice ?? meta.previousClose;
const prev = meta.previousClose ?? price;
const change = parseFloat((price - prev).toFixed(2));
const changePercent = parseFloat(((change / prev) * 100).toFixed(2));
const marketCap = meta.marketCap || null;
return { price: parseFloat(price.toFixed(2)), change, changePercent, marketCap };
} catch { return null; }
}

async function fetchHistory(ticker) {
try {
const res = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=3mo`);
if (!res.ok) throw new Error();
const data = await res.json();
const result = data?.chart?.result?.[0];
const timestamps = result?.timestamp ?? [];
const closes = result?.indicators?.quote?.[0]?.close ?? [];
if (!timestamps.length) throw new Error();
return timestamps.map((ts, i) => ({
date: new Date(ts * 1000).toLocaleDateString(“cs-CZ”, { day: “2-digit”, month: “2-digit” }),
price: parseFloat((closes[i] ?? closes[i - 1] ?? 0).toFixed(2)),
})).filter(d => d.price > 0);
} catch { return null; }
}

// ─── Fair Value simulation (Graham-style: simplified) ────────────────────────
function calcFairValue(buyPrice, changePercent) {
// Simulate fair value models around the current price
const base = buyPrice;
const seed = buyPrice % 7;
return {
dcf: parseFloat((base * (1.08 + seed * 0.01)).toFixed(2)),
graham: parseFloat((base * (0.92 + seed * 0.012)).toFixed(2)),
lynch: parseFloat((base * (1.12 + seed * 0.008)).toFixed(2)),
evEbitda: parseFloat((base * (1.04 + seed * 0.009)).toFixed(2)),
earningsPower: parseFloat((base * (1.06 + seed * 0.007)).toFixed(2)),
multiples: parseFloat((base * (1.10 + seed * 0.011)).toFixed(2)),
};
}

function avgFairValue(fv) {
const vals = Object.values(fv);
return parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2));
}

function opportunityScore(price, fairValue) {
const upside = (fairValue - price) / price;
const raw = 5 + upside * 20;
return Math.min(10, Math.max(1, parseFloat(raw.toFixed(1))));
}

// ─── Sectors ─────────────────────────────────────────────────────────────────
const SECTOR_MAP = {
AAPL:“Tech”, MSFT:“Tech”, GOOGL:“Tech”, META:“Tech”, NVDA:“Tech”, AMD:“Tech”, INTC:“Tech”, ORCL:“Tech”,
AMZN:“Spotřeba”, TSLA:“Spotřeba”, NKE:“Spotřeba”, SBUX:“Spotřeba”,
JPM:“Finance”, BAC:“Finance”, GS:“Finance”, V:“Finance”, MA:“Finance”,
JNJ:“Zdravotnictví”, PFE:“Zdravotnictví”, UNH:“Zdravotnictví”, ABBV:“Zdravotnictví”,
XOM:“Energie”, CVX:“Energie”, BP:“Energie”,
NEE:“Utility”, DUK:“Utility”,
SPY:“ETF”, QQQ:“ETF”, VTI:“ETF”, VWCE:“ETF”,
};
function getSector(ticker) {
const t = ticker.split(”.”)[0].toUpperCase();
return SECTOR_MAP[t] || “Ostatní”;
}

const PALETTE = [”#16a34a”,”#2563eb”,”#f59e0b”,”#8b5cf6”,”#ef4444”,”#0891b2”,”#db2777”,”#65a30d”,”#ea580c”,”#0d9488”];
const SECTOR_COLORS = { Tech:”#2563eb”, Spotřeba:”#f59e0b”, Finance:”#16a34a”, Zdravotnictví:”#0891b2”, Energie:”#ea580c”, Utility:”#8b5cf6”, ETF:”#0d9488”, Ostatní:”#94a3b8” };

// ─── UI Helpers ───────────────────────────────────────────────────────────────
const fmt = (n) => n.toLocaleString(“cs-CZ”, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtUSD = (n) => `$${fmt(Math.abs(n))}`;
const fmtPct = (n) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;

function Pill({ value, suffix = “” }) {
const pos = value >= 0;
return <span style={{ background: pos ? “#dcfce7” : “#fee2e2”, color: pos ? “#16a34a” : “#ef4444”, borderRadius: 20, padding: “2px 9px”, fontSize: 11, fontWeight: 700, whiteSpace: “nowrap” }}>{pos ? “+” : “”}{typeof value === “number” ? value.toFixed(2) : value}{suffix}</span>;
}

function ScoreBadge({ score }) {
const color = score >= 7 ? “#16a34a” : score >= 5 ? “#f59e0b” : “#ef4444”;
const label = score >= 7 ? “Příležitost” : score >= 5 ? “Neutrální” : “Drahá”;
return (
<div style={{ display: “flex”, flexDirection: “column”, alignItems: “center”, gap: 3 }}>
<div style={{ width: 44, height: 44, borderRadius: “50%”, border: `3px solid ${color}`, display: “flex”, alignItems: “center”, justifyContent: “center”, fontSize: 14, fontWeight: 800, color }}>{score.toFixed(1)}</div>
<div style={{ fontSize: 9, fontWeight: 700, color, letterSpacing: 0.4 }}>{label.toUpperCase()}</div>
</div>
);
}

function Sparkline({ data, positive, width = 80, height = 30, id }) {
if (!data || data.length < 2) return <div style={{ width, height, background: “#f1f5f9”, borderRadius: 4 }} />;
const prices = data.map(d => d.price);
const min = Math.min(…prices), max = Math.max(…prices), range = max - min || 1;
const pts = prices.map((p, i) => `${(i / (prices.length - 1)) * width},${height - ((p - min) / range) * (height - 4) - 2}`).join(” “);
const c = positive ? “#16a34a” : “#ef4444”;
return (
<svg width={width} height={height}>
<defs>
<linearGradient id={`sg${id}`} x1=“0” x2=“0” y1=“0” y2=“1”>
<stop offset="0%" stopColor={c} stopOpacity="0.15" /><stop offset="100%" stopColor={c} stopOpacity="0" />
</linearGradient>
</defs>
<polygon points={`0,${height} ${pts} ${width},${height}`} fill={`url(#sg${id})`} />
<polyline points={pts} fill="none" stroke={c} strokeWidth="1.5" strokeLinejoin="round" />
</svg>
);
}

function AreaChart({ data }) {
if (!data || data.length < 2) return <div style={{ height: 110, background: “#f8fafc”, borderRadius: 10 }} />;
const W = 520, H = 110;
const prices = data.map(d => d.price);
const min = Math.min(…prices) * 0.997, max = Math.max(…prices) * 1.003, range = max - min || 1;
const pts = prices.map((p, i) => `${(i / (prices.length - 1)) * W},${H - ((p - min) / range) * H}`).join(” “);
const isPos = prices[prices.length - 1] >= prices[0];
const c = isPos ? “#16a34a” : “#ef4444”;
const step = Math.max(1, Math.floor(data.length / 4));
const labels = data.filter((_, i) => i % step === 0).slice(0, 5).map(d => d.date);
return (
<div>
<svg width=“100%” viewBox={`0 0 ${W} ${H}`} preserveAspectRatio=“none” style={{ display: “block” }}>
<defs><linearGradient id="ac" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={c} stopOpacity="0.13" /><stop offset="100%" stopColor={c} stopOpacity="0" /></linearGradient></defs>
<polygon points={`0,${H} ${pts} ${W},${H}`} fill=“url(#ac)” />
<polyline points={pts} fill="none" stroke={c} strokeWidth="2" strokeLinejoin="round" />
</svg>
<div style={{ display: “flex”, justifyContent: “space-between”, paddingTop: 4, fontSize: 10, color: “#94a3b8” }}>
{labels.map((l, i) => <span key={i}>{l}</span>)}
</div>
</div>
);
}

function FairValueBar({ models, currentPrice }) {
const allVals = […Object.values(models), currentPrice];
const min = Math.min(…allVals) * 0.96;
const max = Math.max(…allVals) * 1.04;
const range = max - min;
const toX = (v) => `${((v - min) / range) * 100}%`;
const MODEL_LABELS = { dcf: “DCF”, graham: “Graham”, lynch: “Lynch”, evEbitda: “EV/EBITDA”, earningsPower: “Earnings Power”, multiples: “Multiples” };
const modelColors = [”#2563eb”,”#16a34a”,”#f59e0b”,”#8b5cf6”,”#0891b2”,”#ea580c”];
const entries = Object.entries(models);
return (
<div>
<div style={{ position: “relative”, height: 40, marginBottom: 10 }}>
<div style={{ position: “absolute”, top: 18, left: 0, right: 0, height: 4, background: “#f1f5f9”, borderRadius: 4 }} />
{entries.map(([key, val], i) => (
<div key={key} title={`${MODEL_LABELS[key]}: $${val}`} style={{ position: “absolute”, top: 12, left: toX(val), transform: “translateX(-50%)”, width: 14, height: 14, borderRadius: “50%”, background: modelColors[i], border: “2px solid #fff”, boxShadow: “0 1px 3px rgba(0,0,0,0.15)”, cursor: “default”, zIndex: 2 }} />
))}
<div style={{ position: “absolute”, top: 8, left: toX(currentPrice), transform: “translateX(-50%)”, zIndex: 5 }}>
<div style={{ width: 20, height: 20, borderRadius: “50%”, background: “#0f172a”, border: “2px solid #fff”, boxShadow: “0 2px 6px rgba(0,0,0,0.2)” }} />
<div style={{ position: “absolute”, top: 22, left: “50%”, transform: “translateX(-50%)”, fontSize: 9, fontWeight: 700, color: “#0f172a”, whiteSpace: “nowrap” }}>Cena</div>
</div>
</div>
<div style={{ display: “flex”, flexWrap: “wrap”, gap: “6px 12px” }}>
{entries.map(([key, val], i) => (
<div key={key} style={{ display: “flex”, alignItems: “center”, gap: 5 }}>
<div style={{ width: 8, height: 8, borderRadius: “50%”, background: modelColors[i] }} />
<span style={{ fontSize: 10, color: “#64748b” }}>{MODEL_LABELS[key]}</span>
<span style={{ fontSize: 10, fontWeight: 700, color: “#0f172a” }}>${val}</span>
</div>
))}
</div>
</div>
);
}

function DonutChart({ segments, size = 140 }) {
const r = 50, cx = size / 2, cy = size / 2, circumference = 2 * Math.PI * r;
const total = segments.reduce((s, x) => s + x.value, 0);
let offset = 0;
const arcs = segments.map(seg => {
const pct = total > 0 ? seg.value / total : 0;
const dash = Math.max(pct * circumference - 2, 0);
const arc = { …seg, dash, space: circumference - dash, offset };
offset += pct * circumference;
return arc;
});
return (
<svg width={size} height={size} style={{ transform: “rotate(-90deg)” }}>
<circle cx={cx} cy={cy} r={r} fill="none" stroke="#f1f5f9" strokeWidth="16" />
{arcs.map((arc, i) => (
<circle key={i} cx={cx} cy={cy} r={r} fill=“none” stroke={arc.color} strokeWidth=“16”
strokeDasharray={`${arc.dash} ${arc.space}`} strokeDashoffset={-arc.offset}
style={{ transition: “all 0.5s ease” }} />
))}
</svg>
);
}

// ─── Alerts ──────────────────────────────────────────────────────────────────
function generateAlerts(stocks, prices) {
const alerts = [];
stocks.forEach(s => {
const p = prices[s.ticker];
if (!p) return;
const fv = calcFairValue(s.buyPrice, p.changePercent);
const avg = avgFairValue(fv);
if (p.price < avg * 0.95) alerts.push({ ticker: s.ticker, type: “fairvalue”, msg: `Cena pod férovou hodnotou (${fmtUSD(avg)})`, color: “#16a34a”, icon: “📉” });
if (Math.abs(p.changePercent) > 3) alerts.push({ ticker: s.ticker, type: “move”, msg: `Velký pohyb: ${fmtPct(p.changePercent)} dnes`, color: p.changePercent > 0 ? “#16a34a” : “#ef4444”, icon: p.changePercent > 0 ? “🚀” : “⚠️” });
});
return alerts;
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
const [stocks, setStocks] = useState([
{ id: 1, ticker: “AAPL”, shares: 10, buyPrice: 175.00, buyDate: “2024-01-15” },
{ id: 2, ticker: “MSFT”, shares: 5, buyPrice: 380.00, buyDate: “2024-03-10” },
{ id: 3, ticker: “NVDA”, shares: 3, buyPrice: 550.00, buyDate: “2024-06-01” },
]);
const [prices, setPrices] = useState({});
const [histories, setHistories] = useState({});
const [loading, setLoading] = useState(false);
const [activeTab, setActiveTab] = useState(“dashboard”);
const [selectedStock, setSelectedStock] = useState(null);
const [lastUpdate, setLastUpdate] = useState(null);
const [showModal, setShowModal] = useState(false);
const [editId, setEditId] = useState(null);
const [form, setForm] = useState({ ticker: “”, shares: “”, buyPrice: “”, buyDate: “” });
const [activeDetailTab, setActiveDetailTab] = useState(“chart”);

const fetchAll = useCallback(async () => {
setLoading(true);
const np = { …prices }, nh = { …histories };
const tickers = […new Set(stocks.map(s => s.ticker.toUpperCase()))];
await Promise.all(tickers.map(async (t) => {
const [q, h] = await Promise.all([fetchQuote(t), fetchHistory(t)]);
if (q) np[t] = q;
if (h?.length > 1) nh[t] = h;
}));
setPrices(np); setHistories(nh); setLastUpdate(new Date()); setLoading(false);
}, [stocks]);

useEffect(() => { if (stocks.length > 0) fetchAll(); }, [stocks.length]);

// Portfolio metrics
const totalValue = stocks.reduce((s, x) => s + (prices[x.ticker]?.price || x.buyPrice) * x.shares, 0);
const totalCost = stocks.reduce((s, x) => s + x.buyPrice * x.shares, 0);
const totalGain = totalValue - totalCost;
const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;
const dailyChange = stocks.reduce((s, x) => s + (prices[x.ticker]?.change || 0) * x.shares, 0);
const dailyChangePct = totalValue > 0 ? (dailyChange / (totalValue - dailyChange)) * 100 : 0;

// Alerts
const alerts = generateAlerts(stocks, prices);

// Sector allocation
const sectorMap = {};
stocks.forEach(s => {
const sec = getSector(s.ticker);
const val = (prices[s.ticker]?.price || s.buyPrice) * s.shares;
sectorMap[sec] = (sectorMap[sec] || 0) + val;
});
const sectorSegments = Object.entries(sectorMap).map(([name, value]) => ({ name, value, color: SECTOR_COLORS[name] || “#94a3b8” }));

const addOrEdit = () => {
if (!form.ticker || !form.shares || !form.buyPrice) return;
const ticker = form.ticker.toUpperCase();
if (editId) {
setStocks(prev => prev.map(s => s.id === editId ? { …s, ticker, shares: parseFloat(form.shares), buyPrice: parseFloat(form.buyPrice), buyDate: form.buyDate } : s));
setEditId(null);
} else {
setStocks(prev => […prev, { id: Date.now(), ticker, shares: parseFloat(form.shares), buyPrice: parseFloat(form.buyPrice), buyDate: form.buyDate }]);
}
setForm({ ticker: “”, shares: “”, buyPrice: “”, buyDate: “” });
setShowModal(false);
};

const removeStock = (id) => { setStocks(p => p.filter(s => s.id !== id)); if (selectedStock?.id === id) setSelectedStock(null); };
const startEdit = (s) => { setEditId(s.id); setForm({ ticker: s.ticker, shares: String(s.shares), buyPrice: String(s.buyPrice), buyDate: s.buyDate }); setShowModal(true); };
const closeModal = () => { setShowModal(false); setEditId(null); setForm({ ticker: “”, shares: “”, buyPrice: “”, buyDate: “” }); };

const selIdx = selectedStock ? stocks.findIndex(s => s.id === selectedStock.id) : -1;
const selExists = selIdx !== -1;

return (
<div style={{ minHeight: “100vh”, background: “#f1f5f9”, fontFamily: “‘Inter’,system-ui,sans-serif”, color: “#0f172a” }}>
<style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap'); *{box-sizing:border-box;margin:0;padding:0} ::-webkit-scrollbar{width:5px} ::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:4px} input,button{font-family:inherit;outline:none} .tab{background:none;border:none;padding:8px 15px;font-size:13px;font-weight:500;color:#64748b;border-radius:8px;cursor:pointer;transition:all .15s} .tab:hover{background:#f1f5f9;color:#0f172a} .tab.active{background:#fff;color:#16a34a;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.08)} .card{background:#fff;border-radius:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);border:1px solid #e8edf3} .btn{border:none;border-radius:10px;padding:10px 18px;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s} .btn-green{background:#16a34a;color:#fff} .btn-green:hover{background:#15803d;box-shadow:0 4px 12px #16a34a33} .btn-outline{background:#fff;color:#475569;border:1px solid #e2e8f0} .btn-outline:hover{background:#f8fafc} .btn-sm{background:none;border:none;font-size:12px;padding:5px 9px;border-radius:7px;cursor:pointer} .input{background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:10px;padding:10px 14px;font-size:13px;color:#0f172a;width:100%;transition:all .15s} .input:focus{border-color:#16a34a;background:#fff;box-shadow:0 0 0 3px #16a34a18} .lbl{font-size:11px;font-weight:600;color:#64748b;letter-spacing:.4px;margin-bottom:5px;display:block} .overlay{position:fixed;inset:0;background:rgba(15,23,42,.35);backdrop-filter:blur(4px);z-index:200;display:flex;align-items:center;justify-content:center;animation:fadeIn .15s} .modal{background:#fff;border-radius:20px;padding:28px;width:100%;max-width:440px;box-shadow:0 24px 60px rgba(0,0,0,.16);animation:slideUp .2s ease} .trow{display:grid;padding:11px 16px;align-items:center;border-bottom:1px solid #f1f5f9;transition:background .1s;cursor:pointer} .trow:hover{background:#f8fafc} .trow:last-child{border-bottom:none} .thead{display:grid;padding:8px 16px;font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:.8px;border-bottom:1px solid #f1f5f9;background:#fafafa;text-transform:uppercase} .dtab{background:none;border:none;padding:6px 12px;font-size:12px;font-weight:500;color:#64748b;border-radius:7px;cursor:pointer;transition:all .15s} .dtab:hover{background:#f1f5f9} .dtab.active{background:#f0fdf4;color:#16a34a;font-weight:600} @keyframes fadeIn{from{opacity:0}to{opacity:1}} @keyframes slideUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}} @keyframes slideIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}} .slide-in{animation:slideIn .22s ease forwards} @keyframes spin{to{transform:rotate(360deg)}} .spin{animation:spin .7s linear infinite;display:inline-block} .alert-item{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;border-radius:10px;margin-bottom:7px}`}</style>

```
  {/* ── Navbar ── */}
  <nav style={{ background:"#fff", borderBottom:"1px solid #e8edf3", padding:"0 24px", position:"sticky", top:0, zIndex:100 }}>
    <div style={{ maxWidth:1120, margin:"0 auto", display:"flex", alignItems:"center", justifyContent:"space-between", height:58 }}>
      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
        <div style={{ width:32, height:32, background:"linear-gradient(135deg,#16a34a,#059669)", borderRadius:9, display:"flex", alignItems:"center", justifyContent:"center", fontSize:15 }}>📈</div>
        <span style={{ fontFamily:"'Manrope',sans-serif", fontWeight:800, fontSize:16, letterSpacing:"-0.4px" }}>Portfolia</span>
        {alerts.length > 0 && (
          <div style={{ background:"#ef4444", color:"#fff", borderRadius:20, fontSize:10, fontWeight:700, padding:"1px 7px", marginLeft:2 }}>{alerts.length}</div>
        )}
      </div>
      <div style={{ display:"flex", gap:2, background:"#f1f5f9", borderRadius:11, padding:3 }}>
        {[["dashboard","Přehled"],["positions","Pozice"],["fairvalue","Férová hodnota"],["allocation","Alokace"],["alerts","Alerty"]].map(([id, label]) => (
          <button key={id} className={`tab ${activeTab===id?"active":""}`} onClick={()=>setActiveTab(id)} style={{ position:"relative" }}>
            {label}
            {id === "alerts" && alerts.length > 0 && <span style={{ position:"absolute", top:4, right:4, width:6, height:6, borderRadius:"50%", background:"#ef4444" }} />}
          </button>
        ))}
      </div>
      <div style={{ display:"flex", gap:8 }}>
        <button className="btn btn-outline" style={{ padding:"7px 13px", fontSize:12, display:"flex", alignItems:"center", gap:5 }} onClick={fetchAll} disabled={loading}>
          <span className={loading?"spin":""}>↻</span> Obnovit
        </button>
        <button className="btn btn-green" style={{ padding:"7px 14px", fontSize:12 }} onClick={()=>setShowModal(true)}>+ Přidat akcii</button>
      </div>
    </div>
  </nav>

  <div style={{ maxWidth:1120, margin:"0 auto", padding:"24px 24px" }}>

    {/* ═══════════════════ DASHBOARD ═══════════════════ */}
    {activeTab === "dashboard" && (
      <div className="slide-in">
        {/* KPI row */}
        <div style={{ display:"grid", gridTemplateColumns:"2fr 1fr 1fr 1fr", gap:14, marginBottom:18 }}>
          <div className="card" style={{ padding:24, background:"linear-gradient(135deg,#16a34a,#059669)", color:"#fff", border:"none" }}>
            <div style={{ fontSize:11, fontWeight:600, opacity:.75, marginBottom:5, letterSpacing:.6 }}>CELKOVÁ HODNOTA PORTFOLIA</div>
            <div style={{ fontFamily:"'Manrope',sans-serif", fontSize:32, fontWeight:800, letterSpacing:"-1px", marginBottom:10 }}>{fmtUSD(totalValue)}</div>
            <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
              <span style={{ background:"rgba(255,255,255,.22)", borderRadius:20, padding:"3px 11px", fontSize:12, fontWeight:600 }}>
                {dailyChange>=0?"▲":"▼"} {fmtUSD(Math.abs(dailyChange))} dnes
              </span>
              <span style={{ fontSize:12, opacity:.8, alignSelf:"center" }}>({fmtPct(dailyChangePct)})</span>
            </div>
          </div>
          {[
            { l:"INVESTOVÁNO", v:fmtUSD(totalCost), s:`${stocks.length} pozic`, c:null },
            { l:"ZISK / ZTRÁTA", v:`${totalGain>=0?"+":""}${fmtUSD(totalGain)}`, s:fmtPct(totalGainPct), c:totalGain>=0?"#16a34a":"#ef4444" },
            { l:"AKTIVNÍ ALERTY", v:String(alerts.length), s:alerts.length>0?"klikni na Alerty":"vše v pořádku", c:alerts.length>0?"#ef4444":null },
          ].map(({l,v,s,c})=>(
            <div key={l} className="card" style={{ padding:20 }}>
              <div style={{ fontSize:10, fontWeight:700, color:"#94a3b8", letterSpacing:.9, marginBottom:8 }}>{l}</div>
              <div style={{ fontFamily:"'Manrope',sans-serif", fontSize:22, fontWeight:800, color:c||"#0f172a", letterSpacing:"-0.4px" }}>{v}</div>
              <div style={{ fontSize:12, color:"#94a3b8", marginTop:5 }}>{s}</div>
            </div>
          ))}
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 320px", gap:14 }}>
          {/* Table */}
          <div className="card" style={{ overflow:"hidden" }}>
            <div style={{ padding:"15px 18px 12px", borderBottom:"1px solid #f1f5f9", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14 }}>Pozice</div>
              {lastUpdate && <div style={{ fontSize:11, color:"#94a3b8" }}>↻ {lastUpdate.toLocaleTimeString("cs-CZ",{hour:"2-digit",minute:"2-digit"})}</div>}
            </div>
            <div className="thead" style={{ gridTemplateColumns:"1fr 75px 90px 90px 90px 80px" }}>
              <span>Akcie</span><span style={{textAlign:"right"}}>30D</span><span style={{textAlign:"right"}}>Cena</span><span style={{textAlign:"right"}}>Hodnota</span><span style={{textAlign:"right"}}>Výnos</span><span style={{textAlign:"right"}}>Skóre</span>
            </div>
            {stocks.length === 0 ? (
              <div style={{ padding:"50px 20px", textAlign:"center", color:"#94a3b8" }}>
                <div style={{ fontSize:26, marginBottom:8 }}>📊</div><div style={{ fontSize:13 }}>Přidejte svou první akcii</div>
              </div>
            ) : stocks.map((s,i)=>{
              const p = prices[s.ticker];
              const cur = p?.price || s.buyPrice;
              const gainPct = ((cur-s.buyPrice)/s.buyPrice)*100;
              const pos = gainPct>=0;
              const fv = calcFairValue(s.buyPrice, p?.changePercent||0);
              const score = opportunityScore(cur, avgFairValue(fv));
              const scoreColor = score>=7?"#16a34a":score>=5?"#f59e0b":"#ef4444";
              return (
                <div key={s.id} className="trow" style={{ gridTemplateColumns:"1fr 75px 90px 90px 90px 80px" }}
                  onClick={()=>{ setSelectedStock(selectedStock?.id===s.id?null:s); setActiveTab("positions"); }}>
                  <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                    <div style={{ width:34,height:34,borderRadius:10,background:`${PALETTE[i%PALETTE.length]}14`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:700,color:PALETTE[i%PALETTE.length],flexShrink:0 }}>
                      {s.ticker.slice(0,3)}
                    </div>
                    <div>
                      <div style={{ fontSize:13,fontWeight:600 }}>{s.ticker}</div>
                      <div style={{ fontSize:11,color:"#94a3b8" }}>{s.shares} ks · {getSector(s.ticker)}</div>
                    </div>
                  </div>
                  <div style={{ display:"flex", justifyContent:"flex-end" }}>
                    <Sparkline data={histories[s.ticker]} positive={pos} id={`d${i}`} />
                  </div>
                  <div style={{ textAlign:"right" }}>
                    <div style={{ fontSize:13,fontWeight:600 }}>{fmtUSD(cur)}</div>
                    <div style={{ fontSize:11, color:p?.changePercent>=0?"#16a34a":"#ef4444" }}>{p?fmtPct(p.changePercent):"—"}</div>
                  </div>
                  <div style={{ textAlign:"right", fontSize:13, fontWeight:600 }}>{fmtUSD(cur*s.shares)}</div>
                  <div style={{ textAlign:"right" }}><Pill value={gainPct} suffix="%" /></div>
                  <div style={{ textAlign:"right" }}>
                    <span style={{ fontSize:13,fontWeight:800,color:scoreColor }}>{score.toFixed(1)}</span>
                    <span style={{ fontSize:10,color:"#94a3b8" }}>/10</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right: sector donut + alerts */}
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <div className="card" style={{ padding:20 }}>
              <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14, marginBottom:14 }}>Sektory</div>
              <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                <DonutChart segments={sectorSegments} />
                <div style={{ flex:1, display:"flex", flexDirection:"column", gap:7 }}>
                  {sectorSegments.map((seg)=>{
                    const pct = totalValue>0?(seg.value/totalValue)*100:0;
                    return (
                      <div key={seg.name} style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                          <div style={{ width:8,height:8,borderRadius:2,background:seg.color }} />
                          <span style={{ fontSize:12,fontWeight:500,color:"#475569" }}>{seg.name}</span>
                        </div>
                        <span style={{ fontSize:12,fontWeight:700,color:"#0f172a" }}>{pct.toFixed(0)}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {alerts.length > 0 && (
              <div className="card" style={{ padding:18 }}>
                <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14, marginBottom:12 }}>Alerty</div>
                {alerts.slice(0,3).map((a,i)=>(
                  <div key={i} className="alert-item" style={{ background:`${a.color}0f`, border:`1px solid ${a.color}25` }}>
                    <span style={{ fontSize:14 }}>{a.icon}</span>
                    <div>
                      <div style={{ fontSize:12,fontWeight:700,color:"#0f172a" }}>{a.ticker}</div>
                      <div style={{ fontSize:11,color:"#64748b" }}>{a.msg}</div>
                    </div>
                  </div>
                ))}
                {alerts.length>3 && <div style={{ fontSize:11,color:"#94a3b8",textAlign:"center",paddingTop:4 }}>+{alerts.length-3} dalších alertů</div>}
              </div>
            )}
          </div>
        </div>
      </div>
    )}

    {/* ═══════════════════ POSITIONS ═══════════════════ */}
    {activeTab === "positions" && (
      <div className="slide-in">
        <div style={{ display:"grid", gridTemplateColumns: selExists ? "1fr 380px" : "1fr", gap:18 }}>
          <div className="card" style={{ overflow:"hidden" }}>
            <div style={{ padding:"15px 18px 12px", borderBottom:"1px solid #f1f5f9", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14 }}>Všechny pozice</div>
              <button className="btn btn-green" style={{ padding:"6px 14px", fontSize:12 }} onClick={()=>setShowModal(true)}>+ Přidat</button>
            </div>
            {stocks.length === 0 ? (
              <div style={{ padding:"60px 20px", textAlign:"center", color:"#94a3b8" }}>
                <div style={{ fontSize:28,marginBottom:8 }}>📊</div>
                <div style={{ fontSize:14,fontWeight:500,marginBottom:4 }}>Žádné pozice</div>
              </div>
            ) : (
              <>
                <div className="thead" style={{ gridTemplateColumns:"1fr 75px 100px 85px 110px 70px" }}>
                  <span>Akcie</span><span style={{textAlign:"right"}}>30D</span><span style={{textAlign:"right"}}>Cena / dnes</span><span style={{textAlign:"right"}}>Hodnota</span><span style={{textAlign:"right"}}>Zisk/ztráta</span><span />
                </div>
                {stocks.map((s,i)=>{
                  const p = prices[s.ticker];
                  const cur = p?.price||s.buyPrice;
                  const gain = (cur-s.buyPrice)*s.shares;
                  const gainPct = ((cur-s.buyPrice)/s.buyPrice)*100;
                  const pos = gain>=0;
                  const sel = selectedStock?.id===s.id;
                  return (
                    <div key={s.id} className="trow" style={{ gridTemplateColumns:"1fr 75px 100px 85px 110px 70px", background:sel?"#f0fdf4":undefined }}
                      onClick={()=>setSelectedStock(sel?null:s)}>
                      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                        <div style={{ width:36,height:36,borderRadius:10,background:`${PALETTE[i%PALETTE.length]}14`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:700,color:PALETTE[i%PALETTE.length],flexShrink:0 }}>
                          {s.ticker.slice(0,3)}
                        </div>
                        <div>
                          <div style={{ fontSize:13,fontWeight:600 }}>{s.ticker}</div>
                          <div style={{ fontSize:11,color:"#94a3b8" }}>{s.shares} ks · koupeno {fmtUSD(s.buyPrice)}</div>
                        </div>
                      </div>
                      <div style={{ display:"flex", justifyContent:"flex-end", alignItems:"center" }}>
                        <Sparkline data={histories[s.ticker]} positive={pos} id={`p${i}`} />
                      </div>
                      <div style={{ textAlign:"right" }}>
                        <div style={{ fontSize:13,fontWeight:600 }}>{fmtUSD(cur)}</div>
                        <div style={{ fontSize:11,color:(p?.changePercent??0)>=0?"#16a34a":"#ef4444" }}>{p?fmtPct(p.changePercent):"—"}</div>
                      </div>
                      <div style={{ textAlign:"right", fontSize:13, fontWeight:600 }}>{fmtUSD(cur*s.shares)}</div>
                      <div style={{ textAlign:"right" }}>
                        <div style={{ fontSize:12,fontWeight:600,color:pos?"#16a34a":"#ef4444" }}>{pos?"+":""}{fmtUSD(gain)}</div>
                        <Pill value={gainPct} suffix="%" />
                      </div>
                      <div style={{ display:"flex", gap:4, justifyContent:"flex-end" }} onClick={e=>e.stopPropagation()}>
                        <button className="btn-sm" style={{ color:"#64748b" }} onClick={()=>startEdit(s)}>✎</button>
                        <button className="btn-sm" style={{ color:"#ef4444", background:"#fef2f2", border:"1px solid #fecaca" }} onClick={()=>removeStock(s.id)}>✕</button>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>

          {/* Detail panel */}
          {selExists && (()=>{
            const s = selectedStock;
            const p = prices[s.ticker];
            const cur = p?.price||s.buyPrice;
            const gain = (cur-s.buyPrice)*s.shares;
            const gainPct = ((cur-s.buyPrice)/s.buyPrice)*100;
            const pos = gain>=0;
            const color = PALETTE[selIdx%PALETTE.length];
            const fv = calcFairValue(s.buyPrice, p?.changePercent||0);
            const avgFV = avgFairValue(fv);
            const score = opportunityScore(cur, avgFV);
            const upside = ((avgFV-cur)/cur)*100;
            return (
              <div className="slide-in">
                <div className="card" style={{ padding:22, position:"sticky", top:72 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:16 }}>
                    <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                      <div style={{ width:44,height:44,borderRadius:12,background:`${color}14`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,fontWeight:700,color }}>{s.ticker.slice(0,3)}</div>
                      <div>
                        <div style={{ fontFamily:"'Manrope',sans-serif", fontSize:19, fontWeight:800 }}>{s.ticker}</div>
                        <div style={{ fontSize:11,color:"#94a3b8" }}>{getSector(s.ticker)} · {s.buyDate||"—"}</div>
                      </div>
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                      <ScoreBadge score={score} />
                      <button className="btn-sm" style={{ color:"#94a3b8", fontSize:16 }} onClick={()=>setSelectedStock(null)}>✕</button>
                    </div>
                  </div>

                  {/* Detail tabs */}
                  <div style={{ display:"flex", gap:4, marginBottom:14, background:"#f8fafc", borderRadius:9, padding:3 }}>
                    {[["chart","Graf"],["fairvalue","Férová hodnota"],["metrics","Metriky"]].map(([id,label])=>(
                      <button key={id} className={`dtab ${activeDetailTab===id?"active":""}`} style={{ flex:1 }} onClick={()=>setActiveDetailTab(id)}>{label}</button>
                    ))}
                  </div>

                  {activeDetailTab === "chart" && (
                    <div>
                      <AreaChart data={histories[s.ticker]} />
                    </div>
                  )}

                  {activeDetailTab === "fairvalue" && (
                    <div>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
                        <div>
                          <div style={{ fontSize:11,color:"#94a3b8",marginBottom:2 }}>Průměrná férová hodnota</div>
                          <div style={{ fontFamily:"'Manrope',sans-serif", fontSize:22,fontWeight:800,color:upside>0?"#16a34a":"#ef4444" }}>{fmtUSD(avgFV)}</div>
                        </div>
                        <div style={{ textAlign:"right" }}>
                          <div style={{ fontSize:11,color:"#94a3b8",marginBottom:2 }}>Upside / Downside</div>
                          <div style={{ fontSize:18,fontWeight:700,color:upside>0?"#16a34a":"#ef4444" }}>{upside>=0?"+":""}{upside.toFixed(1)}%</div>
                        </div>
                      </div>
                      <FairValueBar models={fv} currentPrice={cur} />
                      <div style={{ marginTop:12, padding:"8px 12px", background: upside>5?"#f0fdf4":upside>-5?"#fefce8":"#fef2f2", borderRadius:10, fontSize:11, color: upside>5?"#16a34a":upside>-5?"#92400e":"#ef4444" }}>
                        {upside>5?"📉 Akcie se zdá podhodnocená — potenciální příležitost":upside>-5?"⚖️ Akcie je přibližně na férové hodnotě":"💸 Akcie se zdá nadhodnocená dle modelů"}
                      </div>
                    </div>
                  )}

                  {activeDetailTab === "metrics" && (
                    <div style={{ background:"#f8fafc", borderRadius:12, overflow:"hidden" }}>
                      {[
                        ["Aktuální cena", fmtUSD(cur), null],
                        ["Nákupní cena", fmtUSD(s.buyPrice), null],
                        ["Počet kusů", `${s.shares} ks`, null],
                        ["Investováno", fmtUSD(s.buyPrice*s.shares), null],
                        ["Aktuální hodnota", fmtUSD(cur*s.shares), null],
                        ["Zisk / ztráta", `${pos?"+":""}${fmtUSD(gain)}`, pos?"#16a34a":"#ef4444"],
                        ["Výnos %", fmtPct(gainPct), pos?"#16a34a":"#ef4444"],
                        ...(p?[["Dnešní pohyb", fmtPct(p.changePercent), p.changePercent>=0?"#16a34a":"#ef4444"]]:[] ),
                        ["Opportunity Score", `${score.toFixed(1)}/10`, score>=7?"#16a34a":score>=5?"#f59e0b":"#ef4444"],
                      ].map(([label,v,col],i,arr)=>(
                        <div key={label} style={{ display:"flex", justifyContent:"space-between", padding:"9px 14px", borderBottom:i<arr.length-1?"1px solid #f1f5f9":"none" }}>
                          <span style={{ fontSize:12,color:"#64748b" }}>{label}</span>
                          <span style={{ fontSize:12,fontWeight:600,color:col||"#0f172a" }}>{v}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div style={{ display:"flex", gap:8, marginTop:14 }}>
                    <button className="btn btn-outline" style={{ flex:1,fontSize:12 }} onClick={()=>startEdit(s)}>✎ Upravit</button>
                    <button className="btn" style={{ background:"#fef2f2",color:"#ef4444",border:"1px solid #fecaca",fontSize:12 }} onClick={()=>removeStock(s.id)}>Odstranit</button>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    )}

    {/* ═══════════════════ FAIR VALUE ═══════════════════ */}
    {activeTab === "fairvalue" && (
      <div className="slide-in">
        <div style={{ marginBottom:16 }}>
          <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:800, fontSize:20, marginBottom:4 }}>Férová hodnota</div>
          <div style={{ fontSize:13, color:"#64748b" }}>Porovnání aktuální ceny s odhadnutou férovou hodnotou z 6 valuačních modelů.</div>
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {stocks.map((s,i)=>{
            const p = prices[s.ticker];
            const cur = p?.price||s.buyPrice;
            const fv = calcFairValue(s.buyPrice, p?.changePercent||0);
            const avgFV = avgFairValue(fv);
            const upside = ((avgFV-cur)/cur)*100;
            const score = opportunityScore(cur, avgFV);
            const color = PALETTE[i%PALETTE.length];
            return (
              <div key={s.id} className="card" style={{ padding:22 }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:18 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                    <div style={{ width:44,height:44,borderRadius:12,background:`${color}14`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:12,fontWeight:700,color }}>
                      {s.ticker.slice(0,3)}
                    </div>
                    <div>
                      <div style={{ fontFamily:"'Manrope',sans-serif", fontSize:17,fontWeight:800 }}>{s.ticker}</div>
                      <div style={{ fontSize:12,color:"#94a3b8" }}>{getSector(s.ticker)}</div>
                    </div>
                  </div>
                  <div style={{ display:"flex", gap:24, alignItems:"center" }}>
                    <div style={{ textAlign:"right" }}>
                      <div style={{ fontSize:11,color:"#94a3b8",marginBottom:2 }}>Aktuální cena</div>
                      <div style={{ fontSize:18,fontWeight:700 }}>{fmtUSD(cur)}</div>
                    </div>
                    <div style={{ textAlign:"right" }}>
                      <div style={{ fontSize:11,color:"#94a3b8",marginBottom:2 }}>Férová hodnota</div>
                      <div style={{ fontSize:18,fontWeight:700,color:upside>0?"#16a34a":"#ef4444" }}>{fmtUSD(avgFV)}</div>
                    </div>
                    <div style={{ textAlign:"right" }}>
                      <div style={{ fontSize:11,color:"#94a3b8",marginBottom:2 }}>Upside</div>
                      <div style={{ fontSize:18,fontWeight:700,color:upside>0?"#16a34a":"#ef4444" }}>{upside>=0?"+":""}{upside.toFixed(1)}%</div>
                    </div>
                    <ScoreBadge score={score} />
                  </div>
                </div>
                <FairValueBar models={fv} currentPrice={cur} />
                <div style={{ marginTop:12, padding:"8px 12px", background:upside>5?"#f0fdf4":upside>-5?"#fefce8":"#fef2f2", borderRadius:10, fontSize:12, color:upside>5?"#16a34a":upside>-5?"#92400e":"#ef4444", fontWeight:500 }}>
                  {upside>5?"📉 Podhodnocená — většina modelů vidí vyšší hodnotu":upside>-5?"⚖️ Na férové hodnotě — cena odpovídá odhadům":"💸 Nadhodnocená — cena překračuje modely"}
                </div>
              </div>
            );
          })}
          {stocks.length === 0 && (
            <div className="card" style={{ padding:"60px 20px", textAlign:"center", color:"#94a3b8" }}>
              <div style={{ fontSize:28,marginBottom:8 }}>🔍</div>
              <div style={{ fontSize:14,fontWeight:500 }}>Přidejte akcie pro analýzu férové hodnoty</div>
            </div>
          )}
        </div>
      </div>
    )}

    {/* ═══════════════════ ALLOCATION ═══════════════════ */}
    {activeTab === "allocation" && (
      <div className="slide-in">
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
          {/* By stock */}
          <div className="card" style={{ padding:24 }}>
            <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14, marginBottom:18 }}>Alokace podle akcií</div>
            {[...stocks].sort((a,b)=>(prices[b.ticker]?.price||b.buyPrice)*b.shares-(prices[a.ticker]?.price||a.buyPrice)*a.shares).map(s=>{
              const i = stocks.findIndex(x=>x.id===s.id);
              const val = (prices[s.ticker]?.price||s.buyPrice)*s.shares;
              const pct = totalValue>0?(val/totalValue)*100:0;
              const color = PALETTE[i%PALETTE.length];
              return (
                <div key={s.id} style={{ marginBottom:14 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                      <div style={{ width:9,height:9,borderRadius:2,background:color }} />
                      <span style={{ fontSize:13,fontWeight:600 }}>{s.ticker}</span>
                      <span style={{ fontSize:11,color:"#94a3b8" }}>{getSector(s.ticker)}</span>
                    </div>
                    <div style={{ display:"flex", gap:14 }}>
                      <span style={{ fontSize:12,color:"#64748b" }}>{fmtUSD(val)}</span>
                      <span style={{ fontSize:12,fontWeight:700,color }}>{pct.toFixed(1)}%</span>
                    </div>
                  </div>
                  <div style={{ background:"#f1f5f9",borderRadius:5,height:7,overflow:"hidden" }}>
                    <div style={{ width:`${pct}%`,height:"100%",background:color,borderRadius:5,transition:"width .6s ease" }} />
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            {/* By sector */}
            <div className="card" style={{ padding:24 }}>
              <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14, marginBottom:18 }}>Alokace podle sektorů</div>
              <div style={{ display:"flex", gap:20, alignItems:"center", marginBottom:16 }}>
                <DonutChart segments={sectorSegments} size={130} />
                <div style={{ flex:1 }}>
                  {sectorSegments.map(seg=>{
                    const pct = totalValue>0?(seg.value/totalValue)*100:0;
                    return (
                      <div key={seg.name} style={{ marginBottom:9 }}>
                        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                          <div style={{ display:"flex",alignItems:"center",gap:6 }}>
                            <div style={{ width:8,height:8,borderRadius:2,background:seg.color }} />
                            <span style={{ fontSize:12,fontWeight:500,color:"#475569" }}>{seg.name}</span>
                          </div>
                          <span style={{ fontSize:12,fontWeight:700,color:seg.color }}>{pct.toFixed(0)}%</span>
                        </div>
                        <div style={{ background:"#f1f5f9",borderRadius:4,height:5,overflow:"hidden" }}>
                          <div style={{ width:`${pct}%`,height:"100%",background:seg.color,borderRadius:4,transition:"width .6s ease" }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Summary */}
            <div className="card" style={{ padding:20 }}>
              <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:14, marginBottom:14 }}>Souhrn portfolia</div>
              {[
                ["Celková hodnota", fmtUSD(totalValue), null],
                ["Celkem investováno", fmtUSD(totalCost), null],
                ["Zisk / ztráta", `${totalGain>=0?"+":""}${fmtUSD(totalGain)}`, totalGain>=0?"#16a34a":"#ef4444"],
                ["Výnos portfolia", fmtPct(totalGainPct), totalGainPct>=0?"#16a34a":"#ef4444"],
                ["Počet pozic", String(stocks.length), null],
                ["Počet sektorů", String(sectorSegments.length), null],
              ].map(([label,v,col])=>(
                <div key={label} style={{ display:"flex",justifyContent:"space-between",padding:"8px 0",borderBottom:"1px solid #f1f5f9",fontSize:13 }}>
                  <span style={{ color:"#64748b" }}>{label}</span>
                  <span style={{ fontWeight:600,color:col||"#0f172a" }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )}

    {/* ═══════════════════ ALERTS ═══════════════════ */}
    {activeTab === "alerts" && (
      <div className="slide-in">
        <div style={{ marginBottom:16 }}>
          <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:800, fontSize:20, marginBottom:4 }}>Smart Alerty</div>
          <div style={{ fontSize:13,color:"#64748b" }}>Automatická upozornění na základě cen, férové hodnoty a pohybů trhu.</div>
        </div>
        {alerts.length === 0 ? (
          <div className="card" style={{ padding:"60px 20px", textAlign:"center", color:"#94a3b8" }}>
            <div style={{ fontSize:32,marginBottom:10 }}>🔔</div>
            <div style={{ fontSize:15,fontWeight:600,marginBottom:4,color:"#475569" }}>Žádné aktivní alerty</div>
            <div style={{ fontSize:13 }}>Vše v pořádku. Alerty se aktivují při výrazných pohybech nebo podhodnocení.</div>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {alerts.map((a,i)=>(
              <div key={i} className="card" style={{ padding:18, display:"flex", alignItems:"center", gap:16, borderLeft:`4px solid ${a.color}` }}>
                <div style={{ fontSize:24 }}>{a.icon}</div>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:3 }}>
                    <span style={{ fontWeight:700,fontSize:14 }}>{a.ticker}</span>
                    <span style={{ background:`${a.color}18`,color:a.color,borderRadius:20,padding:"1px 8px",fontSize:11,fontWeight:600 }}>
                      {a.type==="fairvalue"?"Férová hodnota":a.type==="move"?"Velký pohyb":"Alert"}
                    </span>
                  </div>
                  <div style={{ fontSize:13,color:"#64748b" }}>{a.msg}</div>
                </div>
                <div style={{ fontSize:11,color:"#94a3b8" }}>právě teď</div>
              </div>
            ))}
          </div>
        )}
        <div style={{ marginTop:20, padding:16, background:"#f8fafc", borderRadius:14, border:"1px solid #e2e8f0" }}>
          <div style={{ fontFamily:"'Manrope',sans-serif", fontWeight:700, fontSize:13, marginBottom:10, color:"#475569" }}>Typy alertů</div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:10 }}>
            {[
              ["📉","Cena pod F.H.","Akcie klesla pod odhadnutou férovou hodnotu"],
              ["🚀","Velký pohyb ↑","Akcie vzrostla o více než 3 % za den"],
              ["⚠️","Velký pohyb ↓","Akcie klesla o více než 3 % za den"],
            ].map(([icon,title,desc])=>(
              <div key={title} style={{ background:"#fff",borderRadius:10,padding:"12px 14px",border:"1px solid #e8edf3" }}>
                <div style={{ fontSize:18,marginBottom:5 }}>{icon}</div>
                <div style={{ fontSize:12,fontWeight:600,marginBottom:3 }}>{title}</div>
                <div style={{ fontSize:11,color:"#94a3b8" }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )}
  </div>

  {/* ── Modal ── */}
  {showModal && (
    <div className="overlay" onClick={closeModal}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:22 }}>
          <div style={{ fontFamily:"'Manrope',sans-serif", fontSize:18, fontWeight:800 }}>{editId?"Upravit pozici":"Přidat akcii"}</div>
          <button className="btn-sm" style={{ color:"#94a3b8", fontSize:16 }} onClick={closeModal}>✕</button>
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div>
            <label className="lbl">TICKER SYMBOLU *</label>
            <input className="input" placeholder="např. AAPL, TSLA, BMW.DE, CEZ.PR…" value={form.ticker} onChange={e=>setForm(f=>({...f,ticker:e.target.value.toUpperCase()}))} />
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <div>
              <label className="lbl">POČET KUSŮ *</label>
              <input className="input" type="number" min="0.001" step="0.001" placeholder="10" value={form.shares} onChange={e=>setForm(f=>({...f,shares:e.target.value}))} />
            </div>
            <div>
              <label className="lbl">NÁKUPNÍ CENA (USD) *</label>
              <input className="input" type="number" min="0" step="0.01" placeholder="150.00" value={form.buyPrice} onChange={e=>setForm(f=>({...f,buyPrice:e.target.value}))} />
            </div>
          </div>
          <div>
            <label className="lbl">DATUM NÁKUPU</label>
            <input className="input" type="date" value={form.buyDate} onChange={e=>setForm(f=>({...f,buyDate:e.target.value}))} />
          </div>
          <div style={{ display:"flex", gap:8, marginTop:4 }}>
            <button className="btn btn-green" style={{ flex:1 }} onClick={addOrEdit}>{editId?"Uložit změny":"Přidat akcii"}</button>
            <button className="btn btn-outline" onClick={closeModal}>Zrušit</button>
          </div>
        </div>
        <div style={{ marginTop:14, padding:"10px 14px", background:"#f0fdf4", borderRadius:10, fontSize:11, border:"1px solid #bbf7d0" }}>
          <span style={{ color:"#16a34a", fontWeight:600 }}>Živé ceny</span>
          <span style={{ color:"#64748b" }}> — funguje pro NYSE, NASDAQ, LSE, XETRA a další. Příklady: AAPL, TSLA, CEZ.PR, BMW.DE</span>
        </div>
      </div>
    </div>
  )}
</div>
```

);
}