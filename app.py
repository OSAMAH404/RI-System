import streamlit as st
from google import genai
import json
import pandas as pd
from PIL import Image
import io
import base64

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Receipt Digitizer",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# 🔑 API KEY INPUT IN SIDEBAR
# ============================================
st.sidebar.title("⚙️ Settings")
st.sidebar.markdown("---")

# Initialize session state for API key
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# API Key input
api_key_input = st.sidebar.text_input(
    "🔑 Google API Key",
    type="password",
    value=st.session_state.api_key,
    placeholder="Enter your Gemini API key...",
    help="Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)"
)

# Update session state
if api_key_input:
    st.session_state.api_key = api_key_input

# Show API key status
if st.session_state.api_key:
    st.sidebar.success("✅ API Key configured")
else:
    st.sidebar.warning("⚠️ Please enter your API key")
    st.sidebar.markdown("[Get your free API key here](https://aistudio.google.com/app/apikey)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 About")
st.sidebar.markdown("""
This app uses Google's Gemini AI to extract data from:
- 🛒 Retail receipts
- 🍽️ Restaurant bills
- ⚡ Utility bills
- 🏨 Hotel invoices
- ⛽ Gas station receipts
- 🏥 Medical bills
- And more!
""")

# Initialize client only if API key is provided
def get_client():
    if st.session_state.api_key:
        return genai.Client(api_key=st.session_state.api_key)
    return None

# Custom CSS for premium styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        color: #a0aec0;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Card styling */
    .upload-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        margin-bottom: 2rem;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        background: linear-gradient(90deg, #00d4aa 0%, #00b894 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem !important;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
        font-size: 1rem !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    
    /* File uploader styling */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 15px;
        padding: 1rem;
        border: 2px dashed rgba(102, 126, 234, 0.5);
    }
    
    /* Success message styling */
    .success-box {
        background: linear-gradient(90deg, rgba(0, 212, 170, 0.1) 0%, rgba(0, 184, 148, 0.1) 100%);
        border-left: 4px solid #00d4aa;
        padding: 1rem 1.5rem;
        border-radius: 0 10px 10px 0;
        margin: 1rem 0;
    }
    
    /* Divider */
    .custom-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.5), transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🧾 Receipt Digitizer</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload a receipt image and let AI extract all the details for you</p>', unsafe_allow_html=True)

