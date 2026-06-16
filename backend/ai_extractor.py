from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)


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

    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    result = response.choices[0].message.content.strip()

    if result.startswith("```json"):
        result = result.replace("```json", "").replace("```", "").strip()

    return json.loads(result)