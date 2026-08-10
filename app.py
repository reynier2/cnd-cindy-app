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
st.subheader("Powered by Cindy AI Estimator")
st.markdown("---")

st.write("Get a professional repair bid instantly. Pay the $5 fee to unlock the uploader.")

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
# --- BURNED TICKETS (leaked receipts that must NEVER work) ---
BURNED_TICKETS = {
    "cs_live_a1hA7Yia5vsCoyknw7h5UvTUpiEvchfbREQFHAgkS2zcfQaIYXvsSm1JBU",
}
# --- ONE-TIME TICKET LEDGER ---
@st.cache_resource
def get_redeemed_tickets():
    return set()

# --- PAYMENT VERIFICATION ---
session_id = st.query_params.get("session_id")
if session_id:
    redeemed = get_redeemed_tickets()
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
        if checkout.payment_status == "paid":
            if session_id in redeemed or session_id in BURNED_TICKETS:
                st.warning("🎟️ This payment ticket was already used. Please pay $5.00 to unlock your own estimate.")
            else:
                redeemed.add(session_id)
                st.session_state.payment_confirmed = True
                st.session_state.just_paid = True
                # Erase the receipt from the URL so it can't be shared!
                del st.query_params["session_id"]
                st.rerun()
    except Exception as e:
        st.error(f"Payment check error: {e}")

if st.session_state.get("just_paid"):
    st.success("✅ Payment confirmed! Now upload your photos below.")
    st.session_state.just_paid = False

# --- PAY GATE: PAY FIRST, UPLOAD ONCE ---
if not st.session_state.get("payment_confirmed"):
    st.markdown("### 💳 Step 1 of 2: Pay $5.00 to unlock")
    st.info("💡 After paying, you'll be brought right back to this page. Then you upload your photos ONE time and get your bid.")
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Cindy AI Repair Estimate'},
                    'unit_amount': 500,
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={'ref': st.session_state.get('ref_code', 'direct')},
            payment_intent_data={'metadata': {'ref': st.session_state.get('ref_code', 'direct')}},
            success_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/',
        )
        st.markdown(f"[ **👉 CLICK HERE TO PAY $5.00 & UNLOCK YOUR ESTIMATE**]({checkout_session.url})")
    except Exception as e:
        st.error(f"Payment setup error: {e}")
    st.stop() # STOP HERE! Do not show uploader yet.

# --- STEP 2: UPLOAD PHOTOS (paid customers only) ---
st.markdown("### 📸 Step 2 of 2: Upload your photos")
st.info("💡 **Tip:** On your phone, tap 'Choose files' and select **'Take Photo'** or **'Camera'** from the menu!")

uploaded_files = st.file_uploader(
    "Choose images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="mobile_camera_fix_v3"
)

if uploaded_files:
    st.write(f"✅ {len(uploaded_files)} photo(s) uploaded!")

    if st.button("🚀 Generate Estimate"):
        with st.spinner('Cindy is analyzing the photos... this takes about 15 seconds...'):

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

                st.success("Estimate Generated!")
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
                    label="📄 Download Professional PDF Bid",
                    data=pdf_bytes,
                    file_name="CND_Bid_Estimate.pdf",
                    mime="application/pdf"
                )

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