# System prompt for Gemini
SYSTEM_PROMPT = """
You are an expert bill and receipt analyzer. You can analyze ANY type of bill, receipt, or invoice including but not limited to:
- Retail/Shopping receipts
- Restaurant/Food bills
- Grocery store receipts
- Utility bills (electricity, water, gas, internet)
- Medical/Healthcare bills
- Hotel/Accommodation invoices
- Gas/Fuel station receipts
- Transportation receipts (taxi, airline, train)
- Subscription/Service invoices
- Bank statements
- Parking receipts
- E-commerce order confirmations

Analyze the uploaded image and extract ALL visible information comprehensively.

Return the data STRICTLY as a valid JSON object with the following structure:
{
    "bill_type": "Type of bill (e.g., 'Restaurant', 'Retail', 'Utility', 'Medical', 'Hotel', 'Gas Station', 'Grocery', 'Transportation', 'Invoice', 'Other')",
    
    "merchant_info": {
        "name": "Business/Store/Company name",
        "address": "Full address if visible",
        "phone": "Phone number if visible",
        "email": "Email if visible",
        "website": "Website if visible",
        "tax_id": "Tax ID/VAT number if visible",
        "branch": "Branch/Location name if applicable"
    },
    
    "transaction_info": {
        "date": "Transaction date",
        "time": "Transaction time if visible",
        "receipt_number": "Receipt/Invoice/Order number",
        "reference_number": "Any reference or confirmation number",
        "cashier": "Cashier/Server name if visible",
        "terminal_id": "POS/Terminal ID if visible",
        "table_number": "Table number (for restaurants)"
    },
    
    "customer_info": {
        "name": "Customer name if visible",
        "account_number": "Account/Member number if visible",
        "address": "Customer address if visible",
        "phone": "Customer phone if visible",
        "email": "Customer email if visible",
        "loyalty_points": "Loyalty/Reward points if visible"
    },
    
    "items": [
        {
            "item_name": "Name/Description of item or service",
            "item_code": "SKU/Product code if visible",
            "category": "Category if identifiable",
            "quantity": 1,
            "unit": "Unit of measurement (pcs, kg, L, etc.)",
            "unit_price": 0.00,
            "discount": 0.00,
            "tax": 0.00,
            "total_price": 0.00,
            "notes": "Any special notes or modifiers"
        }
    ],
    
    "pricing": {
        "subtotal": 0.00,
        "discount_total": 0.00,
        "discount_description": "Discount type/code if visible",
        "service_charge": 0.00,
        "service_charge_percent": null,
        "tip": 0.00,
        "delivery_fee": 0.00,
        "taxes": [
            {
                "tax_name": "Tax type (VAT, GST, Sales Tax, etc.)",
                "tax_rate": "Tax percentage if visible",
                "tax_amount": 0.00
            }
        ],
        "total_tax": 0.00,
        "total_amount": 0.00,
        "currency": "Currency code (USD, EUR, SAR, etc.)",
        "currency_symbol": "Currency symbol ($, €, ر.س, etc.)"
    },
    
    "payment": {
        "method": "Payment method (Cash, Credit Card, Debit Card, Mobile Payment, etc.)",
        "card_type": "Card brand if visible (Visa, Mastercard, etc.)",
        "card_last_four": "Last 4 digits of card if visible",
        "amount_tendered": 0.00,
        "change_given": 0.00,
        "transaction_id": "Payment transaction ID if visible",
        "approval_code": "Approval/Auth code if visible"
    },
    
    "utility_details": {
        "account_number": "Utility account number",
        "meter_number": "Meter number if applicable",
        "billing_period": "Billing period dates",
        "previous_reading": "Previous meter reading",
        "current_reading": "Current meter reading",
        "consumption": "Total consumption with unit",
        "due_date": "Payment due date",
        "late_fee": "Late payment fee if any"
    },
    
    "hotel_details": {
        "guest_name": "Guest name",
        "room_number": "Room number",
        "check_in": "Check-in date/time",
        "check_out": "Check-out date/time",
        "nights": "Number of nights",
        "room_rate": "Nightly room rate",
        "room_type": "Room type/category"
    },
    
    "fuel_details": {
        "fuel_type": "Fuel type (Regular, Premium, Diesel, etc.)",
        "pump_number": "Pump number",
        "liters_gallons": "Amount of fuel",
        "price_per_unit": "Price per liter/gallon",
        "odometer": "Odometer reading if visible",
        "vehicle_plate": "Vehicle plate number if visible"
    },
    
    "medical_details": {
        "patient_name": "Patient name",
        "provider_name": "Doctor/Provider name",
        "facility": "Hospital/Clinic name",
        "diagnosis_codes": "Diagnosis/ICD codes if visible",
        "insurance_info": "Insurance details if visible",
        "insurance_paid": "Amount paid by insurance",
        "patient_responsibility": "Amount patient owes"
    },
    
    "additional_info": {
        "return_policy": "Return policy if visible",
        "warranty_info": "Warranty information if visible",
        "barcode_data": "Barcode number if visible",
        "qr_code_content": "QR code content description if visible",
        "notes": "Any other important information",
        "promotional_messages": "Any promotional text or offers"
    }
}

Important Instructions:
- Return ONLY the JSON object, no additional text or markdown formatting
- Only include sections that are relevant to the bill type (e.g., skip hotel_details for a grocery receipt)
- If a field is not visible or unclear, use null
- For items, extract as many details as possible from the image
- Ensure all numeric values are actual numbers, not strings
- Be thorough - extract EVERY piece of visible text that could be useful
- Identify the correct bill_type based on the content
- For non-English receipts, translate key fields to English but keep original values in notes if helpful
"""


def analyze_receipt(image_bytes, mime_type):
    """Send image to Gemini API and get structured receipt data."""
    try:
        # Get client
        client = get_client()
        if not client:
            return None, "Please enter your API key in the sidebar to analyze receipts."
        
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create the content with image
        contents = [
            SYSTEM_PROMPT,
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_base64
                }
            }
        ]
        
        # Generate content using the new API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )
        
        # Extract text from response
        response_text = response.text.strip()
        
        # Clean up response if it has markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        # Parse JSON
        receipt_data = json.loads(response_text.strip())
        return receipt_data, None
        
    except json.JSONDecodeError as e:
        return None, f"Failed to parse response as JSON: {str(e)}"
    except Exception as e:
        return None, f"Error analyzing receipt: {str(e)}"


