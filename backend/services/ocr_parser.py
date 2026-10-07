"""
OCR and document extraction service for electricity bills (PDF and Image).
Extracts: Billing Month, Previous Reading, Current Reading, Units, Energy Charge, Fixed Charge, Duty, Total Amount.
Supports Mahavitran (Marathi), MSEDCL, BESCOM, UPPCL, Tata Power, Adani, TANGEDCO bills.
"""

import os
import re
import sys
import logging
from datetime import datetime

# Fix Windows cp1252 console encoding so Marathi/Devanagari characters don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        raw_text = _extract_from_image(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    logger.info(f"[OCR] Raw text ({len(raw_text)} chars): {raw_text[:300].encode('ascii', errors='replace').decode()}")
    extracted = _parse_bill_text(raw_text)
    extracted["raw_text_snippet"] = raw_text[:800] if raw_text else ""
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

    # 1. Try EasyOCR first (pure Python, high accuracy, no binary needed)
    try:
        import easyocr
        reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)
        results = reader.readtext(img_path, detail=0, paragraph=False)
        text = "\n".join(str(r) for r in results)
        if text.strip():
            logger.info(f"EasyOCR extracted {len(text)} chars.")
            return text
    except Exception as e:
        logger.info(f"EasyOCR extraction note: {e}")

    # 2. Fallback: Try PyTesseract with image enhancement
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import pytesseract

        tess_cmd = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tess_cmd):
            pytesseract.pytesseract.tesseract_cmd = tess_cmd

        img = Image.open(img_path)
        gray = img.convert('L')
        sharpened = gray.filter(ImageFilter.SHARPEN)
        enhanced = ImageEnhance.Contrast(sharpened).enhance(2.0)

        config = '--psm 6 -l eng+hin'
        text = pytesseract.image_to_string(enhanced, config=config)
        if not text.strip():
            text = pytesseract.image_to_string(enhanced)

        if text.strip():
            logger.info(f"PyTesseract extracted {len(text)} chars.")
    except Exception as e:
        logger.warning(f"pytesseract image extraction note: {e}")

    # 3. Fallback: OpenCV-based pre-processing + EasyOCR
    if not text.strip():
        try:
            import cv2
            import numpy as np
            import easyocr

            img_cv = cv2.imread(img_path)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            scale = 2
            resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            denoised = cv2.fastNlMeansDenoising(resized, h=10)
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            import tempfile
            tmp_path = tempfile.mktemp(suffix=".png")
            cv2.imwrite(tmp_path, thresh)

            reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)
            results = reader.readtext(tmp_path, detail=0, paragraph=False)
            text = "\n".join(str(r) for r in results)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if text.strip():
                logger.info(f"OpenCV+EasyOCR extracted {len(text)} chars.")
        except Exception as e:
            logger.warning(f"OpenCV+EasyOCR fallback note: {e}")

    return text

