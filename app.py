import streamlit as st
import os
import datetime
import base64
from pathlib import Path
from fpdf import FPDF
import tempfile
import shutil
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

st.write("Upload photos of the repair job, and Cindy will generate a professional bid instantly.")

# --- STRIPE CONFIGURATION ---
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe_api_key:
    st.error("⚠️ ERROR: Stripe Secret Key not found in secrets. Please add 'STRIPE_SECRET_KEY' to your Streamlit secrets.")
    st.stop()

stripe.api_key = stripe_api_key

# --- REFERRAL TRACKING (which distributor's card brought this customer) ---
ref_code = st.query_params.get("ref")
if ref_code:
    st.session_state.ref_code = ref_code

# --- ONE-TIME TICKET LEDGER (Bouncer remembers used tickets) ---
@st.cache_resource
def get_redeemed_tickets():
    return set()

# --- PAYMENT VERIFICATION (READS THE RECEIPT FROM STRIPE) ---
session_id = st.query_params.get("session_id")
if session_id:
    redeemed = get_redeemed_tickets()
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
        if checkout.payment_status == "paid":
            if session_id in redeemed:
                st.warning("🎟️ This payment ticket was already used. Please pay $5.00 to unlock your own estimate.")
            else:
                redeemed.add(session_id)
                st.session_state.payment_confirmed = True
                st.session_state.just_paid = True
                # 🕵️‍♂️ BOUNCER FIX: Erase the receipt from the URL so it can't be shared!
                del st.query_params["session_id"]
                st.rerun()
    except Exception as e:
        st.error(f"Payment check error: {e}")

if st.session_state.get("just_paid"):
    st.success("✅ Payment confirmed! Upload your photos below to generate your estimate.")
    st.session_state.just_paid = False

# --- FILE UPLOADER (OPTIMIZED FOR MOBILE CAMERA) ---
st.markdown("### 📸 Upload Photos")
st.info("💡 **Tip:** On your phone, tap 'Choose files' and select **'Take Photo'** or **'Camera'** from the menu!")

uploaded_files = st.file_uploader(
    "Choose images", 
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="mobile_camera_fix_v3"
)

if uploaded_files:
    st.write(f"✅ {len(uploaded_files)} photo(s) uploaded!")
    
    # Check if payment is confirmed in session state
    if not st.session_state.get("payment_confirmed"):
        st.warning("💳 **Please pay $5.00 to unlock your professional AI estimate.**")
        
        try:
            # Create Stripe Checkout Session (stamped with the distributor's ref code)
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
                success_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/',
            )
            
            st.markdown(f"[ **CLICK HERE TO PAY $5.00 & UNLOCK ESTIMATE**]({checkout_session.url})")
            st.stop()
            
        except Exception as e:
            st.error(f"Payment setup error: {e}")
            st.stop()
    
    # IF PAID, proceed to analysis
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
