import os
import sys
import io
import datetime
import requests
import base64
import json
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from fpdf import FPDF
from urllib.parse import quote_plus

# === CRITICAL FIX FOR AUTOMATION ===
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass

# === CONFIGURATION ===
def load_openai_key():    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_API_KEY").strip()
    
    key_file = Path("E:/cindy/openai_api_key.txt")
    return key_file.read_text().strip() if key_file.exists() else None

def load_rentcast_key():
    key_file = Path("E:/cindy/rentcast_api_key.txt")
    if key_file.exists():
        return key_file.read_text().strip()
    return None

API_KEY = load_openai_key()
RENTCAST_KEY = load_rentcast_key()

# === EMAIL CONFIGURATION ===
EMAIL_SENDER = "rayrealstatedeals@gmail.com"
EMAIL_APP_PASSWORD = "YOUR_16_CHAR_APP_PASSWORD_HERE" # Paste your password here
EMAIL_SUBJECT = "Your Repair Estimate is Ready!"

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
RENTCAST_URL = "https://api.rentcast.io/v1/properties"

HEADERS_OPENAI = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def get_current_time_context():
    now = datetime.datetime.now()
    return f"Current Date: {now.strftime('%A, %B %d, %Y')}. Current Time: {now.strftime('%I:%M %p')}."

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def fetch_property_data(address, city, state):
    # (Same as before - skipped for brevity in contractor mode)
    data = {"address": f"{address}, {city}, {state}", "error": "Skipped in Contractor Mode"}
    return data

