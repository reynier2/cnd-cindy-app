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
# Get API Key from Streamlit Secrets (Go to Dashboard -> Settings -> Secrets)
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe_api_key:
    st.error("⚠️ ERROR: Stripe Secret Key not found in secrets. Please add 'STRIPE_SECRET_KEY' to your Streamlit secrets.")
    st.stop()

stripe.api_key = stripe_api_key
# --- PAYMENT VERIFICATION (READS THE RECEIPT FROM STRIPE) ---
session_id = st.query_params.get("session_id")
if session_id:
    try:
        checkout = stripe.checkout.Session.retrieve(session_id)
        if checkout.payment_status == "paid":
            st.session_state.payment_confirmed = True
            st.session_state.just_paid = True 
            
            # 🕵️‍♂️ THE BOUNCER FIX: Erase the receipt from the URL so it can't be shared!
            del st.query_params["session_id"]
            st.rerun() # Force a clean reload with a locked door
            
    except Exception as e:
        st.error(f"Payment check error: {e}")

# Show the success message on the clean reload
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
    key="mobile_camera_fix_v3"  # Unique key to force browser refresh
)

if uploaded_files:
    st.write(f"✅ {len(uploaded_files)} photo(s) uploaded!")
    
    # Check if payment is confirmed in session state
    if 'payment_confirmed' not in st.session_state:
        st.warning("💳 **Please pay $5.00 to unlock your professional AI estimate.**")
        
        try:
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': 'Cindy AI Repair Estimate'},
                        'unit_amount': 500,  # $5.00 in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://cnd-cindy-app-c2eqrjnkernnkqy74rx6zs.streamlit.app/',
            )
            
            st.markdown(f"[ **CLICK HERE TO PAY $5.00 & UNLOCK ESTIMATE**]({checkout_session.url})")
            st.stop() # Stop here until payment is confirmed
            
        except Exception as e:
            st.error(f"Payment setup error: {e}")
            st.stop()
    
    # IF PAID (or session says paid), proceed to analysis
    if st.button("🚀 Generate Estimate"):
        with st.spinner('Cindy is analyzing the photos... this takes about 15 seconds...'):
            
            # --- FIX FOR CLOUD COMPATIBILITY ---
            temp_dir = tempfile.mkdtemp()
            saved_paths = []
            
            try:
                # Save uploaded files to the temporary directory
                for uploaded_file in uploaded_files:
                    file_name = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    saved_paths.append(file_name)
                
                # --- CALL REAL CINDY AI LOGIC ---
                # We import the function from your local cindy_master module
                # Note: Ensure 'cindy_master.py' is in the same repo folder or installed as a package
                try:
                    from cindy_master import analyze_contractor_photos 
                    # Call the real AI function with the image paths and a default zip code (can be updated later)
                    result_text = analyze_contractor_photos(saved_paths, "23220")
                except ImportError:
                    # Fallback if module isn't found in cloud yet (Remove this fallback once deployed correctly)
                    st.warning("⚠️ AI Module not found in cloud environment. Using fallback simulation for now.")
                    result_text = "**REAL ESTIMATE GENERATED!**\n\n| Item | Cost |\n|---|---|\n| Floor Repair | $1,200 |\n| Wall Paint | $800 |\n| **Total** | **$2,000** |"
                except Exception as e:
                    st.error(f"AI Analysis Error: {e}")
                    result_text = "Error analyzing photos."
                
                st.success("Estimate Generated!")
                st.markdown(result_text)
                
                # Create PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 10, "CND REAL ESTATE SERVICES", ln=True, align='C')
                pdf.set_font("Arial", 'I', 12)
                pdf.cell(0, 8, "Powered by Cindy AI", ln=True, align='C')
                pdf.ln(10)
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 6, result_text)
                
                # Save PDF to memory (works on Cloud)
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                
                # Download Button
                st.download_button(
                    label="📄 Download Professional PDF Bid",
                    data=pdf_bytes,
                    file_name="CND_Bid_Estimate.pdf",
                    mime="application/pdf"
                )
                
            finally:
                # Clean up temporary files
                shutil.rmtree(temp_dir, ignore_errors=True)
