from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def extract_invoice_data(text):
    prompt = f"""
Extract invoice details from the text below.

Return ONLY valid JSON with these fields:
- invoice_number
- vendor
- date
- total_amount

If a field is missing, use null.

Invoice text:
{text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    result = response.text.strip()

    if result.startswith("```json"):
        result = result.replace("```json", "").replace("```", "").strip()

    return json.loads(result)