import streamlit as st
import os
import datetime
import base64
from pathlib import Path
from fpdf import FPDF
import tempfile
import shutil

# --- CONFIGURE PAGE ICON ---
st.set_page_config(
    page_title="CND Real Estate Services",
    page_icon="🏗️",  # <--- PASTE THE CRANE EMOJI HERE!
    layout="wide"
)
st.title("🏗️ CND Real Estate Services")
st.subheader("Powered by Cindy AI Estimator")
st.markdown("---")

st.write("Upload photos of the repair job, and Cindy will generate a professional bid instantly.")

# File Uploader
uploaded_files = st.file_uploader("Choose images", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])

if uploaded_files:
    st.write(f"✅ {len(uploaded_files)} photo(s) uploaded!")
    
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
                
                # --- SIMULATION FOR DEMO (Replace with real AI later) ---
                result_text = "**SIMULATED RESULT FOR DEMO:**\n\n| Item | Cost |\n|---|---|\n| Demo Repair | $100 |\n| **Total** | **$100** |"
                # ------------------------------------------------------------------
                
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