def _parse_bill_text(text):
    """
    Regex and keyword heuristics to extract key fields from normalized text.
    Handles: English bills, Mahavitran/Marathi bills, generic formats.
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

    # Normalize: remove commas inside numbers, collapse whitespace
    clean = re.sub(r'(\d),(\d)', r'\1\2', text)  # "1,234" -> "1234"
    clean = re.sub(r'[ \t]+', ' ', clean)
    
    # ── 1. Distributor Detection ──────────────────────────────────────────────
    if re.search(r"Mahavitran|महावितरण|MSEDCL|MAHADISCOM|Maharashtra State Electricity", clean, re.I):
        data["distributor"] = "Mahavitran"
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
        
    # ── 2. Consumer Number ────────────────────────────────────────────────────
    # English: "Consumer No: 123" | Marathi: "ग्राहक क्रमांक: 123"
    cons_match = re.search(
        r"(?:consumer\s*(?:no|number|id)|ca\s*no|k\s*no|service\s*no"
        r"|ग्राहक\s*क्रमांक)[:\s]+([0-9A-Za-z\-_]+)",
        clean, re.I
    )
    if cons_match:
        data["consumer_number"] = cons_match.group(1).strip()
        data["confidence"]["consumer_number"] = 0.90

    # ── 3. Billing Month ──────────────────────────────────────────────────────
    month_match = re.search(
        r"(?:bill\s*(?:month|date|period)|billing\s*month|बिल\s*महिना|बिलाचा\s*महिना)"
        r"[:\s]+([A-Za-z]{3,9}\s*[-/]?\s*20\d{2}|20\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]20\d{2})",
        clean, re.I
    )
    if month_match:
        parsed_m = _format_month(month_match.group(1).strip())
        if parsed_m:
            data["month"] = parsed_m
            data["confidence"]["month"] = 0.85
    else:
        m2 = re.search(
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
            r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-\s,]+(20\d{2})\b",
            clean, re.I
        )
        if m2:
            parsed_m = _format_month(f"{m2.group(1)} {m2.group(2)}")
            data["month"] = parsed_m
            data["confidence"]["month"] = 0.80
        else:
            # Date patterns like "15-DEC-25" or "04-DEC-25" found in Mahavitran bills
            m3 = re.search(
                r"(\d{1,2})[-/](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-/](\d{2,4})",
                clean, re.I
            )
            if m3:
                year = m3.group(3)
                if len(year) == 2:
                    year = "20" + year
                parsed_m = _format_month(f"{m3.group(2)} {year}")
                data["month"] = parsed_m
                data["confidence"]["month"] = 0.75

    # ── 4. Meter Readings ─────────────────────────────────────────────────────
    prev_match = re.search(
        r"(?:previous|prev|last|मागील)\s*(?:meter\s*)?reading[:\s]+(\d+(?:\.\d+)?)",
        clean, re.I
    )
    curr_match = re.search(
        r"(?:current|curr|present|चालू|सद्यः)\s*(?:meter\s*)?reading[:\s]+(\d+(?:\.\d+)?)",
        clean, re.I
    )

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

    # ── 5. Units Consumed ──────────────────────────────────────────────────────
    units_match = re.search(
        r"(?:units?\s*(?:billed|consumed|used)?|total\s*units|consumption|kwh\s*billed"
        r"|billed\s*units|युनिट|एकूण\s*युनिट)[:\s]+(\d+(?:\.\d+)?)",
        clean, re.I
    )
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

    # ── 6. Energy / Wheeling Charges ──────────────────────────────────────────
    # Marathi: "वीज आकार", English: "Energy Charges", "Wheeling Charges"
    energy_match = re.search(
        r"(?:energy\s*charges?|wheeling\s*charges?|वीज\s*आकार|ऊर्जा\s*शुल्क|ec)"
        r"[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)",
        clean, re.I
    )
    if energy_match:
        try:
            data["energy_charge"] = float(energy_match.group(1))
            data["confidence"]["energy_charge"] = 0.80
        except ValueError:
            pass

    # ── 7. Fixed Charges ──────────────────────────────────────────────────────
    # Mahavitran: "स्थिर आकार"
    fixed_match = re.search(
        r"(?:fixed\s*charges?|demand\s*charges?|स्थिर\s*आकार|fc)"
        r"[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)",
        clean, re.I
    )
    if fixed_match:
        try:
            data["fixed_charge"] = float(fixed_match.group(1))
            data["confidence"]["fixed_charge"] = 0.80
        except ValueError:
            pass

    # ── 8. Duty / Tax ─────────────────────────────────────────────────────────
    # Mahavitran: "वीज शुल्क (16 %)"
    duty_match = re.search(
        r"(?:electricity\s*duty|govt\s*duty|वीज\s*शुल्क|कर|tax|ed)"
        r"[:\s\(]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)",
        clean, re.I
    )
    if duty_match:
        try:
            data["duty"] = float(duty_match.group(1))
            data["confidence"]["duty"] = 0.75
        except ValueError:
            pass

    # ── 9. Total / Net Payable ────────────────────────────────────────────────
    # Mahavitran: "पूर्णांक देयक(रु.)" = 610.00,  "Pay Rs. 610.00" footer
    total_patterns = [
        r"Pay\s+(?:Rs\.?|₹)\s*(\d+(?:\.\d+)?)",
        r"पूर्णांक\s*देयक[^0-9]*(\d+(?:\.\d+)?)",
        r"(?:net\s*(?:bill\s*)?amount|total\s*(?:bill\s*)?amount|amount\s*payable"
        r"|net\s*payable|bill\s*amount|total\s*payable|total\s*due|net\s*due)"
        r"[:\s]+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)",
    ]
    for pat in total_patterns:
        m = re.search(pat, clean, re.I)
        if m:
            try:
                val = float(m.group(1))
                if 10 <= val <= 1_000_000:
                    data["total_amount"] = val
                    data["confidence"]["total_amount"] = 0.92
                    break
            except (ValueError, IndexError):
                pass

    # Fallback: extract all monetary amounts and pick the largest plausible value
    if not data["total_amount"]:
        amounts = re.findall(r"(?:Rs\.?|₹)\s*(\d+(?:\.\d+)?)", clean, re.I)
        if not amounts:
            amounts = re.findall(
                r"(?:total|amount|payable|net|देयक|रु\.?)[:\s=]*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)",
                clean, re.I
            )
        if amounts:
            try:
                valid = [float(v) for v in amounts if 50 <= float(v) <= 500_000]
                if valid:
                    data["total_amount"] = max(valid)
                    data["confidence"]["total_amount"] = 0.70
            except Exception:
                pass

    # ── 10. Mahavitran line-by-line fallback ──────────────────────────────────
    # Bill layout: each row is "<Marathi label> <amount>" on the same line.
    # e.g.  "स्थिर आकार  158.20"  |  "वीज आकार  286.76"  |  "वीज शुल्क (16 %)  83.62"
    # Walk through lines looking for known label keywords and grab the trailing number.
    _LINE_RULES = [
        # (field_name, confidence, keyword_regex)
        ("fixed_charge",  0.85, r"स्थिर\s*आकार"),
        ("energy_charge", 0.85, r"वीज\s*आकार"),
        ("duty",          0.80, r"वीज\s*शुल्क"),
        ("total_amount",  0.95, r"पूर्णांक\s*देयक"),
        ("consumer_number", 0.90, r"ग्राहक\s*क्रमांक"),
    ]
    for line in clean.splitlines():
        line = line.strip()
        if not line:
            continue
        for field, conf, kw in _LINE_RULES:
            if re.search(kw, line, re.I):
                # Find the last number on this line
                nums = re.findall(r"(\d+(?:\.\d+)?)", line)
                if nums:
                    try:
                        val = float(nums[-1])
                        if field == "consumer_number":
                            if not data["consumer_number"]:
                                data["consumer_number"] = nums[-1]
                                data["confidence"]["consumer_number"] = conf
                        elif field == "total_amount":
                            if not data["total_amount"] and 10 <= val <= 1_000_000:
                                data["total_amount"] = val
                                data["confidence"]["total_amount"] = conf
                        else:
                            if not data[field] and val > 0:
                                data[field] = val
                                data["confidence"][field] = conf
                    except ValueError:
                        pass
                break  # Only match one rule per line

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
