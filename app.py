import streamlit as st
import os
import re
import tempfile
import shutil
import base64
import math
from fpdf import FPDF
import stripe
import requests
from urllib.parse import quote_plus
from PIL import Image
from streamlit_js_eval import streamlit_js_eval

# --- 🏗️ ENGINEERING COMPLIANCE CORE ---
class EngineeringComplianceCore:
    def __init__(self):
        self.MANNING_N_CONCRETE = 0.013
        self.ALLOWABLE_SOIL_BEARING_PSI = 30.0

    def check_city_utility_pipe(self, pipe_diameter_in, slope_pct, required_flow_cfs=15.0):
        D = pipe_diameter_in / 12.0
        S = slope_pct / 100.0
        if S <= 0: return False, "RED FLAG: Invalid slope."
        area = (math.pi * (D ** 2)) / 4.0
        hydraulic_radius = D / 4.0
        velocity = (1.486 / self.MANNING_N_CONCRETE) * (hydraulic_radius ** (2/3)) * (S ** 0.5)
        calculated_flow = velocity * area
        if calculated_flow < required_flow_cfs:
            return False, f"RED FLAG: Flow {calculated_flow:.1f} CFS < Req {required_flow_cfs} CFS."
        return True, f"PASS: Flow {calculated_flow:.1f} CFS (Req {required_flow_cfs} CFS)."

