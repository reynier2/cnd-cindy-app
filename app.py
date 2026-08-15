import streamlit as st
import pandas as pd
import pydeck as pdk
import os, json, subprocess, imaplib, email, re, requests
import html as htmllib
from datetime import datetime

st.set_page_config(page_title="CND MASTER COMMAND ROOM", page_icon="🎛️", layout="wide")

PING_FILE = "E:/cindy/war_room_pings.csv"
STATS_FILE = "E:/cindy/business_stats.json"
WATCHER_LOG = "E:/cindy/watcher.log"
CREATE_NO_WINDOW = 0x08000000

if "authed" not in st.session_state:
    st.session_state.authed = False
if not st.session_state.authed:
    st.title("🔒 CND MASTER COMMAND ROOM")
    st.caption("Authorized personnel only.")
    pw = st.text_input("Passcode", type="password")
    if st.button("Unlock the Command Room"):
        if pw == "COVENANT":
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Wrong code. This room is for the CEO only.")
    st.stop()

def watcher_alive():
    try:
        out = subprocess.check_output('wmic process where "name=\'python.exe\'" get commandline', shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore")
        return "war_room_watcher" in out
    except Exception: return False

def ensure_watcher():
    if not watcher_alive():
        try:
            logf = open(WATCHER_LOG, "a", encoding="utf-8", errors="replace")
            subprocess.Popen(["python", "-u", "war_room_watcher.py"], cwd="E:/cindy", stdout=logf, stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW)
        except Exception: pass

def tail_log(path, n=14):
    try:
        lines = open(path, "r", errors="ignore").read().strip().split("\n")
        return "\n".join(lines[-n:])
    except Exception: return "(waiting for log output...)"

def terminal_html(title, text):
    safe = htmllib.escape(text)
    return f"""<div style="background:#0a0a0a;border:1px solid #2a2a2a;border-radius:8px;padding:10px 14px;height:240px;overflow:hidden;">
<div style="color:#777;font-size:10px;letter-spacing:2px;margin-bottom:8px;font-family:Consolas,monospace;">■ {title}</div>
<pre style="margin:0;white-space:pre-wrap;font-family:Consolas,monospace;font-size:11px;color:#33ff66;">{safe}</pre></div>"""

def load_pings():
    if os.path.exists(PING_FILE):
        try: return pd.read_csv(PING_FILE)
        except Exception: pass
    return pd.DataFrame(columns=["timestamp", "address", "lat", "lon", "estimate"])

def load_stats():
    if os.path.exists(STATS_FILE):
        try: return json.load(open(STATS_FILE))
        except Exception: pass
    return {}

def load_trap_activity():
    seen = {}
    def _add(subj, tstr):
        subj = subj.replace("[TRAP]", "").strip()
        if not subj or subj in seen: return
        mm = re.search(r"lat=(-?[\d.]+)\s+lon=(-?[\d.]+)", subj)
        mc = re.search(r"city=(.+)$", subj)
        seen[subj] = {"time": tstr, "event": subj, "lat": float(mm.group(1)) if mm else None, "lon": float(mm.group(2)) if mm else None, "city": mc.group(1).strip() if mc else ""}
    
    # Channel 1: ntfy
    try:
        import time as _t
        r = requests.get("https://ntfy.sh/cnd_covenant_trap_8142/json", timeout=5)
        for line in [l for l in r.text.strip().split("\n") if l.strip()][-40:]:
            d = json.loads(line)
            _add(d.get("message", ""), _t.strftime("%m-%d %H:%M", _t.localtime(d.get("time", 0))))
    except Exception: pass

    # Channel 2: Gmail
    try:
        cfg = json.load(open("E:/cindy/email_config.json"))
        strings = [v for v in cfg.values() if isinstance(v, str)] if isinstance(cfg, dict) else []
        email_addr = next((v for v in strings if "@" in v), None)
        password = next((v for v in strings if v != email_addr), None)
        if email_addr and password:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=10)
            mail.login(email_addr, password)
            mail.select("inbox")
            status, msgs = mail.search(None, 'SUBJECT "[TRAP]"')
            for e_id in msgs[0].split()[-40:]:
                status, data = mail.fetch(e_id, "(RFC822)")
                for resp in data:
                    if isinstance(resp, tuple):
                        m = email.message_from_bytes(resp[1])
                        _add(str(m.get("Subject", "")), str(m.get("Date", ""))[:22])
            mail.logout()
    except Exception: pass

    events = list(seen.values())
    if not events:
        events.append({"time": "—", "event": "(waiting for first usage ping...)", "lat": None, "lon": None, "city": ""})
    return events

