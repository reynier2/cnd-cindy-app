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
def load_openai_key():
    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_API_KEY").strip()
    key_file = Path("E:/cindy/openai_api_key.txt")
    return key_file.read_text().strip() if key_file.exists() else None

def load_rentcast_key():
    if os.getenv("RENTCAST_API_KEY"):
        return os.getenv("RENTCAST_API_KEY").strip()
    key_file = Path("E:/cindy/rentcast_api_key.txt")
    if key_file.exists():
        return key_file.read_text().strip()
    return None

API_KEY = load_openai_key()
RENTCAST_KEY = load_rentcast_key()

# === EMAIL CONFIGURATION ===
EMAIL_SENDER = "rayrealstatedeals@gmail.com"
EMAIL_APP_PASSWORD = "YOUR_16_CHAR_APP_PASSWORD_HERE" # Paste your 16-char app password here
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
    # Skipped for brevity in contractor mode, but kept for investor mode expansion
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
            2. Create a detailed ITEMIZED BID. DO NOT use Markdown tables (no '|' characters). Use this exact clean text format for each item:
            
            **ITEM: [Name of Repair, e.g., Kitchen Drywall Repair]**
            - Scope: [Brief description of work needed based on visual evidence]
            - Materials: ~$[Estimated Cost]
            - Labor: ~[Hours] hrs @ $65/hr = ~$[Labor Cost]
            - Line Total: ~$[Total Cost]
            
            3. After all items, provide a clear **GRAND TOTAL ESTIMATE: $[Total]**
            4. Add a **CRITICAL NOTES** section for potential hidden issues (e.g., 'Check behind wall for mold', 'Verify electrical panel capacity').
            
            Keep the tone professional, direct, and highly structured.
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

def create_pdf_report(text_content, output_path, title="Professional Repair Estimate"):
    pdf = FPDF()
    pdf.add_page()
    
    # --- CND BRANDING HEADER ---
    pdf.set_font("Arial", 'B', 22)          
    pdf.set_text_color(0, 51, 102)          # Professional Dark Blue
    pdf.cell(0, 12, "CND REAL ESTATE SERVICES", ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 11)          
    pdf.set_text_color(80, 80, 80)          # Dark Gray
    pdf.cell(0, 8, "Powered by Cindy AI Estimator", ln=True, align='C')
    
    pdf.ln(8)                               
    
    # Document Title
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)             # Black
    pdf.cell(0, 10, title, ln=True, align='C')
    
    pdf.ln(5)                               
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100)       
    pdf.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align='C')
    
    # Draw a clean separator line
    pdf.ln(5)
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)
    
    # --- BODY CONTENT ---
    pdf.set_font("Arial", size=11)
    pdf.set_text_color(0, 0, 0)
    
    lines = text_content.split('\n')
    
    for line in lines:
        # Clean up any stray markdown characters the AI might slip in
        safe_line = line.strip().replace('|', '-').replace('#', '')
        
        if not safe_line:
            pdf.ln(4) # Extra space for paragraph breaks
            continue
            
        # Handle Bold Headers (Our custom **ITEM:** or **GRAND TOTAL:** format)
        if safe_line.startswith("**") and safe_line.endswith("**"):
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(0, 51, 102) # Blue for headers
            # Remove the asterisks for clean printing
            clean_header = safe_line.replace("**", "")
            pdf.multi_cell(0, 7, clean_header)
            pdf.set_font("Arial", size=11) # Reset
            pdf.set_text_color(0, 0, 0)    # Reset color
        elif safe_line.startswith("-"):
            # Bullet points
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, f"  {safe_line}")
        else:
            # Standard text
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 6, safe_line)

    # --- FOOTER ---
    pdf.ln(10)
    pdf.set_draw_color(0, 51, 102)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(100, 100, 100)       
    pdf.cell(0, 5, "CND Real Estate Services | rayrealstatedeals@gmail.com", ln=True, align='C')
    pdf.cell(0, 5, "Local. Secure. Reliable.", ln=True, align='C')            
    
    pdf.output(output_path)
    return True

def send_email_with_pdf(recipient_email, pdf_path, property_address="Property"):
    if EMAIL_APP_PASSWORD == "YOUR_16_CHAR_APP_PASSWORD_HERE":
        print("[WARNING] Email App Password not set in config. Please update EMAIL_APP_PASSWORD.")
        return False
    
    print(f"[EMAIL] Preparing to send bid to {recipient_email}...")
    
    try:
        # Setup the MIME message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = f"{EMAIL_SUBJECT} - {property_address}"
        
        # Email body
        body = f"""Hello,

Please find attached the detailed, itemized repair estimate and bid generated by CND Real Estate Services. 

This estimate includes material costs, labor projections, and notes on potential hidden issues to help us move forward efficiently.

Let me know if you have any questions or if you are ready to schedule a walkthrough.

Best regards,
Ray
CND Real Estate Services
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach the PDF
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(pdf_path)}"')
        msg.attach(part)
        
        # Connect to Gmail SMTP and send
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipient_email, msg.as_string())
        server.quit()
        
        print(f"[SUCCESS] Email with PDF successfully sent to {recipient_email}!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to send email: {str(e)}")
        return False

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
            
            # === CLOSE THE CIRCUIT: AUTOMATED EMAIL ===
            if args.email:
                send_email_with_pdf(args.email, pdf_file, property_address=f"Zip {args.zipcode}")
            else:
                print("[INFO] No email provided via --email flag. Skipping email dispatch.")
        else:
            print("[FAIL] PDF creation failed.")

    else:
        # === INVESTOR MODE LOGIC ===
        if not args.address:
            args.address = input("\nEnter Property Address: ")
        
        print("🏠 Investor Mode Active (Logic ready for expansion)")
        # You can paste your old investor code block here to keep both modes working!

if __name__ == "__main__":
    main()
