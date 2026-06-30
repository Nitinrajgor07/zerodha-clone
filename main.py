import datetime
import pytz
import pandas as pd
import streamlit as st
import yfinance as yf

IST = pytz.timezone("Asia/Kolkata")

st.set_page_config(page_title="Market", page_icon="📈", layout="centered",
                    initial_sidebar_state="collapsed")

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#0f1116;--card:#1a1d27;--border:#262a38;--text:#e8eaf0;--muted:#8b90a0;--blue:#387ed1;--green:#2cb96a;--red:#e6483f;--radius:10px;}
html,body,[class*="css"],button,input,select,textarea{font-family:'Inter',-apple-system,sans-serif!important;}
[data-testid="stAppViewContainer"],[data-testid="stHeader"],.main{background:var(--bg)!important;}
.block-container{padding-top:8px!important;padding-bottom:90px!important;padding-left:14px!important;padding-right:14px!important;max-width:480px!important;}
#MainMenu,footer,header{visibility:hidden;}
div[data-testid="stVerticalBlock"]>div[data-testid="stElementContainer"]{margin-bottom:10px!important;}
div[data-testid="stButton"] button{border-radius:8px!important;border:1px solid var(--border)!important;background:var(--card)!important;color:var(--text)!important;font-weight:600!important;font-size:0.85rem!important;box-shadow:none!important;}
div[data-testid="stButton"] button[kind="primary"]{background:var(--blue)!important;border-color:var(--blue)!important;color:#fff!important;}
div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stSelectbox"]>div{background:var(--card)!important;border:1px solid var(--border)!important;color:var(--text)!important;border-radius:8px!important;}
.status-pill{display:inline-flex;align-items:center;gap:6px;font-size:0.72rem;font-weight:600;color:var(--muted);padding:4px 10px;border:1px solid var(--border);border-radius:20px;background:var(--card);}
.dot{width:7px;height:7px;border-radius:50%;}
.dot-live{background:var(--green);box-shadow:0 0 0 3px rgba(44,185,106,0.2);}
.dot-pre{background:#f0a500;box-shadow:0 0 0 3px rgba(240,165,0,0.2);}
.dot-closed{background:var(--red);}
.hero{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;margin:10px 0 14px;}
.hero-label{font-size:0.62rem;color:var(--muted);font-weight:600;letter-spacing:0.06em;}
.hero-value{font-size:1.6rem;font-weight:800;color:var(--text);margin-top:2px;}
.hero-sub{font-size:0.72rem;color:var(--muted);margin-top:2px;}
.sec-title{font-size:0.68rem;font-weight:700;color:var(--muted);letter-spacing:0.08em;text-transform:uppercase;margin:18px 0 8px;}
.row-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}
.row-item{display:flex;justify-content:space-between;align-items:center;padding:13px 14px;border-bottom:1px solid var(--border);}
.row-item:last-child{border-bottom:none;}
.row-name{font-size:0.88rem;font-weight:600;color:var(--text);}
.row-sub{font-size:0.7rem;color:var(--muted);margin-top:1px;}
.row-val{font-size:0.88rem;font-weight:700;text-align:right;}
.row-val-sub{font-size:0.7rem;text-align:right;margin-top:1px;}
.up{color:var(--green);}
.down{color:var(--red);}
</style>
""", unsafe_allow_html=True)

DEFAULT_WATCHLIST = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

if "watchlists" not in st.session_state:
    st.session_state.watchlists = {"Watchlist 1": DEFAULT_WATCHLIST.copy()}
if "active_watchlist" not in st.session_state:
    st.session_state.active_watchlist = list(st.session_state.watchlists.keys())[0]
if "holdings" not in st.session_state:
    st.session_state.holdings = {}
if "cash" not in st.session_state:
    st.session_state.cash = 100000.0
if "orders" not in st.session_state:
    st.session_state.orders = []
if "tab" not in st.session_state:
    st.session_state.tab = "home"
if "quick_order_ticker" not in st.session_state:
    st.session_state.quick_order_ticker = None
if "quick_order_side" not in st.session_state:
    st.session_state.quick_order_side = "BUY"


def market_status():
    now = datetime.datetime.now(IST)
    t = now.time()
    if now.weekday() >= 5:
        return "CLOSED", "dot-closed"
    pre_start = datetime.time(9, 8)
    pre_end = datetime.time(9, 15)
    close_t = datetime.time(15, 30)
    if pre_start <= t < pre_end:
        return "PRE-OPEN", "dot-pre"
    if pre_end <= t <= close_t:
        return "LIVE", "dot-live"
    return "CLOSED", "dot-closed"


@st.cache_data(ttl=30, show_spinner=False)
def fetch_prices(tickers):
    out = {}
    if not tickers:
        return out
    try:
        data = yf.download(list(tickers), period="2d", interval="1d",
                            progress=False, group_by="ticker", threads=True)
        for t in tickers:
            try:
                if len(tickers) == 1:
                    closes = data["Close"].dropna()
                else:
                    closes = data[t]["Close"].dropna()
                if len(closes) >= 2:
                    out[t] = {"price": float(closes.iloc[-1]), "prev": float(closes.iloc[-2])}
                elif len(closes) == 1:
                    out[t] = {"price": float(closes.iloc[-1]), "prev": float(closes.iloc[-1])}
            except Exception:
                continue
    except Exception:
        pass
    return out


def place_order(ticker, side, qty):
    t = ticker.strip().upper()
    if not t.endswith(".NS"):
        t += ".NS"
    p = fetch_prices((t,)).get(t, {})
    price = p.get("price")
    if price is None:
        return False, "Price nahi mila — ticker check karo."
    cost = price * qty
    h = st.session_state.holdings
    if side == "BUY":
        if cost > st.session_state.cash:
            return False, "Cash kam hai."
        st.session_state.cash -= cost
        if t in h:
            old_qty, old_avg = h[t]["shares"], h[t]["avg_price"]
            new_qty = old_qty + qty
            h[t]["avg_price"] = (old_qty * old_avg + cost) / new_qty
            h[t]["shares"] = new_qty
        else:
            h[t] = {"shares": qty, "avg_price": price}
    else:
        if t not in h or h[t]["shares"] < qty:
            return False, "Itni quantity holding mein nahi hai."
        h[t]["shares"] -= qty
        if h[t]["shares"] == 0:
            del h[t]
        st.session_state.cash += cost
    st.session_state.orders.insert(0, {"ticker": t, "side": side, "qty": qty, "price": price,
                                        "time": datetime.datetime.now(IST).strftime("%d %b, %I:%M %p")})
    return True, f"{side.title()} {qty} {t.replace('.NS','')} @ ₹{price:,.2f}"


def render_status_bar():
    label, dotcls = market_status()
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 2px 2px;">
      <span style="font-size:1.05rem;font-weight:800;color:var(--text);">Market</span>
      <span class="status-pill"><span class="dot {dotcls}"></span>{label}</span>
    </div>""", unsafe_allow_html=True)