# --- DRIVE-BY GPS BRIDGE ---
def get_gps_from_image(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data or 34853 not in exif_data: return None, None
        gps_info = exif_data[34853]
        def safe_div(v):
            if isinstance(v, tuple) and len(v) == 2: return v[0] / v[1] if v[1] != 0 else 0.0
            return float(v)
        def to_deg(value): return safe_div(value[0]) + (safe_div(value[1]) / 60.0) + (safe_div(value[2]) / 3600.0)
        lat = lon = None
        if 2 in gps_info:
            lat = to_deg(gps_info[2])
            if gps_info.get(1) == 'S': lat = -lat
        if 4 in gps_info:
            lon = to_deg(gps_info[4])
            if gps_info.get(3) == 'W': lon = -lon
        return lat, lon
    except Exception: return None, None

def reverse_geocode_address(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse?format=json&lat=" + str(lat) + "&lon=" + str(lon)
        r = requests.get(url, headers={'User-Agent': 'CindyAI/1.0'}, timeout=10)
        if r.status_code == 200:
            a = r.json().get('address', {})
            street = (str(a.get('house_number', '')) + ' ' + str(a.get('road', ''))).strip()
            city = a.get('city', a.get('town', a.get('village', '')))
            state = a.get('state', '')
            if street and city and state: return street + ', ' + city + ', ' + state
        return None
    except Exception: return None

# --- 📡 ADOPTION ENGINE (DUAL-CHANNEL BULLETPROOF PINGS) ---
def get_visitor_location():
    if "visitor_loc" not in st.session_state:
        try:
            ip = None
            try: ip = st.context.ip_address
            except Exception: pass
            loc = None
            if ip:
                r = requests.get(f"https://ipwho.is/{ip}", timeout=5)
                d = r.json()
                if d.get("latitude"):
                    loc = {"lat": float(d["latitude"]), "lon": float(d["longitude"]), "city": str(d.get("city", ""))}
            st.session_state.visitor_loc = loc
        except Exception:
            st.session_state.visitor_loc = None
    return st.session_state.visitor_loc

def log_trap_event(event, detail=""):
    try:
        loc = get_visitor_location()
        if loc:
            detail = f"{detail} lat={loc['lat']:.3f} lon={loc['lon']:.3f} city={loc['city']}".strip()
        payload = f"[TRAP] {event} {detail}".strip()[:90]

        # Channel 1: ntfy.sh 
        try:
            requests.post("https://ntfy.sh/cnd_covenant_trap_8142", data=payload.encode("utf-8"), timeout=5)
        except Exception: pass

        # Channel 2: Gmail 
        try:
            import smtplib
            from email.mime.text import MIMEText
            sender = st.secrets.get("GMAIL_EMAIL") or os.getenv("GMAIL_EMAIL")
            password = st.secrets.get("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
            if sender and password:
                msg = MIMEText(f"{event} | {detail}")
                msg["Subject"] = payload
                msg["From"] = sender
                msg["To"] = sender
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as s:
                    s.login(sender, password)
                    s.send_message(msg)
        except Exception: pass
    except Exception: pass

# --- 🧠 THE REAL AI BRAIN ---
def analyze_photos_with_ai(photo_paths, zipcode, client_name=""):
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key: return "Error: OpenAI API Key missing in Streamlit Secrets."
    client_rule = f"- This report is PREPARED FOR: {client_name.upper()}. Start with this line." if client_name else "- No client name provided."
    system_prompt = f"""You are the estimating engine of CND Real Estate Services (Cindy AI).
IDENTITY RULES: NEVER invent human names. Only use "CND Real Estate Services". {client_rule}
TASK: Analyze ALL photos. Create ONE itemized bid.
MATERIAL RULES: Name Brand + Product + Size. Show math. List equivalents.
ENGINEERING RULES: If pipe seen: Run Manning's Eq. Stamp PASS/RED FLAG. If foundation: Check 30 PSI limit.
WATER RULES: Mention frost line, PRV if >80psi.
End with: "Reference prices = US national average retail. Verify stock at homedepot.com."
Output: Markdown Table + Summary."""
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": []}]
    messages[1]["content"].append({"type": "text", "text": f"Analyze {len(photo_paths)} photos. Zip: {zipcode}."})
    for path in photo_paths:
        try:
            with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            messages[1]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        except Exception: pass
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-4o", "messages": messages, "max_tokens": 4000}
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=90)
        if response.status_code == 200: return response.json()["choices"][0]["message"]["content"]
        else: return f"AI Error: {response.text}"
    except Exception as e: return f"AI Error: {str(e)}"

def translate_to_spanish(text):
    try:
        chunks, current = [], ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > 1800: chunks.append(current); current = line
            else: current = current + "\n" + line if current else line
        if current: chunks.append(current)
        out = []
        for chunk in chunks:
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=es&dt=t&q=" + quote_plus(chunk)
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                out.append("".join([seg[0] for seg in data[0] if seg and seg[0]]))
            else: out.append(chunk)
        return "\n".join(out)
    except Exception: return text

def generate_image_html(photo_paths):
    html = "<div style='margin-bottom:20px; text-align:center;'>"
    for path in photo_paths:
        try:
            with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            html += f'<img src="data:image/jpeg;base64,{b64}" style="max-width:30%; max-height:200px; margin:5px; border:1px solid #ccc;">'
        except Exception: pass
    html += "</div>"
    return html

def parse_bid_items(text):
    items = []
    for line in text.split("\n"):
        s = line.strip()
        if not s.startswith("|"): continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) < 3: continue
        first = cells[0].lower()
        if "item" in first or "name" in first: continue
        if set(first) <= set("-: "): continue
        money, words = [], []
        for c in cells:
            clean = c.replace("$", "").replace(",", "").strip()
            if re.fullmatch(r"[0-9.]+", clean): money.append(clean)
            else: words.append(c)
        if not words or len(money) < 2: continue
        items.append({"name": words[0], "desc": " ".join(words[1:]), "mat": money[0] if len(money) >= 3 else "0", "labor": money[-2], "total": money[-1]})
    return items

def build_pdf_bytes(result_text, lang, client_name="", photo_paths=[]):
    try:
        import pdfkit
        items = parse_bid_items(result_text)
        if not items: return None
        m = re.search(r"Grand Total:?\s*\$?([\d,.]+)", result_text)
        total = m.group(1) if m else "-"
        subtext = "Con tecnologia de Cindy AI" if lang == "es" else "Powered by Cindy AI Estimator"
        footer = "Gracias por elegir CND Real Estate Services." if lang == "es" else "Thank you for choosing CND Real Estate Services."
        prepared = f"<p style='color:#003366;font-weight:bold;margin:10px 0 0 0;'>PREPARED FOR: {client_name.upper()}</p>" if client_name else ""
        photo_gallery_html = generate_image_html(photo_paths) if photo_paths else ""
        html = f"""<html><head><style>
body {{ font-family: Arial, sans-serif; color: #333; margin: 40px; }}
.header {{ border-bottom: 2px solid #111; padding-bottom: 20px; margin-bottom: 30px; }}
h1 {{ margin: 0; font-size: 24px; letter-spacing: 1px; color: #003366; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
th {{ background-color: #f4f4f4; text-align: left; padding: 12px; font-size: 14px; }}
td {{ padding: 12px; border-bottom: 1px solid #ddd; font-size: 14px; }}
.total-row {{ font-weight: bold; background-color: #fafafa; }}
.right {{ text-align: right; }}
.notes {{ margin-top: 24px; font-size: 12px; color: #555; }}
.footer {{ margin-top: 40px; text-align: center; font-size: 10px; color: #999; font-style: italic; }}
</style></head><body>
<div class="header"><h1>CND REAL ESTATE SERVICES</h1><p style="color:#666;font-style:italic;margin:5px 0 0 0;">{subtext}</p>{prepared}</div>
{photo_gallery_html}
<table><tr><th>Item &amp; Description</th><th class="right">Materials</th><th class="right">Labor</th><th class="right">Total</th></tr>"""
        for it in items:
            html += f"""<tr><td><strong>{it['name']}</strong><br><span style="color:#666;font-size:12px;">{it['desc']}</span></td><td class="right">${it['mat']}</td><td class="right">${it['labor']}</td><td class="right"><strong>${it['total']}</strong></td></tr>"""
        html += f"""<tr class="total-row"><td colspan="3" class="right">Grand Total:</td><td class="right" style="color:#111;font-size:16px;">${total}</td></tr></table>"""
        if "Notes" in result_text:
            note_lines = [l for l in result_text.split("Notes", 1)[1].strip().split("\n") if l.strip()][:6]
            html += "<div class='notes'>" + "<br>".join(note_lines) + "</div>"
        html += f"<div class='footer'>{footer}</div></body></html>"
        return pdfkit.from_string(html, False)
    except Exception: return None

def build_pdf_fallback(result_text, lang, client_name=""):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial", 'B', 22); pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "CND REAL ESTATE SERVICES", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12); pdf.set_text_color(100, 100, 100)
    pdf_sub = "Con tecnologia de Cindy AI" if lang == "es" else "Powered by Cindy AI Estimator"
    pdf.cell(0, 8, pdf_sub, ln=True, align='C')
    if client_name:
        pdf.set_font("Arial", 'B', 12); pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, f"PREPARED FOR: {client_name.upper()}", ln=True, align='C')
    pdf.ln(5); pdf.set_draw_color(0, 51, 102); pdf.set_line_width(1.5); pdf.line(15, pdf.get_y(), 195, pdf.get_y()); pdf.ln(8)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", size=11)
    clean = result_text.replace("**", "").replace("*", "").replace("|", " ").replace("---", "")
    try: clean = clean.encode('latin-1', 'replace').decode('latin-1')
    except Exception: pass
    pdf.multi_cell(0, 7, clean)
    pdf.ln(10); pdf.set_font("Arial", 'I', 9); pdf.set_text_color(150, 150, 150)
    pdf_footer = "Gracias por elegir CND Real Estate Services." if lang == "es" else "Thank you for choosing CND Real Estate Services."
    pdf.cell(0, 5, pdf_footer, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="CND Real Estate Services", page_icon="cindy happy.png", layout="wide")
