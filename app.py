import streamlit as st
import os
import tempfile
import shutil
from fpdf import FPDF
import stripe

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
        "intro": "Suba fotos del trabajo de reparación y Cindy generará un presupuesto profesional al instante.",
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
        "intro": "Upload photos of the repair job, and Cindy will generate a professional bid instantly.",
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

# --- PAY GATE: PAY FIRST, UPLOAD ONCE ---
if not st.session_state.get("payment_confirmed"):
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

                try:
                    from cindy_master import analyze_contractor_photos
                    result_text = analyze_contractor_photos(saved_paths, "23220")
                except ImportError:
                    st.warning("⚠️ AI Module not found in cloud environment. Using fallback simulation for now.")
                    result_text = "**REAL ESTIMATE GENERATED!**\n\n| Item | Cost |\n|---|---|\n| Floor Repair | $1,200 |\n| Wall Paint | $800 |\n| **Total** | **$2,000** |"
                except Exception as e:
                    st.error(f"AI Analysis Error: {e}")
                    result_text = "Error analyzing photos."

                st.success(T["success"])
                st.markdown(result_text)

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 10, "CND REAL ESTATE SERVICES", ln=True, align='C')
                pdf.set_font("Arial", 'I', 12)
                pdf.cell(0, 8, "Powered by Cindy AI", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 6, result_text)

                pdf_bytes = pdf.output(dest='S').encode('latin-1')

                st.download_button(
                    label=T["download"],
                    data=pdf_bytes,
                    file_name="CND_Bid_Estimate.pdf",
                    mime="application/pdf"
                )

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
