"""
extractor.py
Bill / warranty-card extraction using Google's Gemini Vision API (free tier).
Replaces the old local-Ollama pipeline (GTX 1650 4GB VRAM was too weak,
causing garbage output, JSON parse crashes, and 100-270 sec/image speeds).

Cloud API = no GPU dependency, ~2-5 sec/image, reliable structured JSON,
and strong handling of BOTH printed and handwritten text in the same bill.

Gemini free tier: no credit card needed, key from aistudio.google.com/apikey.
"""

import os
import json
import base64
import re
from pathlib import Path

import google.generativeai as genai

# ---- Config -----------------------------------------------------------
# Set your key as an environment variable before running:
#   Windows (PowerShell):  $env:GEMINI_API_KEY="AIza..."
#   Linux/Mac:              export GEMINI_API_KEY="AIza..."
MODEL = "gemini-3.6-flash"

FIELD_LIST = [
    "shop_vendor", "address", "phone", "bill_no", "date",
    "customer_name", "customer_address", "item_description",
    "serial_batch_no", "qty", "rate", "amount", "total", "notes",
]

# Human-readable labels shown in the UI (same order/labels as the old
# Eapro reference workbook, so exports stay compatible).
FIELD_LABELS = {
    "shop_vendor": "Shop/Vendor",
    "address": "Address",
    "phone": "Phone",
    "bill_no": "Bill/Invoice No.",
    "date": "Date",
    "customer_name": "Customer Name",
    "customer_address": "Customer Address",
    "item_description": "Item/Description",
    "serial_batch_no": "Serial/Batch No.",
    "qty": "Qty",
    "rate": "Rate",
    "amount": "Amount",
    "total": "Total",
    "notes": "Notes",
}

PROMPT = f"""You are an expert document-extraction system. You will be shown a photo of a
retail bill / invoice / warranty card. It may contain BOTH machine-printed text and
handwritten text (often the customer name, phone number, date, or item details are
handwritten while the shop letterhead is printed).

Extract the following fields as a flat JSON object with EXACTLY these keys:
{json.dumps(FIELD_LIST)}

Rules:
- If a field is not present or unreadable, use an empty string "" for it — never omit a key.
- Read handwritten text as carefully as printed text; do not skip it.
- If there are multiple line items, join them into "item_description" separated by " | ".
- Numeric fields (qty, rate, amount, total) should be plain numbers as strings, no currency symbols.
- Do not invent data. Only extract what is visibly written.
- Respond with ONLY the JSON object. No markdown fences, no commentary, no preamble.
"""


def configure_gemini():
    """Call once at app startup after GEMINI_API_KEY is set in the environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)


def _media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def extract_fields(image_path: str, client=None) -> dict:
    """
    Send one bill image to Gemini Vision and return a dict of extracted fields.
    Always returns all FIELD_LIST keys (empty string if not found).
    Raises on API failure; caller decides how to handle/report it.
    `client` param kept for call-site compatibility; unused (genai is
    configured globally via configure_gemini()).
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        [
            {"mime_type": _media_type(image_path), "data": image_bytes},
            PROMPT,
        ]
    )

    raw_text = response.text
    cleaned = _strip_json_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: try to grab the first {...} block in case the model
        # added any stray text despite instructions.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse JSON from model response:\n{raw_text}")
        parsed = json.loads(match.group(0))

    # Guarantee every key exists, and everything is a plain string
    # (defends against the old "list-type" crash: if the model ever
    # returns a list/dict for a field, flatten it to a string here).
    result = {}
    for key in FIELD_LIST:
        val = parsed.get(key, "")
        if isinstance(val, (list, dict)):
            val = json.dumps(val) if isinstance(val, dict) else ", ".join(str(v) for v in val)
        result[key] = "" if val is None else str(val)

    return result