st.title("CND Real Estate Services")
st.markdown("---")
lang_param = st.query_params.get("lang")
if lang_param: st.session_state.lang = lang_param
tc1, tc2 = st.columns(2)
if tc1.button("🇺🇸 English"): st.session_state.lang = "en"; st.rerun()
if tc2.button("🇪🇸 Español"): st.session_state.lang = "es"; st.rerun()
lang = st.session_state.get("lang", "en")
if lang == "es":
    T = {"sub": "Con tecnología de Cindy AI", "intro": "Suba fotos ilimitadas del proyecto y Cindy generará un presupuesto profesional al instante.", "free_banner": "🎁 ¡BIENVENIDO! Su primer presupuesto es 100% GRATIS. Sin tarjeta. Después, cada presupuesto cuesta solo $5.00.", "upsell": "🔥 ¿Le gustó? Su próximo presupuesto se desbloquea por solo $5.00.", "step1": "### 💳 Paso 1 de 2: Pague $5.00 para desbloquear", "info1": "💡 Después de pagar, volverá automáticamente a esta página. Luego sube sus fotos UNA sola vez y obtiene su presupuesto.", "paylink": "👉 HAGA CLIC AQUÍ PARA PAGAR $5.00 Y DESBLOQUEAR SU PRESUPUESTO", "used": "🎟️ Este ticket de pago ya fue usado. Por favor pague $5.00 para desbloquear su propio presupuesto.", "paid": "✅ ¡Pago confirmado! Ahora suba sus fotos abajo.", "step2": "### 📸 Paso 2 de 2: Suba sus fotos", "tip": "💡 **Consejo:** En su teléfono, toque 'Choose files' y seleccione **'Take Photo'** o **'Camera'** del menú.", "uploader": "Elija imágenes", "uploaded": "foto(s) subida(s)!", "generate": "🚀 Generar Presupuesto", "spinner": "Cindy está analizando las fotos... esto toma unos 15 segundos...", "success": "¡Presupuesto Generado!", "download": "📄 Descargar Presupuesto PDF Profesional", "product": "Presupuesto de Reparación Cindy AI", "payerr": "Error al configurar el pago:", "checkerr": "Error al verificar el pago:", "client": "👤 Nombre del cliente (opcional, sale en el reporte)"}
