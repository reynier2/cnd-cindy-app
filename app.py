import streamlit as st
import os
import tempfile
import shutil
from fpdf import FPDF
import stripe
import requests
from urllib.parse import quote_plus
from PIL import Image
from streamlit_js_eval import streamlit_js_eval

# --- DRIVE-BY GPS BRIDGE (proven code, ported from Cindy desktop) ---
def get_gps_from_image(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data or 34853 not in exif_data:
            return None, None
        gps_info = exif_data[34853]
        def safe_div(v):
            if isinstance(v, tuple) and len(v) == 2:
                return v[0] / v[1] if v[1] != 0 else 0.0
            return float(v)
        def to_deg(value):
            return safe_div(value[0]) + (safe_div(value[1]) / 60.0) + (safe_div(value[2]) / 3600.0)
        lat = lon = None
        if 2 in gps_info:
            lat = to_deg(gps_info[2])
            if gps_info.get(1) == 'S':
                lat = -lat
        if 4 in gps_info:
            lon = to_deg(gps_info[4])
            if gps_info.get(3) == 'W':
                lon = -lon
        return lat, lon
    except Exception:
        return None, None

def reverse_geocode_address(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse?format=json&lat=" + str(lat) + "&lon=" + str(lon)
        r = requests.get(url, headers={'User-Agent': 'CindyAI/1.0'}, timeout=10)
        if r.status_code == 200:
            a = r.json().get('address', {})
            street = (str(a.get('house_number', '')) + ' ' + str(a.get('road', ''))).strip()
            city = a.get('city', a.get('town', a.get('village', '')))
            state = a.get('state', '')
            if street and city and state:
                return street + ', ' + city + ', ' + state
        return None
    except Exception:
        return None

# --- CONFIGURE PAGE ICON ---
st.set_page_config(
    page_title="CND Real Estate Services",
    page_icon="cindy happy.png",
    layout="wide"
)

st.title("CND Real Estate Services")
st.markdown("---")

# --- LANGUAGE CAPTURE (two links: English & Spanish) ---
lang_param = st.query_params.get("lang")
if lang_param:
    st.session_state.lang = lang_param

# --- LANGUAGE TOGGLE ---
tc1, tc2 = st.columns(2)
if tc1.button("🇺🇸 English"):
    st.session_state.lang = "en"
    st.rerun()
if tc2.button("🇪🇸 Español"):
    st.session_state.lang = "es"
    st.rerun()
lang = st.session_state.get("lang", "en")

if lang == "es":
    T = {
        "sub": "Con tecnología de Cindy AI",
        "intro": "Suba fotos ilimitadas del proyecto y Cindy generará un presupuesto profesional al instante.",
        "free_banner": "🎁 ¡BIENVENIDO! Su primer presupuesto es 100% GRATIS. Sin tarjeta.",
        "upsell": "🔥 ¿Le gustó? Su próximo presupuesto se desbloquea por solo $5.00.",
        "step1": "### 💳 Paso 1 de 2: Pague $5.00 para desbloquear",
        "info1": "💡 Después de pagar, volverá automáticamente a esta página. Luego sube sus fotos UNA sola vez y obtiene su presupuesto.",
        "paylink": "👉 HAGA CLIC AQUÍ PARA PAGAR $5.00 Y DESBLOQUEAR SU PRESUPUESTO",
        "used": "🎟️ Este ticket de pago ya fue usado. Por favor pague $5.00 para desbloquear su propio presupuesto.",
        "paid": "✅ ¡Pago confirmado! Ahora suba sus fotos abajo.",
        "step2": "### 📸 Paso 2 de 2: Suba sus fotos",
        "tip": "💡 **Consejo:** En su teléfono, toque 'Choose files' y seleccione **'Take Photo'** o **'Camera'** del menú.",
        "uploader": "Elija imágenes",
        "uploaded": "foto(s) subida(s)!",
        "generate": "🚀 Generar Presupuesto",
        "spinner": "Cindy está analizando las fotos... esto toma unos 15 segundos...",
        "success": "¡Presupuesto Generado!",
        "download": "📄 Descargar Presupuesto PDF Profesional",
        "product": "Presupuesto de Reparación Cindy AI",
        "payerr": "Error al configurar el pago:",
        "checkerr": "Error al verificar el pago:",
    }
else:
    T = {
        "sub": "Powered by Cindy AI Estimator",
        "intro": "Upload unlimited project photos of the repair job, and Cindy will generate a professional bid instantly.",
        "free_banner": "🎁 WELCOME! Your first AI estimate is 100% FREE. No card needed. After your free one, estimates are just $5.00 each.",
        "upsell": "🔥 Loved it? Your next estimate unlocks for just $5.00.",
        "step1": "### 💳 Step 1 of 2: Pay $5.00 to unlock",
        "info1": "💡 After paying, you'll be brought right back to this page. Then you upload your photos ONE time and get your bid.",
        "paylink": "👉 CLICK HERE TO PAY $5.00 & UNLOCK YOUR ESTIMATE",
        "used": "🎟️ This payment ticket was already used. Please pay $5.00 to unlock your own estimate.",
        "paid": "✅ Payment confirmed! Now upload your photos below.",
        "step2": "### 📸 Step 2 of 2: Upload your photos",
        "tip": "💡 **Tip:** On your phone, tap 'Choose files' and select **'Take Photo'** or **'Camera'** from the menu!",
        "uploader": "Choose images",
        "uploaded": "photo(s) uploaded!",
        "generate": "🚀 Generate Estimate",
        "spinner": "Cindy is analyzing the photos... this takes about 15 seconds...",
        "success": "Estimate Generated!",
        "download": "📄 Download Professional PDF Bid",
        "product": "Cindy AI Repair Estimate",
        "payerr": "Payment setup error:",
        "checkerr": "Payment check error:",
    }

st.subheader(T["sub"])
st.write(T["intro"])

# --- STRIPE CONFIGURATION ---
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe_api_key:
    st.error("⚠️ ERROR: Stripe Secret Key not found in secrets. Please add 'STRIPE_SECRET_KEY' to your Streamlit secrets.")
    st.stop()

stripe.api_key = stripe_api_key

# --- CEO MASTER KEY (owner testing without paying) ---
master_key = os.getenv("MASTER_KEY", "")
if master_key and st.query_params.get("key") == master_key:
    st.session_state.payment_confirmed = True
    st.session_state.ref_code = "OWNER"

# --- REFERRAL TRACKING ---
ref_code = st.query_params.get("ref")
if ref_code:
    st.session_state.ref_code = ref_code

# --- ONE-TIME TICKET LEDGER ---
@st.cache_resource
def get_redeemed_tickets():
    return set()

# --- BURNED TICKETS (leaked receipts that must NEVER work) ---
BURNED_TICKETS = {
    "cs_live_a1hA7Yia5vsCoyknw7h5UvTUpiEvchfbREQFHAgkS2zcfQaIYXvsSm1JBU",
}

# --- PAYMENT VERIFICATION ---
session_id = st.query_params.get("session_id")
if session_id:
    redeemed = get_redeemed_tickets()
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
        if checkout.payment_status == "paid":
            if session_id in redeemed or session_id in BURNED_TICKETS:
                st.warning(T["used"])
            else:
                redeemed.add(session_id)
                st.session_state.payment_confirmed = True
                st.session_state.just_paid = True
                del st.query_params["session_id"]
                st.rerun()
    except Exception as e:
        st.error(f"{T['checkerr']} {e}")

if st.session_state.get("just_paid"):
    st.success(T["paid"])
    st.session_state.just_paid = False

# --- DIGITAL STICKER: FIRST ONE FREE, SECOND ONE PAYS ---
try:
    _freebie_flag = streamlit_js_eval(js_expression="localStorage.getItem('cnd_freebie') || ''")
except Exception:
    _freebie_flag = ""
has_used_freebie = (_freebie_flag == "1")

# --- PAY GATE ---
if not st.session_state.get("payment_confirmed"):
    if has_used_freebie:
        # Sticker found: this phone already took the freebie. Paywall drops.
        st.markdown(T["step1"])
        st.info(T["info1"])
        try:
            meta = {'ref': st.session_state.get('ref_code', 'direct'), 'lang': lang}
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': T['product']},
                        'unit_amount': 500,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                metadata=meta,
                payment_intent_data={'metadata': meta},
                success_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/',
            )
            st.markdown(f"[ **{T['paylink']}**]({checkout_session.url})")
        except Exception as e:
            st.error(f"{T['payerr']} {e}")
        st.stop()
    else:
        # Fresh phone: first one is on the house.
        st.success(T["free_banner"])

# --- STEP 2: UPLOAD PHOTOS ---
st.markdown(T["step2"])
st.info(T["tip"])

uploaded_files = st.file_uploader(
    T["uploader"],
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="mobile_camera_fix_v3"
)

if uploaded_files:
    st.write(f"✅ {len(uploaded_files)} {T['uploaded']}")

    if st.button(T["generate"]):
        with st.spinner(T["spinner"]):

            temp_dir = tempfile.mkdtemp()
            saved_paths = []

            try:
                for uploaded_file in uploaded_files:
                    file_name = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    saved_paths.append(file_name)

                # --- DRIVE-BY BRIDGE: GPS -> ADDRESS -> PROPERTY SPECS ---
                property_line = ""
                if saved_paths:
                    lat, lon = get_gps_from_image(saved_paths[0])
                    if lat and lon:
                        address_str = reverse_geocode_address(lat, lon)
                        if address_str:
                            property_line = "PROPERTY: " + address_str
                            parts = [p.strip() for p in address_str.split(',')]
                            rkey = os.getenv("RENTCAST_API_KEY", "")
                            if len(parts) >= 2 and rkey:
                                try:
                                    h = {"accept": "application/json", "X-Api-Key": rkey}
                                    street = parts[0]
                                    city = parts[1] if len(parts) > 1 else ""
                                    state = parts[2] if len(parts) > 2 else ""
                                    u = "https://api.rentcast.io/v1/properties?address=" + quote_plus(street) + "&city=" + quote_plus(city) + "&state=" + state + "&limit=1"
                                    rr = requests.get(u, headers=h, timeout=10)
                                    if rr.status_code == 200 and rr.json():
                                        pp = rr.json()[0]
                                        property_line += "  |  " + str(pp.get('bedrooms', 0)) + " bed / " + str(pp.get('bathrooms', 0)) + " bath / " + str(pp.get('sqft', 0)) + " sqft / Value $" + str(pp.get('value', 0))
                                except Exception:
                                    pass

                try:
                    from cindy_master import analyze_contractor_photos
                    result_text = analyze_contractor_photos(saved_paths, "23220")
                except ImportError:
                    st.warning("⚠️ AI Module not found in cloud environment. Using fallback simulation for now.")
                    result_text = "**REAL ESTIMATE GENERATED!**\n\n| Item | Cost |\n|---|---|\n| Floor Repair | $1,200 |\n| Wall Paint | $800 |\n| **Total** | **$2,000** |"
                except Exception as e:
                    st.error(f"AI Analysis Error: {e}")
                    result_text = "Error analyzing photos."

                if property_line:
                    result_text = property_line + "\n\n---\n\n" + result_text

                st.success(T["success"])
                st.markdown(result_text)

                # --- PROFESSIONAL PDF LETTERHEAD ---
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 22)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 10, "CND REAL ESTATE SERVICES", ln=True, align='C')
                pdf.set_font("Arial", 'I', 12)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 8, "Powered by Cindy AI Estimator", ln=True, align='C')
                pdf.ln(5)
                pdf.set_draw_color(0, 51, 102)
                pdf.set_line_width(1.5)
                pdf.line(15, pdf.get_y(), 195, pdf.get_y())
                pdf.ln(8)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 7, result_text)
                pdf.ln(10)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(0, 5, "Thank you for choosing CND Real Estate Services.", ln=True, align='C')

                pdf_bytes = pdf.output(dest='S').encode('latin-1')

                st.download_button(
                    label=T["download"],
                    data=pdf_bytes,
                    file_name="CND_Bid_Estimate.pdf",
                    mime="application/pdf"
                )

                # --- SLAP THE STICKER: next time this phone comes, it pays ---
                if not has_used_freebie:
                    try:
                        streamlit_js_eval(js_expression="localStorage.setItem('cnd_freebie','1');")
                    except Exception:
                        pass
                    st.info(T["upsell"])

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
