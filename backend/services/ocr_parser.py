"""
OCR and document extraction service for electricity bills (PDF and Image).
Extracts: Billing Month, Previous Reading, Current Reading, Units, Energy Charge, Fixed Charge, Duty, Total Amount.
"""

import os
import re
import logging
from datetime import datetime

logger = logging.getLogger("ocr_parser")

def extract_bill_data(file_path):
    """
    Extract structured bill information from PDF or image file.
    Returns extracted fields with confidence indicators and raw text for inspection.
    """
    ext = os.path.splitext(file_path)[1].lower()
    raw_text = ""
    
    if ext == ".pdf":
        raw_text = _extract_from_pdf(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        raw_text = _extract_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    extracted = _parse_bill_text(raw_text)
    extracted["raw_text_snippet"] = raw_text[:600] if raw_text else ""
    return extracted

def _extract_from_pdf(pdf_path):
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}. Trying fallback.")
        
    if not text.strip():
        # Scanned PDF fallback
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(pdf_path, first_page=1, last_page=1)
            if images:
                text = pytesseract.image_to_string(images[0])
        except Exception as e:
            logger.info(f"Scanned PDF OCR fallback note: {e}")
            
    return text

def _extract_from_image(img_path):
    text = ""
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import pytesseract
        
        img = Image.open(img_path)
        # Preprocessing: Grayscale & contrast enhancement
        gray = img.convert('L')
        enhanced = ImageEnhance.Contrast(gray).enhance(1.8)
        
        text = pytesseract.image_to_string(enhanced)
    except Exception as e:
        logger.warning(f"pytesseract image extraction note: {e}")
        
    return text

def _parse_bill_text(text):
    """
    Regex and keyword heuristics to extract key fields from normalized text.
    """
    data = {
        "month": None,
        "previous_reading": None,
        "current_reading": None,
        "units": None,
        "energy_charge": None,
        "fixed_charge": None,
        "duty": None,
        "total_amount": None,
        "consumer_number": None,
        "distributor": None,
        "confidence": {}
    }
    
    if not text:
        return data

    clean = text.replace(",", "")
    
    # 1. Distributor detection
    if re.search(r"MSEDCL|MAHADISCOM|Maharashtra State Electricity", clean, re.I):
        data["distributor"] = "MSEDCL"
    elif re.search(r"Tata Power", clean, re.I):
        data["distributor"] = "Tata Power"
    elif re.search(r"Adani Electricity", clean, re.I):
        data["distributor"] = "Adani Electricity"
    elif re.search(r"BESCOM", clean, re.I):
        data["distributor"] = "BESCOM"
    elif re.search(r"UPPCL", clean, re.I):
        data["distributor"] = "UPPCL"
    elif re.search(r"TANGEDCO", clean, re.I):
        data["distributor"] = "TANGEDCO"
        
    # 2. Consumer Number
    cons_match = re.search(r"(?:consumer\s*(?:no|number|id)|ca\s*no|k\s*no|service\s*no)[:\s]+([0-9A-Za-z\-_]+)", clean, re.I)
    if cons_match:
        data["consumer_number"] = cons_match.group(1).strip()
        data["confidence"]["consumer_number"] = 0.90

    # 3. Billing Month / Bill Date
    month_match = re.search(r"(?:bill\s*(?:month|date|period)|billing\s*month)[:\s]+([A-Za-z]{3,9}\s*[-/]?\s*20\d{2}|20\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]20\d{2})", clean, re.I)
    if month_match:
        raw_m = month_match.group(1).strip()
        parsed_m = _format_month(raw_m)
        if parsed_m:
            data["month"] = parsed_m
            data["confidence"]["month"] = 0.85
    else:
        # Search for Month Name + Year pattern e.g. "May 2026", "JUN-2026"
        m2 = re.search(r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-\s,]+(20\d{2})\b", clean, re.I)
        if m2:
            parsed_m = _format_month(f"{m2.group(1)} {m2.group(2)}")
            data["month"] = parsed_m
            data["confidence"]["month"] = 0.80

    # 4. Previous and Current Meter Readings
    prev_match = re.search(r"(?:previous|prev|last)\s*(?:meter\s*)?reading[:\s]+(\d+(?:\.\d+)?)", clean, re.I)
    curr_match = re.search(r"(?:current|curr|present)\s*(?:meter\s*)?reading[:\s]+(\d+(?:\.\d+)?)", clean, re.I)
    
    if prev_match:
        try:
            data["previous_reading"] = float(prev_match.group(1))
            data["confidence"]["previous_reading"] = 0.85
        except ValueError:
            pass
            
    if curr_match:
        try:
            data["current_reading"] = float(curr_match.group(1))
            data["confidence"]["current_reading"] = 0.85
        except ValueError:
            pass

    # 5. Units Consumed
    units_match = re.search(r"(?:units\s*billed|units\s*consumed|total\s*units|consumption|kwh\s*billed|billed\s*units)[:\s]+(\d+(?:\.\d+)?)", clean, re.I)
    if units_match:
        try:
            data["units"] = float(units_match.group(1))
            data["confidence"]["units"] = 0.90
        except ValueError:
            pass
    elif data["previous_reading"] is not None and data["current_reading"] is not None:
        if data["current_reading"] >= data["previous_reading"]:
            data["units"] = round(data["current_reading"] - data["previous_reading"], 2)
            data["confidence"]["units"] = 0.95

    # 6. Energy Charge
    energy_match = re.search(r"(?:energy\s*charges?|wheeling\s*charges?|ec)[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", clean, re.I)
    if energy_match:
        try:
            data["energy_charge"] = float(energy_match.group(1))
            data["confidence"]["energy_charge"] = 0.80
        except ValueError:
            pass

    # 7. Fixed Charge
    fixed_match = re.search(r"(?:fixed\s*charges?|demand\s*charges?|fc)[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", clean, re.I)
    if fixed_match:
        try:
            data["fixed_charge"] = float(fixed_match.group(1))
            data["confidence"]["fixed_charge"] = 0.80
        except ValueError:
            pass

    # 8. Electricity Duty / Taxes
    duty_match = re.search(r"(?:electricity\s*duty|govt\s*duty|tax|ed)[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", clean, re.I)
    if duty_match:
        try:
            data["duty"] = float(duty_match.group(1))
            data["confidence"]["duty"] = 0.75
        except ValueError:
            pass

    # 9. Total / Net Payable Amount
    total_match = re.search(r"(?:net\s*(?:bill\s*)?amount|total\s*(?:bill\s*)?amount|amount\s*payable|net\s*payable|bill\s*amount|total\s*payable)[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", clean, re.I)
    if total_match:
        try:
            data["total_amount"] = float(total_match.group(1))
            data["confidence"]["total_amount"] = 0.90
        except ValueError:
            pass

    return data

def _format_month(raw_str):
    """Normalize various date/month strings to YYYY-MM format"""
    raw_str = raw_str.strip().replace("/", "-")
    for fmt in ("%b %Y", "%B %Y", "%b-%Y", "%B-%Y", "%Y-%m", "%m-%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(raw_str, fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue
    return None