else:
    T = {"sub": "Powered by Cindy AI Estimator", "intro": "Upload unlimited project photos of the repair job, and Cindy will generate a professional bid instantly.", "free_banner": "🎁 WELCOME! Your first AI estimate is 100% FREE. No card needed. After your free one, estimates are just $5.00 each.", "upsell": "🔥 Loved it? Your next estimate unlocks for just $5.00.", "step1": "### 💳 Step 1 of 2: Pay $5.00 to unlock", "info1": "💡 After paying, you'll be brought right back to this page. Then you upload your photos ONE time and get your bid.", "paylink": "👉 CLICK HERE TO PAY $5.00 & UNLOCK YOUR ESTIMATE", "used": "🎟️ This payment ticket was already used. Please pay $5.00 to unlock your own estimate.", "paid": "✅ Payment confirmed! Now upload your photos below.", "step2": "### 📸 Step 2 of 2: Upload your photos", "tip": "💡 **Tip:** On your phone, tap 'Choose files' and select **'Take Photo'** or **'Camera'** from the menu!", "uploader": "Choose images", "uploaded": "photo(s) uploaded!", "generate": "🚀 Generate Estimate", "spinner": "Cindy is analyzing the photos... this takes about 15 seconds...", "success": "Estimate Generated!", "download": "📄 Download Professional PDF Bid", "product": "Cindy AI Repair Estimate", "payerr": "Payment setup error:", "checkerr": "Payment check error:", "client": "👤 Client name (optional, printed on the report)"}
st.subheader(T["sub"])
st.write(T["intro"])
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe_api_key:
    try: stripe_api_key = st.secrets["STRIPE_SECRET_KEY"]
    except Exception: st.error("⚠️ ERROR: Stripe Secret Key not found."); st.stop()
stripe.api_key = stripe_api_key
master_key = os.getenv("MASTER_KEY", "")
if master_key and st.query_params.get("key") == master_key:
    st.session_state.payment_confirmed = True; st.session_state.ref_code = "OWNER"