def render_home():
    render_status_bar()
    holdings = st.session_state.holdings
    prices = fetch_prices(tuple(holdings.keys()))
    total_invested = total_current = day_pnl = prev_total = 0.0
    movers = []
    for tkr, h in holdings.items():
        invested = h["shares"] * h["avg_price"]
        total_invested += invested
        p = prices.get(tkr, {})
        cur = p.get("price", h["avg_price"])
        prev = p.get("prev", cur)
        cur_val = h["shares"] * cur
        total_current += cur_val
        day_pnl += (cur - prev) * h["shares"]
        prev_total += prev * h["shares"]
        pct = ((cur - prev) / prev * 100) if prev else 0.0
        movers.append((tkr, pct))
    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0.0
    day_pct = (day_pnl / prev_total * 100) if prev_total else 0.0
    pcolor = "up" if total_pnl >= 0 else "down"
    dcolor = "up" if day_pnl >= 0 else "down"

    st.markdown(f"""
    <div class="hero">
      <div class="hero-label">CURRENT VALUE</div>
      <div class="hero-value">₹{total_current:,.0f}</div>
      <div class="hero-sub">₹{total_invested:,.0f} invested · Cash ₹{st.session_state.cash:,.0f}</div>
      <div style="display:flex;gap:20px;margin-top:14px;border-top:1px solid var(--border);padding-top:12px;">
        <div><div class="hero-label">DAY'S P&amp;L</div>
          <div class="{dcolor}" style="font-weight:700;font-size:0.95rem;margin-top:2px;">₹{day_pnl:,.0f} ({day_pct:+.2f}%)</div>
        </div>
        <div><div class="hero-label">TOTAL P&amp;L</div>
          <div class="{pcolor}" style="font-weight:700;font-size:0.95rem;margin-top:2px;">₹{total_pnl:,.0f} ({total_pnl_pct:+.2f}%)</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    if movers:
        st.markdown('<div class="sec-title">Top Movers</div>', unsafe_allow_html=True)
        rows = ['<div class="row-card">']
        for tkr, pct in sorted(movers, key=lambda m: abs(m[1]), reverse=True)[:5]:
            cls = "up" if pct >= 0 else "down"
            arrow = "▲" if pct >= 0 else "▼"
            rows.append(f"""<div class="row-item"><span class="row-name">{tkr.replace('.NS','')}</span>
            <span class="row-val {cls}">{arrow} {abs(pct):.2f}%</span></div>""")
        rows.append("</div>")
        st.markdown("".join(rows), unsafe_allow_html=True)
    else:
        st.markdown('<div class="row-card" style="padding:20px;text-align:center;color:var(--muted);font-size:0.82rem;">Abhi koi holding nahi — Orders tab se shuru karo.</div>',
                    unsafe_allow_html=True)


def render_watchlist():
    render_status_bar()

    wl_names = list(st.session_state.watchlists.keys())
    tabs_html_cols = st.columns([4, 1])
    with tabs_html_cols[0]:
        active = st.selectbox("Watchlist", wl_names,
                               index=wl_names.index(st.session_state.active_watchlist),
                               label_visibility="collapsed")
        st.session_state.active_watchlist = active
    with tabs_html_cols[1]:
        if st.button("＋", use_container_width=True, help="Nayi watchlist banao"):
            st.session_state.show_new_wl = True

    if st.session_state.get("show_new_wl"):
        with st.form("new_wl_form", clear_on_submit=True):
            new_name = st.text_input("Naya naam", placeholder="e.g. Tech Stocks")
            c1, c2 = st.columns(2)
            with c1:
                ok = st.form_submit_button("Banao", type="primary", use_container_width=True)
            with c2:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            if ok and new_name.strip():
                if new_name.strip() not in st.session_state.watchlists:
                    st.session_state.watchlists[new_name.strip()] = []
                st.session_state.active_watchlist = new_name.strip()
                st.session_state.show_new_wl = False
                st.rerun()
            if cancel:
                st.session_state.show_new_wl = False
                st.rerun()

    if len(wl_names) > 1:
        with st.expander("Watchlist delete karo"):
            wl_del = st.selectbox("Select", wl_names, label_visibility="collapsed", key="wl_del_select")
            if st.button("Delete watchlist", key="wl_del_btn"):
                del st.session_state.watchlists[wl_del]
                st.session_state.active_watchlist = list(st.session_state.watchlists.keys())[0]
                st.rerun()

    active_list = st.session_state.watchlists[st.session_state.active_watchlist]

    st.markdown('<div class="sec-title">Add Stock</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([4, 1])
    with c1:
        new_t = st.text_input("Add stock", placeholder="e.g. WIPRO.NS", label_visibility="collapsed")
    with c2:
        if st.button("Add", use_container_width=True, type="primary"):
            if new_t.strip():
                t = new_t.strip().upper()
                if not t.endswith(".NS"):
                    t += ".NS"
                if t not in active_list:
                    active_list.append(t)
                st.rerun()

    if not active_list:
        st.markdown('<div class="row-card" style="padding:20px;text-align:center;color:var(--muted);font-size:0.82rem;">Is watchlist mein koi stock nahi — upar se add karo.</div>',
                    unsafe_allow_html=True)
        return

    prices = fetch_prices(tuple(active_list))
    for tkr in active_list:
        p = prices.get(tkr, {})
        cur = p.get("price")
        prev = p.get("prev")
        if cur is not None and prev:
            pct = (cur - prev) / prev * 100
            cls = "up" if pct >= 0 else "down"
            arrow = "▲" if pct >= 0 else "▼"
            price_html = f'₹{cur:,.2f}'
            chg_html = f'<span class="{cls}">{arrow} {abs(pct):.2f}%</span>'
        else:
            price_html = "—"
            chg_html = '<span style="color:var(--muted);">—</span>'

        row_box = st.container()
        with row_box:
            st.markdown(f"""<div class="row-card" style="margin-bottom:8px;">
              <div class="row-item" style="border-bottom:none;">
                <div><div class="row-name">{tkr.replace('.NS','')}</div></div>
                <div><div class="row-val">{price_html}</div><div class="row-val-sub">{chg_html}</div></div>
              </div></div>""", unsafe_allow_html=True)
            bc1, bc2, bc3 = st.columns([1, 1, 1])
            with bc1:
                if st.button("Buy", key=f"buy_{tkr}", use_container_width=True, type="primary"):
                    st.session_state.quick_order_ticker = tkr
                    st.session_state.quick_order_side = "BUY"
            with bc2:
                if st.button("Sell", key=f"sell_{tkr}", use_container_width=True):
                    st.session_state.quick_order_ticker = tkr
                    st.session_state.quick_order_side = "SELL"
            with bc3:
                if st.button("Remove", key=f"rm_{tkr}", use_container_width=True):
                    active_list.remove(tkr)
                    st.rerun()

            if st.session_state.quick_order_ticker == tkr:
                with st.form(f"qo_form_{tkr}", clear_on_submit=False):
                    qty = st.number_input(f"{st.session_state.quick_order_side} qty", min_value=1, value=1, step=1)
                    qc1, qc2 = st.columns(2)
                    with qc1:
                        conf = st.form_submit_button(f"Confirm {st.session_state.quick_order_side}",
                                                      type="primary", use_container_width=True)
                    with qc2:
                        canc = st.form_submit_button("Cancel", use_container_width=True)
                    if conf:
                        ok, msg = place_order(tkr, st.session_state.quick_order_side, qty)
                        (st.success if ok else st.error)(msg)
                        st.session_state.quick_order_ticker = None
                        st.rerun()
                    if canc:
                        st.session_state.quick_order_ticker = None
                        st.rerun()


def render_portfolio():
    render_status_bar()
    st.markdown('<div class="sec-title">Holdings</div>', unsafe_allow_html=True)
    holdings = st.session_state.holdings
    if not holdings:
        st.markdown('<div class="row-card" style="padding:20px;text-align:center;color:var(--muted);font-size:0.82rem;">Koi holding nahi — Orders tab se buy karo.</div>',
                    unsafe_allow_html=True)
        return
    prices = fetch_prices(tuple(holdings.keys()))
    rows = ['<div class="row-card">']
    for tkr, h in holdings.items():
        p = prices.get(tkr, {})
        cur = p.get("price", h["avg_price"])
        invested = h["shares"] * h["avg_price"]
        cur_val = h["shares"] * cur
        pnl = cur_val - invested
        pnl_pct = (pnl / invested * 100) if invested else 0.0
        cls = "up" if pnl >= 0 else "down"
        rows.append(f"""<div class="row-item">
          <div><div class="row-name">{tkr.replace('.NS','')}</div>
               <div class="row-sub">{h['shares']} qty · avg ₹{h['avg_price']:,.2f}</div></div>
          <div><div class="row-val">₹{cur_val:,.0f}</div>
               <div class="row-val-sub {cls}">{pnl:+,.0f} ({pnl_pct:+.2f}%)</div></div>
        </div>""")
    rows.append("</div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_orders():
    render_status_bar()
    st.markdown('<div class="sec-title">Place Order</div>', unsafe_allow_html=True)
    with st.form("order_form", clear_on_submit=True):
        tkr = st.text_input("Ticker", placeholder="e.g. RELIANCE.NS")
        c1, c2 = st.columns(2)
        with c1:
            side = st.selectbox("Side", ["BUY", "SELL"])
        with c2:
            qty = st.number_input("Qty", min_value=1, value=1, step=1)
        submitted = st.form_submit_button("Place order", type="primary", use_container_width=True)
        if submitted and tkr.strip():
            ok, msg = place_order(tkr, side, qty)
            (st.success if ok else st.error)(msg)

    st.markdown('<div class="sec-title">Order History</div>', unsafe_allow_html=True)
    if not st.session_state.orders:
        st.markdown('<div class="row-card" style="padding:20px;text-align:center;color:var(--muted);font-size:0.82rem;">Koi order nahi hua abhi tak.</div>',
                    unsafe_allow_html=True)
    else:
        rows = ['<div class="row-card">']
        for o in st.session_state.orders[:20]:
            cls = "up" if o["side"] == "BUY" else "down"
            rows.append(f"""<div class="row-item">
              <div><div class="row-name">{o['ticker'].replace('.NS','')}</div>
                   <div class="row-sub">{o['time']}</div></div>
              <div><div class="row-val {cls}">{o['side']} {o['qty']}</div>
                   <div class="row-val-sub">@ ₹{o['price']:,.2f}</div></div>
            </div>""")
        rows.append("</div>")
        st.markdown("".join(rows), unsafe_allow_html=True)


PAGES = {"home": ("Home", render_home), "watchlist": ("Watchlist", render_watchlist),
         "orders": ("Orders", render_orders), "portfolio": ("Portfolio", render_portfolio)}
ICONS = {"home": ":material/home:", "watchlist": ":material/visibility:",
         "portfolio": ":material/work:", "orders": ":material/receipt_long:"}

_, render_fn = PAGES[st.session_state.tab]
render_fn()

st.markdown('<div style="height:64px;"></div>', unsafe_allow_html=True)
st.markdown("""
<style>
.st-key-bottom_nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;background:var(--card);border-top:1px solid var(--border);z-index:999;padding:6px 8px 10px;}
.st-key-bottom_nav div[data-testid="stButton"] button{border:none!important;background:transparent!important;flex-direction:column!important;font-size:0.66rem!important;padding:4px 0!important;}
.st-key-bottom_nav div[data-testid="stButton"] button[kind="primary"]{background:transparent!important;color:var(--blue)!important;}
</style>
""", unsafe_allow_html=True)
with st.container(key="bottom_nav"):
    nav_cols = st.columns(4)
    for col, key in zip(nav_cols, PAGES.keys()):
        label, _ = PAGES[key]
        with col:
            if st.button(label, icon=ICONS[key], key=f"nav_{key}", use_container_width=True,
                         type="primary" if st.session_state.tab == key else "secondary"):
                st.session_state.tab = key
                st.rerun()