ensure_watcher()
df = load_pings()
stats = load_stats()
watcher_up = watcher_alive()
acts = load_trap_activity()

st.title("🎛️ CND MASTER COMMAND ROOM")
st.caption(f"{datetime.now().strftime('%A, %B %d, %Y — %I:%M %p')} | CEO EYES ONLY")
if st.button("🔄 Refresh All Screens"): st.rerun()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("DRIVE-BY PINGS", len(df))
m2.metric("USAGE PINGS", sum(1 for a in acts if "error" not in a["event"] and "waiting" not in a["event"]))
m3.metric("PIPELINE VALUE", f"${int(df['estimate'].sum()) if len(df) else 0:,}")
m4.metric("WATCHER", "🟢 LIVE" if watcher_up else "🔴 DOWN")
m5.metric("CITIES REACHED", len(set(a["city"] for a in acts if a["city"])))

left, right = st.columns([2, 1])
with left:
    st.subheader("🗺️ WAR ROOM MAP (drive-by emails)")
    if len(df):
        layer = pdk.Layer("ScatterplotLayer", df, pickable=True, opacity=0.9, get_position="[lon, lat]", get_fill_color="[255, 70, 0, 220]", get_radius=150, radius_min_pixels=6)
        view = pdk.ViewState(latitude=df["lat"].mean(), longitude=df["lon"].mean(), zoom=3.6)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, map_style="dark", tooltip={"html": "<b>{address}</b><br/>Estimate: ${estimate}"}))
    else: st.info("No drive-by pings yet.")

    st.subheader("🌍 ADOPTION MAP (live beta usage)")
    usage_pins = [a for a in acts if a["lat"] is not None]
    if usage_pins:
        udf = pd.DataFrame(usage_pins)
        ulayer = pdk.Layer("ScatterplotLayer", udf, pickable=True, opacity=0.9, get_position="[lon, lat]", get_fill_color="[0, 230, 120, 220]", get_radius=150, radius_min_pixels=6)
        uview = pdk.ViewState(latitude=udf["lat"].mean(), longitude=udf["lon"].mean(), zoom=3.6)
        st.pydeck_chart(pdk.Deck(layers=[ulayer], initial_view_state=uview, map_style="dark", tooltip={"html": "<b>{event}</b><br/>{city}"}))
        cities = udf["city"].value_counts()
        st.markdown(" · ".join([f"**{c}**: {n}" for c, n in cities.items()]))
    else: st.info("No green pins yet. The moment anyone opens the app, runs an estimate, or pays — a green pin drops on their city.")

with right:
    st.subheader("🪤 TRAP ACTIVITY (live feed)")
    if acts:
        nv = sum(1 for a in acts if a["event"].startswith("VISIT"))
        ne = sum(1 for a in acts if a["event"].startswith("ESTIMATE"))
        npw = sum(1 for a in acts if a["event"].startswith("PAYWALL"))
        npay = sum(1 for a in acts if a["event"].startswith("PAYMENT"))
        st.markdown(f"**Visits:** {nv} · **Estimates:** {ne} · **Paywalls:** {npw} · **💰 Payments:** {npay}")
    st.markdown("---")
    st.subheader("⚙️ ENGINE ROOM")
    st.markdown(f"**Watcher:** {'🟢 Running' if watcher_up else '🔴 Down'}")
    st.markdown("**Trap:** 🟢 Dual-Channel Active")

st.markdown("### ⌨️ ENGINE TERMINALS")
tcol1, tcol2 = st.columns(2)
ph1 = tcol1.empty()
ph2 = tcol2.empty()

def paint_terminals(trap_events):
    ph1.markdown(terminal_html("WATCHER — GMAIL HUNTER", tail_log(WATCHER_LOG)), unsafe_allow_html=True)
    trap_lines = "\n".join([f"{a['time']}  {a['event']}" for a in trap_events[:10]])
    ph2.markdown(terminal_html("TRAP FEED — LIVE USAGE", trap_lines), unsafe_allow_html=True)

paint_terminals(acts)

t1, t2 = st.tabs(["📋 FULL PING LOG", "💼 BUSINESS INTEL"])
with t1: st.dataframe(df.sort_values("timestamp", ascending=False) if len(df) else df)
with t2:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", stats.get("leads_contacted", 0))
    c2.metric("Contracts", stats.get("deals_under_contract", 0))
    c3.metric("Investors", stats.get("investors_emailed", 0))
    c4.metric("Offers", stats.get("offers_sent", 0))