ref_code = st.query_params.get("ref")
if ref_code: st.session_state.ref_code = ref_code
@st.cache_resource
def get_redeemed_tickets(): return set()
BURNED_TICKETS = {"cs_test_a1hA7Yia5vsCoyknw7h5UvTUpiEvchfbREQFHAgkS2zcfQaIYXvsSm1JBU"}
session_id = st.query_params.get("session_id")
if session_id:
    redeemed = get_redeemed_tickets()
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
        if checkout.payment_status == "paid":
            if session_id in redeemed or session_id in BURNED_TICKETS: st.warning(T["used"])
            else: 
                redeemed.add(session_id); st.session_state.payment_confirmed = True; st.session_state.just_paid = True
                log_trap_event("PAYMENT", f"$5 ref={st.session_state.get('ref_code', 'direct')}")
                del st.query_params["session_id"]; st.rerun()
    except Exception as e: st.error(f"{T['checkerr']} {e}")
if st.session_state.get("just_paid"): st.success(T["paid"]); st.session_state.just_paid = False
try: _freebie_flag = streamlit_js_eval(js_expression="localStorage.getItem('cnd_freebie') || ''")
except Exception: _freebie_flag = ""
has_used_freebie = (_freebie_flag == "1")
if not st.session_state.get("payment_confirmed"):
    if has_used_freebie:
        st.markdown(T["step1"]); st.info(T["info1"])
        log_trap_event("PAYWALL", f"lang={lang}")
        try:
            meta = {'ref': st.session_state.get('ref_code', 'direct'), 'lang': lang}
            checkout_session = stripe.checkout.Session.create(payment_method_types=['card'], line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': T['product']}, 'unit_amount': 500}, 'quantity': 1}], mode='payment', metadata=meta, payment_intent_data={'metadata': meta}, success_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/?session_id={CHECKOUT_SESSION_ID}', cancel_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/')
            st.markdown(f"[ **{T['paylink']}**]({checkout_session.url})")
        except Exception as e: st.error(f"{T['payerr']} {e}")
        st.stop()
    else: st.success(T["free_banner"])
st.markdown(T["step2"]); st.info(T["tip"])
log_trap_event("VISIT", f"lang={lang}")
client_name = st.text_input(T["client"], value="", key="client_name_field")
uploaded_files = st.file_uploader(T["uploader"], type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="mobile_camera_fix_v3")
if uploaded_files:
    st.write(f"✅ {len(uploaded_files)} {T['uploaded']}")
    if st.button(T["generate"]):
        with st.spinner(T["spinner"]):
            temp_dir = tempfile.mkdtemp()
            saved_paths = []
            try:
                for i, uploaded_file in enumerate(uploaded_files):
                    file_name = os.path.join(temp_dir, f"photo_{i}_{uploaded_file.name}")
                    with open(file_name, "wb") as f: f.write(uploaded_file.getbuffer())
                    saved_paths.append(file_name)
                property_line = ""
                if saved_paths:
                    lat, lon = get_gps_from_image(saved_paths[0])
                    if lat and lon:
                        address_str = reverse_geocode_address(lat, lon)
                        if address_str: property_line = "PROPERTY: " + address_str
                result_text = analyze_photos_with_ai(saved_paths, "23220", client_name)
                if property_line: result_text = property_line + "\n\n---\n\n" + result_text
                if lang == "es": result_text = translate_to_spanish(result_text)
                log_trap_event("ESTIMATE", f"photos={len(uploaded_files)} lang={lang} client={client_name}")
                st.success(T["success"]); st.markdown(result_text)
                pdf_bytes = build_pdf_bytes(result_text, lang, client_name, saved_paths)
                if not pdf_bytes: pdf_bytes = build_pdf_fallback(result_text, lang, client_name)
                st.download_button(label=T["download"], data=pdf_bytes, file_name="CND_Bid_Estimate.pdf", mime="application/pdf")
                if not has_used_freebie:
                    try: streamlit_js_eval(js_expression="localStorage.setItem('cnd_freebie','1');")
                    except Exception: pass
                    st.info(T["upsell"])
            finally: shutil.rmtree(temp_dir, ignore_errors=True)