def display_results(data):
    """Display the extracted receipt data in a beautiful format."""
    
    # Bill type badge
    bill_type = data.get("bill_type", "Receipt")
    st.markdown(f"""
        <div style="display: inline-block; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
        padding: 0.5rem 1.5rem; border-radius: 25px; margin-bottom: 1rem;">
            <span style="color: white; font-weight: 600; font-size: 1rem;">📄 {bill_type}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Get nested data safely
    merchant = data.get("merchant_info", {}) or {}
    transaction = data.get("transaction_info", {}) or {}
    customer = data.get("customer_info", {}) or {}
    pricing = data.get("pricing", {}) or {}
    payment = data.get("payment", {}) or {}
    
    # ===== TOP METRICS =====
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📅 Date",
            value=transaction.get("date") or data.get("date", "N/A")
        )
    
    with col2:
        store_name = merchant.get("name") or data.get("store_name", "N/A")
        display_name = store_name[:18] + "..." if len(str(store_name)) > 18 else store_name
        st.metric(label="🏪 Merchant", value=display_name)
    
    with col3:
        total = pricing.get("total_amount") or data.get("total_amount", 0)
        currency = pricing.get("currency_symbol") or pricing.get("currency", "")
        st.metric(
            label="💰 Total",
            value=f"{currency} {total:.2f}" if total else "N/A"
        )
    
    with col4:
        method = payment.get("method") or data.get("payment_method", "N/A")
        st.metric(label="💳 Payment", value=method or "N/A")
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # ===== MERCHANT & TRANSACTION INFO =====
    with st.expander("🏢 Merchant & Transaction Details", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Merchant Information**")
            if merchant.get("name"):
                st.write(f"**Name:** {merchant['name']}")
            if merchant.get("address"):
                st.write(f"**Address:** {merchant['address']}")
            if merchant.get("phone"):
                st.write(f"**Phone:** {merchant['phone']}")
            if merchant.get("email"):
                st.write(f"**Email:** {merchant['email']}")
            if merchant.get("website"):
                st.write(f"**Website:** {merchant['website']}")
            if merchant.get("tax_id"):
                st.write(f"**Tax ID:** {merchant['tax_id']}")
            if merchant.get("branch"):
                st.write(f"**Branch:** {merchant['branch']}")
        
        with col2:
            st.markdown("**Transaction Information**")
            if transaction.get("date"):
                st.write(f"**Date:** {transaction['date']}")
            if transaction.get("time"):
                st.write(f"**Time:** {transaction['time']}")
            if transaction.get("receipt_number"):
                st.write(f"**Receipt #:** {transaction['receipt_number']}")
            if transaction.get("reference_number"):
                st.write(f"**Reference #:** {transaction['reference_number']}")
            if transaction.get("cashier"):
                st.write(f"**Cashier:** {transaction['cashier']}")
            if transaction.get("terminal_id"):
                st.write(f"**Terminal:** {transaction['terminal_id']}")
            if transaction.get("table_number"):
                st.write(f"**Table #:** {transaction['table_number']}")
    
    # ===== CUSTOMER INFO (if available) =====
    if customer and any(customer.values()):
        with st.expander("👤 Customer Information"):
            cols = st.columns(3)
            fields = [
                ("Name", customer.get("name")),
                ("Account #", customer.get("account_number")),
                ("Phone", customer.get("phone")),
                ("Email", customer.get("email")),
                ("Address", customer.get("address")),
                ("Loyalty Points", customer.get("loyalty_points"))
            ]
            for i, (label, value) in enumerate(fields):
                if value:
                    with cols[i % 3]:
                        st.write(f"**{label}:** {value}")
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # ===== ITEMS TABLE =====
    st.subheader("📋 Itemized List")
    
    items = data.get("items", [])
    if items:
        # Create DataFrame with all available columns
        df = pd.DataFrame(items)
        
        # Define column order and mappings
        column_mapping = {
            "item_name": "Item",
            "item_code": "Code",
            "category": "Category",
            "quantity": "Qty",
            "unit": "Unit",
            "unit_price": "Unit Price",
            "discount": "Discount",
            "tax": "Tax",
            "total_price": "Total",
            "notes": "Notes"
        }
        
        # Rename columns that exist
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Get currency symbol
        curr = pricing.get("currency_symbol", "$")
        
        # Format numeric columns
        for col in ["Unit Price", "Discount", "Tax", "Total"]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: f"{curr}{x:.2f}" if pd.notna(x) and x != 0 else "-"
                )
        
        # Remove columns that are all null or empty
        df = df.dropna(axis=1, how='all')
        
        # Display dataframe
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No items could be extracted from the receipt.")
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # ===== PRICING BREAKDOWN =====
    st.subheader("💵 Pricing Summary")
    
    col1, col2, col3 = st.columns(3)
    curr = pricing.get("currency_symbol", "$")
    
    with col1:
        if pricing.get("subtotal") is not None:
            st.metric(label="Subtotal", value=f"{curr}{pricing['subtotal']:.2f}")
        if pricing.get("discount_total") and pricing.get("discount_total") > 0:
            st.metric(label="Discount", value=f"-{curr}{pricing['discount_total']:.2f}")
            if pricing.get("discount_description"):
                st.caption(f"({pricing['discount_description']})")
    
    with col2:
        if pricing.get("service_charge") and pricing.get("service_charge") > 0:
            label = f"Service Charge ({pricing['service_charge_percent']}%)" if pricing.get("service_charge_percent") else "Service Charge"
            st.metric(label=label, value=f"{curr}{pricing['service_charge']:.2f}")
        if pricing.get("tip") and pricing.get("tip") > 0:
            st.metric(label="Tip", value=f"{curr}{pricing['tip']:.2f}")
        if pricing.get("delivery_fee") and pricing.get("delivery_fee") > 0:
            st.metric(label="Delivery Fee", value=f"{curr}{pricing['delivery_fee']:.2f}")
    
    with col3:
        if pricing.get("total_tax") is not None:
            st.metric(label="Total Tax", value=f"{curr}{pricing['total_tax']:.2f}")
        total_amt = pricing.get("total_amount") or data.get("total_amount", 0)
        if total_amt:
            st.metric(label="💰 TOTAL", value=f"{curr}{total_amt:.2f}")
    
    # Tax breakdown
    taxes = pricing.get("taxes", [])
    if taxes and len(taxes) > 0 and any(t.get("tax_amount") for t in taxes):
        with st.expander("📊 Tax Breakdown"):
            for tax in taxes:
                if tax.get("tax_amount"):
                    rate = f" ({tax['tax_rate']})" if tax.get("tax_rate") else ""
                    st.write(f"**{tax.get('tax_name', 'Tax')}{rate}:** {curr}{tax['tax_amount']:.2f}")
    
    # ===== PAYMENT DETAILS =====
    if payment and any(payment.values()):
        with st.expander("💳 Payment Details"):
            cols = st.columns(3)
            with cols[0]:
                if payment.get("method"):
                    st.write(f"**Method:** {payment['method']}")
                if payment.get("card_type"):
                    st.write(f"**Card Type:** {payment['card_type']}")
                if payment.get("card_last_four"):
                    st.write(f"**Card:** ****{payment['card_last_four']}")
            with cols[1]:
                if payment.get("amount_tendered"):
                    st.write(f"**Amount Tendered:** {curr}{payment['amount_tendered']:.2f}")
                if payment.get("change_given"):
                    st.write(f"**Change:** {curr}{payment['change_given']:.2f}")
            with cols[2]:
                if payment.get("transaction_id"):
                    st.write(f"**Transaction ID:** {payment['transaction_id']}")
                if payment.get("approval_code"):
                    st.write(f"**Approval Code:** {payment['approval_code']}")
    
    # ===== BILL-TYPE SPECIFIC SECTIONS =====
    
    # Utility Details
    utility = data.get("utility_details", {}) or {}
    if utility and any(utility.values()):
        with st.expander("⚡ Utility Bill Details"):
            cols = st.columns(2)
            with cols[0]:
                for key, label in [("account_number", "Account #"), ("meter_number", "Meter #"), 
                                   ("billing_period", "Billing Period"), ("due_date", "Due Date")]:
                    if utility.get(key):
                        st.write(f"**{label}:** {utility[key]}")
            with cols[1]:
                for key, label in [("previous_reading", "Previous Reading"), ("current_reading", "Current Reading"),
                                   ("consumption", "Consumption"), ("late_fee", "Late Fee")]:
                    if utility.get(key):
                        st.write(f"**{label}:** {utility[key]}")
    
    # Hotel Details
    hotel = data.get("hotel_details", {}) or {}
    if hotel and any(hotel.values()):
        with st.expander("🏨 Hotel Stay Details"):
            cols = st.columns(2)
            with cols[0]:
                for key, label in [("guest_name", "Guest"), ("room_number", "Room #"), 
                                   ("room_type", "Room Type"), ("nights", "Nights")]:
                    if hotel.get(key):
                        st.write(f"**{label}:** {hotel[key]}")
            with cols[1]:
                for key, label in [("check_in", "Check-in"), ("check_out", "Check-out"),
                                   ("room_rate", "Nightly Rate")]:
                    if hotel.get(key):
                        st.write(f"**{label}:** {hotel[key]}")
    
    # Fuel Details
    fuel = data.get("fuel_details", {}) or {}
    if fuel and any(fuel.values()):
        with st.expander("⛽ Fuel Purchase Details"):
            cols = st.columns(2)
            with cols[0]:
                for key, label in [("fuel_type", "Fuel Type"), ("pump_number", "Pump #"), 
                                   ("liters_gallons", "Volume")]:
                    if fuel.get(key):
                        st.write(f"**{label}:** {fuel[key]}")
            with cols[1]:
                for key, label in [("price_per_unit", "Price/Unit"), ("odometer", "Odometer"),
                                   ("vehicle_plate", "Vehicle Plate")]:
                    if fuel.get(key):
                        st.write(f"**{label}:** {fuel[key]}")
    
    # Medical Details
    medical = data.get("medical_details", {}) or {}
    if medical and any(medical.values()):
        with st.expander("🏥 Medical Bill Details"):
            cols = st.columns(2)
            with cols[0]:
                for key, label in [("patient_name", "Patient"), ("provider_name", "Provider"), 
                                   ("facility", "Facility"), ("diagnosis_codes", "Diagnosis Codes")]:
                    if medical.get(key):
                        st.write(f"**{label}:** {medical[key]}")
            with cols[1]:
                for key, label in [("insurance_info", "Insurance"), ("insurance_paid", "Insurance Paid"),
                                   ("patient_responsibility", "Patient Owes")]:
                    if medical.get(key):
                        st.write(f"**{label}:** {medical[key]}")
    
    # Additional Info
    additional = data.get("additional_info", {}) or {}
    if additional and any(additional.values()):
        with st.expander("ℹ️ Additional Information"):
            for key, label in [("return_policy", "Return Policy"), ("warranty_info", "Warranty"),
                              ("barcode_data", "Barcode"), ("qr_code_content", "QR Code"),
                              ("promotional_messages", "Promotions"), ("notes", "Notes")]:
                if additional.get(key):
                    st.write(f"**{label}:** {additional[key]}")
    
    # Raw JSON expander
    with st.expander("🔍 View Raw JSON Data"):
        st.json(data)


# Main app logic
def main():
    # Show info if no API key
    if not st.session_state.api_key:
        st.info("👈 **Enter your Google API key in the sidebar to get started!**")
        st.markdown("""
        ### 🚀 How to get started:
        1. Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
        2. Enter the key in the sidebar on the left
        3. Upload a receipt image to analyze
        """)
    
    # File uploader
    st.markdown("### 📤 Upload Receipt Image")
    
    uploaded_file = st.file_uploader(
        "Drag and drop or click to upload",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG"
    )
    
    if uploaded_file is not None:
        # Determine MIME type
        file_extension = uploaded_file.name.split('.')[-1].lower()
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }
        mime_type = mime_types.get(file_extension, 'image/jpeg')
        
        # Create two columns for image and results
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.markdown("### 🖼️ Uploaded Image")
            # Display the uploaded image
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Extracted Data")
            
            # Analyze button
            if st.button("✨ Analyze Receipt", use_container_width=True):
                with st.spinner("🔍 Analyzing receipt with AI..."):
                    # Read image bytes
                    uploaded_file.seek(0)
                    image_bytes = uploaded_file.read()
                    
                    # Analyze with Gemini
                    result, error = analyze_receipt(image_bytes, mime_type)
                    
                    if error:
                        st.error(f"❌ {error}")
                    elif result:
                        st.success("✅ Receipt analyzed successfully!")
                        display_results(result)
                    else:
                        st.error("❌ Could not extract data from the receipt. Please try a clearer image.")


if __name__ == "__main__":
    main()