def analyze_contractor_photos(photo_paths, zipcode="20000"):
    """Analyzes photos specifically for Contractor Bidding."""
    if not API_KEY:
        return "Error: OpenAI API Key missing."
    
    if not photo_paths:
        return "Error: No photos provided."

    messages = [
        {
            "role": "system", 
            "content": f"""You are an expert Licensed General Contractor and Construction Estimator. 
            {get_current_time_context()}
            
            Your Task:
            1. Analyze the provided photos carefully. Identify ALL visible damage, needed repairs, and renovation opportunities.
            2. Create a detailed ITEMIZED BID including:
               - Item Name (e.g., 'Drywall Repair', 'Kitchen Cabinet Install')
               - Description of work needed based on visual evidence.
               - Estimated Material Cost (based on US averages for Zip Code {zipcode}).
               - Estimated Labor Hours & Cost (assume $65/hr labor rate unless specified otherwise).
               - Total Line Item Cost.
            3. Provide a GRAND TOTAL for the project.
            4. Add a 'Notes' section for potential hidden issues (e.g., 'Check behind wall for mold').
            
            Output Format: Markdown Table for the bid, followed by a summary.
            """
        },
        {
            "role": "user",
            "content": []
        }
    ]
    
    prompt_text = f"Analyze these construction/repair photos for a bid estimate. Location Zip: {zipcode}.\n\nBe specific about materials and labor."
    
    messages[1]["content"].append({"type": "text", "text": prompt_text})
    
    # Add Images
    for path in photo_paths:
        if os.path.exists(path):
            try:
                base64_img = encode_image(path)
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                })
                print(f"[PHOTO] Loaded: {os.path.basename(path)}")
            except Exception as e:
                print(f"[WARN] Could not load image {path}: {e}")
        else:
            print(f"[ERROR] Image not found: {path}")

    payload = {
        "model": "gpt-4o", # Using GPT-4o for best vision capabilities
        "messages": messages,
        "max_tokens": 4000
    }
    
    try:
        print("[AI] Analyzing construction photos... this may take 10-20 seconds...")
        response = requests.post(OPENAI_URL, headers=HEADERS_OPENAI, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"API Error: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

def create_pdf_report(text_content, output_path, title="Investment Dossier"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", 'B', 16)
    # --- CND BRANDING HEADER ---
    pdf.set_font("Arial", 'B', 22)          # Big Bold Font
    pdf.set_text_color(0, 51, 102)          # Professional Dark Blue Color
    pdf.cell(0, 12, "CND REAL ESTATE SERVICES", ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 12)          # Italic Subtitle
    pdf.set_text_color(80, 80, 80)          # Dark Gray
    pdf.cell(0, 8, "Powered by Cindy AI Estimator", ln=True, align='C')
    
    pdf.ln(5)                               # Little space
    
    # Original Title Line (Smaller now)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)             # Black
    pdf.cell(0, 10, "Professional Repair Estimate", ln=True, align='C')
    
    pdf.ln(5)                               # Space before content
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Generated on: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    lines = text_content.split('\n')
    
    for line in lines:
        safe_line = line.encode('latin-1', 'ignore').decode('latin-1')
        if "|" in safe_line:
            pdf.set_font("Courier", size=8) 
            pdf.multi_cell(0, 5, safe_line)
            pdf.set_font("Arial", size=11)
        else:
            if "**" in safe_line:
                parts = safe_line.split("**")
                for i, part in enumerate(parts):
                    if i % 2 != 0: 
                        pdf.set_font("Arial", 'B', 11)
                        pdf.write(6, part)
                        pdf.set_font("Arial", size=11)
                    else:
                        pdf.write(6, part)
                pdf.ln(5)
            else:
                pdf.multi_cell(0, 6, safe_line)
                pdf.ln(2)
    # --- FOOTER WITH CONTACT INFO ---
    pdf.ln(15)                              # Space at bottom
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100)       # Light Gray
    pdf.cell(0, 6, "Generated by CND Real Estate Services | rayrealstatedeals@gmail.com", ln=True, align='C')
    pdf.cell(0, 6, "www.cndrealestate.com (Coming Soon)", ln=True, align='C')            
    pdf.output(output_path)
    return True

def send_email_with_pdf(recipient_email, pdf_path, subject_suffix):
    if EMAIL_APP_PASSWORD == "YOUR_16_CHAR_APP_PASSWORD_HERE":
        print("[WARNING] Email App Password not set. Skipping email.")
        return False
    # ... (Same email logic as before) ...
    print(f"[EMAIL] Sending to {recipient_email}...")
    return True # Simplified for demo

def main():
    parser = argparse.ArgumentParser(description="Cindy Master: Investor & Contractor Edition")
    parser.add_argument("--mode", type=str, default="investor", choices=["investor", "contractorestimate"], help="Mode: investor or contractorestimate")
    parser.add_argument("--address", type=str, help="Property Address (for Investor Mode)")
    parser.add_argument("--email", type=str, help="Client Email")
    parser.add_argument("--zipcode", type=str, default="20000", help="Zip Code for Pricing (Contractor Mode)")
    args = parser.parse_args()
    
    print("\n" + "="*70)
    if args.mode == "contractorestimate":
        print("👷 CINDY CONTRACTOR ESTIMATOR MODE")
    else:
        print("🏠 CINDY INVESTOR ANALYST MODE")
    print("="*70)
    print(f" {get_current_time_context()}")
    print("-" * 70)

    photo_paths = []
    
    # --- PHOTO INPUT ---
    print("\n📸 How many photos to upload for analysis? (Max 10)")
    try:
        count = int(input("Enter number: "))
    except ValueError:
        count = 0
        
    for i in range(count):
        path = input(f"Photo {i+1} Full Path: ").strip().strip('"')
        if os.path.exists(path):
            photo_paths.append(path)
        else:
            print(f"⚠️ File not found: {path}")

    if args.mode == "contractorestimate":
        # === CONTRACTOR MODE LOGIC ===
        if not photo_paths:
            print("❌ No photos provided. Cannot generate estimate.")
            return
            
        report = analyze_contractor_photos(photo_paths, args.zipcode)
        
        if "Error" in report:
            print(f"❌ Analysis Failed: {report}")
            return
            
        print("\n" + "="*70)
        print("✅ CONTRACTOR BID COMPLETE!")
        print("="*70)
        print(report)
        
        # Save Files
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        reports_dir = "E:/cindy/reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        pdf_file = f"{reports_dir}/Contractor_Bid_{timestamp}.pdf"
        
        if create_pdf_report(report, pdf_file, title="Professional Repair Estimate"):
            print(f"[PDF] Bid Saved: {pdf_file}")
            # Optional: Email logic here
        else:
            print("[FAIL] PDF creation failed.")

    else:
        # === INVESTOR MODE LOGIC (Existing) ===
        if not args.address:
            args.address = input("\nEnter Property Address: ")
        
        # (Insert existing investor logic here - omitted for brevity but keep your old code here)
        print("🏠 Investor Mode Active (Logic unchanged from previous version)")
        # You can paste your old investor code block here to keep both modes working!

if __name__ == "__main__":
    main()
